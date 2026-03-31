## Why

当前 FreeFix 的 refine 后端只有 `flux` 和 `sdxl` 两条路径, 其中默认主链仍围绕 `FLUX.1-dev` 的自定义 pipeline 展开。  
这条链已经可用, 但它并不等价于 `FLUX.1-Kontext-dev` 这类以图像编辑、一致性保持和多轮改图为核心设计目标的模型, 所以更合理的方向不是“替换现有 flux”, 而是“新增一个可选的 Kontext backend”, 让项目可以在不破坏现有实验口径的前提下扩展能力边界。

## What Changes

- 新增第三种 refine backend: `kontext`, 与现有 `flux` / `sdxl` 并列存在。
- 为 `FLUX.1-Kontext-dev` 新增独立的 refine 入口、模型来源解析和运行时配置, 不复用或替换当前 `FLUX.1-dev` 主链。
- 让 Kontext backend 复用当前 refine 的 render / resume / synthetic supervision 闭环, 保持输出目录和恢复语义一致。
- 在 source real image 可用时, 允许 Kontext backend 把“当前 render 图”与“源真实图”分成不同输入角色, 服务 reference-guided repair 场景。
- 扩展 wrapper、配置说明和测试, 让 `run_fastgs_refine` 与独立 refine 命令都能显式选择 `kontext`。

## Capabilities

### New Capabilities

- `optional-flux-kontext-refine`: 定义 FreeFix 如何把 `FLUX.1-Kontext-dev` 作为可选 refine backend 接入现有 `flux` / `sdxl` 体系, 同时保持旧后端与默认行为不变。

### Modified Capabilities

- 无

## Impact

- 受影响代码:
  - `ours/run_fastgs_refine.py`
  - 新增 `ours/refine_by_kontext.py`
  - 可能抽取或复用 `ours/refine_pipeline_runtime.py` 等公共运行时辅助
  - 可能补充 `exp_cfg/base.yaml` 与相关实验配置
  - `tests/test_run_fastgs_refine.py` 及 Kontext 相关测试
- 受影响系统:
  - refine backend 选择语义
  - 模型本地路径 / 远端来源解析
  - pose-jitter 场景下的 source image -> reference image 接线
  - 文档中的运行示例与依赖说明
- 额外依赖与约束:
  - `diffusers` 需要支持 `FluxKontextPipeline` / `FluxKontextInpaintPipeline`
  - `black-forest-labs/FLUX.1-Kontext-dev` 权重来源与本地缓存路径需要明确
