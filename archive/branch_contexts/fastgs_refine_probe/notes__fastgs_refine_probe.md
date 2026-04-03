## [2026-03-27 09:28:12] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] 笔记: FastGS 与 FreeFix checkpoint / PLY / 坐标系契约对齐

## 来源

### 来源1: `/home/rais/FastGS/train.py` 与 `/home/rais/FastGS/scene/gaussian_model.py`

- 要点:
  - `FastGS` 保存 checkpoint 的语句是 `torch.save((gaussians.capture(...), iteration), checkpoint_path)`。
  - `capture()` 的核心训练态字段顺序是:
    - `active_sh_degree`
    - `_xyz`
    - `_features_dc`
    - `_features_rest`
    - `_scaling`
    - `_rotation`
    - `_opacity`
    - 后面再跟优化器状态和 `spatial_lr_scale`
  - `save_ply()` 写出的字段顺序是:
    - `x/y/z`
    - `nx/ny/nz`
    - `f_dc_*`
    - `f_rest_*`
    - `opacity`
    - `scale_*`
    - `rot_*`

### 来源2: `/home/rais/FreeFix/recon/refiner.py` 与 `/home/rais/FreeFix/recon/trainer.py`

- 要点:
  - `Refiner` 当前默认读取 `cfg.result_dir/ckpts/ckpt_<step>.pt`。
  - 它期望的最小 SH 参数化字段是:
    - `means`
    - `opacities`
    - `quats`
    - `scales`
    - `sh0`
    - `shN`
  - `app_opt=true` 的训练线不会保存 `sh0/shN`, 而是保存:
    - `features`
    - `colors`

### 来源3: 动态样本 `/home/rais/FastGS/output/my4_mask_guarded_v4/checkpoints/ckpt_30000.pth`

- 要点:
  - 动态读取结果:
    - `_xyz`: `(55441, 3)`
    - `_features_dc`: `(55441, 1, 3)`
    - `_features_rest`: `(55441, 15, 3)`
    - `_scaling`: `(55441, 3)`
    - `_rotation`: `(55441, 4)`
    - `_opacity`: `(55441, 1)`
  - 这些形状和 `FreeFix` 的 SH checkpoint 结构是同构的, 只差命名、`opacity` 维度和外层容器。

### 来源4: 动态样本 `/home/rais/FastGS/output/my4_mask_guarded_v4/point_cloud/iteration_30000/point_cloud.ply`

- 要点:
  - 头部字段与 `FreeFix` 的 [export_3dgs_ply.py](/home/rais/FreeFix/recon/export_3dgs_ply.py) 导出产物同构。
  - 这意味着即使只有 `point_cloud.ply`, 也能恢复为 `means/sh0/shN/scales/quats/opacities` 这类高斯参数。

### 来源5: 动态相机对齐验证

- 要点:
  - `FastGS` run `my4_mask_guarded_v4` 使用的数据源是 `/home/rais/FreeFix/data/my4_fullcolmap`。
  - 直接比较 `FastGS/output/.../cameras.json` 与 `FreeFix Parser(data_dir=my4_fullcolmap, normalize=True)` 的 `camtoworlds`:
    - 平均位置误差约 `9.698`
    - 平均旋转矩阵差约 `2.108`
  - 但把 `FastGS` 相机先经过 `parser.transform` 后:
    - 位置误差均值降到接近 `0`
    - 旋转误差均值降到接近 `0`
  - `parser.transform[:3, :3]` 的奇异值三者相同, 说明它是“统一尺度 * 旋转”, 可以稳定作用到高斯位置、旋转、尺度。

## 综合发现

## [2026-03-31 15:53:38] [Session ID: codex-modelscope-rerun-20260331] 笔记: `FLUX.1-dev` 已切到 ModelScope 精简续传

## 来源

### 来源1: 旧整仓下载会话 `86411`

- 要点:
  - 旧会话实际还活着, 不是已经彻底停掉。
  - 它会同时下载:
    - `text_encoder*`
    - `transformer/*`
    - `vae/*`
    - 顶层 `flux1-dev.safetensors`
    - 顶层 `ae.safetensors`
  - 其中顶层 `flux1-dev.safetensors` 对当前 `FluxPipeline.from_pretrained(local_dir, ...)` 路径是冗余下载。

### 来源2: `modelscope download --help`

- 命令:
  - `OMP_NUM_THREADS=1 /home/rais/.local/bin/modelscope download --help`
- 要点:
  - 官方 CLI 明确支持:
    - `--include`
    - `--exclude`
  - 因此可以安全地从“整仓下载”切成“精简下载”。

### 来源3: 本地 `model_index.json` 与仓库内 `ours/pipelines/flux_pipeline.py`

- 要点:
  - `model_index.json` 声明的组件为:
    - `scheduler`
    - `text_encoder`
    - `text_encoder_2`
    - `tokenizer`
    - `tokenizer_2`
    - `transformer`
    - `vae`
  - 当前本地 `FluxPipeline` 也正是按这套 diffusers 目录结构加载。
  - 这进一步说明:
    - 顶层 `flux1-dev.safetensors` 不是当前入口的必需项。

### 来源4: 新精简下载会话 `3152`

- 命令:
  - `OMP_NUM_THREADS=1 /home/rais/.local/bin/modelscope download --model 'black-forest-labs/FLUX.1-dev' --local_dir '/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev' --exclude flux1-dev.safetensors ae.safetensors dev_grid.jpg LICENSE.md`
- 要点:
  - 新会话显示只处理 `6 items`:
    - `text_encoder/model.safetensors`
    - `text_encoder_2/model-00001-of-00002.safetensors`
    - `text_encoder_2/model-00002-of-00002.safetensors`
    - `transformer/diffusion_pytorch_model-00001-of-00003.safetensors`
    - `transformer/diffusion_pytorch_model-00002-of-00003.safetensors`
    - `transformer/diffusion_pytorch_model-00003-of-00003.safetensors`
  - `text_encoder/model.safetensors` 已经正式落盘。
  - `text_encoder_2` 与 `transformer` 当前仍在 `._____temp/` 中续传。

### 来源5: 本地缓存目录快照

- 命令:
  - `find /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev -maxdepth 3 -type f`
  - `du -sh /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev`
  - `df -h /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev`
- 要点:
  - 当前已正式落盘的关键文件包括:
    - `model_index.json`
    - `configuration.json`
    - `scheduler/scheduler_config.json`
    - `tokenizer/*`
    - `tokenizer_2/*`
    - `text_encoder/config.json`
    - `text_encoder/model.safetensors`
    - `text_encoder_2/config.json`
    - `text_encoder_2/model.safetensors.index.json`
    - `transformer/config.json`
    - `transformer/diffusion_pytorch_model.safetensors.index.json`
    - `vae/config.json`
    - `vae/diffusion_pytorch_model.safetensors`
  - 当前模型目录体积已增长到约 `19G`。
  - 文件系统剩余空间约 `124G`, 当前没有磁盘空间风险。

## 综合发现

### 现象

- 当前 rerun 仍未重新启动。
- 当前真正进行中的工作是 ModelScope 精简续传, 而不是 `ours.refine_by_flux` 主流程。

### 已验证结论

- 旧整仓下载已经被停止, 并且不应恢复。
- 新策略已经成功把下载集合收敛为 `6` 个真正缺失的必需权重。
- 当前缓存目录已经具备大部分配置和小组件, 只差 `text_encoder_2` 与 `transformer` 的大权重完成最终落盘。

### 下一步判据

- 当 `text_encoder_2/` 与 `transformer/` 目录下真实出现对应 `.safetensors` 成品文件时:
  - 立即执行本地 `FluxPipeline.from_pretrained(...)` 最小校验
  - 校验通过后立刻启动正式 rerun

## [2026-04-01 00:50:02] [Session ID: codex-rerun-watch-20260401] 笔记: 正式 rerun 已稳定进入 synthetic 主循环

## 来源

### 来源1: 进程与 PTY 动态输出

- 命令:
  - `pgrep -af 'ours\\.refine_by_flux|tee .*run\\.log'`
  - `write_stdin(session_id=6088, chars='')`
- 要点:
  - 当前存在活动进程:
    - `python -u -m ours.refine_by_flux`
    - `tee .../run.log`
  - PTY 持续输出 `0/400 -> 400/400` 的 loss 进度条。
  - 进度条之间还会出现 `0/32 -> 32/32` 的阶段性渲染过程。
  - 这说明当前已经明显越过模型加载和 `ffmpeg` 阻塞, 正在持续执行 synthetic 主流程。

### 来源2: 当前输出目录增量

- 命令:
  - 统计 `before_refine`、`after_refine`、`refine/render`、`refine/gen`、`refine/depth`
- 要点:
  - `before_refine/*.jpg = 100`
  - `before_refine.mp4` 已存在
  - 首次采样:
    - `refine/render = 5`
    - `refine/gen = 5`
    - `refine/depth = 5`
  - 间隔约 20 秒再次采样:
    - `refine/render = 7`
    - `refine/gen = 6`
    - `refine/depth = 7`
  - `after_refine` 当前仍为 `0`, 说明还没到收尾导出阶段。

### 来源3: `generated_cams.jsonl` 与 `pose_jitter_log.jsonl`

- 命令:
  - 读取两个 jsonl 文件末尾几行
- 要点:
  - `generated_cams.jsonl` 当前 `lines=6`, 最后一条是 `plan_index=5`
  - `pose_jitter_log.jsonl` 当前 `lines=7`, 最后一条是 `plan_index=6`
  - 这说明:
    - synthetic plan 至少已经推进到第 `6` 条附近
    - 还在持续采样新的 jitter 相机

### 来源4: `refine_resume_state.json`

- 要点:
  - 当前状态仍是:
    - `status = synthetic_in_progress`
    - `next_plan_index = 0`
    - `latest_completed_plan_index = -1`
  - 这份状态文件暂时没有跟随每个 plan 细粒度刷新。
  - 因此本轮更可靠的真实进度来源是:
    - PTY 实时输出
    - `generated_cams.jsonl`
    - `pose_jitter_log.jsonl`
    - `refine/render|gen|depth` 的文件增长

## 综合发现

### 现象

- rerun 进程仍然存活。
- 产物目录正在持续增长。
- `after_refine` 尚未开始生成。

### 已验证结论

- 这轮 rerun 已稳定进入 synthetic 主循环, 不是假活着。
- 当前进度大约在 `plan_index 5~6 / 972` 附近。
- `refine_resume_state.json` 目前不是这一阶段的最佳进度真相源。

### 下一步判据

- 继续观察 `generated_cams.jsonl` 与 `pose_jitter_log.jsonl` 是否继续前进。
- 当 `after_refine/*.jpg` 开始出现时, 说明主循环已接近完成或进入收尾导出阶段。

## [2026-04-01 01:00:43] [Session ID: codex-rerun-watch-20260401] 笔记: 基于代码语义与短时吞吐的剩余时长估算

## 来源

### 来源1: `ours/refine_by_flux.py` 主循环语义

- 代码位置:
  - `ours/refine_by_flux.py:355-450`
- 要点:
  - 每个 `plan_entry` 的执行顺序是:
    - `refiner.render(...)`
    - 写 `pose_jitter_log.jsonl`
    - 落 `refine/render/*.jpg` 与 `refine/depth/*.jpg`
    - `pipe(...)` 做 Flux 生成
    - 落 `refine/gen/image_*.jpg`
    - 写 `generated_cams.jsonl`
    - `refiner.refine(...)`
    - 达到保存条件时才会打印 `已保存恢复 checkpoint: plan=X/Y`
  - 这说明:
    - `generated_cams.jsonl` 与 `pose_jitter_log.jsonl` 是“进入或完成生成阶段”的证据
    - 但严格完成一个 plan, 还要经过后面的 `refiner.refine(...)`
    - 因而估时应优先参考 checkpoint 口径与短时吞吐, 不能只看 jsonl 行数

### 来源2: 运行中实时日志

- 要点:
  - PTY 实时出现:
    - `已保存恢复 checkpoint: plan=25/972`
  - 这是当前最可靠的“至少完成到 25 条 plan”证据。

### 来源3: 60 秒短时测速

- 采样窗口:
  - `start t=1774976355.9732862`
  - `end t=1774976415.973589`
- 要点:
  - 60 秒内:
    - `generated_cams.jsonl` 从 `plan_index=23` 推进到 `plan_index=25`
    - `pose_jitter_log.jsonl` 从 `plan_index=24` 推进到 `plan_index=26`
  - 保守理解:
    - 近 1 分钟大约推进了 `2` 条 plan 左右
    - 即约 `2 plans/min`

### 来源4: 进程累计运行时长

- 命令:
  - `ps -p 89872 -o etime=,etimes=,pcpu=,pmem=,rss=,cmd=`
- 要点:
  - 当前进程已运行约:
    - `15:02`
    - `etimes=902`
  - 当前 CPU 使用接近 `99.7%`
  - 结合 checkpoint `plan=25/972`:
    - 从启动到现在的平均完成速率大约也在 `1.6 ~ 2.0 plans/min` 量级

## 综合发现

### 现象

- 当前至少已经完成 `25 / 972` 条 plan。
- 最近 60 秒仍在持续前进, 没有卡死迹象。

### 已验证结论

- 按当前真实吞吐估算, 剩余 `947` 条 plan。
- 若按 `2.0 plans/min` 计算:
  - 约 `473.5 分钟`
  - 约 `7.9 小时`
- 若按稍乐观的 `2.2 plans/min` 计算:
  - 约 `430.5 分钟`
  - 约 `7.2 小时`
- 若后续阶段继续维持更快节奏, 可能压到约 `6.3 小时`
  - 这对应约 `2.5 plans/min`
- 但当前更稳妥的口径仍应以 `7 ~ 8 小时` 为主。

### 额外收尾时间

- synthetic 主循环跑完后, 还需要:
  - `refine/gen` 重建视频
  - `after_refine` 固定视角导出
  - `after_refine.mp4` 重建
- 这部分通常还要额外十几分钟量级。

### 当前建议口径

- 对用户汇报:
  - “如果后续速度基本保持当前水平, 剩余大约还要 `7 ~ 8 小时`, 保守按 `8 小时左右` 看更稳。”

## [2026-04-01 01:08:37] [Session ID: codex-rerun-watch-20260401] 笔记: 当前 rerun 的 GPU 利用率呈现分段锯齿, 与主循环阶段切换一致

## 来源

### 来源1: `ours/refine_by_flux.py` 主循环

- 代码位置:
  - `ours/refine_by_flux.py:355`
  - `ours/refine_by_flux.py:393`
  - `ours/refine_by_flux.py:430`
- 要点:
  - 每条 synthetic plan 按严格串行顺序执行:
    - `refiner.render(...)`
    - 保存 `render/depth/masks`
    - `pipe(...)` 做 Flux 生成
    - 保存 `refine/gen`
    - `refiner.refine(..., max_steps=refine_steps)`
  - 当前不是“多 plan 并行”, 而是单 plan 串行。
  - 所以 GPU 利用率天然会随着子阶段切换而波动。

### 来源2: 当前实验配置

- 文件:
  - `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml`
- 要点:
  - `strength: 0.65`
  - `refine_steps: 400`
  - `refine_pipeline_offload_mode: model_cpu`
  - `refine_camera_mode: pose_jitter`
  - `base.yaml` 里 `num_inference_steps: 50`
- 综合解释:
  - `50 * 0.65 -> 32`
  - 当前 PTY 里反复出现的 `0/32` 可以和 Flux 有效 denoise 步数对上。
  - 反复出现的 `0/400` 对应每条 plan 的高斯 refine 训练步数。

### 来源3: `configure_pipeline_offload(...)`

- 文件:
  - `ours/refine_pipeline_runtime.py`
- 要点:
  - `model_cpu` 模式会显式调用:
    - `pipe.enable_model_cpu_offload(device='cuda')`
  - 当前 `run.log` 也已确认本轮确实走了这条路径。
  - 这意味着 Flux pipeline 的重模块会交给 offload hook 迁移和回收。

### 来源4: `recon/refiner.py` 中的 render / refine 细节

- 文件:
  - `recon/refiner.py`
- 要点:
  - `render(...)` 在 `pose_jitter` 模式下会先采样候选相机, 再做渲染。
  - 但本轮 `pose_jitter_log.jsonl` 里多数样本 `attempt_count=1` 且 `alpha_coverage=1.0`
  - 说明“反复重试 jitter 候选”不是当前 GPU 低占用的主因。
  - `refine(...)` 是典型的小粒度单视角循环:
    - 每步只处理 `1` 个 camera
    - 每步都有 `.to(device)`
    - 每步都会 `loss.item()` 更新 `tqdm`
  - 这类循环即便在用 GPU, 也不容易像大 batch 训练那样持续满载。

### 来源5: GPU 动态采样

- 采样1: 20 秒 `nvidia-smi`
  - 观察到:
    - 一段时间 `99% / 24.8GB / 530W+`
    - 随后长段 `8%~10% / 24.8GB / 88~94W`
    - 然后 `70%~78% / 1.7GB / 179~290W`
    - 再次掉到 `8%~14%`
- 采样2: 12 秒 `GPU + compute-app memory`
  - 观察到:
    - `00-07s`: `71% -> 99%`, compute app memory 约 `24.8GB`
    - `08-11s`: `7%~8%`, compute app memory 仍约 `24.8GB`
- 采样3: `nvidia-smi pmon -c 10 -s um`
  - 观察到同一 PID `89872` 在 10 个采样点间出现:
    - `sm=8`
    - `sm=32`
    - `sm=70`
    - `sm=78`
    - `sm=6`
    - `sm=22`

## 综合发现

### 现象

- 用户观察到 GPU 至少有很大一段时间低占用。
- 动态采样证明这种感觉是有依据的, 不是错觉。

### 当前主假设

- 低占用主要来自“单 plan 串行多阶段”叠加“Flux model_cpu offload”。
- 次要来源是 `refiner.refine()` 本身属于小 batch、高频同步的训练循环。

### 备选解释

- 还可能存在额外 CPU / 磁盘同步开销放大空转:
  - `save_image(...)`
  - `depth.cpu().numpy()`
  - `PIL.Image.save(...)`
  - jsonl 追加写入
- 但从当前证据看, 它们更像次要项, 不是最主要项。

### 已验证结论

- 当前这条 rerun 正在交替执行:
  - Flux 32 步生成
  - 400 步高斯 refine
  - 若干 CPU / I/O 边界操作
- GPU 利用率锯齿化是当前执行模型本身的直接结果。
- 其中最值得优先怀疑的性能放大器是:
  - `refine_pipeline_offload_mode: model_cpu`
- 所以“至少一半时间 GPU 没有被有效利用”这个判断, 作为现象描述是成立的。
- 但更精确地说:
  - 它不是单纯“GPU 闲着”
  - 而是当前串行管线里存在大量非满载阶段和 offload / 同步边界。

### 如果以后要优化, 优先级建议

- 第一优先级:
  - 重新评估 `model_cpu` offload 是否仍然必要
- 第二优先级:
  - 减少每条 plan 内的 CPU 边界与落盘频率
- 第三优先级:
  - 评估 `refiner.refine()` 是否能用更大的训练粒度或更少同步点

## [2026-03-31 00:38:00] [Session ID: codex-refine-resume-speed-20260331] 笔记: refine 可恢复链与 fixed render 批量化已在 Flux/SDXL 两条脚本收口

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`

- 要点:
  - `Flux` refine 现在会先读取 `refine_resume_state.json`
  - 若状态已是 `complete` 且 `final_ckpt_path` 真实存在, 会直接退出, 不再重复加载 pipeline
  - `before_refine / after_refine` 已改成 `render_fixed_rgb_batch(...) + rebuild_video_from_frame_dir(...)`
  - synthetic 主循环会周期性写:
    - rolling resume checkpoint
    - `refine_resume_state.json`
    - `refine/generated_cams.jsonl`

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`

- 要点:
  - `SDXL` 已同步到和 `Flux` 同一套恢复路径
  - 之前旧版 `writer` 直写 mp4 的逻辑已去掉
  - 现在也改成:
    - fixed-view batch RGB render
    - synthetic jpg 序列作为真相源
    - mp4 可重建
    - resume state + rolling ckpt

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py` 与 `/root/autodl-tmp/home/rais/FreeFix/recon/refine_runtime.py`

- 要点:
  - `Refiner.rasterize_splats(...)` 原生支持 batched cameras
  - `render_fixed_rgb_batch(...)` 会按分辨率分组后一次性 batch rasterize
  - `refine_runtime.py` 负责:
    - 恢复状态读写
    - stale artifact 清理
    - generated camera 恢复
    - 由 jpg 序列重建 mp4

### 来源4: 本轮静态验证

- 命令:
  - `python3 -m py_compile ours/refine_by_flux.py ours/refine_by_sdxl.py recon/refine_runtime.py recon/refiner.py tests/test_refine_runtime.py tests/test_pose_jitter_refine.py tests/test_refine_view_plan.py tests/test_refine_cli_paths.py`
  - `.pixi/envs/default/bin/python -m unittest tests.test_refine_runtime tests.test_pose_jitter_refine tests.test_refine_view_plan tests.test_refine_cli_paths`
- 关键输出:
  - `py_compile` 通过
  - `Ran 27 tests in 0.138s`
  - `OK`
  - 首轮单测前出现 `libgomp: Invalid value for environment variable OMP_NUM_THREADS`
  - 现场确认当前 shell 的 `OMP_NUM_THREADS=0`
  - 用 `OMP_NUM_THREADS=1` 重跑后, 单测无该报错并继续 `OK`

## 综合发现

### 现象

- `Flux` 的恢复改造已经不是半截状态, 本轮补完后能完整表达:
  - before fixed export
  - synthetic loop
  - after fixed export
  - final checkpoint
- `SDXL` 之前还停在旧逻辑, 现在已经对齐。

### 已验证结论

- 当前 refine 中断恢复的文件级链路已经形成闭环:
  - resume state
  - rolling resume checkpoint
  - generated synthetic camera log
  - stale artifact cleanup
  - jpg -> mp4 rebuild
- “render 图片能不能多个同时生成”这个问题, 当前更合理的答案不是 Python 多线程并发, 而是 fixed-view 走 batch rasterize。
- synthetic 主循环仍不适合直接并行多个 plan:
  - 因为每完成一个 plan, 都会调用 `refiner.refine(...)` 改写当前高斯状态
  - 后一个 plan 的 render 语义依赖前一个 plan 之后的新状态

### 当前边界

- 这轮拿到的是静态证据和纯 Python 测试证据, 不是 GPU 动态 benchmark。
- 当前机器缺少可用 NVIDIA driver, 因此没法在本机补出:
  - fixed-view batch render 的真实耗时收益
  - synthetic 主循环进一步优化方案的 GPU profile

## [2026-03-31 01:05:00] [Session ID: codex-refine-resume-speed-20260331] 笔记: 用户 уточнение 为“jitter render 和 Flux gen 能否并行”

## 来源

### 来源1: GPU 状态

- 命令:
  - `nvidia-smi --query-gpu=name,memory.total,memory.free,utilization.gpu --format=csv,noheader`
- 输出:
  - `NVIDIA RTX PRO 6000 Blackwell Server Edition, 97887 MiB, 97251 MiB, 0 %`

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`

- 要点:
  - 当前主循环顺序是:
    - `refiner.render(...)`
    - `pipe(...)`
    - `refiner.refine(...)`
  - `Flux gen` 明确依赖当轮 `render` 产出的:
    - `rgb_to_refine`
    - `masks`
    - `alpha`

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`

- 要点:
  - `refiner.render(...)` 不是纯 CPU 预处理
  - 它会走 GS rasterization, 还会算 certainty / alpha / depth
  - `refiner.refine(...)` 结束后会改写当前高斯状态

## 综合发现

### 现象

- 现在机器已经有可用 GPU。
- 但用户问的不是 fixed-view 导出, 而是 synthetic 主循环内部:
  - jitter render
  - Flux gen

### 已验证结论

- 同一条 plan 内, `render` 和 `Flux gen` 不能直接并行。
  - 因为 `Flux gen` 的输入就是 `render` 的输出。
- 如果想做“跨 plan 流水线”, 比如:
  - 当前 plan 正在 `Flux gen`
  - 同时去 render 下一条 plan
  - 那在当前语义下也不应该直接这么做
  - 因为下一条 plan 的 render 理应使用上一条 `refiner.refine(...)` 之后的新高斯状态
  - 提前 render 会变成使用旧状态, 语义已经变化

### 工程判断

- 单卡场景下, 就算强行上 CUDA stream 并发:
  - `render` 和 `Flux gen` 也都会抢同一张 GPU
  - `Flux` 通常是更重的主负载
  - 真实收益未必明显, 但显存和调度复杂度会显著上升
- 真正更安全的重叠方向是:
  - CPU 侧提前准备下一条 plan 的元数据
  - 把磁盘写图放后台
  - 而不是让两段 GPU 主计算硬并发

### 值得单独定义的新模式

- 如果后面真的要继续压榨吞吐, 可以考虑“snapshot/chunk pipeline”:
  - 先冻结一份当前 splat snapshot
  - 基于这份 snapshot 一次性 render 多条 jitter plan
  - 再批量做 Flux gen
  - 再统一进入 refine
- 但这已经不是“纯优化”
- 它会改变监督顺序和中间状态语义, 应该作为单独模式而不是默认行为

## [2026-03-31 14:42:00] [Session ID: codex-rerun-flux-20260331] 笔记: rerun 当前阻塞于 Flux 模型来源不可用

## 来源

### 来源1: 新 rerun 的 `run.log`

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/run.log`
- 要点:
  - LPIPS 依赖 `alexnet` 已下载完成
  - `Refiner` 已初始化完成
  - 随后在 `resolve_flux_model_source(cfg)` 处报错退出:
    - `FileNotFoundError: 配置里的 flux_model_path 不存在: /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`

### 来源2: 本机路径检查

- 要点:
  - `~/.cache/modelscope/hub/models/black-forest-labs/...` 下当前没有可用的本地 Flux snapshot
  - 配置里写死的本地路径当前是失效路径

### 来源3: 远端可达性探测

- 命令:
  - `curl -I -L https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/model_index.json`
- 关键返回:
  - `HTTP/2 401`
  - `x-error-code: GatedRepo`
  - `Access to model black-forest-labs/FLUX.1-dev is restricted`

## 综合发现

### 现象

- rerun 不是还在慢慢跑
- 而是已经在冷启动后退出
- 当前输出目录里只有新的 `run.log`, 还没有真正进入 synthetic 主循环

### 已验证结论

- 当前 rerun 的直接阻塞不是 GPU、不是 `Refiner` 初始化、也不是 pose jitter
- 而是 `Flux` 模型来源不可用:
  - 本地配置路径不存在
  - Hugging Face 官方 repo 又是 gated, 当前环境未认证

### 当前边界

- 在没有有效本地 Flux snapshot 或 Hugging Face 访问凭据前, 当前实验无法继续推进到 `FluxPipeline.from_pretrained(...)`

### 现象

- `FastGS` 的高斯内容本身和 `FreeFix` 的 SH 训练线是同类数据。
- `Refiner` 目前只是入口写死了 `FreeFix` 自家的 checkpoint 容器和路径。
- `FastGS` 的 run 里如果有 `.pth`, 可以无损度更高地桥接。
- 如果只有 `point_cloud.ply`, 也仍然有一条可行桥接路线。

### 当前假设

- 对 `app_opt=false` 的 FreeFix 训练线, 可以通过一个小型导入脚本把 `FastGS` 的 `.pth` 或 `.ply` 转成 `FreeFix` `ckpt`。
- 导入时必须同步做一层坐标归一化变换:
  - `means`: 应用 `parser.transform`
  - `quats`: 左乘归一化旋转部分
  - `scales`: 加上统一尺度的 `log(scale)`
- 只要目标 Refine 配置指向相同的数据源, 就不需要复用 `FastGS/cameras.json`。

### 备选解释

- 如果桥接后渲染仍有明显错位, 备选解释不是“字段映射错了”, 而是:
  - 目标 FreeFix 配置用了不同的数据目录
  - 或者用了 `app_opt=true` / 其他不兼容参数化
  - 或者用户想桥接的是只有 PLY、但 PLY 里已经丢失了一部分训练态信息的 run

### 最小实施方向

- 新增 `recon/import_fastgs.py`:
  - 输入 `FastGS` `.pth` 或 `.ply`
  - 输入目标 `data_dir`
  - 输出 `FreeFix` 风格 `ckpt`
- 给 `Refiner` 增加 `load_ckpt_path`
  - 让 `Flux/SDXL` refine 直接吃桥接产物
  - 不必污染已有 `outputs/*/ckpts`

## [2026-03-27 18:04:10] [Session ID: codex-fastgs-path-args-verify] 笔记: 路径参数入口补强后的验证结论

## 来源

### 来源1: 代码复核

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/import_fastgs.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`
- 要点:
  - `import_fastgs.py` 已支持:
    - `--ckpt-path`
    - `--ply-path`
    - `--colmap-path`
  - `refine_by_flux.py / refine_by_sdxl.py` 已支持:
    - `--colmap-path`
    - `--ckpt-path`
  - CLI 传入的 checkpoint 会一路落到 `Refiner(..., load_ckpt_path=...)`

### 来源2: 动态验证命令

- 语法检查:
  - `python3 -m py_compile recon/import_fastgs.py ours/refine_by_flux.py ours/refine_by_sdxl.py recon/refiner.py tests/test_import_fastgs.py tests/test_refine_cli_paths.py`
- 单测:
  - `/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_import_fastgs tests.test_refine_cli_paths tests.test_trainer_eval_path`
- CLI 帮助页:
  - `timeout 10s python3 ours/refine_by_flux.py --help`
  - `timeout 10s python3 ours/refine_by_sdxl.py --help`
- 桥接 smoke:
  - 用临时合成 `ckpt_34.pth`
  - 调用 `python -m recon.import_fastgs --ckpt-path <tmp_ckpt> --colmap-path /root/autodl-tmp/home/rais/FreeFix/data/my4_fullcolmap --output <tmp_out>`

### 来源3: 关键输出

- 单测结果:
  - `Ran 11 tests in 0.049s`
  - `OK`
- `--help` 输出已包含:
  - `--colmap-path COLMAP_PATH`
  - `--ckpt-path CKPT_PATH`
- 桥接 smoke 输出:
  - `[Parser] 264 images, taken by 1 cameras.`
  - `source_format: fastgs_checkpoint`
  - `step: 34`
  - `normalize_enabled: True`
  - `gaussian_count: 1`
  - `{'output_exists': True, 'step': 34, 'normalized_for_freefix': True, 'means_shape': (1, 3)}`

## 综合发现

### 现象

- 参数别名不只是静态存在, 已经被动态验证打通。
- `refine_by_flux.py / refine_by_sdxl.py` 原本存在 CLI 帮助页卡住的问题。

### 已验证结论

- 用户现在可以直接传:
  - `colmap path`
  - `ckpt path`
- 这组参数在桥接脚本和 refine 脚本里都已经可用。
- 为了让帮助页可用, 需要把 `OmegaConf` 以及模型 / 渲染相关重依赖延后到 `parse_args()` 之后再加载。

### 剩余边界

- 这次 bridge/refine 入口仍然是面向 `app_opt=false` 的 SH 训练线。
- “转过来的 ckpt 做 refine” 依然需要目标场景的原始图片和 COLMAP 目录, 因为 FreeFix 仍要自己建 parser、相机和归一化矩阵。

## [2026-03-30 00:59:18] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 多 split / 多 jitter refine 代码收口后的静态结论

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`

- 要点:
  - `Flux` 入口已经切到:
    - `build_real_train_pool(...)`
    - `build_refine_view_plan(...)`
  - synthetic supervise 循环已按 `plan_index / source_split / source_repeat_index / image_id` 跑通整条链路

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`

- 要点:
  - 在本轮之前, `SDXL` 仍然保留旧的 range-based refine 循环
  - 本轮已对齐到和 `Flux` 同一套 plan helper
  - `pose_jitter_log.jsonl` 也已补齐:
    - `plan_index`
    - `source_repeat_index`
    - `image_id`

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml` 与 `/root/autodl-tmp/home/rais/FreeFix/README.md`

- 要点:
  - 新配置键已经正式补入:
    - `refine_train_splits`
    - `refine_camera_source_splits`
    - `pose_jitter_views_per_source`
  - 文档中已明确:
    - `before_refine / after_refine` 仍走固定对比视角
    - 多 split + 多 jitter 会改变 benchmark 语义

### 来源4: 动态验证

- 命令:
  - `python3 -m py_compile ours/refine_by_flux.py ours/refine_by_sdxl.py ours/refine_run_schedule.py recon/refine_view_plan.py recon/refiner.py tests/test_pose_jitter_refine.py tests/test_refine_view_plan.py`
  - `.pixi/envs/default/bin/python -m unittest tests.test_pose_jitter_refine tests.test_refine_view_plan tests.test_refine_cli_paths`
- 关键输出:
  - `py_compile` 通过
  - `Ran 16 tests`
  - `OK`

## 综合发现

### 现象

- `Flux` 和 `SDXL` 现在已经共用同一套多 split / 多 jitter 调度语义
- 计划展开和 pose jitter 日志字段, 已经有轻量测试锁住

### 已验证结论

- 用户要求的这条语义已经落成配置能力:
  - `refine_train_splits: [train, test]`
  - `refine_camera_source_splits: [train, test]`
  - `pose_jitter_views_per_source: 3`
- 当前还没验证的只剩动态长跑层面:
  - 真实场景里 plan 数量是否与预期一致
  - 长跑结束后 checkpoint 是否稳定落盘

### 下一步最小验证

- 先对 `my5` 实景把:
  - train/test 镜头数
  - synthetic plan 总数
  - checkpoint 输出路径
- 做成可观察证据
- 然后再起正式任务

## [2026-03-30 01:05:37] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: `my5` 多 split / 多 jitter smoke 的动态证据

## 来源

### 来源1: 真实 `Refiner` smoke

- 命令:
  - `timeout 300s .pixi/envs/default/bin/python - <<'PY' ...`
- 要点:
  - 读取正式配置:
    - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml`
  - 实际初始化 `Refiner`
  - 实际构造:
    - `build_real_train_pool(...)`
    - `build_refine_view_plan(...)`
  - 实际渲染第一条 pose jitter plan
  - 实际执行 `refiner.save(...)`

### 来源2: 关键输出

- `[Parser] 324 images, taken by 1 cameras.`
- `train_len: 283`
- `test_len: 41`
- `real_train_pool_count: 324`
- `synthetic_plan_count: 972`
- `repeats_per_source: 3`
- `last_plan.source_split: test`
- `last_plan.source_index: 40`
- `last_plan.source_repeat_index: 2`
- `saved_ckpt_exists: true`

## 综合发现

### 现象

- 新配置并不是“纸面上看起来会展开 972 条”
- 它已经在真实 `my5` 数据上被动态算出了 `972`

### 已验证结论

- 当前 `my5` 的 `train + test` 总镜头数就是 `324`
- 每个基镜头抖 `3` 个视角后, synthetic supervise 总数就是 `972`
- `Refiner.save()` 已经能在真实输出目录下成功落盘 probe checkpoint

### 仍未验证部分

- Flux 正式长跑是否会:
  - 跑完整个 `972` synthetic plan
  - 最终也保存正式 refined checkpoint
- 这仍需要正式任务的动态日志来继续确认

## [2026-03-27 18:20:00] [Session ID: codex-fastgs-one-shot-wrapper] 笔记: one-shot wrapper 的参数契约与验证结果

## 来源

### 来源1: 新增脚本

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`
- 要点:
  - wrapper 只负责 orchestration
  - 内部不会复制 bridge 或 refine 的实现
  - 顺序调用:
    - `python -m recon.import_fastgs`
    - `python ours/refine_by_flux.py` 或 `python ours/refine_by_sdxl.py`

### 来源2: 新增回归测试

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/tests/test_run_fastgs_refine.py`
- 要点:
  - 覆盖参数解析
  - 覆盖默认 bridge 输出路径
  - 覆盖 bridge / refine 命令拼接
  - 覆盖按顺序执行与 fail-fast 的 orchestration 行为
  - 覆盖 `python3 ours/run_fastgs_refine.py --help`

### 来源3: 动态验证命令

- 语法检查:
  - `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py`
- 单测:
  - `/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine tests.test_import_fastgs tests.test_refine_cli_paths tests.test_trainer_eval_path`
- CLI 帮助页:
  - `timeout 10s python3 ours/run_fastgs_refine.py --help`
- dry run:
  - `/home/rais/FreeFix/.pixi/envs/default/bin/python ours/run_fastgs_refine.py --ckpt-path <tmp> --colmap-path data/my4_fullcolmap --exp-cfg exp_cfg/my4/flux_shinkai_museum_v2.yaml --dry-run`

### 来源4: 关键输出

- 单测结果:
  - `Ran 17 tests in 0.087s`
  - `OK`
- `--help` 输出已包含:
  - `--ckpt-path`
  - `--ply-path`

## [2026-03-29 11:31:35] [Session ID: codex-add-pose-jitter-apply] 笔记: pose jitter helper 单测需要从 `refiner.py` 解耦

## 来源

### 来源1: 最小导入探测

- 命令:
  - `timeout 20s python3 -c "from recon.refiner import coerce_pose_jitter_triplet; ..."`
  - `timeout 20s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -c "from recon.refiner import coerce_pose_jitter_triplet; ..."`
- 关键输出:
  - 系统 `python3` 直接报 `ModuleNotFoundError: No module named 'torchmetrics'`
  - 项目 `.pixi` 环境里的导入没有立刻失败, 但在 20 秒窗口内一直没返回, 最终 `timeout` 退出码 `124`

### 来源2: `recon/refiner.py` 当前依赖结构

- 顶层 import 会立即拉起:
  - `torchmetrics`
  - `viser`
  - `gsplat`
  - `recon.trainer`
  - `bootstrap_pixi_cuda_env()`
- 这些依赖对真正 refine 运行是合理的, 但对 helper 级单测过重

## 综合发现

### 现象

- 直接从 `recon.refiner` 导入 pose jitter 纯函数, 无法作为“轻量单测入口”使用。

### 当前假设

- 最稳的做法是把纯 pose jitter helper 抽成轻模块。
- `refiner.py` 运行时继续复用这些 helper。
- 单测直接导入轻模块, 避免被整条渲染 / viewer / metrics 依赖链拖慢。

### 最强备选解释

- 也可能不是单个 import 太重, 而是 `recon.trainer` 或 `bootstrap_pixi_cuda_env()` 带来的级联初始化在拖慢启动。
- 但无论根因落在哪一层, 对单测来说结论一样:
  - 不应直接依赖 `recon.refiner` 顶层导入来测试这批纯函数。

### 当前决定

- 后续实现中优先把 pose jitter 纯 helper 抽到轻量模块, 再补单测。

## [2026-03-29 11:44:06] [Session ID: codex-add-pose-jitter-apply] 笔记: pose jitter 真实 Flux smoke 已尝试, 但本轮未完成初始化

## 来源

### 来源1: 轻量动态验证

- 命令:
  - `python3 -m py_compile recon/pose_jitter.py recon/refiner.py ours/refine_by_flux.py ours/refine_by_sdxl.py tests/test_pose_jitter_refine.py tests/test_refine_cli_paths.py`
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_pose_jitter_refine tests.test_refine_cli_paths`
  - `timeout 10s python3 ours/refine_by_flux.py --help`
  - `timeout 10s python3 ours/refine_by_sdxl.py --help`
- 关键输出:
  - `py_compile` 通过
  - `Ran 12 tests in 1.306s`
  - `OK`
  - 两个 `--help` 都能在 10 秒内返回

### 来源2: 真实 smoke 尝试

- 第一次命令:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 ours/refine_by_flux.py --exp_cfg /tmp/pose_jitter_smoke.yaml`
- 关键输出:
  - `ModuleNotFoundError: No module named 'ours'`
- 解释:
  - 这是入口形式问题, 不是 pose jitter 本身出错
  - 该脚本需要按 README 里的模块方式调用:
    - `python3 -m ours.refine_by_flux ...`

### 来源3: 模块方式 smoke

- 第二次命令:
  - `timeout 300s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke.yaml`
- 观测事实:
  - 进程已启动并持续存活一段时间
  - 外部 `ps` 能看到模块进程
  - 但在观察窗口内:
    - 没有 stdout/stderr 新输出
    - 没有创建 `outputs/my5_colmap_fastgs_stable_35k_dense/pose_jitter_smoke_20260329/`
    - 也没有 `refine/pose_jitter_log.jsonl`
  - 为避免无意义长等, 已主动终止该进程

## 综合发现

### 现象

- pose jitter 的代码改动已经通过轻量验证。
- 真实 Flux smoke 这轮只推进到了初始化阶段, 没进入 refine 主循环。

### 当前假设

- 真实 smoke 的阻塞更像是大模型 / 数据 / 渲染栈的冷启动耗时问题。
- 目前没有证据表明 pose jitter 逻辑本身在真实 run 中已经失败。

### 最强备选解释

- 也不能排除还有更深的初始化阻塞, 只是当前没有新的 stdout/stderr 证据。
- 在没有 trace 或更细粒度 profiling 之前, 不能把“长时间无输出”直接定性成 bug。

### 当前结论

- 本轮可以确认:
  - 配置、调用链、fallback、日志写法和 helper 行为已经被动态测试覆盖
- 本轮不能确认:
  - 真实 Flux pose jitter smoke 已完整跑通
- 因此 OpenSpec `4.2` 应暂时保持未勾选

## [2026-03-29 12:17:05] [Session ID: codex-add-pose-jitter-smoke] 笔记: 真实 Flux pose jitter smoke 已定位到 `pipe.to(cuda)` 阶段超时

## 来源

### 来源1: 分段冷启动探针

- 命令:
  - 用 `.pixi` Python 分段导入 `ours.refine_by_flux`、`torch`、`torchvision`、`FluxPipeline`、`Refiner`
- 关键输出:
  - `import ours.refine_by_flux`: 约 `0.002s`
  - `load merged omega config`: 约 `0.492s`
  - `import imageio`: 约 `3.689s`
  - `import torch`: 约 `45.198s`
  - `import torchvision.utils.save_image`: 约 `63.094s`
  - `import FluxPipeline`: 约 `94.912s`
  - `import Refiner + Config`: 约 `100.705s`

### 来源2: 第一轮真实 smoke 加粗阶段日志

- 命令:
  - `timeout 420s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke.yaml`
- 关键输出:
  - `[refine_by_flux] 运行时依赖加载完成`
  - `[refine_by_flux] 开始初始化 Refiner`
  - `[Parser] 324 images, taken by 1 cameras.`
  - `[refine_by_flux] Refiner 初始化完成`
  - `[refine_by_flux] 开始加载 Flux pipeline: ...`
  - 后续看到 pipeline component / checkpoint shard 进度
  - 但在 `420s` 内没有看到:
    - `Flux pipeline 加载完成`
    - `开始创建输出目录`

### 来源3: 第二轮更细阶段日志

- 新增日志边界:
  - `FluxPipeline.from_pretrained 返回`
  - `开始执行 pipe.to(cuda)`
  - `pipe.to(cuda) 返回`
  - `开始替换 scheduler`
- 关键输出:
  - `FluxPipeline.from_pretrained 返回`
  - `开始执行 pipe.to(cuda)`
  - 然后直到 `timeout 420s` 退出
- 同轮现场证据:
  - 没有创建 `outputs/my5_colmap_fastgs_stable_35k_dense/pose_jitter_smoke_20260329/`
  - 没有 `pose_jitter_log.jsonl`
  - `nvidia-smi` 可见该进程占用约 `3650 MiB` 显存

## 综合发现

### 现象

- 真实 pose jitter smoke 不是卡在 CLI、配置合并、`Refiner` 初始化, 也不是卡在 `FluxPipeline.from_pretrained` 本体。
- 当前观测到的最窄阻塞边界是:
  - `pipe.to("cuda")`

### 当前假设

- 在这台机器和这组模型上, `pipe.to("cuda")` 的冷启动耗时本身已经足够长, 会把一个 `420s` 的最小 smoke 窗口吃完。

### 最强备选解释

- 也可能不是单纯“慢”, 而是 `pipe.to("cuda")` 内部某个子模块初始化 / 权重搬运阶段存在更细粒度阻塞。
- 但在当前证据下, 还不能把它直接定性成 bug。

### 当前结论

- OpenSpec `4.2` 这轮仍不能勾选。
- 现在可以非常明确地说:
  - 如果下一轮还要继续跑真实 smoke, 应优先围绕 `pipe.to("cuda")` 继续取证或放宽时间窗口
  - 当前 pose jitter 主链本身尚未拿到“真实首帧跑通”的动态证据
  - `--colmap-path`
  - `--exp-cfg`
  - `--refine-backend`
  - `--dry-run`
- dry run 输出了两条内部命令:
  - 先 `recon.import_fastgs`
  - 后 `ours/refine_by_flux.py`

## 综合发现

### 现象

- 现在用户已经不需要再手工执行“先 bridge, 再 refine”两条命令。
- wrapper 如果不显式固定 `cwd`, 从仓库外目录调用时会有 `python -m recon.import_fastgs` 找不到模块的风险。

### 已验证结论

- `ours/run_fastgs_refine.py` 已经可以作为一条命令入口使用。
- 它默认走 `flux`, 也支持 `--refine-backend sdxl`。
- 子进程现在固定在仓库根目录执行, 因此入口对外部工作目录更稳。

### 当前边界

- wrapper 当前仍然面向 FastGS -> FreeFix `app_opt=false` 这条桥接链路。
- 如果未来要支持 `app_opt=true`, 应该扩展 bridge 参数化本身, 不是只改这个 wrapper。

## [2026-03-27 10:33:50] [Session ID: codex-refine-hessian-attr-explain] 笔记: `hessian_attr` 控制 certainty 掩码的属性来源, 不是冻结列表

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`

- 要点:
  - `Refiner.__init__()` 只是把 `hessian_attr` 保存到 `self.hessian_attr`。
  - 真正使用点在 `rasterize_splats_w_certainty()`:
    - 先对渲染出的 `rgbs[..., :3]` 反传
    - 再取 `self.splats[k].grad.detach() ** 2`
    - 最后把这些属性的 Hessian 近似量拼起来, 生成 `inv_H_gaussian = exp(-exp_index * H)`
  - `_init_optimizer()` 里 `means / scales / quats / opacities / sh0 / shN` 都各自建了优化器, 没有根据 `hessian_attr` 做冻结或白名单裁剪。

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py` 与 `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`

- 要点:
  - `refiner.render(i)` 返回的 `masks` 就是上一步 certainty 渲染产物。
  - 这些 `masks` 会直接传给 Flux / SDXL pipeline 的 `mask=` 参数。

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/ours/schedulers/euler_discrete_scheduler.py` 与 `/root/autodl-tmp/home/rais/FreeFix/ours/schedulers/flow_match_euler_discrete_scheduler.py`

- 要点:
  - guide 阶段融合公式是:
    - `x0 = prior_latents * mask + (1 - mask) * (...)`
  - 这意味着:
    - `mask` 越大, 越偏向保留原始渲染 latent
    - `mask` 越小, 越放开给生成模型 / warp 去改

### 来源4: 最小数值验证

- 命令:
  - `python3 - <<'PY' ... fused = prior*mask + (1-mask)*(warp*0.8 + x0*0.2) ... PY`
- 关键输出:
  - `mask=1.00 -> fused=10.00`
  - `mask=0.00 -> fused=22.00`
  - `mask=0.25 -> fused=19.00`
  - `mask=0.75 -> fused=13.00`
- 结论:
  - `mask=1` 时完全保留 prior
  - `mask=0` 时完全放开到新结果分支

## 综合发现

### 已验证结论

- `hessian_attr` 不是“保持这些参数不动”的配置。
- 它真正表达的是:
  - “在计算 certainty / guide mask 时, 哪些高斯属性的敏感度要算进去”
- 三个字段的真实含义是:
  - `means`: 高斯中心位置, 也就是空间坐标
  - `quats`: 高斯朝向四元数, 控制椭球旋转
  - `scales`: 高斯尺度参数, 当前存的是 log-scale, 渲染前会 `exp()` 成真实尺寸

### 语义推导

- 如果某个像素对 `means/quats/scales` 很敏感, 那么对应 Hessian 近似更大。
- Hessian 越大, `exp(-exp_index * H)` 越小, 最终 certainty 越低。
- certainty 越低, guide mask 越小, 生成阶段就越不“保原图”, 越允许修改。

### 对“想纠正结构”的配置含义

- 如果你只写 `["means"]`:
  - 只把“位置偏差”当成结构敏感来源
  - 修改会相对保守
- 如果你写 `["means", "quats", "scales"]`:
  - 把位置、朝向、尺寸都当成结构敏感来源
  - 几何相关区域更容易被放开编辑
  - 更适合“我怀疑结构本身就歪了, 想让 refine 更主动纠正”

### 风险提醒

- 这套逻辑放大的不是“稳稳修正”, 而是“更敢动结构相关区域”。
- 如果 prompt 很风格化、`strength` 太高、`warp_ratio` 太低, 也可能把结构一起带跑。

## [2026-03-28 17:18:41] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] 笔记: refined ckpt 与最终 3DGS PLY 导出缺口

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py` 与 `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`

- 要点:
  - 两个 refine 入口在流程结束时都只调用 `refiner.save(name=f"ckpt_{cfg.exp_name}")`
  - 当前没有继续触发 `.ply` 导出
  - 因此 refine 结束后的“最终可交换 3DGS 资产”目前仍停在 checkpoint 形态

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`

- 要点:
  - `Refiner.save()` 的落盘位置是:
    - `f"{self.cfg.result_dir}/ckpts/{name}.pt"`
  - 也就是说 refined 结果的标准路径是:
    - `<result_dir>/ckpts/ckpt_<exp_name>.pt`

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/recon/export_3dgs_ply.py`

- 要点:
  - 已具备完整的 checkpoint -> 3DGS PLY 导出逻辑
  - 当前脚本内部已经分离出:
    - `load_splats_from_checkpoint`
    - `build_ply_matrix`
    - `write_binary_ply`
  - 这意味着最佳改法不是复制导出逻辑, 而是把现有能力封成可复用函数, 再从 refine 流程复用

### 来源4: `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`

- 要点:
  - 当前 wrapper 只顺序执行:
    - `python -m recon.import_fastgs`
    - `python -m ours.refine_by_flux|sdxl`
  - wrapper 本身也没有“最终导出 refined ply”的第三步

## 综合发现

### 现象

- 当前链路已经能桥接 FastGS 输入, 也能完成 refine。
- 真正缺的是最后一跳:
  - refined checkpoint -> `.ply`

### 当前假设

- 只要把导出能力接到 refine 主入口, wrapper 自然就会跟着拿到最终 `.ply`。
- 如果再补一个明确的默认输出路径, 用户就不需要 refine 结束后再手工跑一条导出命令。

### 备选解释

- 如果实现时发现 `cfg.base_dir` 与 `cfg.result_dir` 并不总是同一目录, 就需要把 refined ckpt 路径与 `.ply` 输出路径拆开处理, 不能只靠字符串拼接猜位置。

## [2026-03-28 17:26:01] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] 笔记: wrapper 最终 `.ply` 输出的实现与验证证据

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`

- 要点:
  - 新增 `--final-ply-output`
  - 新增 `build_export_command()`
  - `run_pipeline()` 现在顺序执行:
    - `recon.import_fastgs`
    - `ours.refine_by_flux|sdxl`
    - `recon.export_3dgs_ply`
  - `main()` 结束后会同时打印:
    - `bridge_output`
    - `final_ply_output`

### 来源2: 路径推导策略

- 要点:
  - wrapper 只轻量解析 3 个键:
    - `base_dir`
    - `exp_name`
    - `gs_cfg_file`
  - 再读取 `<base_dir>/<gs_cfg_file>` 的 JSON `result_dir`
  - 最终 refined ckpt 路径:
    - `<result_dir>/ckpts/ckpt_<exp_name>.pt`
  - 最终默认 PLY 路径:
    - `<result_dir>/point_cloud_<exp_name>.ply`

### 来源3: 动态验证命令

- 语法检查:
  - `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py`
- 单测:
  - `timeout 30s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine`
- CLI 帮助页:
  - `timeout 10s python3 ours/run_fastgs_refine.py --help`
- dry run:
  - `python3 ours/run_fastgs_refine.py --ckpt-path /tmp/demo_fastgs.pth --colmap-path data/my4_fullcolmap --exp-cfg exp_cfg/my4/flux_shinkai_museum_v2.yaml --dry-run`

### 来源4: 关键输出

- 单测结果:
  - `Ran 9 tests in 1.812s`
  - `OK`
- dry run 输出了三条命令:
  - `recon.import_fastgs`
  - `ours.refine_by_flux`
  - `recon.export_3dgs_ply`
- dry run 还打印了:
  - `final_ply_output: /root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/point_cloud_flux_shinkai_museum_v2.ply`

## 综合发现

### 已验证结论

- 用户现在可以一条命令走完整链路:
  - FastGS 输入 -> FreeFix bridge ckpt -> refine -> 最终 3DGS `.ply`
- 最终导出路径不再靠硬编码猜 `base_dir`, 而是尊重底层 `cfg.json` 里的 `result_dir`
- `--dry-run` 不再依赖 `OmegaConf`, 因此即使在较轻的 `python3` 环境下也能直接看到完整命令链

### 边界

- 这次补的是 wrapper 的最终导出步骤
- 如果用户绕过 wrapper, 直接单独跑 `refine_by_flux.py / refine_by_sdxl.py`, 仍然不会自动导出 `.ply`

## [2026-03-29 10:52:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 随机相机偏移版 Flux refine 的现有插入点与主要风险

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`

- 要点:
  - 当前 refine 主循环对每个 `i` 先执行 `rgb, masks, alpha, depth, cam_param, _ = refiner.render(i)`。
  - 然后把 `rgb` 作为 `image=rgb_to_refine` 送入 `FluxPipeline`。
  - Flux 输出的 `refined_image` 会和同一轮的 `cam_param["c2w"] / cam_param["K"]` 组成 `refine_cams`。
  - 所以现有系统已经具备“渲染 -> 图生图 -> 回写监督”的闭环, 缺的不是框架能力, 而是新视角相机从哪里来、边界怎么控。

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`

- 要点:
  - `Refiner.render(i)` 当前从 `test_dataset[idx]` 或 `train_dataset[idx]` 取原始 `camtoworld` 与 `K`。
  - 目前只支持一个全局的刚体偏移入口: `test_trans + test_rots`。
  - 这说明“相机偏移”概念并不是全无基础, 但现在是全局常量, 不是逐帧随机采样。
  - 生成后的 synthetic 样本会在 `refiner.refine(...)` 中和原始训练相机一起混合训练。

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py`

- 要点:
  - 数据集返回的是严格绑定的一组 `image + K + camtoworld`。
  - 如果生成端改成随机新相机, 那就不再对应任何真实 `image_path/image_name`, 本质上已经不是“复用现成样本”, 而是在 parser 坐标系里新建 synthetic camera sample。

### 来源4: `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml`

- 要点:
  - 当前 refine 默认就暴露了 `test_split / test_trans / test_rots / strength / warp_ratio / gen_prob / gen_loss_weight`。
  - 这表明最自然的扩展位置仍在 refine config 层, 而不是再单独造一层完全平行的新脚本语义。

## 综合发现

### 现象

- 当前 FreeFix refine 已经不是“纯文本生图后再贴回去”, 而是明确的 img2img 闭环。
- 现有生成图 supervision 和使用它的相机参数是同一帧绑定的。
- 系统已经支持“相机统一偏移”, 但还不支持“每帧随机偏移”。

### 当前主假设

- 这条想法在工程上是可插入的。
- 最自然的做法不是替换掉现有 `refiner.render(i)` 主链, 而是新增一个 `sample_refine_camera(i)` 或 `sample_synthetic_refine_camera(base_cam)` 逻辑:
  - 先选一个 base camera
  - 在小范围位移 / 小角度旋转内采样新 `c2w`
  - 用该 `c2w + K` 渲染当前高斯
  - 再做 Flux img2img
  - 最后把生成图和这个新相机一起作为 synthetic refine cam 回写

### 最强备选解释

- 如果偏移太大, 这个链路就不再是“refine”, 而更像“让 2D 扩散模型替 3D 几何脑补未观测区域”。
- 这时它会把错误内容注入高斯, 尤其在遮挡关系、新暴露区域、薄结构和镜面区域更危险。

### 关键风险

- 风险1: 视角偏移一大, 生成图里的新显露区域没有真实多视图约束, 容易出现 hallucination 监督。
- 风险2: 如果继续沿用 `test_split=test`, 那这批 synthetic views 其实是围绕 benchmark 视角做训练增强, 会影响评测口径的纯净性。
- 风险3: 当前 `K` 默认复用原相机内参。如果平移/旋转扰动和视野变化耦合过强, 只动 `c2w` 不动 `K` 可能不够表达某些想要的相机扰动类型。

### 倾向结论

- 这条路线值得做, 但更适合定义成“受控的新视角 synthetic refine 分支”。
- 第一版应限制在“很小的 pose jitter + 原有可见区域附近”的 regime, 不要一上来做大幅 novel view。
- 如果要保持 benchmark 公平, 最好把它绑定到专门的 refine split 或 train-nearby cameras, 而不是直接围绕评测 test 视角采样。

## [2026-03-29 12:40:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 用可选 offload 模式绕过 `pipe.to(cuda)` 阻塞, 完成 pose jitter 真实 smoke

## 来源

### 来源1: 本地 pipeline 与 diffusers 运行时语义复核

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/sdxl_pipeline.py`
  - 已装包 `diffusers.DiffusionPipeline`
- 要点:
  - `FluxPipeline` 与 `StableDiffusionXLImg2ImgPipeline` 在真正推理时都使用 `self._execution_device`
  - 当前环境里的 `DiffusionPipeline` 也确实提供:
    - `enable_model_cpu_offload(self, gpu_id=None, device=None)`
    - `enable_sequential_cpu_offload(self, gpu_id=None, device=None)`
  - 这说明 offload 模式下不能再把 `pipe.device` 当成“实际执行设备”

### 来源2: 本轮实现

- 新增:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_pipeline_runtime.py`
- 修改:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/tests/test_refine_pipeline_runtime.py`
- 要点:
  - 新增 `refine_pipeline_offload_mode: none | model_cpu | sequential_cpu`
  - 默认 `none`, 保持旧行为
  - `model_cpu / sequential_cpu` 路径不再执行 `pipe.to(cuda)`
  - refine 输入张量改成跟随 `resolve_pipeline_execution_device(pipe)` 走

### 来源3: 轻量验证

- 语法检查:
  - `python3 -m py_compile ours/refine_pipeline_runtime.py ours/refine_by_flux.py ours/refine_by_sdxl.py tests/test_refine_pipeline_runtime.py tests/test_refine_cli_paths.py tests/test_pose_jitter_refine.py`
- 单测:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_refine_pipeline_runtime tests.test_refine_cli_paths tests.test_pose_jitter_refine`
- 关键输出:
  - `Ran 19 tests in 0.030s`
  - `OK`

### 来源4: 真实 smoke

- 临时配置:
  - `/tmp/pose_jitter_smoke_model_cpu.yaml`
- 命令:
  - `timeout 600s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke_model_cpu.yaml`
- 关键阶段输出:
  - `FluxPipeline.from_pretrained 返回`
  - `开始启用 enable_model_cpu_offload(device=cuda)`
  - `enable_model_cpu_offload 返回`
  - `pipeline execution device: cuda:0`
  - `开始创建输出目录: outputs/my5_colmap_fastgs_stable_35k_dense/pose_jitter_smoke_20260329_model_cpu`
  - `Pose jitter log: .../refine/pose_jitter_log.jsonl`
- 退出结果:
  - 进程退出码 `0`
- 落盘产物:
  - `before_refine/000.jpg`
  - `after_refine/000.jpg`
  - `refine/render/000.jpg`
  - `refine/gen/image_000.jpg`
  - `refine/pose_jitter_log.jsonl`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_pose_jitter_smoke_20260329_model_cpu.pt`

### 来源5: pose jitter 日志样本

- `pose_jitter_log.jsonl` 首条记录表明:
  - `attempt_count: 1`
  - `accepted_attempt_index: 1`
  - `used_fallback: false`
  - `alpha_coverage: 1.0`
  - 本轮 sample 围绕 `train` split 的 `source_index: 0`

## 综合发现

### 现象

- 默认整模 `pipe.to(cuda)` 路径在上一轮 `420s` 窗口里始终无法越过
- 改成 `model_cpu` offload 后, 同一条 Flux pose jitter refine 链路成功完成了 1 帧真实 smoke

### 已验证结论

- 当前能被证据支撑的结论是:
  - 本机的真实阻塞边界不在 pose jitter 主链本身
  - 而在默认 pipeline 放置路径
  - `refine_pipeline_offload_mode: model_cpu` 是一条可工作的绕行路径
- 这条路径已经足以支撑 OpenSpec `4.2` 收尾

### 仍然保留的边界

- 本轮 smoke 规模仍然很小, 只覆盖了 1 帧
- 它证明“链路能跑通且没有立刻出现明显遮挡越界”, 但不等于已经完成更大规模的视觉质量评测

## [2026-03-29 14:00:17] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: `my5` 上真实验证 `pose_jitter + train` 模式的数据流

## 来源

### 来源1: 临时 smoke 配置

- 文件:
  - `/tmp/my5_pose_jitter_train_smoke_20260329.yaml`
- 要点:
  - `base_dir: outputs/my5_colmap_fastgs_stable_35k_dense`
  - `refine_camera_mode: pose_jitter`
  - `refine_camera_source_split: train`
  - `refine_pipeline_offload_mode: model_cpu`
  - 小规模范围:
    - `refine_start_idx: 0`
    - `refine_end_idx: 3`

### 来源2: 真实运行命令

- 命令:
  - `timeout 900s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/my5_pose_jitter_train_smoke_20260329.yaml`
- 关键输出:
  - `Pose jitter log: outputs/my5_colmap_fastgs_stable_35k_dense/my5_pose_jitter_train_smoke_20260329/refine/pose_jitter_log.jsonl`
- 退出码:
  - `0`

### 来源3: 输出目录

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/my5_pose_jitter_train_smoke_20260329`
- 已落盘:
  - `before_refine/000.jpg~002.jpg`
  - `refine/render/000.jpg~002.jpg`
  - `refine/gen/image_000.jpg~002.jpg`
  - `after_refine/000.jpg~002.jpg`
  - `refine/pose_jitter_log.jsonl`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_my5_pose_jitter_train_smoke_20260329.pt`

### 来源4: pose jitter 日志内容

- 首 3 条记录都明确写出:
  - `source_split: "train"`
  - `source_index: 0 / 1 / 2`
  - `used_fallback: false`
  - `accepted_attempt_index: 1`
- 对应 `source_image_name`:
  - `001_0_generated_videos_generated_video_0_000002.jpg`
  - `001_0_generated_videos_generated_video_0_000003.jpg`
  - `001_0_generated_videos_generated_video_0_000004.jpg`

## 综合发现

### 现象

- `my5` 上这条链路已经真实跑完
- 中间 `refine/render/*.jpg` 和 `refine/gen/image_*.jpg` 都成功写出
- `pose_jitter_log.jsonl` 清楚记录了它是围绕训练集镜头在做局部抖动

### 已验证结论

- 当前实现的真实语义就是:
  - 先取训练集已有镜头作为 base camera
  - 对这个镜头做小幅 pose jitter
  - 用 jitter 后的相机去 render 当前 GS
  - 再把 render 图送进 Flux 做 img2img
  - 最终生成图和 jitter 后的相机参数一起作为 `Gen` 样本送进 refine

### 口径修正

- 上一轮出现的 `FileNotFoundError` 这次没有复现
- 结合用户说明“刚才误删除了”, 当前更合理的口径是:
  - 上次失败不能再当作稳定代码 bug
  - 本轮无干扰重跑才是有效证据

## [2026-03-29 14:28:56] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: `my5` pose jitter smoke 中大面积黑图的来源定位

## 来源

### 来源1: `my5_pose_jitter_train_smoke_20260329` 输出统计

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/my5_pose_jitter_train_smoke_20260329`
- 亮度统计结果:
  - `before_refine/001.jpg`
    - `mean ≈ 0.5025`
  - `refine/render/001.jpg`
    - `mean ≈ 0.0487`
  - `refine/gen/image_001.jpg`
    - `mean ≈ 0.0505`
  - `after_refine/001.jpg`
    - `mean ≈ 0.0418`
  - `refine/render/002.jpg`
    - `mean ≈ 0.0420`
  - `refine/gen/image_002.jpg`
    - `mean ≈ 0.0441`

### 来源2: 对应训练源图统计

- 源图路径:
  - `/home/rais/FastGS/data/my5_colmap_fastgs/images/001_0_generated_videos_generated_video_0_000002.jpg`
  - `/home/rais/FastGS/data/my5_colmap_fastgs/images/001_0_generated_videos_generated_video_0_000003.jpg`
  - `/home/rais/FastGS/data/my5_colmap_fastgs/images/001_0_generated_videos_generated_video_0_000004.jpg`
- 亮度统计:
  - 三张源图灰度均值都约 `0.50`
  - `<0.10` 像素占比都接近 `0`

### 来源3: pose jitter 日志

- `pose_jitter_log.jsonl`:
  - frame 1:
    - `source_split: train`
    - `source_index: 1`
    - `alpha_coverage: 0.9207`
  - frame 2:
    - `source_split: train`
    - `source_index: 2`
    - `alpha_coverage: 0.8289`
- 这说明:
  - 不是 fallback 到别的相机
  - 也不是“几乎什么都没看到”的空视角

### 来源4: certainty mask 统计

- `refine/masks/{0.001,0.01,0.1}/001.jpg` 与 `002.jpg`
  - 平均亮度约 `0.0079`
  - 接近全黑
- 对比 `000.jpg`:
  - mask 明显更亮

## 综合发现

### 现象

- 发黑不是从原始训练图开始的
- 发黑在 `refine/render` 阶段就已经出现
- `gen` 基本只是延续这个暗输入

### 当前假设

- 当前最强假设是:
  - jitter 后的相机虽然仍然看到了大量几何(`alpha_coverage` 高)
  - 但当前 GS 对这些局部新视角的颜色 / 外观重建非常差
  - 所以 novel-view render 本身已经塌成大面积暗图
- certainty mask 几乎全黑也支持这个方向:
  - 当前系统把这几帧视为低确定性区域

### 备选解释

- 也可能和相机局部旋转方向有关:
  - frame 1 / 2 的抖动把视线带向了室内更暗的表面或边界
  - 但这仍然属于“render 端已经先黑了”, 不是 Flux 单独造成的

### 已验证结论

- 当前能被证据支撑的结论是:
  - 大面积黑色的起点在 `refine/render`
  - 不是训练源图本来就黑
  - 也不是 Flux 把一张正常 render 单独压成黑图

## [2026-03-29 14:47:15] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 黑帧真正由 refine 第一步触发, 直接入口是 `DefaultStrategy` 在 `step=0` 重置 opacity

## 来源

### 来源1: 用日志里的同一组 jitter 参数离线重渲染

- 对 `frame 1 / 2` 使用 `pose_jitter_log.jsonl` 里的真实 `pose_jitter_trans` 和 `pose_jitter_rots`
- 枚举:
  - `base_c2w @ T`
  - `T @ base_c2w`
  - `base_c2w @ inv(T)`
  - `inv(T) @ base_c2w`
- 结果:
  - 所有组合的 render 亮度都在 `0.49 ~ 0.50`
  - 没有任何一种会直接渲染成黑图

### 来源2: 动态复现实验

- 先在初始 checkpoint 上渲染 `frame1` 的同一 jitter 相机:
  - `mean ≈ 0.5034`
- 然后只执行 `frame0` 对应的 4 个 refine step
- 再次渲染同一 `frame1` jitter 相机:
  - `mean ≈ 0.0485`
- 同时固定训练相机 `train[1]` 也一起掉到:
  - `mean ≈ 0.0487`

### 来源3: 剥离实验

- `max_steps=1` 且只跑一个真实 train step, 不进入 Gen 分支:
  - 亮度仍从 `0.5034` 掉到 `0.0393`
- 用自渲染图替代 Flux 图:
  - 仍然掉黑
- 关闭 `use_affine`:
  - 仍然掉黑
- 这说明:
  - 不是 Flux 图内容触发
  - 不是 affine 分支触发
  - 而是 refine 第一步本身就在破坏 GS

### 来源4: `DefaultStrategy` 对照实验

- 保持其它条件不变:
  - `strategy_enabled`
    - 亮度: `0.5034 -> 0.0393`
    - opacity 均值: `0.3388 -> 0.0081`
    - opacity 最大值: `1.0 -> 0.01`
  - `strategy_disabled`
    - 亮度: `0.5034 -> 0.5047`
    - opacity 基本不变
- 直接读取 `gsplat.strategy.DefaultStrategy.step_post_backward`:
  - 当 `step % reset_every == 0` 时会调用 `reset_opa(...)`
- 当前 `Refiner.refine()` 从 `step = 0` 开始计数
  - 因此成熟 checkpoint 在 refine 第一步就命中了 opacity reset

## 综合发现

### 现象

- 黑帧不是 `pose_jitter` 相机采样立刻造成的
- 它发生在第一个 refine step 之后
- 一旦第一步发生 opacity reset, 后续无论 jitter 相机还是固定训练相机都会一起发黑

### 上一主假设的回滚

- 上一条“pose jitter 变换方向可能错了”的主假设, 现在不成立
- 推翻它的证据是:
  - 同一组 jitter 参数离线重渲染并不黑
  - 真正触发发黑的是 refine 更新之后的 GS 状态

### 当前主假设

- 当前最强主假设是:
  - `Refiner` 加载的是成熟 checkpoint
  - 但 `DefaultStrategy` 的步数被从 `0` 重新开始
  - 导致 `step=0` 直接命中 `reset_every`, 把成熟 opacity 错误重置到 `0.01`

### 最强备选解释

- 备选解释是:
  - 除了 `reset_opa` 之外, 还有别的 strategy 状态初始化和成熟 checkpoint 不兼容
- 但当前最小对照里, 只要把 strategy callback 静音, 黑化立即消失
- 因此当前已经足够支撑“先修 strategy 步数语义”这一步

### 已验证结论

- 当前黑图的直接触发点已经能明确写成:
  - `DefaultStrategy.step_post_backward()` 在 `step=0` 执行了 `reset_opa`
  - 这不是 `pose_jitter` 独有问题
  - 而是 refine 从成熟 checkpoint 恢复时没有延续原训练时间轴

## [2026-03-29 14:58:52] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: `my5` 正式 100 镜头 jitter refine 已启动并进入主循环

## 来源

### 来源1: 正式运行配置

- 配置文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_100_20260329.yaml`
- 关键口径:
  - `refine_end_idx: 100`
  - `test_split: train`
  - `refine_camera_mode: pose_jitter`
  - `refine_camera_source_split: train`
  - `refine_pipeline_offload_mode: model_cpu`
  - `load_ckpt_path: outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt`

### 来源2: 首次启动失败后的修正

- 首次后台启动时碰到:
  - `FileNotFoundError: .../ckpts/ckpt_34999.pt`
- 复核工作区后确认:
  - 当前真实存在的是:
    - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.pt`
    - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt`
- 因此正式配置改成显式 `load_ckpt_path`, 不再依赖缺失的默认命名

### 来源3: 当前后台任务状态

- 进程:
  - `PID 326050`
- 日志:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_100_20260329.run.log`
- 已确认日志阶段:
  - `Refiner 初始化完成`
  - `FluxPipeline.from_pretrained 返回`
  - `enable_model_cpu_offload 返回`
  - `开始创建输出目录`
  - `Pose jitter log: .../refine/pose_jitter_log.jsonl`
  - 进度条已进入:
    - `0/32`

## 综合发现

### 现象

- 当前正式任务已经不是“只完成配置”
- 它已经真实进入 Flux 主循环
- 输出目录和 refine 子目录都已创建完成

### 当前结论

- 截至 `2026-03-29 14:58:52 UTC`
  - 正式 `my5` 100 镜头 jitter refine 正在后台运行
  - 当前没有新的启动期错误
  - 后续只需要继续观察运行进度和最终产物

## [2026-03-29 15:07:04] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 当前正式 jitter 太保守, 已切到更强 3x 配置重启

## 来源

### 来源1: 用户反馈与当前运行日志

- 用户明确反馈:
  - “抖动太小了, 我看图质量都很高”
- 对应运行目录:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_100_20260329`
- 对应 `pose_jitter_log.jsonl` 前几条:
  - 平移大多在 `0.003 ~ 0.019m`
  - 旋转基本在 `2 度` 内

### 来源2: 更强版本正式配置

- 新配置:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_100_stronger_20260329.yaml`
- 关键变化:
  - `pose_jitter_trans_sigma: [0.03, 0.03, 0.03]`
  - `pose_jitter_trans_max: [0.06, 0.06, 0.06]`
  - `pose_jitter_rot_sigma_deg: [3.0, 3.0, 3.0]`
  - `pose_jitter_rot_max_deg: [6.0, 6.0, 6.0]`

### 来源3: 重启后的后台任务状态

- 旧任务:
  - 已发送 `SIGTERM` 停止
- 新任务:
  - `PID 331670`
- 日志:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_100_stronger_20260329.run.log`
- 新 `pose_jitter_log.jsonl` 第 1 条:
  - `pose_jitter_trans = [-0.0434, -0.0336, 0.0120]`
  - `pose_jitter_rots = [1.026, 2.578, -0.513]`

## 综合发现

### 现象

- 更强版本的第一条采样已经明显大于上一轮
- 当前不是“看起来配大了”
- 而是动态日志里已经真实采到了 `4cm` 量级平移

### 当前结论

- 截至 `2026-03-29 15:07:04 UTC`
  - 更强 3x jitter 正式任务已经启动并在后台运行
  - 第一条实际采样已明显变大
  - 这轮更符合“不要太贴近原镜头”的目标

## [2026-03-29 15:16:55] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: stronger jitter 的首批实际采样已进入 4cm~6cm / 4~6 度量级

## 来源

### 来源1: 当前运行状态

- 进程:
  - `PID 331670`
- 日志:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_100_stronger_20260329.run.log`
- 当前已落盘:
  - `refine/render`: 16 张
  - `refine/gen`: 15 张

### 来源2: 首批 stronger `pose_jitter_log.jsonl`

- frame 0:
  - `trans = [-0.0434, -0.0336, 0.0120]`
  - `rots = [1.026, 2.578, -0.513]`
- frame 2:
  - `trans = [0.0301, 0.0600, 0.0460]`
  - `rots = [4.197, -4.093, 2.500]`
- frame 4:
  - `trans = [-0.0031, 0.0107, -0.0600]`
  - `rots = [-2.509, -3.789, 0.582]`
- frame 8:
  - `trans = [0.0231, 0.0499, -0.0051]`
  - `rots = [-2.781, -6.000, 0.034]`

### 来源3: 前几张输出亮度

- `refine/render/000~005.jpg`
  - 均值约 `0.500 ~ 0.513`
- `refine/gen/image_000~005.jpg`
  - 均值约 `0.501 ~ 0.512`
- 当前没有重新出现黑帧

## 综合发现

### 现象

- stronger 这轮的采样幅度已经明显进入:
  - `4cm ~ 6cm` 量级平移
  - `4 ~ 6` 度量级旋转
- 这比上一轮常见的:
  - `0.003 ~ 0.019m`
  - `<= 2` 度
- 明显更强

### 当前结论

- 当前 stronger 配置已经真正达到了“明显离开原镜头”的目标
- 同时首批 `render / gen` 仍保持正常亮度
- 所以这轮参数目前看是更合适的中强档位

## [2026-03-29 23:20:17] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: stronger 长跑当前不是卡死, 而是中段落盘节奏偏慢

## 来源

### 来源1: 两次间隔 35 秒的动态复查

- 第一次观察:
  - `refine/render`: `19` 张
  - `refine/gen`: `18` 张
  - 最新文件时间:
    - `render/018.jpg @ 2026-03-29 15:18:46 UTC`
    - `gen/image_017.jpg @ 2026-03-29 15:18:42 UTC`
- 35 秒后再次观察:
  - `refine/render`: `21` 张
  - `refine/gen`: `20` 张
  - 最新文件时间:
    - `render/020.jpg @ 2026-03-29 15:19:57 UTC`
    - `gen/image_019.jpg @ 2026-03-29 15:19:53 UTC`

### 来源2: 进程状态

- `ps -p 331670 -o pid,etime,pcpu,pmem,stat,cmd`
- 结果:
  - 进程仍在
  - `STAT=Rsl`
  - `%CPU` 约 `110`

### 来源3: 最新落盘图像亮度抽查

- `refine/render/014~018.jpg`
  - 均值约 `0.502 ~ 0.515`
- `refine/gen/image_013~017.jpg`
  - 均值约 `0.502 ~ 0.514`
- 当前未见黑帧回潮

## 综合发现

### 现象

- 从单次快照看, 输出目录一度像是停在 `19/18` 帧附近
- 这会让人怀疑它是不是“进程活着, 但实际卡住了”

### 当前假设

- 候选假设A:
  - 任务只是中段落盘节奏偏慢, 但仍在推进
- 候选假设B:
  - 任务卡在某个固定帧位, 只是 CPU 仍然忙

### 验证计划

- 不靠单次快照下结论
- 间隔 35 秒重复统计:
  - 文件数量
  - 最新文件时间
  - 进程状态

### 当前结论

- 候选假设B 当前被动态证据推翻
- stronger 这轮现在不是“静默卡死”
- 更准确的描述是:
  - 中间 `refine/render + gen` 阶段仍在持续推进
  - 只是节奏明显比最开始感知到的要慢

## [2026-03-30 00:44:35] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: stronger 正式 run 已完成, jitter 足够强, 但 fixed-view 最终变化偏温和

## 来源

### 来源1: 运行完成状态

- `pgrep -af 'flux_shinkai_museum_v2_35k_pose_jitter_train_100_stronger_20260329.yaml'`
  - 无结果
- 输出目录完整性:
  - `before_refine`: `100` 张
  - `refine/render`: `100` 张
  - `refine/gen`: `100` 张
  - `after_refine`: `100` 张
- 时间戳:
  - run log: `2026-03-29 16:08:29 UTC`
  - `pose_jitter_log.jsonl`: `2026-03-29 16:07:53 UTC`

### 来源2: `pose_jitter_log.jsonl` 汇总

- 样本数:
  - `100`
- fallback:
  - `0`
- 平移范数:
  - 均值 `0.0476`
  - 中位数 `0.0481`
  - 最大值 `0.0850`
- 旋转范数:
  - 均值 `4.7157`
  - 中位数 `4.6859`
  - 最大值 `9.4660`
- 单轴绝对值:
  - `|trans|` 平均 `0.0235`, `p95=0.0600`, `max=0.0600`
  - `|rot|` 平均 `2.3980`, `p95=5.8214`, `max=6.0000`
- 平移最大的几帧:
  - `099`: `trans_norm=0.0850`
  - `069`: `trans_norm=0.0849`
  - `002`: `trans_norm=0.0814`

### 来源3: 中间 `render -> gen` 变化幅度

- `gen-vs-render mae`
  - 均值 `0.0157`
  - 中位数 `0.0155`
  - 最大值 `0.0246`
- 亮度均值:
  - `render`: `0.5016`
  - `gen`: `0.5020`
- 说明:
  - Flux 图生图不是“几乎没改”
  - 中间 synthetic supervise 确实对 jitter 渲染做了可见改写

### 来源4: fixed-view `before -> after` 变化幅度

- `before-vs-after mae`
  - 均值 `0.0116`
  - 中位数 `0.0106`
  - 最大值 `0.0199`
- 亮度均值:
  - `before`: `0.5017`
  - `after`: `0.5038`
- 阈值统计:
  - `mae >= 0.010`: `59/100`
  - `mae >= 0.012`: `39/100`
  - `mae >= 0.015`: `17/100`
  - `mae >= 0.018`: `3/100`
- 变化最大的帧集中在:
  - `042 ~ 046`

### 来源5: 肉眼抽样拼图

- 抽样拼图:
  - `eval_montage_20260330.jpg`
  - `eval_before_after_topdiff_20260330.jpg`
- 观察:
  - 中间 `render / gen` 明显已经不是原固定镜头
  - `after` 相比 `before` 主要表现为:
    - 略提亮
    - 反射和边缘有轻微整理
    - 没有重新出现黑帧
  - 但 fixed-view 最终变化并不激进, 更像温和修整

## 综合发现

### 现象

- stronger 这轮已经完整跑完
- 中间 pose jitter 和 Flux 生成都产生了可见改动
- 但最终固定视角 `after_refine` 相比 `before_refine` 的变化幅度明显更克制

### 当前假设

- 候选假设A:
  - 当前参数已经足够把 synthetic supervise 拉离原镜头
  - 但 3D 优化写回固定视角后的投影改动仍偏保守
- 候选假设B:
  - 当前 fixed-view 变化小, 可能是因为真正有效的监督增量有限
  - 也可能是这组场景本身已经接近收敛上限

### 当前结论

- 可以确认的部分:
  - stronger jitter 已达到“明显离开原镜头”的目标
  - 中间 `render -> gen` 有实质改动
  - 最终 fixed-view 没黑、没崩、没出现明显灾难性退化
- 当前更准确的评价口径:
  - 这轮更像“安全的中强档 refine”
  - 不是“final fixed-view 出现大幅重塑”的那种强刺激结果

### 未决观察

- 现象:
  - 可视化产物和 `tb_refine` 事件文件都落盘了
  - 但按代码应保存到 `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_100_stronger_20260329.pt` 的最终 checkpoint 当前不存在
- 当前还缺的证据:
  - 无 traceback
  - 无显式 save 日志
- 因此现在只能说:
  - 图像评估已完成
  - 但模型持久化是否完整成功, 目前仍是未决项

## [2026-03-31 00:00:00] [Session ID: 019d436e-9bf6-7313-ab99-623578ee4ecf] 笔记: `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 缺少 `after_refine.mp4`

## 来源

### 来源1: 静态代码路径

- 文件: [ours/refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)
- 要点:
  - 代码会初始化 `after_refine_writer = imageio.get_writer(...)`
  - 只有在 refine 主循环全部完成后, 才会进入:
    - fixed-view `after_refine/*.jpg` 渲染
    - `after_refine_writer.close()`
    - `refiner.save(name=f"ckpt_{cfg.exp_name}")`
  - 所以 `after_refine.mp4` 不是额外工具才会生成的, 它本来就是主流程的一部分

### 来源2: 正式 run 日志

- 文件: [run.log](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/run.log)
- 要点:
  - 规范化回车后的日志里能看到:
    - `输出目录与 writer 初始化完成`
    - `真实训练池 ... count=324`
    - `synthetic plan ... count=972`
  - 但没有看到:
    - `开始保存 refine checkpoint`
    - `refine checkpoint 已保存`
  - 也没有 `Traceback` / `Exception` / `Killed`

### 来源3: 实际落盘产物

- 目录: [outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330)
- 要点:
  - `before_refine/` 有 `100` 张, `before_refine.mp4` 已存在
  - `refine/render/` 有 `327` 张
  - `refine/gen/` 有 `327` 张
  - `refine/depth/` 有 `327` 张
  - `pose_jitter_log.jsonl` 有 `327` 行, 最后一条是 `plan_index=326`
  - `after_refine/` 为空
  - 没有 `after_refine.mp4`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/` 下也没有 `ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`

### 来源4: watcher 日志

- 文件: [eval_after_refine.log](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/eval_after_refine.log)
- 要点:
  - 当前只看到了 watcher 反复打印 `refine pid=373665 still running`
  - 没有真正进入 `ours.evaluation` 后的评估输出
  - 这说明它不能被当成“refined 结果已经评估完成”的证据

## 综合发现

### 现象

- 这次 run 不是“只少导出了一个 mp4”
- 它实际上没有走到完整收尾阶段

### 当前结论

- 已验证结论:
  - `after_refine.mp4` 本来就该由主流程自动生成
  - 这次之所以没有, 是因为 run 只完成了 `972` 个 synthetic plan 中的前 `327` 个
  - 它没有进入 `after_refine` fixed-view 渲染阶段
  - 也没有走到 refined checkpoint 保存阶段

### 仍未确认的部分

- 进程为什么停在 `plan_index=326` 附近, 当前还不能下最终根因结论
- 目前只能保守表述为:
  - 这不是“代码里没有 after 输出”
  - 而是“本次正式 run 中途终止或未完整收尾”

## [2026-03-31 00:40:00] [Session ID: 019d436e-9bf6-7313-ab99-623578ee4ecf] 笔记: 当前代码不支持从中间 synthetic plan 断点继续

## 来源

### 来源1: 进程状态

- `ps -ef` 已确认当前没有活着的:
  - `ours.refine_by_flux`
  - `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`

### 来源2: `Refiner` 的恢复语义

- 文件: [recon/refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
- 文件: [recon/refine_runtime.py](/root/autodl-tmp/home/rais/FreeFix/recon/refine_runtime.py)
- 要点:
  - `load_ckpt_path` 只负责加载一个已有高斯 checkpoint
  - `resume_load_step` / `strategy_resume_step` 只是在 densification strategy 里恢复“原训练时间轴步数”
  - 它不是 synthetic plan 的进度恢复
  - 也不会恢复:
    - 已经跑到哪个 `plan_index`
    - 已生成的 `refine/gen/*.jpg`
    - 已经写回多少轮 `refiner.refine(...)`

### 来源3: 当前输出目录状态

- 当前只有:
  - `before_refine/*.jpg`
  - `refine/render/*.jpg`
  - `refine/gen/*.jpg`
  - `pose_jitter_log.jsonl`
- 但没有:
  - 当前 run 的 refined checkpoint
  - 中途 checkpoint
  - “从第几个 plan 继续”的状态文件

## 综合发现

### 已验证结论

- 当前这版代码不能从 `plan_index=326` 原地继续
- 原因不是一句“没开 resume 参数”那么简单
- 而是恢复所需的三个条件都缺:
  - 没有活着的进程
  - 没有中途 checkpoint
  - 没有 synthetic progress 恢复机制

## [2026-04-01 01:37:46] [Session ID: 019d436e-9bf6-7313-ab99-623578ee4ecf] 笔记: `offload_mode=none` 的 resume 重跑已验证生效

## 来源

### 来源1: 旧实例停机前的动态现场

- 命令:
  - `pgrep -af 'ours\\.refine_by_flux|flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330|tee .../run.log'`
  - `rg -n '已保存恢复 checkpoint' run.log`
  - `tail -n 3 refine/pose_jitter_log.jsonl`
- 要点:
  - 旧实例仍活着:
    - `89870` bash pipeline
    - `89872` python
    - `89873` tee
  - 停机前实时推进已经到:
    - `plan_index=92`
    - `render/depth=092`
    - `gen=091`
  - 但最近一次可恢复 checkpoint 仍是:
    - `plan=75/972`
    - `refine_resume_state.json` 仍显示 `next_plan_index=75`

### 来源2: 新实例启动日志

- 文件: [run.log](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/run.log)
- 要点:
  - 新日志出现:
    - `开始执行 pipe.to(cuda)`
    - `pipe.to(cuda) 返回`
    - `恢复 synthetic train pool: restored=75 next_plan_index=75/972`
  - 没有出现:
    - `enable_model_cpu_offload`
    - `model_cpu`

### 来源3: 重启后的产物目录

- 目录: [outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330)
- 要点:
  - 新实例启动后, 目录先回退到:
    - `render_max=075`
    - `depth_max=075`
    - `gen_max=074`
  - 这说明 `75` 之后的旧半截产物没有被沿用
  - 再次采样时已经继续推进到:
    - `render_max=077`
    - `depth_max=077`
    - `gen_max=076`
    - `pose_jitter_log.jsonl` 最后 `plan_index=77`
    - `generated_cams.jsonl` 最后 `plan_index=76`

### 来源4: 新实例进程状态

- 命令:
  - `ps -o pid,pgid,ppid,stat,etime,%cpu,%mem,cmd -p 117765,117767,117768`
- 要点:
  - 新实例当前 PID:
    - `117765` bash pipeline
    - `117767` python
    - `117768` tee
  - 当前 python 进程仍在高占用运行

## 综合发现

### 现象

- 用户要求把 `refine_pipeline_offload_mode` 改成 `none` 后 resume 重跑
- 现场实际需要先停掉旧实例, 否则会污染同一输出目录

### 已验证结论

- 这轮 resume 重跑已经成功切到 `none` 路径
- 证据不是“配置文件改了”, 而是:
  - 新日志出现 `pipe.to(cuda)` 正常返回
  - 新日志里没有 `model_cpu` / `enable_model_cpu_offload`
  - 新实例严格从 `next_plan_index=75` 一档恢复
  - `75` 之后的旧半截产物被清掉, 然后重新向前推进

### 当前仍需注意

- `refine_resume_state.json` 暂时还停在上一次 checkpoint 保存时刻
- 这不是恢复失败
- 只是说明 rolling checkpoint 仍按周期落盘, 所以如果再次中断, 两次 checkpoint 之间那一小段仍可能重做

### 当前最准确的口径

- 对当前这次 run 来说:
  - 不能“继续跑”
  - 只能:
    - 从初始 checkpoint 重新跑
    - 或者先改代码, 做出真正的断点恢复能力后, 再用于后续运行

## [2026-04-01 16:38:13] [Session ID: 37900] 笔记: 重新 bridge 后的新一轮 refine 当前吞吐正常

## 来源

### 来源1: 产物目录二次采样

- 目录: [outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330)
- 要点:
  - 第一次采样:
    - `refine/render=95`
    - `refine/gen=94`
    - `refine/depth=95`
  - 约 75 秒后二次采样:
    - `refine/render=105`
    - `refine/gen=104`
    - `refine/depth=105`
  - `after_refine` 仍为 `0`, 说明当前还在 synthetic plan 主循环里

### 来源2: `refine_resume_state.json`

- 文件: [refine_resume_state.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/refine_resume_state.json)
- 要点:
  - 第一次读到:
    - `next_plan_index=75`
    - `latest_completed_plan_index=74`
  - 第二次读到:
    - `next_plan_index=100`
    - `latest_completed_plan_index=99`
    - `updated_at_utc=2026-04-01T08:37:01.665523+00:00`
  - `plan_total=566`

### 来源3: 后台 PTY 运行输出

- 会话: `79572`
- 要点:
  - 输出持续出现单条 plan 内部的进度条
  - 已看到 `32/32` 阶段结束后立刻进入新的 `400` 步优化阶段
  - 说明主进程没有卡死, 而是在稳定执行每条 synthetic plan

## 综合发现

### 现象

- 重跑后的 `refine` 仍在进行中
- watcher 还未进入 `evaluation`, 因为主 `refine` 进程尚未退出

### 已验证结论

- 这轮 run 是健康推进的, 不是假跑也不是卡在旧保存点
- 当前 `resume_state.json` 只能代表最近一次 rolling save 点, 不能当作毫秒级实时进度
- 以最近一次 75 秒窗口估算, 吞吐大约是 `10 plans / 75s`
- 按这个区间粗估, 从 `plan 105/566` 到收尾大约还需 `55-65` 分钟, 但实际还会受周期性保存与导出阶段影响

### 当前口径

- 可以确认:
  - raw FastGS checkpoint 已重新 bridge
  - 新配置口径下的 refine 已按 `train-only synthetic + test fixed window(0..40)` 正式重跑
- 还不能提前宣称:
  - refined ckpt 已经产出
  - evaluation 已完成

## [2026-04-01 18:17:27] [Session ID: 37900] 笔记: 本轮 `ckpt_35000_freefix.pt` 重跑与评估结果

## 来源

### 来源1: `refine_resume_state.json`

- 文件: [refine_resume_state.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/refine_resume_state.json)
- 要点:
  - `status=complete`
  - `synthetic_complete=true`
  - `after_refine_complete=true`
  - `next_plan_index=566`
  - `latest_completed_plan_index=565`
  - `final_ckpt_path=outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`

### 来源2: refine 与导出产物

- 文件:
  - [ckpt_35000_freefix.pt](/root/autodl-tmp/home/rais/FreeFix/data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt)
  - [ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt)
  - [after_refine.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/after_refine.mp4)
  - [point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply)
- 要点:
  - bridge ckpt 已重新由 `/home/rais/FastGS/output/my5_nomask_v1/checkpoints/ckpt_35000.pth` 转成 FreeFix 入口 ckpt
  - 本轮最终 refined ckpt 已保存
  - `before_refine=41`
  - `after_refine=41`
  - `refine/render=566`
  - `refine/gen=566`
  - `refine/depth=566`
  - refined `point_cloud` 不是自动产物, 本轮已用现有导出脚本补齐

### 来源3: evaluation json

- 文件:
  - [35000_test.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/eval/35000_test.json)
  - [35000_train.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/eval/35000_train.json)
  - [flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330_test.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/eval/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330_test.json)
  - [flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330_train.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/eval/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330_train.json)
- 要点:
  - base bridge ckpt test:
    - `PSNR=27.188240097790228`
    - `SSIM=0.8906744631325326`
    - `LPIPS=0.2037334242245046`
  - refined ckpt test:
    - `PSNR=27.559024531666825`
    - `SSIM=0.8938605901671619`
    - `LPIPS=0.19603789743126893`
  - test 差值(refined - base):
    - `PSNR=+0.3707844338765973`
    - `SSIM=+0.0031861270346292825`
    - `LPIPS=-0.00769552679323568`
  - base bridge ckpt train:
    - `PSNR=27.30250376104887`
    - `SSIM=0.892769445168256`
    - `LPIPS=0.20248514247972638`
  - refined ckpt train:
    - `PSNR=27.745485770828733`
    - `SSIM=0.8964001765941984`
    - `LPIPS=0.19431411403859883`
  - train 差值(refined - base):
    - `PSNR=+0.44298200977986113`
    - `SSIM=+0.0036307314259423906`
    - `LPIPS=-0.008171028441127548`

## 综合发现

### 现象

- 用户要求基于修改后的 `test_split=test` / `refine_end_idx=41` / `train-only synthetic` 口径, 对 `ckpt_35000.pth` 重新 bridge 后再跑一整套 refine 和评估

### 已验证结论

- 这轮已经完整达成该目标
- 当前这套结果的 fixed-view 窗口确实是 `test` split 的 `0..40`
- synthetic 训练池与 camera source 都只来自 `train`
- 自动评估结果显示 refined ckpt 相比 base bridge ckpt 在 `test` 与 `train` 两个 split 上都一致提升:
  - `PSNR` 更高
  - `SSIM` 更高
  - `LPIPS` 更低

### 当前口径

- 可以把这轮结果视为:
  - 重新 bridge `output/my5_nomask_v1/checkpoints/ckpt_35000.pth`
  - 按修改后的 `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml` 完整重跑
  - 再对 base / refined 两个 checkpoint 做同口径 evaluation

## [2026-04-01 18:28:08] [Session ID: 37900] 笔记: 重影候选原因排查 - 位姿错配假设不成立, 更像 synthetic 外观与结构约束冲突

## 来源

### 来源1: `recon/refiner.py` 的相机采样与返回值

- 文件: [refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
- 要点:
  - `render(camera_mode='pose_jitter')` 先读取 `base_c2w`
  - 然后用 `sample_bounded_pose_jitter(...)` 采样扰动
  - 再构造 `jittered_c2w = base_c2w @ build_local_camera_transform(...)`
  - 最终写进 `cam_param['c2w']` 的就是这个 `jittered_c2w`, 不是原始 `base_c2w`

### 来源2: `ours/refine_backend_runner.py` 的 synthetic supervise 调用链

- 文件: [refine_backend_runner.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_backend_runner.py)
- 要点:
  - `refiner.render(...)` 返回的 `cam_param['c2w']` 会直接写进:
    - `refine_cams[0]['camtoworld'] = c2w`
  - 同时 `append_generated_camera_record(...)` 会把同一份 `cam_param['c2w']` 记录进 `generated_cams.jsonl`
  - 恢复时 `restore_completed_generated_cams(...)` 也是直接从日志里把这份 `c2w` 读回来, 没有改回原相机

### 来源3: 本轮产物日志的动态证据

- 文件:
  - [generated_cams.jsonl](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/refine/generated_cams.jsonl)
  - [pose_jitter_log.jsonl](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/refine/pose_jitter_log.jsonl)
- 要点:
  - `generated_cams.jsonl` 首条记录明确是:
    - `camera_mode=pose_jitter`
    - `source_split=train`
    - `source_index=0`
    - 带一份显式保存的 `c2w`
  - `pose_jitter_log.jsonl` 同一条记录明确保存了本次采样的:
    - `pose_jitter_trans`
    - `pose_jitter_rots`
  - 进一步对比 `train[0]` 的原始 `c2w` 与首条 `generated_cams.jsonl['c2w']`, 平移项差值为:
    - `delta_t=[0.00857, -0.02374, 0.00463]`
  - 说明这份训练相机确实已经偏离原相机, 不是“原位姿监督”

### 来源4: `mask / warp` 的实际生效方式

- 文件:
  - [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)
  - [flow_match_euler_discrete_scheduler.py](/root/autodl-tmp/home/rais/FreeFix/ours/schedulers/flow_match_euler_discrete_scheduler.py)
  - [flux_pipeline.py](/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py)
- 要点:
  - `mask` 来自 `multi_certainties`, 本质是基于 Hessian 不确定性算出的多级 certainty mask
  - `warp_mask` 用的是当前渲染视角的 `alpha`
  - 在 scheduler 里:
    - `warp_latent = warp_latent * warp_mask + x0 * (1 - warp_mask)`
    - 若 `guided and warp`, 则 `x0 = prior_latents*mask + (1-mask)*(warp_latent * 0.8 + x0 * 0.2)`
  - 这说明已有结构会被明显保留, 尤其在 `alpha` 覆盖区域和 certainty mask 覆盖区域

## 综合发现

### 现象

- 用户主观感觉这轮 refined 结果更重影

### 已验证结论

- “jitter render 的图被拿去训练非 jitter 原相机位姿” 这条假设, 当前证据不支持
- 更像的解释是:
  - synthetic 图是在 jitter 后新视角上生成的
  - 但 Flux 生成结果未必与这个新视角的真实几何完全一致
  - 后续 `mask + warp(alpha)` 又会把已有结构强力混回去
  - 于是容易把“轻微错位的旧结构”和“新生成纹理”一起写进高斯, 视觉上就会像重影

### 当前仍需注意

- 我顺手发现一个配置一致性信号:
  - 当前磁盘上的 yaml 里 `pose_jitter_views_per_source` 显示为 `1`
  - 但本轮产物 `generated_cams.jsonl` 实际有 `566` 条, 并且 `source_repeat_index` 出现了 `0/1`
  - 这说明“当前文件内容”和“本轮实际运行时配置”之间至少有一处时间差
- 所以下面的判断, 我是以代码调用链和本轮产物日志为准, 不是只以当前 yaml 的静态文本为准

## [2026-04-01 21:12:00] [Session ID: 2a213fb2-1d29-4f62-9c76-68a7700db14c] 笔记: 邻近镜头平均半径模式已完成接线, 当前语义是“高斯方向 + 邻居半径 cap”

## 来源

### 来源1: `ours/refine_backend_runner.py`

- 文件: [refine_backend_runner.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_backend_runner.py)
- 要点:
  - 新增了 `build_refiner_runtime_kwargs(...)`
  - 这一层统一把 wrapper 配置整理成 `Refiner(...)` 参数
  - 新增字段全部用 `getattr(..., default)` 兜底:
    - `pose_jitter_trans_radius_mode`
    - `pose_jitter_neighbor_window`
    - `pose_jitter_neighbor_radius_scale`
  - 这样旧 yaml 就算还没声明这些字段, 也不会在初始化阶段直接报属性不存在

### 来源2: `recon/refiner.py`

- 文件: [refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
- 要点:
  - `render(camera_mode='pose_jitter')` 现在会先算:
    - `trans_radius_limit = _resolve_pose_jitter_trans_radius_limit(...)`
  - 再把这个值传给:
    - `sample_bounded_pose_jitter(..., trans_radius_max=trans_radius_limit)`
  - 半径来源是:
    - 当前 split 序列里
    - 当前镜头到相邻镜头的中心距离
    - 再取平均
    - 最后乘 `pose_jitter_neighbor_radius_scale`
  - 我额外补了 `pose_jitter_pose_sequence_cache`
    - 避免每个 synthetic plan 都把整条相机序列重新读一遍
    - 当前 cache key 是 `(split_kind, trans)`

### 来源3: `recon/pose_jitter.py`

- 文件: [pose_jitter.py](/root/autodl-tmp/home/rais/FreeFix/recon/pose_jitter.py)
- 要点:
  - 当前实现不是“按邻居半径重新定义采样分布”
  - 而是:
    - 先按原来的逐轴高斯 + 逐轴 `trans_max` 采样
    - 如果总平移向量范数超过 `trans_radius_max`
    - 再把整个向量按比例缩回半径球内
  - 这意味着:
    - 方向仍然来自旧高斯
    - 但总位移不会超过邻近镜头平均距离给出的上限

### 来源4: 当前实验配置与验证命令

- 文件:
  - [base.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml)
  - [flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml)
- 命令:
  - `OMP_NUM_THREADS=1 direnv exec . .pixi/envs/default/bin/python -m pytest tests/test_pose_jitter_refine.py`
  - `OMP_NUM_THREADS=1 direnv exec . .pixi/envs/default/bin/python -m unittest tests.test_pose_jitter_refine`
  - `OMP_NUM_THREADS=1 direnv exec . .pixi/envs/default/bin/python -m unittest tests.test_refine_view_plan tests.test_refine_cli_paths tests.test_run_fastgs_refine`
- 要点:
  - `pytest` 在当前 pixi 环境里不存在, 报:
    - `No module named pytest`
  - 随后改用 `unittest` 跑同一组与相关回归测试, 全部通过:
    - `tests.test_pose_jitter_refine`: `13 tests`
    - 相关回归合计: `22 tests`

## 综合发现

### 已验证结论

- “前后两个镜头平均半径作为 jitter 半径范围” 这条链路已经完整打通:
  - 配置层
  - backend wrapper
  - `Refiner`
  - pose jitter helper
  - 实验 yaml
  - 单测
- 当前默认语义明确是:
  - `pose_jitter_neighbor_window: 1`
  - 也就是“前一个 + 后一个”
- 当前实现更保守:
  - 它只把邻居平均半径当作总位移 cap
  - 不会彻底抛弃原本的 `sigma/max` 方向分布

### 当前仍需注意

- 如果后面用户想要的不是“半径上限”, 而是“半径本身也按邻居距离分布去采样”
  - 那还需要再做第二轮语义细化
  - 当前这轮还没有走到那一步

## [2026-04-01 21:28:00] [Session ID: 6f225887-9be2-454c-a76d-72780a9280bd] 笔记: 已把 `my5` 当前实验调成“邻居半径主导型”

## 来源

### 来源1: 当前 `my5 train` 相邻镜头距离统计

- 数据来源:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/cfg.json`
  - `/home/rais/FastGS/data/my5_colmap_fastgs`
  - `recon.datasets.colmap.Parser / Dataset(split='train')`
- 命令:
  - `OMP_NUM_THREADS=1 direnv exec . .pixi/envs/default/bin/python - <<'PY' ...`
- 要点:
  - `train_count = 283`
  - `avg_neighbor` 分布:
    - `p25 = 0.100512`
    - `p50 = 0.133148`
    - `p75 = 0.202616`
    - `p90 = 0.473087`
    - `mean = 0.235181`
  - 这说明:
    - 旧的 `trans_sigma = 0.03`
    - 对大多数镜头来说都偏小
    - 采样范数通常还没碰到邻居半径 cap, 就已经结束了

### 来源2: 当前参数如何才能让“邻居半径”真正主导

- 要点:
  - 如果想让 `neighbor_average_radius` 真正主导
  - 核心不是继续把 `trans_max` 压小
  - 而是:
    - 把 `trans_sigma` 提到和邻居距离同量级
    - 同时让 `trans_max` 保持比大多数邻居 cap 更宽
  - 这样采样更常碰到“总半径 cap”
  - 而不是先被固定 `sigma/max` 自己卡住

## 综合发现

### 已落地调整

- 已修改 [flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_test_x3_20260330.yaml):
  - `pose_jitter_trans_sigma: [0.10, 0.10, 0.10]`
  - `pose_jitter_trans_max: [0.50, 0.50, 0.50]`
  - `pose_jitter_neighbor_radius_scale: 0.85`

### 当前口径

- 这组值的目标不是“更猛”
- 而是“让邻居半径更常成为真正限制项”
- 同时把 `scale` 从 `1.0` 稍微降到 `0.85`
  - 避免一上来就总是顶满相邻镜头平均距离
  - 给重影风险留一点缓冲
