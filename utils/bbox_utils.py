"""
BBox → Mask 转换工具函数

此模块提供边界框（Bounding Box）转换为遮罩的工具函数。

核心函数：
    bbox_to_mask(bboxes, mask_shape, *, dilation, feather, device, chunk_size)

注意：
    - GPU 按 H 维度分块（非 batch 维度），不使用 adaptive_process()
    - feather 参数需要 scipy
"""

import torch
import numpy as np
import gc
import logging
from typing import List, Tuple

try:
    import scipy.ndimage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from .gpu_utils import _create_progress_bars

logger = logging.getLogger(__name__)


# ── 调用者 ──
#   bbox_nodes.py → RT_BBoxToMask
# ⚠️ 修改 BBox→Mask 转换逻辑会影响边界框转遮罩功能！
#   沿 H 维度分块（非 batch），不使用 adaptive_process()，OOM 回退逻辑独立。
def bbox_to_mask(
    bboxes: List[List[int]],
    mask_shape: Tuple[int, int],
    dilation: int = 0,
    feather: int = 0,
    device: str = "auto",
    chunk_size: int = 256,
) -> torch.Tensor:
    """
    将 BBox 列表转换为合并后的 Mask

    分块策略沿 H 维度（非 batch），避免高分辨率 OOM。

    参数：
        bboxes:     边界框列表 [[x1,y1,x2,y2], ...]
        mask_shape: (H, W) 输出尺寸
        dilation:   边界扩展像素数
        feather:    羽化半径（需要 scipy）
        device:     "auto" / "gpu" / "cpu"
        chunk_size: GPU H 维度分块行数

    返回值：
        (H, W) 合并后的遮罩张量，在 CPU 上
    """
    if not bboxes or len(bboxes) == 0:
        return torch.zeros(mask_shape, dtype=torch.float32)

    if feather > 0 and not HAS_SCIPY:
        logger.warning("scipy 不可用，忽略 feather 参数")
        feather = 0

    if device == "auto":
        device = "gpu" if torch.cuda.is_available() else "cpu"

    if device == "cpu" or (not torch.cuda.is_available()):
        return _bbox_to_mask_cpu(bboxes, mask_shape, dilation, feather)

    try:
        return _bbox_to_mask_gpu(bboxes, mask_shape, dilation, feather, chunk_size)
    except RuntimeError as e:
        if "out of memory" not in str(e).lower():
            raise
        logger.warning("BBox→Mask GPU OOM，回退到 CPU 处理")
        torch.cuda.empty_cache()
        gc.collect()
        return _bbox_to_mask_cpu(bboxes, mask_shape, dilation, feather)


def _bbox_to_mask_gpu(
    bboxes: List[List[int]],
    mask_shape: Tuple[int, int],
    dilation: int,
    feather: int,
    chunk_size: int,
) -> torch.Tensor:
    H, W = mask_shape
    device = torch.device("cuda")
    bbox_tensor = torch.tensor(bboxes, dtype=torch.float32, device=device)
    num_bboxes = len(bboxes)

    if feather > 0:
        return _bbox_to_mask_cpu(bboxes, mask_shape, dilation, feather)

    chunk_h = max(1, min(H, chunk_size))
    num_chunks = max(1, (H + chunk_h - 1) // chunk_h)
    total_work = num_chunks * max(1, num_bboxes)
    comfy_pbar, tqdm_pbar = _create_progress_bars(total_work, "BBox→Mask (GPU)")

    def update(n=1):
        if comfy_pbar:
            comfy_pbar.update(n)
        if tqdm_pbar:
            tqdm_pbar.update(n)

    try:
        results = []

        x_coords = torch.arange(W, device=device, dtype=torch.float32).view(1, 1, W)
        x1, y1, x2, y2 = bbox_tensor.unbind(-1)
        x1 = x1.view(-1, 1, 1)
        x2 = x2.view(-1, 1, 1)

        if dilation > 0:
            x1 = (x1 - dilation).clamp(min=0)
            x2 = (x2 + dilation).clamp(max=W)

        for ci in range(num_chunks):
            h_start = ci * chunk_h
            h_end = min(h_start + chunk_h, H)
            chunk_height = h_end - h_start

            y_coords = torch.arange(h_start, h_end, device=device, dtype=torch.float32).view(1, chunk_height, 1)

            if dilation > 0:
                y1_chunk = (y1 - dilation).clamp(min=0).view(-1, 1, 1)
                y2_chunk = (y2 + dilation).clamp(max=H).view(-1, 1, 1)
            else:
                y1_chunk = y1.view(-1, 1, 1)
                y2_chunk = y2.view(-1, 1, 1)

            in_bbox = (x_coords >= x1) & (x_coords < x2) & (y_coords >= y1_chunk) & (y_coords < y2_chunk)
            chunk_result, _ = in_bbox.max(dim=0)
            results.append(chunk_result.cpu().to(dtype=torch.float32))

            del y_coords, in_bbox, chunk_result
            if dilation > 0:
                del y1_chunk, y2_chunk

            update(num_bboxes)
            torch.cuda.empty_cache()

        final = torch.cat(results, dim=0)
        del results, bbox_tensor, x_coords
        torch.cuda.empty_cache()
        gc.collect()
        return final

    finally:
        if tqdm_pbar:
            tqdm_pbar.close()


def _bbox_to_mask_cpu(
    bboxes: List[List[int]],
    mask_shape: Tuple[int, int],
    dilation: int,
    feather: int,
) -> torch.Tensor:
    H, W = mask_shape

    if feather > 0 and HAS_SCIPY:
        from scipy.ndimage import gaussian_filter

    combined = np.zeros(mask_shape, dtype=np.float32)

    for bbox in bboxes:
        x1, y1, x2, y2 = map(int, bbox)

        x1 = max(0, x1 - dilation)
        y1 = max(0, y1 - dilation)
        x2 = min(W, x2 + dilation)
        y2 = min(H, y2 + dilation)

        if x1 >= x2 or y1 >= y2:
            continue

        if feather > 0 and HAS_SCIPY:
            mask_single = np.zeros(mask_shape, dtype=np.float32)
            mask_single[y1:y2, x1:x2] = 1.0
            mask_single = gaussian_filter(mask_single, sigma=feather)
            combined = np.maximum(combined, mask_single)
        else:
            combined[y1:y2, x1:x2] = 1.0

    return torch.from_numpy(combined)