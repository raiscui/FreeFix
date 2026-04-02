## [2026-04-02 04:18:58] [Session ID: omx-1775103327604-vnl611] 笔记: `my5` 正式 Flux refine 启动前预检

## 来源

### 来源1: 当前配置与磁盘现场

- 文件:
  - `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/cfg.json`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/`
- 要点:
  - 当前 `v3` 配置沿用了旧 `exp_name = flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`
  - 当前没有同名输出目录, 也没有 `refine_resume_state.json`
  - 但旧同名 final checkpoint / rolling resume checkpoint / point cloud 还在
  - 已在正式启动前把它们备份为 `__formal_rerun_backup_20260402_041941`

### 来源2: 代码恢复语义核对

- 文件:
  - `ours/refine_backend_runner.py`
- 要点:
  - “检测到本次 refine 已完整完成, 且最终 checkpoint 已存在, 跳过重复执行” 这条早退逻辑依赖 `refine_resume_state.json`
  - 当前现场没有该 state 文件, 所以直接启动不会被旧 final checkpoint 短路
  - 但如果不先备份旧 final 产物, 新 run 半途失败时会留下误导现场

### 来源3: 启动环境预检

- 命令:
  - `direnv exec . bash -lc 'which python3 && python3 -V && which ffmpeg'`
  - `OMP_NUM_THREADS=1 .pixi/envs/default/bin/python3 - <<'PY' ... build_refine_view_plan ... PY`
- 要点:
  - `direnv exec . python3` 当前落到 `/root/miniconda3/bin/python3`, 不是项目 `.pixi` Python
  - 稳定入口应明确使用 `.pixi/envs/default/bin/python3`
  - `.pixi` 内 `python3 = 3.11.10`
  - `.pixi` 内 `ffmpeg = /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/ffmpeg`
  - 当前 `v3` 配置实际展开:
    - `plan_count = 283`
    - `train_pool_count = 283`
    - `splits = ('train',)`
    - `repeats_per_source = 1`

## 综合发现

### 已验证结论

- 这次正式 run 应该使用 `.pixi/envs/default/bin/python3`, 并显式带 `OMP_NUM_THREADS=1`
- 当前 `v3` 配置虽然沿用了旧 `exp_name` 的 `x3` 字样, 但真实执行口径已经是 `train-only + repeat=1`
- 正式启动前已完成必要的旧产物隔离, 可以安全起跑

## [2026-04-02 04:24:19] [Session ID: omx-1775103327604-vnl611] 笔记: 第一次正式启动在 `before_refine.mp4` 阶段失败

## 来源

### 来源1: 首次正式 run 的动态日志

- 文件:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/run.log`
- 要点:
  - 这次 run 已经成功走到:
    - `pipe.to(cuda) 返回`
    - `pipeline execution device: cuda:0`
    - `synthetic plan ... count=283`
    - `开始导出 before_refine`
  - 随后在 `rebuild_video_from_frame_dir(... before_refine.mp4 ...)` 里失败
  - traceback 末尾是:
    - `FileNotFoundError: [Errno 2] No such file or directory: '/home/rais/FreeFix/.pixi/envs/default/bin/ffmpeg'`

### 来源2: ffmpeg 路径核对

- 命令:
  - `pwd`
  - `ls -l /home/rais/FreeFix/.pixi/envs/default/bin/ffmpeg`
  - `ls -l /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/ffmpeg`
  - `which ffmpeg`
- 要点:
  - 当前 shell `PWD=/home/rais/FreeFix`
  - `.pixi/envs/default/bin/ffmpeg` 在这两个绝对路径下都不存在
  - 当前机器实际可用 ffmpeg 是 `/usr/bin/ffmpeg`

## 综合发现

### 已验证结论

- 第一次正式 run 失败点是 `before_refine.mp4` 的 ffmpeg writer 初始化, 不是 refine 主链路
- 根因是我把 `IMAGEIO_FFMPEG_EXE` 错指到了一个不存在的 `.pixi` 路径
- 这次半截输出应先完整备份, 再用 `/usr/bin/ffmpeg` 干净重启

## [2026-04-02 05:45:06] [Session ID: omx-1775103327604-vnl611] 笔记: Kontext 正式 run 的第一份中途进度证据

## 来源

### 来源1: `kontext_pose_jitter_train_kontext` 的恢复状态与帧计数

- 文件:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_pose_jitter_train_kontext/refine_resume_state.json`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_pose_jitter_train_kontext/refine/render/`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_pose_jitter_train_kontext/refine/gen/`
- 要点:
  - `plan_total = 283`
  - `latest_completed_plan_index = 24`
  - `next_plan_index = 25`
  - `status = synthetic_in_progress`
  - 当前帧计数:
    - `refine/render = 50`
    - `refine/gen = 49`
    - `refine/depth = 50`
  - `before_refine_complete = true`
  - `after_refine_complete = false`

## 综合发现

### 已验证结论

- Kontext 正式 run 已稳定进入主循环, 不是停在启动阶段
- rolling resume checkpoint 已经切换成 Kontext 自己的同名输出:
  - `ckpt_kontext_pose_jitter_train_kontext__resume_latest.pt`
- 当前最合理的做法是继续等待 Kontext 完整结束, 然后立刻接 evaluation 和最终对比
