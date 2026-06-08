import torch


# ── 调用者 ──
#   image_nodes.py → RT_PoissonBlend, RT_BlendInpaint
#   color_nodes.py → RT_ColorMatch
# ⚠️ 修改签名/行为前必须确认以上 3 个调用者兼容！
def select_device(device: str) -> torch.device:
    if device == "cpu":
        return torch.device("cpu")
    if device == "gpu" or (device == "auto" and torch.cuda.is_available()):
        return torch.device("cuda")
    return torch.device("cpu")


__all__ = [
    "select_device",
]