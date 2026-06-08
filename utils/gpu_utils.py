"""
GPU/CPU 自适应处理工具函数

此模块提供无状态的 GPU/CPU 自适应处理函数
节点通过组合这些函数获得 GPU 分块 + OOM 回退 + 进度条能力，

1. 自适应策略选择（auto 模式）：
   - 估算当前数据所需显存
   - 查询 GPU 可用显存（减去 500MB 安全余量）
   - 所需显存 ≤ 可用显存 × 50% → GPU 分块处理
   - 否则 → CPU 多线程处理

2. 单一路径原则：
   - 节点不需要判断 device=="cpu" 还是 device=="gpu"
   - adaptive_process 内部统一调度，GPU OOM 时自动回退 CPU
   - 进度条在回退时自动重建，避免累计超 100%

3. 无状态设计：
   - 所有配置通过参数传入（batch_size / device / cpu_workers）
   - process_fn 是纯函数：fn(chunk, **kwargs) → Tensor
   - 不依赖实例状态，每次调用完全独立

4. 内存管理：
   - GPU 分块：每处理完一个 chunk 立即 del + empty_cache
   - OOM 回退：显式 gc.collect() 辅助 Python 回收
   - CPU 多线程：ThreadPoolExecutor 的 future.result() 自动管理生命周期

=============================================================================
使用模式
=============================================================================

    from ..utils import adaptive_process, expand_mask

    def expand(self, mask, expand=0, batch_size=8, device="auto"):
        if expand == 0:
            return (mask.clone(),)

        result = adaptive_process(
            mask,                               # 输入张量 [B, ...]
            expand_mask,                        # 处理函数 fn(chunk, expand=expand) → Tensor
            batch_size=batch_size,              # GPU 分块大小
            device=device,                      # "auto" / "gpu" / "cpu"
            desc=f"Mask Expand ({expand})",     # 进度条描述
            steps_per_item=abs(expand),         # 每样本进度步数
            expand=expand,                      # → 作为 kwargs 传给 expand_mask
        )
        return (result,)

=============================================================================
核心函数
=============================================================================

    adaptive_process(data, process_fn, *,
                    batch_size, device, desc, steps_per_item,
                    memory_estimate_fn, cpu_workers, **kwargs)
"""

import gc
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

import torch

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 可选依赖检测
# ---------------------------------------------------------------------------

try:
    from comfy.utils import ProgressBar
    HAS_COMFY_PROGRESS = True
except ImportError:
    HAS_COMFY_PROGRESS = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# GPU 安全余量（MB）：避免把最后一点显存也占满导致驱动崩溃
GPU_SAFETY_MARGIN_MB = 500

# 显存占空比：规划时只使用可用显存的 50%，为 PyTorch 内部缓存/碎片留空间
MEMORY_HEADROOM_FACTOR = 0.5

# 显存估算放大系数：
#   ×1  → 输入数据（从 CPU 拷贝到 GPU）
#   ×2  → 输出数据（process_fn 返回的 Tensor）
#   ×3  → 中间缓冲（如卷积核、临时特征图、PyTorch 内部分配）
MEMORY_ESTIMATE_FACTOR = 3


# ============================================================================
# 内部辅助函数
# ============================================================================

#region 获取当前 GPU 可用显存（GB）。
def _get_available_gpu_memory() -> float:
    """
    获取当前 GPU 可用显存（GB）。

    计算公式：
        available = (total_memory - allocated_memory - safety_margin) / (1024³)

    返回值为 0.0 表示 GPU 不可用或已耗尽。
    """
    if not torch.cuda.is_available():
        return 0.0

    allocated = torch.cuda.memory_allocated()
    total = torch.cuda.get_device_properties(0).total_memory
    available = (total - allocated - GPU_SAFETY_MARGIN_MB * 1024 ** 2) / (1024 ** 3)

    if available < 0:
        logger.warning(
            "GPU 显存已耗尽: allocated=%.2fGB, total=%.2fGB",
            allocated / (1024 ** 3),
            total / (1024 ** 3),
        )
        return 0.0

    return available
#endregion

#region 默认显存估算函数。
def _default_memory_estimate(data: torch.Tensor, batch_size: int) -> float:
    """
    默认显存估算函数。

    公式：
        4D 输入 [B, H, W, C]:  batch_size × H × W × C × 4 字节 × 3 倍 / (1024³)
        3D 输入 [B, H, W]:     batch_size × H × W × 1 × 4 字节 × 3 倍 / (1024³)

    ×3 的 3 倍放大系数覆盖输入 + 输出 + 中间缓存（见 MEMORY_ESTIMATE_FACTOR 注释）。
    C=1 对于 3D 数据是保守估计（实际遮罩处理通常不产生多通道中间结果）。

    注意：
        如果 process_fn 的输出比输入大很多（如 mask→RGB 图像），
        调用方应传入自定义 memory_estimate_fn 进行更准确的估算。
    """
    if data.dim() == 4:
        _, H, W, C = data.shape
        return batch_size * H * W * C * 4 * MEMORY_ESTIMATE_FACTOR / (1024 ** 3)
    else:
        _, H, W = data.shape
        return batch_size * H * W * 1 * 4 * MEMORY_ESTIMATE_FACTOR / (1024 ** 3)
#endregion

#region 决定处理策略："cpu" | "gpu_chunked"。
def _determine_strategy(
    data: torch.Tensor,
    device_preference: str,
    memory_estimate_fn: Optional[Callable] = None,
    batch_size: int = 8,
) -> str:
    #1. device="cpu"     → 直接使用 CPU
    if device_preference == "cpu":
        logger.info("用户指定 CPU 模式")
        return "cpu"
    #2. device="gpu"     → 尝试 GPU（不可用时降级 CPU）
    if device_preference == "gpu":
        if torch.cuda.is_available():
            logger.info("用户指定 GPU 模式")
            return "gpu_chunked"
        logger.warning("GPU 不可用，降级到 CPU 模式")
        return "cpu"
    #3. device="auto"    → auto 模式：根据显存自动选择
    if not torch.cuda.is_available():
        logger.info("GPU 不可用，使用 CPU 模式")
        return "cpu"

    estimate = memory_estimate_fn or _default_memory_estimate
    required = estimate(data, batch_size)
    available = _get_available_gpu_memory()

    logger.info(
        "显存估算: 需要 %.2fGB, 可用 %.2fGB (阈值 %.0f%%)",
        required,
        available,
        MEMORY_HEADROOM_FACTOR * 100,
    )

    if required <= available * MEMORY_HEADROOM_FACTOR:
        logger.info("显存充足，使用 GPU 分块处理")
        return "gpu_chunked"

    logger.info("显存不足，降级到 CPU 模式")
    return "cpu"
#endregion



#region 创建 ComfyUI ProgressBar 和 tqdm 双层进度条。   
def _create_progress_bars(total: int, desc: str):
    """
    创建 ComfyUI ProgressBar 和 tqdm 双层进度条。

    (由 bbox_utils.py 的 bbox_to_mask 内部调用，不直接暴露给节点)
        - tqdm：在终端/日志中显示进度，方便无 GUI 环境下调试

    返回值：
        (comfy_pbar | None, tqdm_pbar | None)
    """
    comfy_pbar = None
    tqdm_pbar = None

    if HAS_COMFY_PROGRESS:
        comfy_pbar = ProgressBar(total)

    if HAS_TQDM:
        tqdm_pbar = tqdm(total=total, desc=desc)

    return comfy_pbar, tqdm_pbar
#endregion



# ============================================================================
# 处理路径：GPU 分块
# ============================================================================

#region GPU 分块处理路径。
def _gpu_chunked(
    data: torch.Tensor,
    B: int,
    process_fn: Callable,
    batch_size: int,
    steps_per_item: int,
    update_progress: Callable[[int], None],
    **kwargs,
) -> torch.Tensor:
    """
    GPU 分块处理路径。

    策略：
        - B == 1：不拆分，直接在 GPU 上处理单个样本（避免 batch_size 开销）
        - B >  1：按 batch_size 分块，逐块 →GPU→处理→保留在GPU→最后统一回CPU

    内存管理：
        - 每 N 个块释放一次 GPU 缓存（避免频繁 empty_cache）
        - 结果先保留在 GPU 列表，最后统一转移到 CPU
        - 删除中间变量，但不立即 empty_cache

    进度：
        - 每完成一个 chunk 更新 steps_per_item × chunk_actual 步
    """
    device = torch.device("cuda")

    # ---- B == 1 快速路径 ----
    if B == 1:
        single = data.to(device, non_blocking=True)
        
        with torch.no_grad():
            result = process_fn(single, **kwargs)
        
        del single
        update_progress(max(1, B * steps_per_item))
        return result.cpu()

    # ---- B > 1 标准分块路径 ----
    num_chunks = max(1, (B + batch_size - 1) // batch_size)
    results = []

    with torch.no_grad():
        for chunk_idx in range(num_chunks):
            start = chunk_idx * batch_size
            end = min(start + batch_size, B)
            chunk_actual = end - start

            # 分块 → GPU
            chunk = data[start:end].to(device, non_blocking=True)

            # 处理
            chunk_result = process_fn(chunk, **kwargs)

            # 保留在 GPU 上，暂不回 CPU
            results.append(chunk_result)
            del chunk

            update_progress(chunk_actual * steps_per_item)

            # 每 4 个块释放一次缓存，避免太频繁
            if (chunk_idx + 1) % 4 == 0:
                torch.cuda.empty_cache()

        # 最后统一转移到 CPU
        final_results = [r.cpu() for r in results]
        del results
    
    torch.cuda.empty_cache()
    return torch.cat(final_results, dim=0)
#endregion



# ============================================================================
# 处理路径：CPU 多线程
# ============================================================================

#region CPU 多线程处理路径。
def _cpu_multithread(
    data: torch.Tensor,
    B: int,
    process_fn: Callable,
    cpu_workers: int,
    steps_per_item: int,
    update_progress: Callable[[int], None],
    **kwargs,
) -> torch.Tensor:
    """
    CPU 多线程处理路径。

    策略：
        - B == 1：单样本单线程（避免线程池开销）
        - B >  1：ThreadPoolExecutor 并行处理每个样本

    线程安全：
        - 结果按索引预分配列表 [None] * B，as_completed 后填入
        - 单个样本失败不影响其他样本（异常会传播到主线程）

    注意：
        每个线程内调用 process_fn 时也包裹 torch.no_grad()，
        避免不必要的梯度图构建（虽然 CPU 上不完全阻止但减少开销）。
        传入 .clone() 而非视图，防止 process_fn 原地修改污染原始输入。
    """
    if B == 1:
        with torch.no_grad():
            result = process_fn(data.clone(), **kwargs)
        update_progress(max(1, B * steps_per_item))
        return result

    num_workers = min(cpu_workers, B)
    results = [None] * B

    logger.info("CPU 多线程处理，样本数: %d，线程数: %d", B, num_workers)

    def _worker(idx: int):
        """单个样本的处理闭包，捕获 process_fn 和 kwargs。"""
        with torch.no_grad():
            return process_fn(data[idx:idx + 1].clone(), **kwargs)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_map = {executor.submit(_worker, idx): idx for idx in range(B)}

        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception:
                logger.error("样本 %d 处理失败", idx, exc_info=True)
                # 取消剩余任务后重新抛出
                for f in future_map:
                    f.cancel()
                raise
            update_progress(steps_per_item)

    return torch.cat(results, dim=0)
#endregion



# ============================================================================
# 输入校验
# ============================================================================

#region 校验 adaptive_process 的输入数据。
def _validate_input(data: torch.Tensor) -> None:
    """
    校验 adaptive_process 的输入数据。

    检查项：
        1. 必须是 torch.Tensor
        2. 维度至少为 2（[B, ...]）
        3. 不包含 NaN（可能导致静默错误）
        4. 不包含 Inf（同上）

    抛出：
        TypeError: 非 Tensor 输入
        ValueError: 维度不足 / 包含 NaN 或 Inf
    """
    if not isinstance(data, torch.Tensor):
        raise TypeError(
            f"adaptive_process 期望 torch.Tensor 输入，收到 {type(data).__name__}"
        )

    if data.dim() < 2:
        raise ValueError(
            f"输入张量维度必须 ≥ 2（[B, ...]），当前 dim={data.dim()}, shape={data.shape}"
        )

    if torch.isnan(data).any():
        raise ValueError("输入数据包含 NaN 值，请检查上游节点输出")

    if torch.isinf(data).any():
        raise ValueError("输入数据包含 Inf 值，请检查上游节点输出")
#endregion#endregion



# ============================================================================
# 公开 API
# ============================================================================

#region adaptive_process 公开 API。
# ── 调用者 ──
#   mask_nodes.py → RT_ImageToMask, RT_MaskExpand, RT_MaskFeather, RT_MaskToImage
#   bbox_utils.py  → (import _create_progress_bars 内部使用)
# ⚠️ 修改 GPU/CPU 调度策略会影响所有 5 个使用 adaptive_process 的节点！
#   OOM 回退逻辑、分块大小选择、显存估算均在此函数统一控制。
def adaptive_process(
    data: torch.Tensor,
    process_fn: Callable[[torch.Tensor], torch.Tensor],
    *,
    batch_size: int = 8,
    device: str = "auto",
    desc: str = "Processing",
    steps_per_item: int = 1,
    memory_estimate_fn: Optional[Callable[[torch.Tensor, int], float]] = None,
    cpu_workers: Optional[int] = None,
    **kwargs,
) -> torch.Tensor:
    """
    GPU/CPU 自适应处理入口。用于：1、需要大量计算的操作。2、可能导致OOM的大张量处理。3、需要进度条展示的长时间任务。

    自动选择 GPU 分块或 CPU 多线程策略，GPU OOM 时自动回退到 CPU。
    进度条自动重建，确保 OOM 回退后进度不超过 100%。

    Args:
        data:
            输入张量，形状 [B, ...]。
            B == 0 时直接返回空数据（不做任何处理）。

        process_fn:
            处理函数，签名为 fn(chunk, **kwargs) → Tensor。
            - GPU 路径：chunk 在 GPU 上，返回张量也在 GPU 上（随后由本函数移回 CPU）
            - CPU 路径：chunk 在 CPU 上，返回张量也在 CPU 上
            - **kwargs 由本函数的同名参数传入

        batch_size:
            GPU 分块大小（默认 8）。
            每个 chunk 独立上传到 GPU → 处理 → 下载结果 → 释放显存。
            大分辨率（如 4K）建议减小此值（如 2~4）。

        device:
            设备偏好：
            - "auto"（默认）：根据显存自动选择
            - "gpu"：强制 GPU（不可用时降级 CPU）
            - "cpu"：强制 CPU

        desc:
            进度条描述文本（同时用于 ComfyUI ProgressBar 和 tqdm）。

        steps_per_item:
            每处理一个样本对应的进度条步数。
            例如 expand_mask 每像素 1 步，可设为 abs(expand)。
            默认 1 表示每样本算 1 步。

        memory_estimate_fn:
            显存估算函数 fn(data, batch_size) → GB。
            默认使用 _default_memory_estimate（3 倍放大估算）。
            如果 process_fn 输出远大于输入（如 3D→4D 转换），
            应传入自定义估算函数。

        cpu_workers:
            CPU 线程数。默认 min(batch_size, cpu_count - 1)。
            多线程对 I/O 密集型任务帮助有限，主要加速计算密集型 process_fn。

        **kwargs:
            透传给 process_fn 的额外参数。

    Returns:
        处理后的张量，保证在 CPU 上。

    Raises:
        TypeError: 输入不是 torch.Tensor
        ValueError: 输入维度不足 / 包含 NaN/Inf

    Example:
        >>> result = adaptive_process(
        ...     mask,
        ...     expand_mask,
        ...     batch_size=8,
        ...     device="auto",
        ...     desc="Mask Expand (+5)",
        ...     steps_per_item=5,
        ...     expand=5,
        ... )
    """
    # ---- 输入校验 ----
    _validate_input(data)

    B = data.shape[0]

    # ---- 空批次快速返回 ----
    if B == 0:
        logger.info("空数据（B=0），跳过处理")
        return data

    # ---- 策略选择 ----
    strategy = _determine_strategy(data, device, memory_estimate_fn, batch_size)
    total_work = max(1, B * steps_per_item)

    # ---- CPU 线程数确定 ----
    if cpu_workers is None or cpu_workers <= 0:
        max_cpu = max(1, os.cpu_count() - 1) if os.cpu_count() else 4
        cpu_workers = min(batch_size, max_cpu)

    # ---- 进度条初始化 ----
    comfy_pbar, tqdm_pbar = _create_progress_bars(total_work, desc)

    def _make_update(cp, tp) -> Callable[[int], None]:
        """闭包：将双层进度条包装为统一的 update(n) 接口。"""
        def update(n: int = 1) -> None:
            if cp is not None:
                cp.update(n)
            if tp is not None:
                tp.update(n)
        return update

    update = _make_update(comfy_pbar, tqdm_pbar)

    # ---- 执行 ----
    try:
        if strategy == "gpu_chunked":
            try:
                result = _gpu_chunked(
                    data, B, process_fn,
                    batch_size, steps_per_item, update,
                    **kwargs,
                )
            # ------------------------------------------------------------------
            # OOM 精确捕获：
            #   PyTorch >= 1.10 有 torch.cuda.OutOfMemoryError 专用异常
            #   旧版本回退到 RuntimeError + "out of memory" 字符串匹配
            #   关键：回退 CPU 前必须重建进度条，否则 GPU 已累加的步数
            #         会导致 CPU 路径从头累加后超过 total_work
            # ------------------------------------------------------------------
            except torch.cuda.OutOfMemoryError as e:
                logger.warning("GPU OOM (torch.cuda.OutOfMemoryError)，回退到 CPU: %s", e)
                logger.debug("  data.shape=%s, batch_size=%d", data.shape, batch_size)

                torch.cuda.empty_cache()
                gc.collect()

                if tqdm_pbar is not None:
                    tqdm_pbar.close()
                comfy_pbar, tqdm_pbar = _create_progress_bars(total_work, desc)
                update = _make_update(comfy_pbar, tqdm_pbar)

                result = _cpu_multithread(
                    data, B, process_fn,
                    cpu_workers, steps_per_item, update,
                    **kwargs,
                )
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.warning("GPU OOM (RuntimeError)，回退到 CPU: %s", e)
                    logger.debug("  data.shape=%s, batch_size=%d", data.shape, batch_size)

                    torch.cuda.empty_cache()
                    gc.collect()

                    if tqdm_pbar is not None:
                        tqdm_pbar.close()
                    comfy_pbar, tqdm_pbar = _create_progress_bars(total_work, desc)
                    update = _make_update(comfy_pbar, tqdm_pbar)

                    result = _cpu_multithread(
                        data, B, process_fn,
                        cpu_workers, steps_per_item, update,
                        **kwargs,
                    )
                else:
                    raise
        else:
            # CPU 路径
            result = _cpu_multithread(
                data, B, process_fn,
                cpu_workers, steps_per_item, update,
                **kwargs,
            )
    finally:
        # ---- GPU 资源清理 ----
        # 无论正常还是异常退出，确保释放 GPU 缓存，
        # 但减少 GC 调用频率
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # 关闭 tqdm 进度条（避免残留输出）
        if tqdm_pbar is not None:
            tqdm_pbar.close()

    return result
#endregion