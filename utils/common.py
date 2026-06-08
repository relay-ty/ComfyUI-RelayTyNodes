"""
通用工具函数模块

此模块包含通用的工具函数和基础类。

核心功能：
- get_input_type: 获取输入值的类型名称
- AnyType: 通配符类型，用于动态输入端口
"""

from typing import Any


# ── 调用者 ──
#   (暂无节点直接引用，辅助工具函数)
def get_input_type(input_value):
    """
    获取输入值的类型名称

    用于在运行时动态判断输入数据的类型，支持类型通配符。

    参数：
        input_value: 任意类型的输入值

    返回值：
        str: 输入值的类型名称，如果为None则返回"*"通配符
    """
    if input_value is None:
        return "*"
    return type(input_value).__name__


# ── 调用者 ──
#   math_nodes.py → RT_MathExpression（INPUT_TYPES 中使用 any 实例）
# ⚠️ 修改 __ne__ 行为会影响所有使用 any 通配符端口的节点！
class AnyType(str):
    """
    通配符类型，用于 ComfyUI 动态输入端口

    在比较运算中始终返回 False，使节点可以接受任意类型的输入。
    主要用于开关类节点（RT_LazySwitch 等）

    使用方式：
        from utils import AnyType
        any = AnyType("*")

        # 在 INPUT_TYPES 中使用
        "required": {
            "input": (any, {}),
        }
    """

    def __ne__(self, __value: object) -> bool:
        return False


any = AnyType("*")


# ── 调用者 ──
#   mask_draw_nodes.py → RT_DrawMaskOnImage
# ⚠️ 修改颜色格式解析逻辑会影响所有使用颜色字符串的节点！
def parse_color_str(color_str: str) -> tuple:
    """
    解析颜色字符串为 RGB + Alpha 元组

    支持格式：
        - Hex: "#FF0000" / "#FF000080" / "#F00" / "#F008"
        - RGB: "255, 0, 0" / "1.0, 0.0, 0.0"
        - RGBA: "255, 0, 0, 128" / "1.0, 0.0, 0.0, 0.5"

    参数：
        color_str: 颜色字符串

    返回值：
        (rgb: list[float], alpha: float) - RGB 值域 [0, 1]，alpha 值域 [0, 1]

    异常：
        ValueError: 无效的颜色格式
    """
    color_str = color_str.strip()

    if color_str.startswith('#'):
        hex_color = color_str.lstrip('#')
        if len(hex_color) == 3:
            rgb = [int(c * 2, 16) / 255.0 for c in hex_color]
            alpha = 1.0
        elif len(hex_color) == 4:
            rgb = [int(c * 2, 16) / 255.0 for c in hex_color[:3]]
            alpha = int(hex_color[3] * 2, 16) / 255.0
        elif len(hex_color) == 6:
            rgb = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
            alpha = 1.0
        elif len(hex_color) == 8:
            rgb = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
            alpha = int(hex_color[6:8], 16) / 255.0
        else:
            raise ValueError(f"无效的Hex颜色格式: {color_str}")
    else:
        parts = [x.strip() for x in color_str.split(',')]
        values = []
        for x in parts:
            val = float(x)
            values.append(val / 255.0 if val > 1.0 else val)

        rgb = values[:3]
        alpha = values[3] if len(values) == 4 else 1.0

    return rgb, alpha


__all__ = [
    "get_input_type",
    "AnyType",
    "any",
    "parse_color_str",
]
