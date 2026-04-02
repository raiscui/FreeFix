## [2026-03-29 23:16:05] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] 主题: 若继续实现双图参考修复, 优先按两条路线推进

### 待后续处理事项
- 路线A: 正统长期方案
  - 为当前 Flux refine 引入 IP-Adapter 资产
  - 在配置里新增参考图来源与 scale
  - 保持 `image=待修图`, `ip_adapter_image=参考图`
  - 做小样本 smoke run, 重点检查 identity drift 和 geometry drift
- 路线B: 短期先能用方案
  - 不碰当前 Flux pipeline 资产
  - 先把参考图内容折进 prompt 或预处理阶段, 只做弱参考而不是严格双图条件
  - 明确它只是近似替代, 不是严格意义上的"A 修 B"
