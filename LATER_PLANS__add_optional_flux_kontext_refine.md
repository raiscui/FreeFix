## [2026-04-01 11:16:55] [Session ID: session-20260401T110504Z-113863] 主题: Kontext v2 可继续补更细的语义对齐

### 待后续处理事项
- 在真实 `FLUX.1-Kontext-dev` 权重下补一轮 GPU smoke, 观察 `edit_pipe.components -> inpaint_pipe` 共享组件在大模型和 offload 模式下的稳定性
- 评估是否需要为 `kontext` 单独补更细的 prompt / negative_prompt / mask threshold 配置, 避免长期复用主链默认值
- 如果后续确实需要更贴近当前私有 `flux/sdxl` 行为, 再评估:
  - 更细的 mask 映射
  - 是否引入局部 warp 近似
  - 是否接入官方支持之外的 reference 条件能力

## [2026-04-01 15:58:40] [Session ID: omx-1775055181169-iytve2] 主题: 压缩 Kontext 自动 prompt, 避免 CLIP 77 token 截断

### 待后续处理事项
- 本轮 3 图 preview 运行时已观察到动态告警:
  - `Token indices sequence length is longer than the specified maximum sequence length for this model (120 > 77)`
  - reference 说明尾部被截断
- 这说明当前自动 prompt 语义虽正确, 但文案过长
- 下一轮建议:
  - 把 repair clause 与 reference clause 压缩成更短版本
  - 目标优先控制在 CLIP 77 token 上限内
  - 压缩后再跑一轮 3 图 preview 对照
