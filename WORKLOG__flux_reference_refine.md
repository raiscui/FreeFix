## [2026-03-29 23:16:05] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] 任务名称: 评估 Flux refine 的双图参考修复能力并整理改造路线

### 任务内容
- 核对当前项目里的 Flux refine 是否支持"参考图 A + 待修图 B"
- 区分当前仓库能力边界、底层 pipeline 扩展入口和本地模型资产限制
- 给出长期正确方案和短期先能用方案

### 完成过程
- 读取 [ours/refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py), 确认当前 refine 调用只传一张待修图
- 读取 [ours/pipelines/flux_pipeline.py](/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py), 确认底层预留了 `ip_adapter_image` 一类额外图像条件入口
- 检查本地 [/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev/model_index.json](/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev/model_index.json), 确认当前模型资产没有 `image_encoder` 和 `feature_extractor`
- 再用 Context7 核对 `diffusers` 官方文档, 确认 FLUX 的正统双图条件路线是 `load_ip_adapter(...) + ip_adapter_image=...`

### 总结感悟
- "代码里留了参数"不等于"当前项目已经具备这项能力"
- 对这个项目来说, 最自然的双图语义应该是:
  - `image`: 待修图 B
  - `ip_adapter_image`: 参考图 A
- 如果不愿意引入新的参考图适配器权重, 那就不该假装当前这条 Flux refine 能优雅支持双图参考修复
