"""
Mask操作节点实现

此模块包含与遮罩操作相关的节点。

节点列表：
- RT_ImageToMask: 从图像通道提取遮罩（亮度/RGB/Alpha/HSV 通道 + 色阶调整）
- RT_MaskToImage: 将遮罩转换为 RGB 图像
- RT_BatchMask: 将单个Mask复制为指定数量的批次
- RT_GetMaskFromBatch: 从遮罩批次中根据索引获取连续的遮罩子批次
- RT_MaskExpand: 遮罩扩展/收缩（正值外扩、负值内缩，支持圆角/直角）
- RT_MaskFeather: 遮罩高斯羽化（对Mask边缘进行高斯模糊）
- RT_MaskScale: 遮罩缩放（使用最近邻插值保持边缘锐利）
"""

import torch

from ..utils import RelayNodeBase, extract_channel, apply_levels, adaptive_process, gaussian_blur_mask, expand_mask, resize_masks_batch

# region RT_ImageToMask
# RT图像通道转遮罩节点
class RT_ImageToMask(RelayNodeBase):
    """
    图像通道转遮罩节点

    功能：从图像的指定色彩通道（亮度/R/G/B/Alpha/H/S/V）提取为遮罩，
         支持黑点/白点/Gamma色阶调整、反转。

    输入：
    - image: (B, H, W, C) 输入图像，值域 [0, 1]
    - channel: 要提取的通道
    - black_point: 黑点值（0-1），低于此值的像素映射到 0
    - white_point: 白点值（0-1），高于此值的像素映射到 1
    - gamma: Gamma 校正（0.01-9.99）
    - invert: 是否反转输出遮罩
    - batch_size: 批次大小
    - device: 计算设备（auto/gpu/cpu）

    输出：
    - mask: (B, H, W) 提取的遮罩
    """

    CHANNEL_OPTIONS = [
        "luminance",
        "red",
        "green",
        "blue",
        "alpha",
        "hue",
        "saturation",
        "value",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "输入图像 (B, H, W, C)"}),
                "channel": (cls.CHANNEL_OPTIONS, {
                    "default": "red",
                    "tooltip": "要提取为遮罩的色彩通道"
                }),
                "black_point": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "黑点阈值，低于此值的像素映射为黑色"
                }),
                "white_point": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "白点阈值，高于此值的像素映射为白色"
                }),
                "gamma": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.01,
                    "max": 9.99,
                    "step": 0.01,
                    "tooltip": "Gamma 校正值，<1 提亮中间调，>1 压暗中间调"
                }),
                "invert": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "反转输出的遮罩"
                }),
                "batch_size": ("INT", {
                    "default": 8,
                    "min": 1,
                    "max": 4096,
                    "step": 1,
                    "tooltip": "批次大小"
                }),
                "device": (["auto", "cpu", "cuda"], {
                    "default": "auto",
                    "tooltip": "计算设备"
                }),
            },
            "optional": {
                "mask": ("MASK", {
                    "tooltip": "可选：与已有遮罩组合（取交集）"
                }),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "execute"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT图像通道转遮罩

## 功能
从图像中提取指定色彩通道作为遮罩，支持亮度、RGB、Alpha、HSV通道，并提供黑点/白点/Gamma色阶调整。

## 输入
- 图像: 输入图像 (B, H, W, C)
- 遮罩: 可选，与已有遮罩组合（取交集）

## 输出
- 遮罩: 提取的遮罩 (B, H, W)

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 通道 | red | 要提取为遮罩的色彩通道 |
| 黑点 | 0.0 | 黑点阈值，低于此值的像素映射为黑色（0.0-1.0） |
| 白点 | 1.0 | 白点阈值，高于此值的像素映射为白色（0.0-1.0） |
| 伽马 | 1.0 | Gamma校正值，<1 提亮中间调，>1 压暗中间调（0.01-9.99） |
| 反转遮罩 | false | 是否反转输出遮罩 |
| 批次大小 | 8 | 批次大小 |
| 计算设备 | auto | 计算设备 |

## 参数选项说明
| 参数名称 | 对应选项 | 说明 |
|----------|----------|------|
| 通道 | luminance | 亮度通道（0.299R + 0.587G + 0.114B），推荐通用场景 |
| 通道 | red | 红色通道，适合提取暖色/肤色区域 |
| 通道 | green | 绿色通道，适合提取植被/绿幕 |
| 通道 | blue | 蓝色通道，适合提取天空/水面 |
| 通道 | alpha | 透明度通道（RGBA 图像的第4通道），无 alpha 时输出全白 |
| 通道 | hue | 色相（HSV），按色调分离，如提取特定颜色范围 |
| 通道 | saturation | 饱和度（HSV），高值=鲜艳区域，低值=灰暗区域 |
| 通道 | value | 明度（HSV），类似亮度但权重均匀 |

## 使用建议
- 从图像亮度通道创建遮罩：channel=luminance
- 按颜色饱和度分离区域：channel=saturation, black_point=0.3
- 色调筛选特定颜色：channel=hue, black_point=0.05, white_point=0.15（红色范围）

色阶公式：`result = ((channel - black_point) / (white_point - black_point)) ^ (1/gamma)`
"""

    def __init__(self):
        super().__init__()

    # 通道提取 + 色阶调整组合函数（供 adaptive_process 调用）
    @staticmethod
    def _extract_and_levels(chunk, channel, black_point, white_point, gamma, invert):
        result = extract_channel(chunk, channel)
        result = apply_levels(result, black_point, white_point, gamma, invert)
        return result

    def execute(self, image, channel="red", black_point=0.0, white_point=1.0,
                gamma=1.0, invert=False, mask=None, batch_size=8, device="auto"):
        # 判断是否需要色阶调整（黑点/白点/Gamma/反转）
        needs_levels = (
            abs(black_point) > 1e-6
            or abs(white_point - 1.0) > 1e-6
            or abs(gamma - 1.0) > 1e-6
            or invert
        )

        # 快速路径：无需色阶调整且是简单通道
        if not needs_levels and channel in ("red", "green", "blue", "alpha"):
            channel_idx = {"red": 0, "green": 1, "blue": 2, "alpha": 3}[channel]
            # 处理alpha通道缺失的情况
            if channel == "alpha" and image.shape[-1] < 4:
                result = torch.ones(
                    image.shape[0], image.shape[1], image.shape[2],
                    dtype=image.dtype, device=image.device,
                )
            else:
                result = image[..., channel_idx]
        # 快速路径：无需色阶调整的亮度计算
        elif not needs_levels and channel == "luminance":            
            result = (
                0.299 * image[..., 0]
                + 0.587 * image[..., 1]
                + 0.114 * image[..., 2]
            )
        # 通用路径：使用 adaptive_process 进行 GPU/CPU 自适应处理
        else:
            result = adaptive_process(
                image,
                self._extract_and_levels,
                batch_size=batch_size,
                device=device,
                desc=f"提取通道 ({channel})",
                channel=channel,
                black_point=black_point,
                white_point=white_point,
                gamma=gamma,
                invert=invert,
            )

        # 应用可选的遮罩
        if mask is not None:
            # 处理batch维度不匹配
            if mask.shape[0] != result.shape[0]:
                if mask.shape[0] == 1:
                    mask = mask.expand_as(result)
            result = result * mask.to(result.device, dtype=result.dtype)

        return (result,)
# endregion

# region RT_MaskToImage
# RT遮罩转图像节点
class RT_MaskToImage(RelayNodeBase):
    """
    遮罩转图像节点

    功能：将遮罩 (B, H, W) 转换为 RGB 图像 (B, H, W, 3)，
         用于可视化遮罩或将遮罩送入需要图像输入的节点。

    输入：
    - mask: (B, H, W) 输入遮罩
    - color: 输出颜色（white/red/green/blue）
    - invert: 是否反转遮罩

    输出：
    - image: (B, H, W, 3) 图像
    """

    COLOR_OPTIONS = ["white", "red", "green", "blue"]

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "输入遮罩 (B, H, W)"}),
                "color": (cls.COLOR_OPTIONS, {
                    "default": "white",
                    "tooltip": "遮罩的颜色映射"
                }),
                "invert": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "反转遮罩"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "execute"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT遮罩转图像

## 功能
将遮罩转换为 RGB 图像，用于可视化或将遮罩送入图像处理流程。

## 输入
- 遮罩: 输入遮罩 (B, H, W)

## 输出
- 图像: 转换后的 RGB 图像 (B, H, W, 3)

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 颜色 | white | 遮罩的颜色映射 |
| 反转遮罩 | false | 是否反转遮罩 |

## 参数选项说明
| 参数名称 | 对应选项 | RGB值 |
|----------|----------|-------|
| 颜色 | white | (1, 1, 1) |
| 颜色 | red | (1, 0, 0) |
| 颜色 | green | (0, 1, 0) |
| 颜色 | blue | (0, 0, 1) |

## 使用建议
- 遮罩可视化预览
- 将遮罩结果送入后续图像处理节点
"""

    COLOR_MAP = {
        "white": (1.0, 1.0, 1.0),
        "red": (1.0, 0.0, 0.0),
        "green": (0.0, 1.0, 0.0),
        "blue": (0.0, 0.0, 1.0),
    }
    # 缓存颜色张量，按 (color, device, dtype) 缓存
    _color_tensor_cache = {}

    # 获取颜色张量，缓存不存在则创建
    @classmethod
    def _get_color_tensor(cls, color, device, dtype):
        key = (color, device, dtype)
        if key not in cls._color_tensor_cache:
            r, g, b = cls.COLOR_MAP[color]
            cls._color_tensor_cache[key] = torch.tensor(
                [r, g, b], dtype=dtype, device=device
            ).view(1, 1, 1, 3)  # 预先 reshape 为可广播形状
        return cls._color_tensor_cache[key]

    def execute(self, mask, color="white", invert=False):
        # 1. 处理2D输入（无batch维度）
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)

        # 2. 可选：如果确信输入已在 [0,1] 内，可注释下行以提速
        # mask = mask.clamp(0.0, 1.0)

        # 3. 统一处理反转（如果需要）
        if invert:
            mask = 1.0 - mask

        # 4. 扩展为3通道
        if color == "white":
            # 白色：采用官方实现模式（reshape + movedim + expand）
            # 确保维度正确 (B,H,W) -> (B,1,H,W) -> (B,H,W,1) -> (B,H,W,3)
            result = mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])).movedim(1, -1).expand(-1, -1, -1, 3)
        else:
            # 彩色：乘上预缓存的颜色张量（广播乘法，产生新内存）
            color_tensor = self._get_color_tensor(color, mask.device, mask.dtype)
            result = mask.unsqueeze(-1) * color_tensor

        return (result,)
# endregion

# region RT_BatchMask
# RT复制遮罩批次节点
class RT_BatchMask(RelayNodeBase):
    """
    RT复制遮罩批次节点

    功能：将单个Mask复制为指定数量的批次。

    输入：
    - mask: (H, W) 或 (1, H, W) 输入遮罩
    - count: 复制数量

    输出：
    - masks: (count, H, W) 复制后的遮罩批次
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "输入单个Mask (H, W)"}),
                "count": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 99999,
                    "step": 1,
                    "tooltip": "复制数量"
                }),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("masks",)
    FUNCTION = "batch"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT复制遮罩批次

## 功能
将单个Mask复制为指定数量的批次。

## 输入
- 遮罩: 单个Mask，(H, W) 或 (1, H, W)

## 输出
- 遮罩批次: 复制后的批次，(count, H, W)

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 复制数量 | 1 | 要复制的数量 |
"""

    def __init__(self):
        super().__init__()

    def batch(self, mask, count=1):
        # 统一处理为 (1, H, W)
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)
        elif mask.dim() == 3 and mask.shape[0] == 1:
            pass
        else:
            # 更合理的错误处理：返回原输入或抛出异常
            logger.warning(f"RT_BatchMask: 输入形状 {mask.shape} 不符合预期，期望 (H,W) 或 (1,H,W)")
            return (mask,)
        # 复制批次
        return (mask.repeat(count, 1, 1),)

# endregion

# region RT_GetMaskFromBatch
# RT从批次获取遮罩节点
class RT_GetMaskFromBatch(RelayNodeBase):
    """
    RT从批次获取遮罩节点

    功能：从遮罩批次中根据索引获取连续的遮罩子批次。

    输入：
    - masks: (batch, H, W) 输入遮罩批次
    - batch_index: 起始批次索引（从0开始）
    - length: 要获取的遮罩数量

    输出：
    - mask: (length, H, W) 获取的遮罩子批次
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "masks": ("MASK", {"tooltip": "输入遮罩批次 (batch, H, W)"}),
                "batch_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "step": 1,
                    "tooltip": "起始批次索引，从0开始"
                }),
                "length": ("INT", {
                    "default": 1,
                    "min": 1,
                    "step": 1,
                    "tooltip": "要获取的遮罩数量"
                }),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "get_mask_from_batch"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT从批次获取遮罩

## 功能
从遮罩批次中根据索引获取连续的遮罩子批次。

## 输入
- 遮罩批次: 输入遮罩批次 (batch, H, W)

## 输出
- 遮罩: 获取的遮罩子批次 (length, H, W)

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 批次索引 | 0 | 起始批次索引，从0开始 |
| 获取数量 | 1 | 要获取的遮罩数量 |
"""

    def __init__(self):
        super().__init__()

    def get_mask_from_batch(self, masks, batch_index=0, length=1):
        if masks is None:
            return (torch.zeros((1, 1), dtype=torch.float32),)

        if len(masks.shape) == 2:
            # 2D输入，直接返回（无batch维度）
            return (masks,)

        if len(masks.shape) == 3:
            batch_size = masks.shape[0]

            # 限制索引在有效范围内
            batch_index = min(batch_size - 1, max(0, batch_index))
            # 限制长度不超过剩余数据
            length = min(batch_size - batch_index, max(1, length))

            # 获取连续的遮罩子批次
            return (masks[batch_index:batch_index + length],)

        return (torch.zeros((1, 1), dtype=torch.float32),)

# endregion

# region RT_MaskExpand
# RT遮罩扩展/收缩节点（正值外扩、负值内缩）
class RT_MaskExpand(RelayNodeBase):
    """
    遮罩扩展/收缩节点

    功能：调整Mask区域大小，正值向外扩展（膨胀），负值向内收缩（腐蚀）。

    输入：
    - mask: (B, H, W) 输入Mask
    - expand: 扩展像素数（正值外扩，负值内缩，±4096）
    - tapered_corners: 是否使用渐变角落（True=圆角，False=直角）

    输出：
    - mask: 调整后的Mask

    应用场景：
    - 预处理Mask后送入融合节点
    - 消除Mask边缘锯齿
    - 调整修复区域范围
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "输入Mask (B, H, W)"}),
                "expand": ("INT", {
                    "default": 0,
                    "min": -4096,
                    "max": 4096,
                    "step": 1,
                    "tooltip": "扩展像素数：正值外扩（膨胀），负值内缩（腐蚀）"
                }),
                "tapered_corners": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "True=圆角过渡（使用十字形结构元素），False=直角（方形结构元素）"
                }),
            },
            "optional": {
                "batch_size": ("INT", {
                    "default": 8,
                    "min": 1,
                    "max": 4096,
                    "step": 1,
                    "tooltip": "批次大小"
                }),
                "device": (["auto", "cpu", "gpu"], {
                    "default": "auto",
                    "tooltip": "处理设备"
                }),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "expand"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT遮罩扩展/收缩

## 功能
调整Mask区域范围。正值向外扩展（膨胀），负值向内收缩（腐蚀）。

## 输入
- 遮罩: 输入遮罩 (B, H, W)

## 输出
- 遮罩: 处理后的遮罩 (B, H, W)

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 扩展量 | 0 | >0 外扩遮罩边界；<0 内缩遮罩边界（±4096） |
| 渐变角落 | true | True=圆角过渡（十字形结构元素），False=直角（方形结构元素） |
| 批次大小 | 8 | 批次大小 |
| 设备 | auto | 处理设备（auto/gpu/cpu） |

## 使用建议
- 预处理：在融合前调整Mask覆盖范围
- 消除锯齿：轻微膨胀平滑Mask边缘
- 精细控制：与 RT_MaskFeather 配合使用
"""

    def expand(self, mask, expand=0, tapered_corners=True, batch_size=8, device="auto"):
        if expand == 0:
            return (mask.clone(),)

        result = adaptive_process(
            mask,
            expand_mask,
            batch_size=batch_size,
            device=device,
            desc=f"Mask Expand ({'+' if expand > 0 else ''}{expand})",
            steps_per_item=abs(expand),
            expand=expand,
            tapered_corners=tapered_corners,
        )
        return (result,)

# endregion

# region RT_MaskFeather
# RT遮罩高斯羽化节点
class RT_MaskFeather(RelayNodeBase):
    """
    遮罩高斯羽化节点

    功能：对Mask边缘进行高斯模糊，产生柔和的过渡效果。

    输入：
    - mask: (B, H, W) 输入Mask
    - kernel: 高斯核大小（3~100，奇数）
    - sigma: 高斯sigma值（0.1~50）

    输出：
    - mask: 羽化后的Mask

    应用场景：
    - 为融合操作准备羽化遮罩
    - 产生自然的边缘过渡
    - 与 RT_MaskExpand 配合控制边界范围
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "输入Mask (B, H, W)"}),
                "kernel": ("INT", {
                    "default": 30,
                    "min": 3,
                    "max": 100,
                    "step": 1,
                    "tooltip": "高斯核大小（像素，自动取奇数）"
                }),
                "sigma": ("FLOAT", {
                    "default": 20.0,
                    "min": 0.1,
                    "max": 50.0,
                    "step": 0.1,
                    "tooltip": "高斯sigma值（越大越柔和）"
                }),
            },
            "optional": {
                "batch_size": ("INT", {
                    "default": 8,
                    "min": 1,
                    "max": 4096,
                    "step": 1,
                    "tooltip": "批次大小"
                }),
                "device": (["auto", "cpu", "gpu"], {
                    "default": "auto",
                    "tooltip": "处理设备"
                }),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "feather"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT遮罩高斯羽化

## 功能
对Mask边缘进行高斯模糊，产生柔和的羽毛状过渡。

## 输入
- 遮罩: 输入遮罩 (B, H, W)

## 输出
- 遮罩: 羽化后的遮罩 (B, H, W)

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 内核大小 | 15 | 高斯核大小，越大边缘过渡越宽（奇数） |
| 标准差 | 10.0 | 高斯标准差，越大边缘越柔和 |
| 批次大小 | 8 | 批次大小 | 
| 设备 | auto | 处理设备（auto/gpu/cpu） |

## 使用建议
- 羽化范围建议值：10~30
- 羽化强度建议值：5~20
- 先用 RT_MaskExpand 调整Mask范围，再用本节点羽化
"""

    def feather(self, mask, kernel=15, sigma=10.0, batch_size=8, device="auto"):
        if kernel <= 1:
            return (mask.clone(),)
        if kernel % 2 == 0:
            kernel += 1

        result = adaptive_process(
            mask,
            gaussian_blur_mask,
            batch_size=batch_size,
            device=device,
            desc=f"Mask Blur (k={kernel}, sigma={sigma:.1f})",
            steps_per_item=1,
            kernel_size=kernel,
            sigma=sigma,
        )
        return (result,)

# endregion

# region RT_MaskScale
# RT遮罩缩放节点（使用最近邻插值保持边缘锐利）
class RT_MaskScale(RelayNodeBase):
    """
    遮罩缩放节点

    功能：对遮罩进行缩放操作，使用最近邻插值保持边缘锐利。
         支持绝对尺寸和相对比例两种缩放模式。

    遮罩特性适配：
    - 使用最近邻插值（nearest）保持边缘锐利
    - 保留输入 dtype，避免浮点概率遮罩被截断
    - 支持批量处理

    输入：
    - mask: (B, H, W) 输入遮罩，值域 [0, 1]
    - mode: 缩放模式（absolute/scale）
    - width: 目标宽度（absolute模式）
    - height: 目标高度（absolute模式）
    - scale: 缩放比例（scale模式）

    输出：
    - mask: (B, target_h, target_w) 缩放后的遮罩
    """

    CATEGORY = "RelayTyNodes"

    DESCRIPTION = """
# RT遮罩缩放

## 功能
对遮罩进行缩放操作，使用**最近邻插值**保持边缘锐利。支持绝对尺寸和相对比例两种缩放模式。

## 遮罩特性适配
- 使用最近邻插值保持边缘锐利，避免模糊过渡
- 保留输入 dtype，避免浮点概率遮罩被截断
- 支持批量处理

## 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| mask | MASK | 输入遮罩，形状 (B, H, W)，值域 [0, 1] |
| mode | 枚举 | 缩放模式：absolute（绝对尺寸）/ scale（相对比例） |
| width | INT | 目标宽度（absolute模式，1-4096） |
| height | INT | 目标高度（absolute模式，1-4096） |
| scale | FLOAT | 缩放比例（scale模式，0.01-10.0） |

## 输出
| 参数 | 类型 | 说明 |
|------|------|------|
| mask | MASK | 缩放后的遮罩，形状 (B, target_h, target_w) |

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| mode | absolute | 缩放模式：absolute（绝对尺寸）/ scale（相对比例） |
| width | 512 | 目标宽度（absolute模式） |
| height | 512 | 目标高度（absolute模式） |
| scale | 1.0 | 缩放比例（scale模式，1.0=原尺寸） |

## 缩放模式说明
- **absolute（绝对尺寸）**：指定目标宽高，将遮罩缩放到指定尺寸
- **scale（相对比例）**：指定缩放比例，1.0=原尺寸，0.5=缩小一半，2.0=放大两倍

## 使用示例
1. 绝对尺寸模式：将遮罩缩放到 512x512
2. 相对比例模式：将遮罩放大 2 倍
3. 按比例缩小：将 scale 设为 0.5
"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "输入遮罩 (B, H, W)，值域 [0, 1]"}),
                "mode": (["absolute", "scale"], {
                    "default": "absolute",
                    "tooltip": "缩放模式：absolute（绝对尺寸）/ scale（相对比例）"
                }),
                "width": ("INT", {
                    "default": 512,
                    "min": 1,
                    "max": 4096,
                    "step": 1,
                    "tooltip": "目标宽度（absolute模式）"
                }),
                "height": ("INT", {
                    "default": 512,
                    "min": 1,
                    "max": 4096,
                    "step": 1,
                    "tooltip": "目标高度（absolute模式）"
                }),
                "scale": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.01,
                    "max": 10.0,
                    "step": 0.01,
                    "tooltip": "缩放比例（scale模式），1.0=原尺寸"
                }),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "execute"

    def execute(self, mask, mode="absolute", width=512, height=512, scale=1.0):
        if mode == "absolute":
            target_h, target_w = height, width
        else:
            # scale模式：根据原始尺寸计算目标尺寸
            B, H, W = mask.shape
            target_h = max(1, int(H * scale))
            target_w = max(1, int(W * scale))

        result = resize_masks_batch(
            masks=mask,
            target_h=target_h,
            target_w=target_w,
            preserve_dtype=True
        )
        return (result,)
# endregion




