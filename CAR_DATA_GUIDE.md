# 车辆点云数据处理指南

## 快速开始

### 步骤 1：转换 PCD 到 PLY

你的点云是 PCD 格式，需要先转换为 PLY 格式。

#### 单个文件转换：

```bash
python convert_pcd_to_ply.py /mnt/zongrx/dynamic_point/075/1743646156115_23.pcd \
    --output dataset/car_data/car_075_23.ply \
    --max_points 30000 \
    --downsample uniform
```

**参数说明：**
- `input`: 输入 PCD 文件路径
- `--output`: 输出 PLY 文件路径（可选，默认与输入同名）
- `--max_points`: 最大点数（默认 30000）
- `--downsample`: 降采样方法
  - `uniform`: 随机均匀采样（快）
  - `voxel`: 体素降采样（保持结构，推荐）

#### 批量转换（如果有多个文件）：

```bash
# 转换整个目录
python convert_pcd_to_ply.py /mnt/zongrx/dynamic_point/075/ \
    --output dataset/car_data/ \
    --max_points 30000 \
    --downsample voxel
```

### 步骤 2：运行 PointDreamer 重建

```bash
# 单个文件
python demo.py --config configs/car_noisy.yaml --pc_file dataset/car_data/car_075_23.ply

# 批量处理（处理整个目录）
python demo.py --config configs/car_noisy.yaml --pc_file dataset/car_data/
```

### 步骤 3：查看结果

结果保存在：`output_car/[文件名]_car_noisy/models/model_normalized.obj`

使用 Meshlab 或 Blender 打开：
```bash
# 使用 Meshlab（如果已安装）
meshlab output_car/car_075_23_car_noisy/models/model_normalized.obj

# 或者使用 Blender
blender output_car/car_075_23_car_noisy/models/model_normalized.obj
```

---

## 配置参数调整

如果默认配置效果不好，可以调整 `configs/car_noisy.yaml`：

### 1. 如果几何重建效果差（网格破碎、有洞）

尝试传统方法：
```yaml
geo_from: 'SPR'  # 从 'POCO' 改为 'SPR'
```

或者在转换时保留更多点：
```bash
python convert_pcd_to_ply.py input.pcd --max_points 50000  # 增加到 50000（会变慢）
```

### 2. 如果纹理在边界有伪影

尝试多层级 NBF：
```yaml
edge_dilate_kernels: [21, 11, 7, 5, 3, 1]  # 从 [21] 改为多层级
```

或者关闭 NBF：
```yaml
edge_dilate_kernels: [0]
```

### 3. 如果车辆不完整，缺失部分很多

增加视角数量：
```yaml
view_num: 12  # 从 8 增加到 12 或 16
```

改变完整方式：
```yaml
complete_unseen_by: 'optimize'  # 从 'neighbor' 改为 'optimize'（慢但效果好）
```

### 4. 如果速度太慢

减少视角：
```yaml
view_num: 4  # 减少到 4
```

使用快速纹理生成：
```yaml
texture_gen_method: 'linear'  # 从 'DDNM_inpaint' 改为 'linear'（快但质量差）
```

---

## 输出文件说明

运行完成后，输出目录结构：

```
output_car/car_075_23_car_noisy/
├── models/
│   ├── model_normalized.obj  ← 最终带纹理的网格（用这个！）
│   ├── model_normalized.mtl  ← 材质文件
│   └── model_normalized.png  ← 纹理贴图
├── geo/
│   └── ...                   ← 中间几何文件
├── others/
│   ├── 0_sparse.png          ← 视角 0 的稀疏投影
│   ├── 0_inpainted.png       ← 视角 0 的修补结果
│   ├── 0_mask0.png           ← 前景 mask
│   ├── 0_mask2.png           ← 需要修补的区域
│   └── atlas_wo_background.png  ← UV 纹理图集
└── input_pc.ply              ← 归一化后的输入点云
```

---

## 常见问题

### Q1: 转换脚本报错 "No module named 'plyfile'"

```bash
pip install plyfile
```

### Q2: 点云颜色看起来不对

检查 PCD 文件的 RGB 字段格式。有些 PCD 文件使用打包的 RGB 格式（单个 float），需要解包：

如果遇到这种情况，修改 `convert_pcd_to_ply.py` 中的颜色读取部分。

### Q3: 重建速度很慢（每个样本 > 5 分钟）

- 确保你使用的是 GPU（CUDA）
- 减少 `view_num` 参数
- 使用 `texture_gen_method: 'linear'` 而不是 `DDNM_inpaint`

### Q4: 内存不足 (Out of Memory)

- 减少 `max_points`（转换时）
- 降低 `xatlas_texture_res`（从 1024 改为 512）
- 减少 `view_num`

### Q5: 我想使用我的稀疏视角图像

目前 PointDreamer 不直接支持外部图像输入。如果需要，你需要：
1. 修改 `demo.py` 的 `get_inpainted_images` 函数
2. 添加相机参数匹配逻辑
3. 在有外部图像的视角直接加载图像而不是修补

这是一个高级功能，需要理解代码和相机几何。

---

## 性能参考

**测试环境：** NVIDIA A100 GPU

| 配置 | view_num | texture_gen_method | 时间/样本 |
|------|----------|-------------------|----------|
| 快速 | 4 | linear | ~30s |
| 默认 | 8 | DDNM_inpaint | ~60s |
| 高质量 | 12 | DDNM_inpaint | ~90s |

---

## 下一步

1. 先用默认配置测试一个样本
2. 检查结果质量
3. 根据结果调整参数
4. 批量处理所有数据

祝重建顺利！
