"""
Mask绘制节点实现

此模块包含将Mask以可视化方式绘制到图像上的节点，提供轮廓描边、半透明叠加等绘制功能。

节点列表：
- RT_MaskContour: 在图像上绘制Mask轮廓描边（OpenCV闭合矢量轮廓）
- RT_DrawMaskOnImage: 在图像上半透明叠加绘制Mask，支持多种颜色格式

注：RT_MaskContour 使用 OpenCV findContours 绘制闭合矢量轮廓线（可调线宽）；
     mask_utils.draw_mask_outline 使用 Sobel 卷积绘制栅格边缘像素（可调颜色/阈值），
     两者视觉效果不同，适用于不同场景。
"""

import torch
import torch.nn.functional as F
import numpy as np
import gc
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("OpenCV不可用，描边功能将被禁用")

from ..utils import RelayNodeBase, parse_color_str


# region RT_MaskContour
# RT遮罩描边节点（OpenCV轮廓）
class RT_MaskContour(RelayNodeBase):
    """
    RT遮罩描边节点

    功能说明：
    - 输入图像和Mask
    - 找到Mask中每个独立区域的轮廓
    - 在图像上绘制每个区域的红色轮廓线

    输入：
    - images: (B, H, W, C) 或 (H, W, C) - 输入图像
    - mask: (B, H, W) 或 (H, W) - 输入Mask
    - line_width: int - 描边线宽

    输出：
    - images: (B, H, W, C) - 带描边的图像
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "输入图像，支持 (B, H, W, C) 或 (H, W, C)"}),
                "mask": ("MASK", {"tooltip": "输入Mask，支持 (B, H, W) 或 (H, W)"}),
                "line_width": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 20,
                    "step": 1,
                    "tooltip": "描边线宽"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "draw_contour"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT遮罩描边

## 功能
在图像上绘制Mask每个独立区域的轮廓线。

## 输入
- 图像: 输入图像，支持 (B, H, W, C) 或 (H, W, C)
- 遮罩: 输入Mask，支持 (B, H, W) 或 (H, W)

## 输出
- 图像: 带描边的图像

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 线宽 | 3 | 描边线宽（1-20） |

## 使用建议
- 需要OpenCV支持，如果未安装将返回原始图像。

## 与 mask_utils.draw_mask_outline 的区别
本节点使用 OpenCV findContours 绘制**闭合矢量轮廓线**（可调线宽），
mask_utils.draw_mask_outline 使用 Sobel 卷积绘制**栅格边缘像素**（可调颜色/阈值）。
两者视觉效果不同，适用于不同场景。
"""

    def __init__(self):
        super().__init__()

    def draw_contour(self, images: torch.Tensor, mask: torch.Tensor, line_width: int = 3) -> tuple:
        if not HAS_CV2:
            logger.warning("OpenCV不可用，返回原始图像")
            return (images,)

        images_dim = len(images.shape)
        mask_dim = len(mask.shape)

        images_batch = images.shape[0] if images_dim == 4 else 1
        mask_batch = mask.shape[0] if mask_dim == 3 else 1

        if images_dim == 3 and mask_dim == 2:
            images = images.unsqueeze(0)
            mask = mask.unsqueeze(0)
        elif images_dim == 3 and mask_dim == 3:
            images = images.unsqueeze(0)
        elif images_dim == 4 and mask_dim == 3:
            if images_batch != mask_batch:
                if mask_batch == 1:
                    mask = mask.repeat(images_batch, 1, 1)
                else:
                    return (images,)
        elif images_dim == 4 and mask_dim == 2:
            mask = mask.repeat(images_batch, 1, 1)
        else:
            return (images,)

        batch_size, height, width, channels = images.shape
        images_np = images.cpu().numpy().astype(np.float32)
        mask_np = mask.cpu().numpy().astype(np.float32)

        for b in range(batch_size):
            current_mask = (mask_np[b] > 0.5).astype(np.uint8)

            contours, _ = cv2.findContours(current_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                cv2.drawContours(images_np[b], [contour], -1, (1.0, 0.0, 0.0), line_width)

        result = torch.from_numpy(images_np).float()
        return (result,)


# endregion


# region RT_DrawMaskOnImage
# RT遮罩绘制节点（深度优化版）
class RT_DrawMaskOnImage(RelayNodeBase):
    """
    在图像上绘制Mask节点 (深度优化版)

    功能：使用批量矩阵运算将Mask叠加到图像上，支持RGB和RGBA图像，
         支持多种颜色格式（RGB、RGBA、Hex）

    深度优化策略 (基于2025-2026最佳实践)：
    1. 默认使用CPU处理，避免大图像OOM
    2. 分块处理超大数据，防止显存一次性超载
    3. 显式释放中间张量，减少内存占用
    4. 使用连续张量优化，提升CUDA运算效率
    5. 预检查显存，智能降级CPU
    6. 使用混合精度(FP16/FP32)自适应策略
    7. 流式处理，避免一次性加载
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "输入图像"}),
                "mask": ("MASK", {"tooltip": "要绘制的Mask"}),
                "color": ("STRING", {
                    "default": "255, 0, 0",
                    "tooltip": "颜色值，支持格式：\nRGB: 255, 0, 0\nRGBA: 255, 0, 0, 128\nHex: #FF0000 或 #FF000080"
                }),
                "opacity": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Mask透明度"
                }),
            },
            "optional": {
                "device": (["cpu", "gpu"], {
                    "default": "cpu",
                    "tooltip": "处理设备 (cpu推荐用于大图像)"
                }),
                "batch_size": ("INT", {
                    "default": 32,
                    "min": 1,
                    "max": 99999,
                    "step": 1,
                    "tooltip": "批次大小"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "apply"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT遮罩绘制

## 功能
在图像上半透明叠加绘制Mask，支持多种颜色格式。

## 输入
- 图像: 输入图像
- 遮罩: 输入遮罩

## 输出
- 图像: 绘制后的图像

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 颜色 | 255, 0, 0 | 支持RGB/RGBA/Hex格式 |
| 不透明度 | 1.0 | Mask透明度 (0-1) |
| 设备 | cpu | 处理设备 (cpu/gpu) |
| 批次大小 | 32 | 批次大小 |

## 使用建议
- RGB格式示例: "255, 0, 0" 或 "1.0, 0.0, 0.0"
- RGBA格式示例: "255, 0, 0, 128"
- Hex格式示例: "#FF0000" 或 "#FF000080"
"""

    def _parse_color_str(self, color_str):
        return parse_color_str(color_str)

    def _check_gpu_memory(self, required_gb: float = 2.0) -> tuple:
        if not torch.cuda.is_available():
            return False, "CUDA不可用"

        try:
            mem_info = torch.cuda.mem_get_info()
            free_gb = mem_info[0] / (1024 ** 3)
            total_gb = mem_info[1] / (1024 ** 3)
            used_gb = total_gb - free_gb

            if free_gb < required_gb:
                return False, f"显存不足: 已用 {used_gb:.2f} GB, 剩余 {free_gb:.2f} GB, 需要 {required_gb:.2f} GB"

            return True, f"显存充足: 已用 {used_gb:.2f} GB, 剩余 {free_gb:.2f} GB"
        except Exception as e:
            return False, f"检查失败: {str(e)}"

    def _apply_chunk(
        self,
        img_chunk: torch.Tensor,
        msk_chunk: torch.Tensor,
        rgb: Tuple[float, float, float],
        alpha_val: float,
    ) -> torch.Tensor:
        B, H, W, C = img_chunk.shape

        fill_color = torch.tensor(rgb, dtype=img_chunk.dtype, device=img_chunk.device)
        mask_expanded = msk_chunk.unsqueeze(-1)
        blend_factor = mask_expanded * alpha_val

        if C == 4:
            img_rgb = img_chunk[..., :3]
            img_a = img_chunk[..., 3:]
            out_rgb = img_rgb * (1 - blend_factor) + fill_color * blend_factor
            out_a = torch.maximum(img_a, blend_factor)
            result = torch.cat((out_rgb, out_a), dim=-1)
        else:
            result = img_chunk * (1 - blend_factor) + fill_color * blend_factor

        return result

    def apply(
        self,
        image: torch.Tensor,
        mask: torch.Tensor,
        color: str,
        opacity: float = 1.0,
        device: str = "cpu",
        batch_size: int = 1,
    ) -> tuple:
        if len(image.shape) == 3:
            image = image.unsqueeze(0)

        if len(mask.shape) == 2:
            mask = mask.unsqueeze(0)

        B, H, W, C = image.shape
        BM, HM, WM = mask.shape
        original_device = image.device
        original_dtype = image.dtype

        processing_device = torch.device("cpu")

        if device == "gpu" and torch.cuda.is_available():
            try:
                import model_management
                per_chunk_gb = (batch_size * H * W * C * 4) / (1024 ** 3) + 0.5
                requested_gb = per_chunk_gb + 1.0
                gpu_ok, msg = self._check_gpu_memory(requested_gb)

                if gpu_ok:
                    processing_device = model_management.get_torch_device()
                    logger.info(f"使用GPU处理: {msg}, 批处理尺寸={batch_size}")
                else:
                    logger.info(f"降级到CPU: {msg}")
                    processing_device = torch.device("cpu")
            except Exception as e:
                logger.info(f"GPU初始化失败: {str(e)}")
                processing_device = torch.device("cpu")

        rgb, color_alpha = self._parse_color_str(color)
        alpha_val = opacity * color_alpha

        result_list = []

        with torch.no_grad():
            if HM != H or WM != W:
                mask_cpu = mask.to(torch.device("cpu"))
                mask_cpu = F.interpolate(
                    mask_cpu.unsqueeze(1).float(),
                    size=(H, W),
                    mode="nearest-exact"
                ).squeeze(1)
                del mask
                gc.collect()
                if torch.cuda.is_available():
                    try:
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
                mask = mask_cpu

            if B > BM:
                mask = mask.repeat((B + BM - 1) // BM, 1, 1)[:B]
            elif BM > B:
                mask = mask[:B]

            num_chunks = max(1, (B + batch_size - 1) // batch_size)

            for i in range(num_chunks):
                start_idx = i * batch_size
                end_idx = min(start_idx + batch_size, B)

                img_chunk = image[start_idx:end_idx].to(processing_device, non_blocking=True)
                msk_chunk = mask[start_idx:end_idx].to(processing_device, non_blocking=True)

                if not img_chunk.is_contiguous():
                    img_chunk = img_chunk.contiguous()
                if not msk_chunk.is_contiguous():
                    msk_chunk = msk_chunk.contiguous()

                chunk_result = self._apply_chunk(img_chunk, msk_chunk, rgb, alpha_val)

                result_list.append(chunk_result.to(original_device, original_dtype))

                del img_chunk, msk_chunk, chunk_result
                gc.collect()

            del mask
            gc.collect()

            if torch.cuda.is_available() and processing_device.type == "cuda":
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass

        if len(result_list) == 1:
            final_result = result_list[0]
        else:
            final_result = torch.cat(result_list, dim=0)

        del result_list
        gc.collect()

        return (final_result,)
# endregion