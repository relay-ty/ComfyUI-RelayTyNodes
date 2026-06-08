"""
ComfyUI-RelayTyNodes 节点库入口点

此模块是 ComfyUI-RelayTyNodes 扩展的主入口，负责：
1. 导出节点类映射（NODE_CLASS_MAPPINGS）
2. 导出节点显示名称映射（NODE_DISPLAY_NAME_MAPPINGS）
3. 定义前端扩展目录（WEB_DIRECTORY）

ComfyUI 加载流程：
1. ComfyUI 扫描 custom_nodes 目录
2. 导入各扩展的 __init__.py
3. 通过 NODE_CLASS_MAPPINGS 注册节点类
4. 通过 NODE_DISPLAY_NAME_MAPPINGS 获取节点显示名称
5. 加载 WEB_DIRECTORY 中的前端资源

项目仓库：https://github.com/relay-ty/ComfyUI-RelayTyNodes
"""

# 从 nodes 模块导入节点类映射和显示名称映射
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# 定义前端扩展目录，指向 web 文件夹
# ComfyUI 会自动加载此目录下的 JavaScript 和 CSS 文件
WEB_DIRECTORY = "web"

# 定义模块导出的内容
# 确保 ComfyUI 能够正确识别和加载节点
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']