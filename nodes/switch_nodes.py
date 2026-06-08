"""
Switch节点实现

此模块包含各种开关节点，用于根据条件选择并输出相应的输入值。

节点列表：
- RT_LazySwitch: 单路惰性开关节点
- RT_LazySwitch2way: 双路惰性开关节点
"""

# 导入RelayNodeBase基类
from ..utils import RelayNodeBase


# region RT_LazySwitch
# RT惰性开关节点（单路）
class RT_LazySwitch(RelayNodeBase):
    """
    基本LazySwitch节点

    功能：根据condition参数的值，选择并输出on_true或on_false
    应用场景：在工作流中实现条件逻辑，动态切换不同的输入

    惰性求值特性：
    - 只有被选中的输入才会被计算
    - 未被选中的输入可以为None而不影响执行
    - 提高工作流执行效率，避免不必要的计算
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
                # 条件参数，用于决定返回哪个输入值
                "condition": ("BOOLEAN", {"default": True}),
                # 条件为真时的输入值，使用*通配符表示任意类型，启用惰性求值
                "on_true": ("*", {"lazy": True}),
                # 条件为假时的输入值，使用*通配符表示任意类型，启用惰性求值
                "on_false": ("*", {"lazy": True}),
            }
        }

    # 定义节点的输出类型，使用*通配符表示任意类型
    RETURN_TYPES = ("*",)
    # 定义节点的输出名称
    RETURN_NAMES = ("output",)
    # 定义节点的主要函数
    FUNCTION = "switch"
    # 节点分类
    CATEGORY = "RelayTyNodes"
    # 节点描述文档
    DESCRIPTION = """
# RT惰性开关

## 功能
根据条件值选择并输出对应的输入。支持惰性求值，只有被选中的输入才会被计算。

## 输入
- 条件: 条件值（True/False）
- 条件为真: 条件为真时的输出
- 条件为假: 条件为假时的输出

## 输出
- 输出: 根据条件选择的结果

## 使用建议
- 惰性求值特性：未被选中的输入可以为None而不影响执行
- 提高工作流执行效率，避免不必要的计算

## 示例
```
condition=True, on_true="A", on_false="B" → output="A"
condition=False, on_true="A", on_false="B" → output="B"
```
"""

    def __init__(self):
        super().__init__()

    def check_lazy_status(self, condition, on_true, on_false):
        """
        检查惰性输入的状态

        用于在执行前验证所需的输入是否已提供，避免运行时错误。

        参数：
            condition (bool): 条件值，决定哪个输入会被使用
            on_true: 条件为真时的输入值
            on_false: 条件为假时的输入值

        返回值：
            list or None: 未提供的必需输入名称列表，如果所有必需输入都已提供则返回None
        """
        result = []
        if condition:
            if on_true is None:
                result.append("on_true")
        else:
            if on_false is None:
                result.append("on_false")
        return result if result else None

    def switch(self, condition, on_true=None, on_false=None):
        """
        执行条件选择逻辑

        根据condition参数的值，返回对应的输入值。
        由于使用了惰性求值，未被选中的输入不会被计算。

        参数：
            condition (bool): 条件值，为True时返回on_true，为False时返回on_false
            on_true: 条件为真时的输入值（任意类型）
            on_false: 条件为假时的输入值（任意类型）

        返回值：
            tuple: 包含选择结果的元组
        """
        if condition:
            # 条件为真，返回on_true对应的输入值
            return (on_true,)
        else:
            # 条件为假，返回on_false对应的输入值
            return (on_false,)


# endregion


# region RT_LazySwitch2way
# RT双路惰性开关节点
class RT_LazySwitch2way(RelayNodeBase):
    """
    双路LazySwitch节点

    功能：根据condition参数的值，同时选择并输出两组输入值
    应用场景：需要同时切换多个相关输入的场景，如同时切换图像和蒙版

    惰性求值特性：
    - 只有被选中的输入组才会被计算
    - 未被选中的输入组可以为None而不影响执行
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
                # 条件值，布尔类型，默认为True
                "condition": ("BOOLEAN", {"default": True}),
                # 条件为真时的第一个输入，支持任意类型，启用惰性求值
                "on_true_1": ("*", {"lazy": True}),
                # 条件为真时的第二个输入，支持任意类型，启用惰性求值
                "on_true_2": ("*", {"lazy": True}),
                # 条件为假时的第一个输入，支持任意类型，启用惰性求值
                "on_false_1": ("*", {"lazy": True}),
                # 条件为假时的第二个输入，支持任意类型，启用惰性求值
                "on_false_2": ("*", {"lazy": True}),
            }
        }

    # 定义节点的输出类型，支持任意类型，两个输出
    RETURN_TYPES = ("*", "*",)
    # 定义节点的输出名称
    RETURN_NAMES = ("output1", "output2",)
    # 定义节点的主要函数
    FUNCTION = "switch"
    # 节点分类
    CATEGORY = "RelayTyNodes"
    # 节点描述文档
    DESCRIPTION = """
# RT双路惰性开关

## 功能
根据条件值同时选择并输出两组对应的输入。支持惰性求值。

## 输入
- 条件: 条件值（True/False）
- 条件为真①: 条件为真时的第一个输出
- 条件为真②: 条件为真时的第二个输出
- 条件为假①: 条件为假时的第一个输出
- 条件为假②: 条件为假时的第二个输出

## 输出
- 输出①: 根据条件选择的第一个结果
- 输出②: 根据条件选择的第二个结果

## 使用建议
- 需要同时切换多个相关输入的场景，如同时切换图像和蒙版
- 惰性求值特性：只有被选中的输入组才会被计算
- 未被选中的输入组可以为None而不影响执行

## 示例
```
condition=True  → output1=on_true_1, output2=on_true_2
condition=False → output1=on_false_1, output2=on_false_2
```
"""

    def __init__(self):
        super().__init__()

    def check_lazy_status(self, condition, on_true_1, on_true_2, on_false_1, on_false_2):
        """
        检查惰性输入的状态

        用于在执行前验证所需的输入是否已提供，避免运行时错误。

        参数：
            condition (bool): 条件值，决定哪组输入会被使用
            on_true_1: 条件为真时的第一个输入值
            on_true_2: 条件为真时的第二个输入值
            on_false_1: 条件为假时的第一个输入值
            on_false_2: 条件为假时的第二个输入值

        返回值：
            list or None: 未提供的必需输入名称列表，如果所有必需输入都已提供则返回None
        """
        result = []
        if condition:
            if on_true_1 is None:
                result.append("on_true_1")
            if on_true_2 is None:
                result.append("on_true_2")
        else:
            if on_false_1 is None:
                result.append("on_false_1")
            if on_false_2 is None:
                result.append("on_false_2")
        return result if result else None

    def switch(self, condition, on_true_1=None, on_true_2=None, on_false_1=None, on_false_2=None):
        """
        执行条件选择逻辑

        根据condition参数的值，同时返回对应的两组输入值。
        由于使用了惰性求值，未被选中的输入组不会被计算。

        参数：
            condition (bool): 条件值，为True时返回on_true组，为False时返回on_false组
            on_true_1: 条件为真时的第一个输入值（任意类型）
            on_true_2: 条件为真时的第二个输入值（任意类型）
            on_false_1: 条件为假时的第一个输入值（任意类型）
            on_false_2: 条件为假时的第二个输入值（任意类型）

        返回值：
            tuple: 包含两个选择结果的元组 (output1, output2)
        """
        if condition:
            # 条件为真，返回on_true组的两个输入值
            return (on_true_1, on_true_2,)
        else:
            # 条件为假，返回on_false组的两个输入值
            return (on_false_1, on_false_2,)
# endregion