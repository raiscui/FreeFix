# 任务计划: 创建 fastdropgs checkpoint 转换与 refine 支持的 OpenSpec change

## [2026-03-29 16:54:59] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] [记录类型]: 初始化 OpenSpec 新变更计划

## 目标

创建一个新的 OpenSpec change, 用来描述"支持把 fastdropgs 的 `.pth` checkpoint 转换到当前工程, 并允许转换结果继续进入 refine 流程"这项能力, 并拿到第一个 artifact 的官方模板。

## 阶段

- [x] 阶段1: 读取上下文与相关 skill
- [ ] 阶段2: 确认 change 命名、工作流与现有变更占用情况
- [ ] 阶段3: 创建 change 并查看 artifact 状态
- [ ] 阶段4: 获取第一个 artifact 的指引并整理交付

## 关键问题

1. 用户目标是否足够清晰, 可以直接派生 kebab-case change 名称: 是。核心目标就是新增 `fastdropgs checkpoint -> 当前工程格式` 的转换支持, 且转换后还能 refine。
2. 是否需要非默认 workflow schema: 当前没有。用户只要求新开 change, 没有指定 schema。
3. 这次任务是否适合放进主线默认六文件: 不适合。当前默认 `task_plan.md` 主线是安装和环境问题, 本任务更像独立需求变更。

## 做出的决定

- 决定1: 启用支线上下文 `__fastdropgs_checkpoint_refine`, 避免污染主线计划。
- 决定2: 先按 skill 要求走默认 OpenSpec workflow, 不主动创建 proposal 之外的 artifact。
- 决定3: 先采用更稳的命名方向 `support-fastdropgs-checkpoint-refine`, 因为它同时覆盖"新增格式支持"与"可继续 refine"两层意图。
- 决定4: 保留一个备选命名方向 `add-fastdropgs-checkpoint-conversion`, 如果 CLI 或现有约定提示更适合聚焦"转换"而不是"refine", 再调整。

## 遇到错误

- 错误1: 当前机器没有 `openspec` CLI, `openspec --help` 直接报 `command not found`。
- 错误2: 当前机器也没有 `pnpm`, 因此不能直接走 `pnpm view ...` 这类 npm registry 探测。

## [2026-03-29 16:58:25] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] [记录类型]: 范围核对完成, 准备手工创建 change 目录

## 阶段

- [x] 阶段1: 读取上下文与相关 skill
- [x] 阶段2: 确认 change 命名、工作流与现有变更占用情况
- [ ] 阶段3: 创建 change 并查看 artifact 状态
- [ ] 阶段4: 获取第一个 artifact 的指引并整理交付

## 关键问题

1. 当前机器是否能按 skill 原样调用 `openspec new change`: 不能。CLI 不在 PATH, 需要采用仓库里已验证过的手工 fallback。
2. 用户给的 `fastdropgs` checkpoint 是否真是另一种完全不同的结构: 目前证据显示不是。动态读取 `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth` 后, 它和现有 FastGS `.pth` 一样都是 `(capture_tuple, iteration)` 结构, 且 `capture_tuple` 长度同为 `14`。
3. 现有桥接和 refine 编排是否已经完全不能吃这份文件: 不是。动态 smoke 表明 `recon.import_fastgs` 已能把这份文件导成 FreeFix checkpoint, `ours/run_fastgs_refine.py --dry-run` 也已经能把它串进 bridge + refine + ply 导出命令。

## 做出的决定

- 决定5: 把 change 名称收敛为 `add-fastdropgs-checkpoint-bridge`。
- 决定6: 这次 change 的重点不是重写一套大解析器, 而是把当前"实际上已能工作, 但还没被正式命名/测试/文档化"的 `fastdropgs` 支持变成显式能力。
- 决定7: 在 CLI 缺失的前提下, 先手工创建 `openspec/changes/add-fastdropgs-checkpoint-bridge/` 目录, 再按默认 spec-driven workflow 给出第一个 artifact `proposal` 的模板。

## 状态

**目前在阶段3** - 变更名已经确认, 动态证据也已补齐, 现在开始创建新的 change 目录并整理 `proposal` 模板。

## [2026-03-29 16:59:33] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] [记录类型]: change 骨架已创建, 进入交付

## 阶段

- [x] 阶段1: 读取上下文与相关 skill
- [x] 阶段2: 确认 change 命名、工作流与现有变更占用情况
- [x] 阶段3: 创建 change 并查看 artifact 状态
- [x] 阶段4: 获取第一个 artifact 的指引并整理交付

## 关键问题

1. change 目录是否已创建: 是。`openspec/changes/add-fastdropgs-checkpoint-bridge/` 已手工创建。
2. 是否拿到了官方 `openspec status` 输出: 没有。CLI 缺失, 只能基于仓库现有 `add-pose-jitter-refine` 结构推断默认 workflow。
3. 当前最合理的 artifact 序列推断是什么: `proposal -> design -> tasks -> capability spec`。
4. 当前 change 的完成度应如何表述: 已完成“new change”这一步, 当前是 `0/4` artifacts 完成, 第一个待写 artifact 是 `proposal.md`。

## 做出的决定

- 决定8: 对外明确区分“这是按仓库现有 OpenSpec 风格推断出的 workflow”, 不把它表述成 CLI 已验证的官方状态。
- 决定9: proposal 模板直接沿用仓库现有 `Why / What Changes / Capabilities / Impact` 结构, 这样和后续已有 change 的风格最一致。

## 状态

**目前已完成** - OpenSpec 新 change 已创建, 第一个 artifact `proposal` 的模板和填充方向已经准备好, 可以继续起草。

## [2026-03-29 17:05:32] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] [记录类型]: 按 ff-change 口径补齐 apply-ready artifacts

## 目标

将 `add-fastdropgs-checkpoint-bridge` 从“只有 change 目录”推进到“proposal / design / tasks / capability spec 全部齐备”, 让后续实现可以直接按任务清单开始。

## 阶段

- [x] 阶段1: 回读现有 bridge、wrapper、测试与上游 `fast-dropgs` 证据
- [x] 阶段2: 收敛 change 的真实边界与设计取舍
- [x] 阶段3: 创建 proposal / design / tasks / capability spec
- [x] 阶段4: 回读 artifacts 并确认 apply-ready

## 关键问题

1. 这次 change 最核心的缺口是什么:
   - 不是 tensor 结构完全不兼容
   - 而是 `fast-dropgs` 来源语义、`chkpnt*.pth` 命名、默认输出路径、测试和文档还没被正式支持
2. 当前 artifacts 是否已经齐全:
   - 是
   - 已创建 `proposal.md`、`design.md`、`tasks.md` 和 `specs/fastdropgs-checkpoint-bridge/spec.md`
3. 当前 change 是否已到 apply-ready:
   - 是
   - 后续可以直接进入实现

## 做出的决定

- 决定10: 沿用仓库里已有的 spec-driven OpenSpec 结构, 不额外发明新的 artifact 类型。
- 决定11: design 明确把“复用现有 tuple 解析主链”设成第一原则, 避免把实现引向重复造轮子。
- 决定12: tasks 明确把 `source_format` 语义、`chkpnt` step 识别、默认输出命名、wrapper 文案、测试和 README 一起纳入实现范围。

## 状态

**目前已完成** - `add-fastdropgs-checkpoint-bridge` 的 apply-ready artifacts 已全部补齐, 可以直接进入实现阶段。

## [2026-03-29 17:18:34] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] [记录类型]: 开始按 OpenSpec change `add-fastdropgs-checkpoint-bridge` 实施

## 目标

按 `openspec/changes/add-fastdropgs-checkpoint-bridge/tasks.md` 的任务拆解, 在不破坏现有 FastGS / PLY bridge 主链的前提下, 正式支持 `fast-dropgs` 的 `chkpnt*.pth` checkpoint, 并补齐默认输出、防撞名、测试和文档。

## 阶段

- [ ] 阶段1: 回读实现相关代码并收敛最小改动面
- [ ] 阶段2: 修改 bridge 与 wrapper 代码
- [ ] 阶段3: 补单测与文档
- [ ] 阶段4: 运行验证并回写 OpenSpec tasks

## 关键问题

1. 这轮是否需要重写 checkpoint 解析器:
   - 当前判断: 不需要
   - 原因: `fast-dropgs` 的 capture tuple 与现有 FastGS `.pth` 同型
2. 当前最可能直接影响用户体验的缺口是什么:
   - `source_format` 仍然笼统
   - `chkpnt50000.pth` 的默认 bridge 输出名容易撞
   - 帮助文本与 README 还没有显式提到 `fast-dropgs`
3. 这轮验证最小闭环是什么:
   - 定向单测
   - `run_fastgs_refine.py --dry-run`
   - 真实 `fast-dropgs` 样本的 bridge smoke

## 做出的决定

- 决定13: 先做最小正确实现, 优先改 `source_format`、step 识别和默认输出, 不扩大到抽象化重命名脚本。
- 决定14: wrapper 继续保持轻量, 不引入对 `recon.import_fastgs` 的重依赖导入, 避免破坏 `--help` 的轻环境可用性。
- 决定15: 只有在测试和 smoke 验证通过后, 才回写 `tasks.md` 勾选完成项。

## 状态

**目前在阶段1** - 正在回读实现文件并准备开始代码修改。

## [2026-03-29 17:21:02] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] [记录类型]: 实现与验证完成

## 阶段

- [x] 阶段1: 回读实现相关代码并收敛最小改动面
- [x] 阶段2: 修改 bridge 与 wrapper 代码
- [x] 阶段3: 补单测与文档
- [x] 阶段4: 运行验证并回写 OpenSpec tasks

## 关键问题

1. `fast-dropgs` 的来源语义是否已经显式化:
   - 是
   - 真实 bridge smoke 已输出 `source_format: fastdropgs_checkpoint`
2. `chkpnt50000.pth` 的默认 bridge 输出是否还会落成容易撞名的通用名:
   - 不会
   - dry-run 现在输出的是 `my8_input_50k_from45k_resetopt_chkpnt50000_freefix.pt`
3. 当前验证是否已经覆盖真实 full refine:
   - 没有
   - 当前覆盖的是定向单测、wrapper `--help`、dry-run 和真实 bridge smoke

## 做出的决定

- 决定16: 当前把这条 change 视为实现完成, 因为 `tasks.md` 中定义的实现项已经全部落地并验证。
- 决定17: 保留“匹配真实 `my8` exp_cfg 做 full refine smoke”在 `LATER_PLANS__fastdropgs_checkpoint_refine.md`, 不把它混成这条 change 的必做项。

## 状态

**目前已完成** - `add-fastdropgs-checkpoint-bridge` 的代码实现、定向验证和 tasks 回写都已完成。

## [2026-03-29 18:26:58] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] [记录类型]: 按用户选择继续执行 `my8` 真实 refine smoke

## 目标

在已完成 `add-fastdropgs-checkpoint-bridge` 代码支持的基础上, 继续完成用户选定的后续步骤:
- 为 `my8` 补齐可被 FreeFix refine 消费的运行契约
- 使用 `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth` 跑真实 bridge + refine + PLY 导出
- 如主链跑通, 再补 base/refined 双评估

## 阶段

- [x] 阶段1: 回读既有 `fastdropgs` 支线、`my6/my7` 模板和真实输入事实
- [ ] 阶段2: 重新核对 `my8` 的 split、配置契约和运行前置条件
- [ ] 阶段3: 落 `my8` 配置、`cfg.json` 与 bridge 输出目录
- [ ] 阶段4: 跑真实 refine smoke 并核对产物
- [ ] 阶段5: 视运行结果补评估与支线收尾记录

## 关键问题

1. 这轮是否继续沿用 `__fastdropgs_checkpoint_refine` 支线上下文:
   - 是
   - 因为这一步就是前一轮 `LATER_PLANS` 里保留的同一条后续验证
2. `my8` 是否可以直接照抄旧的 `my6/my7` 动态 split 探测命令:
   - 不能直接照抄
   - 已验证事实: 旧探测脚本里使用的 `Dataset(..., test_every=8)` 在当前仓库报 `TypeError`
   - 当前结论: 需要改读项目当前版本真实支持的数据集入口, 重新拿到 `my8` 的 split 证据
3. 当前最稳的复用策略是什么:
   - 先复用 `my6/my7` 的配置骨架和目录约定
   - 但 `load_step`、`result_dir`、bridge 输出路径与 `my8` split 证据必须按 `my8` 重新落

## 做出的决定

- 决定18: 这轮先不急着开跑, 先把 `my8` split 与当前代码可接受的运行契约重新核实。
- 决定19: `my8` 的 bridge 输出继续显式固定路径, 避免 `chkpnt50000` 默认名和其它来源互相覆盖。
- 决定20: 只有在 dry-run 和真实 refine 命令都通过后, 才把这轮视为完成。

## 遇到错误

- 错误3: 复用旧 probe 时, `Dataset.__init__()` 报 `unexpected keyword argument 'test_every'`。

## 状态

**目前在阶段2** - 已经接上用户选择的后续步骤, 正在用当前仓库真实支持的数据集入口重新核对 `my8` split 和运行前置条件。

## [2026-03-29 18:26:58] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] [记录类型]: `my8` 场景契约已收敛, 转入配置落盘

## 阶段

- [x] 阶段1: 回读既有 `fastdropgs` 支线、`my6/my7` 模板和真实输入事实
- [x] 阶段2: 重新核对 `my8` 的 split、配置契约和运行前置条件
- [ ] 阶段3: 落 `my8` 配置、`cfg.json` 与 bridge 输出目录
- [ ] 阶段4: 跑真实 refine smoke 并核对产物
- [ ] 阶段5: 视运行结果补评估与支线收尾记录

## 关键问题

1. 应该使用哪一个 `my8` 场景目录:
   - 已验证事实:
     - `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/cameras.json` 里只有 `277` 个视角
     - `/home/rais/FastGS/data/my8_colmap_fastgs/images` 有 `324` 张图
     - `/home/rais/FastGS/data/my8_colmap_fastgs/input` 有 `277` 张图, 是 `images/` 的真子集
     - `/home/rais/FastGS/data/my8_colmap_fastgs_input_pruned_v1` 的 parser 结果也是 `277` 张图
   - 已验证结论:
     - 这轮真实 refine 应该对齐 `my8_colmap_fastgs_input_pruned_v1`, 而不是 `324` 图版本的 `my8_colmap_fastgs`
2. `my8` 的 split 应该如何设置:
   - 已验证事实:
     - pruned 场景下 `Parser(test_every=8) + Dataset` 得到:
       - `train = 242`
       - `test = 35`
     - 上游 `fast-dropgs` 输出目录里:
       - `test/ours_50000/gt = 35`
       - `train/ours_50000/gt = 242`
   - 已验证结论:
     - `refine_start_idx: 0`
     - `refine_end_idx: 35`
     - `train_start_idx: 0`
     - `train_end_idx: 242`
3. 这轮运行的最小安全参数是什么:
   - 当前结论:
     - 继续复用 `my6/my7` 的 Flux refine 参数
     - 但 `base_dir`、`data_dir`、`load_step` 和 bridge 输出目录按 `my8` 重建

## 做出的决定

- 决定21: 正式采用 `/home/rais/FastGS/data/my8_colmap_fastgs_input_pruned_v1` 作为 `my8` refine 场景目录。
- 决定22: `my8` 训练契约目录命名为 `outputs/my8_colmap_fastgs_input_pruned_v1_stable_50k_dense`。
- 决定23: 真实 bridge 输出显式固定到 `data/fastgs_bridge/my8_input_50k_from45k_resetopt/chkpnt50000_freefix.pt`。

## 状态

**目前在阶段3** - `my8` 的场景目录、split 和输出路径已经拿到动态证据, 现在开始创建配置文件和运行目录。

## [2026-03-29 18:46:27] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] [记录类型]: `my8` 真实 refine、评估与收尾全部完成

## 阶段

- [x] 阶段1: 回读既有 `fastdropgs` 支线、`my6/my7` 模板和真实输入事实
- [x] 阶段2: 重新核对 `my8` 的 split、配置契约和运行前置条件
- [x] 阶段3: 落 `my8` 配置、`cfg.json` 与 bridge 输出目录
- [x] 阶段4: 跑真实 refine smoke 并核对产物
- [x] 阶段5: 视运行结果补评估与支线收尾记录

## 关键问题

1. `my8` 的真实 bridge + refine + export 是否完整成功:
   - 已验证事实:
     - `ours.run_fastgs_refine.py` 退出码为 `0`
     - bridge 输出:
       - `data/fastgs_bridge/my8_input_50k_from45k_resetopt/chkpnt50000_freefix.pt`
     - refined checkpoint:
       - `outputs/my8_colmap_fastgs_input_pruned_v1_stable_50k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastdropgs_my8_input_50k_from45k_resetopt_fixsh_rerun.pt`
     - final ply:
       - `outputs/my8_colmap_fastgs_input_pruned_v1_stable_50k_dense/point_cloud_flux_shinkai_museum_v2_fastdropgs_my8_input_50k_from45k_resetopt_fixsh_rerun.ply`
   - 已验证结论:
     - `my8` 的 fast-dropgs -> FreeFix -> Flux refine 主链路已经真实跑通
2. 关键中间产物是否齐全:
   - 已验证事实:
     - `before_refine/*.jpg = 35`
     - `refine/render/*.jpg = 35`
     - `refine/gen/*.jpg = 35`
     - `refine/depth/*.jpg = 35`
     - `after_refine/*.jpg = 35`
     - `refine/masks/*/*.jpg = 105`
   - 已验证结论:
     - 这轮 refine 的中间证据链完整
3. 评估是否完整成功:
   - 已验证事实:
     - `ours.evaluation` 最终退出码为 `0`
     - 过程中先暴露了 refined eval 对字符串 `exp_name` 的恢复步数 bug
     - 修复后 base/refined 四个 JSON 全部落盘
   - 已验证结论:
     - `my8` 已完成 base/refined 双评估
4. 当前量化结果如何:
   - 已验证事实:
     - bridge base `50000_test.json`:
       - `PSNR = 13.414619009835379`
       - `SSIM = 0.6838097095489502`
       - `LPIPS = 0.6090567026819501`
     - bridge base `50000_train.json`:
       - `PSNR = 13.37577955781921`
       - `SSIM = 0.6841142317972893`
       - `LPIPS = 0.6125454131729346`
     - refined `..._test.json`:
       - `PSNR = 20.24192292349679`
       - `SSIM = 0.8179223418235779`
       - `LPIPS = 0.48989963701793127`
     - refined `..._train.json`:
       - `PSNR = 20.399197341982`
       - `SSIM = 0.8188200809738853`
       - `LPIPS = 0.49108883184342345`
     - refined 相比 bridge base:
       - `test`: `PSNR +6.8273`, `SSIM +0.1341`, `LPIPS -0.1192`
       - `train`: `PSNR +7.0234`, `SSIM +0.1347`, `LPIPS -0.1215`

## 做出的决定

- 决定24: 将 `my8_colmap_fastgs_input_pruned_v1` 固化为本轮 `my8` fast-dropgs refine 的默认对齐场景。
- 决定25: 保留本轮补上的 refined eval 恢复步数修复, 因为它不是 `my8` 特例, 会影响所有字符串命名的 refined checkpoint 评估。

## 遇到错误

- 错误4: `ours.evaluation` 在 refined eval 阶段把字符串型 `exp_name` 误当成数值步数使用, 报 `ValueError`。
- 错误5: 当前 refined ckpt 本身没有 `step` 字段, 因此仅靠 `payload_step` 兜底还不够。

## 状态

**目前已完成** - `my8` 的配置补齐、真实 fast-dropgs refine、PLY 导出、评估和相关评估 bug 修复都已完成。
