## [2026-03-27 22:21:03] [Session ID: 20260327T221426Z-main] 任务名称: 基于 my5_colmap_fastgs 完成 my5 稳态 12k 训练

### 任务内容
- 新建 `exp_cfg/my5/` 下的训练配置和 Flux refine 配置。
- 使用 `/home/rais/FastGS/data/my5_colmap_fastgs` 这份外部 COLMAP 数据完成一轮真实训练。
- 核对 `my5` 的 `train/test` 索引范围, 避免把 `my4` 的旧 `0..100` 范围直接错误平移。

### 完成过程
- 先回读 `my4` 的 `stable_12k_dense` 训练配置和 `flux_shinkai_museum_v2` refine 配置。
- 再读 `ours/refine_by_flux.py`、`recon/refiner.py`、`recon/datasets/colmap.py`, 确认:
  - `train_*` 作用于 `train_dataset`
  - `refine_*` 作用于 `test_dataset`
- 用项目环境里的真实 `Parser` / `Dataset` 动态验证 `my5` 当前切分结果:
  - 总图像数 `324`
  - `train = 283`
  - `test = 41`
- 基于这个结果生成:
  - `exp_cfg/my5/recon_my5_colmap_fastgs_stable_12k_dense.yaml`
  - `exp_cfg/my5/flux_shinkai_museum_v2.yaml`
- 先运行一次 `max_steps=1` 的 smoke test, 确认 YAML、数据路径和训练入口都可用。
- smoke test 通过后, 启动真实 `12k` 训练并落盘日志 `outputs/my5_colmap_fastgs_stable_12k_dense_run.log`
- 最后核对训练收尾产物:
  - `ckpt_8999.pt`
  - `ckpt_9999.pt`
  - `ckpt_10999.pt`
  - `ckpt_11999.pt`
  - 对应 `stats/*.json`

### 总结感悟
- `refine_*` 和 `train_*` 是否对齐, 不能看原始图片总数猜, 必须看代码实际索引的是哪套 dataset。
- 对这类“参考旧配置平移新场景”的任务, 先做一次最小 smoke test, 能避免把长训时间浪费在 YAML 或路径级错误上。
- 当前 `my5` 训练已经完整收口, 后续 Flux refine 可以直接接 `ckpt_11999.pt`。

## [2026-03-27 22:31:22] [Session ID: 20260327T221426Z-main] 任务名称: 完成 my5 基础模型评估并修复评估入口的短训兼容性

### 任务内容
- 修复 `ours.evaluation` 的 CLI 默认行为, 让它支持 `load_step != 29999` 的训练结果。
- 为 `my5 stable_12k_dense @ 11999` 运行真实评估。
- 核对评估结果文件、渲染图数量和 refined 缺失时的跳过行为。

### 完成过程
- 先读取 `ours/evaluation.py`, 确认旧入口写死:
  - `29999`
  - `cfg.exp_name`
- 然后修改为:
  - 基础模型默认使用 `cfg.load_step`
  - 支持 `--load-step`
  - refined checkpoint 不存在时打印跳过信息而不是直接失败
- 新增回归测试 `tests/test_evaluation_cli.py`
- 运行验证:
  - `python3 -m py_compile ours/evaluation.py tests/test_evaluation_cli.py`
  - `.pixi/envs/default/bin/python -m unittest tests.test_evaluation_cli`
- 真实执行:
  - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml --eval_test`
- 读取结果文件, 得到:
  - test:
    - `PSNR 26.6474`
    - `SSIM 0.8797`
    - `LPIPS 0.2054`
  - train:
    - `PSNR 26.7282`
    - `SSIM 0.8815`
    - `LPIPS 0.2036`

### 总结感悟
- 评估入口写死长训 step, 在短训项目里会变成一种“隐藏故障”。
- 这类问题最好直接修入口默认行为, 而不是每次靠一次性命令绕过去。
- 当前 `my5` 基础评估已经完成, 下一步只剩 refine 完成后的 refined 评估。

## [2026-03-27 14:43:43] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 任务名称: 补上 my5 训练过程中的周期视频自动导出, 并回填现有 4 档 checkpoint 视频

### 任务内容
- 让 `my5` 训练按 checkpoint 节奏自动导出轨迹视频。
- 修复 `render_traj()` 对固定 `valset[30:80]` 的旧假设。
- 把这次已经训练完的 `8999 / 9999 / 10999 / 11999` 四档视频也实际补导出来。

### 完成过程
- 先读 `recon/trainer.py`, 确认:
  - 训练循环只保存 checkpoint, 自动 render 逻辑被注释
  - `render_traj()` 写死取 `30..80`, 对 `my5 test=41` 有越界风险
- 然后在训练器里新增:
  - `render_video_steps`
  - `render_video_interp`
  - `render_video_start_idx`
  - `render_video_end_idx`
  - `maybe_render_training_video()`
- 同时把视频产物发布逻辑改成:
  - 保留最新别名:
    - `render.mp4`
    - `alpha.mp4`
  - 额外保留带 step 名的副本:
    - `render_ckpt_<step>.mp4`
    - `alpha_ckpt_<step>.mp4`
- 为这次改动新增回归测试:
  - `tests/test_trainer_video_export.py`
- 做真实短测时先撞到一个动态 bug:
  - 我误把 `render_traj()` 包上了 `@torch.no_grad()`
  - 结果 certainty 路径里的 `backward()` 直接报错
- 修掉这个问题后, 重新做真实短测:
  - 成功生成:
    - `outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke_r2/to_refine/render_ckpt_0.mp4`
    - `.../alpha_ckpt_0.mp4`
- 最后把当前已有的 4 个真实 checkpoint 全部补导:
  - [render_ckpt_8999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_8999.mp4)
  - [alpha_ckpt_8999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/alpha_ckpt_8999.mp4)
  - [render_ckpt_9999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_9999.mp4)
  - [alpha_ckpt_9999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/alpha_ckpt_9999.mp4)
  - [render_ckpt_10999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_10999.mp4)
  - [alpha_ckpt_10999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/alpha_ckpt_10999.mp4)
  - [render_ckpt_11999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_11999.mp4)
  - [alpha_ckpt_11999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/alpha_ckpt_11999.mp4)

### 总结感悟
- 这类“导出 certainty / mask”的渲染函数, 不一定能无脑套 `no_grad`, 因为它可能内部就靠一次反向传播构造派生可视化。
- 如果一个产物既要给下游流程用, 又要给人留档看, 最稳的是同时保留:
  - 最新别名
  - 带 checkpoint 名的稳定副本

## [2026-03-27 18:09:34] [Session ID: 20260327T175741Z-main] 任务名称: 完成 `35k base` 与 `35k te7` 的真实对比, 并补共同 holdout 公平评测

### 任务内容
- 保留 `35000` 基线配置, 跑完 `test_every: 8` 的 `35k base`。
- 新建并跑完只改 `test_every: 7` 的 `35k te7` 对照线。
- 不只看各自默认 split, 还额外构造一份双方都没见过的共同 holdout 交集 benchmark。

### 完成过程
- 先续档 `task_plan__colmap_my5.md`, 避免继续在 1000+ 行的旧计划里追加。
- 然后接管并跑完:
  - `outputs/my5_colmap_fastgs_stable_35k_dense_run.log`
  - `outputs/my5_colmap_fastgs_stable_35k_dense_te7_run.log`
- 两条线都核对了:
  - `ckpt_11999.pt`
  - `ckpt_29999.pt`
  - `ckpt_34999.pt`
  - 对应 `train_step*.json`
  - 对应 `render_ckpt_*.mp4`
- 跑完两条线的基础评估后, 又新增:
  - `exp_cfg/my5/partitions/my5_te7_te8_common_holdout.json`
  - `flux_shinkai_museum_v2_35k_common_holdout.yaml`
  - `flux_shinkai_museum_v2_35k_te7_common_holdout.yaml`
- 最后基于共同 holdout 6 张图做公平对比, 避免把“默认 test 集不同”误当成纯模型差异。

### 总结感悟
- 对 split 规则做对比时, 改掉 `test_every` 不只是“训练集变了”, 连 benchmark 也一起变了。
- 所以这类实验最稳的做法不是只看默认 `test` 分数, 而是再补一个固定 holdout 口径。
- 当前这轮结果已经足够说明:
  - `35k test_every: 8` 比 `35k test_every: 7` 更稳
  - 后续没必要把 `te7` 当成新的主线基线

## [2026-03-27 18:54:03] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 任务名称: 完成 `50k + 长 densify` 训练、评估与 `35k base` 对比

### 任务内容
- 在 `my5` 主线上新增一条:
  - `max_steps: 50000`
  - `refine_stop_iter: 30000`
  的长 densify base 路线。
- 明确保持:
  - `app_opt=false`
  - `test_every: 8`
  - 其它核心训练参数与 `35k base` 同口径。
- 跑完真实训练、基础评估, 并和现有 `35k base` 做直接对比。

### 完成过程
- 新建并使用:
  - [recon_my5_colmap_fastgs_stable_50k_longdensify.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/recon_my5_colmap_fastgs_stable_50k_longdensify.yaml)
  - [flux_shinkai_museum_v2_50k_longdensify.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_50k_longdensify.yaml)
- 先做 `1 step` smoke test, 确认:
  - 切分正常
  - 训练入口正常
  - 周期视频导出正常
- 再串行跑完真实 `50k` 训练, 核对:
  - `ckpt_11999.pt`
  - `ckpt_29999.pt`
  - `ckpt_34999.pt`
  - `ckpt_49999.pt`
  - 对应 `render_ckpt_*.mp4`
- 最后完成基础评估, 得到:
  - `test`: `PSNR 27.0530`, `SSIM 0.88359`, `LPIPS 0.18192`
  - `train`: `PSNR 27.1429`, `SSIM 0.88646`, `LPIPS 0.18085`
- 对比 `35k base`:
  - `test`: `PSNR +0.02845`, `SSIM -0.00072`, `LPIPS -0.00315`
  - `train`: `PSNR -0.01433`, `SSIM -0.00036`, `LPIPS -0.00279`

### 总结感悟
- 这条长 densify 路线确实继续扩大了几何容量, 不是“只多跑了 15000 步”。
- 但当前收益已经明显变成边际收益:
  - `PSNR` 小涨
  - `LPIPS` 小降
  - `SSIM` 微跌
- 如果后面继续优化 base, 更值得做的是:
  - 继续精细调 densify 窗口
  - 或回头清洗数据 / COLMAP
  - 而不是无脑继续加步数

## [2026-03-27 15:07:17] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 任务名称: 完成 my5 的 Flux refine 与 refined 评估

### 任务内容
- 基于 `ckpt_11999.pt` 启动 `flux_shinkai_museum_v2` refine。
- 核对 refined checkpoint、前后视频和中间生成结果。
- 继续执行 refined 评估, 拿到 refine 后的真实指标。

### 完成过程
- 先确认 `refine_by_flux` 实际读取的是:
  - 基础训练 `cfg.json`
  - `ckpt_11999.pt`
  - 当前 `train/test` 数据索引
- 由此确认这轮视频导出改动不会破坏 refine 输入链路
- 然后真实执行:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml`
- refine 跑完后核对:
  - [ckpt_flux_shinkai_museum_v2.pt](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt)
  - [before_refine.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/before_refine.mp4)
  - [after_refine.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2/after_refine.mp4)
  - `before_refine / refine/gen / after_refine` 三组都各有 `41` 张
- 接着执行 refined 评估:
  - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml --eval_test`
- 最终拿到 refined 结果:
  - `test`:
    - `PSNR 26.7537`
    - `SSIM 0.8818`
    - `LPIPS 0.2234`
  - `train`:
    - `PSNR 26.8082`
    - `SSIM 0.8830`
    - `LPIPS 0.2217`

### 总结感悟
- 这轮 refine 是成功收口的, 不是只生成了中间图, 而是完整落了 refined checkpoint 和 refine 后评估。
- 当前 `PSNR / SSIM` 比基础模型略好, 但 `LPIPS` 变差, 说明“更像参考图的像素统计”和“更好的感知相似度”并没有自动同向。

## [2026-03-27 15:36:37] [Session ID: 20260327T153637Z-main] 任务名称: 完成 my5 的 30k 对照训练、refine 与 12k 对照评估

### 任务内容
- 新建 `30k` 对照配置:
  - `exp_cfg/my5/recon_my5_colmap_fastgs_stable_30k_dense.yaml`
  - `exp_cfg/my5/flux_shinkai_museum_v2_30k.yaml`
- 完成 `my5 stable_30k_dense` 的真实训练、基础评估、Flux refine 和 refined 评估。
- 用统一口径对比 `12k` 与 `30k` 的基础模型和 refine 后模型质量。

### 完成过程
- 先对 `30k` YAML 做最小 smoke test, 确认:
  - `Trainset Size = 283`
  - `Test Size = 41`
  - 视频导出仍可正常触发
- 然后启动真实 `30k` 训练并核对关键产物:
  - `ckpt_11999.pt`
  - `ckpt_29999.pt`
  - `train_step11999.json`
  - `train_step29999.json`
  - `render_ckpt_11999.mp4`
  - `render_ckpt_29999.mp4`
- 接着执行 `29999` 的基础评估, 得到:
  - `test`: `PSNR 26.9957`, `SSIM 0.8837`, `LPIPS 0.1882`
  - `train`: `PSNR 27.0887`, `SSIM 0.8859`, `LPIPS 0.1869`
- 再执行 `30k` 的 Flux refine, 核对:
  - `ckpt_flux_shinkai_museum_v2.pt`
  - `before_refine.mp4`
  - `after_refine.mp4`
  - `before_refine / refine/gen / after_refine` 都各 `41` 张
- 最后执行 refined 评估, 得到:
  - `test`: `PSNR 26.7695`, `SSIM 0.8837`, `LPIPS 0.2254`
  - `train`: `PSNR 26.8649`, `SSIM 0.8853`, `LPIPS 0.2232`

### 总结感悟
- 对这条 `my5 stable_dense` 线来说, 把训练从 `12k` 拉到 `30k`, 基础模型收益是明确且稳定的:
  - test `PSNR +0.3482`
  - test `SSIM +0.0041`
  - test `LPIPS -0.0172`
- 但把 `12k` 上的 Flux refine 参数原样搬到 `30k` 上会过度修正:
  - 相比 `30k base`, refine 后 `PSNR` 下降约 `0.2261`
  - `LPIPS` 变差约 `0.0372`
- 当前最好的结果不是 `30k refine`, 而是 `30k base`。后续如果继续做 refine, 应优先调轻:
  - `strength`
  - `warp_ratio`
  - `refine_steps`

## [2026-03-27 17:38:13] [Session ID: 20260327T173813Z-main] 任务名称: 复核 `30k refine` 指标变差是否属于评测基准错误

### 任务内容
- 重新核对 `30k refine -> 30k base` 的指标差异是不是由 benchmark 取错对象导致。
- 检查:
  - GT 来源
  - test/train split 配对
  - 单帧指标计算
  - 是否存在额外相机偏移

### 完成过程
- 先读取:
  - `ours/evaluation.py`
  - `recon/refiner.py`
  - `recon/datasets/colmap.py`
- 确认评估入口最终比较的是:
  - 当前渲染结果 `colors`
  - 对应样本的 `data["image"] / 255.0`
- 再用项目 `.pixi` 环境动态验证:
  - `Dataset(split='test')` 与 `Refiner.test_dataset` 读到的是同一批 test 图片
  - `refiner.render(..., eval=True)` 返回的 `eval_results`
    与我手工重算的 `psnr / ssim / lpips` 完全一致
- 最后对 `30k` 导出的 `before_refine/after_refine` 做逐帧复算:
  - `41` 帧里:
    - `PSNR` 变好 `13` 帧
    - `SSIM` 变好 `17` 帧
    - `LPIPS` 变好 `0` 帧

### 总结感悟
- 这次没有发现 benchmark 本身有错:
  - 没有 GT 取错
  - 没有 split 错位
  - 没有指标方向搞反
  - 当前配置也没有额外 test 视角扰动
- 更合理的解释是:
  - refine 让一部分帧看起来更锐、更干净、更“好看”
  - 但这些增强同时让它偏离了原始 test 图
  - 所以主观观感和 fidelity 指标开始分叉

## [2026-03-27 18:55:57] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 任务名称: `50k + 长 densify` 支线收口补记

### 任务内容
- 按上下文文件的尾部追加规则, 补登记这轮 `50k` 训练与评估的最终结论。

### 完成过程
- 复核 `50k` 训练日志、checkpoint、阶段视频和评估 JSON。
- 确认这轮与 `35k base` 可以直接同 benchmark 对比。
- 把结论同步回:
  - `task_plan__colmap_my5.md`
  - `notes__colmap_my5.md`
  - `EPIPHANY_LOG__colmap_my5.md`
  - `LATER_PLANS__colmap_my5.md`

### 总结感悟
- `50k + 长 densify` 是有效优化, 但已经不是高斜率收益段。
- 当前这条 base 主线更适合进入“精调 densify / 清洗数据”的阶段, 不适合继续粗放堆步数。

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 任务名称: 把外部 `my5_nomask_v1` FastGS checkpoint 接进 FreeFix 并完成 refine

### 任务内容
- 把 `/home/rais/FastGS/output/my5_nomask_v1/checkpoints/ckpt_35000.pth` 复制到本项目 `data/`。
- 在本项目内把这份 FastGS `.pth` 转成 FreeFix 可读的 bridge ckpt。
- 基于 `my5` 的现有 COLMAP 数据和 `app_opt=false` 主线配置, 跑完一轮真实 Flux refine。

### 完成过程
- 先动态确认外部 checkpoint 结构:
  - `iteration = 35000`
  - 初始高斯数 `49200`
- 再复制到:
  - [ckpt_35000.pth](/root/autodl-tmp/home/rais/FreeFix/data/fastgs_bridge/my5_nomask_v1/ckpt_35000.pth)
- 然后桥接转换到:
  - [ckpt_35000_freefix.pt](/root/autodl-tmp/home/rais/FreeFix/data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt)
- 为这轮外部 checkpoint 新建专用 refine 配置:
  - [flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.yaml)
- 中途撞到一个真实运行级 bug:
  - `ours/run_fastgs_refine.py` 用脚本路径方式调用 refine 时, 实跑会报 `ModuleNotFoundError: No module named 'ours'`
- 随后把 wrapper 改成 `python -m ours.refine_by_flux / ours.refine_by_sdxl`, 并跑过:
  - `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py`
  - `.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine`
- 最后真实 refine 成功收口, 产物包括:
  - [before_refine.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/before_refine.mp4)
  - [after_refine.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/after_refine.mp4)
  - [gen.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/refine/gen.mp4)
  - [ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.pt](/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.pt)

### 总结感悟
- 这条桥接链路已经从“理论可行”升级成了“真实 `my5` 外部 run 已验证可用”。
- 外部 FastGS checkpoint 进入 FreeFix refine 后, 高斯数从 `49200` 增长到了 `154614`, 说明它能被继续 densify, 不是只做静态渲染。
- 当前还没补定量评估, 不是 refine 没跑完, 而是评估入口暂时还不支持像 refine 一样直接接外部 bridge ckpt。

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 任务名称: 补上 bridge ckpt 的评估入口, 并完成 `my5_nomask_v1` 的 base/refined 对比

### 任务内容
- 给 [evaluation.py](/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py) 增加:
  - `--ckpt-path`
  - `--colmap-path`
  这两类运行时 override。
- 确保 bridge base 评估能读外部转换 ckpt, 同时 refined 评估仍然读:
  - `ckpt_<exp_name>.pt`
- 跑完这条 `my5_nomask_v1` bridge 线的真实 base / refined 评估并做对比。

### 完成过程
- 先在 [evaluation.py](/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py) 里补了:
  - `resolve_optional_checkpoint_path`
  - `apply_runtime_path_overrides`
  - `use_ckpt_override` 分流
- 再更新 [test_evaluation_cli.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_evaluation_cli.py), 锁定:
  - 基础评估可用外部 ckpt override
  - refined 评估不会误吃这个 override
- 做完验证:
  - `python3 -m py_compile ours/evaluation.py tests/test_evaluation_cli.py`
  - `.pixi/envs/default/bin/python -m unittest tests.test_evaluation_cli`
  - `.pixi/envs/default/bin/python -m ours.evaluation --help`
- 最后执行真实评估:
  - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.yaml --colmap-path /home/rais/FastGS/data/my5_colmap_fastgs --ckpt-path /root/autodl-tmp/home/rais/FreeFix/data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt --eval_test`
- 得到结果:
  - bridge base `test`:
    - `PSNR 23.9542`
    - `SSIM 0.84888`
    - `LPIPS 0.25503`
  - refined `test`:
    - `PSNR 26.6134`
    - `SSIM 0.88035`
    - `LPIPS 0.22109`
  - refined 相对 base 的 `test` 增量:
    - `PSNR +2.6592`
    - `SSIM +0.03147`
    - `LPIPS -0.03394`

### 总结感悟
- 这次已经把“外部 bridge ckpt 不能评估”的链路缺口补齐了。
- 更重要的是, 这条 `my5_nomask_v1` 线上 refine 的收益非常明确, 不是边际改善, 而是量化上也有明显拉升。
- 但同时也观察到一个重要现象:
  - bridge base 明显低于 FastGS 原始 `results.json`
  - refined 虽然拉回来了很多, 但仍没完全追平原始 FastGS 结果
- 这个现象值得后续单独调查, 但当前还不能直接说已经确认根因。

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 任务名称: bridge 评估对比收尾与支线记录补齐

### 任务内容
- 复核 `my5_nomask_v1` 这条外部 bridge 线的 base / refined / FastGS 原始指标。
- 把这轮对比的最终结论和长期风险同步回支线记录。
- 明确区分:
  - 已验证结论
  - 候选假设

### 完成过程
- 重新读取并核对:
  - `35000_test.json`
  - `35000_train.json`
  - `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_test.json`
  - `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_train.json`
  - `/home/rais/FastGS/output/my5_nomask_v1/results.json`
- 复核后的关键 test 指标是:
  - bridge base:
    - `PSNR 23.9542`
    - `SSIM 0.84888`
    - `LPIPS 0.25503`
  - refined:
    - `PSNR 26.6134`
    - `SSIM 0.88035`
    - `LPIPS 0.22109`
  - FastGS 原始记录:
    - `PSNR 27.2039`
    - `SSIM 0.8910`
    - `LPIPS 0.2026`
- refined 相对 bridge base 的 test 增量确认是:
  - `PSNR +2.6592`
  - `SSIM +0.03147`
  - `LPIPS -0.03394`
- 最后把“bridge base 低于 FastGS 原始结果”沉淀为长期风险, 并把后续最小验证路线写回 `LATER_PLANS__colmap_my5.md`。

### 总结感悟
- 跨框架 checkpoint 对接里, “可以继续 refine” 和 “可以无损复现原始 base benchmark” 是两件不同的事。
- 这次已经证明 bridge refine 这条生产链路可用。
- 但如果后面要做严谨结论, 还需要继续验证 bridge fidelity 的损失到底来自:
  - 导入归一化
  - benchmark 口径
  - 还是渲染 / 相机契约差异

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 任务名称: 锁定 `my5_nomask_v1` bridge base 掉分根因

### 任务内容
- 用最小可证伪实验回答:
  - 为什么 FastGS `ckpt_35000.pth` 转进 FreeFix 后, bridge base 会从约 `27.2` 掉到约 `23.95`
- 重点区分:
  - benchmark 问题
  - checkpoint 解析问题
  - renderer 问题
  - 归一化变换问题

### 完成过程
- 先验证 benchmark:
  - FreeFix test GT 与 FastGS `test/ours_35000/gt` 的 `41` 张图逐帧像素一致
  - FastGS render 用 FreeFix 指标重算后仍是:
    - `PSNR 27.2039`
    - `SSIM 0.8898`
    - `LPIPS 0.1978`
- 再验证 checkpoint 解析:
  - `ckpt_35000.pth` 和 `point_cloud/iteration_35000/point_cloud.ply` 解出的高斯状态逐项完全一致
- 再做 raw / normalized 判别实验:
  - raw checkpoint + raw cameras + FreeFix renderer:
    - `PSNR 27.1882`
    - `SSIM 0.8907`
    - `LPIPS 0.2037`
  - normalized checkpoint + normalized cameras:
    - `PSNR 23.9542`
    - `SSIM 0.8489`
    - `LPIPS 0.2550`
- 最后做 DC-only 实验:
  - 把 `shN` 清零后, raw 与 normalized 两条线几乎完全一致:
    - `PSNR 25.9171`
    - `SSIM 0.8764`
    - `LPIPS 0.2295`

### 总结感悟
- 这次已经把掉分来源收缩到非常具体的一点:
  - 不是“整个 bridge 思路不对”
  - 而是“坐标归一化时, 高阶 SH 没跟着全局旋转一起变换”
- 由于这份场景的全局旋转约有 `86.79` 度, 这个遗漏不是小误差, 会直接伤到 view-dependent color。
- 这也解释了为什么:
  - bridge base 掉得明显
  - refine 却还能把它拉回很多
  - 因为 refine 本质上在重新修补方向相关外观
