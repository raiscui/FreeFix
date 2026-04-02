# 任务计划: 基于 my6_nomask_v1 做 FastGS -> FreeFix bridge 与 Flux refine

## [2026-03-28 00:00:00] [Session ID: 113355] [记录类型]: 建立 my6 支线计划并完成首轮事实核对

## 目标

- 参考 `my5` 的 `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun` 口径。
- 使用 `../FastGS/output/my6_nomask_v1/checkpoints/ckpt_35000.pth` 转成 FreeFix bridge checkpoint。
- 在 FreeFix 里基于 `my6_colmap_fastgs` 真实跑一轮 Flux refine。
- 核对 refine 产物目录、refined checkpoint 和导出的 point cloud。

## 阶段

- [x] 阶段1: 回读 `my5 fixsh rerun` 流程并确认 `my6` 输入事实
- [ ] 阶段2: 生成 `my6` 的 FreeFix 训练契约与 refine 配置
- [ ] 阶段3: 执行 bridge + refine + 导出 point cloud
- [ ] 阶段4: 核对产物并补记录

## 关键问题

1. `my6` 的原始 FastGS checkpoint 是否存在:
   - 已验证事实:
     - `../FastGS/output/my6_nomask_v1/checkpoints/ckpt_35000.pth` 存在。
     - 文件时间为 `2026-03-28 18:02`。
2. `my6` 当前是否已经有可复用的 FreeFix `base_dir`:
   - 已验证事实:
     - `outputs/` 下未命中 `my6` 对应目录。
   - 当前结论:
     - 需要先补 `my6` 的 FreeFix 配置与 `cfg.json` 契约。
3. refine 入口最少依赖什么:
   - 已验证事实:
     - `ours.refine_by_flux` 会先读取 `base_dir/cfg.json`。
     - `--colmap-path` 和 `--ckpt-path` 可以运行时覆盖数据目录与基础 checkpoint。
   - 当前结论:
     - 不必先真实训练 `my6` FreeFix 基线, 但必须先准备合法的 `cfg.json`。

## 做出的决定

- 决定1: 支线统一使用后缀 `__colmap_my6`。
- 决定2: 这轮沿用 `my5 35k` 的训练骨架参数和 Flux refine 参数。
- 决定3: `my6` 先创建独立 `base_dir`, 再用 bridge checkpoint 作为 refine 的真实输入, 避免覆盖任何 `my5` 结果。

## 状态

**目前在阶段2** - 已确认 `my6` 的 checkpoint、数据目录和 refine 入口依赖, 现在开始生成 `my6` 的 FreeFix 契约与 refine 配置。

## [2026-03-28 00:00:00] [Session ID: 113355] [记录类型]: `my6` 配置与运行契约已就绪, 转入真实执行

## 阶段

- [x] 阶段1: 回读 `my5 fixsh rerun` 流程并确认 `my6` 输入事实
- [x] 阶段2: 生成 `my6` 的 FreeFix 训练契约与 refine 配置
- [ ] 阶段3: 执行 bridge + refine + 导出 point cloud
- [ ] 阶段4: 核对产物并补记录

## 关键问题

1. `my6` 的 split 长度是否已经和原始 FastGS 结果对齐:
   - 已验证事实:
     - FastGS `test/ours_35000/gt` 文件数为 `41`
     - FastGS `train/ours_35000/gt` 文件数为 `283`
     - FreeFix `Parser + Dataset(test_every=8)` 计算得到:
       - `total = 324`
       - `train = 283`
       - `test = 41`
   - 已验证结论:
     - `my6` 可以沿用和 `my5` 一样的:
       - `refine_start_idx: 0`
       - `refine_end_idx: 41`
       - `train_start_idx: 0`
       - `train_end_idx: 283`
2. 真实运行前的最小契约是否已经齐备:
   - 已验证事实:
     - 已创建:
       - `exp_cfg/my6/recon_my6_colmap_fastgs_stable_35k_dense.yaml`
       - `exp_cfg/my6/flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun.yaml`
       - `outputs/my6_colmap_fastgs_stable_35k_dense/cfg.json`
       - `outputs/my6_colmap_fastgs_stable_35k_dense/ckpts/`
       - `data/fastgs_bridge/my6_nomask_v1/`
     - `ours.run_fastgs_refine --dry-run` 已成功打印出:
       - bridge
       - refine
       - export
       三段真实命令
   - 已验证结论:
     - 现在可以直接启动真实 bridge + refine 流程

## 做出的决定

- 决定4: bridge 输出显式固定到 `data/fastgs_bridge/my6_nomask_v1/ckpt_35000_freefix.pt`, 避免默认文件名和其他 `35000` 来源冲突。

## 状态

**目前在阶段3** - `my6` 的配置、`cfg.json` 和 dry-run 已通过, 现在开始跑真实 bridge + refine + point cloud 导出。

## [2026-03-28 11:41:10] [Session ID: 113355] [记录类型]: `my6` bridge、refine、导出与评估全部完成

## 阶段

- [x] 阶段1: 回读 `my5 fixsh rerun` 流程并确认 `my6` 输入事实
- [x] 阶段2: 生成 `my6` 的 FreeFix 训练契约与 refine 配置
- [x] 阶段3: 执行 bridge + refine + 导出 point cloud
- [x] 阶段4: 核对产物并补记录

## 关键问题

1. 真实 bridge/refine/export 是否完整成功:
   - 已验证事实:
     - `ours.run_fastgs_refine` 退出码为 `0`
     - bridge 输出:
       - `data/fastgs_bridge/my6_nomask_v1/ckpt_35000_freefix.pt`
     - refined checkpoint:
       - `outputs/my6_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun.pt`
     - final ply:
       - `outputs/my6_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun.ply`
   - 已验证结论:
     - `my6` 的 FastGS -> FreeFix -> Flux refine 主链路已真实跑通
2. 关键中间产物是否齐全:
   - 已验证事实:
     - `before_refine/*.jpg = 41`
     - `refine/gen/*.jpg = 41`
     - `after_refine/*.jpg = 41`
     - `refine/masks/*/*.jpg = 123`
     - `before_refine.mp4`:
       - `h264`
       - `1280x720`
       - `12 fps`
       - `41` 帧
   - 已验证结论:
     - 这轮 refine 的可视化与中间证据链完整
3. 当前量化结果如何:
   - 已验证事实:
     - bridge base `35000_test.json`:
       - `PSNR = 26.789751983270413`
       - `SSIM = 0.8660964602377357`
       - `LPIPS = 0.1905317891661714`
     - bridge base `35000_train.json`:
       - `PSNR = 26.885772678119135`
       - `SSIM = 0.8681562502898091`
       - `LPIPS = 0.18941189145978685`
     - refined `..._test.json`:
       - `PSNR = 25.96044777660835`
       - `SSIM = 0.8537763313549321`
       - `LPIPS = 0.21491573423874089`
     - refined `..._train.json`:
       - `PSNR = 26.035200294251997`
       - `SSIM = 0.8553645463377343`
       - `LPIPS = 0.2130649968613163`
     - refined 相比 bridge base:
       - `test`: `PSNR -0.8293`, `SSIM -0.0123`, `LPIPS +0.0244`
       - `train`: `PSNR -0.8506`, `SSIM -0.0128`, `LPIPS +0.0237`
   - 已验证结论:
     - 当前这组 `fixsh_rerun` 参数在 `my6` 上和 `my5` 一样, 会拉低 GT 指标

## 做出的决定

- 决定5: 本轮交付口径以“bridge + refine + export + eval 全部跑通”收口。
- 决定6: 当前 `my6` 的默认量化基线应优先看 bridge base, 不直接把这组 refine 结果当成更优模型。

## 状态

**目前已完成** - `my6` 的 FastGS checkpoint 已完成 FreeFix bridge、Flux refine、PLY 导出和 base/refined 双评估。
