# Capability: Pose Jitter Refine

## Purpose

定义 FreeFix refine 如何在固定视角之外, 安全地使用现有相机附近的小幅 synthetic pose 采样来生成新的 img2img supervision, 同时避免 benchmark 污染和大范围 novel-view hallucination 被直接写回 3D。

## Requirements

### Requirement: Refine supports both fixed and pose-jitter camera modes

系统 SHALL 为 refine 提供显式的相机模式配置, 至少支持 `fixed` 和 `pose_jitter` 两种模式。

#### Scenario: Fixed mode preserves current behavior

- **WHEN** 用户未启用 `pose_jitter`, 或者明确选择 `fixed`
- **THEN** 系统 SHALL 继续沿用当前固定视角 refine 链路, 不改变现有 render -> img2img -> refine 的默认行为

#### Scenario: Pose-jitter mode samples a nearby synthetic camera before rendering

- **WHEN** 用户启用 `pose_jitter`
- **THEN** 系统 SHALL 在正式渲染 synthetic supervise 图像前, 先围绕 base camera 采样一个附近的新相机位姿

### Requirement: Pose-jitter source split is configurable and separate from evaluation semantics

系统 SHALL 允许用户显式配置 pose jitter 围绕哪一组真实相机采样, 且该配置不得隐式等同于 benchmark eval split。

#### Scenario: User chooses train cameras as the source of base poses

- **WHEN** 用户将 `refine_camera_source_split` 设为 `train`
- **THEN** 系统 SHALL 从训练相机集合中选择 base camera, 再围绕它进行 pose jitter 采样

#### Scenario: Evaluation split is not silently reused as the default synthetic source

- **WHEN** 用户启用了 `pose_jitter`
- **THEN** 系统 SHALL 不得在没有显式说明的情况下继续把 benchmark eval split 当作默认 synthetic refine 来源

### Requirement: Pose jitter remains bounded by explicit translation and rotation limits

系统 SHALL 同时支持 pose jitter 的采样尺度和硬上限语义, 并保证实际采样结果不会越过配置上限。

#### Scenario: Random sampling produces a large perturbation candidate

- **WHEN** pose jitter 的原始采样结果超过了配置的平移或旋转上限
- **THEN** 系统 SHALL 对该采样结果执行裁剪、重采样或拒绝, 直到最终扰动满足配置边界

#### Scenario: A conservative jitter profile is configured

- **WHEN** 用户使用小扰动配置
- **THEN** 系统 SHALL 只在 base camera 附近生成局部 synthetic view, 而不是跨到大范围 novel-view 区域

### Requirement: Synthetic supervision uses the sampled camera consistently

系统 SHALL 保证 synthetic supervise 图像与其绑定的相机参数一致。采样后的图像不得在回写时偷偷挂回原始 fixed camera。

#### Scenario: A synthetic image is accepted for refinement

- **WHEN** 某个 pose-jitter synthetic view 通过安全检查并进入 refine
- **THEN** 系统 SHALL 使用该 synthetic view 对应的 `c2w + K` 作为监督相机参数

#### Scenario: Base camera is only the sampling anchor

- **WHEN** pose jitter 基于某个真实相机生成了一个新视角
- **THEN** 系统 SHALL 将 base camera 仅视作采样锚点, 而不是最终 supervision 的相机标签

### Requirement: Unsafe synthetic views fall back instead of directly supervising hallucinations

系统 SHALL 在 synthetic 视角明显越界或可见区域不足时执行过滤与回退, 而不是把高风险样本直接写回高斯。

#### Scenario: Rendered synthetic view fails the safety check

- **WHEN** synthetic 相机的渲染结果不满足最低安全条件, 例如有效覆盖率过低
- **THEN** 系统 SHALL 重采样、回退到 base camera, 或跳过该样本, 而不是直接进入 img2img supervision

#### Scenario: Repeated sampling still produces unsafe candidates

- **WHEN** pose jitter 连续多次采样都无法得到安全 synthetic view
- **THEN** 系统 SHALL 使用可解释的 fallback 行为结束本轮, 并留下日志说明发生了回退

### Requirement: The project documents a small-jitter-first validation recipe

项目 SHALL 提供一套面向 pose-jitter refine 的最小验证建议, 明确推荐先从小扰动开始, 并提醒 benchmark split 与 hallucination 风险。

#### Scenario: User wants to try pose-jitter refine for the first time

- **WHEN** 用户第一次启用 `pose_jitter`
- **THEN** 项目 SHALL 提供可直接执行的小扰动实验建议, 包括推荐起步参数、观察指标和风险提醒
