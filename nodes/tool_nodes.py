"""
工具节点实现

此模块包含各种工具类节点，提供实用功能。

节点列表：
- RT_ResolutionSelector: 分辨率选择节点
- RT_AspectRatioSelector: 比例选择节点
- RT_AspectRatioDetector: 比例检测节点
"""

# 导入必要的库和基类
import torch
from ..utils import RelayNodeBase


# region RT_ResolutionSelector
# RT分辨率选择器节点
class RT_ResolutionSelector(RelayNodeBase):
    """
    分辨率选择节点

    功能：根据选择的分辨率选项，输出对应的整数分辨率值
    应用场景：快速选择标准分辨率值，如视频编码、图像生成等场景

    支持的分辨率：
    - 360P: 360像素
    - 480P: 480像素  
    - 720P: 720像素（高清）
    - 1080P: 1080像素（全高清）
    - 1440P: 1440像素（2K）
    - 2160P: 2160像素（4K）
    """

    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点的输入参数

        返回值：
            dict: 包含required输入参数的字典
        """
        return {
            "required": {
                # 分辨率选项下拉菜单
                "resolution": (
                    [
                        "360P",  # 360像素
                        "480P",  # 480像素
                        "720P",  # 720像素（高清）
                        "1080P",  # 1080像素（全高清）
                        "1440P",  # 1440像素（2K）
                        "2160P",  # 2160像素（4K）
                    ],
                    {"default": "720P", },  # 默认选中720P
                ),
            }
        }

    # 定义节点的输出类型为整数
    RETURN_TYPES = ("INT",)
    # 定义节点的输出名称
    RETURN_NAMES = ("resolution",)
    # 定义节点的主要函数
    FUNCTION = "select"
    # 节点分类
    CATEGORY = "RelayTyNodes"
    # 节点描述文档
    DESCRIPTION = """
# RT分辨率选择器

## 功能
快速选择标准分辨率值，输出对应的整数值。

## 输入
- 分辨率: 分辨率选项

## 输出
- 分辨率: 分辨率整数值

## 参数选项说明
| 参数名称 | 对应选项 | 说明 |
|----------|----------|------|
| 分辨率 | 360P | 360像素 |
| 分辨率 | 480P | 480像素 |
| 分辨率 | 720P | 720像素（高清） |
| 分辨率 | 1080P | 1080像素（全高清） |
| 分辨率 | 1440P | 1440像素（2K） |
| 分辨率 | 2160P | 2160像素（4K） |
"""

    def __init__(self):
        super().__init__()

    def select(self, resolution):
        """
        执行分辨率选择逻辑

        参数：
            resolution (str): 选择的分辨率字符串，如"720P"、"1080P"等

        返回值：
            tuple: 包含分辨率整数值的元组
        """
        # 分辨率映射字典，将字符串映射到对应的整数值
        resolution_map = {
            "360P": 360,
            "480P": 480,
            "720P": 720,
            "1080P": 1080,
            "1440P": 1440,
            "2160P": 2160
        }

        # 返回对应的分辨率值，如果未找到则返回默认值720
        return (resolution_map.get(resolution, 720),)


# RT比例选择器节点
class RT_AspectRatioSelector(RelayNodeBase):
    """
    比例选择节点

    功能：根据选择的比例选项，输出对应的宽高比字符串
    应用场景：快速选择标准比例值，如图像裁剪、画布设置等场景

    支持的比例：
    - 1:1: 正方形
    - 4:3: 标准电视比例
    - 16:9: 宽屏电视比例
    - 9:16: 竖屏手机比例
    - 3:4: 竖屏标准比例
    - 21:9: 超宽屏比例
    """

    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点的输入参数

        返回值：
            dict: 包含required输入参数的字典
        """
        return {
            "required": {
                # 比例选项下拉菜单
                "aspect_ratio": (
                    [
                        "1:1",  # 正方形
                        "4:3",  # 标准电视比例
                        "16:9",  # 宽屏电视比例
                        "9:16",  # 竖屏手机比例
                        "3:4",  # 竖屏标准比例
                        "21:9",  # 超宽屏比例
                    ],
                    {"default": "9:16", },  # 默认选中9:16（适合手机屏幕）
                ),
            }
        }

    # 定义节点的输出类型为字符串
    RETURN_TYPES = ("STRING",)
    # 定义节点的输出名称
    RETURN_NAMES = ("aspect_ratio",)
    # 定义节点的主要函数
    FUNCTION = "select"
    # 节点分类
    CATEGORY = "RelayTyNodes"
    # 节点描述文档
    DESCRIPTION = """
# RT比例选择器

## 功能
快速选择标准宽高比，输出对应的字符串。

## 输入
- 宽高比: 比例选项

## 输出
- 宽高比: 比例字符串

## 参数选项说明
| 参数名称 | 对应选项 | 说明 |
|----------|----------|------|
| 宽高比 | 1:1 | 正方形 |
| 宽高比 | 4:3 | 标准电视比例 |
| 宽高比 | 16:9 | 宽屏电视比例 |
| 宽高比 | 9:16 | 竖屏手机比例 |
| 宽高比 | 3:4 | 竖屏标准比例 |
| 宽高比 | 21:9 | 超宽屏比例 |
"""

    def __init__(self):
        super().__init__()

    def select(self, aspect_ratio):
        """
        执行比例选择逻辑

        参数：
            aspect_ratio (str): 选择的比例字符串，如"16:9"、"9:16"等

        返回值：
            tuple: 包含比例字符串的元组
        """
        # 直接返回选择的比例字符串
        return (aspect_ratio,)


# endregion


# region RT_AspectRatioDetector
# RT比例检测器节点
class RT_AspectRatioDetector(RelayNodeBase):
    """
    比例检测节点

    功能：根据输入参考图的宽高比，输出对应的常用比例字符串
    应用场景：自动检测图像的比例并转换为标准比例格式，便于后续处理

    检测逻辑：
    1. 获取输入图像的宽度和高度
    2. 计算宽高比的最简分数形式
    3. 匹配到最接近的标准比例
    """

    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点的输入参数

        返回值：
            dict: 包含required输入参数的字典
        """
        return {
            "required": {
                # 参考图像输入，用于检测比例
                "image": ("IMAGE",),
            }
        }

    # 定义节点的输出类型为字符串
    RETURN_TYPES = ("STRING",)
    # 定义节点的输出名称
    RETURN_NAMES = ("aspect_ratio",)
    # 定义节点的主要函数
    FUNCTION = "detect"
    # 节点分类
    CATEGORY = "RelayTyNodes"
    # 节点描述文档
    DESCRIPTION = """
# RT比例检测器

## 功能
根据输入图像自动检测并输出最接近的标准宽高比。

## 输入
- 图像: 参考图像

## 输出
- 宽高比: 检测到的比例字符串

## 检测逻辑
1. 获取输入图像的宽度和高度
2. 计算宽高比的实际值
3. 匹配到最接近的标准比例

## 支持的标准比例
| 比例 | 说明 |
|------|------|
| 1:1 | 正方形 |
| 4:3 | 标准电视比例 |
| 16:9 | 宽屏电视比例 |
| 9:16 | 竖屏手机比例 |
| 3:4 | 竖屏标准比例 |
| 21:9 | 超宽屏比例 |
"""

    def __init__(self):
        super().__init__()

    def detect(self, image):
        """
        执行比例检测逻辑

        参数：
            image (torch.Tensor): 输入图像张量，形状通常为 (batch_size, height, width, channels)

        返回值：
            tuple: 包含检测到的比例字符串的元组
        """
        # 定义标准比例列表及其对应的宽高比值
        standard_ratios = [
            ("1:1", 1.0),
            ("4:3", 4/3),
            ("16:9", 16/9),
            ("9:16", 9/16),
            ("3:4", 3/4),
            ("21:9", 21/9),
        ]

        # 默认返回值
        detected_ratio = "1:1"

        # 检查图像是否有效
        if image is not None and len(image.shape) >= 3:
            # 获取图像的高度和宽度
            # 图像张量形状通常为 (batch_size, height, width, channels)
            height = image.shape[1]
            width = image.shape[2]

            # 计算宽高比
            if height > 0:
                actual_ratio = width / height

                # 找到最接近的标准比例
                min_diff = float('inf')
                for ratio_str, ratio_val in standard_ratios:
                    diff = abs(actual_ratio - ratio_val)
                    if diff < min_diff:
                        min_diff = diff
                        detected_ratio = ratio_str

        # 返回检测到的比例字符串
        return (detected_ratio,)
# endregion