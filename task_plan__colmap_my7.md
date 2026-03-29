# 任务计划: 基于 my7_nomask_v1 做 FastGS -> FreeFix bridge 与 Flux refine

## [2026-03-28 15:53:37] [Session ID: 75b3a1b3-0719-49e9-adc0-80fc3ad65971] [记录类型]: 建立 my7 支线计划并完成首轮事实核对

## 目标

- 参考 `my6` 已跑通的 `flux_shinkai_museum_v2_fastgs_my6_nomask_v1_35000_fixsh_rerun` 流程。
- 使用 `/home/rais/FastGS/output/my7_nomask_v1/checkpoints/ckpt_35000.pth` 转成 FreeFix bridge checkpoint。
- 在 FreeFix 里基于 `my7_colmap_fastgs` 真实跑一轮 Flux refine。
- 核对 refined checkpoint、最终 point cloud 和评估结果。

## 阶段

- [x] 阶段1: 回读 `my6` 支线并确认 `my7` 输入事实
- [ ] 阶段2: 生成 `my7` 的 FreeFix 契约与 refine 配置
- [ ] 阶段3: 执行 bridge + refine + 导出 point cloud
- [ ] 阶段4: 核对产物并补记录

## 关键问题

1. `my7` 的原始 FastGS checkpoint 是否存在:
   - 已验证事实:
     - `/home/rais/FastGS/output/my7_nomask_v1/checkpoints/ckpt_35000.pth` 存在。
     - `cfg_args` 指向的数据目录是 `/root/autodl-tmp/home/rais/FastGS/data/my7_colmap_fastgs`。
2. `my7` 当前是否已经有可复用的 FreeFix `base_dir`:
   - 已验证事实:
     - `outputs/my7*`、`exp_cfg/my7`、`data/fastgs_bridge/my7_nomask_v1` 当前都不存在。
   - 当前结论:
     - 需要先补 `my7` 的配置、`cfg.json` 契约和 bridge 目录。
3. `my7` 的 train/test 切分能否直接沿用 `my6`:
   - 已验证事实:
     - FastGS `test/ours_35000/gt = 41`
     - FastGS `train/ours_35000/gt = 283`
     - FreeFix `Parser + Dataset(test_every=8)` 动态验证得到:
       - `total = 324`
       - `train = 283`
       - `test = 41`
   - 已验证结论:
     - `my7` 可以沿用 `my6` 的:
       - `refine_start_idx: 0`
       - `refine_end_idx: 41`
       - `train_start_idx: 0`
       - `train_end_idx: 283`

## 做出的决定

- 决定1: 支线统一使用后缀 `__colmap_my7`。
- 决定2: 这轮优先复用 `my6` 的训练契约和 Flux refine 参数, 不额外引入新变量。
- 决定3: `my7` 先创建独立 `base_dir`, 再用 bridge checkpoint 作为 refine 的真实输入, 避免覆盖任何 `my6` 结果。

## 状态

**目前在阶段2** - `my7` 的 checkpoint、数据目录和 split 事实已核对完成, 现在开始生成专用配置与运行契约。

## [2026-03-28 15:56:59] [Session ID: 75b3a1b3-0719-49e9-adc0-80fc3ad65971] [记录类型]: `my7` 配置与运行契约已就绪, 转入真实执行

## 阶段

- [x] 阶段1: 回读 `my6` 支线并确认 `my7` 输入事实
- [x] 阶段2: 生成 `my7` 的 FreeFix 契约与 refine 配置
- [ ] 阶段3: 执行 bridge + refine + 导出 point cloud
- [ ] 阶段4: 核对产物并补记录

## 关键问题

1. 真实运行前的最小契约是否已经齐备:
   - 已验证事实:
     - 已创建:
       - `exp_cfg/my7/recon_my7_colmap_fastgs_stable_35k_dense.yaml`
       - `exp_cfg/my7/flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.yaml`
       - `outputs/my7_colmap_fastgs_stable_35k_dense/cfg.json`
       - `outputs/my7_colmap_fastgs_stable_35k_dense/ckpts/`
       - `data/fastgs_bridge/my7_nomask_v1/`
     - `ours.run_fastgs_refine --dry-run` 已成功打印出:
       - bridge
       - refine
       - export
       三段真实命令
   - 已验证结论:
     - 现在可以直接启动真实 bridge + refine 流程。
2. 这轮 bridge 输出是否需要显式固定:
   - 已验证事实:
     - wrapper 的默认 bridge 输出仍可能与其它 `35000` 来源撞名。
   - 已验证结论:
     - 继续显式固定到 `data/fastgs_bridge/my7_nomask_v1/ckpt_35000_freefix.pt` 更稳。

## 做出的决定

- 决定4: `my7` 继续沿用 `my6` 的显式 bridge 输出策略, 避免默认文件名和其它 `35000` 来源冲突。

## 状态

**目前在阶段3** - `my7` 的配置、`cfg.json` 和 dry-run 已通过, 现在开始跑真实 bridge + refine + point cloud 导出。

## [2026-03-28 16:22:55] [Session ID: 75b3a1b3-0719-49e9-adc0-80fc3ad65971] [记录类型]: `my7` bridge、refine、导出与评估全部完成

## 阶段

- [x] 阶段1: 回读 `my6` 支线并确认 `my7` 输入事实
- [x] 阶段2: 生成 `my7` 的 FreeFix 契约与 refine 配置
- [x] 阶段3: 执行 bridge + refine + 导出 point cloud
- [x] 阶段4: 核对产物并补记录

## 关键问题

1. 真实 bridge/refine/export 是否完整成功:
   - 已验证事实:
     - `ours.run_fastgs_refine` 退出码为 `0`
     - bridge 输出:
       - `data/fastgs_bridge/my7_nomask_v1/ckpt_35000_freefix.pt`
     - refined checkpoint:
       - `outputs/my7_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.pt`
     - final ply:
       - `outputs/my7_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_fastgs_my7_nomask_v1_35000_fixsh_rerun.ply`
   - 已验证结论:
     - `my7` 的 FastGS -> FreeFix -> Flux refine 主链路已真实跑通。
2. 关键中间产物是否齐全:
   - 已验证事实:
     - `before_refine/*.jpg = 41`
     - `refine/render/* = 41`
     - `refine/gen/* = 41`
     - `refine/depth/* = 41`
     - `after_refine/*.jpg = 41`
     - `refine/masks/*/*.jpg = 123`
   - 已验证结论:
     - 这轮 refine 的中间证据链完整。
3. 当前量化结果如何:
   - 已验证事实:
     - bridge base `35000_test.json`:
       - `PSNR = 21.090533419353207`
       - `SSIM = 0.7887053794977141`
       - `LPIPS = 0.5076869995128818`
     - bridge base `35000_train.json`:
       - `PSNR = 21.330377086733762`
       - `SSIM = 0.7935950878230927`
       - `LPIPS = 0.49953793436815375`
     - refined `..._test.json`:
       - `PSNR = 21.339683951401128`
       - `SSIM = 0.7886283921032418`
       - `LPIPS = 0.5100315903745046`
     - refined `..._train.json`:
       - `PSNR = 21.51363738771041`
       - `SSIM = 0.7908771360299612`
       - `LPIPS = 0.506397417387777`
     - refined 相比 bridge base:
       - `test`: `PSNR +0.2492`, `SSIM -0.0001`, `LPIPS +0.0023`
       - `train`: `PSNR +0.1833`, `SSIM -0.0027`, `LPIPS +0.0069`
   - 已验证结论:
     - 这组 `my6` 复用参数在 `my7` 上不是纯负收益。
     - 它带来了小幅 `PSNR` 提升, 但 `SSIM` 与 `LPIPS` 有轻微回退。

## 做出的决定

- 决定5: 本轮交付口径以“bridge + refine + export + eval 全部跑通”收口。
- 决定6: 当前 `my7` 结果应视为一组已完成的可复用 refine 分支, 是否继续调参要看你更看重 `PSNR` 还是更看重 `LPIPS / SSIM`。

## 状态

**目前已完成** - `my7` 的 FastGS checkpoint 已完成 FreeFix bridge、Flux refine、PLY 导出和 base/refined 双评估。
