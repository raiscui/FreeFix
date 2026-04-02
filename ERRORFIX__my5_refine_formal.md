## [2026-04-02 04:26:38] [Session ID: omx-1775103327604-vnl611] 问题: 正式 `my5` refine 在 `before_refine.mp4` 阶段因 ffmpeg 路径错误失败

### 现象
- `ours.refine_by_flux --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 已成功完成:
  - `Refiner` 初始化
  - Flux pipeline 加载与 `pipe.to(cuda)`
  - synthetic plan 构建
  - `before_refine` jpg 导出
- 但在拼装 `before_refine.mp4` 时抛出:
  - `FileNotFoundError: [Errno 2] No such file or directory: '/home/rais/FreeFix/.pixi/envs/default/bin/ffmpeg'`

### 原因
- 运行命令里把 `IMAGEIO_FFMPEG_EXE` 错设成了一个并不存在的 `.pixi` 路径
- 当前项目 `.pixi` 环境并没有 `ffmpeg` 可执行文件
- 机器上的真实 ffmpeg 在 `/usr/bin/ffmpeg`

### 修复
- 先把第一次失败产生的半截输出目录完整备份, 避免脏现场混入正式重跑
- 重启时改用:
  - `IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg`
- 其余配置、checkpoint 入口和 `exp_name` 保持不变

### 验证
- 修复后重新启动, 动态日志已确认:
  - 成功越过 `before_refine.mp4` 阶段
  - 成功进入主 refine 循环
  - `run.log` 中已经出现连续训练进度输出
