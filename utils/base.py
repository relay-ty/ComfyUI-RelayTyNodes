"""
基础类模块

此模块包含所有 RelayTyNodes 节点的基础类。

核心功能：
- RelayNodeBase: 所有自定义节点的基类，提供统一的节点分类名称
"""


# ── 调用者 ──
#   mask_nodes.py      → RT_ImageToMask, RT_MaskToImage, RT_BatchMask,
#                         RT_GetMaskFromBatch, RT_MaskExpand, RT_MaskFeather
#   nodes_debug.py     → RT_SeparateMasks, RT_GetTrack
#   bbox_nodes.py      → RT_BBoxToMask
#   mask_draw_nodes.py → RT_MaskContour, RT_DrawMaskOnImage
#   image_nodes.py     → RT_PoissonBlend, RT_BlendInpaint
#   color_nodes.py     → RT_ColorMatch
#   switch_nodes.py    → RT_LazySwitch, RT_LazySwitch2way
#   tool_nodes.py      → RT_ResolutionSelector, RT_AspectRatioSelector, RT_AspectRatioDetector
#   math_nodes.py      → RT_MathExpression
#   string_nodes.py    → RT_JoinStringMulti, RT_JoinStrings
#   mask_track_nodes.py → RT_GetTrack, RT_SeparateMasks
# ⚠️ 修改 RelayNodeBase 会影响全部 22 个节点！务必充分测试！
class RelayNodeBase:
    """
    所有 RelayTyNodes 节点的基础类

    提供通用的节点配置，如分类名称等，确保所有节点具有一致的行为。

    类属性：
        CATEGORY: 节点在 ComfyUI 菜单中的分类名称，固定为 "RelayTyNodes"

    使用方式：
        class MyCustomNode(RelayNodeBase):
            # 自定义节点实现
            pass
    """

    CATEGORY = "RelayTyNodes"

    def __init__(self):
        super().__init__()
        if not hasattr(self, "properties"):
            self.properties = {}
        self.properties.setdefault("aux_id", "relay-ty/ComfyUI-RelayTyNodes")