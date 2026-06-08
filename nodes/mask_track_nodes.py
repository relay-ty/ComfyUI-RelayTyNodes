"""
遮罩跟踪节点实现

此模块包含与视频跟踪相关的遮罩操作节点。

节点列表：
- RT_SeparateMasks: 将Mask序列分离为多个独立区域，并跟踪每个区域在视频帧中的轨迹
- RT_GetTrack: 从打包的tracks中根据索引提取单条轨迹遮罩
"""

import logging
import gc
import torch
import numpy as np

logger = logging.getLogger(__name__)

try:
    import scipy.ndimage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("scipy不可用，RT_SeparateMasks 将返回原始Mask")

from ..utils import RelayNodeBase


# region RT_GetTrack
# RT获取Track节点
class RT_GetTrack(RelayNodeBase):
    """
    RT获取Track节点

    功能说明：
    - 输入 RT_SeparateMasks 输出的打包tracks
    - 根据索引取出指定的单条track

    输入：
    - all_tracks: (num_tracks, B, H, W) - 打包的tracks
    - track_index: int - 要获取的track索引（从0开始）

    输出：
    - track: (B, H, W) - 指定索引的单条track遮罩

    错误处理：
    - 输入维度不正确时返回空遮罩并记录警告
    - 索引越界时自动 clamp 到有效范围
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "all_tracks": ("MASK", {"tooltip": "打包的tracks，形状 (num_tracks, B, H, W) — 即 RT_SeparateMasks 的 all_tracks 输出"}),
                "track_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 999,
                    "step": 1,
                    "tooltip": "要获取的track索引（从0开始）。越界时自动 clamp 到 [0, num_tracks-1]"
                }),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("track",)
    FUNCTION = "get_track"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT获取Track

## 功能
从 RT_SeparateMasks 输出的打包tracks中，根据索引取出指定的单条track遮罩。

## 输入
- 全部轨迹: 打包的tracks，(num_tracks, B, H, W)

## 输出
- 轨迹: (B, H, W) 指定索引的单条track遮罩

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 轨迹索引 | 0 | 要获取的track索引（从0开始），越界自动clamp |

## 使用建议
- 配合 RT_SeparateMasks 使用，提取单条轨迹后送入遮罩处理流程
- 多条轨迹时创建多个 RT_GetTrack 节点分别提取
"""

    def __init__(self):
        super().__init__()

    def get_track(self, all_tracks, track_index=0):
        if all_tracks.dim() != 4:
            logger.warning(
                f"RT_GetTrack: 输入维度应为4 (num_tracks, B, H, W)，"
                f"当前 dim={all_tracks.dim()}, shape={all_tracks.shape}"
            )
            if all_tracks.dim() == 3:
                return (all_tracks,)
            if all_tracks.dim() == 2:
                return (all_tracks.unsqueeze(0),)

        num_tracks, batch_size, height, width = all_tracks.shape

        if track_index < 0 or track_index >= num_tracks:
            clamped_idx = max(0, min(track_index, num_tracks - 1))
            logger.warning(
                f"RT_GetTrack: track_index={track_index} 越界 "
                f"(num_tracks={num_tracks})，已 clamp 到 {clamped_idx}"
            )
            track_index = clamped_idx

        return (all_tracks[track_index],)
# endregion


# region RT_SeparateMasks
# RT遮罩分离节点（视频跟踪）
class RT_SeparateMasks(RelayNodeBase):
    """
    RT遮罩分离 + 视频跟踪节点

    功能说明：
    - 输入一组Mask序列（代表视频帧）
    - 分离每个帧中未连接的区域
    - 根据位置和面积相似度跟踪不同帧中的同一遮罩
    - 输出所有遮罩的跨帧轨迹

    应用场景：
    - 视频中多个遮罩的分离和跟踪
    - 视频分割后的instance跟踪
    - 运动物体追踪（多目标）

    注意：
        核心算法依赖 scipy.ndimage.label（连通区域标记），
        属于纯 CPU numpy 操作，无法使用 adaptive_process 加速。
        但通过 ComfyUI ProgressBar 提供了完整的进度反馈。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "masks": ("MASK", {"tooltip": "输入Mask序列，形状 (B, H, W)"}),
                "area_threshold": ("INT", {
                    "default": 32,
                    "min": 1,
                    "max": 100000,
                    "step": 1,
                    "tooltip": "面积阈值（像素）：小于此面积的连通区域被忽略"
                }),
                "similarity_threshold": ("FLOAT", {
                    "default": 0.3,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": "面积相似度阈值（0~1）：相邻帧同一track的面积比低于此值视为不同物体"
                }),
            },
            "optional": {
                "max_tracks": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 32,
                    "step": 1,
                    "tooltip": "最大跟踪数量，0 表示不限制。超出部分按面积排序截断"
                }),
            }
        }

    RETURN_TYPES = ("MASK", "INT")
    RETURN_NAMES = ("all_tracks", "num_tracks")
    FUNCTION = "separate"
    CATEGORY = "RelayTyNodes"
    DESCRIPTION = """
# RT遮罩分离

## 功能
将Mask序列分离为多个独立区域，并跟踪每个区域在视频帧中的轨迹。

## 输入
- 遮罩序列: Mask序列，形状 (B, H, W)

## 输出
- 全部轨迹: 所有轨迹打包，形状 (num_tracks, B, H, W)
- 轨迹数量: 实际轨迹数量

## 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 面积阈值 | 32 | 像素面积，小于此值的连通区域被忽略 |
| 相似度阈值 | 0.3 | 相邻帧同一track面积比低于此值视为不同物体 |
| 最大跟踪数 | 0 | 0=不限制；>0 按面积排序保留前N条track |

## 跟踪算法
1. 对每帧进行连通区域标记（scipy.ndimage.label）
2. 计算每个区域的中心点和面积，按面积从大到小排序
3. 帧间贪心匹配：优先匹配距离近且面积相似的区域
4. 未匹配的区域分配给空闲track（新出现的物体）

## 使用建议
- 大 mask 区域快速变化 → 降低相似度阈值（如 0.1）
- 多个大小相近物体 → 提高相似度阈值（如 0.6）
- 配合 RT_GetTrack 提取单条轨迹遮罩

## 注意
需要scipy支持，未安装则返回原始Mask。
"""

    def __init__(self):
        super().__init__()

    @staticmethod
    def _make_progress_bar(total, desc):
        pbar = None
        try:
            from comfy.utils import ProgressBar
            pbar = ProgressBar(total)
        except ImportError:
            pass

        def update(n=1):
            if pbar:
                pbar.update(n)
        return pbar, update

    @staticmethod
    def _label_all_frames(masks, batch_size, height, width, area_threshold, update):
        frame_regions = []
        max_regions_per_frame = 0

        for b in range(batch_size):
            mask_np = masks[b].cpu().numpy().astype(np.uint8)

            structure = np.ones((3, 3), dtype=np.int8)
            labeled, num_components = scipy.ndimage.label(mask_np, structure=structure)

            regions = []
            for component in range(1, num_components + 1):
                component_mask = (labeled == component)
                area = int(np.sum(component_mask))

                if area >= area_threshold:
                    y_indices, x_indices = np.where(component_mask)
                    center_y = float(np.mean(y_indices))
                    center_x = float(np.mean(x_indices))

                    regions.append({
                        "area": area,
                        "center": (center_y, center_x),
                        "mask": component_mask.astype(np.float32),
                    })

            regions.sort(key=lambda x: -x["area"])
            frame_regions.append(regions)
            max_regions_per_frame = max(max_regions_per_frame, len(regions))

            del mask_np, labeled
            update(1)

        return frame_regions, max_regions_per_frame

    @staticmethod
    def _track_regions(frame_regions, batch_size, max_regions_per_frame, similarity_threshold):
        tracks = [[None] * batch_size for _ in range(max_regions_per_frame)]

        for idx, region in enumerate(frame_regions[0][:max_regions_per_frame]):
            tracks[idx][0] = region

        for b in range(1, batch_size):
            current_regions = frame_regions[b]

            available_tracks = [
                t for t in range(max_regions_per_frame)
                if tracks[t][b - 1] is not None
            ]

            used_regions = set()
            used_tracks = set()

            pairs = []
            for t in available_tracks:
                last_region = tracks[t][b - 1]
                for r_idx, region in enumerate(current_regions):
                    dist = np.sqrt(
                        (last_region["center"][0] - region["center"][0]) ** 2
                        + (last_region["center"][1] - region["center"][1]) ** 2
                    )
                    min_area = min(last_region["area"], region["area"])
                    max_area = max(last_region["area"], region["area"])
                    area_ratio = min_area / max(max_area, 1)

                    if area_ratio >= similarity_threshold:
                        pairs.append((dist, t, r_idx))

            pairs.sort()

            for dist, t, r_idx in pairs:
                if r_idx in used_regions or t in used_tracks:
                    continue
                tracks[t][b] = current_regions[r_idx]
                used_regions.add(r_idx)
                used_tracks.add(t)

            for r_idx, region in enumerate(current_regions):
                if r_idx in used_regions:
                    continue
                for t in range(max_regions_per_frame):
                    if all(tracks[t][pb] is None for pb in range(b)):
                        tracks[t][b] = region
                        break

        return tracks

    @staticmethod
    def _build_output_tracks(tracks, batch_size, height, width):
        outputs = []
        for t in range(len(tracks)):
            track_tensor = torch.zeros((batch_size, height, width), dtype=torch.float32)

            for b in range(batch_size):
                if tracks[t][b] is not None:
                    track_tensor[b] = torch.from_numpy(tracks[t][b]["mask"])

            if track_tensor.max() > 0:
                outputs.append(track_tensor)

        if len(outputs) == 0:
            return (
                torch.zeros((1, batch_size, height, width), dtype=torch.float32),
                0,
            )

        all_tracks = torch.stack(outputs, dim=0)
        return all_tracks, len(outputs)

    def separate(self, masks, area_threshold=32, similarity_threshold=0.3, max_tracks=0):
        if not HAS_SCIPY:
            logger.warning("scipy不可用，返回原始Mask")
            if masks.dim() == 2:
                return (masks.unsqueeze(0), 1)
            if masks.dim() == 3:
                return (masks.unsqueeze(0), 1)
            return (masks, 1)

        if masks.dim() == 2:
            masks = masks.unsqueeze(0)

        batch_size, height, width = masks.shape

        _create_pbar, _update = RT_SeparateMasks._make_progress_bar(batch_size, "RT遮罩分离")

        frame_regions, max_regions_per_frame = RT_SeparateMasks._label_all_frames(
            masks, batch_size, height, width, area_threshold, _update
        )

        if max_tracks > 0:
            max_regions_per_frame = min(max_regions_per_frame, max_tracks)

        if max_regions_per_frame == 0:
            logger.info("RT遮罩分离：未检测到任何有效区域")
            return (torch.zeros((1, batch_size, height, width), dtype=torch.float32), 0)

        tracks = RT_SeparateMasks._track_regions(frame_regions, batch_size, max_regions_per_frame, similarity_threshold)

        all_tracks, num_tracks = RT_SeparateMasks._build_output_tracks(tracks, batch_size, height, width)

        gc.collect()
        return (all_tracks, num_tracks)
# endregion