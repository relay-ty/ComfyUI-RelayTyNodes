"""
BBox处理节点实现

此模块包含与边界框（Bounding Box）相关的节点。

节点列表：
- RT_BBoxToMask: 将边界框列表转换为遮罩图像，支持GPU分块处理、羽化

依赖：
- utils/bbox_utils.py: bbox_to_mask 提供底层 GPU/CPU 自适应处理
"""

import torch

from ..utils import RelayNodeBase, bbox_to_mask


# region RT_BBoxToMask
# RTBBox转遮罩节点
class RT_BBoxToMask(RelayNodeBase):
    """
    BBox转遮罩节点

    功能：将边界框(BBox)列表转换为Mask图像，支持GPU分块处理，
         可选择是否对mask边界进行羽化处理

    输入：
    - bboxes: BBox列表 [[x1,y1,x2,y2], ...]
    - image: 参考图像（用于获取尺寸）
    - dilation: 边界扩展像素数
    - feather: 羽化（高斯模糊）半径

    输出：
    - mask: 合并后的Mask
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "参考图像（用于获取输出尺寸）"}),
                "bboxes": ("BBOX", {"tooltip": "边界框列表 [[x1,y1,x2,y2], ...]"}),
                "dilation": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 200,
                    "step": 1,
                    "tooltip": "边界扩展像素数"
                }),
                "feather": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "tooltip": "羽化（高斯模糊）半径"
                }),
            },
            "optional": {
                "chunk_size": ("INT", {
                    "default": 8,
                    "min": 1,
                    "max": 4096,
                    "step": 1,
                    "tooltip": "GPU分块大小（按H维度，避免高分辨率OOM）"
                }),
                "device": (["auto", "cpu", "gpu"], {
                    "default": "auto",
                    "tooltip": "处理设备"
                }),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RTBBox转遮罩

## 功能
将边界框列表转换为Mask图像。支持 GPU 分块处理（按 H 维度分块），自动 OOM 回退 CPU，内置进度条。

## 输入
- 边界框: BBox列表，格式为 [[x1,y1,x2,y2], ...]
- 图像: 参考图像（用于获取输出尺寸）

## 输出
- 遮罩: 合并后的Mask

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 扩展像素 | 0 | 边界扩展像素数（0-200） |
| 羽化半径 | 0 | 羽化半径，>0会对Mask边缘进行高斯模糊 |
| 分块大小 | 8 | GPU分块行数（1-4096） |
| 设备 | auto | 处理设备（auto/gpu/cpu） |

## 使用建议
- 羽化功能需要scipy支持，如果未安装将忽略羽化参数。
"""

    def __init__(self):
        super().__init__()

    def process(self, bboxes, image, dilation=0, feather=0, chunk_size=8, device="auto"):
        if not bboxes or len(bboxes) == 0:
            _, height, width, _ = image.shape
            return (torch.zeros((1, height, width), dtype=torch.float32, device=image.device),)

        _, height, width, _ = image.shape

        combined_mask = bbox_to_mask(
            bboxes, (height, width), dilation, feather, device, chunk_size
        )

        return (combined_mask.unsqueeze(0),)
# endregion