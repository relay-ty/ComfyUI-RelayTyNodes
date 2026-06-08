"""
颜色处理节点实现

此模块包含颜色迁移（Color Transfer）相关的节点，用于将参考图像的颜色分布迁移到目标图像上。

节点列表：
- RT_ColorMatch: 颜色匹配节点，将参考图像的颜色分布迁移到目标图像，适用于视频帧颜色校正、风格统一等场景。
                 支持 OkLab 和 RGB 两种色彩空间，支持批量并行处理和 OOM 回退机制。
"""

import torch
import numpy as np
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple
from ..utils import RelayNodeBase

logger = logging.getLogger(__name__)


# region RT_ColorMatch
# RT颜色匹配节点（支持多种色彩空间）
class RT_ColorMatch(RelayNodeBase):
    """
    功能：将参考图像的颜色分布迁移到目标图像上，用于视频帧颜色校正、风格统一等场景。
    """

    # OkLab转换的常量矩阵（RGB转OkLab）
    _M1_OKLAB = torch.tensor([
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005]
    ])
    _M2_OKLAB = torch.tensor([
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660]
    ])
    _M1_INV_OKLAB = torch.tensor([
        [4.0767416621, -3.3077115913, 0.2309699292],
        [-1.2684380046, 2.6097574011, -0.3413193965],
        [-0.0041960863, -0.7034186147, 1.7076147010]
    ])
    _M2_INV_OKLAB = torch.tensor([
        [1.0, 0.3963377774, 0.2158037573],
        [1.0, -0.1055613458, -0.0638541728],
        [1.0, -0.0894841775, -1.2914855480]
    ])

    def __init__(self):
        super().__init__()

    # Lab转换的常量白点值（D65）
    _xyz_white_point = torch.tensor([0.95047, 1.0, 1.08883])

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_ref": ("IMAGE", {"tooltip": "参考图像（提供颜色风格）"}),
                "image_target": ("IMAGE", {"tooltip": "目标图像（将被修改的图像）"}),
                "method": (['reinhard_lab', 'reinhard_oklab', 'reinhard_oklch', 'reinhard', 'mkl', 'mvgd', 'hm'], {
                    "default": 'reinhard_lab',
                    "tooltip": "颜色匹配算法:\n"
                              "• reinhard_lab: Lab空间Reinhard（GPU加速，推荐）\n"
                              "• reinhard_oklab: OkLab空间Reinhard（感知均匀，效果更好）⭐\n"
                              "• reinhard_oklch: OkLch空间Reinhard（保持色相，仅调亮度饱和度）⭐\n"
                              "• reinhard: 标准Reinhard（RGB空间）\n"
                              "• mkl: Monge-Kantorovich线性化\n"
                              "• mvgd: 多元高斯分布（复杂颜色）\n"
                              "• hm: 直方图匹配（快速）"
                }),
                "strength": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.05,
                    "tooltip": "颜色迁移强度（0=无变化，1=完全迁移）"
                }),
            },
            "optional": {
                "device": (["auto", "cpu", "gpu"], {
                    "default": "gpu",
                    "tooltip": "处理设备（auto: 自动选择，gpu: 优先GPU，cpu: 强制CPU）"
                }),
                "batch_size": ("INT", {
                    "default": 16,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "tooltip": "批次大小"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "execute"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT颜色匹配

## 功能
将参考图像的颜色分布迁移到目标图像上，适用于视频帧颜色统一校正、局部重绘后颜色匹配、风格迁移。

## 输入
- 参考图像: 提供颜色风格的图像
- 目标图像: 需要调整颜色的图像

## 输出
- 图像: 颜色匹配后的图像

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 算法 | reinhard_lab | 颜色匹配算法 |
| 强度 | 1.0 | 迁移强度（0=无变化，1=完全迁移，>1=增强） |
| 批次大小 | 16 | 批次大小 |
| 设备 | gpu | 处理设备（auto/gpu/cpu） |

## 参数选项说明
| 参数名称 | 对应选项 | 速度 | 效果 | 推荐场景 |
|----------|----------|------|------|----------|
| 算法 | reinhard_lab | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ | GPU批量处理（经典） |
| 算法 | reinhard_oklab | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ⭐推荐首选！感知均匀，效果更好 |
| 算法 | reinhard_oklch | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 保持原图色相，仅调整亮度和饱和度 |
| 算法 | reinhard | ⚡⚡⚡⚡ | ⭐⭐⭐ | GPU RGB匹配 |
| 算法 | mkl | ⚡⚡ | ⭐⭐⭐⭐ | 平衡效果（CPU） |
| 算法 | mvgd | ⚡ | ⭐⭐⭐⭐ | 复杂颜色（CPU） |
| 算法 | hm | ⚡⚡ | ⭐⭐⭐ | 快速预览（CPU） |

## 新算法说明
- **reinhard_oklab**: 基于 OkLab 颜色空间（感知均匀），比传统 Lab 空间效果更好
- **reinhard_oklch**: 基于 OkLch 颜色空间（L=亮度，C=色度、h=色相），保持原图色相不变

## 使用建议
1. ⭐日常使用：reinhard_oklab + strength=1.0（推荐！）
2. 保持色相：reinhard_oklch + strength=1.0
3. 经典方案：reinhard_lab + strength=1.0
4. 视频处理：reinhard_oklab + batch_size=8-16
5. 显存不足：切换到cpu 或减小batch_size
"""

    def execute(self, image_target: torch.Tensor, image_ref: torch.Tensor,
                method: str = 'reinhard_lab', strength: float = 1.0,
                device: str = "auto", batch_size: int = 16) -> Tuple[torch.Tensor]:
        B, H, W, C = image_target.shape
        ref_B = image_ref.shape[0]
        logger.info("[RT_ColorMatch] 开始处理: target=%d, ref=%d, method=%s, batch_size=%d, device=%s",
                    B, ref_B, method, batch_size, device)

        if strength == 0:
            logger.info("[RT_ColorMatch] strength=0，跳过处理")
            return (image_target,)

        if method in ['mkl', 'mvgd', 'hm']:
            result = self._color_matcher_cpu(image_target, image_ref, method, strength)
            return result

        # GPU 方法：预处理 + 通道拼接 + GPU处理
        # 统一参考图像的批次大小
        if ref_B != B:
            if ref_B == 1:
                image_ref = image_ref.expand(B, -1, -1, -1)
            elif ref_B < B:
                repeats = (B + ref_B - 1) // ref_B
                image_ref = image_ref.repeat(repeats, 1, 1, 1)[:B]
            else:
                image_ref = image_ref[:B]

        # 确定目标设备
        if device == "auto":
            target_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        elif device == "gpu":
            target_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            target_device = torch.device("cpu")

        # 直接在 GPU 上分批次处理，避免 adaptive_process 的额外开销
        if target_device.type == "cuda":
            result = self._gpu_chunked_process_separate(image_target, image_ref, method, strength, batch_size, 
                                                       desc=f"{method}颜色匹配", device=target_device)
        else:
            # CPU 路径使用多线程
            result = self._cpu_direct_process_separate(image_target, image_ref, method, strength)
        return (result,)

    def _rgb_to_lab(self, rgb: torch.Tensor) -> torch.Tensor:
        """将 RGB 图像转换为 Lab 色彩空间"""
        rgb = rgb.clamp(0.0, 1.0)

        # 伽马校正：将 sRGB 转换为线性 RGB
        mask = rgb > 0.04045
        rgb_converted = torch.where(mask, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)

        # 线性 RGB 转换为 XYZ 色彩空间
        X = 0.4124564 * rgb_converted[..., 0] + 0.3575761 * rgb_converted[..., 1] + 0.1804375 * rgb_converted[..., 2]
        Y = 0.2126729 * rgb_converted[..., 0] + 0.7151522 * rgb_converted[..., 1] + 0.0721750 * rgb_converted[..., 2]
        Z = 0.0193339 * rgb_converted[..., 0] + 0.1191920 * rgb_converted[..., 1] + 0.9503041 * rgb_converted[..., 2]

        # 归一化 XYZ 相对于白点 (D65)
        X = X / 0.95047
        Y = Y / 1.0
        Z = Z / 1.08883

        # XYZ 转换为 Lab
        mask_l = Y > 0.008856
        fY = torch.where(mask_l, Y ** (1 / 3), 7.787 * Y + 16 / 116)
        fX = torch.where(X > 0.008856, X ** (1 / 3), 7.787 * X + 16 / 116)
        fZ = torch.where(Z > 0.008856, Z ** (1 / 3), 7.787 * Z + 16 / 116)

        L = 116 * fY - 16
        a = 500 * (fX - fY)
        b = 200 * (fY - fZ)

        return torch.stack([L, a, b], dim=-1)

    def _lab_to_rgb(self, lab: torch.Tensor) -> torch.Tensor:
        """将 Lab 色彩空间转换为 RGB 图像"""
        L, a, b = lab[..., 0:1], lab[..., 1:2], lab[..., 2:3]

        fY = (L + 16.0) / 116.0
        fX = a / 500.0 + fY
        fZ = fY - b / 200.0

        xyz_white = self._xyz_white_point.to(device=lab.device, dtype=lab.dtype)

        Y = torch.where(fY ** 3 > 0.008856, fY ** 3, (fY - 16.0 / 116.0) / 7.787)
        X = torch.where(fX ** 3 > 0.008856, fX ** 3, (fX - 16.0 / 116.0) / 7.787)
        Z = torch.where(fZ ** 3 > 0.008856, fZ ** 3, (fZ - 16.0 / 116.0) / 7.787)

        X = X * xyz_white[0]
        Y = Y * xyz_white[1]
        Z = Z * xyz_white[2]

        # XYZ 转换为线性 RGB
        r = 3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
        g = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
        b_rgb = 0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z

        rgb = torch.cat([r, g, b_rgb], dim=-1)
        # 反伽马校正：线性 RGB 转换为 sRGB
        rgb = torch.where(rgb > 0.0031308, 1.055 * (rgb ** (1.0 / 2.4)) - 0.055, 12.92 * rgb)

        return rgb.clamp(0.0, 1.0)

    def _reinhard_lab_core(self, target: torch.Tensor, ref: torch.Tensor, strength: float) -> torch.Tensor:
        """在 Lab 色彩空间执行 Reinhard 颜色匹配"""
        src_lab = self._rgb_to_lab(target)
        ref_lab = self._rgb_to_lab(ref)

        # 展平为 (B, 3, H*W) 以便计算统计量
        src_lab_flat = src_lab.reshape(src_lab.shape[0], 3, -1)
        ref_lab_flat = ref_lab.reshape(ref_lab.shape[0], 3, -1)

        # 计算均值和标准差
        src_mean = src_lab_flat.mean(dim=-1, keepdim=True)
        src_std = src_lab_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)
        ref_mean = ref_lab_flat.mean(dim=-1, keepdim=True)
        ref_std = ref_lab_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)

        # 执行颜色匹配：调整目标的均值和标准差到参考的分布
        corrected_flat = (src_lab_flat - src_mean) * (ref_std / src_std) + ref_mean
        corrected_lab = corrected_flat.view(src_lab.shape)
        corrected_rgb = self._lab_to_rgb(corrected_lab)

        # 根据 strength 混合原始图像和匹配后的图像
        return (1.0 - strength) * target + strength * corrected_rgb

    def _reinhard_rgb_core(self, target: torch.Tensor, ref: torch.Tensor, strength: float) -> torch.Tensor:
        """在 RGB 色彩空间执行 Reinhard 颜色匹配"""
        target_flat = target.reshape(target.shape[0], -1, 3)
        ref_flat = ref.reshape(ref.shape[0], -1, 3)

        src_mean = target_flat.mean(dim=1, keepdim=True)
        src_std = target_flat.std(dim=1, keepdim=True).clamp_min(1e-6)
        ref_mean = ref_flat.mean(dim=1, keepdim=True)
        ref_std = ref_flat.std(dim=1, keepdim=True).clamp_min(1e-6)

        corrected_flat = (target_flat - src_mean) * (ref_std / src_std) + ref_mean
        corrected_rgb = corrected_flat.reshape(target.shape)

        return (1.0 - strength) * target + strength * corrected_rgb

    def _rgb_to_oklab(self, rgb: torch.Tensor) -> torch.Tensor:
        """将 RGB 转换为 OkLab 色彩空间（感知均匀的色彩空间）"""
        rgb = rgb.clamp(0.0, 1.0)
        m1 = self._M1_OKLAB.to(device=rgb.device, dtype=rgb.dtype)
        # 线性 RGB 转换为 LMS 色彩空间
        lms = torch.tensordot(rgb, m1, dims=1)
        # 非线性转换
        lms_prime = torch.sign(lms) * torch.abs(lms) ** (1/3)
        m2 = self._M2_OKLAB.to(device=rgb.device, dtype=rgb.dtype)
        # LMS' 转换为 OkLab
        oklab = torch.tensordot(lms_prime, m2, dims=1)
        return oklab

    def _oklab_to_rgb(self, oklab: torch.Tensor) -> torch.Tensor:
        """将 OkLab 色彩空间转换为 RGB"""
        m2_inv = self._M2_INV_OKLAB.to(device=oklab.device, dtype=oklab.dtype)
        lms_prime = torch.tensordot(oklab, m2_inv, dims=1)
        lms = lms_prime ** 3
        m1_inv = self._M1_INV_OKLAB.to(device=oklab.device, dtype=oklab.dtype)
        rgb = torch.tensordot(lms, m1_inv, dims=1)
        return rgb.clamp(0.0, 1.0)

    def _oklab_to_oklch(self, oklab: torch.Tensor) -> torch.Tensor:
        """将 OkLab 转换为 OkLCh（极坐标表示）"""
        L = oklab[..., 0:1]
        a = oklab[..., 1:2]
        b = oklab[..., 2:3]
        C = torch.sqrt(a ** 2 + b ** 2)  # 色度
        h = torch.atan2(b, a)  # 色相
        return torch.cat([L, C, h], dim=-1)

    def _oklch_to_oklab(self, oklch: torch.Tensor) -> torch.Tensor:
        """将 OkLCh（极坐标）转换回 OkLab"""
        L = oklch[..., 0:1]
        C = oklch[..., 1:2]
        h = oklch[..., 2:3]
        a = C * torch.cos(h)
        b = C * torch.sin(h)
        return torch.cat([L, a, b], dim=-1)

    def _reinhard_oklab_core(self, target: torch.Tensor, ref: torch.Tensor, strength: float) -> torch.Tensor:
        """在 OkLab 色彩空间执行 Reinhard 颜色匹配（感知均匀，效果更好）"""
        src_oklab = self._rgb_to_oklab(target)
        ref_oklab = self._rgb_to_oklab(ref)

        src_flat = src_oklab.reshape(src_oklab.shape[0], 3, -1)
        ref_flat = ref_oklab.reshape(ref_oklab.shape[0], 3, -1)

        src_mean = src_flat.mean(dim=-1, keepdim=True)
        src_std = src_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)
        ref_mean = ref_flat.mean(dim=-1, keepdim=True)
        ref_std = ref_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)

        corrected_flat = (src_flat - src_mean) * (ref_std / src_std) + ref_mean
        corrected_oklab = corrected_flat.view(src_oklab.shape)
        corrected_rgb = self._oklab_to_rgb(corrected_oklab)

        return (1.0 - strength) * target + strength * corrected_rgb

    def _reinhard_oklch_core(self, target: torch.Tensor, ref: torch.Tensor, strength: float) -> torch.Tensor:
        """在 OkLCh 色彩空间执行 Reinhard 颜色匹配（只调整亮度和色度，保持原始色相）"""
        src_oklab = self._rgb_to_oklab(target)
        ref_oklab = self._rgb_to_oklab(ref)
        src_oklch = self._oklab_to_oklch(src_oklab)
        ref_oklch = self._oklab_to_oklch(ref_oklab)

        _, H, W, _ = target.shape
        # 展平 L（亮度）和 C（色度）通道
        src_l_flat = src_oklch[..., 0:1].reshape(src_oklch.shape[0], 1, -1)
        src_c_flat = src_oklch[..., 1:2].reshape(src_oklch.shape[0], 1, -1)
        ref_l_flat = ref_oklch[..., 0:1].reshape(ref_oklch.shape[0], 1, -1)
        ref_c_flat = ref_oklch[..., 1:2].reshape(ref_oklch.shape[0], 1, -1)

        # 计算亮度和色度的统计量
        src_l_mean = src_l_flat.mean(dim=-1, keepdim=True)
        src_l_std = src_l_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)
        src_c_mean = src_c_flat.mean(dim=-1, keepdim=True)
        src_c_std = src_c_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)
        ref_l_mean = ref_l_flat.mean(dim=-1, keepdim=True)
        ref_l_std = ref_l_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)
        ref_c_mean = ref_c_flat.mean(dim=-1, keepdim=True)
        ref_c_std = ref_c_flat.std(dim=-1, keepdim=True).clamp_min(1e-6)

        # 只调整亮度和色度，保持原始色相 h 不变
        corrected_l = (src_l_flat - src_l_mean) * (ref_l_std / src_l_std) + ref_l_mean
        corrected_c = (src_c_flat - src_c_mean) * (ref_c_std / src_c_std) + ref_c_mean

        corrected_oklch = torch.zeros_like(src_oklch)
        corrected_oklch[..., 0:1] = corrected_l.view(-1, H, W, 1)
        corrected_oklch[..., 1:2] = corrected_c.view(-1, H, W, 1)
        corrected_oklch[..., 2:3] = src_oklch[..., 2:3]  # 保持原始色相

        corrected_oklab = self._oklch_to_oklab(corrected_oklch)
        corrected_rgb = self._oklab_to_rgb(corrected_oklab)

        return (1.0 - strength) * target + strength * corrected_rgb

    def _gpu_chunked_process_separate(self, image_target: torch.Tensor, image_ref: torch.Tensor,
                                        method: str, strength: float, batch_size: int,
                                        desc: str = "Processing", device: torch.device = None) -> torch.Tensor:
        """
        GPU分块处理：直接分开处理target和ref，避免通道拼接的内存开销
        支持OOM自动降级到更小batch_size或回退CPU
        """
        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        B = image_target.shape[0]
        current_batch_size = batch_size
        results = []
        
        try:
            from comfy.utils import ProgressBar
            pbar = ProgressBar(B)
        except ImportError:
            pbar = None
        
        # 预先获取core方法，避免循环内重复查询
        core_method = self._get_core_method(method)
        if core_method is None:
            raise ValueError(f"[RT_ColorMatch] 不支持的method: {method}，支持的方法: reinhard_lab, reinhard_oklab, reinhard_oklch, reinhard")

        with torch.no_grad():
            chunk_idx = 0
            processed = 0
            last_progress_update = 0
            
            while processed < B:
                try:
                    start = processed
                    end = min(start + current_batch_size, B)
                    chunk_actual = end - start
                    
                    # 分别上传target和ref块到GPU
                    target_chunk = image_target[start:end].to(device, non_blocking=True)
                    ref_chunk = image_ref[start:end].to(device, non_blocking=True)
                    
                    # 直接调用core方法处理
                    result = core_method(target_chunk, ref_chunk, strength)
                    
                    # 立即移回CPU并释放GPU
                    results.append(result.cpu())
                    del target_chunk, ref_chunk, result
                    
                    # 每4块清理一次缓存，平衡性能和显存
                    if chunk_idx % 4 == 0:
                        torch.cuda.empty_cache()
                    
                    processed = end
                    chunk_idx += 1
                    
                    if pbar:
                        pbar.update(chunk_actual)
                        
                except torch.cuda.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    if current_batch_size <= 1:
                        logger.warning("[RT_ColorMatch] GPU OOM，回退到CPU处理剩余帧")
                        # 拼接已处理的结果 + CPU处理剩余部分
                        cpu_result = self._cpu_direct_process_separate(image_target[processed:], 
                                                                       image_ref[processed:], 
                                                                       method, strength)
                        if len(results) > 0:
                            results.append(cpu_result)
                        else:
                            results = [cpu_result]
                        # 更新进度条
                        if pbar:
                            pbar.update(B - processed)
                        break
                    else:
                        current_batch_size = max(1, current_batch_size // 2)
                        logger.warning("[RT_ColorMatch] GPU OOM，减小batch_size到 %d", current_batch_size)

        torch.cuda.empty_cache()
        return torch.cat(results, dim=0)

    def _get_core_method(self, method: str):
        """获取对应的core处理方法，不支持的方法返回None"""
        methods = {
            "reinhard_lab": self._reinhard_lab_core,
            "reinhard_oklab": self._reinhard_oklab_core,
            "reinhard_oklch": self._reinhard_oklch_core,
            "reinhard": self._reinhard_rgb_core
        }
        return methods.get(method)

    def _cpu_direct_process_separate(self, image_target: torch.Tensor, image_ref: torch.Tensor,
                                     method: str, strength: float) -> torch.Tensor:
        """
        CPU直接处理：分开处理target和ref（数据已在CPU上）
        支持多线程并行处理（使用concurrent.futures）
        """
        B = image_target.shape[0]
        num_workers = min(4, (B + 31) // 32)  # 每32张图用一个worker
        
        try:
            from comfy.utils import ProgressBar
            pbar = ProgressBar(B)
        except ImportError:
            pbar = None

        core_method = self._get_core_method(method)
        if core_method is None:
            raise ValueError(f"[RT_ColorMatch] 不支持的method: {method}，支持的方法: reinhard_lab, reinhard_oklab, reinhard_oklch, reinhard")

        with torch.no_grad():
            # 小batch直接处理
            if B <= 32 or num_workers <= 1:
                result = core_method(image_target, image_ref, strength)
                if pbar:
                    pbar.update(B)
                return result
            
            # 大batch并行处理（保证顺序，带异常保护）
            import concurrent.futures
            chunk_size = max(1, B // num_workers)
            results = [None] * num_workers  # 预分配位置，保证顺序
            failed_chunks = []
            
            def process_chunk(chunk_idx):
                """处理单个chunk，带异常保护"""
                start = chunk_idx * chunk_size
                end = min(start + chunk_size, B)
                try:
                    return chunk_idx, core_method(image_target[start:end], image_ref[start:end], strength)
                except Exception as e:
                    logger.error(f"[RT_ColorMatch] 处理chunk {chunk_idx} 失败: {str(e)}")
                    # 返回原图作为降级处理
                    return chunk_idx, image_target[start:end].clone()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(process_chunk, i) for i in range(num_workers)]
                processed = 0
                last_progress = 0
                for future in concurrent.futures.as_completed(futures):
                    idx, chunk_result = future.result()
                    results[idx] = chunk_result  # 按索引放置，保证顺序
                    processed += chunk_result.shape[0]
                    # 平滑进度条更新（每处理10%更新一次）
                    if pbar and processed - last_progress >= B // 10:
                        pbar.update(processed - last_progress)
                        last_progress = processed
                # 更新剩余进度
                if pbar and processed > last_progress:
                    pbar.update(processed - last_progress)
            
            if failed_chunks:
                logger.warning(f"[RT_ColorMatch] 共有 {len(failed_chunks)} 个chunk处理失败，已使用原图替代")
            
            return torch.cat(results, dim=0)

    def _color_matcher_cpu(self, image_target: torch.Tensor, image_ref: torch.Tensor,
                           method: str, strength: float) -> Tuple[torch.Tensor]:
        """
        CPU 颜色匹配实现（使用 color-matcher 库）
        支持 mkl, mvgd, hm 等算法
        """
        try:
            from color_matcher import ColorMatcher
        except ImportError as e:
            raise ImportError("请安装color-matcher库: pip install color-matcher") from e

        batch_size = image_target.size(0)
        ref_batch_size = image_ref.size(0)

        def process_single(idx):
            cm = ColorMatcher()
            image_target_np = image_target[idx].cpu().numpy()
            # 如果参考图像少于 batch，循环使用最后一张
            image_ref_np = image_ref[min(idx, ref_batch_size - 1)].cpu().numpy()
            try:
                image_result = cm.transfer(src=image_target_np, ref=image_ref_np, method=method)
                if strength != 1:
                    image_result = image_target_np + strength * (image_result - image_target_np)
                return torch.from_numpy(image_result)
            except Exception as e:
                logger.error(f"[RT_ColorMatch] 处理 {idx} 时错误: {e}")
                return torch.from_numpy(image_target_np)

        # 批量处理：多线程或单线程
        if batch_size > 1:
            max_threads = min(os.cpu_count() or 4, batch_size)
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                out = list(executor.map(process_single, range(batch_size)))
        else:
            out = [process_single(i) for i in range(batch_size)]

        return (torch.stack(out).float().clamp_(0, 1),)
# endregion
