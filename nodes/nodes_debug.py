"""
显存优化与调试节点模块

此模块包含用于优化显存使用和处理大图像的节点。

节点列表：
- RT_MaskScale → 已迁移到 mask_nodes.py
- RT_SafeDownscale: 显存优化缩放节点，在高显存操作前缩小图像
- RT_SafeUpscale: 显存优化放大节点，处理完成后恢复原始尺寸
"""

import logging
import torch
import torch.nn.functional as F
from typing import Tuple

from ..utils import RelayNodeBase

logger = logging.getLogger(__name__)


class RT_SafeDownscale(RelayNodeBase):
    """
    显存优化缩放节点（安全下采样）

    在高显存操作（如 RemoveBackground）前将图像缩小到安全尺寸，
    避免 CUDA OOM 错误。

    适用场景：
        - RemoveBackground 节点处理高分辨率图像时显存不足
        - 任何显存密集型操作前预处理
        - 大批量图像处理前的尺寸控制

    使用建议：
        建议尺寸：1024-2048 像素（根据显存情况调整）
        工作流：LoadImage → RT_SafeDownscale → RemoveBackground → RT_SafeUpscale → 后续节点
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "输入图像"}),
                "max_size": ("INT", {
                    "default": 2048,
                    "min": 256,
                    "max": 4096,
                    "step": 128,
                    "tooltip": "最大尺寸（像素）。图像的最长边将缩放至此值"
                }),
            },
            "optional": {
                "method": (["lanczos", "bilinear", "nearest"], {
                    "default": "lanczos",
                    "tooltip": "缩放算法：lanczos（质量最好）、bilinear（平衡）、nearest（速度最快）"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("image", "orig_width", "orig_height")
    FUNCTION = "execute"
    CATEGORY = "RelayTyNodes/Debug"
    DESCRIPTION = """
# RT安全缩放（显存优化）

## 功能
在高显存操作前将图像缩小到安全尺寸，避免 CUDA OOM 错误。

## 输入
- 图像: 输入图像

## 输出
- 图像: 缩放后的图像
- 原始宽度: 原始图像宽度（用于后续还原）
- 原始高度: 原始图像高度（用于后续还原）

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 最大尺寸 | 2048 | 图像最长边缩放至此值（256-4096） |
| 缩放算法 | lanczos | 缩放算法 |

## 使用建议
- 工作流：LoadImage → RT_SafeDownscale → RemoveBackground → RT_SafeUpscale
- 建议最大尺寸：1024-2048（根据显存情况调整）
- RTX 5070 Ti 16GB 建议使用 2048
"""

    def execute(
        self,
        image: torch.Tensor,
        max_size: int = 2048,
        method: str = "lanczos",
    ) -> Tuple[torch.Tensor, int, int]:
        # image: (B, H, W, C)
        B, H, W, C = image.shape
        orig_w, orig_h = W, H

        max_edge = max(H, W)
        if max_edge > max_size:
            scale = max_size / max_edge
            new_h = int(round(H * scale))
            new_w = int(round(W * scale))

            # 转换格式：BHWC -> BCHW -> 缩放 -> BHWC
            image_bchw = image.permute(0, 3, 1, 2).float() / 255.0 if image.dtype == torch.uint8 else image.permute(0, 3, 1, 2)

            mode_map = {"lanczos": "area", "bilinear": "bilinear", "nearest": "nearest"}
            resized = F.interpolate(image_bchw, size=(new_h, new_w), mode=mode_map.get(method, "area"), align_corners=False if method == "bilinear" else None)

            image = resized.permute(0, 2, 3, 1)

            logger.info(f"RT_SafeDownscale: {orig_w}x{orig_h} -> {new_w}x{new_h}")

        return (image, orig_w, orig_h)


class RT_SafeUpscale(RelayNodeBase):
    """
    显存优化放大节点（安全上采样）

    配合 RT_SafeDownscale 使用，在显存密集型操作完成后，
    将图像恢复到原始尺寸。

    使用建议：
        工作流：LoadImage → RT_SafeDownscale → RemoveBackground → RT_SafeUpscale → 后续节点
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "输入图像（已缩小的图像）"}),
                "orig_width": ("INT", {"default": 1024, "min": 64, "max": 8192, "tooltip": "原始宽度（来自 RT_SafeDownscale）"}),
                "orig_height": ("INT", {"default": 1024, "min": 64, "max": 8192, "tooltip": "原始高度（来自 RT_SafeDownscale）"}),
            },
            "optional": {
                "method": (["lanczos", "bilinear", "nearest"], {
                    "default": "bilinear",
                    "tooltip": "放大算法：lanczos（质量最好）、bilinear（平衡）、nearest（速度最快）"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "execute"
    CATEGORY = "RelayTyNodes/Debug"
    DESCRIPTION = """
# RT安全放大（显存优化）

## 功能
在显存密集型操作完成后，将图像恢复到原始尺寸。

## 输入
- 图像: 输入图像（已缩小的图像）
- 原始宽度: 原始图像宽度（来自 RT_SafeDownscale）
- 原始高度: 原始图像高度（来自 RT_SafeDownscale）

## 输出
- 图像: 恢复到原始尺寸的图像

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 放大算法 | bilinear | 放大算法 |

## 使用建议
- 必须配合 RT_SafeDownscale 使用
- 工作流：LoadImage → RT_SafeDownscale → RemoveBackground → RT_SafeUpscale → 后续节点
"""

    def execute(
        self,
        image: torch.Tensor,
        orig_width: int,
        orig_height: int,
        method: str = "bilinear",
    ) -> Tuple[torch.Tensor]:
        B, H, W, C = image.shape

        if H != orig_height or W != orig_width:
            image_bchw = image.permute(0, 3, 1, 2)
            mode_map = {"lanczos": "area", "bilinear": "bilinear", "nearest": "nearest"}
            resized = F.interpolate(image_bchw, size=(orig_height, orig_width), mode=mode_map.get(method, "bilinear"), align_corners=False if method == "bilinear" else None)
            image = resized.permute(0, 2, 3, 1)
            logger.info(f"RT_SafeUpscale: {W}x{H} -> {orig_width}x{orig_height}")

        return (image,)


class RT_VRAMCheck(RelayNodeBase):
    """
    显存状态检查节点（调试用）

    显示当前 GPU 显存使用情况，帮助诊断 OOM 问题。

    适用场景：
        - 诊断显存不足问题
        - 优化工作流参数
        - 调试大图像处理流程
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trigger": ("*", {}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("vram_info",)
    FUNCTION = "execute"
    CATEGORY = "RelayTyNodes/Debug"
    DESCRIPTION = """
# RT显存检查（调试）

## 功能
显示当前 GPU 显存使用情况，帮助诊断 OOM 问题。

## 输入
- 触发: 任意输入（用于在执行流程中插入检查点）

## 输出
- 显存信息: 当前显存使用情况的文本描述

## 使用建议
- 在 RemoveBackground 等显存密集型节点前后插入
- 用于诊断显存不足问题
"""

    def execute(self, trigger) -> Tuple[str]:
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            free = total - reserved

            info = (
                f"GPU 显存状态:\n"
                f"  已分配: {allocated:.2f} GB\n"
                f"  已预留: {reserved:.2f} GB\n"
                f"  总计: {total:.2f} GB\n"
                f"  可用: {free:.2f} GB"
            )
            logger.info(f"RT_VRAMCheck: {info}")
        else:
            info = "无 GPU（CUDA 不可用）"
            logger.info("RT_VRAMCheck: CPU 模式")

        return (info,)


# endregion
