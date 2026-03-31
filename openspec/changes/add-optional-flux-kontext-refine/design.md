## Context

当前仓库已经有两条并列的 refine 入口:

- `ours/refine_by_flux.py`
- `ours/refine_by_sdxl.py`

两者都遵守同一条大致的数据闭环:

- `recon/refiner.py` 先按当前相机或 synthetic plan 渲染一张图
- 这张 render 图作为待修输入送进 2D diffusion backend
- 生成结果再和对应的 `c2w + K` 一起回写到 `refiner.refine(...)`

在 orchestration 层, `ours/run_fastgs_refine.py` 当前只接受 `flux` 和 `sdxl` 两个 backend, 默认仍是 `flux`。  
这说明项目已经具备“多 backend 并列接入”的结构, 但目前还没有 `Kontext` 这第三条分支。

另一方面, 当前项目并不是只有“单图 prompt 修图”这么简单。

- `recon/refiner.py` 的 pose-jitter 路径已经知道 synthetic view 对应的 source camera
- `recon/datasets/colmap.py` 的样本契约本身就带着 `image`、`image_path`、`image_name`
- 这意味着系统天然就能区分:
  - 当前待修的 render 图
  - source real image

这正是 `FLUX.1-Kontext-dev` 有价值的地方。  
它不该被硬塞成“替代 `FLUX.1-dev` 的新默认权重”, 而更适合作为一条单独的、以图像编辑和 reference-guided repair 为强项的可选 backend。

## Goals / Non-Goals

**Goals:**

- 为项目新增 `kontext` refine backend, 与 `flux` / `sdxl` 并列存在。
- 保持当前 `flux` 默认行为和已有实验口径不变。
- 让 `Kontext` backend 复用现有 refine 的 resume、输出目录、synthetic supervision 与 wrapper 入口。
- 在 source real image 可用时, 支持把它作为 `Kontext` 的参考图输入, 而不是挤占当前 render 图的主输入语义。
- 给模型来源、配置项、测试和使用文档建立清晰约束。

**Non-Goals:**

- 本次不把 `FLUX.1-Kontext-dev` 设成新的默认 backend。
- 本次不删除或弱化现有 `flux` / `sdxl` 路径。
- 本次不承诺让 `Kontext` 完全复刻当前自定义 `flux/sdxl` pipeline 的私有 `mask_scheduler` / `warp_*` 行为。
- 本次不顺手重写 `recon/refiner.py` 的相机采样逻辑。
- 本次不把“reference-guided repair”扩展成任意多参考图、多风格控制系统。

## Decisions

### 决策1: 新增独立 `ours/refine_by_kontext.py`, 不把 `Kontext` 混进现有 `flux` 模块

- 决定:
  - 新增独立入口 `ours/refine_by_kontext.py`
  - 它沿用现有 CLI 约定, 与 `ours.refine_by_flux` / `ours.refine_by_sdxl` 保持同级关系
- 理由:
  - 用户明确要求是“类似 `sdxl/flux`, 而不是代替”
  - `Kontext` 的 pipeline 类型、输入语义和最佳使用方式都不同, 硬塞进 `refine_by_flux.py` 只会把边界搞混
- 备选方案:
  - 在 `ours/refine_by_flux.py` 内部再加一个 `model_variant=kontext`
- 为什么不选:
  - 会让 `flux` 与 `kontext` 的模型来源、调用参数和行为差异全部堆在一处
  - 后续维护和回归分析都会更乱

### 决策2: orchestration 层显式增加 `kontext` backend, 但默认值仍保持 `flux`

- 决定:
  - `ours/run_fastgs_refine.py` 的 `--refine-backend` 选择扩展为:
    - `flux`
    - `sdxl`
    - `kontext`
  - 默认值继续保持 `flux`
- 理由:
  - 这样用户能以最小心智负担试用新 backend
  - 同时不会影响现有脚本、实验配置和文档习惯
- 备选方案:
  - 把默认值直接改成 `kontext`
- 为什么不选:
  - 用户已经明确说明这不是替代
  - 改默认值会污染现有实验与 rerun 口径

### 决策3: 模型来源使用独立的 `kontext_model_path` 语义, 不复用 `flux_model_path`

- 决定:
  - `Kontext` backend 使用自己的模型路径配置, 例如 `kontext_model_path`
  - 若命中本地目录, 则按本地快照加载; 未提供时再走默认 repo id
  - `flux_model_path` 继续只服务 `FLUX.1-dev`
- 理由:
  - 这两份权重不是同一种 pipeline 资产
  - 混用一个路径键会制造“看起来能共用, 实际一加载就错”的灰色地带
- 备选方案:
  - 让 `kontext` 继续复用 `flux_model_path`
- 为什么不选:
  - 会把两种模型的真相源混成一处
  - 也不利于错误诊断和缓存管理

### 决策4: v1 优先采用官方 Kontext pipeline 兼容路径, 而不是把现有私有扩散扩展全部搬过去

- 决定:
  - v1 的 `Kontext` backend 优先围绕官方 `FluxKontextPipeline` / `FluxKontextInpaintPipeline` 组织
  - 若当前 refine 提供了可兼容的 edit mask, 则优先走 inpaint/edit 路径
  - 若某些现有私有参数语义无法直接映射, v1 允许采用更保守、更官方兼容的行为
- 理由:
  - `Kontext` 的价值首先在于模型能力本身, 不是先复制一遍当前私有 pipeline 魔改
  - 先跑通“可用且可解释”的版本, 比一上来追求行为完全等价更稳
- 备选方案:
  - 先重写一份自定义 `kontext_pipeline.py`, 把 `mask_scheduler` / `warp_*` 全部照搬
- 为什么不选:
  - 工作量和风险都明显更高
  - 也会把 change 的目标从“新增 optional backend”拖成“再造一条私有 pipeline”

### 决策5: `Kontext` 的主输入和参考输入必须分角色, 不得复用同一个槽位硬糊过去

- 决定:
  - 当前 render 图继续扮演“待修图”的主输入角色
  - source real image 可用时, 作为独立的参考图输入
  - source real image 不可用时, backend 允许退化成单图编辑路径, 而不是直接失败
- 理由:
  - 当前项目真正需要的不是普通风格迁移
  - 而是“拿真实源图作为证据, 修补 jitter render 里不合理的局部”
- 备选方案:
  - 直接把 source real image 覆盖到主输入槽位, 让 render 图退到 prompt 或别的临时参数里
- 为什么不选:
  - 这样会破坏当前 refine 的主语义
  - 也会让“到底修的是哪张图”变得不清楚

### 决策6: 保持现有输出 / resume / wrapper 契约不变, 让 `Kontext` 看起来像“新增 backend”, 而不是“新增工作流”

- 决定:
  - `Kontext` backend 继续沿用当前的:
    - `before_refine/after_refine`
    - `refine/generated_cams.jsonl`
    - `refine_resume_state.json`
    - rolling checkpoint
  - `ours/run_fastgs_refine.py` 后续 bridge / export 路径不因 backend 改变
- 理由:
  - 这是把新 backend 控制在最小影响面的关键
  - 也能复用现有验证和排障资产
- 备选方案:
  - 给 `Kontext` 单独创造另一套输出目录和恢复协议
- 为什么不选:
  - 会让 backend 扩展演变成流程分叉
  - 不利于对比不同 backend 的真实差异

## Risks / Trade-offs

- [官方 Kontext 接口与当前私有 `flux/sdxl` 扩展并不完全同构] -> v1 接受更保守的映射方式, 明确记录哪些私有语义暂未等价迁移。
- [`FLUX.1-Kontext-dev` 权重获取和本地缓存路径可能与现有 `FLUX.1-dev` 不同] -> 用独立 `kontext_model_path` 和清晰报错隔离问题面。
- [pose-jitter 下的 source real image 并非所有数据路径都稳定可用] -> 明确 fallback 到单图编辑, 不把“参考图缺失”升级成整个 refine 失败。
- [backend 数量增加, 未来测试矩阵会膨胀] -> 复用现有 wrapper / resume / output 契约, 把新增测试尽量集中在 backend 选择和 Kontext 专属输入映射。
- [v1 若不复刻 `mask_scheduler` / `warp_*`, 编辑局部性可能与当前 `flux` 不完全一致] -> 文档里明确这是“新增可选 backend”的行为差异, 而不是“现有 flux 回归”。

## Migration Plan

1. 为 wrapper 和独立 refine 命令新增 `kontext` backend 选择, 保持默认仍为 `flux`。
2. 新建 `ours/refine_by_kontext.py`, 复用当前 refine loop、resume、输出与 synthetic supervision 契约。
3. 为 `Kontext` backend 增加独立模型来源解析与配置字段, 避免和 `flux_model_path` 混用。
4. 接入官方 Kontext pipeline 的主输入 / 参考输入 / 掩码映射, 先打通 v1 行为。
5. 为 wrapper、配置解析、source-image reference fallback 和 CLI 帮助补测试与文档。

回滚策略:

- 如 `Kontext` backend 在实现或验证阶段表现不稳定, 直接撤回 `kontext` backend 入口与对应配置字段
- `flux` / `sdxl` 默认链路与现有配置不应受到任何影响

## Open Questions

- v1 最稳的 Kontext 接线应优先落在哪个官方 pipeline:
  - `FluxKontextPipeline`
  - `FluxKontextInpaintPipeline`
  - 还是两者按掩码可用性做分流
- 当前 refine 里的多掩码语义, v1 是否应先保守折叠成一张 union mask
- 是否需要单独的 `kontext_prompt` / `kontext_negative_prompt`, 还是先复用当前 `prompt` / `negative_prompt`
- `FLUX.1-Kontext-dev` 在本项目机器上的最佳本地缓存来源, 是否沿用现有 Flux 一样的本地快照分发方式
