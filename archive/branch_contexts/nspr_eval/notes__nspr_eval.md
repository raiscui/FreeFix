## [2026-04-01 07:08:15] [Session ID: 4138] 笔记: `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 的 `NSPR/PSNR` 口径核对

## 来源

### 来源1: 实验配置与正式产物

- 文件:
  - [exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml)
  - [run.log](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/run.log)
- 要点:
  - 当前实验名确实存在, 对应输出目录也已完整落盘。
  - 配置里 `test_split: train`。
  - `before_refine/after_refine` 的固定窗口是 `refine_start_idx=0` 到 `refine_end_idx=100`。
  - 训练池与 synthetic source pool 都包含 `[train, test]`, 日志里也明确提示 benchmark 会被污染。

### 来源2: 评估代码路径

- 文件:
  - [ours/evaluation.py](/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py)
  - [recon/refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
  - [ours/refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)
- 要点:
  - 项目里原生定义的指标只有:
    - `PSNR`
    - `SSIM`
    - `LPIPS`
  - 没有任何真实叫 `NSPR` 的评估字段。
  - `ours.evaluation` 的 test 循环使用 `range(cfg.refine_start_idx, cfg.refine_end_idx)`。
  - 当前配置的 `refine_end_idx=100`, 但 `my5` 的真实 test split 只有 `41` 张, 所以这条默认脚本在本配置上不适合直接作为 test 指标真相源。
  - `ours.refine_by_flux` 里的 `before_refine/after_refine` 固定窗口默认不传 split, 会落到 `cfg.test_split`。
  - 由于当前配置 `test_split=train`, 所以 before/after 的 `100` 张固定窗口实际上是前 `100` 张 train 图。

### 来源3: 数据划分与 checkpoint 存在性

- 动态验证:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/cfg.json` 显示:
    - `data_dir=/home/rais/FastGS/data/my5_colmap_fastgs`
    - `test_every=8`
    - `partition=None`
  - 因此数据集回退到按 `test_every=8` 做互斥划分。
  - 实际 `Dataset` 长度:
    - `train=283`
    - `test=41`
  - 相关 checkpoint 已存在:
    - base: [ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt)
    - refined: [ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt)

### 来源4: 动态重算结果

- 验证命令:
  - `direnv exec . .pixi/envs/default/bin/python -u - <<'PY' ... Refiner.render(..., eval=True) ... PY`
- 评估口径:
  - `test_split_eval`: 原始 test split 的 `41` 张
  - `fixed_window_train_eval`: 当前实验 before/after 固定窗口对应的前 `100` 张 train 图
  - `full_train_eval`: 全量 `283` 张 train 图
- 动态结果:
  - base `test_split_eval`:
    - `PSNR 26.7527`
    - `SSIM 0.8826`
    - `LPIPS 0.2231`
  - refined `test_split_eval`:
    - `PSNR 27.9998`
    - `SSIM 0.9015`
    - `LPIPS 0.1849`
  - delta `test_split_eval`:
    - `PSNR +1.2470`
    - `SSIM +0.0189`
    - `LPIPS -0.0383`
  - base `fixed_window_train_eval`:
    - `PSNR 27.3972`
    - `SSIM 0.8918`
    - `LPIPS 0.2173`
  - refined `fixed_window_train_eval`:
    - `PSNR 28.4914`
    - `SSIM 0.9070`
    - `LPIPS 0.1809`
  - delta `fixed_window_train_eval`:
    - `PSNR +1.0942`
    - `SSIM +0.0153`
    - `LPIPS -0.0364`
  - base `full_train_eval`:
    - `PSNR 26.7943`
    - `SSIM 0.8837`
    - `LPIPS 0.2213`
  - refined `full_train_eval`:
    - `PSNR 27.9318`
    - `SSIM 0.9002`
    - `LPIPS 0.1845`
  - delta `full_train_eval`:
    - `PSNR +1.1376`
    - `SSIM +0.0165`
    - `LPIPS -0.0368`

## 综合发现

### 现象

- 用户提到的 `NSPR` 在仓库里找不到对应指标实现。
- 项目里真正存在的是 `PSNR / SSIM / LPIPS`。
- 当前实验的 benchmark 语义天然不干净, 因为配置明确把 `test` split 纳入了训练与 synthetic source pool。

### 当前结论

- 如果把用户的 `NSPR` 按 `PSNR` 理解, 那么:
  - 按原 `test` split 的 `41` 张重算, refined `PSNR = 27.9998`
  - 按当前 before/after 固定窗口的 `100` 张 train 图重算, refined `PSNR = 28.4914`
  - 按完整 `train` split 的 `283` 张重算, refined `PSNR = 27.9318`
- 其中最贴近“固定窗口 before/after 观感”的是 `28.4914`。
- 最贴近“按 test split 仍然算一下”的是 `27.9998`, 但它不是干净 benchmark。

### 仍未确认的部分

- 用户口中的 `NSPR` 是否就是单纯口误写成了 `PSNR`。
- 如果用户想问的是别的自定义指标, 需要用户给出确切定义或上游口径。
