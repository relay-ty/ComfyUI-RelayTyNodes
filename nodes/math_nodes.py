"""
数学表达式节点实现

此模块包含数学表达式计算节点，支持动态添加输入变量和任意类型输入。

节点列表：
- RT_MathExpression: 数学表达式计算节点（支持动态添加输入变量，支持 any 类型）
"""

import ast
import math
import operator as op
import random
import logging

from ..utils import RelayNodeBase, AnyType, any
from ..utils.math_utils import safe_sqrt, safe_log, safe_log10, safe_div, safe_floordiv, safe_mod

logger = logging.getLogger(__name__)

# 运算符映射
operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg,
    ast.Mod: op.mod,
    ast.BitAnd: op.and_,
    ast.BitOr: op.or_,
    ast.Invert: op.invert,
    ast.And: lambda a, b: 1 if a and b else 0,
    ast.Or: lambda a, b: 1 if a or b else 0,
    ast.Not: lambda a: 0 if a else 1,
    ast.RShift: op.rshift,
    ast.LShift: op.lshift,
}

# 内置函数（结构化格式，支持参数校验和自动补全）
functions = {
    "abs": {"args": (1, 1), "call": lambda a: abs(a), "hint": "number"},
    "sqrt": {"args": (1, 1), "call": safe_sqrt, "hint": "number"},
    "log": {"args": (1, 1), "call": safe_log, "hint": "number"},
    "log10": {"args": (1, 1), "call": safe_log10, "hint": "number"},
    "sin": {"args": (1, 1), "call": math.sin, "hint": "number"},
    "cos": {"args": (1, 1), "call": math.cos, "hint": "number"},
    "tan": {"args": (1, 1), "call": math.tan, "hint": "number"},
    "asin": {"args": (1, 1), "call": math.asin, "hint": "number"},
    "acos": {"args": (1, 1), "call": math.acos, "hint": "number"},
    "atan": {"args": (1, 1), "call": math.atan, "hint": "number"},
    "floor": {"args": (1, 1), "call": math.floor, "hint": "number"},
    "ceil": {"args": (1, 1), "call": math.ceil, "hint": "number"},
    "round": {"args": (1, 2), "call": lambda a, n=0: round(a, n), "hint": "number, dp? = 0"},
    "pow": {"args": (2, 2), "call": op.pow, "hint": "base, exponent"},
    "max": {"args": (1, -1), "call": lambda *args: max(args), "hint": "...numbers"},
    "min": {"args": (1, -1), "call": lambda *args: min(args), "hint": "...numbers"},
    "random": {"args": (0, 0), "call": lambda: random.random(), "hint": "() → float in [0, 1)"},
    "randint": {"args": (2, 2), "call": lambda a, b: random.randint(int(a), int(b)), "hint": "min, max"},
    "randomint": {"args": (2, 2), "call": lambda a, b: random.randint(int(a), int(b)), "hint": "min, max"},
    "randomchoice": {"args": (2, -1), "call": lambda *args: random.choice(args), "hint": "...numbers"},
    "exp": {"args": (1, 1), "call": math.exp, "hint": "number"},
    "int": {"args": (1, 1), "call": lambda a: int(a), "hint": "number"},
    "float": {"args": (1, 1), "call": lambda a: float(a), "hint": "number"},
    # 三元函数：iif(条件, 真值, 假值)
    "iif": {"args": (3, 3), "call": lambda a, b, c=0: b if a else c, "hint": "condition, true, false"},
    # 限幅函数
    "clamp": {"args": (3, 3), "call": lambda a, lo, hi: max(lo, min(hi, a)), "hint": "value, min, max"},
    "clip": {"args": (3, 3), "call": lambda a, lo, hi: max(lo, min(hi, a)), "hint": "value, min, max"},
}

# 自动补全词表（兼容 pysssss.autocomplete 扩展）
autocompleteWords = [
    {
        "text": name,
        "value": f"{name}()",
        "showValue": False,
        "hint": info["hint"],
        "caretOffset": -1,
    }
    for name, info in functions.items()
]


# region RT_MathExpression
# RT数学表达式节点（支持动态输入变量）
class RT_MathExpression(RelayNodeBase):
    """
    RT数学表达式节点

    功能：支持变量和常量的数学表达式求值，支持动态添加输入变量（通过 inputcount 和 "Update inputs" 按钮）

    输入：
    - a, b, c, ... z: 动态输入端口（数量由 inputcount 控制，支持任意类型）

    输出：
    - result: 表达式的计算结果
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "expression": ("STRING", {
                    "default": "a + b",
                    "multiline": True,
                    "dynamicPrompts": False,
                    "tooltip": "数学表达式，支持变量名、运算符、比较运算和内置函数"
                }),
                "inputcount": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": 26,
                    "step": 1,
                    "tooltip": "输入变量的数量（2-26，对应 a~z）"
                }),
            },
            "optional": {
                "a": (any, {"default": 0}),
                "b": (any, {"default": 0}),
            }
        }
        # 兼容 pysssss.autocomplete 扩展（若已安装）
        try:
            from pysssss import autocomplete
            inputs["required"]["expression"][1]["pysssss.autocomplete"] = {
                "words": autocompleteWords,
                "separator": ""
            }
        except ImportError:
            pass
        return inputs

    RETURN_TYPES = ("FLOAT", "INT", "BOOLEAN")
    RETURN_NAMES = ("float", "int", "bool")
    FUNCTION = "evaluate"
    CATEGORY = "RelayTyNodes"
    OUTPUT_NODE = True  # 启用 UI 实时显示结果

    @classmethod
    def IS_CHANGED(cls, expression, **kwargs):
        """含 random/randint 的表达式强制重新执行，不走缓存"""
        if "random" in expression.lower() or "randint" in expression.lower():
            return float("nan")
        return expression

    DESCRIPTION = """
# RT数学表达式

## 功能
支持变量和常量的数学表达式求值，支持动态添加输入变量。点击 "Update inputs" 按钮可根据输入数量动态调整 a~z 端口。
同时输出 float、int、bool 三种类型的结果。

## 输入
- a, b, c, ... z: 动态输入端口（数量由输入数量控制，支持任意类型）

## 输出
- 浮点: 表达式计算的浮点结果
- 整数: 表达式计算的整数结果
- 布尔: 表达式计算的布尔结果（用于比较和逻辑运算）

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 表达式 | a + b | 数学表达式，支持变量名、运算符、比较运算 |
| 输入数量 | 2 | 动态输入端口数量（2-26，对应 a~z），点击 "Update inputs" 生效 |

## 支持的运算符
- 算术: +, -, *, /, //, **, %
- 位运算: &, |, ^, <<, >>, ~
- 比较: >, <, >=, <=, ==, !=
- 逻辑: and, or, not（也支持 &&, ||, !）
- Python风格: and / or / not
- C风格: && / || / !

## 支持的函数
| 函数 | 说明 |
|------|------|
| abs(x) | 绝对值 |
| sqrt(x) | 平方根 |
| log(x) / log10(x) | 自然对数 / 常用对数 |
| exp(x) | e的x次方 |
| sin/cos/tan(x) | 三角函数 |
| asin/acos/atan(x) | 反三角函数 |
| floor/ceil(x) | 向下/向上取整 |
| round(x, n) | 四舍五入（n=小数位数） |
| pow(x, y) | x的y次方 |
| max/min(...) | 最大/最小值 |
| random() | [0,1) 随机浮点数 |
| randint(a, b) | [a, b] 随机整数 |
| randomint(a, b) | 同 randint（别名） |
| randomchoice(...) | 随机选择一个值 |
| int(x) / float(x) | 类型转换 |
| iif(cond, t, f) | 三元：条件为真返回t，否则返回f |
| clamp/clip(v, lo, hi) | 限幅：将v限制在[lo, hi] |

## 属性访问（图像/潜空间）
- `a.width` / `a.height`：获取连接到 a 端口的图像或潜空间尺寸
- 支持 IMAGE tensor（B,H,W,C）和 LATENT dict

## 表达式示例
- `a + b * c`：基本运算
- `(a + b) * c - d`：括号运算
- `((1-a)%b+(b-1))%b+c`：取模运算
- `a > 1 and b > 2`：逻辑比较
- `a > 1 && b > 2`：C风格逻辑
- `a == b or c != d`：等于/不等于
- `iif(a > 5, 100, 200)`：三元表达式
- `clamp(a, 0, 100)`：限幅
- `a.width * 0.5`：使用图像尺寸
- `randint(1, 100)`：随机数（自动禁用缓存）
"""

    def _get_size(self, target, property_name):
        """借鉴 Swwan/Custom-Scripts：支持图像/latent 的尺寸属性访问"""
        # Latent 字典类型 {"samples": tensor}
        if isinstance(target, dict) and "samples" in target:
            samples = target["samples"]
            if property_name == "width":
                return samples.shape[3] * 8
            return samples.shape[2] * 8
        # torch.Tensor (B, H, W, C) 格式
        if hasattr(target, 'shape') and len(target.shape) >= 3:
            if property_name == "width":
                return target.shape[2]
            if property_name == "height":
                return target.shape[1]
        return None

    def evaluate(self, expression, inputcount=2, **kwargs):
        # 1. 动态收集输入变量（a, b, c...）
        inputs = {}
        for i in range(inputcount):
            var_name = chr(ord("a") + i)
            inputs[var_name] = kwargs.get(var_name, 0)

        # 2. 标准化表达式：将 C 风格运算符 && || ! 转换为 Python and or not
        import re
        normalized_expr = expression
        normalized_expr = normalized_expr.replace('&&', ' and ')
        normalized_expr = normalized_expr.replace('||', ' or ')
        # 注意：! 在 Python 中是 bitwise not，需要特殊处理 != 的情况
        normalized_expr = re.sub(r'!(?!=)', ' not ', normalized_expr)
        # 移除多余空格
        normalized_expr = ' '.join(normalized_expr.split())

        # 3. 表达式安全校验
        try:
            tree = ast.parse(normalized_expr, mode='eval')
            # 安全检查：只允许安全的表达式节点类型
            allowed_nodes = (
                ast.Expression, ast.BinOp, ast.UnaryOp,
                ast.Constant, ast.Num, ast.Name, ast.Call,
                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                ast.Pow, ast.Mod, ast.BitAnd, ast.BitOr, ast.BitXor,
                ast.LShift, ast.RShift, ast.Not, ast.USub,
                ast.And, ast.Or, ast.BoolOp,
                # 比较运算符
                ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
                # 容器操作
                ast.Tuple, ast.List,
                # 借鉴 Swwan：属性访问（如 a.width / a.height）
                ast.Attribute,
                # 上下文标记（变量加载）
                ast.Load,
            )
            for node in ast.walk(tree):
                if not isinstance(node, allowed_nodes):
                    logger.warning(f"[RT_MathExpression] 表达式包含非法节点类型: {type(node).__name__}")
                    return {"ui": {"value": [0.0]}, "result": (0.0, 0, False)}
        except SyntaxError as e:
            logger.warning(f"[RT_MathExpression] 表达式语法错误: {e}")
            return {"ui": {"value": [0.0]}, "result": (0.0, 0, False)}

        # 4. 构建变量字典和函数
        local_vars = {**inputs}
        for name, info in functions.items():
            local_vars[name] = self._make_function(name, info["call"], info["args"])

        # 5. 手写求值（借鉴 Custom-Scripts 模式：更安全，支持属性访问）
        try:
            def eval_node(node):
                if isinstance(node, ast.Constant):
                    return node.value
                if isinstance(node, ast.Num):  # 兼容旧版 Python
                    return node.n
                if isinstance(node, ast.BinOp):
                    l = eval_node(node.left)
                    r = eval_node(node.right)
                    if type(node.op) in operators:
                        return operators[type(node.op)](l, r)
                    raise TypeError(f"不支持的二元运算符: {type(node.op).__name__}")
                if isinstance(node, ast.UnaryOp):
                    val = eval_node(node.operand)
                    if type(node.op) in operators:
                        return operators[type(node.op)](val)
                    raise TypeError(f"不支持的一元运算符: {type(node.op).__name__}")
                if isinstance(node, ast.BoolOp):
                    values = [eval_node(v) for v in node.values]
                    if isinstance(node.op, ast.And):
                        result = 1
                        for v in values:
                            result = result and v
                        return 1 if result else 0
                    if isinstance(node.op, ast.Or):
                        result = 0
                        for v in values:
                            result = result or v
                        return 1 if result else 0
                    raise TypeError(f"不支持的布尔运算符: {type(node.op).__name__}")
                if isinstance(node, ast.Compare):
                    l = eval_node(node.left)
                    for op, comparator in zip(node.ops, node.comparators):
                        r = eval_node(comparator)
                        if isinstance(op, ast.Eq):
                            if not (l == r): return 0
                        elif isinstance(op, ast.NotEq):
                            if not (l != r): return 0
                        elif isinstance(op, ast.Gt):
                            if not (l > r): return 0
                        elif isinstance(op, ast.GtE):
                            if not (l >= r): return 0
                        elif isinstance(op, ast.Lt):
                            if not (l < r): return 0
                        elif isinstance(op, ast.LtE):
                            if not (l <= r): return 0
                        else:
                            raise NotImplementedError(f"不支持的比较运算符: {type(op).__name__}")
                        l = r
                    return 1
                if isinstance(node, ast.Name):
                    if node.id in local_vars:
                        return local_vars[node.id]
                    raise NameError(f"变量未定义: {node.id}")
                # 借鉴 Swwan：属性访问 a.width / a.height
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) and node.value.id in inputs:
                        target = inputs[node.value.id]
                        if node.attr in ("width", "height"):
                            size = self._get_size(target, node.attr)
                            if size is not None:
                                return size
                    raise AttributeError(f"无法访问属性: {node.value.id if isinstance(node.value, ast.Name) else '?'}.{node.attr}")
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in local_vars:
                        fn = local_vars[node.func.id]
                        args = [eval_node(arg) for arg in node.args]
                        return fn(*args)
                    raise NameError(f"未定义的函数: {node.func.id if isinstance(node.func, ast.Name) else '?'}")
                if isinstance(node, ast.Tuple):
                    return tuple(eval_node(elt) for elt in node.elts)
                if isinstance(node, ast.List):
                    return [eval_node(elt) for elt in node.elts]
                raise TypeError(f"不支持的节点类型: {type(node).__name__}")

            result = eval_node(tree.body)

            # 6. 类型转换
            bool_result = bool(result)
            try:
                int_result = int(result) if not isinstance(result, bool) else (1 if result else 0)
            except (ValueError, TypeError, OverflowError):
                int_result = 0
            try:
                float_result = float(result) if not isinstance(result, bool) else (1.0 if result else 0.0)
            except (ValueError, TypeError, OverflowError):
                float_result = 0.0

            # 7. 借鉴 Custom-Scripts：UI 实时显示 + 字典返回
            display_value = float_result
            return {
                "ui": {"value": [display_value]},
                "result": (float_result, int_result, bool_result)
            }
        except Exception as e:
            logger.warning(f"[RT_MathExpression] 表达式求值失败: {e}")
            return {"ui": {"value": [0.0]}, "result": (0.0, 0, False)}

    def _make_function(self, name, func, arg_range):
        def wrapper(*args):
            min_args, max_args = arg_range
            if min_args <= len(args) <= (100 if max_args == -1 else max_args):
                try:
                    return func(*args)
                except:
                    return 0
            return 0
        return wrapper
# endregion
