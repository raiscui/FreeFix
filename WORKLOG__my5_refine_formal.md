## [2026-04-02 04:26:38] [Session ID: omx-1775103327604-vnl611] 任务名称: 使用 `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 正式启动 `my5` Flux refine

### 任务内容
- 回读 `my5` 当前正式 refine 配置、旧同名产物和恢复语义
- 备份旧同名 final / resume / point cloud, 避免这次正式 run 被旧结果污染
- 用正确解释器和正确 ffmpeg 路径启动新的正式 `Flux refine`
- 动态确认新 run 越过 `before_refine.mp4` 阶段并进入主 refine 循环

### 完成过程
- 先确认当前 `v3` 配置虽然沿用了旧 `exp_name`, 但现场没有 `refine_resume_state.json`, 因此不会被“已 complete”早退逻辑直接跳过
- 再把以下旧同名交付物备份为 `__formal_rerun_backup_20260402_041941`:
  - `ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`
  - `ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330__resume_latest.pt`
  - `point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
- 启动前预检发现:
  - `direnv exec . python3` 实际落到 `/root/miniconda3/bin/python3`, 不是项目 `.pixi` Python
  - 当前 `v3` 配置真实 `plan_count = 283`, `train-only`, `repeats_per_source = 1`
- 第一次正式启动已成功走到 `before_refine` 导出, 但在 `before_refine.mp4` writer 初始化时报错:
  - `FileNotFoundError: ... /home/rais/FreeFix/.pixi/envs/default/bin/ffmpeg`
- 复核后确认 `.pixi` 里并没有 ffmpeg 可执行文件, 当前机器真实可用入口是 `/usr/bin/ffmpeg`
- 将第一次失败的半截输出目录备份为:
  - `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330__failed_ffmpeg_path_20260402_042533`
- 随后用以下稳定入口重新正式启动:
  - `OMP_NUM_THREADS=1 IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg .pixi/envs/default/bin/python3 -u -m ours.refine_by_flux --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml`
- 动态确认重启后的 run 已成功越过第一次失败点, 并进入主 refine 循环:
  - `pipeline execution device: cuda:0`
  - `synthetic plan ... count=283`
  - `before_refine` 32/32 完成
  - 随后出现主循环训练进度 `0/800 -> ... -> 400/400 ...`

### 总结感悟
- 对复用旧 `exp_name` 的正式重跑, 先隔离旧 final 产物, 比“直接覆盖再观察”稳得多
- `readlink -f .pixi/.../ffmpeg` 这类路径推断不能替代真实 `ls` 或 `which ffmpeg` 验证
- 这次真正需要的不是改代码, 而是把运行入口、ffmpeg 路径和旧产物现场治理做对
## [2026-04-02 08:46:02] [Session ID: omx-1775103327604-vnl611] 任务名称: 补导出 Flux / Kontext refined ply 并完成指标对比

### 任务内容
- 为最终完成的 Flux refined checkpoint 导出 `ply`
- 为最终完成的 Kontext refined checkpoint 导出 `ply`
- 分别运行 Flux / Kontext evaluation
- 汇总 base / Flux / Kontext 的 train/test 指标差异

### 完成过程
- 先导出两份 refined point cloud:
  - `point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
  - `point_cloud_kontext_pose_jitter_train_kontext.ply`
- 随后发现当前磁盘上的 `v3` yaml 已经切到 Kontext `exp_name`, 因此为 Flux 额外生成一份只用于 evaluation 的临时 yaml:
  - `/tmp/freefix_my5_flux_eval_20260402T084602Z.yaml`
- 用 `ours.evaluation --eval_test` 重新跑两边评估, 产出:
  - Flux: `.../flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/eval/*.json`
  - Kontext: `.../kontext_pose_jitter_train_kontext/eval/*.json`
- 再读取 `35000_{train,test}.json` 与 refined `*_ {train,test}.json`, 并用 `jd` 做 refined json 差异核对

### 总结感悟
- 这轮真正重要的不是“有没有 refined 结果”, 而是把 Flux / Kontext 放回同一个 base 指标基线下比较
- 当前这组结果里, Kontext 在 train/test 的 `PSNR / SSIM / LPIPS` 三项上都优于 Flux
- 对这种多轮重跑任务, `exp_name` 和评估配置一定要与真实 checkpoint 对齐, 否则很容易读错结果
