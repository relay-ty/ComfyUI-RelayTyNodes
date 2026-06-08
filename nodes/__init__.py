"""
节点注册模块

此模块负责注册所有自定义节点，使ComfyUI能够识别和加载它们。

节点分类：
- 开关节点 (switch_nodes): 用于条件选择和分支逻辑
- 工具节点 (tool_nodes): 提供实用工具功能
- Mask操作节点 (mask_nodes): 提供遮罩扩展/收缩、羽化、分离、跟踪、合并等功能
- BBox节点 (bbox_nodes): 提供边界框转遮罩等功能
- Mask绘制节点 (mask_draw_nodes): 提供遮罩轮廓描边、半透明叠加等绘制功能
- 图像融合节点 (image_nodes): 提供Poisson梯度域融合和Alpha混合功能
- 字符串处理节点 (string_nodes): 提供字符串连接等功能

注册流程：
1. 从各模块导入节点类
2. 构建 NODE_CLASS_MAPPINGS 字典（节点名 -> 节点类）
3. 构建 NODE_DISPLAY_NAME_MAPPINGS 字典（节点名 -> 显示名称）

注意事项：
- 所有节点类名必须以 RT_ 前缀开头
- 显示名称格式为 "RT节点中文名"
"""

from .switch_nodes import RT_LazySwitch, RT_LazySwitch2way
from .tool_nodes import RT_ResolutionSelector, RT_AspectRatioSelector, RT_AspectRatioDetector
from .mask_nodes import RT_ImageToMask, RT_MaskToImage, RT_BatchMask, RT_MaskExpand, RT_GetMaskFromBatch, RT_MaskFeather
from .mask_track_nodes import RT_SeparateMasks, RT_GetTrack
from .bbox_nodes import RT_BBoxToMask
from .mask_draw_nodes import RT_MaskContour, RT_DrawMaskOnImage
from .string_nodes import RT_JoinStringMulti, RT_JoinStrings
from .math_nodes import RT_MathExpression
from .color_nodes import RT_ColorMatch
from .image_nodes import RT_PoissonBlend, RT_PoissonBlendV2, RT_BlendInpaint
from .mask_nodes import RT_MaskScale

NODE_CLASS_MAPPINGS = {
    "RT_LazySwitch": RT_LazySwitch,
    "RT_LazySwitch2way": RT_LazySwitch2way,

    "RT_ResolutionSelector": RT_ResolutionSelector,
    "RT_AspectRatioSelector": RT_AspectRatioSelector,
    "RT_AspectRatioDetector": RT_AspectRatioDetector,

    "RT_MaskExpand": RT_MaskExpand,
    "RT_MaskFeather": RT_MaskFeather,
    "RT_SeparateMasks": RT_SeparateMasks,
    "RT_GetTrack": RT_GetTrack,
    "RT_BatchMask": RT_BatchMask,
    "RT_GetMaskFromBatch": RT_GetMaskFromBatch,
    "RT_ImageToMask": RT_ImageToMask,
    "RT_MaskToImage": RT_MaskToImage,

    "RT_BBoxToMask": RT_BBoxToMask,

    "RT_MaskContour": RT_MaskContour,
    "RT_DrawMaskOnImage": RT_DrawMaskOnImage,

    "RT_JoinStringMulti": RT_JoinStringMulti,
    "RT_JoinStrings": RT_JoinStrings,

    "RT_MathExpression": RT_MathExpression,

    "RT_ColorMatch": RT_ColorMatch,

    "RT_PoissonBlend": RT_PoissonBlend,
    "RT_PoissonBlendV2": RT_PoissonBlendV2,
    "RT_BlendInpaint": RT_BlendInpaint,

    "RT_MaskScale": RT_MaskScale,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RT_LazySwitch": "RT惰性开关",
    "RT_LazySwitch2way": "RT双路惰性开关",

    "RT_ResolutionSelector": "RT分辨率选择器",
    "RT_AspectRatioSelector": "RT比例选择器",
    "RT_AspectRatioDetector": "RT比例检测器",

    "RT_MaskExpand": "RT遮罩扩展/收缩",
    "RT_MaskFeather": "RT遮罩高斯羽化",
    "RT_SeparateMasks": "RT遮罩分离",
    "RT_GetTrack": "RT获取Track",
    "RT_BatchMask": "RT复制遮罩批次",
    "RT_GetMaskFromBatch": "RT从批次获取遮罩",
    "RT_ImageToMask": "RT图像通道转遮罩",
    "RT_MaskToImage": "RT遮罩转图像",

    "RT_BBoxToMask": "RTBBox转遮罩",

    "RT_MaskContour": "RT遮罩描边",
    "RT_DrawMaskOnImage": "RT遮罩绘制",

    "RT_JoinStringMulti": "RT多字符串连接",
    "RT_JoinStrings": "RT双字符串连接",

    "RT_MathExpression": "RT数学表达式",

    "RT_ColorMatch": "RT颜色匹配",

    "RT_PoissonBlend": "RT泊松融合",
    "RT_PoissonBlendV2": "RT泊松融合V2",
    "RT_BlendInpaint": "RT遮罩混合",

    "RT_MaskScale": "RT遮罩缩放",
}