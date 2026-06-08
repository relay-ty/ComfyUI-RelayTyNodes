"""
字符串处理节点实现

此模块包含各种字符串处理节点，提供字符串连接等功能。

节点列表：
- RT_JoinStringMulti: 多个字符串连接节点（所有输入都可不连线）
- RT_JoinStrings: 双字符串连接节点
"""

from ..utils import RelayNodeBase

# 解析字符串中的转义字符
def parse_escape_chars(s):
    """
    解析字符串中的转义字符
    
    参数：
        s: 输入字符串
        
    返回：
        解析后的字符串，将 \\n, \\t, \\r 等转换为实际字符
    """
    if not s:
        return s
    
    # 使用字符串替换解析常见转义字符
    s = s.replace('\\n', '\n')
    s = s.replace('\\t', '\t')
    s = s.replace('\\r', '\r')
    s = s.replace('\\\\', '\\')
    
    return s

# region RT_JoinStringMulti
# RT多字符串连接节点（所有输入都可不连线）
class RT_JoinStringMulti(RelayNodeBase):
    """
    RT多字符串连接节点

    功能：连接多个字符串输入，支持自定义分隔符和清理空白
    改进：所有输入都可以为空且可不连线，inputcount 支持 2-1000
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "inputcount": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "输入字符串的数量（2-1000）"
                }),
                "delimiter": ("STRING", {
                    "default": "\\n",
                    "multiline": False,
                    "tooltip": "连接分隔符（支持 \\n, \\t 等转义字符）"
                }),
                "clean_whitespace": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "清理每个输入的首尾空白字符"
                }),
                "return_list": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "返回字符串列表而非连接后的字符串"
                }),
            },
            "optional": {
                "string_1": ("STRING", {
                    "default": "",
                    "forceInput": True,  # 显示为输入端口
                    "tooltip": "第一个字符串"
                }),
                "string_2": ("STRING", {
                    "default": "",
                    "forceInput": True,  # 显示为输入端口
                    "tooltip": "第二个字符串"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "combine"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT多字符串连接

## 功能
连接多个字符串输入，支持自定义分隔符和清理空白。所有输入都可以为空，inputcount 支持 2-1000。

## 输入
- 字符串① ~ 字符串N: 要连接的字符串（所有都可不连线）

## 输出
- 字符串: 连接后的字符串或字符串列表

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 输入数量 | 2 | 输入字符串的数量（2-1000） |
| 分隔符 | 空格 | 连接分隔符（支持 \\n, \\t 等转义字符） |
| 清理空白 | false | 清理每个输入的首尾空白 |
| 返回列表 | false | 返回字符串列表而非单字符串 |
"""

    def combine(self, inputcount, delimiter=" ", clean_whitespace=False, return_list=False, **kwargs):
        """
        合并多个字符串

        参数：
            inputcount: 输入数量
            delimiter: 分隔符（会解析转义字符）
            clean_whitespace: 是否清理首尾空白
            return_list: 是否返回列表
            **kwargs: 所有字符串输入

        返回：
            tuple: 合并后的字符串或字符串列表
        """
        # 解析分隔符中的转义字符
        delimiter = parse_escape_chars(delimiter)

        # 处理 inputcount=0 的情况
        if inputcount <= 0:
            if return_list:
                return ([],)
            else:
                return ("",)

        strings = []

        # 遍历所有字符串输入
        for c in range(1, inputcount + 1):
            text = kwargs.get(f"string_{c}", "")
            
            # 清理空白
            if clean_whitespace:
                text = text.strip()
            
            # 只处理非空字符串
            if text != "":
                strings.append(text)

        if return_list:
            return (strings,)
        else:
            return (delimiter.join(strings),)
# endregion


# region RT_JoinStrings
# RT双字符串连接节点
class RT_JoinStrings(RelayNodeBase):
    """
    RT双字符串连接节点

    功能：连接两个字符串，支持自定义分隔符和清理空白
    改进：两个输入都可以不连线
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "delimiter": ("STRING", {
                    "default": " ",
                    "multiline": False,
                    "tooltip": "连接分隔符（支持 \\n, \\t 等转义字符）"
                }),
                "clean_whitespace": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "清理每个输入的首尾空白字符"
                }),
            },
            "optional": {
                "string1": ("STRING", {
                    "default": "",
                    "forceInput": False,  # 修改为 False，显示为输入框
                    "tooltip": "第一个字符串"
                }),
                "string2": ("STRING", {
                    "default": "",
                    "forceInput": False,  # 修改为 False，显示为输入框
                    "tooltip": "第二个字符串"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "joinstring"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT双字符串连接

## 功能
连接两个字符串，支持自定义分隔符和清理空白。

## 输入
- 字符串①: 第一个字符串（可不连线）
- 字符串②: 第二个字符串（可不连线）

## 输出
- 字符串: 连接后的字符串

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 分隔符 | 空格 | 连接分隔符（支持 \\n, \\t 等转义字符） |
| 清理空白 | false | 清理每个输入的首尾空白 |
"""

    def joinstring(self, delimiter=" ", clean_whitespace=False, string1="", string2=""):
        """
        连接两个字符串

        参数：
            delimiter: 分隔符（会解析转义字符）
            clean_whitespace: 是否清理首尾空白
            string1: 第一个字符串
            string2: 第二个字符串

        返回：
            tuple: 连接后的字符串
        """
        # 解析分隔符中的转义字符
        delimiter = parse_escape_chars(delimiter)

        # 清理空白
        if clean_whitespace:
            string1 = string1.strip()
            string2 = string2.strip()

        # 收集非空字符串
        strings = []
        if string1 != "":
            strings.append(string1)
        if string2 != "":
            strings.append(string2)

        return (delimiter.join(strings),)
# endregion
