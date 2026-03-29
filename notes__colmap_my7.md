## [2026-03-28 15:53:37] [Session ID: 75b3a1b3-0719-49e9-adc0-80fc3ad65971] 笔记: my7 FastGS -> FreeFix refine 的首轮事实核对

## 来源

### 来源1: `/home/rais/FastGS/output/my7_nomask_v1`

- 要点:
  - `checkpoints/ckpt_35000.pth` 存在。
  - `cfg_args` 记录:
    - `source_path='/root/autodl-tmp/home/rais/FastGS/data/my7_colmap_fastgs'`
    - `eval=True`
  - FastGS 当前已有:
    - `train/ours_35000`
    - `test/ours_35000`
    - `videos`

### 来源2: FastGS 渲染结果计数

- 动态证据:
  - `test/ours_35000/gt = 41`
  - `train/ours_35000/gt = 283`
  - `test/ours_35000/renders = 41`
  - `train/ours_35000/renders = 283`

### 来源3: FreeFix `Parser + Dataset(test_every=8)` 动态验证

- 动态证据:
  - `[Parser] 324 images, taken by 1 cameras.`
  - `{'total': 324, 'train': 283, 'test': 41, 'test_indices_preview': [0, 8, 16, 24, 32, 40, 48, 56, 64, 72]}`

### 来源4: `my6` 已跑通配置

- 路径:
  - `exp_cfg/my6/recon_my6_colmap_fastgs_stable_35k_dense.yaml`
  - `exp_cfg/my6/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun.yaml`
  - `outputs/my6_colmap_fastgs_stable_35k_dense/cfg.json`
- 要点:
  - `my6` 采用:
    - `result_dir: outputs/my6_colmap_fastgs_stable_35k_dense`
    - `test_every: 8`
    - `app_opt: false`
    - `depth_loss: true`
  - refine 参数采用:
    - `strength: 0.65`
    - `refine_steps: 400`
    - `warp_ratio: 0.3`
    - `hessian_attr: ["means", "quats", "scales"]`

## 综合发现

### 现象

- `my7` 当前只有 FastGS 原始训练结果, 还没有对应的 FreeFix `base_dir` 和配置文件。
- 但它的 train/test 切分和 `my6` 一致。

### 当前结论

- `my7` 可以直接沿用 `my6` 的配置骨架和 refine 索引范围。
- 这轮真正需要替换的主要是:
  - `data_dir`
  - `result_dir / base_dir`
  - `exp_name`
  - bridge 输出目录

### 下一步

- 新建 `exp_cfg/my7/recon_my7_colmap_fastgs_stable_35k_dense.yaml`
- 新建 `exp_cfg/my7/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.yaml`
- 生成 `outputs/my7_colmap_fastgs_stable_35k_dense/cfg.json`
- 执行 `ours.run_fastgs_refine`

## [2026-03-28 15:56:59] [Session ID: 75b3a1b3-0719-49e9-adc0-80fc3ad65971] 笔记: my7 dry-run 与运行契约核对

## 来源

### 来源1: 新建的 my7 配置与契约文件

- 路径:
  - `exp_cfg/my7/recon_my7_colmap_fastgs_stable_35k_dense.yaml`
  - `exp_cfg/my7/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.yaml`
  - `outputs/my7_colmap_fastgs_stable_35k_dense/cfg.json`
- 要点:
  - `data_dir` 已切到 `/home/rais/FastGS/data/my7_colmap_fastgs`
  - `base_dir / result_dir` 已切到 `outputs/my7_colmap_fastgs_stable_35k_dense`
  - `exp_name` 已切到 `flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun`
  - refine 参数保持与 `my6` 一致:
    - `strength: 0.65`
    - `refine_steps: 400`
    - `warp_ratio: 0.3`

### 来源2: `ours.run_fastgs_refine --dry-run`

- 动态证据:
  - 已成功打印:
    - `python -m recon.import_fastgs`
    - `python -m ours.refine_by_flux`
    - `python -m recon.export_3dgs_ply`
  - bridge 输出路径:
    - `data/fastgs_bridge/my7_nomask_v1/ckpt_35000_freefix.pt`
  - 最终 PLY 输出路径:
    - `outputs/my7_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.ply`

## 综合发现

### 当前结论

- `my7` 的运行契约已经完整。
- 当前没有看到路径错绑、结果目录错指向或输出撞名的问题。

### 下一步

- 启动真实 `ours.run_fastgs_refine`
- 完成后核对 bridge checkpoint、refined checkpoint、最终 PLY 和图像输出

## [2026-03-28 16:22:55] [Session ID: 75b3a1b3-0719-49e9-adc0-80fc3ad65971] 笔记: my7 真实执行结果与量化对照

## 来源

### 来源1: `ours.run_fastgs_refine` 真实执行

- 命令:
  - `.pixi/envs/default/bin/python -m ours.run_fastgs_refine --ckpt-path /home/rais/FastGS/output/my7_nomask_v1/checkpoints/ckpt_35000.pth --colmap-path /home/rais/FastGS/data/my7_colmap_fastgs --exp-cfg exp_cfg/my7/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.yaml --bridge-output data/fastgs_bridge/my7_nomask_v1/ckpt_35000_freefix.pt`
- 动态证据:
  - bridge 阶段输出:
    - `gaussian_count: 35704`
  - export 阶段输出:
    - `gaussian_count: 72075`
    - `property_count: 62`
  - 进程退出码:
    - `0`

### 来源2: refine 输出目录核对

- 路径:
  - `outputs/my7_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun`
- 动态证据:
  - `before_refine/*.jpg = 41`
  - `refine/render/* = 41`
  - `refine/gen/* = 41`
  - `refine/depth/* = 41`
  - `after_refine/*.jpg = 41`
  - `refine/masks/*/*.jpg = 123`

### 来源3: 真实评估结果

- 命令:
  - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my7/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.yaml --colmap-path /home/rais/FastGS/data/my7_colmap_fastgs --ckpt-path /root/autodl-tmp/home/rais/FreeFix/data/fastgs_bridge/my7_nomask_v1/ckpt_35000_freefix.pt --eval_test`
- 路径:
  - `outputs/my7_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun/eval/35000_test.json`
  - `outputs/my7_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun/eval/35000_train.json`
  - `outputs/my7_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun/eval/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun_test.json`
  - `outputs/my7_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun/eval/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun_train.json`
- 动态证据:
  - base test:
    - `PSNR 21.0905`
    - `SSIM 0.7887`
    - `LPIPS 0.5077`
  - base train:
    - `PSNR 21.3304`
    - `SSIM 0.7936`
    - `LPIPS 0.4995`
  - refined test:
    - `PSNR 21.3397`
    - `SSIM 0.7886`
    - `LPIPS 0.5100`
  - refined train:
    - `PSNR 21.5136`
    - `SSIM 0.7909`
    - `LPIPS 0.5064`

## 综合发现

### 现象

- `my7` 的 bridge、refine、导出和评估都是真实跑通的。
- 和 `my6` 不同, 这次 refine 在 `PSNR` 上有小幅提升。
- 但 `SSIM` 与 `LPIPS` 没有同步变好。

### 当前结论

- `my7` 当前这组 `fixsh_rerun` 参数的量化变化为:
  - `test`: `PSNR +0.2492`, `SSIM -0.0001`, `LPIPS +0.0023`
  - `train`: `PSNR +0.1833`, `SSIM -0.0027`, `LPIPS +0.0069`
- 如果后续继续追 `my7` 的 refine, 更合理的方向不是“盲目继续加大强度”, 而是围绕:
  - `strength`
  - `warp_ratio`
  - `prompt`
  做更克制的小步调参。
