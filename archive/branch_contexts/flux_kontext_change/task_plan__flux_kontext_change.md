# 任务计划: 创建可选 FLUX.1-Kontext-dev OpenSpec change

## [2026-03-31 16:48:25] [Session ID: codex-flux-kontext-change-20260331] [记录类型]: 初始化支线计划

## 目标

创建一条新的 OpenSpec change, 用于描述“为当前项目增加可选 `FLUX.1-Kontext-dev` 路径, 与现有 `sdxl/flux` 并列存在, 而不是替代 `FLUX.1-dev`”。

## 阶段

- [x] 阶段1: 确认用户目标与命名方向
- [x] 阶段2: 创建 OpenSpec change 骨架
- [x] 阶段3: 查看 artifact 状态与首个 artifact 说明
- [x] 阶段4: 记录结果并交付给用户

## 关键问题

1. 这次 change 的目标是“替换现有 `FLUX.1-dev`”吗: 不是。用户明确要求是新增一个可选 `FLUX.1-Kontext-dev` 路径, 与 `sdxl/flux` 并列存在。
2. 这次是否已经有足够的变更描述来生成 change 名称: 是。可以基于“可选 Kontext refine 支持”生成 kebab-case 名称。
3. 命名上最需要保留的语义是什么: “新增可选能力”, 不是“替换默认后端”。
4. 当前项目是否已有 `openspec/specs/` 主规格目录可供“Modified Capabilities”复用: 没有。当前仓库只有 `openspec/changes/...` 下的 change artifacts, 因此本次 proposal 更适合先从 `New Capabilities` 起步。

## 做出的决定

- 决定1: 采用“新增可选能力”口径创建 change, 避免命名误导成“模型替换”。
- 决定2: 优先使用更贴近仓库语义的 change 名称 `add-optional-flux-kontext-refine`。
- 决定3: 遵循 OpenSpec 新建 change 的标准流程, 本轮只创建骨架、查看状态、展示首个 artifact 指引, 不提前写 proposal/design/tasks。

## 遇到错误

- 观察1: `find openspec/specs ...` 返回目录不存在。
  - 这不是阻塞错误。
  - 它说明当前仓库还没有沉淀到主规格目录, proposal 的 `Modified Capabilities` 应谨慎使用。

## 状态

**目前已完成** - change 骨架、artifact 状态与首个 `proposal` 模板都已取回, 可以继续进入 proposal 撰写。

## [2026-03-31 16:53:28] [Session ID: codex-flux-kontext-change-20260331] [记录类型]: 进入 fast-forward artifact 生成

## 目标

把 `add-optional-flux-kontext-refine` 一次性推进到 apply-ready, 也就是至少完成 `proposal`、`design`、`specs`、`tasks` 四份 artifact。

## 阶段

- [x] 阶段1: 确认当前 change 的 apply 依赖图
- [ ] 阶段2: 生成 `proposal`
- [ ] 阶段3: 生成 `design`
- [ ] 阶段4: 生成 `specs`
- [ ] 阶段5: 生成 `tasks`
- [ ] 阶段6: 重新检查 `openspec status` 并交付

## 关键问题

1. `applyRequires` 当前要求哪一份 artifact: `tasks`。这意味着需要把前置 `proposal/design/specs` 一并做完。
2. 当前仓库里已有并列 refine 后端语义吗: 有。`ours/run_fastgs_refine.py` 目前支持 `flux` 和 `sdxl` 两个 backend。
3. `Kontext` 这次最自然的产品语义是什么: 新增第三种可选 refine backend, 优先服务 reference-guided 的图像编辑/修补, 而不是替代现有 `flux`。
4. 当前系统里是否已经存在可以给 Kontext 提供参考图的真实数据契约: 有。`recon/refiner.py` 的 pose-jitter 路径已经保留 `source_image_name`, `recon/datasets/colmap.py` 也直接提供 `image/image_path/image_name`。

## 做出的决定

- 决定4: 本轮直接完成所有 apply 前置 artifact, 不再逐个等用户确认。
- 决定5: `proposal/design/specs/tasks` 全部采用“新增 optional backend”口径, 明确排除“替换 `FLUX.1-dev` 默认链路”。
- 决定6: `design/spec` 里把 `Kontext` 重点锚定到“待修 render + source real image”的双图语义, 因为这和当前仓库 pose-jitter / refine 数据流最契合。

## 遇到错误

- 暂无新错误。

## 状态

**目前在阶段2** - 已完成上下文和接口事实收集, 正在起草 `proposal`。

## [2026-03-31 16:58:42] [Session ID: codex-flux-kontext-change-20260331] [记录类型]: fast-forward artifact 已完成并通过验证

## 阶段

- [x] 阶段1: 确认当前 change 的 apply 依赖图
- [x] 阶段2: 生成 `proposal`
- [x] 阶段3: 生成 `design`
- [x] 阶段4: 生成 `specs`
- [x] 阶段5: 生成 `tasks`
- [x] 阶段6: 重新检查 `openspec status` 并交付

## 关键问题

1. 这次是否已经达到 apply-ready: 是。`openspec status --change add-optional-flux-kontext-refine` 显示 `Progress: 4/4 artifacts complete`。
2. 这组 artifact 是否通过 OpenSpec 校验: 是。`openspec validate add-optional-flux-kontext-refine` 返回 `is valid`。
3. 本次 artifact 最核心的边界是否已经锁住: 是。文档整体都明确 `Kontext` 是新增可选 backend, 默认 `flux` 不变, 不是替代现有 `FLUX.1-dev`。

## 做出的决定

- 决定7: capability 名采用 `optional-flux-kontext-refine`, 把“optional + kontext + refine”三层语义一次固定。
- 决定8: design 中明确接受 v1 的官方兼容优先路线, 不把“完全复制当前私有 `mask_scheduler/warp_*` 语义”当作首版前提。
- 决定9: tasks 中把工作切成 backend 接线、Kontext 实现、验证回归、文档说明四组, 便于后续直接 apply/实现。

## 遇到错误

- 暂无新错误。

## 状态

**目前已完成** - `add-optional-flux-kontext-refine` 的 `proposal/design/specs/tasks` 已全部创建并通过 `openspec validate`。
