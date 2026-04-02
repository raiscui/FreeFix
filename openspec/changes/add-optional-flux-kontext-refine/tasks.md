## 1. Backend 接线与配置

- [x] 1.1 在 `ours/run_fastgs_refine.py` 中新增 `kontext` backend 选项, 保持默认值仍为 `flux`。
- [x] 1.2 新增 Kontext 专属模型来源配置与解析逻辑, 例如 `kontext_model_path`, 并确保它与 `flux_model_path` 独立。
- [x] 1.3 更新帮助文本、配置注释或示例配置, 明确 `kontext` 是可选 backend, 不是默认替代项。

## 2. Kontext refine 实现

- [x] 2.1 新建 `ours/refine_by_kontext.py`, 复用当前 refine 的 CLI、resume、输出目录和 synthetic supervision 主循环。
- [x] 2.2 接入 `FluxKontextPipeline` / `FluxKontextInpaintPipeline` 的加载与 offload 流程, 让当前 render 图作为主编辑输入。
- [x] 2.3 在 source real image 可用时接入参考图输入, 并为掩码映射或无参考图场景提供明确 fallback。

## 3. 验证与回归保护

- [x] 3.1 扩展 `tests/test_run_fastgs_refine.py`, 覆盖 `kontext` backend 的参数解析和命令拼接。
- [x] 3.2 为 Kontext 模型来源解析、参考图 fallback 和关键输入映射补轻量单测或行为测试。
- [x] 3.3 跑至少一组 `--help` / dry-run / 轻量 smoke 验证, 确认新增 backend 不会破坏现有 `flux` / `sdxl` 入口。

## 4. 文档与使用建议

- [x] 4.1 为 `kontext` backend 补一条最小可执行示例, 包括 backend 选择、模型路径准备和推荐场景。
- [x] 4.2 在文档里明确记录 `kontext` 与现有 `flux` / `sdxl` 的差异, 特别是 reference-guided repair 与私有 `warp/mask` 语义差别。
