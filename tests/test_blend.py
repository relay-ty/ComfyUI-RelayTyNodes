import torch
import torchvision.transforms as T
import numpy as np

# 创建一个简单的测试mask：中心是白色方块
mask = torch.zeros((1, 100, 100))
mask[:, 25:75, 25:75] = 1.0  # 中心白色方块

print("原始mask:")
print("中心区域值:", mask[0, 50, 50].item())  # 应该是1.0
print("边缘外侧值:", mask[0, 10, 10].item())   # 应该是0.0
print("边缘处值:", mask[0, 25, 25].item())   # 应该是1.0

# 应用高斯模糊
kernel = 15
sigma = 10.0
transform = T.GaussianBlur(kernel_size=(kernel, kernel), sigma=(sigma, sigma))
blurred_mask = transform(mask)

print("\n模糊后的mask:")
print("中心区域值:", blurred_mask[0, 50, 50].item())  # 仍接近1.0
print("边缘外侧值(10,10):", blurred_mask[0, 10, 10].item())   # 原来0，现在应该>0了（向外扩展）
print("边缘外侧值(20,20):", blurred_mask[0, 20, 20].item())   # 检查扩展范围
print("边缘内侧值(30,30):", blurred_mask[0, 30, 30].item())   # 检查内部变化
print("边缘处值(25,25):", blurred_mask[0, 25, 25].item())   # 边缘现在是渐变的

# 查看一些具体点
print("\n具体点的mask值变化:")
points = [(50,50), (35,35), (30,30), (25,25), (20,20), (15,15), (10,10)]
for y,x in points:
    orig = mask[0, y, x].item()
    blur = blurred_mask[0, y, x].item()
    print(f"({y},{x}): 原始={orig:.3f}, 模糊后={blur:.3f}, 变化={blur-orig:.3f}")
