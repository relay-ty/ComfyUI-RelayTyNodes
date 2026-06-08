#!/usr/bin/env python3
import torch
import torchvision.transforms as T

# 创建一个简单的测试mask：中心是白色方块
mask = torch.zeros((1, 1, 100, 100))  # (B, C, H, W)
mask[:, :, 25:75, 25:75] = 1.0  # 中心白色方块

# 应用高斯模糊
kernel = 15
sigma = 10.0
transform = T.GaussianBlur(kernel_size=(kernel, kernel), sigma=(sigma, sigma))
blurred_mask = transform(mask)

# 保存结果，让我们直接检查数值
with open('blend_test_result.txt', 'w', encoding='utf-8') as f:
    f.write("原始mask:\n")
    f.write(f"中心区域值 (50,50): {mask[0,0,50,50].item():.4f}\n")
    f.write(f"边缘外侧 (10,10): {mask[0,0,10,10].item():.4f}\n")
    f.write(f"边缘处 (25,25): {mask[0,0,25,25].item():.4f}\n")
    
    f.write("\n模糊后的mask:\n")
    f.write(f"中心区域值 (50,50): {blurred_mask[0,0,50,50].item():.4f}\n")
    f.write(f"边缘外侧 (10,10): {blurred_mask[0,0,10,10].item():.4f}\n")
    f.write(f"边缘外侧 (20,20): {blurred_mask[0,0,20,20].item():.4f}\n")
    f.write(f"边缘内侧 (30,30): {blurred_mask[0,0,30,30].item():.4f}\n")
    f.write(f"边缘处 (25,25): {blurred_mask[0,0,25,25].item():.4f}\n")
    
    f.write("\n具体点的mask值变化:\n")
    points = [(50,50), (35,35), (30,30), (25,25), (20,20), (15,15), (10,10)]
    for y,x in points:
        orig = mask[0,0,y,x].item()
        blur = blurred_mask[0,0,y,x].item()
        f.write(f"({y},{x}): 原始={orig:.3f}, 模糊后={blur:.3f}, 变化={blur-orig:.3f}\n")

print("测试结果已保存到 blend_test_result.txt")
