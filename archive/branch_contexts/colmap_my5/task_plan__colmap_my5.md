# 任务计划: 基于 my5_colmap_fastgs 做 35k 与 test_every=7 对比

## [2026-03-27 17:57:41] [Session ID: 20260327T175741Z-main] [记录类型]: 因 task_plan 超过 1000 行续档, 承接 35k 对照主线

## 目标

- 保留现有 `35k` 基线配置不变, 完整跑完 `test_every: 8` 这条母线。
- 新增一条只改 `test_every: 7` 的 `35k` 对照线, 并在同口径下完成基础评估。
- 用真实训练与评估结果回答: 这条 `my5` 数据在 `35000` 步下, `test_every` 从 `8` 改到 `7` 后, base 质量会怎么变化。

## 阶段

- [ ] 阶段1: 接管正在运行的 `35k` 基线训练并核对关键产物
- [ ] 阶段2: 运行 `35k` 基线基础评估
- [ ] 阶段3: 串行运行 `35k te7` 真实训练并核对关键产物
- [ ] 阶段4: 运行 `35k te7` 基础评估
- [ ] 阶段5: 汇总对比结果并更新支线记录

## 关键问题

1. 这次对比的变量是否足够单一:
   - 已验证事实:
     - `35k` 基线与 `35k te7` 都保持:
       - `max_steps: 35000`
       - `refine_stop_iter: 9000`
       - `render_video_steps: [12000, 30000, 35000]`
       - 相同的优化与 densify 参数
     - 当前唯一主动变化项是:
       - `test_every: 8 -> 7`
   - 当前结论:
     - 这轮 base 对照可以把主要差异收敛到数据切分规则上
2. 当前两条线的真实切分长度是什么:
   - 已验证事实:
     - `test_every: 8`:
       - `train = 283`
       - `test = 41`
     - `test_every: 7`:
       - `train = 277`
       - `test = 47`
   - 当前结论:
     - `flux_shinkai_museum_v2_35k*.yaml` 里的 `train/refine` 索引已经和真实长度对齐
3. 当前已知的运行风险是什么:
   - 已验证事实:
     - 并行 smoke test 曾触发:
       - `torch_extensions/.../gsplat_cuda/lock`
     - 串行复跑后, 两条线都通过
   - 已验证结论:
     - 后续真实训练必须保持串行, 不能并行起两条训练

## 做出的决定

- 决定1: 续档后只保留当前 `35k vs te7` 这条主线, 旧计划快照已移动到:
  - `archive/branch_contexts/colmap_my5/snapshots/2026-03-27_175741/task_plan__colmap_my5.md`
- 决定2: 本轮先只做 base 对照, 不把 refine 混进来, 免得多出第二个变量。
- 决定3: 训练顺序固定为:
  - 先完成 `35k` 基线
  - 再启动 `35k te7`

## 遇到错误

- 错误1:
  - 并行 smoke test 会触发 `gsplat` JIT 锁竞争
  - 当前处理方式是全程串行运行训练任务

## 状态

**目前在阶段1** - 已完成续档, 正在接管 `35k` 基线训练, 先确认它当前跑到哪里、有没有异常、关键 checkpoint 与视频是否按节奏落盘。

## [2026-03-27 17:57:41] [Session ID: 20260327T175741Z-main] [记录类型]: `35k` 基线训练已完成, 转入基础评估

## 阶段

- [x] 阶段1: 接管正在运行的 `35k` 基线训练并核对关键产物
- [ ] 阶段2: 运行 `35k` 基线基础评估
- [ ] 阶段3: 串行运行 `35k te7` 真实训练并核对关键产物
- [ ] 阶段4: 运行 `35k te7` 基础评估
- [ ] 阶段5: 汇总对比结果并更新支线记录

## 关键问题

1. `35k` 基线是否真的完整收口:
   - 已验证事实:
     - 训练进程退出 `code 0`
     - 日志命中:
       - `Step:  11999`
       - `Step:  29999`
       - `Step:  34999`
     - 未命中:
       - `Traceback`
       - `RuntimeError`
       - `Error:`
   - 已验证结论:
     - `35k` 基线训练正常结束
2. 关键产物是否完整:
   - 已验证事实:
     - checkpoints:
       - `ckpt_11999.pt`
       - `ckpt_29999.pt`
       - `ckpt_34999.pt`
     - stats:
       - `train_step11999.json`
       - `train_step29999.json`
       - `train_step34999.json`
     - 视频:
       - `render_ckpt_11999.mp4`
       - `render_ckpt_29999.mp4`
       - `render_ckpt_34999.mp4`
   - 已验证结论:
     - 基线训练的 3 个关键节点都已落盘

## 做出的决定

- 决定4: 基线训练证据已经足够, 现在直接进入 `34999` 的基础评估。

## 状态

**目前在阶段2** - `35k` 基线训练已验证完成, 正在执行 `flux_shinkai_museum_v2_35k.yaml` 的基础评估。

## [2026-03-27 17:57:41] [Session ID: 20260327T175741Z-main] [记录类型]: `35k` 基线基础评估完成, 转入 `35k te7` 真实训练

## 阶段

- [x] 阶段1: 接管正在运行的 `35k` 基线训练并核对关键产物
- [x] 阶段2: 运行 `35k` 基线基础评估
- [ ] 阶段3: 串行运行 `35k te7` 真实训练并核对关键产物
- [ ] 阶段4: 运行 `35k te7` 基础评估
- [ ] 阶段5: 汇总对比结果并更新支线记录

## 关键问题

1. `35k` 基线 base 指标目前是多少:
   - 已验证事实:
     - `34999_test.json`:
       - `PSNR = 27.02455199637064`
       - `SSIM = 0.8843123098699058`
       - `LPIPS = 0.18506437685431504`
     - `34999_train.json`:
       - `PSNR = 27.157236779957692`
       - `SSIM = 0.8868114263767067`
       - `LPIPS = 0.18364840411571226`
   - 已验证结论:
     - `35k` 基线 base 已经比此前 `30k base` 略有继续提升
2. 评估产物与切分是否对齐:
   - 已验证事实:
     - `34999_test/` 下有 `41` 张
     - `34999_train/` 下有 `283` 张
   - 已验证结论:
     - 当前 `35k` 基线评估口径是自洽的

## 做出的决定

- 决定5: 现在直接串行启动 `exp_cfg/my5/recon_my5_colmap_fastgs_stable_35k_dense_te7.yaml` 的真实训练。

## 状态

**目前在阶段3** - `35k` 基线 base 结果已拿到, 正在启动 `35k te7` 真实训练, 训练结束后再跑同口径基础评估。

## [2026-03-27 17:57:41] [Session ID: 20260327T175741Z-main] [记录类型]: `35k te7` 训练已完成, 转入基础评估

## 阶段

- [x] 阶段1: 接管正在运行的 `35k` 基线训练并核对关键产物
- [x] 阶段2: 运行 `35k` 基线基础评估
- [x] 阶段3: 串行运行 `35k te7` 真实训练并核对关键产物
- [ ] 阶段4: 运行 `35k te7` 基础评估
- [ ] 阶段5: 汇总对比结果并更新支线记录

## 关键问题

1. `35k te7` 是否同样完整收口:
   - 已验证事实:
     - 训练进程退出 `code 0`
     - 日志命中:
       - `Step:  11999`
       - `Step:  29999`
       - `Step:  34999`
     - 未命中:
       - `Traceback`
       - `RuntimeError`
       - `Error:`
   - 已验证结论:
     - `35k te7` 训练正常结束
2. 关键产物与视频是否完整:
   - 已验证事实:
     - checkpoints:
       - `ckpt_11999.pt`
       - `ckpt_29999.pt`
       - `ckpt_34999.pt`
     - stats:
       - `train_step11999.json`
       - `train_step29999.json`
       - `train_step34999.json`
     - 视频:
       - `render_ckpt_11999.mp4`
       - `render_ckpt_29999.mp4`
       - `render_ckpt_34999.mp4`
     - `render_ckpt_34999.mp4`:
       - `1280x720`
       - `12 fps`
       - `47` 帧
   - 已验证结论:
     - `te7` 这条线的训练产物也齐全

## 做出的决定

- 决定6: 现在直接跑 `flux_shinkai_museum_v2_35k_te7.yaml` 的基础评估。

## 状态

**目前在阶段4** - `35k te7` 训练已完成, 正在执行基础评估, 评估结束后就做两条 35k 线的最终对比。

## [2026-03-27 18:09:34] [Session ID: 20260327T175741Z-main] [记录类型]: `35k base` vs `35k te7` 对比完成, 本轮闭环

## 阶段

- [x] 阶段1: 接管正在运行的 `35k` 基线训练并核对关键产物
- [x] 阶段2: 运行 `35k` 基线基础评估
- [x] 阶段3: 串行运行 `35k te7` 真实训练并核对关键产物
- [x] 阶段4: 运行 `35k te7` 基础评估
- [x] 阶段5: 汇总对比结果并更新支线记录

## 关键问题

1. 如果只看各自默认 split, `35k te7` 比 `35k base` 怎么样:
   - 已验证事实:
     - `35k base`:
       - `test`: `PSNR 27.0246`, `SSIM 0.8843`, `LPIPS 0.1851`
       - `train`: `PSNR 27.1572`, `SSIM 0.8868`, `LPIPS 0.1836`
     - `35k te7`:
       - `test`: `PSNR 26.9623`, `SSIM 0.8833`, `LPIPS 0.1880`
       - `train`: `PSNR 27.1250`, `SSIM 0.8863`, `LPIPS 0.1867`
     - `te7 - base`:
       - `test`: `PSNR -0.0623`, `SSIM -0.0010`, `LPIPS +0.0029`
       - `train`: `PSNR -0.0323`, `SSIM -0.0005`, `LPIPS +0.0030`
   - 当前结论:
     - 在各自默认 split 下, `te7` 略差
2. 这是不是严格同一 benchmark:
   - 已验证事实:
     - `test_every: 8` 的 `test = 41`
     - `test_every: 7` 的 `test = 47`
     - 两条线的默认 `test` 集并不是同一批图
   - 已验证结论:
     - 只看默认 `test` JSON 还不够严谨
3. 在双方都没见过的共同 holdout 上, 结果是什么:
   - 已验证事实:
     - 共同 holdout 取交集索引:
       - `[0, 56, 112, 168, 224, 280]`
       - 共 `6` 张
     - `35k base` 共同 holdout:
       - `PSNR 28.6706`
       - `SSIM 0.9127`
       - `LPIPS 0.1492`
     - `35k te7` 共同 holdout:
       - `PSNR 28.5839`
       - `SSIM 0.9125`
       - `LPIPS 0.1534`
     - `te7 - base`:
       - `PSNR -0.0867`
       - `SSIM -0.00027`
       - `LPIPS +0.00421`
   - 已验证结论:
     - 即使拉到同一批双方都未见过的图上, `te7` 仍然略差

## 做出的决定

- 决定7: 本轮对比结论以两层口径同时给出:
  - 默认 split 结果
  - 共同 holdout 结果
- 决定8: 当前 `35000` 这套配置继续保留 `test_every: 8` 作为更优基线。

## 状态

**目前已完成** - `35k base` 与 `35k te7` 的训练、基础评估和共同 holdout 公平对比都已完成, 当前结论是保留 `test_every: 8` 更稳。

## [2026-03-27 18:39:37] [Session ID: 20260327T183937Z-main] [记录类型]: 继续基于 `35k base` 推进 `50k + 长 densify`, 保持 `app_opt=false`

## 目标

- 以当前 `35k base` 为母线, 新开一条 `50k + 长 densify` 的 base 训练线。
- 明确保持 `app_opt=false`, 避免破坏后续 checkpoint 迁移语义。
- 完成这条线的 smoke test、真实训练和基础评估, 再和现有 `35k base` 做同 benchmark 对比。

## 阶段

- [ ] 阶段1: 落盘 `50k + 长 densify` 的训练与评估配置
- [ ] 阶段2: 执行最小 smoke test
- [ ] 阶段3: 启动真实 `50k` 训练并核对关键产物
- [ ] 阶段4: 运行 `50k` 基础评估
- [ ] 阶段5: 对比 `35k base` 与 `50k long_densify base`

## 关键问题

1. 这轮要锁住哪些变量:
   - 已验证事实:
     - 用户已明确:
       - 先做 `50k + 长 densify`
       - 不做 `app_opt=true`
   - 当前结论:
     - 这轮除了:
       - `max_steps`
       - `refine_stop_iter`
       - 对应保存 / 评估 / 视频节奏
     - 其余关键项都应保持和 `35k base` 一致
2. 为什么当前优先怀疑 densify 窗口而不是 `app_opt`:
   - 已验证事实:
     - `35k base` 从 `11999` 到 `34999`:
       - `num_GS = 322660`
       - 一直没有变化
     - `30k -> 35k` 的收益已经变小:
       - `PSNR +0.0289`
       - `SSIM +0.00057`
       - `LPIPS -0.00314`
   - 当前结论:
     - 当前更像是“后半段只在磨已有 splats”
     - 先延长 densify 窗口比盲目只加步数更值得验证
3. 这轮的对比 benchmark 是否天然一致:
   - 已验证事实:
     - 这条新线继续保持:
       - `test_every: 8`
   - 当前结论:
     - 后续 `50k` 和现有 `35k base` 可以直接按同一默认 test benchmark 对比

## 做出的决定

- 决定9: 新训练线保持 `app_opt=false`, 不把 checkpoint 结构改掉。
- 决定10: 长 densify 先采用项目里更保守、也更有历史依据的口径:
  - `max_steps: 50000`
  - `refine_stop_iter: 30000`
- 决定11: 先做 1 step smoke test, 通过后再启动真实训练。

## 状态

**目前在阶段1** - 正在创建 `50k + 长 densify` 的训练 / 评估配置, 随后做 smoke test。

## [2026-03-27 18:39:37] [Session ID: 20260327T183937Z-main] [记录类型]: `50k + 长 densify` 配置已落盘, smoke test 通过, 转入真实训练

## 阶段

- [x] 阶段1: 落盘 `50k + 长 densify` 的训练与评估配置
- [x] 阶段2: 执行最小 smoke test
- [ ] 阶段3: 启动真实 `50k` 训练并核对关键产物
- [ ] 阶段4: 运行 `50k` 基础评估
- [ ] 阶段5: 对比 `35k base` 与 `50k long_densify base`

## 关键问题

1. 新配置是否已经齐备:
   - 已验证事实:
     - 已新建:
       - `exp_cfg/my5/recon_my5_colmap_fastgs_stable_50k_longdensify.yaml`
       - `exp_cfg/my5/flux_shinkai_museum_v2_50k_longdensify.yaml`
   - 已验证结论:
     - 静态配置已经完成
2. smoke test 是否走通:
   - 已验证事实:
     - `Trainset Size: 283`
     - `Test Size: 41`
     - `Step:  0`
     - `Published checkpoint videos ... render_ckpt_0.mp4`
   - 已验证结论:
     - 新配置训练入口可用
     - 视频导出链路可用

## 做出的决定

- 决定12: 直接启动真实 `50k` 训练, 日志落到:
  - `outputs/my5_colmap_fastgs_stable_50k_longdensify_run.log`

## 状态

**目前在阶段3** - `50k + 长 densify` 的 smoke test 已通过, 正在启动真实训练。

## [2026-03-27 18:39:37] [Session ID: 20260327T183937Z-main] [记录类型]: `50k + 长 densify` 训练完成, 转入基础评估

## 阶段

- [x] 阶段1: 落盘 `50k + 长 densify` 的训练与评估配置
- [x] 阶段2: 执行最小 smoke test
- [x] 阶段3: 启动真实 `50k` 训练并核对关键产物
- [ ] 阶段4: 运行 `50k` 基础评估
- [ ] 阶段5: 对比 `35k base` 与 `50k long_densify base`

## 关键问题

1. 真实 `50k` 训练是否正常收口:
   - 已验证事实:
     - 训练进程退出 `code 0`
     - 日志命中:
       - `Step:  11999`
       - `Step:  29999`
       - `Step:  34999`
       - `Step:  49999`
     - 未命中:
       - `Traceback`
       - `RuntimeError`
       - `Error:`
   - 已验证结论:
     - 这条长 densify 训练完整结束
2. 长 densify 是否真的发生了:
   - 已验证事实:
     - `train_step11999.json`:
       - `num_GS = 388446`
     - `train_step29999.json`:
       - `num_GS = 514867`
     - `train_step34999.json`:
       - `num_GS = 514867`
     - `train_step49999.json`:
       - `num_GS = 514867`
   - 已验证结论:
     - 这轮不是“只把步数拉长”
     - densify 确实把几何容量继续拉高了

## 做出的决定

- 决定13: 现在直接运行 `flux_shinkai_museum_v2_50k_longdensify.yaml` 的基础评估。

## 状态

**目前在阶段4** - `50k + 长 densify` 训练已完成, 正在执行基础评估。

## [2026-03-27 18:54:03] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: `50k` 基础评估已完成, 准备收口与 `35k base` 的对比结论

## 阶段

- [x] 阶段1: 落盘 `50k + 长 densify` 的训练与评估配置
- [x] 阶段2: 执行最小 smoke test
- [x] 阶段3: 启动真实 `50k` 训练并核对关键产物
- [x] 阶段4: 运行 `50k` 基础评估
- [ ] 阶段5: 对比 `35k base` 与 `50k long_densify base`

## 关键问题

1. `50k` 的基础评估结果是多少:
   - 已验证事实:
     - `49999_test.json`:
       - `PSNR = 27.0529984264839`
       - `SSIM = 0.8835913975064348`
       - `LPIPS = 0.18191619162879338`
     - `49999_train.json`:
       - `PSNR = 27.142906478773998`
       - `SSIM = 0.8864561190874753`
       - `LPIPS = 0.18085349435414527`
   - 已验证结论:
     - `50k + 长 densify` 已完成基础评估, 指标可用于和 `35k base` 直接比较
2. 为什么这轮可以直接横向对比 `35k base`:
   - 已验证事实:
     - 两条线都保持:
       - `test_every: 8`
       - 同一份 `my5` 数据
       - 同一默认 test benchmark
   - 已验证结论:
     - 当前差异可以主要归因到:
       - `max_steps: 35000 -> 50000`
       - `refine_stop_iter: 9000 -> 30000`

## 做出的决定

- 决定14: 继续把这轮结论写回:
  - `task_plan__colmap_my5.md`
  - `notes__colmap_my5.md`
  - `WORKLOG__colmap_my5.md`
  - `EPIPHANY_LOG__colmap_my5.md`

## 状态

**目前在阶段5** - `50k` 基础评估已完成, 正在汇总它相对 `35k base` 的实际收益与代价。

## [2026-03-27 18:55:57] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: `50k + 长 densify` 对比完成, 本轮闭环

## 阶段

- [x] 阶段1: 落盘 `50k + 长 densify` 的训练与评估配置
- [x] 阶段2: 执行最小 smoke test
- [x] 阶段3: 启动真实 `50k` 训练并核对关键产物
- [x] 阶段4: 运行 `50k` 基础评估
- [x] 阶段5: 对比 `35k base` 与 `50k long_densify base`

## 关键问题

1. `50k + 长 densify` 相对 `35k base` 的 test 增量是什么:
   - 已验证事实:
     - `PSNR +0.028446430113259424`
     - `SSIM -0.000720912363471049`
     - `LPIPS -0.0031481852255216547`
   - 已验证结论:
     - `50k` 在 test 上有小幅收益
     - 但收益已经明显进入边际区间
2. 这轮额外算力主要换来了什么:
   - 已验证事实:
     - `num_GS`:
       - `35k base = 322660`
       - `50k long_densify = 514867`
   - 已验证结论:
     - 这轮主要换来了更高的几何容量
     - 量化收益存在, 但不再是大幅跃迁

## 做出的决定

- 决定15: 当前保留 `50k + 长 densify` 这套配置和产物, 作为后续 base 精调参考线。
- 决定16: 下一轮若继续优化 base, 优先考虑:
  - 精细化 densify 窗口搜索
  - 数据 / COLMAP 清洗
  而不是重新打开 `app_opt=true`。

## 状态

**目前已完成全部阶段** - `50k + 长 densify` 的训练、评估和相对 `35k base` 的对比都已收口, 当前结论已经同步到支线上下文文件。

## [2026-03-27 19:08:27] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 接管外部 `my5_nomask_v1` checkpoint, 准备复制、转换并做 refine

## 阶段

- [ ] 阶段1: 确认外部 checkpoint 结构与项目内转换入口
- [ ] 阶段2: 复制 checkpoint 到本项目 `data/` 并完成转换
- [ ] 阶段3: 为转换后的 checkpoint 准备 refine 配置
- [ ] 阶段4: 运行 refine 并核对产物
- [ ] 阶段5: 如可行则完成 refine 后评估并更新记录

## 关键问题

1. 外部 `ckpt_35000.pth` 是否能被当前项目直接识别:
   - 当前假设:
     - 需要先经过专门转换, 才能接入现有 `ours.refine_by_flux` 流程
   - 当前缺口:
     - 还未确认项目内已有哪一个脚本负责这种转换
2. 这次 refine 应该挂到哪套数据与配置上:
   - 已知事实:
     - 用户指定来源 checkpoint:
       - `/home/rais/FastGS/output/my5_nomask_v1/checkpoints/ckpt_35000.pth`
     - 用户要求:
       - 先复制到 `data`
       - 再做转换
       - 然后做 refine
   - 当前缺口:
     - 还需确认转换产物最终应该落到:
       - 新的 `outputs/...`
       - 还是某个兼容 `refine_by_flux` 的中间目录

## 做出的决定

- 决定17: 先不急着复制和跑 refine, 先定位项目里的真实转换链路, 避免把 checkpoint 放错位置。

## 状态

**目前在阶段1** - 正在确认外部 checkpoint 的转换入口、落盘目录和 refine 接口要求。

## [2026-03-27 19:08:27] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 转换链路已确认, 转入复制与配置落盘

## 阶段

- [x] 阶段1: 确认外部 checkpoint 结构与项目内转换入口
- [ ] 阶段2: 复制 checkpoint 到本项目 `data/` 并完成转换
- [ ] 阶段3: 为转换后的 checkpoint 准备 refine 配置
- [ ] 阶段4: 运行 refine 并核对产物
- [ ] 阶段5: 如可行则完成 refine 后评估并更新记录

## 关键问题

1. 外部 checkpoint 是否真的兼容桥接脚本:
   - 已验证事实:
     - `/home/rais/FastGS/output/my5_nomask_v1/checkpoints/ckpt_35000.pth` 存在
     - `torch.load` 结果是:
       - `(model_args, iteration)`
       - `iteration = 35000`
       - 高斯数量 `49200`
   - 已验证结论:
     - 这份文件符合 `recon.import_fastgs` 预期的 FastGS checkpoint 结构
2. 这次 refine 应该挂到哪套 FreeFix 配置上:
   - 已验证事实:
     - FastGS `cfg_args` 指向的数据也是:
       - `/root/autodl-tmp/home/rais/FastGS/data/my5_colmap_fastgs`
     - 当前 FreeFix `35k` 主线的 `cfg.json` 是:
       - `app_opt=false`
       - `data_dir=/home/rais/FastGS/data/my5_colmap_fastgs`
   - 已验证结论:
     - 本轮最适合复用 `outputs/my5_colmap_fastgs_stable_35k_dense/cfg.json`
     - 但应新开独立 `exp_name`, 避免覆盖已有 refine / eval 目录

## 做出的决定

- 决定18: 源 `pth` 先复制到:
  - `data/fastgs_bridge/my5_nomask_v1/`
- 决定19: 转换后的 FreeFix bridge ckpt 也放在同一目录, 保留来源链路。
- 决定20: refine 配置基于 `35k` 的 Flux 配置新开独立文件, 不复用旧 `exp_name`。

## 状态

**目前在阶段2/3** - 正在复制外部 checkpoint, 并落盘专用 refine 配置。

## [2026-03-27 19:08:27] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 外部 checkpoint 已复制并完成 bridge 转换, 准备启动 refine

## 阶段

- [x] 阶段1: 确认外部 checkpoint 结构与项目内转换入口
- [x] 阶段2: 复制 checkpoint 到本项目 `data/` 并完成转换
- [x] 阶段3: 为转换后的 checkpoint 准备 refine 配置
- [ ] 阶段4: 运行 refine 并核对产物
- [ ] 阶段5: 如可行则完成 refine 后评估并更新记录

## 关键问题

1. 复制与转换是否都已成功:
   - 已验证事实:
     - 已复制到:
       - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000.pth`
     - 已转换到:
       - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
     - `recon.import_fastgs` 输出:
       - `step = 35000`
       - `normalize_enabled = True`
       - `gaussian_count = 49200`
   - 已验证结论:
     - bridge 阶段已走通
2. refine 将使用哪套入口:
   - 已验证事实:
     - 已新建专用配置:
       - `exp_cfg/my5/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.yaml`
     - refine 入口支持:
       - `--colmap-path`
       - `--ckpt-path`
   - 已验证结论:
     - 接下来可直接用 `ours/refine_by_flux.py` 启动真实 refine

## 做出的决定

- 决定21: refine 结果保留在 `35k` 主线目录下, 但使用新的 `exp_name`, 不覆盖已有结果。

## 状态

**目前在阶段4** - bridge ckpt 已准备好, 正在启动真实 refine。

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 外部 FastGS checkpoint 的 bridge refine 已完成, 本轮闭环

## 阶段

- [x] 阶段1: 确认外部 checkpoint 结构与项目内转换入口
- [x] 阶段2: 复制 checkpoint 到本项目 `data/` 并完成转换
- [x] 阶段3: 为转换后的 checkpoint 准备 refine 配置
- [x] 阶段4: 运行 refine 并核对产物
- [x] 阶段5: 汇总 refine 结果并记录后续评估缺口

## 关键问题

1. refine 是否真实收口:
   - 已验证事实:
     - refine 进程退出 `code 0`
     - 日志未命中:
       - `Traceback`
       - `RuntimeError`
       - `ModuleNotFoundError`
       - `KeyError`
     - 关键产物齐全:
       - `before_refine / after_refine / refine/gen / refine/render / refine/depth` 都各 `41` 张
       - `before_refine.mp4`
       - `after_refine.mp4`
       - `refine/gen.mp4`
       - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.pt`
   - 已验证结论:
     - 这轮 bridge refine 已完整结束
2. 外部 FastGS 点进入 FreeFix refine 后发生了什么:
   - 已验证事实:
     - bridge 初始高斯数:
       - `49200`
     - refined checkpoint 高斯数:
       - `154614`
   - 已验证结论:
     - 这份外部 FastGS checkpoint 不只是“能加载”
     - 它已经被 FreeFix refine 当成有效初始状态继续 densify 与优化
3. 为什么本轮没有继续跑定量评估:
   - 已验证事实:
     - 当前 `ours.evaluation` 的基础评估入口默认仍从:
       - `cfg.base_dir/ckpts/ckpt_<load_step>.pt`
       读取基础模型
     - 本轮基础模型实际来自:
       - `--ckpt-path data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
   - 已验证结论:
     - refine 本身已完成
     - 但如果要评估这条 bridge base / refined 线, 最好后续再给 evaluation 增加 `--ckpt-path` override

## 做出的决定

- 决定22: 保留本轮 bridge 源文件、转换产物和 refine 产物, 作为后续外部 FastGS -> FreeFix 路径的标准样例。
- 决定23: 本轮先停在 refine 完成, 不为了补评估去临时篡改 `ckpts/ckpt_35000.pt` 目录契约。

## 状态

**目前已完成全部阶段** - 外部 `my5_nomask_v1` checkpoint 已完成复制、转换与 refine, 结果和后续缺口都已记录。

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: 开始补 evaluation 的外部 ckpt 入口, 准备做 bridge base/refined 对比

## 阶段

- [ ] 阶段1: 为 evaluation 增加外部 `--ckpt-path` override
- [ ] 阶段2: 用单测锁定 CLI 契约
- [ ] 阶段3: 运行 bridge base + refined 真实评估
- [ ] 阶段4: 汇总对比结果并更新支线记录

## 关键问题

1. 当前评估链路真正缺的是什么:
   - 已验证事实:
     - `ours.evaluation` 目前只支持:
       - `--load-step`
       - `--skip-refined`
     - 但 bridge base 的真实入口需要:
       - `--ckpt-path`
   - 当前结论:
     - 这是一个明确的入口缺口, 不是评估逻辑本身坏掉
2. 这次要对比哪两组结果:
   - 已知事实:
     - 基础 bridge ckpt:
       - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
     - refined ckpt:
       - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.pt`
   - 当前结论:
     - 这轮对比口径应是:
       - bridge base
       - bridge refine 后

## 做出的决定

- 决定24: 先做最小改动, 让 evaluation 复用 refine 已经验证过的路径 override 模式。

## 状态

**目前在阶段1** - 正在修改评估入口, 让它支持 bridge ckpt 的真实评估。

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: evaluation 外部 ckpt 入口已落地并通过验证, 转入真实评估

## 阶段

- [x] 阶段1: 为 evaluation 增加外部 `--ckpt-path` override
- [x] 阶段2: 用单测锁定 CLI 契约
- [ ] 阶段3: 运行 bridge base + refined 真实评估
- [ ] 阶段4: 汇总对比结果并更新支线记录

## 关键问题

1. 入口补丁是否已经具备动态证据:
   - 已验证事实:
     - `python3 -m py_compile ours/evaluation.py tests/test_evaluation_cli.py`
     - `.pixi/envs/default/bin/python -m unittest tests.test_evaluation_cli`
     - `.pixi/envs/default/bin/python -m ours.evaluation --help`
   - 已验证结论:
     - 评估入口已支持:
       - `--colmap-path`
       - `--ckpt-path`
2. refined 评估是否会误用外部 base ckpt:
   - 已验证事实:
     - 新测试显式锁定:
       - 基础评估 `include_ckpt_override=True`
       - refined 评估 `include_ckpt_override=False`
   - 已验证结论:
     - base 与 refined 的读取口径已经分开

## 做出的决定

- 决定25: 现在直接跑真实评估, 不再额外插入更多中间 smoke。

## 状态

**目前在阶段3** - 正在执行 bridge base 与 refined 的真实评估。

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] [记录类型]: bridge base / refined 评估完成, 对比结论已收口

## 阶段

- [x] 阶段1: 为 evaluation 增加外部 `--ckpt-path` override
- [x] 阶段2: 用单测锁定 CLI 契约
- [x] 阶段3: 运行 bridge base + refined 真实评估
- [x] 阶段4: 汇总对比结果并更新支线记录

## 关键问题

1. bridge base vs refined 的真实指标差异是什么:
   - 已验证事实:
     - bridge base `35000_test.json`:
       - `PSNR = 23.95420037246332`
       - `SSIM = 0.848878347292179`
       - `LPIPS = 0.2550300701362331`
     - refined `..._test.json`:
       - `PSNR = 26.613409786689573`
       - `SSIM = 0.8803512395882025`
       - `LPIPS = 0.22109279745235677`
     - test 增量:
       - `PSNR +2.659209414226254`
       - `SSIM +0.03147289229602346`
       - `LPIPS -0.03393727268387631`
     - train 增量:
       - `PSNR +2.638686972035117`
       - `SSIM +0.03098149097429148`
       - `LPIPS -0.03432484013242351`
   - 已验证结论:
     - 这轮 refine 对 bridge base 是明显正收益
2. 这组结果和 FastGS 原始结果的关系是什么:
   - 已验证事实:
     - FastGS `results.json` 记录:
       - `PSNR = 27.203941345214844`
       - `SSIM = 0.8910136222839355`
       - `LPIPS = 0.20262764394283295`
     - 当前 bridge base 明显低于这个值
     - 当前 refined 结果比 bridge base 明显回升, 但仍低于 FastGS 原始记录
   - 当前结论:
     - 已确认存在“bridge fidelity 仍有损失”的现象
     - 但这轮还没有进一步验证具体根因

## 做出的决定

- 决定26: 当前先把“evaluation 入口已补齐 + refine 对 bridge base 有显著提升”作为主结论交付。
- 决定27: 把“bridge base 低于 FastGS 原始结果”记录成后续调查项, 不在没有新证据时贸然下根因结论。

## 状态

**目前已完成全部阶段** - evaluation 入口已补齐, bridge base / refined 对比已完成, 本轮结果和后续风险都已记录。

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] [记录类型]: bridge 评估结果已复核, 本轮正式收尾交付

## 关键问题

1. 当前对外可交付的对比结论是否已经有足够证据:
   - 已验证事实:
     - `bridge base`:
       - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/35000_test.json`
       - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/35000_train.json`
     - `refined`:
       - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_test.json`
       - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000/eval/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_train.json`
     - `FastGS` 原始记录:
       - `/home/rais/FastGS/output/my5_nomask_v1/results.json`
   - 已验证结论:
     - 这轮 base / refined / FastGS 三方对比已经有真实落盘证据, 可以直接交付
2. 当前还不能下结论的部分是什么:
   - 已观察到的事实:
     - bridge base 明显低于 FastGS 原始结果
   - 当前假设:
     - 可能和 `import_fastgs` 归一化契约、benchmark 切分口径、相机顺序或渲染约定有关
   - 验证计划:
     - 做一次 `--no-normalize` 导入对照
     - 核对 FastGS / FreeFix 的 split 与相机顺序
     - 必要时补单帧指标复算

## 做出的决定

- 决定28: 本轮先交付“refine 对 bridge base 有显著提升”这一已验证结论, 不把 bridge fidelity 损失误写成已确认根因。
- 决定29: 由于环境未暴露 `CODEX_SESSION_ID`, 本轮收尾记录采用当前 UTC 时间派生标识:
  - `20260327T194314Z-main`

## 状态

**目前已完成全部阶段** - bridge base / refined / FastGS 原始结果已复核, 支线记录已补齐, 下一轮若继续就是做最小验证实验查 bridge fidelity 损失来源。

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] [记录类型]: 启动 bridge base 掉分原因调查

## 目标

- 用最小可证伪实验判断:
  - 为什么 `my5_nomask_v1` 的 FastGS checkpoint 转进 FreeFix 后, `bridge base` 分数会明显低于 FastGS 原始记录
- 输出必须区分:
  - 现象
  - 假设
  - 验证证据
  - 已验证结论

## 阶段

- [ ] 阶段1: 静态阅读导入与评估链路, 列出候选原因
- [ ] 阶段2: 验证 benchmark 口径是否一致
- [ ] 阶段3: 验证导入归一化是否造成主要损失
- [ ] 阶段4: 汇总证据并给出当前最稳妥结论

## 关键问题

1. 当前最强主假设是什么:
   - 当前假设:
     - `import_fastgs` 的 similarity 归一化或坐标契约, 可能让转换后的状态偏离了 FastGS 原始 checkpoint
2. 当前最强备选解释是什么:
   - 当前假设:
     - FastGS 与 FreeFix 的 benchmark 口径并不完全一致, 包括:
       - test split
       - 相机顺序
       - 图像对应关系
3. 什么证据会推翻主假设:
   - 验证计划:
     - 如果 `--no-normalize` 导入后分数几乎不变, 主假设会明显减弱
     - 如果发现 test split 或图像对应不一致, benchmark 口径问题优先级会上升

## 做出的决定

- 决定30: 本轮先不改训练和 refine 参数, 只做最小验证实验。
- 决定31: 先查 benchmark 口径, 再查导入归一化, 避免一开始就把责任归到导入脚本上。

## 状态

**目前在阶段1** - 正在阅读 `import_fastgs`、评估入口与相关配置, 先收敛候选原因, 再做最小实验。

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] [记录类型]: bridge 掉分原因验证完成, 已锁定为“归一化时高阶 SH 未随旋转变换”

## 阶段

- [x] 阶段1: 静态阅读导入与评估链路, 列出候选原因
- [x] 阶段2: 验证 benchmark 口径是否一致
- [x] 阶段3: 验证导入归一化是否造成主要损失
- [x] 阶段4: 汇总证据并给出当前最稳妥结论

## 关键问题

1. benchmark 口径是不是主因:
   - 已验证事实:
     - FreeFix `test` dataset 和 FastGS `test/ours_35000/gt`:
       - 数量同为 `41`
       - 前 5 张逐帧像素一致
       - 最终 `all_pixels_equal = True`
     - FastGS 原始 render 用 FreeFix 指标重算:
       - `PSNR 27.2039`
       - `SSIM 0.8898`
       - `LPIPS 0.1978`
   - 已验证结论:
     - benchmark / 指标实现差异不是这次 `PSNR 23.95` 掉分的主因
2. checkpoint 解析是否出错:
   - 已验证事实:
     - `ckpt_35000.pth` 与 `point_cloud/iteration_35000/point_cloud.ply` 解出的:
       - `means`
       - `opacities`
       - `scales`
       - `quats`
       - `sh0`
       - `shN`
       全部 `max_abs = 0.0`
   - 已验证结论:
     - 不是 checkpoint tuple 映射错误
3. 掉分发生在什么步骤:
   - 已验证事实:
     - raw checkpoint + raw cameras + FreeFix renderer:
       - `PSNR 27.1882`
       - `SSIM 0.8907`
       - `LPIPS 0.2037`
     - normalized checkpoint + normalized cameras:
       - `PSNR 23.9542`
       - `SSIM 0.8489`
       - `LPIPS 0.2550`
     - `--no-normalize` 但仍喂给 normalized cameras:
       - `PSNR 11.6517`
       - `SSIM 0.6638`
       - `LPIPS 0.7779`
   - 已验证结论:
     - 坐标归一化本身是必须的
     - 但当前“归一化后的参数变换”是不完整的
4. 归一化里最可能缺了什么:
   - 已验证事实:
     - `resolve_colmap_transform()` 的全局旋转角约 `86.79` 度
     - `transform_splats_to_freefix()` 只变换了:
       - `means`
       - `quats`
       - `scales`
     - 没有旋转:
       - `sh0`
       - `shN`
     - 当把 `shN` 全部清零后:
       - raw + raw cameras: `PSNR 25.9171`, `SSIM 0.8764`, `LPIPS 0.2295`
       - normalized + normalized cameras: `PSNR 25.9171`, `SSIM 0.8764`, `LPIPS 0.2295`
       - 两边几乎完全一致
   - 已验证结论:
     - 几何变换本身没有问题
     - 主要损失来自高阶 SH 在大角度全局旋转后没有做 SH basis rotation

## 做出的决定

- 决定32: 把“高阶 SH 未随全局旋转一起变换”升级为当前已验证主结论。
- 决定33: 暂不直接改代码, 先把证据完整交付给用户; 如果用户要继续, 下一步就是在 `recon.import_fastgs` 里补 SH rotation。

## 状态

**目前已完成全部阶段** - bridge 掉分来源已经锁定到导入归一化阶段, 更具体地说是“高阶 SH 系数未随全局旋转变换”, 当前只差把结论和后续修复建议交付给用户。

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] [记录类型]: 继续执行 bridge 修复, 目标是补齐 SH rotation 并复验真实评估

## 目标

- 在 `recon.import_fastgs` 中补齐高阶 SH 的全局旋转变换。
- 用单测和真实 `my5_nomask_v1` bridge 评估确认:
  - 修复后 normalized bridge base 应明显接近 raw / FastGS 原始结果

## 阶段

- [ ] 阶段1: 选定 SH rotation 实现方案并完成代码修改
- [ ] 阶段2: 补回归测试, 覆盖 DC-only 不变与旋转一致性
- [ ] 阶段3: 运行静态验证与单测
- [ ] 阶段4: 重跑真实 bridge 评估并核对指标回升幅度

## 关键问题

1. 这次修复的目标是否足够单一:
   - 已验证事实:
     - 当前主损失已锁定在 `shN` 旋转缺失
   - 当前决定:
     - 本轮只修 SH rotation, 不顺手改别的 bridge 逻辑
2. 修复成功的最小证据是什么:
   - 验证计划:
     - `DC-only` 回归仍需保持不变
     - full SH 的 normalized bridge 真实评估应明显接近 raw `27.19`

## 做出的决定

- 决定34: 这轮先做最正确修复, 不做“只把 SHN 清零”的临时补丁。
- 决定35: 修完后直接用 `my5_nomask_v1` 真实 bridge 重评估, 不只停留在单测。

## 状态

**目前在阶段1** - 正在选定 SH rotation 实现方案, 接下来直接修改 `recon.import_fastgs.py` 并补测试。

## [2026-03-27 21:19:24] [Session ID: 20260327T194314Z-main] [记录类型]: SH rotation 修复与真实 bridge 复验完成

## 阶段

- [x] 阶段1: 选定 SH rotation 实现方案并完成代码修改
- [x] 阶段2: 补回归测试, 覆盖 DC-only 不变与旋转一致性
- [x] 阶段3: 运行静态验证与单测
- [x] 阶段4: 重跑真实 bridge 评估并核对指标回升幅度

## 关键问题

1. 修复后真实指标回升到什么程度:
   - 已验证事实:
     - 修复后 fixed bridge `test`:
       - `PSNR 27.188240097790228`
       - `SSIM 0.8906744631325326`
       - `LPIPS 0.2037334242245046`
     - 修复前 old bridge `test`:
       - `PSNR 23.95420037246332`
       - `SSIM 0.848878347292179`
       - `LPIPS 0.2550300701362331`
     - FastGS 原始记录:
       - `PSNR 27.203941345214844`
       - `SSIM 0.8910136222839355`
       - `LPIPS 0.20262764394283295`
   - 已验证结论:
     - 修复后 bridge base 已经基本追平 FastGS 原始结果
2. 修复增量是否足够大:
   - 已验证事实:
     - fixed - old:
       - `PSNR +3.2340`
       - `SSIM +0.04180`
       - `LPIPS -0.05130`
     - fixed - FastGS:
       - `PSNR -0.0157`
       - `SSIM -0.00034`
       - `LPIPS +0.00111`
   - 已验证结论:
     - 当前残余误差已经进入极小范围, 可以把这次 bridge 掉分 bug 视为已修复

## 做出的决定

- 决定36: 把新的修复版 bridge checkpoint 固化为 canonical 文件:
  - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
- 决定37: 旧错误版本保留为备份:
  - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000_pre_shfix_freefix.pt`

## 状态

**目前已完成全部阶段** - 代码修复、单测、真实 bridge 导入、真实评估和 canonical checkpoint 更新都已完成。

## [2026-03-27 21:24:17] [Session ID: 20260327T212417Z-main] [记录类型]: 基于修复后 canonical bridge checkpoint 再跑一轮 refine 与评估

## 目标

- 基于已经修复 SH rotation 的 canonical bridge checkpoint:
  - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
  再跑一轮新的 refine。
- 这轮 rerun 不覆盖旧的:
  - `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000`
  也不覆盖仅含 base 评估的:
  - `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh`
- 跑完后拿到 3 组同口径结果:
  - 旧 bridge refine
  - 修复后 bridge base
  - 修复后 bridge refine rerun

## 阶段

- [ ] 阶段1: 新建 fixsh rerun 专用 refine 配置, 锁定独立 exp_name
- [ ] 阶段2: 串行运行修复后 bridge 的真实 refine
- [ ] 阶段3: 运行修复后 bridge 的 base + refined 评估
- [ ] 阶段4: 汇总 rerun 结果并更新支线记录

## 关键问题

1. 这轮 rerun 的变量是否足够单一:
   - 已验证事实:
     - bridge 掉分 bug 已修复
     - canonical `ckpt_35000_freefix.pt` 已经是修复后的版本
   - 当前决定:
     - 本轮只替换起始 bridge checkpoint
     - refine 参数继续沿用:
       - `strength: 0.65`
       - `refine_steps: 400`
       - `warp_ratio: 0.3`
2. 如何避免覆盖旧证据:
   - 当前决定:
     - 新建独立配置文件
     - 新 exp_name 固定为:
       - `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun`
3. 这轮最小成功证据是什么:
   - 验证计划:
     - refine 目录需要完整落盘:
       - `before_refine.mp4`
       - `after_refine.mp4`
       - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt`
     - 评估后至少要能回答:
       - 修复 bridge bug 后, refine 还剩多少真实收益

## 做出的决定

- 决定38: 本轮 refine 显式使用当前 canonical bridge checkpoint:
  - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
- 决定39: 评估仍然使用 `--ckpt-path`, 确保 base 评估的是外部 bridge checkpoint, 而不是误读 `base_dir/ckpts` 里的别的文件。

## 状态

**目前在阶段1** - 正在补 fixsh rerun 的独立配置, 下一步直接启动真实 refine。

## [2026-03-27 21:24:17] [Session ID: 20260327T212417Z-main] [记录类型]: fixsh rerun 配置已创建, refine 已启动

## 阶段

- [x] 阶段1: 新建 fixsh rerun 专用 refine 配置, 锁定独立 exp_name
- [ ] 阶段2: 串行运行修复后 bridge 的真实 refine
- [ ] 阶段3: 运行修复后 bridge 的 base + refined 评估
- [ ] 阶段4: 汇总 rerun 结果并更新支线记录

## 关键问题

1. refine 是否已经真正开始:
   - 已验证事实:
     - 日志命中:
       - `[Parser] 324 images`
       - `Using Flux model source: /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`
       - `Loading pipeline components... 100%`
   - 当前结论:
     - 本轮 rerun 的 refine 入口已正常启动

## 做出的决定

- 决定40: 继续保持串行执行, refine 结束前不启动别的训练或评估任务。

## 状态

**目前在阶段2** - fixsh rerun 的真实 refine 已启动, 正在等待完整落盘。

## [2026-03-27 21:35:37] [Session ID: 20260327T212417Z-main] [记录类型]: fixsh rerun refine 已完成, 转入 base + refined 评估

## 阶段

- [x] 阶段1: 新建 fixsh rerun 专用 refine 配置, 锁定独立 exp_name
- [x] 阶段2: 串行运行修复后 bridge 的真实 refine
- [ ] 阶段3: 运行修复后 bridge 的 base + refined 评估
- [ ] 阶段4: 汇总 rerun 结果并更新支线记录

## 关键问题

1. refine 是否完整收口:
   - 已验证事实:
     - `before_refine/`: `41` 张
     - `refine/gen/`: `41` 张
     - `after_refine/`: `41` 张
     - 已落盘:
       - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt`
       - `before_refine.mp4`
       - `after_refine.mp4`
   - 已验证结论:
     - 这轮 fixsh rerun refine 已完整结束

## 做出的决定

- 决定41: 现在直接用同一份 exp cfg 执行 base + refined 评估, 不再插入别的实验。

## 状态

**目前在阶段3** - fixsh rerun refine 已完成, 正在执行 base 和 refined 的真实评估。

## [2026-03-27 21:37:03] [Session ID: 20260327T212417Z-main] [记录类型]: fixsh rerun 的 base + refined 评估完成, 本轮闭环

## 阶段

- [x] 阶段1: 新建 fixsh rerun 专用 refine 配置, 锁定独立 exp_name
- [x] 阶段2: 串行运行修复后 bridge 的真实 refine
- [x] 阶段3: 运行修复后 bridge 的 base + refined 评估
- [x] 阶段4: 汇总 rerun 结果并更新支线记录

## 关键问题

1. 修复后 bridge refine 还剩多少真实收益:
   - 已验证事实:
     - 修复后 base `test`:
       - `PSNR 27.188240097790228`
       - `SSIM 0.8906744631325326`
       - `LPIPS 0.2037334242245046`
     - 修复后 refined `test`:
       - `PSNR 26.752713505814715`
       - `SSIM 0.8825770921823455`
       - `LPIPS 0.22314650619902263`
     - refined - base:
       - `PSNR -0.4355`
       - `SSIM -0.00810`
       - `LPIPS +0.01941`
   - 已验证结论:
     - 同一组 refine 参数在修复后 bridge 上仍会把 GT 指标拉差
2. 新 rerun 相对旧 bridge refine 有没有改善:
   - 已验证事实:
     - 新 refined `test` - 旧 refined `test`:
       - `PSNR +0.1393`
       - `SSIM +0.00223`
       - `LPIPS +0.00205`
   - 已验证结论:
     - 修复 bridge bug 后再 refine, 相比旧 bridge refine 确实略有改善
     - 但仍然没有超过修复后的 base
3. bridge base 与 FastGS 原始记录现在还差多少:
   - 已验证事实:
     - base - FastGS:
       - `PSNR -0.0157`
       - `SSIM -0.00034`
       - `LPIPS +0.00111`
   - 已验证结论:
     - 当前 canonical bridge base 已经基本追平 FastGS 原始 benchmark

## 做出的决定

- 决定42: 当前 `35000` bridge 路线的默认量化基线应切换为修复后的 canonical base, 而不是旧 bridge refine。
- 决定43: 如果后面继续追主观观感, 下一步应该做的是轻量 refine 参数搜索, 不是继续沿用这组偏强参数。

## 状态

**目前已完成全部阶段** - fixsh rerun 的配置、真实 refine、真实评估和对比结论都已完成。

## [2026-03-28 17:37:14] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] [记录类型]: 按用户要求直接导出 fixsh rerun 的最终 3DGS PLY

## 目标

- 直接把 `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun` 的 refined checkpoint 导出成最终 `.ply`
- 给出实际落盘路径, 不再停留在“有没有”的口头判断

## 阶段

- [x] 阶段1: 确认 exp cfg、base_dir 与 refined checkpoint 是否存在
- [ ] 阶段2: 执行 checkpoint -> `.ply` 导出
- [ ] 阶段3: 验证文件落盘并补记录

## 关键问题

1. 已验证事实:
   - refined checkpoint 已存在:
     - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt`
   - 目前尚未找到对应 `.ply`
2. 当前动作:
   - 直接调用 `recon.export_3dgs_ply` 导出
3. 默认目标路径:
   - `outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.ply`

## 做出的决定

- 决定44: 不再等待 wrapper 或后续流程补导出, 这轮直接从现存 refined checkpoint 导出最终 `.ply`

## 状态

**目前在阶段2** - 正在执行 fixsh rerun refined checkpoint 的 `.ply` 导出。

## [2026-03-28 17:37:14] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] [记录类型]: fixsh rerun 最终 3DGS PLY 已导出并校验

## 阶段

- [x] 阶段1: 确认 exp cfg、base_dir 与 refined checkpoint 是否存在
- [x] 阶段2: 执行 checkpoint -> `.ply` 导出
- [x] 阶段3: 验证文件落盘并补记录

## 关键问题

1. 导出命令:
   - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m recon.export_3dgs_ply --ckpt /root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt --output /root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.ply`
2. 关键输出:
   - `gaussian_count: 159281`
   - `property_count: 62`
3. 落盘校验:
   - 文件已存在:
     - `outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.ply`
   - 文件大小:
     - `38M`
   - `file` 识别结果:
     - `PLY model, binary, little endian, version 1.0`

## 做出的决定

- 决定45: 这份 rerun 结果现在以 `ckpt + final ply` 两种形态同时保留, 便于后续 viewer / 外部工具链复用。

## 状态

**目前已完成** - fixsh rerun 的最终 `.ply` 已直接导出并完成基础校验。

## [2026-03-28 17:55:00] [Session ID: 945d570e-8f9a-4112-9004-6a0f244a9a65] [记录类型]: 为 `after_refine.mp4` 制作镜头轨迹动画数据导出工具

## 目标

- 为 `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun/after_refine.mp4` 导出可复用的镜头轨迹动画数据文件。
- 导出结果必须和视频逐帧一一对应, 不能把训练期 `to_refine` 轨迹误当成 refine 后视频轨迹。

## 阶段

- [x] 阶段1: 回读 `colmap_my5` 支线上下文并确认目标视频来源
- [ ] 阶段2: 验证 `after_refine.mp4` 的真实相机来源与现有 sidecar 的关系
- [ ] 阶段3: 实现导出工具并补最小回归测试
- [ ] 阶段4: 对目标视频真实导出并校验落盘结果

## 关键问题

1. 当前现象:
   - `after_refine.mp4` 位于 `fixsh_rerun` refine 输出目录, 共 `41` 帧。
   - `recon/trainer.py::render_traj()` 也会生成 `41` 帧 `refine_c2ws.npy`, 但那条链路属于训练阶段 `to_refine`, 且静态代码显示它对 `camtoworld` 额外右乘了平移矩阵。
2. 当前主假设:
   - `after_refine.mp4` 的真实镜头轨迹来自 `Refiner.test_dataset[idx]["camtoworld"]`, 也就是 `refine_by_flux.py` 在 `refine_start_idx..refine_end_idx` 范围内逐帧调用 `refiner.render(i)` 的那组测试相机。
3. 最强备选解释:
   - 如果真实比对发现 `after_refine.mp4` 与 `to_refine/ckpt_34999/refine_c2ws.npy` 完全一致, 那说明当前 `my5` 这条线上训练期导出轨迹和 refine 测试轨迹恰好重合, 工具可以直接复用 sidecar。
4. 计划路线:
   - 方案A(最佳方案): 直接从 `exp_cfg/base_dir/cfg.json + test split + refine_start/end` 重建真实相机序列, 再导出 JSON 动画数据。
   - 方案B(先能用方案): 如果检测到目标视频和某个现有 `refine_c2ws.npy` 完全同构, 允许直接从 sidecar 快速导出, 但仍要在元数据里标明来源口径。

## 做出的决定

- 决定46: 继续沿用 `colmap_my5` 支线文件, 不另开新后缀, 因为这件事直接服务于同一条 `fixsh_rerun` 结果链路。
- 决定47: 不走“从 MP4 像素反推位姿”的路线。优先导出真实相机元数据, 这样结果才可验证、可复现、可再次渲染。
- 决定48: 导出格式优先做人类可读、也便于二次处理的 JSON, 并把逐帧矩阵、位置、旋转和基础视频信息一起落盘。

## 状态

**目前在阶段2** - 已确认目标视频来源代码路径, 正在做 `after_refine` 真实轨迹与 `to_refine` sidecar 的最小动态比对。

## [2026-03-28 18:08:00] [Session ID: 945d570e-8f9a-4112-9004-6a0f244a9a65] [记录类型]: `after_refine.mp4` 镜头轨迹导出工具已完成并完成真实导出

## 阶段

- [x] 阶段1: 回读 `colmap_my5` 支线上下文并确认目标视频来源
- [x] 阶段2: 验证 `after_refine.mp4` 的真实相机来源与现有 sidecar 的关系
- [x] 阶段3: 实现导出工具并补最小回归测试
- [x] 阶段4: 对目标视频真实导出并校验落盘结果

## 关键问题

1. `after_refine.mp4` 的真实轨迹是否已经确认:
   - 已验证事实:
     - `after_refine.mp4` 共 `41` 帧
     - 真实导出工具按 `Refiner.test_dataset` 导出后, JSON 也得到 `41` 帧
     - 自动定位到的 refine 配置是:
       - `exp_cfg/my5/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.yaml`
   - 已验证结论:
     - `after_refine.mp4` 的逐帧轨迹就是 refine 测试集相机, 不是训练期渲染 sidecar 本身
2. `to_refine/ckpt_34999/refine_c2ws.npy` 能不能直接当成 `after_refine` 轨迹:
   - 已验证事实:
     - 两者旋转矩阵逐帧完全一致:
       - `rotation_matrix_diff_max = 0.0`
     - 但平移逐帧恒定相差约 `2.5`:
       - `translation_diff_mean = 2.4999999956190857`
   - 已验证结论:
     - 训练期 `to_refine` 轨迹不能直接冒充 `after_refine` 真实轨迹
     - 它只适合作为对照 sidecar 元数据保留
3. 工具是否已经真实可用:
   - 已验证事实:
     - 新脚本:
       - `ours/export_refine_video_trajectory.py`
     - 新测试:
       - `tests/test_export_refine_video_trajectory.py`
     - 真实导出结果:
       - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun/after_refine_camera_trajectory.json`
     - JSON 顶层包含:
       - `video`
       - `refine`
       - `frames`
       - `training_render_sidecar_comparison`
   - 已验证结论:
     - 这轮工具已经能直接对真实 `after_refine.mp4` 落地镜头轨迹动画数据文件

## 做出的决定

- 决定49: 这类 refine 视频轨迹导出统一以 `refiner_test_dataset` 为主口径, 不再默认复用 `to_refine/refine_c2ws.npy`。
- 决定50: 保留 `training_render_sidecar_comparison` 字段, 让后续查看 JSON 时能直接看见训练侧 sidecar 与真实 refine 轨迹的差异证据。

## 状态

**目前已完成** - 导出工具、单测、真实导出和关键差异验证都已完成。

## [2026-03-28 18:18:00] [Session ID: 945d570e-8f9a-4112-9004-6a0f244a9a65] [记录类型]: 补充 Unity 友好版轨迹 sidecar

## 关键问题

1. 用户当前真实需求:
   - 不只是“找到 JSON”
   - 而是要把轨迹导入 Unity
2. 已验证事实:
   - 原始导出文件确实存在:
     - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun/after_refine_camera_trajectory.json`
   - 同时已补一份 Unity 友好版:
     - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun/after_refine_camera_trajectory_unity.json`
   - Unity 版每帧包含:
     - `quaternionXyzw`
     - `cameraToWorldRowMajor`
     - `cameraToWorldColumnMajor`
     - `intrinsicsRowMajor`
3. 当前结论:
   - 现在用户不需要再自己换四元数顺序或手工拍平矩阵
   - 直接优先读 Unity 版 sidecar 即可

## 做出的决定

- 决定51: 导出器默认同时写出通用 JSON 和 Unity 友好 JSON。
- 决定52: Unity 版先保持原始 FreeFix/COLMAP-normalized 坐标系, 不擅自加额外轴变换, 避免把用户已对齐好的几何空间再扭坏。

## 状态

**目前已完成** - 通用版与 Unity 版轨迹 sidecar 都已落盘并验证。
