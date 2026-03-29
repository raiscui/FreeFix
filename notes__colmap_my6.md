## [2026-03-28 00:00:00] [Session ID: 113355] 笔记: my6 FastGS -> FreeFix refine 的最小运行契约

## 来源

### 来源1: `my5 fixsh rerun` 参考配置

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/recon_my5_colmap_fastgs_stable_35k_dense.yaml`
- 要点:
  - `my5` 的专用 refine 线是:
    - `base_dir: outputs/my5_colmap_fastgs_stable_35k_dense`
    - `exp_name: flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun`
  - refine 参数使用:
    - `strength: 0.65`
    - `refine_steps: 400`
    - `warp_ratio: 0.3`
  - 训练契约保持:
    - `test_every: 8`
    - `refine_stop_iter: 9000`
    - `pose_opt: true`
    - `app_opt: false`
    - `depth_loss: true`

### 来源2: `ours.refine_by_flux` 与 `ours.run_fastgs_refine`

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`
- 要点:
  - refine 会先读取:
    - `base_dir/cfg.json`
  - 运行时可覆盖:
    - `--colmap-path`
    - `--ckpt-path`
  - `run_fastgs_refine` 负责串联:
    - `recon.import_fastgs`
    - `ours.refine_by_flux`
    - `recon.export_3dgs_ply`
  - 如果 bridge 输出沿用默认文件名:
    - `outputs/fastgs_bridge/ckpt_35000_freefix.pt`
    - 会和别的 `35000` 来源撞名

### 来源3: `my6` 原始输入与动态验证

- 路径:
  - `/root/autodl-tmp/home/rais/FastGS/output/my6_nomask_v1/checkpoints/ckpt_35000.pth`
  - `/home/rais/FastGS/data/my6_colmap_fastgs`
- 动态证据:
  - `ckpt_35000.pth` 存在
  - FastGS `cfg_args` 显示:
    - `source_path='/root/autodl-tmp/home/rais/FastGS/data/my6_colmap_fastgs'`
    - `eval=True`
  - FastGS 渲染结果数量:
    - `test/ours_35000/gt = 41`
    - `train/ours_35000/gt = 283`
  - FreeFix 动态计算:
    - `total = 324`
    - `train = 283`
    - `test = 41`

## 综合发现

### 现象

- `my6` 当前只有 FastGS 原始训练结果。
- 它还没有像 `my5` 那样现成的 FreeFix `base_dir`。

### 当前结论

- `my6` 不需要先补跑一整轮 FreeFix 训练, 但必须先准备:
  - `recon` 契约 YAML
  - `base_dir/cfg.json`
  - `base_dir/ckpts/`
- `my6` 的 refine 索引范围可以直接使用:
  - `refine_start_idx: 0`
  - `refine_end_idx: 41`
  - `train_start_idx: 0`
  - `train_end_idx: 283`
- 这轮最稳的 bridge 输出路径是:
  - `data/fastgs_bridge/my6_nomask_v1/ckpt_35000_freefix.pt`

## [2026-03-28 11:41:10] [Session ID: 113355] 笔记: my6 `fixsh_rerun` 真实执行结果

## 来源

### 来源1: `ours.run_fastgs_refine` 真实执行

- 命令:
  - `.pixi/envs/default/bin/python -m ours.run_fastgs_refine --ckpt-path ../FastGS/output/my6_nomask_v1/checkpoints/ckpt_35000.pth --colmap-path /home/rais/FastGS/data/my6_colmap_fastgs --exp-cfg exp_cfg/my6/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun.yaml --bridge-output data/fastgs_bridge/my6_nomask_v1/ckpt_35000_freefix.pt`
- 动态证据:
  - bridge 阶段输出:
    - `gaussian_count: 74398`
  - export 阶段输出:
    - `gaussian_count: 198394`
    - `property_count: 62`
  - 进程退出码:
    - `0`

### 来源2: refine 输出目录核对

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my6_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun`
- 动态证据:
  - `before_refine/*.jpg = 41`
  - `refine/gen/*.jpg = 41`
  - `after_refine/*.jpg = 41`
  - `refine/masks/*/*.jpg = 123`
  - `before_refine.mp4`:
    - `h264`
    - `1280x720`
    - `12 fps`
    - `41` 帧

### 来源3: 真实评估结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my6_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun/eval/35000_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my6_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun/eval/35000_train.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my6_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun/eval/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my6_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun/eval/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun_train.json`
- 动态证据:
  - base test:
    - `PSNR 26.7898`
    - `SSIM 0.8661`
    - `LPIPS 0.1905`
  - base train:
    - `PSNR 26.8858`
    - `SSIM 0.8682`
    - `LPIPS 0.1894`
  - refined test:
    - `PSNR 25.9604`
    - `SSIM 0.8538`
    - `LPIPS 0.2149`
  - refined train:
    - `PSNR 26.0352`
    - `SSIM 0.8554`
    - `LPIPS 0.2131`

## 综合发现

### 现象

- `my6` 的 bridge、refine 和导出都是真实跑通的。
- 但当前这组 refine 参数在 `my6` 上没有带来更好的 GT 指标。

### 当前结论

- `my6` 的 bridge base 已经是可直接评估、可直接导出的稳定结果。
- 当前 `fixsh_rerun` 参数在 `my6` 上的量化变化为:
  - `test`: `PSNR -0.8293`, `SSIM -0.0123`, `LPIPS +0.0244`
  - `train`: `PSNR -0.8506`, `SSIM -0.0128`, `LPIPS +0.0237`
- 如果后续继续追 `my6` 的 refine, 更合理的方向是减弱参数而不是直接沿用当前强度。
