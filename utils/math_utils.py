"""
数学工具函数

此模块包含安全的数学工具函数，用于处理常见的数学操作。
"""

import math


# ── 调用者 ──
#   math_nodes.py → RT_MathExpression
# ⚠️ 修改签名/行为前必须确认调用者兼容！
def safe_sqrt(a):
    """
    安全的开平方根函数，防止对负数开平方
    """
    if a < 0:
        raise ValueError(f"sqrt({a}): 不能对负数开平方")
    return math.sqrt(a)


# ── 调用者 ──
#   math_nodes.py → RT_MathExpression
# ⚠️ 修改签名/行为前必须确认调用者兼容！
def safe_log(a):
    """
    安全的自然对数函数，防止对非正数取对数
    """
    if a <= 0:
        raise ValueError(f"log({a}): 对数参数必须大于0")
    return math.log(a)


# ── 调用者 ──
#   math_nodes.py → RT_MathExpression
# ⚠️ 修改签名/行为前必须确认调用者兼容！
def safe_log10(a):
    """
    安全的常用对数函数，防止对非正数取对数
    """
    if a <= 0:
        raise ValueError(f"log10({a}): 对数参数必须大于0")
    return math.log10(a)


# ── 调用者 ──
#   math_nodes.py → RT_MathExpression（函数字典中注册，间接调用）
# ⚠️ 修改签名/行为前必须确认调用者兼容！
def safe_div(a, b):
    """
    安全的除法函数，防止除零错误
    """
    if b == 0:
        raise ZeroDivisionError(f"{a} / {b}: 除数不能为零")
    return a / b


# ── 调用者 ──
#   math_nodes.py → RT_MathExpression（函数字典中注册，间接调用）
# ⚠️ 修改签名/行为前必须确认调用者兼容！
def safe_floordiv(a, b):
    """
    安全的整除函数，防止除零错误
    """
    if b == 0:
        raise ZeroDivisionError(f"{a} // {b}: 除数不能为零")
    return a // b


# ── 调用者 ──
#   math_nodes.py → RT_MathExpression（函数字典中注册，间接调用）
# ⚠️ 修改签名/行为前必须确认调用者兼容！
def safe_mod(a, b):
    """
    安全的取模函数，防止除零错误
    """
    if b == 0:
        raise ZeroDivisionError(f"{a} % {b}: 除数不能为零")
    return a % b
