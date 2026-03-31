# Capability: Optional Flux Kontext Refine

## Purpose

定义 FreeFix 如何把 `FLUX.1-Kontext-dev` 作为一个新的、可选的 refine backend 接入当前 `flux` / `sdxl` 体系, 同时保持现有默认行为不变, 并在 source real image 可用时支持 reference-guided repair。

## ADDED Requirements

### Requirement: Refine backend selection supports kontext alongside flux and sdxl

系统 SHALL 提供 `kontext` 作为新的 refine backend 选择, 且不得通过引入 `kontext` 改变当前 `flux` 默认行为。

#### Scenario: User selects kontext in the wrapper

- **WHEN** 用户在 wrapper 中显式传入 `--refine-backend kontext`
- **THEN** 系统 SHALL 路由到独立的 Kontext refine 入口, 而不是复用 `ours.refine_by_flux`

#### Scenario: Existing commands omit the backend argument

- **WHEN** 用户继续沿用现有命令, 没有显式选择 `kontext`
- **THEN** 系统 SHALL 保持当前默认 backend 和现有 `flux` / `sdxl` 行为不变

### Requirement: Kontext backend preserves the existing refine runtime contract

系统 SHALL 让 `kontext` backend 复用当前 refine 的恢复、输出和 synthetic supervision 契约, 而不是创建另一套不兼容工作流。

#### Scenario: Kontext backend runs a refine job

- **WHEN** 用户使用 `kontext` backend 启动 refine
- **THEN** 系统 SHALL 继续产出与现有 backend 一致的恢复和输出工件, 包括 `before_refine`、`after_refine`、resume state 与 generated camera 记录

#### Scenario: Wrapper chains bridge, refine, and export with kontext

- **WHEN** 用户通过 `ours/run_fastgs_refine.py` 选择 `kontext`
- **THEN** 系统 SHALL 继续遵守当前 bridge -> refine -> export 的 orchestration 语义, 而不是要求一套新的下游调用方式

### Requirement: Kontext model source is configured independently from FLUX.1-dev

系统 SHALL 为 `FLUX.1-Kontext-dev` 提供独立的模型来源配置, 并与现有 `flux_model_path` 语义隔离。

#### Scenario: User provides a local Kontext model path

- **WHEN** 用户为 Kontext backend 提供本地模型目录
- **THEN** 系统 SHALL 优先使用该目录加载 `FLUX.1-Kontext-dev`, 并在目录不存在或缺少必要文件时给出明确错误

#### Scenario: Flux and Kontext are both available locally

- **WHEN** 用户同时保留 `FLUX.1-dev` 和 `FLUX.1-Kontext-dev` 的本地快照
- **THEN** 系统 SHALL 分别使用各自的配置或默认来源, 不得把两者混成同一个路径真相源

### Requirement: Kontext uses the current render as the primary edit image

系统 SHALL 把当前 render 图视为 Kontext refine 的主编辑对象, 而不是让参考图覆盖这一语义。

#### Scenario: Kontext processes a synthetic or fixed render

- **WHEN** 当前 refine 轮次已经生成了待修的 render 图
- **THEN** 系统 SHALL 把这张 render 图作为 Kontext 的主输入图像

#### Scenario: The backend prepares supervision after editing

- **WHEN** Kontext 完成当前轮次编辑
- **THEN** 系统 SHALL 继续把编辑结果绑定回当前 render 对应的 supervision 相机参数, 而不是改写成另一张参考图的相机标签

### Requirement: Kontext can use source real image as an optional reference input

系统 SHALL 在 source real image 可用时, 支持把它作为独立的参考图输入给 Kontext backend, 尤其是在 pose-jitter 这类 source anchor 明确的场景中。

#### Scenario: Pose-jitter plan exposes a source real image

- **WHEN** 当前 synthetic plan 对应的 source real image 可从数据契约中取得
- **THEN** 系统 SHALL 能把该 source real image 作为独立参考输入传给 Kontext, 而不是复用主输入槽位

#### Scenario: Source real image is unavailable

- **WHEN** 当前轮次没有可用的 source real image
- **THEN** 系统 SHALL 退化为单图编辑路径或其他已文档化的 fallback, 而不是直接终止整个 refine 作业

### Requirement: Kontext accepts a documented, compatible edit-mask path

系统 SHALL 为 Kontext backend 提供一条清晰、可解释的掩码接线方式, 即使它与当前私有 `flux/sdxl` 扩展并不完全等价。

#### Scenario: A compatible edit mask can be derived

- **WHEN** 当前 refine 轮次能够从现有 mask / alpha 数据导出一张兼容 Kontext 的编辑掩码
- **THEN** 系统 SHALL 把该掩码送进 Kontext 的编辑流程

#### Scenario: Existing private mask semantics cannot be mapped one-to-one

- **WHEN** 当前 `mask_scheduler` 或 `warp_*` 语义无法直接映射到官方 Kontext 接口
- **THEN** 系统 SHALL 使用已文档化的保守映射或 fallback 行为, 而不是静默假装语义完全一致

### Requirement: The project documents how to choose and use the kontext backend

项目 SHALL 提供对 `kontext` backend 的使用说明, 明确它与 `flux` / `sdxl` 的关系、前置依赖和预期差异。

#### Scenario: User wants to try kontext for the first time

- **WHEN** 用户第一次选择 `kontext`
- **THEN** 项目 SHALL 提供至少一条可执行的命令或配置示例, 说明如何选择 backend、准备模型以及理解它与 `flux` / `sdxl` 的区别

#### Scenario: User compares existing backends with kontext

- **WHEN** 用户查阅 backend 说明
- **THEN** 文档 SHALL 明确 `kontext` 是新增可选能力, 不是对现有 `flux` 默认链路的替代
