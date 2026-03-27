## [2026-03-27 22:14:26] [Session ID: 20260327T221426Z-main] 笔记: my5 训练与 Flux refine 配置对齐依据

## 来源

### 来源1: `my4` 参考配置

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_stable_12k_dense.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum_v2.yaml`
- 要点:
  - `my4` 当前作为参考的训练线是 `stable_12k_dense`
  - 训练关键窗口:
    - `max_steps: 12000`
    - `refine_stop_iter: 9000`
    - `pose_opt: true`
    - `app_opt: false`
    - `depth_loss: true`
  - Flux 关键参数:
    - `strength: 0.65`
    - `refine_steps: 400`
    - `warp_ratio: 0.3`
    - `load_step: 11999`

### 来源2: 索引语义代码

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`
  - `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`
  - `/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py`
- 要点:
  - `train_start_idx/train_end_idx` 实际取的是 `refiner.train_dataset`
  - `refine_start_idx/refine_end_idx` 实际取的是 `refiner.test_dataset`
  - 无 `partition.json` 时:
    - `train = indices[indices % test_every != 0]`
    - `test = indices[indices % test_every == 0]`
  - `refiner.render(i)` 默认 `split="test"`

### 来源3: my5 数据目录与动态验证

- 路径:
  - `/home/rais/FastGS/data/my5_colmap_fastgs`
- 动态证据:
  - 目录存在:
    - `images/`
    - `input/`
    - `sparse/0`
    - `distorted/database.db`
  - 直接用项目里的 `Parser` 与 `Dataset` 计算得到:
    - `total = 324`
    - `train = 283`
    - `test = 41`
    - `first_test_indices = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72]`
    - `last_test_index = 320`
    - `last_train_index = 323`

### 来源4: checkpoint 命名规则

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/trainer.py`
- 要点:
  - `torch.save(..., f"{self.ckpt_dir}/ckpt_{step}.pt")`
  - 最后一轮满足:
    - `step == max_steps - 1`
  - 因此 `max_steps: 12000` 的最终 checkpoint 名是:
    - `ckpt_11999.pt`

## 综合发现

### 现象

- 用户希望按 `my4` 的稳态训练线训练一套 `my5`。
- 但 `my4` 的 Flux 配置里 `0..100` 只是旧场景下的人工范围, 不能直接平移到 `my5`。

### 当前结论

- `my5` 训练配置可以直接复用 `my4 stable_12k_dense` 的训练参数骨架。
- `my5` Flux 配置里应改成:
  - `refine_start_idx: 0`
  - `refine_end_idx: 41`
  - `train_start_idx: 0`
  - `train_end_idx: 283`
- 如果后续用户想改成按自定义 `partition.json` 切分, 那这四个索引需要跟着新的 partition 重新计算, 不能继续硬编码当前数值。

## [2026-03-27 22:21:03] [Session ID: 20260327T221426Z-main] 笔记: my5 稳态 12k 训练已完成, `11999` 可直接作为 refine 入口

## 来源

### 来源1: 真实训练日志

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense_run.log`
- 动态证据:
  - 训练最终结束于:
    - `Step: 11999 {'mem': 0.8086118698120117, 'ellipse_time': 107.94528388977051, 'num_GS': 302199}`
  - 错误关键字扫描:
    - `rg -n "Traceback|RuntimeError|Error:" ...`
  - 结果:
    - 无命中

### 来源2: 输出目录核对

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense`
- 要点:
  - `cfg.json` 已写出
  - checkpoints 已存在:
    - `ckpt_8999.pt`
    - `ckpt_9999.pt`
    - `ckpt_10999.pt`
    - `ckpt_11999.pt`
  - stats 已存在:
    - `train_step8999.json`
    - `train_step9999.json`
    - `train_step10999.json`
    - `train_step11999.json`

## 综合发现

### 现象

- 这轮 `my5` 训练不只是起跑成功, 而是完整跑到了 `12000` 步配置对应的最终保存点。
- 当前日志里没有显式异常关键字。

### 当前结论

- `exp_cfg/my5/flux_shinkai_museum_v2.yaml` 里的 `load_step: 11999` 已经有真实 checkpoint 对应。
- 如果下一步要做 Flux refine, 当前不需要再改索引或 checkpoint 名称, 可以直接开跑。

## [2026-03-27 22:31:22] [Session ID: 20260327T221426Z-main] 笔记: `ours.evaluation` 已修正为兼容短训场景, my5 基础评估结果已落盘

## 来源

### 来源1: 评估入口代码与回归测试

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py`
  - `/root/autodl-tmp/home/rais/FreeFix/tests/test_evaluation_cli.py`
- 要点:
  - 基础评估 step 现在默认读取 `cfg.load_step`
  - 可用 `--load-step` 手工覆盖
  - refined checkpoint 不存在时会打印跳过信息, 不再抛错
  - 验证命令:
    - `python3 -m py_compile ours/evaluation.py tests/test_evaluation_cli.py`
    - `.pixi/envs/default/bin/python -m unittest tests.test_evaluation_cli`

### 来源2: my5 真实评估结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/11999_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/11999_train.json`
- 动态证据:
  - `test`:
    - `psnr = 26.647448051266554`
    - `ssim = 0.8796708249464268`
    - `lpips = 0.20539226346626516`
  - `train`:
    - `psnr = 26.728178482594846`
    - `ssim = 0.8815288269898917`
    - `lpips = 0.20358432587170347`

### 来源3: 评估渲染数量核对

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/11999_test`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/11999_train`
- 要点:
  - `11999_test/` 共 `41` 张
  - `11999_train/` 共 `283` 张

## 综合发现

### 现象

- 旧评估 CLI 默认值只适合 `29999 + 已有 refine checkpoint` 的路径。
- `my5` 这种 `11999` 短训基础评估场景会被旧默认行为挡住。

### 当前结论

- 这次修复之后, `ours.evaluation` 已经能直接服务当前 `my5` 这类短训场景。
- 当前已经完成的是基础模型 `11999` 的评估。
- refined 评估仍需要等 `ckpt_flux_shinkai_museum_v2.pt` 真实存在后再继续。

## [2026-03-27 15:19:41] [Session ID: 20260327T151941Z-main] 笔记: `my5 30k_dense` 已完成训练, 关键对照点与周期视频都已落盘

## 来源

### 来源1: 真实 30k 训练日志

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense_run.log`
- 动态证据:
  - 训练进程正常退出 `code 0`
  - 错误关键字扫描:
    - `rg -n "Traceback|RuntimeError|Error:" outputs/my5_colmap_fastgs_stable_30k_dense_run.log`
    - 结果为空
  - 关键 step:
    - `Step: 11999`
    - `Step: 29999`

### 来源2: 30k 输出目录

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense`
- 要点:
  - checkpoints:
    - `ckpt_11999.pt`
    - `ckpt_29999.pt`
  - stats:
    - `train_step11999.json`
    - `train_step29999.json`
  - 视频:
    - `render_ckpt_11999.mp4`
    - `alpha_ckpt_11999.mp4`
    - `render_ckpt_29999.mp4`
    - `alpha_ckpt_29999.mp4`

### 来源3: `ffprobe` 核对

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/to_refine/render_ckpt_29999.mp4`
- 动态证据:
  - `codec_name = h264`
  - `width = 1280`
  - `height = 720`
  - `r_frame_rate = 12/1`
  - `nb_frames = 41`

## 综合发现

### 现象

- 这条 `30k` 线不是只完成了最终 checkpoint。
- 和 `12k` 对照需要的中间点 `11999` 也被完整保留下来了。

### 当前结论

- 当前已经具备继续执行:
  - `29999` 基础评估
  - `29999` refine
  - refined 评估
- 等这些结果出来后, 就能直接回答“12k 之后继续训练有没有收益”。

## [2026-03-27 15:19:41] [Session ID: 20260327T151941Z-main] 笔记: `my5 30k_dense @ 29999` 基础评估结果明显优于 `12k` 基线

## 来源

### 来源1: 30k 基础评估结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/29999_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/29999_train.json`
- 动态证据:
  - `test`:
    - `psnr = 26.99565171032417`
    - `ssim = 0.883747217131824`
    - `lpips = 0.18820923239719578`
  - `train`:
    - `psnr = 27.08867610216983`
    - `ssim = 0.8859333686609572`
    - `lpips = 0.18689768224322753`

### 来源2: 与 12k 基线对照

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/11999_test.json`
- 要点:
  - `12k test`:
    - `psnr = 26.647448051266554`
    - `ssim = 0.8796708249464268`
    - `lpips = 0.20539226346626516`

### 来源3: 评估样本数量核对

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/29999_test`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/29999_train`
- 动态证据:
  - `29999_test/` 共 `41` 张
  - `29999_train/` 共 `283` 张

## 综合发现

### 现象

- 在不改 `pose_opt / depth_loss / test_every / refine_stop_iter` 的前提下, 仅把训练窗口从 `12k` 拉到 `30k`, 基础指标就已经更好了。

### 当前结论

- `12k` 之后继续训练不是“白跑”。
- 至少在当前这条单变量对照线上, 它同时带来了:
  - 更高的 `PSNR`
  - 更高的 `SSIM`
  - 更低的 `LPIPS`
- 接下来需要确认的是:
  - `30k + refine` 还会不会继续提升, 还是会像 `12k + refine` 一样出现 `LPIPS` 回弹。

## [2026-03-27 15:19:41] [Session ID: 20260327T151941Z-main] 笔记: `30k` refine 已完成, 产物完整并对齐 `41` 个 test 视角

## 来源

### 来源1: refine 日志与 refined checkpoint

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2_refine_run.log`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
- 动态证据:
  - refine 进程正常退出 `code 0`
  - 错误关键字扫描为空
  - refined checkpoint 已落盘

### 来源2: refine 前后目录数量

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/before_refine`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/refine/gen`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/after_refine`
- 动态证据:
  - `before_refine/` 共 `41` 张
  - `refine/gen/` 共 `41` 张
  - `after_refine/` 共 `41` 张

### 来源3: refine 前后视频核对

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/before_refine.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/after_refine.mp4`
- 动态证据:
  - 两者都是:
    - `h264`
    - `1280x720`
    - `12 fps`
    - `41` 帧

## 综合发现

### 现象

- `30k` 这条线并没有停在“基础评估更好”这一步。
- refine 主链也已经完整跑通了。

### 当前结论

- 现在只差最后一件事:
  - 跑 refined 评估
- 一旦这组指标出来, 就能给出 `12k 基础 / 12k refine / 30k 基础 / 30k refine` 的完整四象限对照。

## [2026-03-27 14:43:43] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 笔记: my5 训练过程中的周期视频导出已恢复, 旧 checkpoint 视频也已补齐

## 来源

### 来源1: 训练器视频导出路径

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/trainer.py`
- 静态证据:
  - 训练循环里原本只保存 checkpoint
  - eval / render 触发逻辑被注释掉
  - `render_traj()` 原来写死:
    - `for i in range(30, 80): data = self.valset[i]`
- 当前修复:
  - 新增:
    - `render_video_steps`
    - `render_video_interp`
    - `render_video_start_idx`
    - `render_video_end_idx`
  - 新增辅助逻辑:
    - `is_scheduled_training_step`
    - `resolve_render_traj_range`
    - `publish_render_videos`
  - 训练保存 checkpoint 后会按配置触发:
    - `self.maybe_render_training_video(step)`
  - 手动 `--set ckpt=...` 补导时也会保留:
    - `render_ckpt_<step>.mp4`
    - `alpha_ckpt_<step>.mp4`

### 来源2: 回归测试

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/tests/test_trainer_video_export.py`
- 要点:
  - 锁住一基 step 调度语义
  - 锁住 `valset` 范围裁切逻辑
  - 锁住最新别名和带 step 命名副本的复制逻辑
  - 锁住训练期自动调用 `render_traj()` 的参数传递

### 来源3: 真实短测与真实补导

- 短测命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my5/recon_my5_colmap_fastgs_stable_12k_dense.yaml --set max_steps=1 --set save_steps=[1] --set render_video_steps=[1] --set render_video_start_idx=0 --set render_video_end_idx=2 --set result_dir=outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke_r2`
- 短测动态证据:
  - 输出:
    - `Published checkpoint videos to outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke_r2/to_refine/render_ckpt_0.mp4`
    - `.../alpha_ckpt_0.mp4`
  - `ffprobe`:
    - `render_ckpt_0.mp4`: `h264`, `1280x720`, `12 fps`, `2` 帧
    - `alpha_ckpt_0.mp4`: `h264`, `1280x720`, `12 fps`, `2` 帧
- 现有 checkpoint 补导:
  - 已真实跑完:
    - `ckpt_8999.pt`
    - `ckpt_9999.pt`
    - `ckpt_10999.pt`
    - `ckpt_11999.pt`
  - 当前产物:
    - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_8999.mp4`
    - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_9999.mp4`
    - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_10999.mp4`
    - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_11999.mp4`
    - 以及对应 `alpha_ckpt_*.mp4`
  - `ffprobe`:
    - `render_ckpt_11999.mp4`: `h264`, `1280x720`, `12 fps`, `41` 帧
    - `alpha_ckpt_11999.mp4`: `h264`, `1280x720`, `12 fps`, `41` 帧

### 来源4: 动态排错证据

- 第一轮短测报错:
  - `RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn`
- 触发链路:
  - `render_traj()`
  - `rasterize_splats_w_certainty()`
  - `rgbs[..., :3].backward(...)`
- 已验证结论:
  - certainty 渲染依赖一次真实反向传播
  - 因此 `render_traj()` 不能套 `@torch.no_grad()`

## 综合发现

### 现象

- 之前“训练不自动出视频”不是错觉, 而是训练主循环根本没有把视频导出接回来。
- 同时旧 `render_traj()` 只适合某个固定数据窗口, 对 `my5` 这种 `41` 张 test 图的新场景不稳。

### 当前结论

- 现在训练器已经支持按 `render_video_steps` 节奏自动导视频。
- `render_traj()` 已改成按真实 `valset` 长度和可选窗口工作, 不再写死 `30..80`。
- 当前 `my5` 这套已训练结果, 也已经补齐 `8999 / 9999 / 10999 / 11999` 四档视频。

## [2026-03-27 15:07:17] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 笔记: my5 Flux refine 已完成, refined 评估结果已落盘

## 来源

### 来源1: refine 配置与日志

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2_refine_run.log`
- 动态证据:
  - refine 入口:
    - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml`
  - 进程正常退出
  - 错误关键字扫描无命中:
    - `Traceback`
    - `RuntimeError`
    - `Error:`

### 来源2: refine 产物

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2`
- 要点:
  - `before_refine/` 共 `41` 张
  - `refine/gen/` 共 `41` 张
  - `after_refine/` 共 `41` 张
  - `before_refine.mp4` 已存在
  - `after_refine.mp4` 已存在
  - `ffprobe after_refine.mp4`:
    - `h264`
    - `1280x720`
    - `12 fps`
    - `41` 帧

### 来源3: refined 评估结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/flux_shinkai_museum_v2_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/flux_shinkai_museum_v2_train.json`
- 动态证据:
  - `test`:
    - `psnr = 26.753718445940716`
    - `ssim = 0.8817750462671605`
    - `lpips = 0.22343256960554822`
  - `train`:
    - `psnr = 26.80816613995987`
    - `ssim = 0.8829991606857246`
    - `lpips = 0.2217243981445636`
  - 渲染数量:
    - `flux_shinkai_museum_v2_test/` 共 `41` 张
    - `flux_shinkai_museum_v2_train/` 共 `283` 张

## 综合发现

### 现象

- 这轮 refine 已经完整跑完, refined checkpoint 和前后对照视频都已存在。
- refined 评估也已经和当前 `my5` 切分范围完整对齐。

### 当前结论

- refine 后 `PSNR / SSIM` 有小幅提升。
- 但 `LPIPS` 比 refine 前更高, 说明这组 Flux 参数在感知指标上没有同步变好。
- 如果后面还要继续调, 最值得优先碰的是:
  - `strength`
  - `warp_ratio`
  - `refine_steps`

## [2026-03-27 15:36:37] [Session ID: 20260327T153637Z-main] 笔记: `my5` 最终实验结论是“30k 基础更优, 但沿用 12k 的 refine 参数会过度修正”

## 来源

### 来源1: 30k refined 评估结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/flux_shinkai_museum_v2_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/flux_shinkai_museum_v2_train.json`
- 动态证据:
  - `test`:
    - `psnr = 26.76950226760492`
    - `ssim = 0.8836645963715344`
    - `lpips = 0.22542380341669407`
  - `train`:
    - `psnr = 26.86490932370243`
    - `ssim = 0.8852884613583029`
    - `lpips = 0.22316270971887947`

### 来源2: 四组 test 指标对照

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/11999_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/eval/flux_shinkai_museum_v2_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/29999_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2/eval/flux_shinkai_museum_v2_test.json`
- 要点:
  - `12k base test`: `26.6474 / 0.8797 / 0.2054`
  - `12k refine test`: `26.7537 / 0.8818 / 0.2234`
  - `30k base test`: `26.9957 / 0.8837 / 0.1882`
  - `30k refine test`: `26.7695 / 0.8837 / 0.2254`

### 来源3: 关键增量

- 动态证据:
  - `30k base vs 12k base`:
    - `PSNR +0.3482`
    - `SSIM +0.0041`
    - `LPIPS -0.0172`
  - `30k refine vs 30k base`:
    - `PSNR -0.2261`
    - `SSIM -0.00008`
    - `LPIPS +0.0372`
  - `30k refine vs 12k refine`:
    - `PSNR +0.0158`
    - `SSIM +0.0019`
    - `LPIPS +0.0020`

## 综合发现

### 现象

- 更长训练窗口给基础模型带来了稳定收益。
- 但把 `12k` 上那套 refine 参数原样平移到 `30k` 上, 效果并不会跟着基础模型一起单调变好。

### 当前结论

- 如果问题是“12k 之后继续训练有没有收益”, 答案是:
  - 有, 而且基础模型收益明显
- 如果问题是“30000步后再套当前 refine 参数值不值”, 答案是:
  - 不值
  - 当前最优结果其实停在 `30k base`
- 后续若要继续做 refine, 优先方向应该是:
  - 降低 `strength`
  - 降低 `warp_ratio`
  - 缩短 `refine_steps`

## [2026-03-27 17:38:13] [Session ID: 20260327T173813Z-main] 笔记: 当前 benchmark 没有取错对象, “看起来更好”与“更接近 GT”在这条 refine 线上发生了分离

## 来源

### 来源1: 评估入口与 GT 配对代码

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py`
  - `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`
  - `/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py`
- 静态证据:
  - `ours/evaluation.py` 调的是 `refiner.render(..., eval=True)`:
    - `test` 走 `split='test'`
    - `train` 走 `split='train'`
  - `recon/refiner.py` 里 `eval=True` 时直接计算:
    - `psnr(colors, data["image"] / 255.0)`
    - `ssim(colors, data["image"] / 255.0)`
    - `lpips(colors, data["image"] / 255.0)`
  - `recon/datasets/colmap.py` 里 `data["image"]` 直接来自:
    - `self.parser.image_paths[index]`
    - 也就是 COLMAP 场景目录里的真实图片

### 来源2: 动态验证, 确认数据集与 Refiner 看到的是同一批 GT

- 动态证据:
  - `Dataset(split='test')` 与 `Refiner.test_dataset` 都得到:
    - `test 0 -> 001_0_generated_videos_generated_video_0_000001.jpg`
    - `test 1 -> 001_0_generated_videos_generated_video_0_000009.jpg`
    - `test 40 -> 012_9_generated_videos_generated_video_0_000024.jpg`
  - `train` 侧也一一对应:
    - `train 0 -> 001_0_generated_videos_generated_video_0_000002.jpg`
    - `train 282 -> 012_9_generated_videos_generated_video_0_000027.jpg`

### 来源3: 动态验证, `eval_results` 与手工重算逐帧完全一致

- 动态证据:
  - 对 `30k base` 的 test 样本:
    - `idx=0`
    - `idx=1`
    - `idx=40`
  - `refiner.render(..., eval=True)` 返回的:
    - `psnr`
    - `ssim`
    - `lpips`
  - 与我手工用同一张 GT 重算出来的结果完全一致

### 来源4: 配置里没有额外 test 相机偏移

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_30k.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2.yaml`
- 静态证据:
  - `test_split: test`
  - `test_trans: [0, 0, 0]`
  - `test_rots: [0, 0, 0]`
- 当前结论:
  - 当前 test 评估没有额外视角扰动

### 来源5: 逐帧对比 `before_refine` 与 `after_refine` 的动态证据

- 动态证据:
  - 共 `41` 帧
  - `after_refine` 相比 `before_refine`:
    - `PSNR` 变好的帧数: `13`
    - `SSIM` 变好的帧数: `17`
    - `LPIPS` 变好的帧数: `0`
  - 均值(基于导出的 `before/after_refine` 图像复算, 不是 JSON 原值):
    - `before PSNR ≈ 26.9293`
    - `after  PSNR ≈ 26.7069`
    - `before SSIM ≈ 0.8761`
    - `after  SSIM ≈ 0.8759`
    - `before LPIPS ≈ 0.1821`
    - `after  LPIPS ≈ 0.2165`

## 综合发现

### 现象

- 用户主观上觉得 `30k refine` 更顺眼, 这个感受并不奇怪。
- 但从“对原始 test 图的保真度”角度看, 它平均并没有更接近 GT。

### 当前结论

- 当前 benchmark 没有发现“拿错 GT / split 错位 / 指标方向搞反 / 相机被偷偷偏移”这类错误。
- 更合理的解释是:
  - refine prompt 在做“去雾、锐化、修错、增强纹理”
  - 这些变化会让图更讨眼睛喜欢
  - 但也会让它偏离原始 test 图, 所以保真指标下降
- 这不是“评测基准错了”, 更像是:
  - 主观审美目标
  - 与 GT fidelity 指标
  两者开始分叉了

## [2026-03-27 17:57:41] [Session ID: 20260327T175741Z-main] 笔记: `__colmap_my5` 支线续档前的可复用摘要

## 来源

### 来源1: `task_plan__colmap_my5.md` 续档前快照

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/archive/branch_contexts/colmap_my5/snapshots/2026-03-27_175741/task_plan__colmap_my5.md`
- 要点:
  - 这条支线已经完整覆盖:
    - `12k` 训练 / 基础评估 / refine / refined 评估
    - `30k` 训练 / 基础评估 / refine / refined 评估
    - 新开的 `35k` 基线与 `35k te7` 配置与 smoke test
  - 当前最新未完成主线是:
    - `35k base`
    - `35k te7`
    的基础训练与基础评估对比

### 来源2: 当前支线其它六文件

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my5.md`
  - `/root/autodl-tmp/home/rais/FreeFix/WORKLOG__colmap_my5.md`
  - `/root/autodl-tmp/home/rais/FreeFix/LATER_PLANS__colmap_my5.md`
  - `/root/autodl-tmp/home/rais/FreeFix/ERRORFIX__colmap_my5.md`
  - `/root/autodl-tmp/home/rais/FreeFix/EPIPHANY_LOG__colmap_my5.md`
- 要点:
  - `30k base` 目前仍是这条支线里已验证的最好 base 结果
  - 旧 Flux refine 参数直接平移到更强 base 上, 不保证会更好
  - 自动 checkpoint 视频导出已经接回训练流程, `35k` 这轮会按配置自动出视频

### 来源3: `35k` 新一轮的动态证据

- 要点:
  - `test_every: 8`:
    - `train = 283`
    - `test = 41`
  - `test_every: 7`:
    - `train = 277`
    - `test = 47`
  - 并行 smoke test 曾触发:
    - `torch_extensions/.../gsplat_cuda/lock`
  - 串行复跑后两条配置都通过

## 六文件摘要

- 涉及的上下文集:
  - `__colmap_my5`
- 任务目标:
  - 围绕 `my5_colmap_fastgs` 做训练、评估、refine 与后续对照实验
- 关键决定:
  - 索引范围必须按真实 `train/test` 长度计算, 不能照抄旧场景
  - 评估入口要对齐 `cfg.load_step`
  - 更长训练和更强 refine 需要拆开看, 不能混成一个结论
- 关键发现:
  - `30k` 对 base 有稳定收益
  - 当前 refine 参数对 `30k base` 过强
  - `35k` 对照实验里, `test_every` 是目前唯一主动变量
- 实际变更:
  - 已有 `12k / 30k / 35k / 35k_te7` 配置
  - 自动视频导出与短训兼容评估已落地
- 支线组活跃度判定:
  - 活跃
- 暂缓事项 / 后续方向:
  - 先完成 `35k base` 与 `35k te7` 的 base 对照
  - refine 调参属于下一阶段, 暂不混入
- 错误与根因:
  - `gsplat` JIT 锁竞争来自并行起跑, 不是 YAML 错误
- 重大规律:
  - “主观更顺眼”与“更接近 GT”在 refine 路径上可能分叉
- 可复用点候选:
  - 长训对照时, 先锁单变量, 再谈 refine
  - COLMAP split 相关索引必须动态实算
  - `gsplat` 首轮 JIT 编译不要并行起多条训练
- 最适合写到哪里:
  - 当前先保留在支线 `notes`, 不额外扩散到新的长期文件
- 需要同步的现有文档:
  - 暂无
- 是否需要新增或更新 `docs/` / `specs/` / plan 文档:
  - 否
- 是否提取/更新 skill:
  - 否, 当前结论更偏这条支线的运行经验

## 行动建议

- 当前活跃任务最值得坚持的策略是:
  - 把 `35k` 与 `35k te7` 按完全相同的 base 口径跑完
  - 不要插入 refine
  - 不要并行起第二条训练
- 对比结论输出时, 重点先看:
  - `34999_test.json`
  - `34999_train.json`
  - 对应 `render_ckpt_34999.mp4`
  - 再解释切分变化是否让 base 结果更稳或更弱

## [2026-03-27 18:09:34] [Session ID: 20260327T175741Z-main] 笔记: `35k base` vs `35k te7` 已完成, 默认 split 与共同 holdout 口径都已补齐

## 来源

### 来源1: 两条 `35k` 线的默认基础评估结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2/eval/34999_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2/eval/34999_train.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense_te7/flux_shinkai_museum_v2/eval/34999_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense_te7/flux_shinkai_museum_v2/eval/34999_train.json`
- 动态证据:
  - `35k base`:
    - `test`: `27.0246 / 0.8843 / 0.1851`
    - `train`: `27.1572 / 0.8868 / 0.1836`
  - `35k te7`:
    - `test`: `26.9623 / 0.8833 / 0.1880`
    - `train`: `27.1250 / 0.8863 / 0.1867`

### 来源2: 共同 holdout 配置与结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/partitions/my5_te7_te8_common_holdout.json`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_common_holdout.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_te7_common_holdout.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/eval_tmp/my5_colmap_fastgs_stable_35k_dense_common_holdout/flux_shinkai_museum_v2_common_holdout/eval/34999_test.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/eval_tmp/my5_colmap_fastgs_stable_35k_dense_te7_common_holdout/flux_shinkai_museum_v2_common_holdout/eval/34999_test.json`
- 动态证据:
  - 共同 holdout 索引:
    - `[0, 56, 112, 168, 224, 280]`
  - `35k base`:
    - `PSNR 28.6706`
    - `SSIM 0.9127`
    - `LPIPS 0.1492`
  - `35k te7`:
    - `PSNR 28.5839`
    - `SSIM 0.9125`
    - `LPIPS 0.1534`

## 综合发现

### 现象

- 如果只看各自默认 `test` 分数, `35k te7` 比 `35k base` 略差。
- 但这个口径有一个天然问题:
  - `test_every` 一改, `test` 集本身也变了
  - 所以默认 `test` JSON 不是严格同一 benchmark

### 当前结论

- 在“各自默认 split”这个口径下:
  - `te7` 略差
- 在“双方都没见过的共同 holdout 6 张图”这个更公平的口径下:
  - `te7` 仍然略差
- 因此当前可以比较有把握地说:
  - 这轮 `35000` 对照里, `test_every: 7` 没有带来收益
  - `test_every: 8` 仍然是更稳的保留方案

### 额外说明

- 共同 holdout 只有 `6` 张, 规模不大。
- 但它的价值在于:
  - 两条模型都没见过这些图
  - 可以把“benchmark 变了”这个干扰项显式压下去
- 如果后面要继续做更严谨的 split 研究, 最好固定一份独立 `partition.json` 作为所有实验共用 benchmark。

## [2026-03-27 18:09:34] [Session ID: 20260327T180934Z-main] 笔记: 不依赖 refine 时, `35k base` 仍有几条可行优化路线

## 来源

### 来源1: 当前 `35k base` 配置与训练器开关

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/recon_my5_colmap_fastgs_stable_35k_dense.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/recon/trainer.py`
- 静态证据:
  - 当前 `35k base`:
    - `max_steps: 35000`
    - `refine_stop_iter: 9000`
    - `pose_opt: true`
    - `app_opt: false`
    - `depth_loss: true`
    - `antialiased: false`
    - `revised_opacity: false`
  - 训练器里这些都是真实生效的可调项, 不是废配置

### 来源2: `12k -> 30k -> 35k` 的真实 base 收益

- 动态证据:
  - `12k test`:
    - `PSNR 26.6474`
    - `SSIM 0.8797`
    - `LPIPS 0.2054`
  - `30k test`:
    - `PSNR 26.9957`
    - `SSIM 0.8837`
    - `LPIPS 0.1882`
  - `35k test`:
    - `PSNR 27.0246`
    - `SSIM 0.8843`
    - `LPIPS 0.1851`
  - 增量:
    - `12k -> 30k`:
      - `PSNR +0.3482`
      - `SSIM +0.0041`
      - `LPIPS -0.0172`
    - `30k -> 35k`:
      - `PSNR +0.0289`
      - `SSIM +0.00057`
      - `LPIPS -0.00314`

### 来源3: `35k base` 的 GS 状态

- 动态证据:
  - `train_step11999.json`:
    - `num_GS = 322660`
  - `train_step29999.json`:
    - `num_GS = 322660`
  - `train_step34999.json`:
    - `num_GS = 322660`
- 当前结论:
  - 从 `11999` 到 `34999`, 当前模型一直在优化已有 splats
  - 没有再新增几何容量

### 来源4: `my4` 的历史增强路线

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_quality.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_stable_12k_app.yaml`
- 静态证据:
  - `quality` 线明确把“更长训练 + 更长 densify + pose/app/depth”视为增强路径
  - `stable_12k_app` 线明确把“只恢复 `app_opt`”视为可单独证伪的单因素实验

## 综合发现

### 现象

- `35k base` 还在继续变好, 但 `30k -> 35k` 的收益已经明显变小。
- 当前 densify 早在 `9000` 就停掉了, 后面只是对已有 GS 做长时间打磨。
- 这意味着当前残留的“视觉瑕疵”里, 很可能混着两类问题:
  - 结构容量不够或 densify 停得太早
  - 外观漂移 / 曝光不一致 / 颜色补偿不足

### 候选路线

- 路线1: 延长 base 训练, 但重点不是单纯加步数, 而是把 densify 窗口一起拉长
  - 当前假设:
    - 许多瑕疵不是“优化不够久”, 而是“几何容量冻结太早”
  - 证据:
    - `num_GS` 从 `11999` 到 `34999` 完全不变
    - `my4 quality` 线也明确用过“更长训练 + 更长 densify”
  - 最小验证:
    - 保持 `app_opt=false`
    - 先做 `50k`
    - 把 `refine_stop_iter` 从 `9000` 拉到 `20000` 或 `30000`
  - 当前判断:
    - 这是我最推荐先试的 base 路线

- 路线2: 保持 `35k` 训练窗口不变, 只做 `app_opt=true` 的单因素实验
  - 当前假设:
    - 如果瑕疵更像曝光漂移、颜色不稳、局部脏污感, `app_opt` 可能比继续长训更直接
  - 证据:
    - 当前 `35k base` 明确是 `app_opt=false`
    - `my4` 里专门有一条只恢复 `app_opt` 的单因素线
  - 最小验证:
    - 复制当前 `35k base`
    - 只把 `app_opt` 改成 `true`
    - 其它都不动
  - 当前判断:
    - 如果你说的“瑕疵”更偏外观而不是结构, 这条优先级很高

- 路线3: 走数据 / COLMAP 侧清洗, 不继续硬拧训练参数
  - 当前假设:
    - 某些 persistent artifact 可能来自:
      - 位姿误差
      - 模糊帧
      - 脏帧
      - 稀疏点质量
  - 证据:
    - `my4 quality` 第一条增强就先提了“更干净场景”
    - 当前 `pose_opt` 已经开着, 说明这类问题并非完全不存在
  - 最小验证:
    - 先挑几张最明显的瑕疵帧
    - 对应回看原图、相机位姿和 COLMAP 对齐质量
  - 当前判断:
    - 这条路线天花板高, 但人工成本也最高

- 路线4: 低成本画质试探, 例如 `antialiased=true`
  - 当前假设:
    - 如果你主要在意锯齿、闪烁、边缘毛刺, 抗锯齿可能会更顺眼
  - 证据:
    - 训练器里有正式开关
    - 但注释也明确提醒它“可能稍伤量化指标”
  - 当前判断:
    - 这条更像视觉取向的尝试, 不该放在第一优先级

### 当前建议排序

- 第一优先:
  - `50k + 长 densify`
- 第二优先:
  - `35k + app_opt=true` 单因素
- 第三优先:
  - 数据 / COLMAP 清洗
- 第四优先:
  - `antialiased=true` 这类偏渲染观感的小试验

## [2026-03-27 18:54:03] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 笔记: `50k + 长 densify` 相对 `35k base` 的实际收益

## 来源

### 来源1: `35k` 与 `50k` 基础评估 JSON

- 路径:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2/eval/34999_test.json`
  - `outputs/my5_colmap_fastgs_stable_50k_longdensify/flux_shinkai_museum_v2/eval/49999_test.json`
- 要点:
  - `test`: `PSNR +0.02845`, `SSIM -0.00072`, `LPIPS -0.00315`
  - `train`: `PSNR -0.01433`, `SSIM -0.00036`, `LPIPS -0.00279`
  - `num_GS`: 从 `35k base` 的 `322660` 提升到 `50k` 的 `514867`

## 综合发现

### 当前结论

- 这条 `50k + 长 densify` 不是无效长训, 几何容量确实继续长大了。
- 量化结果上, 它对 `test PSNR` 和 `test LPIPS` 有小幅正收益。
- 但收益已经进入很窄的边际区间, 同时 `SSIM` 还有轻微回落。

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 笔记: `my5_nomask_v1` 外部 bridge ckpt 的 base / refined / FastGS 三方对比

## 来源

### 来源1: bridge base / refined 评估 JSON

- 路径:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/35000_test.json`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/35000_train.json`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_test.json`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_train.json`
- 要点:
  - bridge base `test`:
    - `PSNR 23.9542`
    - `SSIM 0.84888`
    - `LPIPS 0.25503`
  - refined `test`:
    - `PSNR 26.6134`
    - `SSIM 0.88035`
    - `LPIPS 0.22109`
  - refined 相对 bridge base:
    - `test PSNR +2.6592`
    - `test SSIM +0.03147`
    - `test LPIPS -0.03394`
    - `train PSNR +2.6387`
    - `train SSIM +0.03098`
    - `train LPIPS -0.03432`

### 来源2: FastGS 原始结果记录

- 路径:
  - `/home/rais/FastGS/output/my5_nomask_v1/results.json`
- 要点:
  - `PSNR 27.2039`
  - `SSIM 0.8910`
  - `LPIPS 0.2026`

## 综合发现

### 已验证事实

- refine 对 bridge base 的收益非常明确, 不只是主观画面修补。
- bridge base 和 FastGS 原始结果之间存在明显差距。
- refined 把这条差距拉回了很多, 但还没有完全追平 FastGS 原始记录。

### 候选假设

- 假设1:
  - `import_fastgs` 的归一化契约, 对这份 `my5` checkpoint 可能不是严格对齐的
- 假设2:
  - FastGS 与 FreeFix 的 benchmark 口径并不完全一致, 例如:
    - test split
    - 相机顺序
    - 图像匹配关系
- 假设3:
  - 两边渲染细节不同, 导致同一状态在量化上不可直接一比一对齐

### 下一步最小验证

- 先做一次 `--no-normalize` 对照导入并重评估
- 再核对 test 图顺序与相机顺序
- 最后按单帧补一次指标复算, 看差异是否来自 benchmark 口径

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 笔记: `my5_nomask_v1` bridge 掉分原因已锁定到高阶 SH 旋转缺失

## 来源

### 来源1: benchmark 与 checkpoint 契约验证

- 要点:
  - FreeFix `test` dataset 与 FastGS `test/ours_35000/gt` 的 `41` 张 GT 图逐帧像素一致
  - FastGS render 用 FreeFix 指标重算:
    - `PSNR 27.2039`
    - `SSIM 0.8898`
    - `LPIPS 0.1978`
  - `ckpt_35000.pth` 与 `point_cloud.ply` 解出的:
    - `means / opacities / scales / quats / sh0 / shN`
    全部完全一致

### 来源2: raw / normalized 对照评估

- 要点:
  - raw checkpoint + raw cameras + FreeFix renderer:
    - `PSNR 27.1882`
    - `SSIM 0.8907`
    - `LPIPS 0.2037`
  - normalized checkpoint + normalized cameras:
    - `PSNR 23.9542`
    - `SSIM 0.8489`
    - `LPIPS 0.2550`
  - `--no-normalize` checkpoint 如果直接喂给 normalized cameras:
    - `PSNR 11.6517`
    - `SSIM 0.6638`
    - `LPIPS 0.7779`

### 来源3: 变换矩阵与 DC-only 对照

- 要点:
  - FreeFix 归一化 transform 的旋转角约:
    - `86.79` 度
  - `transform_splats_to_freefix()` 当前会变换:
    - `means`
    - `quats`
    - `scales`
  - 但不会旋转:
    - `sh0`
    - `shN`
  - 当把 `shN` 清零后:
    - raw + raw cameras:
      - `PSNR 25.9171`
      - `SSIM 0.8764`
      - `LPIPS 0.2295`
    - normalized + normalized cameras:
      - `PSNR 25.9171`
      - `SSIM 0.8764`
      - `LPIPS 0.2295`
    - 两者几乎完全一致

## 综合发现

### 已验证结论

- 不是 benchmark 对不上。
- 不是 `ckpt_35000.pth` 的解析错误。
- 不是 FreeFix renderer 本身不能复现 FastGS raw 状态。
- 真正的问题发生在:
  - 把 raw FastGS 状态变换到 FreeFix normalized 坐标时
- 更具体地说:
  - 几何参数已经正确跟着全局 similarity transform 走了
  - 但高阶 SH 系数没有随全局旋转做对应的 SH basis rotation
- 因此当前 bridge base 掉分的主因已经锁定为:
  - `recon.import_fastgs` 的归一化变换只覆盖了几何, 没覆盖方向相关颜色

### 后续修复方向

- 如果继续落地修复, 第一优先是:
  - 给 `transform_splats_to_freefix()` 增加高阶 SH rotation
- 修完后最小回归验证应该是:
  - raw + raw cameras vs normalized + normalized cameras
  - 二者在 full SH 下重新接近
