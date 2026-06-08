"""
遮罩工具函数模块

此模块包含遮罩处理相关的工具函数。

核心功能：
- resize_masks_batch: 批量缩放掩膜张量到目标尺寸，保留输入 dtype
- draw_mask_outline: 在图像上绘制遮罩轮廓，支持批量和自定义颜色

值域约定：
- 图像值域为 [0, 1]（ComfyUI 标准），轮廓颜色参数也应在 [0, 1] 范围内
"""

import logging
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

_SOBEL_X = torch.tensor(
    [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
    dtype=torch.float32,
).view(1, 1, 3, 3)

_SOBEL_Y = torch.tensor(
    [[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
    dtype=torch.float32,
).view(1, 1, 3, 3)


# ── 调用者 ──
#   (暂无节点直接引用，工具函数，可通过 utils.resize_masks_batch 调用)
def resize_masks_batch(
    masks: torch.Tensor,
    target_h: int,
    target_w: int,
    preserve_dtype: bool = True,
) -> torch.Tensor:
    """
    批量缩放掩膜张量到目标尺寸

    使用最近邻插值对批量掩膜进行缩放，保持边缘锐利。默认保留输入 dtype，
    避免浮点概率遮罩被截断为整数。

    参数：
        masks: 输入掩膜张量，形状为 [B, H, W] 或 [B, 1, H, W]
        target_h: 目标高度，必须为正整数
        target_w: 目标宽度，必须为正整数
        preserve_dtype: 是否保留输入 dtype，默认 True；设为 False 返回 long 类型

    返回值：
        缩放后的掩膜张量，形状为 [B, target_h, target_w]

    异常：
        TypeError: masks 不是 torch.Tensor
        ValueError: masks 维度不为 3 或 4，或 target_h/target_w 非正整数
    """
    _validate_masks_input(masks, target_h, target_w)

    if masks.dim() == 4:
        if masks.shape[1] == 1:
            masks = masks.squeeze(1)
        else:
            raise ValueError(f"4 维掩膜的 dim[1] 必须为 1，实际: {masks.shape[1]}")

    if target_h == 0 and target_w == 0:
        return masks

    B, H, W = masks.shape
    if (H, W) == (target_h, target_w):
        return masks

    input_dtype = masks.dtype
    masks_bchw = masks.unsqueeze(1).float()
    resized_bchw = F.interpolate(masks_bchw, size=(target_h, target_w), mode="nearest")
    result = resized_bchw.squeeze(1)

    if preserve_dtype and not input_dtype.is_floating_point:
        return result.round().to(input_dtype)
    if preserve_dtype:
        return result.to(input_dtype)
    return result.round().long()

# 验证掩膜输入参数
def _validate_masks_input(masks: torch.Tensor, target_h: int, target_w: int) -> None:
    if not isinstance(masks, torch.Tensor):
        raise TypeError(f"masks 必须是 torch.Tensor，实际类型: {type(masks).__name__}")

    if masks.dim() not in (3, 4):
        raise ValueError(f"masks 必须是 3 维 [B, H, W] 或 4 维 [B, 1, H, W]，实际维度: {masks.dim()}")

    if not (isinstance(target_h, int) and target_h >= 0):
        raise ValueError(f"target_h 必须为非负整数，实际值: {target_h}")
    if not (isinstance(target_w, int) and target_w >= 0):
        raise ValueError(f"target_w 必须为非负整数，实际值: {target_w}")

    if torch.isnan(masks.float()).any():
        logger.warning("输入掩膜包含 NaN 值，可能导致缩放结果异常")


# ── 调用者 ──
#   mask_draw_nodes.py → 注释中引用（实际使用 OpenCV 路径，非本函数）
#   (暂无节点直接调用；Sobel 边缘绘制功能，供未来节点使用)
def draw_mask_outline(
    image: torch.Tensor,
    mask: torch.Tensor,
    inner_mask: torch.Tensor | None = None,
    edge_threshold: float = 0.1,
    outline_color: tuple[float, float, float] = (1.0, 0.0, 0.0),
    inner_outline_color: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> torch.Tensor:
    """
    在图像上绘制 mask 的轮廓

    图像值域要求：[0, 1]（ComfyUI 标准）。轮廓颜色参数同样应在 [0, 1] 范围内。
    支持批量输入，逐张绘制轮廓。

    参数：
        image: 输入图像张量，形状为 [H, W, C] 或 [B, H, W, C]
        mask: 遮罩张量，形状为 [H, W] 或 [B, H, W]
        inner_mask: 可选的内遮罩张量，形状为 [H, W] 或 [B, H, W]
        edge_threshold: Sobel 边缘检测阈值，默认 0.1
        outline_color: 外轮廓 RGB 颜色（[0,1] 范围），默认红色 (1, 0, 0)
        inner_outline_color: 内轮廓 RGB 颜色（[0,1] 范围），默认蓝色 (0, 0, 1)

    返回值：
        绘制了遮罩轮廓的图像张量，形状与输入 image 一致

    异常：
        ValueError: mask 与 image 的空间尺寸 (H, W) 不匹配
    """
    device = image.device

    image, was_3d = _ensure_batch_dim(image, min_dim=3)
    mask, _ = _ensure_batch_dim(mask, min_dim=2, target_batch=image.shape[0])
    if inner_mask is not None:
        inner_mask, _ = _ensure_batch_dim(inner_mask, min_dim=2, target_batch=image.shape[0])

    B, H_img, W_img = image.shape[0], image.shape[1], image.shape[2]
    H_mask, W_mask = mask.shape[1], mask.shape[2]
    if (H_mask, W_mask) != (H_img, W_img):
        raise ValueError(
            f"mask 空间尺寸 ({H_mask}, {W_mask}) 与 image ({H_img}, {W_img}) 不匹配"
        )
    if inner_mask is not None:
        H_inner, W_inner = inner_mask.shape[1], inner_mask.shape[2]
        if (H_inner, W_inner) != (H_img, W_img):
            raise ValueError(
                f"inner_mask 空间尺寸 ({H_inner}, {W_inner}) 与 image ({H_img}, {W_img}) 不匹配"
            )

    if image.shape[-1] == 4:
        result = image[..., :3].clone()
    else:
        result = image.clone()

    sobel_x = _SOBEL_X.to(device)
    sobel_y = _SOBEL_Y.to(device)

    mask_bin = (mask > 0.5).float().unsqueeze(1)

    grad_x = F.conv2d(mask_bin, sobel_x, padding=1)
    grad_y = F.conv2d(mask_bin, sobel_y, padding=1)
    edge_mag = torch.sqrt(grad_x ** 2 + grad_y ** 2).squeeze(1)

    for b in range(B):
        edges = edge_mag[b] > edge_threshold
        if edges.any():
            result[b, edges, 0] = outline_color[0]
            result[b, edges, 1] = outline_color[1]
            result[b, edges, 2] = outline_color[2]

    if inner_mask is not None:
        inner_mask_bin = (inner_mask > 0.5).float().unsqueeze(1)

        grad_x_inner = F.conv2d(inner_mask_bin, sobel_x, padding=1)
        grad_y_inner = F.conv2d(inner_mask_bin, sobel_y, padding=1)
        edge_mag_inner = torch.sqrt(grad_x_inner ** 2 + grad_y_inner ** 2).squeeze(1)

        for b in range(B):
            edges_inner = edge_mag_inner[b] > edge_threshold
            if edges_inner.any():
                result[b, edges_inner, 0] = inner_outline_color[0]
                result[b, edges_inner, 1] = inner_outline_color[1]
                result[b, edges_inner, 2] = inner_outline_color[2]

    if was_3d:
        result = result.squeeze(0)
    return result

# 确保张量有 batch 维度
def _ensure_batch_dim(
    tensor: torch.Tensor,
    min_dim: int,
    target_batch: int | None = None,
) -> tuple[torch.Tensor, bool]:
    """
    确保张量有 batch 维度，返回 (调整后的张量, 是否进行了升维)。

    参数：
        tensor: 输入张量
        min_dim: 最小期望维度（不含 batch），如 image=3 表示期望 [H,W,C]
        target_batch: 目标 batch 大小，用于广播单张到 batch

    返回值：
        (调整后的张量, 是否进行了 unsqueeze(0))
    """
    expected_dims = min_dim + 1
    if tensor.dim() == min_dim:
        tensor = tensor.unsqueeze(0)
        was_expanded = True
    elif tensor.dim() == expected_dims:
        was_expanded = False
    else:
        raise ValueError(
            f"张量维度必须为 {min_dim} 或 {expected_dims}，实际: {tensor.dim()}"
        )

    if target_batch is not None and tensor.shape[0] == 1 and target_batch > 1:
        tensor = tensor.expand(target_batch, *tensor.shape[1:])

    return tensor, was_expanded


# ── 调用者 ──
#   nodes_debug.py → RT_MaskExpand
# ⚠️ 修改膨胀/腐蚀算法会影响遮罩扩展/收缩功能！
def expand_mask(mask: torch.Tensor, expand: int, tapered_corners: bool = True) -> torch.Tensor:
    """
    形态学膨胀/腐蚀（GPU 统一实现）

    tapered_corners=True：十字形核 [[0,1,0],[1,1,1],[0,1,0]]，圆角效果
        GPU 实现为 max(水平 1×K max_pool, 垂直 K×1 max_pool)
    tapered_corners=False：方形核 K×K max_pool，直角效果

    参数：
        mask:            [B, H, W] 浮点遮罩，值域 [0, 1]
        expand:          正值膨胀，负值腐蚀
        tapered_corners: 是否使用渐变角落（True=圆角，False=直角）

    返回值：
        [B, H, W] 处理后的遮罩
    """
    if expand == 0:
        return mask.clone()

    abs_expand = abs(expand)
    # 大半径：一次性使用大核
    if abs_expand >= 5:
        K = 2 * abs_expand + 1
        return _morphology_once(mask, K, expand, tapered_corners)
    # 小半径：迭代 3x3 核
    result = mask.clone()
    for _ in range(abs_expand):
        result = _morphology_once(result, 3, expand, tapered_corners)
    return result


# 单次形态学操作（膨胀/腐蚀，支持方形和十字形核）
def _morphology_once(mask: torch.Tensor, kernel_size: int, direction: int, tapered_corners: bool):
    """
    单次形态学操作（膨胀或腐蚀）
    Args:
        mask: [B, H, W]
        kernel_size: 池化核大小（奇数）
        direction: 正=膨胀，负=腐蚀
        tapered_corners: 是否使用十字形核
    """
    if direction > 0:
        return _dilate(mask, kernel_size, tapered_corners).clamp(0, 1)
    else:
        # 腐蚀 = 1 - 膨胀(1 - mask)
        inverted = 1 - mask
        eroded = _dilate(inverted, kernel_size, tapered_corners)
        return (1 - eroded).clamp(0, 1)


# 膨胀操作（取局部最大值）
def _dilate(mask: torch.Tensor, kernel_size: int, tapered_corners: bool):
    """
    膨胀核心：取局部最大值
    Args:
        mask: [B, H, W]
        kernel_size: 奇数
        tapered_corners: True=十字形，False=方形
    """
    x = mask.unsqueeze(1)  # [B, 1, H, W]
    pad = kernel_size // 2

    if tapered_corners:
        # 水平方向最大池化
        h = F.max_pool2d(x, (1, kernel_size), stride=1, padding=(0, pad))
        # 垂直方向最大池化
        v = F.max_pool2d(x, (kernel_size, 1), stride=1, padding=(pad, 0))
        # 逐元素取最大值，再移除通道维度
        return torch.max(h, v).squeeze(1)
    else:
        # 方形最大池化
        return F.max_pool2d(x, kernel_size, stride=1, padding=pad).squeeze(1)

# ── 调用者 ──
#   nodes_debug.py → RT_MaskFeather
# ⚠️ 修改高斯模糊逻辑会影响遮罩羽化效果！调用创建独立 T.GaussianBlur 实例（CPU 多线程安全）
def gaussian_blur_mask(
    mask: torch.Tensor, kernel_size: int, sigma: float
) -> torch.Tensor:
    """
    单张/批量 mask 高斯模糊

    每个调用创建独立的 torchvision T.GaussianBlur 实例，
    确保 CPU 多线程安全。

    参数：
        mask:        [B, H, W] 浮点遮罩
        kernel_size: 高斯核大小（奇数；偶数自动 +1）
        sigma:       高斯 sigma 值

    返回值：
        模糊后的 [B, H, W] 遮罩
    """
    import torchvision.transforms as T
    transform = T.GaussianBlur(
        kernel_size=(kernel_size, kernel_size), sigma=(sigma, sigma)
    )
    return transform(mask.unsqueeze(1)).squeeze(1)


# ── 调用者 ──
#   mask_nodes.py → RT_ImageToMask
# ⚠️ 修改通道提取逻辑会影响遮罩提取质量！依赖 rgb_to_hsv (image_utils.py)
def extract_channel(image: torch.Tensor, channel: str) -> torch.Tensor:
    """
    从 4D RGB 图像张量中提取指定通道

    支持通道：
    - "luminance":  亮度 0.299R + 0.587G + 0.114B
    - "red" / "green" / "blue": RGB 单通道
    - "alpha":      透明度通道（image[..., 3]）
    - "hue" / "saturation" / "value": HSV 通道

    参数：
        image:   [B, H, W, C] RGB 张量，值域 [0, 1]
        channel: 通道名，不区分大小写

    返回值：
        [B, H, W] 单通道张量，值域 [0, 1]
    """
    from .image_utils import rgb_to_hsv

    if channel == "luminance":
        return 0.299 * image[..., 0] + 0.587 * image[..., 1] + 0.114 * image[..., 2]
    elif channel == "red":
        return image[..., 0]
    elif channel == "green":
        return image[..., 1]
    elif channel == "blue":
        return image[..., 2]
    elif channel == "alpha":
        if image.shape[-1] >= 4:
            return image[..., 3]
        return torch.ones(
            image.shape[0], image.shape[1], image.shape[2],
            dtype=image.dtype, device=image.device,
        )
    elif channel in ("hue", "saturation", "value"):
        hsv = rgb_to_hsv(image)
        idx = {"hue": 0, "saturation": 1, "value": 2}[channel]
        return hsv[..., idx]
    return image[..., 0]


# ── 调用者 ──
#   mask_nodes.py → RT_ImageToMask
# ⚠️ 修改色阶公式会影响遮罩提取的对比度/亮度！处理顺序: clamp → Levels → Gamma → 反转
def apply_levels(
    channel_data: torch.Tensor,
    black_point: float,
    white_point: float,
    gamma: float,
    invert: bool,
) -> torch.Tensor:
    """
    色阶（Levels）调整管线

    处理顺序：clamp → Levels 缩放 → Gamma 校正 → 反转

    参数：
        channel_data: [B, H, W] 单通道数据，值域 [0, 1]
        black_point:  黑点阈值
        white_point:  白点阈值
        gamma:        Gamma 值（=1 时无变化）
        invert:       是否反转

    返回值：
        [B, H, W] 调整后的单通道数据
    """
    channel_data = channel_data.clamp(0.0, 1.0)

    if abs(black_point) > 1e-6 or abs(white_point - 1.0) > 1e-6:
        scale = 1.0 / max(white_point - black_point, 1e-8)
        channel_data = (channel_data - black_point) * scale
        channel_data = channel_data.clamp(0.0, 1.0)

    if abs(gamma - 1.0) > 1e-6:
        channel_data = torch.pow(channel_data, 1.0 / max(gamma, 1e-6))
        channel_data = channel_data.clamp(0.0, 1.0)

    if invert:
        channel_data = 1.0 - channel_data

    return channel_data


# ── 调用者 ──
#   (模块内部辅助函数，暂无节点直接引用；供上层 mask 函数内部校验使用)
def _validate_mask_input(mask: torch.Tensor, func_name: str) -> bool:
    """
    验证 mask 输入合法性

    参数：
        mask:      待校验的 mask 张量
        func_name: 调用方函数名

    返回值：
        True 有效，False 无效
    """
    if mask is None:
        return False
    if not isinstance(mask, torch.Tensor):
        logger.error(f"[{func_name}] 错误：mask 必须是 torch.Tensor，当前: {type(mask)}")
        return False
    if mask.numel() == 0:
        logger.error(f"[{func_name}] 错误：mask 不能是空张量")
        return False
    if len(mask.shape) != 3:
        logger.error(f"[{func_name}] 错误：mask 必须为 3D [B,H,W]，当前: {mask.shape}")
        return False
    if not torch.is_floating_point(mask):
        logger.warning(f"[{func_name}] 警告：mask 建议使用浮点型，当前: {mask.dtype}")
    return True


__all__ = [
    "resize_masks_batch",
    "draw_mask_outline",
    "expand_mask",
    "gaussian_blur_mask",
    "extract_channel",
    "apply_levels",
    "_validate_mask_input",
]