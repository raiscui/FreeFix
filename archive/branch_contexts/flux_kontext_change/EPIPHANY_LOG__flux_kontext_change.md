## [2026-03-31 16:59:21] [Session ID: codex-flux-kontext-change-20260331] 主题: Kontext 首版最大的风险不是模型接不进来, 而是接口语义并不等同于当前私有 refine 扩展

### 发现来源
- 在为 `add-optional-flux-kontext-refine` 编写 proposal / design / spec 时, 对照了:
  - 当前 `ours/refine_by_flux.py` / `ours/refine_by_sdxl.py` 的调用参数
  - 官方 `FluxKontextPipeline` / `FluxKontextInpaintPipeline` 的接口语义

### 核心问题
- 当前仓库的 `flux/sdxl` refine 调用已经依赖多项私有扩展:
  - `mask_scheduler`
  - `warp_image`
  - `warp_until`
  - `warp_mask`
- 官方 Kontext 路线更偏标准 image edit / inpaint 语义
- 这意味着“新增 Kontext backend”并不自动等于“行为和当前 flux/sdxl 完全一致”

### 为什么重要
- 如果后续实现阶段忽略这件事, 很容易把“新增 backend 的正常差异”误判成“现有 flux 回归”
- 也容易在设计上滑向一个更大的工程:
  - 不是接入新 backend
  - 而是再造一份私有 Kontext pipeline

### 未来风险
- 如果实现阶段执着于 1:1 复刻当前私有语义, 会明显拖慢落地速度
- 如果实现阶段完全不说明差异, 用户会误以为 `kontext` 与 `flux` 是可直接互换的 backend

### 当前结论
- 首版最合理的路径是:
  - 先保证 `kontext` 成为一个真正可用的 optional backend
  - 再逐步评估哪些私有语义值得继续迁移
- “兼容当前流程” 和 “复刻当前所有私有细节” 不是同一件事

### 后续讨论入口
- 后续真正开始实现 `ours/refine_by_kontext.py` 时, 先回看这条记录和 `design.md` 的决策4/风险部分
