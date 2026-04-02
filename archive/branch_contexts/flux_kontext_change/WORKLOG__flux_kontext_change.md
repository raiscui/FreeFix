## [2026-03-31 16:50:03] [Session ID: codex-flux-kontext-change-20260331] 任务名称: 创建可选 FLUX.1-Kontext-dev 的 OpenSpec change 骨架

### 任务内容
- 创建新的 OpenSpec change:
  - `add-optional-flux-kontext-refine`
- 明确这次变更的口径是“新增可选路径”, 不是“替代现有 `FLUX.1-dev`”
- 取回当前 change 的 artifact 状态与首个 `proposal` 模板

### 完成过程
- 先回读项目上下文文件与 `EXPERIENCE.md`, 确认当前仓库已经在使用 `openspec/changes/` 工作流
- 根据用户补充“类似 `sdxl/flux`, 而不是代替”, 将 change 名定为 `add-optional-flux-kontext-refine`
- 执行 `openspec new change add-optional-flux-kontext-refine`, 成功创建 `spec-driven` change 骨架
- 执行 `openspec status --change add-optional-flux-kontext-refine`, 确认当前是 `0/4 artifacts complete`, 第一份 ready artifact 为 `proposal`
- 执行 `openspec instructions proposal --change add-optional-flux-kontext-refine`, 取回 `proposal.md` 的结构说明与模板
- 额外检查 `openspec/specs/`, 确认当前仓库还没有主规格目录, 因此 proposal 里更适合优先从 `New Capabilities` 起步

### 总结感悟
- 对这类“新增但不替代”的需求, change 名里保留 `optional` 很重要, 能防止后续 proposal/design 口径跑偏
- 当前仓库的 OpenSpec 还主要停留在 `changes/` 层, proposal 里的 capability 约束会比平时更关键
- 下一步最自然的延续, 就是直接起草 `proposal.md`

## [2026-03-31 16:58:42] [Session ID: codex-flux-kontext-change-20260331] 任务名称: fast-forward 完成 `add-optional-flux-kontext-refine` 全部 artifact

### 任务内容
- 一次性完成 `proposal`、`design`、`specs`、`tasks`
- 把需求口径固定为“新增可选 `Kontext` backend, 与 `flux/sdxl` 并列, 不替代现有 `flux`”
- 用 OpenSpec 状态和校验命令确认 change 已到 apply-ready

### 完成过程
- 先读取 `openspec status --change ... --json`, 确认 `applyRequires` 最终要求 `tasks`
- 再读取 `openspec instructions proposal/design/specs/tasks --json`, 按 schema 模板逐份生成 artifact
- 结合当前仓库代码结构补齐实现边界:
  - `ours/run_fastgs_refine.py` 当前只有 `flux/sdxl`
  - `ours/refine_by_flux.py` 与 `ours/refine_by_sdxl.py` 已经形成并列入口
  - `recon/refiner.py` / `recon/datasets/colmap.py` 已经能提供 source real image 语义
- 生成:
  - `proposal.md`
  - `design.md`
  - `specs/optional-flux-kontext-refine/spec.md`
  - `tasks.md`
- 最后执行:
  - `openspec status --change add-optional-flux-kontext-refine`
  - `openspec validate add-optional-flux-kontext-refine`
  - 两者都通过

### 总结感悟
- 这次最重要的不是“把 Kontext 塞进来”, 而是把“新增 optional backend”与“替换现有 flux”明确切开
- 只要 runtime contract 继续复用当前 refine 闭环, 新 backend 的引入成本和验证成本都会小很多
- 现在这条 change 已经具备直接进入 apply / implementation 的条件
