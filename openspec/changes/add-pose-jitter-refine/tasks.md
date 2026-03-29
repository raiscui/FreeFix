## 1. 配置与语义

- [x] 1.1 在 `exp_cfg/base.yaml` 中新增 refine camera mode、source split 和 pose jitter 边界配置。
- [x] 1.2 明确 `fixed` 与 `pose_jitter` 的默认行为, 保证旧配置不改也能维持当前流程。
- [x] 1.3 为新配置补说明, 明确 benchmark split 不应直接作为默认 synthetic refine 来源。

## 2. 相机采样与渲染接入

- [x] 2.1 在 `recon/refiner.py` 中抽出 base camera 选择逻辑, 让 pose jitter 可以围绕指定 split 的相机工作。
- [x] 2.2 实现受控的平移 / 旋转采样, 并强制遵守配置的硬上限。
- [x] 2.3 确保 sampled `c2w + K` 能一路传到 render、img2img 和 `refiner.refine(...)` 的 synthetic supervision。

## 3. 安全过滤与回退

- [x] 3.1 为 synthetic 相机增加至少一种轻量安全检查, 避免明显越界样本直接进入监督。
- [x] 3.2 在采样失败或连续命中过滤阈值时, 回退到 base camera 或安全跳过该 synthetic 样本。
- [x] 3.3 为采样、过滤和 fallback 补日志, 方便后续分析 hallucination 风险。

## 4. 验证与文档

- [x] 4.1 为配置解析、采样边界和 fallback 逻辑补单测或轻量行为测试。
- [x] 4.2 跑一组小规模 pose jitter smoke refine, 重点检查多视角一致性和遮挡边界是否变差。
- [x] 4.3 更新使用文档或命令示例, 明确推荐的小扰动起步值、风险边界和 benchmark 注意事项。
