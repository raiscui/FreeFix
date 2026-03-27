# 任务计划: 基于 my5_colmap_fastgs 训练一套 my5

## [2026-03-27 22:14:26] [Session ID: 20260327T221426Z-main] [记录类型]: 建立 my5 训练支线计划

## 目标

- 使用 `/home/rais/FastGS/data/my5_colmap_fastgs` 这份外部 COLMAP 数据, 在当前仓库里启动一套 `my5` 训练。
- 复用 `my4` 的 `stable_12k_dense` 训练策略, 但把数据路径、输出目录和 Flux refine 索引范围都对齐到 `my5`。
- 在真正启动长训前, 先做一次最小 smoke test, 确保 YAML 配置和训练入口都能被当前项目环境正确加载。

## 阶段

- [x] 阶段1: 回读项目上下文、`my4` 配置和训练入口
- [x] 阶段2: 验证 `my5` 数据结构与 `train/test` 索引语义
- [ ] 阶段3: 生成 `my5` 训练配置和 Flux refine 配置
- [ ] 阶段4: 执行 smoke test 并启动真实训练
- [ ] 阶段5: 记录运行入口、日志位置和后续建议

## 关键问题

1. `my5` 数据当前能不能直接给 `recon.datasets.colmap.Parser` 读取:
   - 已验证事实:
     - 目录存在 `images/`
     - 目录存在 `sparse/0`
     - 目录存在 `distorted/database.db`
   - 当前结论:
     - 这份数据已经满足当前训练入口的基本目录骨架, 不需要先做额外导入脚本。
2. `flux` 配置里的 `train_*` 和 `refine_*` 到底指向哪套索引:
   - 已验证事实:
     - `ours/refine_by_flux.py` 里:
       - `train_*` 用于 `refiner.train_dataset[j]`
       - `refine_*` 用于 `refiner.render(i)` 的默认 `test` split
     - `recon/datasets/colmap.py` 里:
       - 无 `partition` 时, `train` 与 `test` 会按 `test_every` 做互斥划分
   - 当前结论:
     - 这两组索引不能按原始图片总数直接照抄。
3. `my5` 在当前 `test_every: 8` 规则下的真实长度是多少:
   - 已验证事实:
     - 动态脚本输出:
       - `total = 324`
       - `train = 283`
       - `test = 41`
   - 当前结论:
     - 这轮若要全覆盖当前切分:
       - `train_start_idx = 0`
       - `train_end_idx = 283`
       - `refine_start_idx = 0`
       - `refine_end_idx = 41`
4. `load_step` 该写多少:
   - 已验证事实:
     - `recon/trainer.py` 按 `ckpt_{step}.pt` 存盘
     - 最终一步会在 `step == max_steps - 1` 时保存
   - 当前结论:
     - 若训练配置 `max_steps = 12000`, 最终 checkpoint 名应对齐 `ckpt_11999.pt`
     - 因此 Flux 配置的 `load_step` 也应写 `11999`

## 做出的决定

- 决定1: 新配置统一放到 `exp_cfg/my5/` 下, 不去改 `exp_cfg/my4/` 现有文件。
- 决定2: 训练配置继续沿用 `my4 stable_12k_dense` 的稳态参数, 先保证同类可比。
- 决定3: 数据路径直接使用用户给出的外部绝对路径, 不额外复制数据。
- 决定4: Flux 配置保持 `my4` 已跑通的 prompt 与参数, 只改 `base_dir` 和索引范围。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段3** - 已经完成索引语义和真实长度验证, 现在开始落盘 `my5` 配置文件。

## [2026-03-27 22:14:26] [Session ID: 20260327T221426Z-main] [记录类型]: `my5` 配置已落盘, 转入 smoke test

## 阶段

- [x] 阶段1: 回读项目上下文、`my4` 配置和训练入口
- [x] 阶段2: 验证 `my5` 数据结构与 `train/test` 索引语义
- [x] 阶段3: 生成 `my5` 训练配置和 Flux refine 配置
- [ ] 阶段4: 执行 smoke test 并启动真实训练
- [ ] 阶段5: 记录运行入口、日志位置和后续建议

## 关键问题

1. 这轮配置文件是否已经全部落地:
   - 已验证事实:
     - 已新建 `exp_cfg/my5/recon_my5_colmap_fastgs_stable_12k_dense.yaml`
     - 已新建 `exp_cfg/my5/flux_shinkai_museum_v2.yaml`
   - 当前结论:
     - 进入运行前所需的静态配置已经齐备
2. 下一步最需要先验证什么:
   - 当前主假设:
     - 训练入口可以直接吃这份 YAML 和外部场景路径
   - 最强备选解释:
     - 也可能在真实启动时暴露出环境缺包、数据字段不兼容或 CUDA 运行时问题
   - 当前验证计划:
     - 先用 `max_steps=1` 做一次 smoke test
     - 通过后再启动真正的长训

## 做出的决定

- 决定5: 不直接盲启 12k 长训, 先做一次最小 smoke test。
- 决定6: smoke test 使用同一份 YAML, 只通过命令行 override 改 `max_steps` 和 `result_dir`, 避免生成第二套几乎重复的配置文件。

## 状态

**目前在阶段4** - 正在执行最小 smoke test, 确认训练入口、数据路径和当前环境能正常起跑。

## [2026-03-27 22:18:31] [Session ID: 20260327T221426Z-main] [记录类型]: smoke test 通过, 转入真实 12k 训练

## 阶段

- [x] 阶段1: 回读项目上下文、`my4` 配置和训练入口
- [x] 阶段2: 验证 `my5` 数据结构与 `train/test` 索引语义
- [x] 阶段3: 生成 `my5` 训练配置和 Flux refine 配置
- [x] 阶段4: 执行 smoke test 并启动真实训练
- [ ] 阶段5: 记录运行入口、日志位置和后续建议

## 关键问题

1. smoke test 是否真的走通了训练主链:
   - 已验证事实:
     - 运行命令:
       - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my5/recon_my5_colmap_fastgs_stable_12k_dense.yaml --set max_steps=1 --set result_dir=outputs/my5_colmap_fastgs_stable_12k_dense_smoke`
     - 动态输出:
       - `Trainset Size: 283`
       - `Test Size: 41`
       - `Model initialized. Number of GS: 30359`
       - `Step: 0`
   - 已验证结论:
     - YAML 可加载
     - 外部 `my5` 数据路径可读
     - 当前训练入口可以真正跑起来
2. smoke test 有没有暴露新阻塞:
   - 已观察到的现象:
     - 有一条 `TORCH_CUDA_ARCH_LIST is not set` warning
   - 当前结论:
     - 这不是当前训练启动的阻塞错误
     - 本轮不扩大范围去改环境变量, 先把真实训练启动起来
3. 下一步怎么执行最稳:
   - 当前决定:
     - 用同一份 YAML 启动真实 12k 训练
     - 同时把 stdout/stderr 写进日志文件, 方便后续继续接管和排错

## 做出的决定

- 决定7: 保留 smoke test 结果作为动态证据, 不再重复做第二次相同短测。
- 决定8: 真实训练日志落到 `outputs/my5_colmap_fastgs_stable_12k_dense_run.log`。

## 状态

**目前在阶段5前半段** - smoke test 已通过, 现在启动真实 `12k` 训练并记录会话与日志入口。

## [2026-03-27 22:21:03] [Session ID: 20260327T221426Z-main] [记录类型]: `my5 stable_12k_dense` 训练完成并完成产物核对

## 阶段

- [x] 阶段1: 回读项目上下文、`my4` 配置和训练入口
- [x] 阶段2: 验证 `my5` 数据结构与 `train/test` 索引语义
- [x] 阶段3: 生成 `my5` 训练配置和 Flux refine 配置
- [x] 阶段4: 执行 smoke test 并启动真实训练
- [x] 阶段5: 记录运行入口、日志位置和后续建议

## 关键问题

1. 真实 12k 训练是否正常完成:
   - 已验证事实:
     - 训练会话已返回 `exit code 0`
     - 日志关键字扫描:
       - `rg -n "Traceback|RuntimeError|Error:" outputs/my5_colmap_fastgs_stable_12k_dense_run.log`
       - 返回空结果, `rg` 退出码为 `1`
   - 已验证结论:
     - 本轮训练正常结束
     - 没有扫到显式异常关键字
2. 关键 checkpoint 和 stats 是否完整落盘:
   - 已验证事实:
     - `ckpt_8999.pt`
     - `ckpt_9999.pt`
     - `ckpt_10999.pt`
     - `ckpt_11999.pt`
     - `train_step8999.json`
     - `train_step9999.json`
     - `train_step10999.json`
     - `train_step11999.json`
   - 已验证结论:
     - 这次训练的关键存档点完整存在
     - Flux 配置继续使用 `load_step: 11999` 是正确的
3. 当前最终状态是什么:
   - 已验证事实:
     - 日志尾部最终记录:
       - `Step: 11999 {'mem': 0.8086118698120117, 'ellipse_time': 107.94528388977051, 'num_GS': 302199}`
   - 已验证结论:
     - 这轮 `my5 stable_12k_dense` 训练已经完整收口
     - 当前可以直接把 `ckpt_11999.pt` 作为后续 Flux refine 的入口

## 做出的决定

- 决定9: 本轮到“完成训练 + 产物核对”为止, 不在同一回合里继续自动启动 Flux refine。
- 决定10: 保留已生成的 `exp_cfg/my5/flux_shinkai_museum_v2.yaml`, 作为下一步 refine 的直接入口。

## 状态

**目前已完成** - `my5 stable_12k_dense` 已完成训练, 关键 checkpoint、stats 和日志都已核对。

## [2026-03-27 22:21:03] [Session ID: 20260327T221426Z-main] [记录类型]: 继续执行下一步, 为 my5 做评估并修正评估入口的短训兼容性

## 目标

- 对刚完成的 `my5 stable_12k_dense @ 11999` 做真实评估。
- 避免把“评估入口硬编码 29999 / refined checkpoint 必存在”这种旧假设误当成当前项目事实。
- 让 `ours.evaluation` 在 `load_step != 29999` 且 refined checkpoint 尚不存在的场景下也能直接使用。

## 阶段

- [x] 阶段1: 回读 `__colmap_my5` 上下文和当前产物状态
- [x] 阶段2: 核对 `ours.evaluation` 的当前 CLI 行为
- [ ] 阶段3: 修复评估入口并补回归测试
- [ ] 阶段4: 运行 my5 评估并核对结果文件
- [ ] 阶段5: 更新支线记录和后续计划

## 关键问题

1. 当前评估 CLI 为什么不能直接拿来跑 `my5`:
   - 已观察到的现象:
     - `ours/evaluation.py` 的 `__main__` 里写死了:
       - `eval(cfg, 29999, ...)`
       - `eval(cfg, cfg.exp_name, ...)`
   - 当前结论:
     - 这对当前 `my5` 是不对的
     - 因为基础 checkpoint 是 `11999`, refined checkpoint 目前还不存在
2. 这是不是“命令用错了”, 还是“入口本身就不兼容”:
   - 当前主假设:
     - 是入口本身不兼容短训和“只评估基础模型”的场景
   - 最强备选解释:
     - 也可能项目一直默认要求“先 refine 再 eval”, 只是 README 没写清楚
   - 当前验证计划:
     - 先修入口为:
       - 基础评估默认使用 `cfg.load_step`
       - refined checkpoint 不存在时自动跳过 refined eval
     - 再用 `my5` 真实跑一轮验证这个设计是否符合现有目录结构

## 做出的决定

- 决定11: 不做一次性临时脚本绕过, 直接修正 `ours.evaluation` 的默认行为。
- 决定12: 同时补一组最小 `unittest`, 锁住这次入口修复。

## 状态

**目前在阶段3** - 正在修改评估入口和测试, 随后立即跑 `my5` 的真实评估。

## [2026-03-27 22:31:22] [Session ID: 20260327T221426Z-main] [记录类型]: my5 基础模型评估完成, refined 评估因 checkpoint 缺失被正确跳过

## 阶段

- [x] 阶段1: 回读 `__colmap_my5` 上下文和当前产物状态
- [x] 阶段2: 核对 `ours.evaluation` 的当前 CLI 行为
- [x] 阶段3: 修复评估入口并补回归测试
- [x] 阶段4: 运行 my5 评估并核对结果文件
- [x] 阶段5: 更新支线记录和后续计划

## 关键问题

1. 评估入口修复是否真的生效:
   - 已验证事实:
     - `python3 -m py_compile ours/evaluation.py tests/test_evaluation_cli.py` 通过
     - `.pixi/envs/default/bin/python -m unittest tests.test_evaluation_cli` 通过, 共 `4` 项
     - 真实评估命令:
       - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml --eval_test`
     - 真实输出:
       - `Skip refined evaluation because checkpoint does not exist: outputs/my5_colmap_fastgs_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
   - 已验证结论:
     - 当前 CLI 已不再写死 `29999`
     - refined checkpoint 缺失时也不会误报失败
2. 这次 `my5` 基础模型评估结果是什么:
   - 已验证事实:
     - `11999_test.json`
       - `psnr = 26.647448051266554`
       - `ssim = 0.8796708249464268`
       - `lpips = 0.20539226346626516`
     - `11999_train.json`
       - `psnr = 26.728178482594846`
       - `ssim = 0.8815288269898917`
       - `lpips = 0.20358432587170347`
   - 已验证结论:
     - `my5 stable_12k_dense @ 11999` 的基础模型评估已经完成
3. 评估产物数量是否和当前索引范围对齐:
   - 已验证事实:
     - `11999_test/` 下有 `41` 张图
     - `11999_train/` 下有 `283` 张图
   - 已验证结论:
     - 和当前 `my5` 的 `test/train` 索引范围完全一致

## 做出的决定

- 决定13: 本轮交付口径限定为“基础模型评估已完成”。
- 决定14: refined 评估保留到后续 refine 完成后再继续。

## 状态

**目前已完成** - `my5` 的基础模型评估已完成, 结果和评估渲染都已落盘。

## [2026-03-27 14:34:34] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 补上 my5 训练过程中的周期视频自动导出

## 目标

- 让 `my5` 训练在指定 checkpoint 节奏上自动导出轨迹视频, 不再只能训练后手动补导。
- 修复 `render_traj()` 对 `valset[30:80]` 的硬编码, 让它兼容 `my5` 当前只有 `41` 张 test 图的真实场景。
- 把自动导出的视频文件名改成带 checkpoint 的稳定命名, 避免 `render.mp4` / `alpha.mp4` 被后续导出覆盖。

## 阶段

- [x] 阶段1: 回读 `__colmap_my5` 上下文与训练器视频导出路径
- [ ] 阶段2: 设计导出节奏配置、取样范围和命名规则
- [ ] 阶段3: 修改训练器与 `my5` 配置
- [ ] 阶段4: 补测试并做真实验证
- [ ] 阶段5: 更新支线记录与后续建议

## 关键问题

1. 当前为什么看起来“训练不自动出视频”:
   - 已观察到的现象:
     - `recon/trainer.py` 里训练循环末尾的 eval / 轨迹导出逻辑被整段注释掉了
     - 当前只会保存 checkpoint, 不会在训练过程中自动调用 `render_traj()`
   - 已验证结论:
     - 现在的默认行为确实是不自动导视频
2. 能不能只把注释解开:
   - 已观察到的现象:
     - `render_traj()` 里写死了 `for i in range(30, 80): data = self.valset[i]`
     - 当前 `my5` 的 `valset` 长度只有 `41`
   - 当前主假设:
     - 如果直接恢复自动调用, `my5` 会在视频导出阶段触发越界
   - 最强备选解释:
     - 旧逻辑也许只服务某个固定数据子区间, 并不是通用轨迹导出实现
   - 当前验证计划:
     - 先把样本范围改成按 `valset` 真实长度和可配置边界裁切
     - 再把自动导出接回训练节奏
3. 这次最稳的节奏和命名应该是什么:
   - 当前决定:
     - 导出节奏采用显式配置 `render_video_steps`
     - `my5` 默认先对齐 `save_steps`
     - 产物至少保留:
       - `render_ckpt_<step>.mp4`
       - `alpha_ckpt_<step>.mp4`

## 做出的决定

- 决定15: 这次不做“手工跑完训练后再导一次”的一次性补救, 直接把自动导出能力补回训练主流程。
- 决定16: 默认行为保持显式开启, 避免给别的训练线无意增加额外耗时。
- 决定17: `render_traj()` 先修成泛化版本, 再接自动触发, 不做冒险式顺序颠倒。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段2** - 已确认不是“命令没写”而是“自动导出链路当前被关掉了”, 现在开始设计配置字段和稳定输出命名。

## [2026-03-27 14:43:43] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: my5 周期视频自动导出已接回训练流程, 现有 4 档 checkpoint 视频已补齐

## 阶段

- [x] 阶段1: 回读 `__colmap_my5` 上下文与训练器视频导出路径
- [x] 阶段2: 设计导出节奏配置、取样范围和命名规则
- [x] 阶段3: 修改训练器与 `my5` 配置
- [x] 阶段4: 补测试并做真实验证
- [x] 阶段5: 更新支线记录与后续建议

## 关键问题

1. 自动导出链路现在是否真的恢复了:
   - 已验证事实:
     - 静态检查:
       - `.pixi/envs/default/bin/python -m py_compile recon/trainer.py tests/test_trainer_video_export.py tests/test_trainer_eval_path.py tests/test_evaluation_cli.py`
     - 单测:
       - `.pixi/envs/default/bin/python -m unittest tests.test_trainer_video_export tests.test_trainer_eval_path tests.test_evaluation_cli`
       - 共 `11` 项, 全部通过
     - 真实短测:
       - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my5/recon_my5_colmap_fastgs_stable_12k_dense.yaml --set max_steps=1 --set save_steps=[1] --set render_video_steps=[1] --set render_video_start_idx=0 --set render_video_end_idx=2 --set result_dir=outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke_r2`
     - 短测真实输出:
       - `Published checkpoint videos to .../render_ckpt_0.mp4 and .../alpha_ckpt_0.mp4`
   - 已验证结论:
     - 训练过程中的自动视频导出已经恢复
2. 中间有没有暴露新的真实 bug:
   - 已观察到的现象:
     - 第一轮短测里, 我给 `render_traj()` 加的 `@torch.no_grad()` 导致:
       - `RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn`
   - 已验证结论:
     - 这不是数据问题
     - 是 `rasterize_splats_w_certainty()` 需要反向传播来生成 certainty 掩码, 不能被 `no_grad` 包住
   - 最终修复:
     - 移除 `render_traj()` 上的 `@torch.no_grad()`
     - 复跑短测后通过
3. 当前已经补齐了哪些真实视频产物:
   - 已验证事实:
     - 真实补导命令已跑完:
       - `8999`
       - `9999`
       - `10999`
       - `11999`
     - 当前目录:
       - `outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_8999.mp4`
       - `outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_9999.mp4`
       - `outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_10999.mp4`
       - `outputs/my5_colmap_fastgs_stable_12k_dense/to_refine/render_ckpt_11999.mp4`
       - 以及对应 `alpha_ckpt_*.mp4`
     - `ffprobe`:
       - `render_ckpt_11999.mp4`: `h264`, `1280x720`, `12 fps`, `41` 帧
       - `alpha_ckpt_11999.mp4`: `h264`, `1280x720`, `12 fps`, `41` 帧
   - 已验证结论:
     - 这次不只是“以后训练会自动出”
     - 当前这套已经完成的 `my5` 训练, 也已经把 4 档节奏视频补齐了

## 做出的决定

- 决定18: 自动导出默认保持显式配置开启, 本轮只在 `my5` YAML 上打开。
- 决定19: 训练内自动导出与手动 checkpoint 补导统一走 `render_traj()` 的新命名逻辑。
- 决定20: `to_refine/render.mp4` / `alpha.mp4` 继续保留为最新别名, 同时额外保存带 checkpoint 名的副本。

## 遇到错误

- 错误1:
  - `render_traj()` 上误加 `@torch.no_grad()`, 导致 certainty 渲染路径失效
  - 已修复并复验通过

## 状态

**目前已完成** - `my5` 的周期视频自动导出已经接回训练流程, 当前已有 checkpoint 也全部补齐了节奏视频。

## [2026-03-27 14:54:56] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 继续执行 my5 refine

## 目标

- 基于 `outputs/my5_colmap_fastgs_stable_12k_dense/ckpts/ckpt_11999.pt` 启动 `flux_shinkai_museum_v2` refine。
- 确认 refine 输入链路没有被这轮视频导出改动破坏。
- refine 完成后核对 refined checkpoint 和关键输出目录。

## 阶段

- [x] 阶段1: 回读 `__colmap_my5` 支线上下文与 refine 配置
- [ ] 阶段2: 核对 refine 入口依赖的输入路径
- [ ] 阶段3: 启动真实 refine
- [ ] 阶段4: 核对 refine 产物
- [ ] 阶段5: 更新记录与后续建议

## 关键问题

1. 现在能不能直接启动 refine:
   - 已验证事实:
     - refine 配置已存在:
       - `exp_cfg/my5/flux_shinkai_museum_v2.yaml`
     - 基础 checkpoint 已存在:
       - `outputs/my5_colmap_fastgs_stable_12k_dense/ckpts/ckpt_11999.pt`
   - 当前结论:
     - refine 的静态前提已满足
2. 这轮视频导出改动会不会反过来破坏 refine:
   - 当前主假设:
     - refine 主要依赖 checkpoint 与数据集索引, 不直接依赖 `to_refine/render.mp4`
   - 最强备选解释:
     - 也可能下游仍偷偷读取 `to_refine/` 根目录中的某些 sidecar 文件
   - 当前验证计划:
     - 先读 `ours/refine_by_flux.py` 和 `recon/refiner.py`
     - 确认真实输入依赖后再启动长任务

## 做出的决定

- 决定21: 这轮先验证 refine 输入链路, 再启动真实 refine, 不盲跑。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段2** - 正在核对 `refine_by_flux` 与 `recon.refiner` 的真实输入依赖, 确认可以直接开跑。

## [2026-03-27 14:54:56] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: my5 Flux refine 已完成, 转入 refined 评估

## 阶段

- [x] 阶段1: 回读 `__colmap_my5` 支线上下文与 refine 配置
- [x] 阶段2: 核对 refine 入口依赖的输入路径
- [x] 阶段3: 启动真实 refine
- [x] 阶段4: 核对 refine 产物
- [ ] 阶段5: 运行 refined 评估并更新记录

## 关键问题

1. refine 是否正常完成:
   - 已验证事实:
     - refine 进程已 `exit code 0`
     - `rg -n "Traceback|RuntimeError|Error:" outputs/my5_colmap_fastgs_stable_12k_dense/flux_shinkai_museum_v2_refine_run.log`
     - 无命中, `rg` 退出码 `1`
     - 关键 checkpoint 已存在:
       - `outputs/my5_colmap_fastgs_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
   - 已验证结论:
     - 这轮 refine 已经正常收口
2. refine 的主产物是否完整:
   - 已验证事实:
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
   - 已验证结论:
     - refine 前后对照和中间生成产物都已经完整落盘
3. 下一步最合理的动作是什么:
   - 当前决定:
     - 直接执行 refined 评估
     - 这样 `my5` 这条线可以在同一轮里拿到 refine 后的真实指标

## 做出的决定

- 决定22: refine 完成后不止停在 checkpoint 已生成, 直接顺手跑 refined 评估。

## 状态

**目前在阶段5** - refine 已完成且产物已核对, 现在开始跑 refined 评估。

## [2026-03-27 15:07:17] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: my5 refine 与 refined 评估全部完成

## 阶段

- [x] 阶段1: 回读 `__colmap_my5` 支线上下文与 refine 配置
- [x] 阶段2: 核对 refine 入口依赖的输入路径
- [x] 阶段3: 启动真实 refine
- [x] 阶段4: 核对 refine 产物
- [x] 阶段5: 运行 refined 评估并更新记录

## 关键问题

1. refined 评估是否正常完成:
   - 已验证事实:
     - 评估进程 `exit code 0`
     - 结果文件已生成:
       - `flux_shinkai_museum_v2_test.json`
       - `flux_shinkai_museum_v2_train.json`
   - 已验证结论:
     - refined 模型评估已完成
2. refine 后指标如何:
   - 已验证事实:
     - `test`:
       - `PSNR = 26.753718445940716`
       - `SSIM = 0.8817750462671605`
       - `LPIPS = 0.22343256960554822`
     - `train`:
       - `PSNR = 26.80816613995987`
       - `SSIM = 0.8829991606857246`
       - `LPIPS = 0.2217243981445636`
     - 相比 refine 前基础模型:
       - `test PSNR` 小幅上升约 `+0.1063`
       - `test SSIM` 小幅上升约 `+0.0021`
       - `test LPIPS` 变高约 `+0.0180`
   - 当前结论:
     - 这轮 refine 在像素指标上略有提升
     - 但感知指标 `LPIPS` 变差, 后续如果要继续优化, 需要重点盯这条权衡
3. refine 产物数量是否和 `my5` 当前切分一致:
   - 已验证事实:
     - `after_refine/` 共 `41` 张
     - `eval/flux_shinkai_museum_v2_test/` 共 `41` 张
     - `eval/flux_shinkai_museum_v2_train/` 共 `283` 张
   - 已验证结论:
     - refine 与 refined 评估都和当前 `my5` 的 test/train 长度对齐

## 做出的决定

- 决定23: 这轮先以现有 Flux 参数收口, 不在同一回合里继续调 `strength / warp_ratio / refine_steps`。

## 状态

**目前已完成** - `my5` 的基础训练、周期视频、Flux refine 和 refined 评估都已完成。

## [2026-03-27 15:08:45] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 启动 my5 的 30k 对照线, 比较 12k 之后继续训练的收益

## 目标

- 新开一条 `my5` 的 `30k_dense` 对照训练线。
- 口径上尽量只改训练窗口, 保持 `stable_12k_dense` 的其它关键参数不变。
- 训练完成后对 `29999` 做基础评估、Flux refine 和 refined 评估, 再和当前 `12k` 结果对照。

## 阶段

- [x] 阶段1: 回读 `my4` 长训参考线与当前 `my5` 基线
- [ ] 阶段2: 生成 `my5 30k_dense` 配置与 refine 配置
- [ ] 阶段3: 执行 smoke test 并启动真实 30k 训练
- [ ] 阶段4: 运行 `29999` 基础评估、Flux refine 与 refined 评估
- [ ] 阶段5: 汇总 `12k vs 30k(+refine)` 对照结论

## 关键问题

1. 30k 这条线到底该参考 `my4` 的哪种配置:
   - 已观察到的现象:
     - `exp_cfg/my4/recon_my4.yaml` 是 `30k`, 但同时:
       - `pose_opt: false`
       - `depth_loss: false`
       - `test_every: 1`
     - 当前 `my5 stable_12k_dense` 用的是:
       - `pose_opt: true`
       - `depth_loss: true`
       - `test_every: 8`
   - 当前结论:
     - 如果直接平移 `recon_my4.yaml`, 一次会改太多变量
2. 这轮最稳的对照口径是什么:
   - 当前主假设:
     - 为了只看“12k 之后继续训练有没有收益”, 最稳的是:
       - 保持 `my5 stable_12k_dense` 其它参数不变
       - 只把 `max_steps` 拉到 `30000`
       - 同时保留 `11999` 与 `29999` 两个关键保存点
   - 最强备选解释:
     - 也可以把 `refine_stop_iter` 一起拉长到 `15000`, 但那会把“训练更久”和“densify 更久”混在一起
   - 当前决定:
     - 本轮先只改训练窗口, 不同步改 densify 窗口

## 做出的决定

- 决定24: `my5 30k_dense` 先做“只延长训练窗口”的单变量对照。
- 决定25: 关键 checkpoint 至少保留 `11999` 与 `29999`, 便于直接对比 `12k` 和 `30k`。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段2** - 正在生成 `my5 30k_dense` 训练配置和对应的 Flux refine 配置。

## [2026-03-27 15:11:59] [Session ID: 20260327T151159Z-main] [记录类型]: 接手 30k 对照线, 先做 smoke test 再启动真实长训

## 阶段

- [x] 阶段1: 回读 `my4` 长训参考线与当前 `my5` 基线
- [x] 阶段2: 生成 `my5 30k_dense` 配置与 refine 配置
- [ ] 阶段3: 执行 smoke test 并启动真实 30k 训练
- [ ] 阶段4: 运行 `29999` 基础评估、Flux refine 与 refined 评估
- [ ] 阶段5: 汇总 `12k vs 30k(+refine)` 对照结论

## 关键问题

1. 当前 30k 配置是否符合单变量对照口径:
   - 已验证事实:
     - `recon_my5_colmap_fastgs_stable_30k_dense.yaml` 仅把:
       - `result_dir`
       - `max_steps`
       - `eval_steps`
       - `save_steps`
       - `render_video_steps`
       调整到 30k 对照线
     - `refine_stop_iter` 仍保持 `9000`
     - `pose_opt` / `depth_loss` / `test_every` 都保持与 `12k stable_dense` 一致
   - 当前结论:
     - 这条线符合“只看 12k 之后继续训练有没有收益”的对照目标
2. 现在最需要先确认什么:
   - 当前主假设:
     - 新 YAML 能直接被训练入口吃下
   - 最强备选解释:
     - 也可能在真实启动时才暴露出路径、日志目录或视频导出参数的小问题
   - 当前验证计划:
     - 先运行一次 `max_steps=1` 的最小 smoke test
     - 如果通过, 立刻切到真实 `30k` 长训

## 做出的决定

- 决定26: 延续 `__colmap_my5` 这套支线上下文, 不回切默认六文件。
- 决定27: 先用 override 做最小 smoke test, 不再额外生成新的 smoke YAML。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段3前半段** - 已确认 30k 配置口径正确, 现在开始执行 smoke test。

## [2026-03-27 15:11:59] [Session ID: 20260327T151159Z-main] [记录类型]: 30k smoke test 通过, 切换到真实长训

## 阶段

- [x] 阶段1: 回读 `my4` 长训参考线与当前 `my5` 基线
- [x] 阶段2: 生成 `my5 30k_dense` 配置与 refine 配置
- [x] 阶段3: 执行 smoke test 并启动真实 30k 训练
- [ ] 阶段4: 运行 `29999` 基础评估、Flux refine 与 refined 评估
- [ ] 阶段5: 汇总 `12k vs 30k(+refine)` 对照结论

## 关键问题

1. smoke test 是否真的走通训练主链和视频导出:
   - 已验证事实:
     - 运行命令:
       - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my5/recon_my5_colmap_fastgs_stable_30k_dense.yaml --set max_steps=1 --set save_steps=[1] --set render_video_steps=[1] --set render_video_start_idx=0 --set render_video_end_idx=2 --set result_dir=outputs/my5_colmap_fastgs_stable_30k_dense_smoke`
     - 动态输出:
       - `Trainset Size: 283`
       - `Test Size: 41`
       - `Model initialized. Number of GS: 30359`
       - `Rendering trajectory for 2 validation views`
       - `Published checkpoint videos to outputs/my5_colmap_fastgs_stable_30k_dense_smoke/to_refine/render_ckpt_0.mp4`
   - 已验证结论:
     - 新 30k YAML 可直接被训练入口加载
     - 数据路径和节奏视频导出在 30k 线下都正常
2. 现在最合理的下一步是什么:
   - 当前决定:
     - 立刻启动真实 `30k` 长训
     - 日志统一写到 `outputs/my5_colmap_fastgs_stable_30k_dense_run.log`

## 做出的决定

- 决定28: 不重复做第二次同类短测, 直接进入长训。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段3后半段** - smoke test 已通过, 现在启动真实 `30k` 训练并持续轮询日志。

## [2026-03-27 15:19:41] [Session ID: 20260327T151941Z-main] [记录类型]: `my5 30k_dense` 训练完成, 转入基础评估

## 阶段

- [x] 阶段1: 回读 `my4` 长训参考线与当前 `my5` 基线
- [x] 阶段2: 生成 `my5 30k_dense` 配置与 refine 配置
- [x] 阶段3: 执行 smoke test 并启动真实 30k 训练
- [ ] 阶段4: 运行 `29999` 基础评估、Flux refine 与 refined 评估
- [ ] 阶段5: 汇总 `12k vs 30k(+refine)` 对照结论

## 关键问题

1. 真实 30k 训练是否正常收口:
   - 已验证事实:
     - 训练进程 `exit code 0`
     - `rg -n "Traceback|RuntimeError|Error:" outputs/my5_colmap_fastgs_stable_30k_dense_run.log`
       返回空结果, `rg` 退出码为 `1`
     - 日志关键点:
       - `Step:  11999 {'mem': 0.8295893669128418, 'ellipse_time': 133.72730588912964, 'num_GS': 320998}`
       - `Step:  29999 {'mem': 0.8295893669128418, 'ellipse_time': 366.7633469104767, 'num_GS': 320998}`
   - 已验证结论:
     - 这轮 `30k` 训练已正常结束
2. 关键中间产物和最终产物是否完整:
   - 已验证事实:
     - checkpoint:
       - `ckpt_11999.pt`
       - `ckpt_29999.pt`
     - stats:
       - `train_step11999.json`
       - `train_step29999.json`
     - 周期视频:
       - `render_ckpt_11999.mp4`
       - `alpha_ckpt_11999.mp4`
       - `render_ckpt_29999.mp4`
       - `alpha_ckpt_29999.mp4`
     - `ffprobe render_ckpt_29999.mp4`:
       - `h264`
       - `1280x720`
       - `12 fps`
       - `41` 帧
   - 已验证结论:
     - 当前已经具备做 `29999` 基础评估和后续 refine 的全部前提

## 做出的决定

- 决定29: 不额外插入 `11999` 的 30k 线中途评估, 先完成用户明确要求的 `29999 + refine + 评估` 主链。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段4前半段** - `my5 30k_dense` 训练已完成, 现在开始跑 `29999` 的基础评估。

## [2026-03-27 15:19:41] [Session ID: 20260327T151941Z-main] [记录类型]: `29999` 基础评估完成, 转入 30k refine

## 阶段

- [x] 阶段1: 回读 `my4` 长训参考线与当前 `my5` 基线
- [x] 阶段2: 生成 `my5 30k_dense` 配置与 refine 配置
- [x] 阶段3: 执行 smoke test 并启动真实 30k 训练
- [ ] 阶段4: 运行 `29999` 基础评估、Flux refine 与 refined 评估
- [ ] 阶段5: 汇总 `12k vs 30k(+refine)` 对照结论

## 关键问题

1. `29999` 的基础评估是否正常完成:
   - 已验证事实:
     - 评估进程 `exit code 0`
     - refined checkpoint 不存在时输出:
       - `Skip refined evaluation because checkpoint does not exist: outputs/my5_colmap_fastgs_stable_30k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
     - 结果文件已生成:
       - `29999_test.json`
       - `29999_train.json`
   - 已验证结论:
     - 当前基础评估已经完成
     - refined 跳过行为仍与之前修复后的设计一致
2. `30k` 基础指标相对 `12k` 是否有收益:
   - 已验证事实:
     - `29999_test`:
       - `PSNR = 26.99565171032417`
       - `SSIM = 0.883747217131824`
       - `LPIPS = 0.18820923239719578`
     - `29999_train`:
       - `PSNR = 27.08867610216983`
       - `SSIM = 0.8859333686609572`
       - `LPIPS = 0.18689768224322753`
     - 相比 `12k` 基础模型 `11999_test`:
       - `PSNR` 上升约 `+0.3482`
       - `SSIM` 上升约 `+0.0041`
       - `LPIPS` 降低约 `-0.0172`
   - 当前结论:
     - 仅从基础模型看, `12k` 之后继续训练是有正收益的

## 做出的决定

- 决定30: 继续保持同一组 Flux 参数, 先完成 `30k` refine 的一阶对照, 不中途改 prompt 或 `strength`。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段4中段** - `29999` 基础评估已完成, 现在开始执行 `30k` 的 Flux refine。

## [2026-03-27 15:19:41] [Session ID: 20260327T151941Z-main] [记录类型]: `30k` refine 完成, 转入 refined 评估

## 阶段

- [x] 阶段1: 回读 `my4` 长训参考线与当前 `my5` 基线
- [x] 阶段2: 生成 `my5 30k_dense` 配置与 refine 配置
- [x] 阶段3: 执行 smoke test 并启动真实 30k 训练
- [ ] 阶段4: 运行 `29999` 基础评估、Flux refine 与 refined 评估
- [ ] 阶段5: 汇总 `12k vs 30k(+refine)` 对照结论

## 关键问题

1. `30k refine` 是否真的正常收口:
   - 已验证事实:
     - refine 进程 `exit code 0`
     - `rg -n "Traceback|RuntimeError|Error:" outputs/my5_colmap_fastgs_stable_30k_dense/flux_shinkai_museum_v2_refine_run.log`
       返回空结果, `rg` 退出码为 `1`
     - refined checkpoint 已存在:
       - `ckpt_flux_shinkai_museum_v2.pt`
   - 已验证结论:
     - refine 主流程已经完成
2. refine 前后产物是否完整:
   - 已验证事实:
     - `before_refine/` 共 `41` 张
     - `refine/gen/` 共 `41` 张
     - `after_refine/` 共 `41` 张
     - `before_refine.mp4`:
       - `h264`
       - `1280x720`
       - `12 fps`
       - `41` 帧
     - `after_refine.mp4`:
       - `h264`
       - `1280x720`
       - `12 fps`
       - `41` 帧
   - 已验证结论:
     - 当前已具备执行 refined 评估的全部前提

## 做出的决定

- 决定31: refine 收口后立刻继续 refined 评估, 不把最后一组指标留到后续再补。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段4后半段** - `30k` refine 已完成且产物已核对, 现在开始跑 refined 评估。

## [2026-03-27 15:36:37] [Session ID: 20260327T153637Z-main] [记录类型]: `my5 30k + refine + 评估` 全部完成, 给出 12k 对照结论

## 阶段

- [x] 阶段1: 回读 `my4` 长训参考线与当前 `my5` 基线
- [x] 阶段2: 生成 `my5 30k_dense` 配置与 refine 配置
- [x] 阶段3: 执行 smoke test 并启动真实 30k 训练
- [x] 阶段4: 运行 `29999` 基础评估、Flux refine 与 refined 评估
- [x] 阶段5: 汇总 `12k vs 30k(+refine)` 对照结论

## 关键问题

1. `30k refined` 评估是否正常完成:
   - 已验证事实:
     - 评估进程 `exit code 0`
     - 结果文件已生成:
       - `flux_shinkai_museum_v2_test.json`
       - `flux_shinkai_museum_v2_train.json`
     - 样本数量:
       - refined `test` 共 `41` 张
       - refined `train` 共 `283` 张
   - 已验证结论:
     - `30k` refined 评估已完成
2. `12k` 之后继续训练有没有收益:
   - 已验证事实:
     - `12k base test`:
       - `PSNR = 26.647448051266554`
       - `SSIM = 0.8796708249464268`
       - `LPIPS = 0.20539226346626516`
     - `30k base test`:
       - `PSNR = 26.99565171032417`
       - `SSIM = 0.883747217131824`
       - `LPIPS = 0.18820923239719578`
     - base 对照增量:
       - `PSNR +0.3482036590576172`
       - `SSIM +0.004076392185397237`
       - `LPIPS -0.017183031069069377`
   - 已验证结论:
     - 对当前 `my5 stable_dense` 这条线来说, `12k` 之后继续训练到 `30k` 是有明确正收益的
3. 同一套 Flux refine 参数在 `30k` 上表现如何:
   - 已验证事实:
     - `30k refine test`:
       - `PSNR = 26.76950226760492`
       - `SSIM = 0.8836645963715344`
       - `LPIPS = 0.22542380341669407`
     - `30k refine vs 30k base`:
       - `PSNR -0.22614944271925097`
       - `SSIM -0.00008262076028964227`
       - `LPIPS +0.037214571019498294`
     - `12k refine vs 12k base`:
       - `PSNR +0.1062703946741621`
       - `SSIM +0.0021042213207337346`
       - `LPIPS +0.018040306139283063`
   - 已验证结论:
     - 这组 Flux 参数对 `30k` 基础模型是过度 refine
     - 它不但没有延续 `30k base` 的优势, 反而把 `PSNR` 和 `LPIPS` 都拉差了

## 做出的决定

- 决定32: 本轮按用户要求到“30k + refine + 评估 + 对照结论”为止收口, 不继续现场改 refine 参数。

## 遇到错误

- 暂无新错误。

## 状态

**目前已完成** - `my5` 的 `30k` 训练、基础评估、Flux refine、refined 评估和 `12k` 对照结论都已完成。

## [2026-03-27 17:38:13] [Session ID: 20260327T173813Z-main] [记录类型]: 复核“30k refine 看起来更好但指标更差”是否属于评测基准问题

## 目标

- 判断当前 `30k refine -> 30k base` 的差异, 是不是评测基准错误导致的。
- 分清楚:
  - 主观观感为什么可能更好
  - 指标为什么却更差
  - 评估代码到底是不是拿对了 GT

## 阶段

- [ ] 阶段1: 回读上下文并核查评估口径代码
- [ ] 阶段2: 验证 GT 来源、指标定义和输出配对关系
- [ ] 阶段3: 给出“基准是否有问题”的结论与下一步建议

## 关键问题

1. 当前用户质疑的核心不是“refine 有没有变化”, 而是:
   - 这些数值是不是在错误的基准上算出来的
2. 当前主假设:
   - 评估基准本身大概率没错
   - 但主观“更顺眼”与 `PSNR / SSIM / LPIPS` 更优, 本来就不是同一件事
3. 最强备选解释:
   - 也可能存在:
     - GT 取错 split
     - 图像配对错位
     - 指标方向理解错
     - 评估前后预处理不一致
4. 当前验证计划:
   - 直接读 `ours/evaluation.py` 和底层 metric / dataset 路径
   - 核对评估输出目录与 GT 数量是否一一对应
   - 如有必要, 抽样看一组 refine / GT / base 的实际文件对应关系

## 做出的决定

- 决定33: 先做证据型复核, 不直接把“参数过强”继续当作最终口径。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段1** - 正在回读评估实现与数据配对逻辑, 先确认 benchmark 到底算的是什么。

## [2026-03-27 17:38:13] [Session ID: 20260327T173813Z-main] [记录类型]: benchmark 复核完成, 当前没有发现 GT 或配对基准错误

## 阶段

- [x] 阶段1: 回读上下文并核查评估口径代码
- [x] 阶段2: 验证 GT 来源、指标定义和输出配对关系
- [x] 阶段3: 给出“基准是否有问题”的结论与下一步建议

## 关键问题

1. 当前 benchmark 是否拿错了 GT:
   - 已验证事实:
     - `ours/evaluation.py` 通过 `refiner.render(..., eval=True)` 取指标
     - `recon/refiner.py` 直接把渲染结果和 `data["image"] / 255.0` 对比
     - `recon/datasets/colmap.py` 里 `data["image"]` 直接来自 `parser.image_paths[index]`
   - 已验证结论:
     - 当前指标比较对象就是 COLMAP 场景里的真实 test/train 图片
2. 当前 test 配对或相机口径是否有隐藏偏移:
   - 已验证事实:
     - `Dataset(split='test')` 与 `Refiner.test_dataset` 返回的是同一批 test 图片
     - `30k` 配置里:
       - `test_trans: [0, 0, 0]`
       - `test_rots: [0, 0, 0]`
     - `refiner.render(..., eval=True)` 的单帧 `eval_results` 与手工重算完全一致
   - 已验证结论:
     - 当前没有发现 split 错位、GT 错位、指标方向错误或额外相机偏移
3. 为什么会出现“看起来更好但指标更差”:
   - 已验证事实:
     - 对导出的 `before_refine/after_refine` 逐帧复算后:
       - `PSNR` 变好的帧数只有 `13/41`
       - `SSIM` 变好的帧数只有 `17/41`
       - `LPIPS` 变好的帧数是 `0/41`
   - 已验证结论:
     - `30k refine` 不是完全没变好
     - 它确实让一部分帧更顺眼
     - 但平均上更偏离原始 GT, 尤其感知距离 `LPIPS` 全面变差

## 做出的决定

- 决定34: 当前口径修正为“benchmark 基准没错, 但主观审美目标与 fidelity 指标发生分叉”。

## 遇到错误

- 错误1:
  - 一开始误用系统 `python3` 做动态验证, 缺少项目依赖
  - 已切回 `.pixi/envs/default/bin/python` 复验通过

## 状态

**目前已完成** - benchmark 复核完成, 当前没有发现评测基准错误。

## [2026-03-27 17:51:55] [Session ID: 20260327T175155Z-main] [记录类型]: 新开 35k vs 35k(test_every=7) 对照线

## 目标

- 以当前 `30k stable_dense` 为骨架, 新建一条 `35k` 基线。
- 在不改变其它关键训练参数的前提下, 再新建一条 `test_every: 7` 的 `35k` 对照线。
- 先完成两条线的基础训练与基础评估对比, 回答 `test_every: 7` 对结果的影响。

## 阶段

- [ ] 阶段1: 核对 35k 口径与 `test_every: 7` 切分长度
- [ ] 阶段2: 生成 35k 基线与 te7 对照配置
- [ ] 阶段3: 做 smoke test 并启动真实训练
- [ ] 阶段4: 运行基础评估并做 35k 对比
- [ ] 阶段5: 更新记录并给出结论

## 关键问题

1. 当前仓库里有没有现成的 35k 配置可以直接复用:
   - 已验证事实:
     - `exp_cfg/my5/` 下只有:
       - `stable_12k_dense`
       - `stable_30k_dense`
     - 没有现成 `35k`
   - 当前结论:
     - 这轮需要先生成新的 35k 配置
2. 当前这轮“进行对比”最稳的默认口径是什么:
   - 当前主假设:
     - 先只比较基础训练与基础评估
     - 不把 refine 也一起卷进来, 避免一次引入第二个变量
   - 最强备选解释:
     - 也可以把 refine 一起跑完再比
   - 当前决定:
     - 先做 base 对照, 后续若需要再继续 refine
3. 35k 基线该怎么“保留”:
   - 当前结论:
     - 新建一条 `test_every: 8` 的 `35k` 基线
     - 再以它为母线改出 `test_every: 7`

## 做出的决定

- 决定35: 当前默认把“保留 35000 这套配置”解释为“新建并保留 35k 基线 + te7 对照”。
- 决定36: 本轮先不做 refine, 先把 `test_every` 这个单变量看清楚。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段1** - 正在计算 `test_every: 7` 下的真实 train/test 长度, 准备生成配置。

## [2026-03-27 17:51:55] [Session ID: 20260327T175155Z-main] [记录类型]: 35k 基线与 te7 对照配置已落盘, 转入 smoke test

## 阶段

- [x] 阶段1: 核对 35k 口径与 `test_every: 7` 切分长度
- [x] 阶段2: 生成 35k 基线与 te7 对照配置
- [ ] 阶段3: 做 smoke test 并启动真实训练
- [ ] 阶段4: 运行基础评估并做 35k 对比
- [ ] 阶段5: 更新记录并给出结论

## 关键问题

1. `test_every: 7` 下的真实切分长度是多少:
   - 已验证事实:
     - `train_len = 277`
     - `test_len = 47`
   - 已验证结论:
     - 对应 Flux 配置已对齐:
       - `refine_end_idx = 47`
       - `train_end_idx = 277`
2. 当前已经生成了哪些配置:
   - 已验证事实:
     - `recon_my5_colmap_fastgs_stable_35k_dense.yaml`
     - `flux_shinkai_museum_v2_35k.yaml`
     - `recon_my5_colmap_fastgs_stable_35k_dense_te7.yaml`
     - `flux_shinkai_museum_v2_35k_te7.yaml`
   - 当前结论:
     - 静态配置前提已经齐备

## 做出的决定

- 决定37: 两条 35k 线都先做 1 step smoke test, 再启动真实训练。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段3前半段** - 正在做 `35k` 基线和 `35k te7` 的最小 smoke test。

## [2026-03-27 17:51:55] [Session ID: 20260327T175155Z-main] [记录类型]: 并行 smoke test 暴露 `gsplat` JIT 锁竞争, 改为串行复验

## 关键问题

1. 当前 smoke test 是否都成功:
   - 已验证事实:
     - `35k te7` smoke test 已成功:
       - `Trainset Size: 277`
       - `Test Size: 47`
       - `Published checkpoint videos ... render_ckpt_0.mp4`
     - `35k` 基线 smoke test 失败
   - 当前结论:
     - `te7` 配置本身是通的
     - 基线失败不代表 YAML 有问题
2. 当前失败最可能是什么:
   - 已观察到的现象:
     - 基线短测报错:
       - `FileNotFoundError: ... torch_extensions/.../gsplat_cuda/lock`
   - 当前主假设:
     - 两条线并行启动时, `gsplat` 的 JIT 编译锁发生竞争
   - 最强备选解释:
     - 也可能是基线 YAML 自身有问题
   - 当前验证计划:
     - 单独串行重跑 `35k` 基线 smoke test
     - 若单跑通过, 就把原因收口为 JIT 锁竞争

## 做出的决定

- 决定38: 后续这轮不再并行起跑训练任务, 统一改为串行。

## 遇到错误

- 错误2:
  - 并行 smoke test 时触发 `gsplat_cuda` 的 `torch_extensions` 锁文件竞争
  - 当前正在通过串行重跑验证

## 状态

**目前仍在阶段3前半段** - `te7` 已通过, 现在单独重跑 `35k` 基线 smoke test。

## [2026-03-27 17:51:55] [Session ID: 20260327T175155Z-main] [记录类型]: 两条 35k 线 smoke test 全部通过, 转入真实训练

## 阶段

- [x] 阶段1: 核对 35k 口径与 `test_every: 7` 切分长度
- [x] 阶段2: 生成 35k 基线与 te7 对照配置
- [x] 阶段3: 做 smoke test 并启动真实训练
- [ ] 阶段4: 运行基础评估并做 35k 对比
- [ ] 阶段5: 更新记录并给出结论

## 关键问题

1. 基线串行复跑后是否通过:
   - 已验证事实:
     - `35k` 基线串行 smoke test 输出:
       - `Trainset Size: 283`
       - `Test Size: 41`
       - `Published checkpoint videos ... render_ckpt_0.mp4`
   - 已验证结论:
     - 基线 YAML 本身没有问题
2. 并行失败的真正原因是什么:
   - 已验证事实:
     - 并行跑时只有一条撞到:
       - `torch_extensions/.../gsplat_cuda/lock`
     - 串行重跑立即通过
   - 已验证结论:
     - 失败原因收口为 `gsplat` JIT 锁竞争

## 做出的决定

- 决定39: 真实训练按串行执行:
  - 先跑 `35k` 基线
  - 再跑 `35k te7`

## 遇到错误

- 错误2:
  - 并行 smoke test 时触发 `gsplat_cuda` 的 `torch_extensions` 锁文件竞争
  - 已通过串行复跑验证并绕开

## 状态

**目前在阶段3后半段** - smoke test 已全部通过, 现在启动真实 `35k` 基线训练。
