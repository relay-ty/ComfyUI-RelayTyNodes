"""
诊断工具模块

此模块包含用于性能监控和调试的诊断工具。

核心功能：
- get_memory_info: 获取当前GPU显存使用情况
"""

import torch


# ── 调用者 ──
#   (暂无节点直接引用，诊断工具函数，可通过 utils.get_memory_info 调用)
# ⚠️ 修改签名/行为前注意：未来可能有节点引用此函数
def get_memory_info() -> str:
    """
    获取当前GPU显存使用情况

    返回值：
        str: 包含显存信息的字符串，如果没有GPU则返回"CPU mode"
    """
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024 ** 3
        reserved = torch.cuda.memory_reserved() / 1024 ** 3
        max_allocated = torch.cuda.max_memory_allocated() / 1024 ** 3
        return f"Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB, Peak: {max_allocated:.2f}GB"
    return "CPU mode"


__all__ = [
    "get_memory_info",
]