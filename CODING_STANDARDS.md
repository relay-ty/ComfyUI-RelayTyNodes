# ComfyUI-RelayTyNodes 代码规范

## 1. 项目结构

```
ComfyUI-RelayTyNodes/
├── utils/                   # 工具函数目录（10 个文件，纯函数 + 基类）
│   ├── __init__.py          # 统一导出（24 个公开符号）
│   ├── base.py              # RelayNodeBase 节点基类
│   ├── common.py            # AnyType, any, get_input_type, parse_color_str
│   ├── device_utils.py      # select_device 设备选择
│   ├── image_utils.py       # resize_images_batch, rgb_to_hsv
│   ├── mask_utils.py        # resize_masks_batch, draw_mask_outline,
│   │                          expand_mask, gaussian_blur_mask,
│   │                          extract_channel, apply_levels
│   ├── gpu_utils.py         # ★ adaptive_process（GPU/CPU 自适应核心）
│   ├── bbox_utils.py        # bbox_to_mask
│   ├── diagnostics.py       # get_memory_info
│   └── math_utils.py        # safe_sqrt, safe_log, safe_div 等
├── nodes/                   # 节点实现（11 个文件，继承 RelayNodeBase）
│   ├── __init__.py          # 节点注册（NODE_CLASS_MAPPINGS）
│   ├── mask_nodes.py        # RT_ImageToMask
│   ├── nodes_debug.py       # ★ RT_MaskExpand, RT_MaskFeather, RT_SeparateMasks,
│   │                          RT_GetTrack, RT_BatchMask, RT_GetMaskFromBatch, RT_MaskToImage
│   ├── bbox_nodes.py        # RT_BBoxToMask
│   ├── mask_draw_nodes.py   # RT_MaskContour, RT_DrawMaskOnImage
│   ├── image_nodes.py       # RT_PoissonBlend, RT_BlendInpaint
│   ├── color_nodes.py       # RT_ColorMatch
│   ├── switch_nodes.py      # RT_LazySwitch, RT_LazySwitch2way
│   ├── tool_nodes.py        # RT_ResolutionSelector, RT_AspectRatioSelector, RT_AspectRatioDetector
│   ├── math_nodes.py        # RT_MathExpression
│   └── string_nodes.py      # RT_JoinStringMulti, RT_JoinStrings
├── web/js/                  # 前端扩展（4 个 .js）
├── reference/               # 外部参考资料（只读，不参与构建）
├── requirements.txt
├── CODING_STANDARDS.md
├── DEVELOPMENT.md
└── README.md
```

## 2. 模块职责划分

### 2.1 utils/ — 工具层（底层，零内部依赖）

| 文件 | 职责 | 导出 |
|------|------|------|
| `base.py` | 节点基类，统一 CATEGORY + properties | `RelayNodeBase` |
| `common.py` | 通用类型和工具 | `AnyType`, `any`, `get_input_type`, `parse_color_str` |
| `device_utils.py` | 设备选择 | `select_device` |
| `image_utils.py` | 图像处理 | `resize_images_batch`, `rgb_to_hsv` |
| `mask_utils.py` | 遮罩处理算法 | `resize_masks_batch`, `draw_mask_outline`, `expand_mask`, `gaussian_blur_mask`, `extract_channel`, `apply_levels` |
| `gpu_utils.py` | ★ GPU/CPU 自适应处理核心 | `adaptive_process`（含 `_create_progress_bars` 内部供 bbox_utils 复用） |
| `bbox_utils.py` | BBox → Mask 转换 | `bbox_to_mask` |
| `diagnostics.py` | 诊断工具 | `get_memory_info` |
| `math_utils.py` | 安全数学工具 | `safe_sqrt`, `safe_log`, `safe_log10`, `safe_div`, `safe_floordiv`, `safe_mod` |

**放置原则**：
- 纯函数（无状态，相同输入必然相同输出）
- 不感知 nodes/ 层
- 可独立测试和复用

### 2.2 nodes/ — 节点层（顶层）

| 文件 | 职责 | 节点 |
|------|------|------|
| `mask_nodes.py` | 图像通道 → 遮罩提取 | `RT_ImageToMask` |
| `nodes_debug.py` | ★ 遮罩操作（调试中） | `RT_MaskExpand`, `RT_MaskFeather`, `RT_SeparateMasks`, `RT_GetTrack`, `RT_BatchMask`, `RT_GetMaskFromBatch`, `RT_MaskToImage` |
| `bbox_nodes.py` | BBox → Mask | `RT_BBoxToMask` |
| `mask_draw_nodes.py` | 遮罩可视化绘制 | `RT_MaskContour`, `RT_DrawMaskOnImage` |
| `image_nodes.py` | 图像融合 | `RT_PoissonBlend`, `RT_BlendInpaint` |
| `color_nodes.py` | 颜色匹配 | `RT_ColorMatch` |
| `switch_nodes.py` | 条件开关 | `RT_LazySwitch`, `RT_LazySwitch2way` |
| `tool_nodes.py` | 工具选择器 | `RT_ResolutionSelector`, `RT_AspectRatioSelector`, `RT_AspectRatioDetector` |
| `math_nodes.py` | 数学表达式 | `RT_MathExpression` |
| `string_nodes.py` | 字符串连接 | `RT_JoinStringMulti`, `RT_JoinStrings` |

**放置原则**：
- 继承 `RelayNodeBase` 的节点类
- 组合 utils/ 的纯函数完成功能
- 向 ComfyUI 暴露节点接口

### 2.3 架构模式：函数式组合（核心）

节点不实例化任何 Processor 类，而是通过**函数式组合**调用 utils/ 纯函数：

```python
# 标准模式：adaptive_process(data, 算法函数, **参数)
result = adaptive_process(
    mask,           # 输入张量 [B, ...]
    expand_mask,    # 算法纯函数 fn(chunk, **kwargs) → Tensor
    device="auto",
    batch_size=8,
    expand=5,       # → 透传给 expand_mask 的 kwargs
)
```

`adaptive_process` 内部自动处理：GPU/CPU 策略选择 → GPU 分块 → OOM 回退 → 双层进度条。

### 2.4 依赖方向规范（强制）

```
nodes/                        ← 继承 RelayNodeBase，组合 utils 函数
  │                              向 ComfyUI 暴露节点类
  │  只允许 import ↓
  │
utils/                        ← 纯函数 + 基类 + GPU/CPU 自适应调度
                                零内部依赖，不感知 nodes

严禁反向：utils 不可 import nodes
```

| 层 | 可引用 | 禁止引用 |
|----|--------|----------|
| `nodes/` | `utils/`（通过 `from ..utils import ...`） | — |
| `utils/` | 第三方库、标准库 | `nodes/` |

**设计意图**：
- `utils/` 是最底层，纯函数+基类，**零内部依赖**。它不感知 `nodes` 的存在，可独立测试和复用。
- `nodes/` 是顶层，组合 `utils` 的工具函数与基类，对 ComfyUI 暴露节点接口。是唯一直接面向用户的层。

**校验方法**：
```bash
# utils 不应引用 nodes（应无输出）
rg "from \.\.nodes" utils/
```

### 2.5 utils 修改规范（强制）⚠️

**核心原则：utils 中的函数被多个节点共享，禁止随意修改签名或行为。**

#### 2.5.1 修改前必须做的事

1. **查看调用者注释**：每个公开函数定义前都有 `── 调用者 ──` 注释块，列出所有引用该函数的节点
2. **确认所有调用者兼容**：修改签名、返回值类型、或关键算法逻辑前，必须逐个检查调用者
3. **充分测试**：修改高影响面函数（如 `RelayNodeBase`、`adaptive_process`）必须测试所有下游节点

#### 2.5.2 调用者注释规范（每个 utils 公开函数必须标注）

```python
# ── 调用者 ──
#   xxx_nodes.py → RT_Xxx
#   yyy_nodes.py → RT_Yyy
# ⚠️ 修改签名/行为前必须确认以上 N 个调用者兼容！
def some_function(data, ...):
    ...
```

注释格式要求：
- 以 `── 调用者 ──` 开头
- 每行 `#   文件名.py → 节点名`，说明调用者
- 以 `# ⚠️ 修改签名/行为前必须确认以上 N 个调用者兼容！` 结尾
- 若暂无节点引用，标注 `(暂无节点直接引用，工具函数)` 或 `(模块内部辅助函数)`
- 若为高影响面函数，额外说明影响范围（如 `⚠️ 修改 RelayNodeBase 会影响全部 22 个节点！`）

#### 2.5.3 新增 utils 函数时

新函数定义时必须同步添加调用者注释，即使暂无调用者：

```python
# ── 调用者 ──
#   (暂无节点引用，新增工具函数)
def new_utility(data, ...):
    ...
```

#### 2.5.4 新增节点引用 utils 函数时

在节点中新增对 utils 函数的 import 和调用时，**必须同步更新**该 utils 函数的调用者注释，将新节点加入清单。

#### 2.5.5 修改高影响面函数时的特别注意事项

| 函数 | 影响面 | 注意事项 |
|------|--------|----------|
| `RelayNodeBase` | 全部 22 个节点 | 修改 `__init__` / `CATEGORY` 会影响所有节点 |
| `adaptive_process` | 5 个节点 + bbox_utils | OOM 回退、分块策略、进度条逻辑均在此统一控制 |
| `AnyType` | 全部使用 `any` 通配符的端口 | 修改 `__ne__` 行为会影响类型匹配 |

#### 2.5.6 禁止的操作

- ❌ **直接修改 utils 函数签名**而不检查调用者
- ❌ **修改算法实现**导致输出结果变化而不通知下游
- ❌ **添加/删除参数**而不更新调用者注释
- ❌ **修改返回值类型**（如 Tensor→tuple）而不适配所有调用者

## 3. 导入规范

### 3.1 导入顺序

```python
# 1. 标准库
from typing import Optional, Tuple

# 2. 第三方库
import torch
import torch.nn.functional as F
try:
    from comfy.utils import ProgressBar
    HAS_PROGRESS_BAR = True
except ImportError:
    HAS_PROGRESS_BAR = False

# 3. 项目内部 - utils
from ..utils import (
    RelayNodeBase,
    resize_images_batch,
    resize_masks_batch,
    AnyType,
    any,
)
```

### 3.2 导入示例

```python
# 工具函数
from ..utils import RelayNodeBase
from ..utils import AnyType, any
from ..utils import resize_images_batch, resize_masks_batch
from ..utils import expand_mask, gaussian_blur_mask
from ..utils import adaptive_process, select_device
from ..utils import bbox_to_mask

# 合并导入
from ..utils import (
    RelayNodeBase,
    AnyType,
    any,
    resize_images_batch,
    adaptive_process,
)
```

## 4. 命名规范

### 4.1 类命名

- 使用 PascalCase
- 以 `RT_` 前缀开头（RelayTyNodes）

```python
class RT_PoissonBlend(RelayNodeBase):
class RT_ColorMatch(RelayNodeBase):
class AnyType(str):
```

### 4.2 函数/方法命名

- 使用 snake_case
- 私有方法以 `_` 开头

```python
def resize_images_batch(images, target_h, target_w):
def _expand_mask_single(mask, expand):
```

### 4.3 常量命名

- 使用 UPPER_SNAKE_CASE

```python
HAS_PROGRESS_BAR = True
DEFAULT_BATCH_SIZE = 8
```

### 4.4 变量命名

- 使用 snake_case
- 类型后缀约定：
  - `_tensor`: Tensor 变量
  - `_gpu`: GPU 上的变量
  - `_cpu`: CPU 上的变量
  - `_chunk`: 分块数据

```python
adjusted_mask = mask
mask_gpu = mask.to(device)
result_cpu = result.cpu()
orig_chunk = original[start:end]
```

## 5. 节点开发规范

### 5.0 节点设计原则（强制）

#### 5.0.1 单一职责原则

每个节点只做**一件事**。判断标准：如果用"和"或"+"来描述节点功能（如"分离+跟踪"），通常意味着应该拆分为多个节点。

```python
# ✅ 正确：只做一件事
class RT_AspectRatioDetector(RelayNodeBase):
    """根据输入图像检测宽高比"""
    ...

# ❌ 错误：同时做分离和跟踪两件事
class RT_SeparateMasks(RelayNodeBase):
    """Mask分离 + 视频跟踪 — "和/+"是拆分信号"""
    ...
```

#### 5.0.2 拆分判定标准

满足以下**任意一条**即可考虑拆分为多个节点：

1. **独立可用性**：节点的某部分功能有独立的输入输出，可以单独使用
2. **参数局部性**：节点参数中存在仅对部分功能生效的参数（如 `max_tracks` 只对跟踪有意义，对分离无意义）
3. **算法可替换性**：未来可能需要替换某部分功能的算法实现（如换不同的跟踪算法）

#### 5.0.3 不拆分的情形（天然耦合）

以下情形属于天然耦合，**不应拆分**：

1. **算法内多步骤**：如色彩空间转换的 `矩阵乘法 → 对数映射`，拆分后步骤无独立使用价值
2. **内部状态传递**：拆分会导致用户需要手动传递内部中间张量
3. **零独立场景**：拆分后每个子节点完全没有独立使用场景

#### 5.0.4 职责边界示例

| 节点 | 职责 | 边界 |
|------|------|------|
| `RT_ResolutionSelector` | 选择分辨率 → 输出整数 | 不检测、不计算、不校验 |
| `RT_AspectRatioDetector` | 检测图像比例 → 输出字符串 | 不选择、不裁剪、不缩放 |
| `RT_PoissonBlend` | 按遮罩融合两张图（Poisson梯度域） | 不做遮罩羽化（由 RT_MaskFeather 负责） |
| `RT_MaskContour` | 绘制 Mask 闭合轮廓线 | 不做边缘像素绘制（由 draw_mask_outline 负责） |

#### 5.0.5 模块级函数放置规范（强制）

**核心原则：模块级函数（在 class 外部定义的顶层函数）必须满足"公用"条件才允许存在，否则必须放入类内部或嵌套为闭包。**

**判定标准**：搜索整个代码库，若函数在所有 `nodes/*.py` 和 `utils/*.py` 中仅被 **1 个调用者**引用，则不是公用函数。

| 调用者数量 | 函数归属 | 放置方式 |
|-----------|---------|---------|
| ≥ 2 个不同节点/模块 | **模块级公用函数** | 顶层 `def`（可加 `_` 前缀表示内部函数） |
| = 1 个节点类 | 该类的静态方法 | `@staticmethod` 在类内部 |
| = 1 个函数（该函数也在类内部） | 嵌套闭包 | `def` 定义在调用它的函数体内部 |

**示例 1：节点专用函数 → 放入类内部**

```python
# ❌ 错误：模块级但只被一个类使用
def _alpha_blend_chunk(combined, **kwargs):
    C = (combined.shape[-1] - 1) // 2
    original = combined[..., :C]
    inpaint = combined[..., C:2 * C]
    mask = combined[..., -1:]
    return original * (1.0 - mask) + inpaint * mask

class RT_BlendInpaint(RelayNodeBase):
    def execute(self, ...):
        result = adaptive_process(combined, _alpha_blend_chunk, ...)  # 模块级引用

# ✅ 正确：作为 @staticmethod 放入唯一使用它的类
class RT_BlendInpaint(RelayNodeBase):
    @staticmethod
    def _alpha_blend_chunk(combined, **kwargs):
        C = (combined.shape[-1] - 1) // 2
        original = combined[..., :C]
        inpaint = combined[..., C:2 * C]
        mask = combined[..., -1:]
        return original * (1.0 - mask) + inpaint * mask

    def execute(self, ...):
        result = adaptive_process(combined, self._alpha_blend_chunk, ...)  # self. 引用
```

**示例 2：函数内部专用辅助函数 → 嵌套为闭包**

```python
class RT_PoissonBlend(RelayNodeBase):
    @staticmethod
    def _poisson_blend_chunk(combined, iters=400, tolerance=1e-4, **kwargs):
        # _shift_bhwc 和 _laplacian 只在本函数内使用 → 嵌套定义
        def _shift_bhwc(tensor, dx, dy):
            bchw = tensor.permute(0, 3, 1, 2)
            ...
        def _laplacian(img):
            up = _shift_bhwc(img, 0, -1)
            ...
        # 主逻辑使用嵌套函数
        lap = _laplacian(inpaint)
        ...
```

**设计意图**：
- 避免模块命名空间污染（减少顶层符号数量）
- 明确函数归属（一眼看出"这个函数属于哪个节点"）
- 作用域最小化（嵌套闭包仅在被调用函数中可见，零泄漏）
- 提高可维护性（修改节点时只需在类内部搜索，无需跳到模块顶层）

**校验方法**：
```bash
# 检查 nodes/ 目录下所有非类方法的模块级定义
# 逐一确认其是否有 ≥2 个不同调用者
rg "^def " nodes/ --no-heading
```

### 5.0.6 `# region` / `# endregion` 注释规范（强制）

每个节点类必须用 `# region` / `# endregion` 包裹，与 [mask_nodes.py](file:///e:/AppData/ComfyUI/ComfyUI_windows_portable/ComfyUI/custom_nodes/ComfyUI-RelayTyNodes/nodes/mask_nodes.py) 保持一致，支持 IDE 代码折叠。

```python
# region RT_MyNode
# 节点中文功能描述（单行）
class RT_MyNode(RelayNodeBase):
    """详细 docstring"""
    ...
# endregion
```

格式要求：
- `# region RT_ClassName`（注意 `#` 后有空格）
- 第二行为单行中文功能摘要注释 `# 中文描述`
- 类定义结束后单独一行 `# endregion`
- 相邻节点之间空 2 行（与 `# region` 之间空 1 行）

### 5.1 节点模板

```python
# region RT_MyNode
# [节点中文名称]节点（[可选的简短说明]）
class RT_MyNode(RelayNodeBase):
    """
    节点文档字符串

    功能说明：
    - 简短描述

    参数说明：
    - param1: 参数1说明

    输出说明：
    - output1: 输出1说明
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input1": ("IMAGE", {"tooltip": "输入1说明"}),
            },
            "optional": {
                "option1": ("INT", {"default": 0, "min": 0, "max": 100}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "execute"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT节点名称(中文)

## 功能
简明描述节点的核心功能，不超过3行。

## 输入
- 输入1: 描述

## 输出
- 输出1: 描述

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 参数中文名称 | 默认值 | 参数详细说明，包括取值范围、单位、作用等 |
"""

    def execute(self, input1, option1=0):
        result = self._process(input1, option1)
        return (result,)

    # [函数简短描述]
    def _process(self, input1, option1):
        """
        函数文档字符串

        详细说明函数的功能和使用方式。

        参数：
            input1: 参数说明
            option1: 参数说明

        返回值：
            返回值说明
        """
        ...
# endregion
```

### 5.1.1 文档编写规范（强制）

1. **文档字符串（docstring）**：
   - 所有类、函数、模块必须有文档字符串
   - 模块文档字符串在文件开头（见 §6.1）
   - 类文档字符串描述类的功能、参数、输出
   - 函数文档字符串描述功能、参数、返回值、示例

2. **上方注释**：
   - 在类定义上方使用 `# region RT_ClassName` + 单行注释，格式：`# [节点中文名称]节点（[可选的简短说明]）`
   - 类定义结束后单独一行 `# endregion`（详见 §5.0.6）
   - 在函数定义上方使用单行注释，格式：`# [函数简短描述]`
   - 示例：
     ```python
     # 解析字符串中的转义字符
     def parse_escape_chars(s):
         """函数文档字符串"""
         ...

     # region RT_JoinStringMulti
     # RT多字符串连接节点（所有输入都可不连线）
     class RT_JoinStringMulti(RelayNodeBase):
         """类文档字符串"""
         ...
     # endregion
     ```

### 5.1.2 行内注释规范（强制）

**核心原则：注释解释"为什么"（why），而非"是什么"（what）。代码本身已经表达了 what。**

#### 5.1.2.1 应该写注释的场景

| 场景 | 说明 | 示例 |
|------|------|------|
| **算法步骤的数学含义** | 密集计算逻辑需要说明每一步在算法中的角色 | `# Jacobi 更新：除以 4 得到四邻域均值，加上源梯度修正` |
| **数据流关键节点** | 张量拼接/拆分/reshape 等操作的目的 | `# 沿通道维度拼接 original + inpaint + mask，供 processing 函数统一拆分` |
| **边界条件和分支逻辑** | 解释条件判断的设计意图 | `# 二值化 Mask（>0.5 视为修复区域）` |
| **非显而易见的优化选择** | 某种写法为什么比另一种更好 | `# 仅计算 mask 区域内的平均变化，用于收敛判断` |
| **调试/临时逻辑** | `# TODO:` / `# FIXME:` / `# HACK:` 标记 | `# TODO: 后续考虑用共轭梯度法加速收敛` |

#### 5.1.2.2 不应写注释的场景

| 场景 | 说明 | 反例 |
|------|------|------|
| 变量声明 | 变量名已自解释 | `# 定义变量 x` ← 冗余 |
| 简单赋值 | 代码一眼可见 | `# 将结果赋给 result` ← 冗余 |
| 标准 API 调用 | 函数名已说明用途 | `# 调用 torch.clamp 裁剪` ← 冗余 |
| 代码本身直接体现的逻辑 | 注释不应重复代码 | `# 如果 mask 为 None` ← 代码已写 `if mask is None:` |

#### 5.1.2.3 格式要求

| 要求 | 说明 |
|------|------|
| **语言** | 与项目一致，使用中文 |
| **位置** | 注释紧邻被说明代码的**上一行**（独立行），不与代码同行 |
| **前缀** | 以 `# ` 开头（井号后空格） |
| **长度** | 单行不超过 79 字符，超长则换行用第二行 `# ` 续写 |
| **分组** | 多行相关代码前用注释作"分段标题"，上空一行 |

```python
# ✅ 正确示例：注释解释算法含义、数据流意图
class RT_PoissonBlend(RelayNodeBase):
    def execute(self, ...):
        B, H, W, C = original.shape

        # Mask 标准化：无 mask → 全修复；2D → 加 batch 维度
        if mask is None:
            mask_data = torch.ones(B, H, W, device=original.device, dtype=original.dtype)
        ...

        # 沿通道维度拼接 original + inpaint + mask，供 processing 函数统一拆分
        combined = torch.cat([original, inpaint, mask_data.unsqueeze(-1)], dim=-1)

        result = adaptive_process(
            combined,
            self._poisson_blend_chunk,
            ...

    @staticmethod
    def _poisson_blend_chunk(combined, iters=400, ...):
        """Poisson 融合处理函数"""

        # 从 combined 张量的末尾维拆分三部分
        original = combined[..., :C]
        inpaint = combined[..., C:2 * C]
        mask = combined[..., -1]

        # 二值化 Mask（>0.5 视为修复区域）
        m = (mask > 0.5).float()
        # 初始解 = 原图（非 mask 区域保持不变）
        V = original.clone()

        # Jacobi 迭代求解泊松方程
        for _ in range(iters):
            ...
            # Jacobi 更新：除以 4 得到四邻域均值，加上源梯度修正
            V_new = (sumN + lap) / 4.0
            # 非 mask 区域保持 original 不变
            V_new = torch.where(M_exp, V_new, original)

            # 仅计算 mask 区域内的平均变化，用于收敛判断
            err = torch.mean(torch.abs(V_new - V)[M_exp.expand_as(V)])
```

```python
# ❌ 错误示例：注释重复代码
x = x + 1  # 将 x 加 1                          ← 冗余
result = torch.zeros_like(data)  # 创建零张量    ← 冗余
if mask is None:                 # 检查 mask      ← 冗余
```

### 5.2 显存管理规范

#### 5.2.1 分块处理模式

```python
def my_heavy_function(self, data, device, batch_size=8):
    # 1. 估算显存需求
    B = data.shape[0]
    num_chunks = max(1, (B + batch_size - 1) // batch_size)

    # 2. 预分配结果
    result = torch.zeros_like(data)

    # 3. 分块处理
    for chunk_idx in range(num_chunks):
        start = chunk_idx * batch_size
        end = min(start + batch_size, B)

        # 移动到 GPU
        chunk = data[start:end].to(device)

        # 处理
        chunk_result = self._process_chunk(chunk)

        # 立即释放中间变量
        del chunk
        torch.cuda.empty_cache()

        # 存回 CPU
        result[start:end] = chunk_result.cpu()
        del chunk_result

    return result
```

#### 5.2.2 避免计算图保留

```python
# 错误：保留了计算图
training_losses = []
for batch in dataloader:
    loss = model(batch)
    training_losses.append(loss)  # 计算图被保留！

# 正确：分离计算图
training_losses = []
for batch in dataloader:
    loss = model(batch)
    training_losses.append(loss.detach().cpu().item())
```

### 5.3 进度条规范

```python
try:
    from comfy.utils import ProgressBar
    HAS_PROGRESS_BAR = True
except ImportError:
    HAS_PROGRESS_BAR = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

def execute_with_progress(self, num_items):
    comfy_pbar = None
    if HAS_PROGRESS_BAR:
        comfy_pbar = ProgressBar(num_items)

    iterator = range(num_items)
    if HAS_TQDM:
        iterator = tqdm(iterator, desc="处理中")

    for i in iterator:
        # 处理逻辑
        if comfy_pbar:
            comfy_pbar.update(1)
```

## 6. 文档规范

### 6.1 节点文件模块文档（强制）

**每个 `nodes/*.py` 文件必须以模块级 docstring 开头**，格式如下：

```python
"""
[模块中文名称]节点实现

此模块包含[简要模块功能描述]。

节点列表：
- RT_NodeName1: 节点功能简短描述
- RT_NodeName2: 节点功能简短描述

注：[可选的附加说明，如依赖关系、前后端配合情况等]
"""
```

**完整示例**（引自 `nodes/mask_nodes.py`）：

```python
"""
Mask操作节点实现

此模块包含与遮罩操作相关的节点。

节点列表：
- RT_ImageToMask: 从图像通道提取遮罩（亮度/RGB/HSV通道 + 色阶调整）

注：底层使用 utils/mask_utils.py 的 extract_channel + apply_levels，
    GPU/CPU调度由 utils/gpu_utils.py 的 adaptive_process 统一处理。
"""
```

**要求**：
- 模块文档必须是文件的第一个有效内容（在 import 之前）
- `节点列表` 必须列出本文件中**所有**节点类及其功能描述
- 如果有前端 JS 配合，在"注"中说明

### 6.2 前端 JS 文件文档（强制）

**每个 `web/js/*.js` 文件必须以 JSDoc 块注释开头**，格式如下：

```javascript
/**
 * =============================================================================
 * ComfyUI-RelayTyNodes - [模块中文名称]前端扩展
 * =============================================================================
 *
 * 模块说明:
 *   [此模块的作用概述]
 *
 * 前后端配合节点:
 *   - RT_NodeName (nodes/xxx.py): 后端提供[后端功能]；
 *     本前端扩展提供[前端功能]。
 *
 * 扩展功能:
 *   - 功能1描述
 *   - 功能2描述
 *
 * =============================================================================
 */
```

**完整示例**（引自 `web/js/string_nodes.js`）：

```javascript
/**
 * =============================================================================
 * ComfyUI-RelayTyNodes - 字符串节点前端扩展
 * =============================================================================
 *
 * 模块说明:
 *   为 RT_JoinStringMulti 节点提供前端动态端口管理功能。
 *
 * 前后端配合节点:
 *   - RT_JoinStringMulti (nodes/string_nodes.py): 后端提供字符串连接逻辑；
 *     本前端扩展提供"Update inputs"按钮，根据 inputcount 参数动态添加/移除输入端口。
 *
 * 扩展功能:
 *   - 动态输入端口管理：根据 inputcount widget 的值动态调整 string_* 输入端口数量
 *   - 节点创建时自动初始化默认数量的输入端口
 *
 * =============================================================================
 */
```

**要求**：
- 文档必须是文件顶部第一个内容
- 如需配合后端节点，必须在 `前后端配合节点` 中明确说明对应的后端文件和节点名
- 全局工具类 JS 文件（如 `help_popup.js`）需在 `关联节点` 中说明适用范围

### 6.3 函数文档 

```python
def function_name(param1, param2):
    """
    函数简短描述

    详细说明函数的功能和使用方式。

    参数：
        param1: 参数1说明
        param2: 参数2说明

    返回值：
        返回值说明

    示例：
        >>> result = function_name(a, b)
    """
```

### 6.4 节点 DESCRIPTION 规范（强制）

#### 6.4.1 统一格式模板

```markdown
# RT节点名称(中文)
## 功能
简明描述节点的核心功能，不超过3行。
## 输入
- 输入1: 描述
- 输入2: 描述
## 输出
- 输出1: 描述
- 输出2: 描述

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 参数中文名称 | 默认值 | 参数详细说明，包括取值范围、单位、作用等 |

## 参数选项说明（如有）
|参数名称| 对应选项 | 属性1 | 属性2 | 说明 |
|------|------|-------|-------|------|
| 参数中文名称 | option_value | 值 | 值 | 选项说明 |

## 使用建议（如有）
- 使用场景1
- 使用场景2
- 注意事项
```

#### 6.4.2 格式规范

| 元素 | 规范要求 | 示例 |
|------|----------|------|
| **标题** | `# RT节点名称(中文)`，使用中文显示名 | `# RT图像通道转遮罩` |
| **功能章节** | 必须有，用 `## 功能`，简明扼要 | `## 功能\n从图像通道提取遮罩` |
| **输入输出** | 参数名使用英文（与 `INPUT_TYPES` 一致），描述使用中文，顺序与 `INPUT_TYPES` 定义一致 | `- image_ref: 参考图像（提供颜色风格）` |
| **参数表格** | 使用 `| 参数 | 默认值 | 说明 |` 格式，参数名为中文 | `| 黑点 | 0.0 | 黑点阈值... |` |
| **选项表格** | 使用 `| 选项 | 属性1 | 属性2 | 说明 |` 格式，选项值保持英文 | `| reinhard_lab | ⚡⚡⚡ | ⭐⭐⭐ | GPU批量处理 |` |
| **使用建议** | 使用 `- 列表项` 格式 | `- 工作流：A → B → C` |

#### 6.4.3 输入输出描述一致性规范（强制）

**核心原则**：DESCRIPTION 中的输入输出描述必须与 `INPUT_TYPES`、`nodeDefs.json`、`i18n.js` 保持一致。

**一致性要求**：

| 文件 | 一致性要求 |
|------|----------|
| `INPUT_TYPES` (nodes/*.py) | 参数名（英文）、顺序、类型 |
| `DESCRIPTION` (nodes/*.py) | 参数名（中文显示名）、顺序、描述 |
| `nodeDefs.json` | 参数名（英文 key）、顺序、中文显示名 |
| `i18n.js` | 参数名（英文 key）、顺序、中文显示名 |

**格式规范**：
- 参数名使用**中文显示名**（与 `nodeDefs.json` 和 `i18n.js` 中的翻译一致）
- 格式：`- 中文名称: 描述内容`
- 顺序必须与 `INPUT_TYPES` 定义顺序一致

**示例**：

```python
# INPUT_TYPES 定义
def INPUT_TYPES(cls):
    return {
        "required": {
            "image_ref": ("IMAGE", {"tooltip": "参考图像"}),
            "image_target": ("IMAGE", {"tooltip": "目标图像"}),
        }
    }

# DESCRIPTION 描述（参数名使用中文显示名）
DESCRIPTION = """
## 输入
- 参考图像: 提供颜色风格的图像
- 目标图像: 需要调整颜色的图像
"""
```

**nodeDefs.json 格式**：
```json
{
  "RT_ColorMatch": {
    "inputs": {
      "image_ref": { "name": "参考图像" },
      "image_target": { "name": "目标图像" }
    }
  }
}
```

**i18n.js 格式**：
```javascript
"RT_ColorMatch": {
    inputs: {
        image_ref: "参考图像",
        image_target: "目标图像"
    }
}
```

**校验方法**：
1. 检查 DESCRIPTION 中输入输出的中文参数名是否与 `nodeDefs.json` 和 `i18n.js` 中的翻译一致
2. 检查 DESCRIPTION 中参数顺序是否与 `INPUT_TYPES` 定义顺序一致
3. 检查描述内容是否清晰说明参数用途

#### 6.4.4 参数与选项区分规则

| 类型 | 定义 | 命名规则 | 示例 |
|------|------|----------|------|
| **参数** | 用户可输入调整的值 | 中文名称，对应 `nodeDefs.json` 和 `i18n.js` | `黑点`、`羽化范围`、`分块大小` |
| **选项** | 固定选项列表中的值 | 英文原名称，保持与代码中一致 | `reinhard_lab`、`luminance`、`red` |

**关键原则**：
- **参数名称必须使用中文**，且与 `locales/zh/nodeDefs.json` 和 `web/js/i18n.js` 中的翻译保持一致
- **选项值必须保持英文**，因为这些是实际的选项值，用户需要知道选择的是什么

#### 6.4.5 表格列数规范

| 表格类型 | 列数 | 列标题 |
|----------|------|--------|
| 参数表格 | 3列 | `参数`、`默认值`、`说明` |
| 选项表格 | 4列 | `选项`、`属性1`、`属性2`、`说明` |

#### 6.4.6 章节顺序（强制）

1. `# RT节点名称(中文)` - 节点标题（中文显示名）
2. `## 功能` - 功能描述
3. `## 输入` - 输入端口说明（如有）
4. `## 输出` - 输出端口说明（如有）
5. `## 参数说明` - 参数表格（如有参数）
6. `## 参数选项说明` - 选项表格（如有选项）
7. `## 使用建议` - 使用场景和注意事项

#### 6.4.7 示例

```markdown
# RT颜色匹配

## 功能
将参考图像的颜色分布迁移到目标图像上。

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 强度 | 1.0 | 迁移强度（0=无变化，1=完全迁移，>1=增强） |
| 批次大小 | 8 | 批次大小 |

## 参数选项说明
| 参数名称 | 对应选项 | 速度 | 效果 | 说明 |
|----------|----------|------|------|------|
| 算法 | reinhard_lab | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ | GPU批量处理（经典） |
| 算法 | reinhard_oklab | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 推荐首选！感知均匀 |

## 使用建议
- 日常使用：reinhard_oklab + 强度=1.0
- 视频处理：reinhard_oklab + 批次大小=8-16
```

## 7. 错误处理规范

### 7.1 导入错误处理

```python
import logging
logger = logging.getLogger(__name__)

try:
    from comfy.utils import ProgressBar
    HAS_PROGRESS_BAR = True
except ImportError:
    HAS_PROGRESS_BAR = False
    logger.warning("comfy.utils 不可用，进度条功能被禁用")
```

### 7.2 处理错误

```python
import logging
logger = logging.getLogger(__name__)

def safe_process(self, data):
    try:
        result = self._process(data)
        return result
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return self._get_default_result()
```

## 8. 测试规范

### 8.1 测试文件命名

```
tests/
├── __init__.py
├── test_blend.py            # 测试图像融合模块
└── test_blend_simple.py     # 简单融合测试
```

### 8.2 测试函数命名

```python
def test_resize_images_batch():
    """测试 resize_images_batch 函数"""
    pass

def test_expand_mask():
    """测试 expand_mask 纯函数"""
    pass
```

## 9. 性能优化提示

### 9.1 避免在循环中创建张量

```python
# 不好：循环中创建
for i in range(100):
    result = torch.zeros_like(data)  # 每次都分配内存

# 好：预分配后复用
result = torch.zeros_like(data)
for i in range(100):
    result.zero_()
    result.add_(processed_chunk)
```

### 9.2 及时释放显存

```python
# 处理完成后及时删除和清理
del intermediate_variable
torch.cuda.empty_cache()
```

### 9.3 使用连续张量

```python
if not tensor.is_contiguous():
    tensor = tensor.contiguous()
```

## 10. 提交前检查清单

- [ ] 所有导入语句正确
- [ ] 语法检查通过（`python -m py_compile`）
- [ ] 新增函数/类已添加到 `__init__.py` 导出
- [ ] 新增/修改 utils 函数已同步更新调用者注释（见 §2.5）
- [ ] 文档字符串完整
- [ ] 节点类使用 `# region` / `# endregion` 包裹（见 §5.0.6）
- [ ] 模块级函数已确认公用性（≥2 调用者，见 §5.0.5）
- [ ] 遵循命名规范
- [ ] 节点重命名后已同步更新所有引用文件（见记忆 多文件同步更新要求）
- [ ] 无硬编码的敏感信息
