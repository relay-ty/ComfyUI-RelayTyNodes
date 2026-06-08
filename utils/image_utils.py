"""
图像工具函数模块

此模块包含图像处理相关的工具函数。

核心功能：
- resize_images_batch: 批量缩放图像张量到目标尺寸，支持自动格式检测和多种插值模式
"""

import logging
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ── 调用者 ──
#   image_nodes.py → RT_PoissonBlend（Poisson 融合前的图像尺寸对齐）
# ⚠️ 修改插值逻辑或签名会影响图像融合结果！
def resize_images_batch(
    images: torch.Tensor,
    target_h: int,
    target_w: int,
    mode: str = "bilinear",
    align_corners: bool = False,
    antialias: bool = False,
    data_format: str = "auto",
) -> torch.Tensor:
    """
    批量缩放图像张量到目标尺寸

    支持 BHWC 和 BCHW 两种内存格式的自动检测与转换。当输入尺寸已匹配目标时，
    直接返回原张量以节省计算。

    参数：
        images: 输入图像张量，形状为 [B, H, W, C] 或 [B, C, H, W]
        target_h: 目标高度，必须为正整数
        target_w: 目标宽度，必须为正整数
        mode: 插值算法，可选 "bilinear" / "nearest" / "bicubic" / "area"，默认 "bilinear"
        align_corners: 是否对齐角点，仅对 bilinear/bicubic 有效，默认 False
        antialias: 是否启用抗锯齿，仅对 bilinear/bicubic 且缩小操作时生效，默认 False
        data_format: 输入格式，"auto" 自动检测 / "BHWC" / "BCHW"，默认 "auto"

    返回值：
        缩放后的图像张量，形状与输入格式一致

    异常：
        TypeError: images 不是 torch.Tensor
        ValueError: images 维度不为 4，或 target_h/target_w 非正整数
    """
    _validate_input(images, target_h, target_w)

    if data_format == "auto":
        data_format = _detect_format(images)

    if data_format == "BHWC":
        if images.shape[1:3] == (target_h, target_w):
            return images
        B, H, W, C = images.shape
        images_bchw = images.permute(0, 3, 1, 2)
    elif data_format == "BCHW":
        if images.shape[2:4] == (target_h, target_w):
            return images
        B, C, H, W = images.shape
        images_bchw = images
    else:
        raise ValueError(f"不支持的数据格式: '{data_format}'，可选 'auto' / 'BHWC' / 'BCHW'")

    kwargs = _build_interpolate_kwargs(mode, align_corners, antialias, target_h, target_w, images_bchw)

    resized_bchw = F.interpolate(images_bchw, size=(target_h, target_w), **kwargs)

    if data_format == "BHWC":
        return resized_bchw.permute(0, 2, 3, 1)
    return resized_bchw


# ── 调用者 ──
#   mask_utils.py → extract_channel("hue"/"saturation"/"value")
#     → mask_nodes.py → RT_ImageToMask（间接）
# ⚠️ 修改 HSV 转换公式会影响遮罩提取的色相/饱和度/明度通道！
def rgb_to_hsv(image: torch.Tensor) -> torch.Tensor:
    """
    将 RGB 图像转换为 HSV 色彩空间（纯 PyTorch 实现，GPU 友好）

    参数：
        image: (..., 3) RGB 图像张量，值域 [0, 1]

    返回值：
        (..., 3) HSV 张量，H∈[0,1], S∈[0,1], V∈[0,1]
    """
    r, g, b = image[..., 0], image[..., 1], image[..., 2]
    max_val, _ = torch.max(image, dim=-1)
    min_val, _ = torch.min(image, dim=-1)
    delta = max_val - min_val
    eps = 1e-8

    h = torch.zeros_like(max_val)
    mask = delta > eps

    r_max = (max_val == r) & mask
    h[r_max] = ((g[r_max] - b[r_max]) / (delta[r_max] + eps)) % 6

    g_max = (max_val == g) & mask
    h[g_max] = (b[g_max] - r[g_max]) / (delta[g_max] + eps) + 2

    b_max = (max_val == b) & mask
    h[b_max] = (r[b_max] - g[b_max]) / (delta[b_max] + eps) + 4

    h = h / 6.0

    s = torch.zeros_like(max_val)
    s[mask] = delta[mask] / (max_val[mask] + eps)

    return torch.stack([h, s, max_val], dim=-1)


def _validate_input(images: torch.Tensor, target_h: int, target_w: int) -> None:
    if not isinstance(images, torch.Tensor):
        raise TypeError(f"images 必须是 torch.Tensor，实际类型: {type(images).__name__}")

    if images.dim() != 4:
        raise ValueError(f"images 必须是 4 维张量 [B, H, W, C] 或 [B, C, H, W]，实际维度: {images.dim()}")

    if not (isinstance(target_h, int) and target_h > 0):
        raise ValueError(f"target_h 必须为正整数，实际值: {target_h}")
    if not (isinstance(target_w, int) and target_w > 0):
        raise ValueError(f"target_w 必须为正整数，实际值: {target_w}")

    if torch.isnan(images).any():
        logger.warning("输入张量包含 NaN 值，可能导致缩放结果异常")


def _detect_format(images: torch.Tensor) -> str:
    """
    自动检测图像张量的内存格式

    启发式规则：
    - 如果 dim=1 的大小为 1、3 或 4，判定为 BCHW（通道优先）
    - 如果 dim=3 的大小为 1、3 或 4，判定为 BHWC（通道在后）
    - 无法判断时默认按 BHWC 处理

    参数：
        images: 4 维张量 [B, H, W, C] 或 [B, C, H, W]

    返回值：
        "BHWC" 或 "BCHW"
    """
    dim_channel_candidates = {1, 3, 4}

    dim1_is_channel = images.shape[1] in dim_channel_candidates
    dim3_is_channel = images.shape[3] in dim_channel_candidates

    if dim1_is_channel and not dim3_is_channel:
        return "BCHW"
    if dim3_is_channel and not dim1_is_channel:
        return "BHWC"

    if dim1_is_channel and dim3_is_channel:
        logger.debug(
            f"张量形状 {list(images.shape)} 的 dim[1]={images.shape[1]} 和 dim[3]={images.shape[3]} 均可能为通道数，"
            f"默认按 BHWC 处理"
        )
        return "BHWC"

    logger.warning(f"无法自动判断张量 {list(images.shape)} 的格式，默认按 BHWC 处理")
    return "BHWC"


def _build_interpolate_kwargs(
    mode: str,
    align_corners: bool,
    antialias: bool,
    target_h: int,
    target_w: int,
    images_bchw: torch.Tensor,
) -> dict:
    supported_modes = {"bilinear", "nearest", "bicubic", "area"}
    if mode not in supported_modes:
        raise ValueError(f"不支持的插值模式: '{mode}'，可选 {sorted(supported_modes)}")

    kwargs: dict = {"mode": mode}

    if mode in ("bilinear", "bicubic"):
        kwargs["align_corners"] = align_corners

        is_downsampling = target_h < images_bchw.shape[2] or target_w < images_bchw.shape[3]
        if antialias and is_downsampling:
            kwargs["antialias"] = True
    elif antialias:
        logger.debug(f"antialias 参数在 mode='{mode}' 下无效，已忽略")

    return kwargs