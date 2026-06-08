"""
工具函数模块

此模块包含 ComfyUI-RelayTyNodes 使用的工具函数和基础类。

功能列表：
- RelayNodeBase: 所有自定义节点的基类
- AnyType: 通配符类型，用于动态输入端口
- adaptive_process: GPU/CPU自适应处理入口（GPU分块 + OOM回退 + 进度条）
- resize_images_batch: 批量缩放图像张量
- resize_masks_batch: 批量缩放掩膜张量
- draw_mask_outline: 在图像上绘制遮罩轮廓
- expand_mask / gaussian_blur_mask: 遮罩形态学操作
- extract_channel / apply_levels: 图像通道提取与色阶调整
- bbox_to_mask: BBox列表转遮罩
- get_memory_info: GPU显存诊断
- get_input_type: 获取输入值的类型名称
- safe_sqrt, safe_log, safe_log10, safe_div, safe_floordiv, safe_mod: 安全的数学工具函数

使用示例：
    from utils import RelayNodeBase, AnyType, any

    class MyNode(RelayNodeBase):
        pass
"""

from .base import RelayNodeBase
from .common import AnyType, any, get_input_type, parse_color_str
from .device_utils import select_device
from .image_utils import resize_images_batch, rgb_to_hsv
from .mask_utils import (
    resize_masks_batch,
    draw_mask_outline,
    expand_mask,
    gaussian_blur_mask,
    extract_channel,
    apply_levels,
)
from .math_utils import safe_sqrt, safe_log, safe_log10, safe_div, safe_floordiv, safe_mod
from .gpu_utils import adaptive_process
from .bbox_utils import bbox_to_mask
from .diagnostics import get_memory_info

__all__ = [
    "RelayNodeBase",
    "AnyType",
    "any",
    "get_input_type",
    "parse_color_str",
    "resize_images_batch",
    "rgb_to_hsv",
    "resize_masks_batch",
    "draw_mask_outline",
    "expand_mask",
    "gaussian_blur_mask",
    "extract_channel",
    "apply_levels",
    "select_device",
    "adaptive_process",
    "bbox_to_mask",
    "get_memory_info",
    "safe_sqrt",
    "safe_log",
    "safe_log10",
    "safe_div",
    "safe_floordiv",
    "safe_mod",
]
