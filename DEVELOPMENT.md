# ComfyUI-RelayTyNodes 开发指南

## 项目概述

本项目是 ComfyUI 的自定义节点扩展库，提供常用的自定义节点功能。

**面向读者**：开发者
**README.md**：用户文档
**CODING_STANDARDS.md**：代码规范

---

## 🔄 节点开发/更新工作流程

当有新节点开发或现有节点更新时，请按照以下流程执行：

### 一、开发前准备

| 步骤 | 内容 | 目的 |
|------|------|------|
| 1 | 查看现有项目结构 | 了解目录组织 |
| 2 | 阅读 `CODING_STANDARDS.md` | 了解代码规范 |
| 3 | 阅读 `DEVELOPMENT.md` | 了解当前状态和待办事项 |
| 4 | 查看 `reference/` 参考资料 | 学习借鉴（只读） |

### 二、开发中

| 步骤 | 内容 | 规范来源 |
|------|------|----------|
| 0 | 检查单一职责 | 节点的 FUNCTION 是否只做一件事？如果用"和/+"描述功能则需拆分。详见 `CODING_STANDARDS.md §5.0` |
| 1 | 遵循命名规范 | 类名使用 `RT_` 前缀，PascalCase |
| 2 | 继承 `RelayNodeBase` | `from ..utils import RelayNodeBase` |
| 3 | 设置 `CATEGORY = "RelayTyNodes"` | 统一分类 |
| 4 | 继承基类自动获得 `aux_id` | 无需手动设置，`RelayNodeBase.__init__` 已统一处理 |
| 5 | 添加 `DESCRIPTION` | Markdown 格式帮助文档 |
| 6 | 添加 `INPUT_TYPES` 的 tooltip | 用户体验 |
| 7 | 遵循导入规范 | 标准库 → 第三方 → 项目内部 |
| 8 | 添加依赖回退机制 | `try-except` 模式处理可选依赖 |
| 9 | 考虑代码复用 | 通用纯函数提取到 `utils/`；添加节点功能到 `nodes/` |
| 10 | 修改 utils 函数时 | **禁止直接修改签名/行为** ← 先查看 `CODING_STANDARDS.md §2.5`，确认调用者注释 |

### 三、开发后

| 步骤 | 内容 | 命令/操作 |
|------|------|-----------|
| 1 | 语法检查 | `python -m py_compile <file>.py` |
| 2 | 基本功能测试 | 在 ComfyUI 中运行节点 |
| 3 | 边界测试 | 空输入、异常值、大数据量 |
| 4 | 性能测试（如适用） | 显存占用、内存泄漏检查 |

### 四、文档更新

| 步骤 | 文件 | 更新内容 |
|------|------|----------|
| 1 | `DEVELOPMENT.md` | **必须** - 添加变更记录到"已完成优化记录"章节 |
| 2 | `README.md` | **必须** - 更新节点列表 |
| 3 | `pyproject.toml` | **必须** - 更新版本号 |
| 4 | `requirements.txt` | **如需要** - 添加新依赖 |
| 5 | `CODING_STANDARDS.md` | **如需要** - 更新项目结构或规范 |

### 五、提交前检查清单

#### 代码规范检查

| 检查项 | 说明 | 状态 |
|--------|------|------|
| 命名规范 | 类名使用 PascalCase，函数名使用 snake_case | ☐ |
| 节点前缀 | 所有节点类名必须以 `RT_` 开头 | ☐ |
| 分类设置 | `CATEGORY = "RelayTyNodes"` | ☐ |
| 返回类型 | `RETURN_TYPES` 与实际返回值一致 | ☐ |
| 函数名 | `FUNCTION` 指定的函数存在且正确 | ☐ |

#### 文档完整性检查

| 检查项 | 说明 | 状态 |
|--------|------|------|
| DESCRIPTION | 添加详细的节点帮助文档（Markdown 格式） | ☐ |
| 参数说明 | 所有输入参数都有 tooltip 说明 | ☐ |
| 输出说明 | 所有输出都有清晰说明 | ☐ |
| 使用示例 | 添加使用场景和示例 | ☐ |

#### 依赖管理检查

| 检查项 | 说明 | 状态 |
|--------|------|------|
| requirements.txt | 添加新依赖到 requirements.txt | ☐ |
| 依赖回退 | 非必需依赖添加 try-except 和回退机制 | ☐ |
| 错误处理 | 添加适当的错误处理和日志记录 | ☐ |

#### 测试检查

| 检查项 | 说明 | 状态 |
|--------|------|------|
| 语法检查 | `python -m py_compile` 通过 | ☐ |
| 基本测试 | 在 ComfyUI 中测试节点是否正常显示 | ☐ |
| 连线测试 | 测试所有输入输出端口是否正常工作 | ☐ |
| 边界测试 | 测试空输入、异常值等边界情况 | ☐ |

#### 版本管理检查

| 检查项 | 说明 | 状态 |
|--------|------|------|
| 版本号更新 | 更新 pyproject.toml 中的版本号 | ☐ |
| 变更日志 | 添加变更说明到 DEVELOPMENT.md | ☐ |
| 节点状态 | 更新节点状态标记 | ☐ |

---

### 六、变更记录格式

在 `DEVELOPMENT.md` 的"已完成优化记录"章节中，使用以下格式：

```markdown
### YYYY-MM-DD

1. **变更标题**
   - 具体变更内容1
   - 具体变更内容2
   - 文件: `affected_file.py`
```

**示例**：

```markdown
### 2026-05-24

1. **RT_ImageBlend 功能增强**
   - 添加 `mask_expand` 参数
   - 添加 `mask_preview` 输出
   - 文件: `blend_nodes.py`
```

---

## 📊 项目状态

### 当前版本
- **版本**: v2.0.0
- **最后更新**: 2026-05-26
- **节点总数**: 22 个

### 健康状态
| 指标 | 状态 | 说明 |
|------|------|------|
| 代码质量 | ✅ 良好 | 无语法错误，代码规范 |
| 测试覆盖 | ⚠️ 部分 | 需要补充单元测试 |
| 文档完整度 | ✅ 良好 | 所有节点都有 DESCRIPTION |
| 依赖管理 | ✅ 良好 | requirements.txt 已更新 |
| 代码一致性 | ✅ 良好 | D004, D005 已修复 |

---

## 📝 待办事项

### 高优先级
| ID | 任务 | 状态 | 负责人 | 备注 |
|----|------|------|--------|------|
| T001 | 简化 RT_ImageBlend 节点 | ✅ 完成 | - | 移除无效功能 |
| T002 | 添加单元测试 | ⏳ 待开始 | - | 核心功能测试 |
| T007 | 清理 color_nodes.py 重复代码 | ✅ 完成 | - | 删除末尾重复的注册代码 |
| T008 | 补充节点 aux_id 属性 | ✅ 完成 | - | RT_MathExpression 等节点 |

### 中优先级
| ID | 任务 | 状态 | 负责人 | 备注 |
|----|------|------|--------|------|
| T003 | 优化 image_nodes.py 性能 | ⏳ 待开始 | - | 参考参考资料 |
| T004 | 添加更多颜色匹配算法 | ⏳ 进行中 | - | 已添加 OkLab/OkLch 算法 |

### 低优先级
| ID | 任务 | 状态 | 负责人 | 备注 |
|----|------|------|--------|------|
| T005 | 添加节点图标 | ⏳ 待开始 | - | 提升UI体验 |
| T006 | 添加节点搜索标签 | ⏳ 待开始 | - | 方便搜索 |

---

## ✅ 已完成优化记录

### 2026-05-24

1. **RT_BlendInpaint 功能增强（第一轮）**
   - 添加 `mask_expand` 可选参数，支持遮罩大小调整
   - 正值向外扩展（膨胀），负值向内收缩（腐蚀）
   - 使用圆形结构元素进行形态学操作
   - 添加 `mask_preview` 输出，在首帧上用红色描边显示遮罩位置
   - 使用 Sobel 边缘检测实现轮廓绘制
   - 更新了类文档字符串和 DESCRIPTION 文档
   - 文件: `blend_nodes.py`

2. **RT_BlendInpaint 功能优化（第一轮）**
   - 移除 MASK 输出，只保留 IMAGE 和 mask_preview 输出
   - 明确处理顺序：先执行 mask_expand 调整遮罩，再用 kernel 和 sigma 羽化
   - 简化了 _blend_inpaint_chunk 方法
   - mask_preview 显示的是调整后的遮罩范围（adjusted_mask）
   - 文件: `blend_nodes.py`

3. **RT_ImageBlend 功能增强（第一轮）**
   - 添加 `mask_expand` 可选参数，支持遮罩大小调整
   - 添加 `mask_preview` 输出，在首帧上用红色描边显示遮罩位置
   - 明确处理顺序：先执行 mask_expand 调整遮罩，再进行 Poisson 融合
   - mask_preview 显示的是调整后的遮罩范围（adjusted_mask）
   - 复用了 _expand_mask 和 _draw_mask_outline 方法
   - 更新了类文档字符串和 DESCRIPTION 文档
   - 文件: `blend_nodes.py`

4. **两个节点功能增强（第二轮）**
   - 参数顺序调整：将功能参数放在设备和性能参数前面
   - 添加 `mask_inner_keep` 参数，支持内遮罩保留区域控制
   - `mask_inner_keep` 大于 0 时，只在遮罩边缘区域进行融合，中间保持原图
   - 更新 `_draw_mask_outline` 方法，支持双轮廓显示：红色外遮罩，蓝色内遮罩
   - 更新了两个节点的文档和类说明
   - 文件: `blend_nodes.py`

5. **RT_BlendInpaint 简化优化**
   - 移除 `mask_inner_keep` 参数，分析后确认该节点不需要此功能
   - 高斯模糊本身自然实现了边缘过渡，无需额外控制
   - 用户可以通过 `kernel` 和 `sigma` 更好地控制融合区域
   - 保留 RT_ImageBlend 中的 `mask_inner_keep`，因为 Poisson 融合需要
   - 文件: `blend_nodes.py`

6. **设备处理全面修复**
   - 将共享方法 `expand_mask` 和 `draw_mask_outline` 移到类外，两个节点都能调用
   - 在两个节点的核心函数开头统一将所有输入张量移动到目标设备
   - 简化函数调用，移除冗余的 `.to(device)` 操作
   - 确保所有运算都在同一设备上进行，避免 cuda 和 cpu 混合的错误
   - 文件: `blend_nodes.py`

7. **卷积核设备一致性修复**
   - `draw_mask_outline`: 使用 `mask_bin.device` 动态创建 sobel 卷积核
   - `expand_mask`: 使用 `mask.device` 创建圆形结构元素
   - 移除 `expand_mask` 函数的冗余 `device` 参数
   - 更新所有调用位置
   - 文件: `blend_nodes.py`

8. **进度条优化**
   - 移除了 `logging.info()` 输出的进度信息
   - 保留 `comfy.utils.ProgressBar` UI 进度条
   - 两个节点现在都只使用 ComfyUI 原生进度条显示处理进度
   - 文件: `blend_nodes.py`

9. **双重进度条实现**
   - 学习 ComfyUI-WanAnimatePreprocess 的进度条实现方式
   - 为所有使用进度条的节点添加 ProgressBar + tqdm 双重进度条模式
   - blend_nodes.py: RT_ImageBlend 和 RT_BlendInpaint 两个节点添加 tqdm 支持
   - color_nodes.py: RT_ColorMatch 节点添加 tqdm 支持
   - 同时在 ComfyUI 界面和控制台显示进度条
   - 确保向后兼容：如果 tqdm 未安装，自动降级到仅使用 ProgressBar

10. **全节点检查**
   - 检查了所有 22 个节点的质量和规范性
   - 发现问题：color_nodes.py 末尾有重复的 NODE_CLASS_MAPPINGS 注册代码（与 nodes/__init__.py 重复）
   - 发现问题：部分节点缺少 aux_id 属性设置（RT_MathExpression, RT_JoinStringMulti, RT_JoinStrings 等）
   - 整体评估：命名规范 ✅，分类设置 ✅，文档完整 ✅，依赖处理 ✅

11. **代码一致性问题修复**
    - D004: 清理 color_nodes.py 末尾重复的 NODE_CLASS_MAPPINGS 和 NODE_DISPLAY_NAME_MAPPINGS
    - D005: 为 RT_MathExpression、RT_JoinStringMulti、RT_JoinStrings 添加 __init__ 方法和 aux_id 属性
    - 文件: color_nodes.py, math_nodes.py, string_nodes.py

12. **项目结构优化**
    - 创建 utils/math_utils.py，将 math_nodes.py 中的 safe_* 函数提取出来
    - 提取的函数：safe_sqrt, safe_log, safe_log10, safe_div, safe_floordiv, safe_mod
    - 更新 utils/__init__.py，导出 math_utils 模块的函数
    - 更新 math_nodes.py，使用新的导入路径
    - 优化目的：提高代码复用性，未来其他节点可以使用这些数学工具
    - 文件: utils/math_utils.py, nodes/math_nodes.py, utils/__init__.py
    - 相关文档：更新 CODING_STANDARDS.md 和 DEVELOPMENT.md，记录新的项目结构
    - 语法验证：已验证所有修改文件的语法正确性

13. **RT_ColorMatch 代码优化**
    - 修复发现的问题：
      - 移除未使用的 `gc` 导入
      - 移除模块级 `logging.basicConfig`，改用 `logger = logging.getLogger()`
      - 添加 `__init__` 方法和 `aux_id` 属性
      - 添加 `_xyz_white_point` 类属性避免重复创建
      - 修改变量命名 `b_val` 为 `b_rgb`
      - 更新所有 `logging.*` 调用为 `logger.*`
    - 联网搜索先进的颜色匹配算法
    - 添加 OkLab 颜色空间支持（感知均匀，比 CIE Lab 更好）：
      - 添加 `_rgb_to_oklab` 方法：RGB 转 OkLab
      - 添加 `_oklab_to_rgb` 方法：OkLab 转 RGB
      - 添加 `_oklab_to_oklch` 方法：OkLab 转 OkLch（极坐标形式）
      - 添加 `_oklch_to_oklab` 方法：OkLch 转 OkLab
      - 添加 `_reinhard_oklab_gpu` 方法：OkLab 空间的 Reinhard 颜色匹配
      - 添加 `_reinhard_oklch_gpu` 方法：OkLch 空间的 Reinhard（保持色相）
    - 新增两种算法选项：
      - `reinhard_oklab`: OkLab 空间 Reinhard，感知均匀，效果更好
      - `reinhard_oklch`: OkLch 空间 Reinhard，保持原图色相不变
    - 更新 INPUT_TYPES 添加新算法选项
    - 更新 DESCRIPTION 添加新算法说明
    - 文件: nodes/color_nodes.py
    - 语法验证：已验证所有修改文件的语法正确性

14. **blend_nodes.py 代码质量修复**
    - 移除未使用的 `gc` 导入
    - 移除模块级 `logging.basicConfig`，改用 `logger = logging.getLogger("RT_ImageBlend")`
    - 为 `RT_ImageBlend` 添加 `__init__` 方法和 `aux_id` 属性
    - 为 `RT_BlendInpaint` 添加 `__init__` 方法和 `aux_id` 属性
    - 更新所有 `logging.*` 调用为 `logger.*`
    - **重要 bug 修复**：修复内部遮罩逻辑错误（`torch.where` 条件反了）
      - 现在 `inner_mask_gpu > 0` 时正确使用 `inpaint` 填充
    - 文件: nodes/blend_nodes.py
    - 语法验证：已验证所有修改文件的语法正确性

15. **blend_nodes.py 简化输出和修复 bug**
    - 修复 Poisson 融合的维度错误（`_poisson_composite_chunk` 中 `unsqueeze(1)` 导致 5 维张量问题）
    - 移除 RT_ImageBlend 的额外输出（`mask_preview`、`adjusted_mask`）
    - 移除 RT_BlendInpaint 的额外输出（`mask_preview`、`adjusted_mask`）
    - 移除 `draw_mask_outline` 未使用的导入
    - 两个节点现在都只输出融合后的图像
    - 文件: nodes/blend_nodes.py
    - 语法验证：已验证所有修改文件的语法正确性

16. **RT_ImageBlend Poisson 融合算法升级**
    - 完全按照参考实现重新实现标准的 Poisson Image Editing (Pérez et al. 2003)
    - 使用标准公式：ΔV = ΔS inside Ω; V = D on ∂Ω
    - 添加三个辅助方法：_shift_img, _shift_mask, _laplacian
    - 使用复制边界填充（replicate padding），避免边界伪影
    - 使用正确的 Jacobi 迭代更新：V_new = (sumN + lap) / 4.0
    - 移除 mask_inner_keep 参数（简化参数，保留核心功能）
    - 文件: nodes/blend_nodes.py
    - 语法验证：已验证所有修改文件的语法正确性

17. **RT_ImageBlend 功能优化**
    - 移除局部颜色匹配功能
    - 恢复使用内遮罩方案（mask_inner_keep）
    - 修改处理顺序：先将 inpaint 的内遮罩部分替换至 original 对应区域，然后再进行 Poisson 融合
    - 文件: nodes/blend_nodes.py
    - 语法验证：已验证所有修改文件的语法正确性

18. **MaskProcessor 优化**
    - 移除 GPU 全量处理策略，只保留 GPU 分块处理和 CPU 处理
    - 添加 CPU 多线程处理支持（支持 `cpu_workers` 参数）
    - 使用 `ThreadPoolExecutor` 并行处理多个 batch
    - 更新文档和注释
    - 文件: core/mask_processor.py
    - 语法验证：已验证所有修改文件的语法正确性

### 2026-05-22

1. **更新 requirements.txt**
   - 添加 `opencv-python` 和 `kornia` 依赖
   - 文件: `requirements.txt`

2. **mask_nodes.py 优化**
   - 添加 scipy 依赖检查和回退机制
   - 添加 OpenCV 依赖检查和回退机制
   - 更新节点 DESCRIPTION 添加依赖说明

3. **bbox_nodes.py 优化**
   - 添加 scipy 依赖检查和回退机制
   - 更新节点 DESCRIPTION 添加依赖说明

4. **color_nodes.py 优化**
   - 已支持 ComfyUI 原生 ProgressBar
   - 已支持 GPU/CPU 自动切换
   - 已支持显存不足自动降级

5. **blend_nodes.py 注释优化**
   - 优化 RT_ImageBlend 类文档字符串，添加核心特性、适用场景、技术原理和使用建议
   - 优化 RT_BlendInpaint 类文档字符串，添加核心特性、适用场景、技术原理和使用建议
   - 为 _advanced_color_match、_blend_inpaint、_blend_inpaint_chunk 等方法添加详细注释

6. **所有节点注释检查**
   - 检查了所有节点文件的注释情况
   - 确认所有节点都有必要的类文档字符串、INPUT_TYPES 注释、DESCRIPTION 文档
   - 确认所有核心方法都有清晰的注释说明

---

## 📋 技术债务清单

| ID | 问题 | 影响 | 计划修复 |
|----|------|------|----------|
| D001 | RT_ImageBlend 功能复杂效果不佳 | 用户体验 | ✅ 已修复 |
| D002 | 缺少单元测试 | 代码质量 | T002 |
| D003 | 部分算法未使用 GPU 加速 | 性能 | T003 |
| D004 | color_nodes.py 末尾重复注册代码 | 维护性 | ✅ 已修复 |
| D005 | 部分节点缺少 aux_id 属性 | 追踪性 | ✅ 已修复 |

---

## 节点列表

本项目包含 **22 个自定义节点**：

### 开关节点 (2个)
| 类名 | 显示名称 | 文件 | 状态 |
|------|----------|------|------|
| RT_LazySwitch | RT惰性开关 | switch_nodes.py | ✅ 稳定 |
| RT_LazySwitch2way | RT双路惰性开关 | switch_nodes.py | ✅ 稳定 |

### 工具节点 (3个)
| 类名 | 显示名称 | 文件 | 状态 |
|------|----------|------|------|
| RT_ResolutionSelector | RT分辨率选择器 | tool_nodes.py | ✅ 稳定 |
| RT_AspectRatioSelector | RT比例选择器 | tool_nodes.py | ✅ 稳定 |
| RT_AspectRatioDetector | RT比例检测器 | tool_nodes.py | ✅ 稳定 |

### 遮罩处理节点 (9个)
| 类名 | 显示名称 | 文件 | 状态 |
|------|----------|------|------|
| RT_MaskExpand | RT遮罩扩展/收缩 | nodes_debug.py | ⚠️ 调试中 |
| RT_MaskFeather | RT遮罩高斯羽化 | nodes_debug.py | ⚠️ 调试中 |
| RT_SeparateMasks | RT遮罩分离 | nodes_debug.py | ⚠️ 需要 scipy |
| RT_GetTrack | RT获取Track | nodes_debug.py | ✅ 稳定 |
| RT_BatchMask | RT复制遮罩批次 | nodes_debug.py | ✅ 稳定 |
| RT_GetMaskFromBatch | RT从批次获取遮罩 | nodes_debug.py | ✅ 稳定 |
| RT_ImageToMask | RT图像通道转遮罩 | mask_nodes.py | ✅ 稳定 |
| RT_MaskToImage | RT遮罩转图像 | nodes_debug.py | ⚠️ 调试中 |
| RT_MaskContour | RT遮罩描边 | mask_draw_nodes.py | ⚠️ 需要 OpenCV |
| RT_DrawMaskOnImage | RT遮罩绘制 | mask_draw_nodes.py | ✅ 稳定 |
| RT_BBoxToMask | RTBBox转遮罩 | bbox_nodes.py | ⚠️ 需要 scipy |

### 字符串处理节点 (2个)
| 类名 | 显示名称 | 文件 | 状态 |
|------|----------|------|------|
| RT_JoinStringMulti | RT多字符串连接 | string_nodes.py | ✅ 稳定 |
| RT_JoinStrings | RT双字符串连接 | string_nodes.py | ✅ 稳定 |

### 数学表达式节点 (1个)
| 类名 | 显示名称 | 文件 | 状态 |
|------|----------|------|------|
| RT_MathExpression | RT数学表达式 | math_nodes.py | ✅ 稳定 |

### 颜色匹配节点 (1个)
| 类名 | 显示名称 | 文件 | 状态 |
|------|----------|------|------|
| RT_ColorMatch | RT颜色匹配 | color_nodes.py | ✅ 稳定 |

### 图像融合节点 (2个)
| 类名 | 显示名称 | 文件 | 状态 |
|------|----------|------|------|
| RT_ImageBlend | RT图像融合 | image_nodes.py | ⚠️ 开发中 |
| RT_BlendInpaint | RT遮罩羽化混合 | image_nodes.py | ✅ 稳定 |

---

## 项目结构

```
ComfyUI-RelayTyNodes/
├── __init__.py              # 节点库入口
├── utils/                   # 工具函数（10 个文件，纯函数 + 基类）
│   ├── __init__.py          # 统一导出（24 个公开符号）
│   ├── base.py              # RelayNodeBase 节点基类
│   ├── common.py            # AnyType, any, get_input_type, parse_color_str
│   ├── device_utils.py      # select_device 设备选择
│   ├── image_utils.py       # resize_images_batch, rgb_to_hsv
│   ├── mask_utils.py        # resize_masks_batch, expand_mask, gaussian_blur_mask,
│   │                          extract_channel, apply_levels
│   ├── gpu_utils.py         # ★ adaptive_process（GPU/CPU 自适应核心）
│   ├── bbox_utils.py        # bbox_to_mask
│   ├── diagnostics.py       # get_memory_info
│   └── math_utils.py        # safe_sqrt, safe_log, safe_div 等
├── nodes/                   # 节点实现（11 个文件，继承 RelayNodeBase）
│   ├── __init__.py          # 节点注册（NODE_CLASS_MAPPINGS）
│   ├── switch_nodes.py      # 开关类节点
│   ├── tool_nodes.py        # 工具类节点
│   ├── mask_nodes.py        # RT_ImageToMask
│   ├── nodes_debug.py       # ★ RT_MaskExpand, RT_MaskFeather, RT_SeparateMasks,
│   │                          RT_GetTrack, RT_BatchMask, RT_GetMaskFromBatch, RT_MaskToImage
│   ├── mask_draw_nodes.py   # 遮罩绘制节点
│   ├── bbox_nodes.py        # BBox处理节点
│   ├── string_nodes.py      # 字符串处理节点
│   ├── math_nodes.py        # 数学表达式节点
│   ├── color_nodes.py       # 颜色匹配节点
│   └── image_nodes.py       # 图像融合节点
├── tests/                   # 测试文件
│   └── ...
├── example_workflows/       # 示例工作流（.json）
├── web/
│   └── js/                 # 前端资源
│       ├── help_popup.js    # 帮助弹窗
│       ├── math_nodes.js    # 数学节点前端
│       ├── setgetnodes.js   # Set/Get节点前端
│       └── string_nodes.js  # 字符串节点前端
├── README.md               # 用户文档
├── DEVELOPMENT.md          # 开发者文档
├── CODING_STANDARDS.md     # 代码规范
├── LICENSE
├── .gitignore
├── pyproject.toml
└── requirements.txt         # Python依赖

# 本地目录（已忽略，不纳入版本控制）
└── reference/               # 参考学习资料（只读，禁止修改）
```

### 目录说明

| 目录 | 说明 |
|------|------|
| `core/` | 核心处理器，包含可复用的处理类 |
| `utils/` | 工具函数，包含无状态的工具函数和基础类 |
| `nodes/` | 节点实现，继承 RelayNodeBase 的节点类 |
| `tests/` | 测试文件 |
| `web/js/` | 前端 JavaScript 资源 |
| `reference/` | **参考资料目录**，从外部学习借鉴的代码/文档，**只读，禁止修改** |

---

## 节点规范

### 命名规范

| 规范 | 说明 |
|------|------|
| 节点前缀 | `RT_`（所有节点必须以此开头） |
| 分类名称 | `RelayTyNodes`（在 ComfyUI 菜单中显示的分类） |
| 类名格式 | `PascalCase`（如 `RT_LazySwitch`） |
| 函数名 | `snake_case`（如 `switch`, `select`） |
| 显示名称 | `RT中文名称`（如 `RT惰性开关`） |

### 文件命名规范

| 类型 | 规范 |
|------|------|
| 后端节点文件 | `switch_nodes.py`、`tool_nodes.py`（不使用 rt_ 前缀） |
| 前端文件 | `web/js/*.js`（不使用 rt_ 前缀） |

---

## 节点开发

### 节点分类

所有节点统一分类为 `RelayTyNodes`，在 ComfyUI 中显示在该分类下。

### 节点类型说明

| 类型 | 说明 |
|------|------|
| `required` | 必需输入参数（必须连线才能执行） |
| `optional` | 可选输入参数（可以为空或不连线） |
| `hidden` | 隐藏参数（如模型路径、prompt 等） |

### 常用返回类型

| 类型 | 说明 |
|------|------|
| `*` | 任意类型（AnyType，惰性求值） |
| `STRING` | 字符串 |
| `INT` | 整数 |
| `FLOAT` | 浮点数 |
| `BOOLEAN` | 布尔值 |
| `IMAGE` | 图像张量 |
| `MASK` | 遮罩张量 |
| `BBOX` | 边界框 |

### 节点关键属性

| 属性 | 说明 |
|------|------|
| `INPUT_TYPES` | 定义节点的输入参数 |
| `RETURN_TYPES` | 定义节点的输出类型 |
| `FUNCTION` | 节点的主函数名 |
| `CATEGORY` | 节点分类（固定为 `RelayTyNodes`） |
| `DESCRIPTION` | 节点帮助文档（Markdown 格式） |
| `OUTPUT_NODE` | 是否为输出节点（用于 UI 显示） |

### 关键文件说明

#### utils/ - 工具函数目录

包含基础类和工具函数（10 个文件，纯函数 + 基类）：

- `utils/base.py`: `RelayNodeBase` 基类，所有节点需继承此类
- `utils/gpu_utils.py`: ★ `adaptive_process` GPU/CPU 自适应处理核心入口
- `utils/mask_utils.py`: 遮罩处理纯函数（expand_mask, gaussian_blur_mask, extract_channel, apply_levels 等）
- `utils/image_utils.py`: 图像处理工具函数（resize_images_batch, rgb_to_hsv）
- `utils/common.py`: 通用工具函数（AnyType, any, get_input_type, parse_color_str）
- `utils/bbox_utils.py`: BBox→Mask 转换函数
- `utils/device_utils.py`: 设备选择函数
- `utils/diagnostics.py`: GPU 显存诊断函数
- `utils/math_utils.py`: 安全数学工具函数

```python
from ..utils import RelayNodeBase, adaptive_process, expand_mask

class RT_MyNode(RelayNodeBase):
    ...
```

#### tests/ - 测试文件目录

包含测试脚本：

- `tests/test_blend.py`: 混合节点测试
- `tests/test_blend_simple.py`: 简单混合测试

#### nodes/*.py - 节点实现

每个节点文件包含一类相关节点，如 `switch_nodes.py` 包含开关类节点。

#### nodes/__init__.py - 节点注册

```python
from .switch_nodes import RT_LazySwitch, RT_LazySwitch2way
# ... 其他导入

NODE_CLASS_MAPPINGS = {
    "RT_LazySwitch": RT_LazySwitch,
    # ...
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RT_LazySwitch": "RT惰性开关",
    # ...
}
```

#### __init__.py - 入口文件

```python
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
WEB_DIRECTORY = "web"
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
```

---

## 帮助文档系统

### 添加 DESCRIPTION

每个节点都可以添加 `DESCRIPTION` 属性来提供帮助文档。

```python
DESCRIPTION = """
# 节点名称

## 功能说明
这里是节点的功能描述。

## 输入参数
- param1: 参数1说明
- param2: 参数2说明

## 输出
- output: 输出说明

## 示例
示例用法说明。
"""
```

### 帮助弹窗实现

帮助弹窗功能通过 `web/js/help_popup.js` 实现。

**特性**：
- 自动为所有 `RelayTyNodes` 分类的节点添加帮助按钮
- 支持 Markdown 格式渲染
- 绿色问号图标（`#4ade80`）
- 支持 Legacy Canvas 和 Vue 两种节点模式

---

## 高级特性

### AnyType 任意类型

使用 `AnyType` 可以创建接受任意类型输入的端口。

```python
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any = AnyType("*")

INPUT_TYPES = {
    "optional": {
        "x1": (any, {"forceInput": True}),
    }
}
```

### forceInput 属性

`forceInput: True` 表示该输入**必须连线**，不会显示输入框。

`forceInput: False` 或不设置表示该输入可以**不连线**，会显示输入框。

### OUTPUT_NODE 输出节点

设置 `OUTPUT_NODE = True` 可以让节点在 UI 上直接显示计算结果。

```python
OUTPUT_NODE = True

def evaluate(self, ...):
    return {
        "ui": {"value": [result]},  # UI 显示的值
        "result": (int_result, float_result),  # 实际输出
    }
```

### 动态输入端口

通过 JavaScript 可以动态添加/删除输入端口。

```javascript
// web/js/math_nodes.js
self.addInput(`x${i}`, "*", {shape: 7});  // 添加输入端口
self.removeInput(self.inputs.length - 1);   // 删除最后一个输入端口
```

---

## 调试技巧

### 常见问题排查

1. **节点未显示**
   - 检查 `__init__.py` 是否正确导出
   - 检查 `nodes/__init__.py` 的导入路径
   - 检查 `NODE_CLASS_MAPPINGS` 是否包含所有节点

2. **导入错误**
   - 确认节点类已正确导入到 `nodes/__init__.py`
   - 确认 `from ..utils import RelayNodeBase` 路径正确（指向 `utils/` 目录）

3. **类型错误**
   - 检查 `INPUT_TYPES` 和 `RETURN_TYPES` 格式
   - 确认返回值的数量和类型与 `RETURN_TYPES` 一致

4. **动态端口不工作**
   - 检查 JavaScript 文件是否在 `WEB_DIRECTORY` 目录下
   - 检查 `app.registerExtension` 是否正确注册

### 测试流程

1. 启动 ComfyUI
2. 在节点搜索中输入 `RT_` 查看节点
3. 连接节点并执行工作流
4. 检查输出是否符合预期

---

## Git 协作流程

### 分支命名

- `feature/xxx`：新功能
- `fix/xxx`：修复 bug
- `refactor/xxx`：重构

### 提交规范

```
<type>: <subject>
<body>
```

Type 类型：feat / fix / docs / style / refactor / test / chore

---

## 参考资源

- [ComfyUI 官方仓库](https://github.com/comfyanonymous/ComfyUI)
- [本项目仓库](https://github.com/relay-ty/ComfyUI-RelayTyNodes)
- `reference/` 文件夹中的学习资料

---

## ✅ 节点开发后检查清单

### 1. 代码检查
| 检查项 | 说明 | 状态 |
|--------|------|------|
| 命名规范 | 类名使用 PascalCase，函数名使用 snake_case | ☐ |
| 节点前缀 | 所有节点类名必须以 `RT_` 开头 | ☐ |
| 分类设置 | `CATEGORY = "RelayTyNodes"` | ☐ |
| 返回类型 | `RETURN_TYPES` 与实际返回值一致 | ☐ |
| 函数名 | `FUNCTION` 指定的函数存在且正确 | ☐ |

### 2. 文档检查
| 检查项 | 说明 | 状态 |
|--------|------|------|
| DESCRIPTION | 添加详细的节点帮助文档（Markdown格式） | ☐ |
| 参数说明 | 所有输入参数都有 tooltip 说明 | ☐ |
| 输出说明 | 所有输出都有清晰说明 | ☐ |
| 使用示例 | 添加使用场景和示例 | ☐ |

### 3. 依赖检查
| 检查项 | 说明 | 状态 |
|--------|------|------|
| requirements.txt | 添加新依赖到 requirements.txt | ☐ |
| 依赖回退 | 非必需依赖添加 try-except 和回退机制 | ☐ |
| 错误处理 | 添加适当的错误处理和日志记录 | ☐ |

### 4. 测试检查
| 检查项 | 说明 | 状态 |
|--------|------|------|
| 基本测试 | 在 ComfyUI 中测试节点是否正常显示 | ☐ |
| 连线测试 | 测试所有输入输出端口是否正常工作 | ☐ |
| 边界测试 | 测试空输入、异常值等边界情况 | ☐ |
| 性能测试 | 测试大数据量处理是否会导致 OOM | ☐ |

### 5. 文档更新
| 检查项 | 说明 | 状态 |
|--------|------|------|
| README.md | 更新节点列表和说明 | ☐ |
| DEVELOPMENT.md | 更新待办事项和项目状态 | ☐ |
| 节点状态 | 更新节点状态标记（✅稳定 / ⚠️需要依赖 / 🚧进行中） | ☐ |

### 6. 版本管理
| 检查项 | 说明 | 状态 |
|--------|------|------|
| 版本号更新 | 更新 pyproject.toml 中的版本号 | ☐ |
| 变更日志 | 添加变更说明到待办事项 | ☐ |

---

## 🔌 前后端配合节点指南

本项目中有一些节点需要前后端配合工作，以下是详细说明。

### 节点类型分类

#### 类型 1: 纯后端节点
多数节点属于此类，不需要前端 JavaScript 代码。
- 例子: RT_LazySwitch, RT_ResolutionSelector 等
- 特点: 仅需 Python 后端代码

#### 类型 2: 后端 + 前端动态UI
需要前后端配合，前端动态管理输入端口。
- 例子: RT_MathExpression, RT_JoinStringMulti
- 特点: 前端动态增删端口，后端用 **kwargs 接收所有输入

#### 类型 3: 纯前端虚拟节点
不需要后端 Python 代码，完全在前端实现。
- 例子: RT_GetNode
- 特点: 使用 LiteGraph.registerNodeType 直接在前端注册

---

### 详细节点说明

#### RT_MathExpression - 数学表达式节点

**文件位置**:
- 后端: `nodes/math_nodes.py`
- 前端: `web/js/math_nodes.js`

**配合流程**:
```
1. 后端 INPUT_TYPES 定义
   - inputcount: 控制输入数量 (1-100)
   - 默认 x1, x2, x3 三个输入
   - forceInput: True 强制显示为端口

2. 前端动态管理
   - 用户修改 inputcount widget
   - 点击 "Update inputs" 按钮
   - addInput() / removeInput() 增删 xN 端口

3. 后端接收处理
   - evaluate() 使用 **kwargs 接收所有输入
   - 根据 inputcount 遍历 x1 ~ xN
   - 支持任意类型输入
```

**关键代码**:
```python
# 后端接收
def evaluate(self, inputcount, expression, **kwargs):
    for i in range(1, inputcount + 1):
        var_name = f"x{i}"
        variables[var_name] = kwargs.get(var_name, 0.0)
```

```javascript
// 前端动态管理
self.addWidget("button", "Update inputs", null, () => {
    const numInputs = self.inputs.filter(input =>
        input.name && input.name.startsWith("x")
    ).length;
    
    if (targetCount < numInputs) {
        // 删除多余端口
        for (let i = 0; i < numInputs - targetCount; i++) {
            self.removeInput(self.inputs.length - 1);
        }
    } else {
        // 添加新端口
        for (let i = numInputs + 1; i <= targetCount; i++) {
            self.addInput(`x${i}`, "*", {shape: 7});
        }
    }
});
```

---

#### RT_JoinStringMulti - 多字符串连接节点

**文件位置**:
- 后端: `nodes/string_nodes.py`
- 前端: `web/js/string_nodes.js`

**配合流程**:
```
1. 后端 INPUT_TYPES 定义
   - inputcount: 控制输入数量 (2-1000)
   - 默认 string_1, string_2 两个输入
   - forceInput: True 强制显示为端口

2. 前端动态管理
   - 与 RT_MathExpression 相同架构
   - addInput() / removeInput() 增删 string_N 端口

3. 后端接收处理
   - combine() 使用 **kwargs 接收所有输入
   - 根据 inputcount 遍历 string_1 ~ string_N
```

**关键代码**:
```python
# 后端接收
def combine(self, inputcount, delimiter=" ", **kwargs):
    for c in range(1, inputcount + 1):
        text = kwargs.get(f"string_{c}", "")
        strings.append(text)
```

---

#### RT_GetNode - 获取节点值（纯前端虚拟节点）

**文件位置**:
- 前端: `web/js/setgetnodes.js`
- 后端: ❌ 不需要

**特点**:
- 纯前端虚拟节点
- 使用 LiteGraph.registerNodeType 直接注册
- 跨子图搜索 KJNodes SetNode
- 支持 Go to setter 跳转功能

**注册方式**:
```javascript
app.registerExtension({
    name: "RelayTyNodes.GetNode",
    
    registerCustomNodes() {
        class GetNode extends LGraphNode {
            static title = "RT_GetNode";
            static category = "RelayTyNodes";
            // ...
        }
        LiteGraph.registerNodeType("RT_GetNode", GetNode);
    }
});
```

**注意**: RT_GetNode 在 nodes/__init__.py 中不需要注册。

---

### 前后端配合开发最佳实践

#### 模式 1: 动态端口节点（推荐架构）

**后端**:
```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "inputcount": ("INT", {"default": 2, "min": 1, "max": 100}),
        },
        "optional": {
            "param_1": ("TYPE", {"forceInput": True}),  # 默认几个
            "param_2": ("TYPE", {"forceInput": True}),
        }
    }

def execute(self, inputcount, **kwargs):
    for i in range(1, inputcount + 1):
        value = kwargs.get(f"param_{i}", default)
```

**前端**:
```javascript
const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
nodeType.prototype.onNodeCreated = function() {
    originalOnNodeCreated.apply(this, arguments);
    
    setTimeout(() => {
        this.addWidget("button", "Update inputs", null, () => {
            // 动态添加/删除端口
        });
    }, 0);
};
```

#### 模式 2: 纯前端虚拟节点

- 使用 LiteGraph.registerNodeType
- 不需要在 nodes/__init__.py 中注册
- 适合跨节点引用、工具类功能

---

### 常见问题排查

1. **动态端口不显示**
   - 检查 JavaScript 文件是否在 web/js/ 下
   - 检查 WEB_DIRECTORY = "web" 是否在 __init__.py 中
   - 检查 app.registerExtension 是否正确

2. **后端收不到参数**
   - 确认参数名称前后端一致
   - 确认使用 **kwargs 接收
   - 确认 inputcount 范围正确

3. **纯前端节点不显示**
   - 确认不在 nodes/__init__.py 中重复注册
   - 检查 LiteGraph.registerNodeType 调用

---

## 📦 发布流程

1. 更新版本号（pyproject.toml）
2. 确保所有测试通过
3. 更新 DEVELOPMENT.md 中的项目状态
4. 更新 README.md 中的节点信息
5. 创建 Git tag
6. 推送并创建 Release
