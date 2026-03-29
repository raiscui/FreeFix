## Why

当前 FreeFix 的 Flux refine 已经是一条明确的闭环:

- 先用当前高斯和当前相机渲染一张图
- 再把这张图送进 Flux 做 img2img
- 最后把生成图和同一份 `c2w + K` 作为 synthetic supervision 写回高斯

这条链路已经能修局部画面问题。  
但它有一个明显边界: 监督基本只围绕固定视角展开。

从我们刚做完的探索看, 如果只在现有相机附近做很小的 pose jitter, 再渲染、再图生图、再回写, 这条路线是有希望给 refine 增加“近邻视角监督”的。它更像一种受控增广, 而不是完全换一套训练逻辑。

问题也很明确。

- 如果 jitter 太大, Flux 会开始替 3D 几何脑补未观测区域
- 这些 hallucination 一样会被当成监督写回高斯
- 如果继续围绕 `test_split` 近邻去训练, benchmark 口径还会被污染

所以这次 change 的目标, 不是简单“把相机改成随机”。  
而是把“受控的小幅 pose jitter synthetic refine”正式定义清楚, 给它边界、默认行为、回退策略和验证口径。

## What Changes

- 为 refine 新增显式的相机模式语义, 至少区分 `fixed` 和 `pose_jitter`
- 为 `pose_jitter` 模式新增 base camera 来源配置, 让 synthetic refine source split 能和 eval split 解耦
- 为 pose jitter 新增受控扰动参数, 包括平移 / 旋转的采样尺度与硬上限
- 为 synthetic view 增加安全回退语义, 避免明显越界的视角直接进入监督
- 提供一套适合第一版验证的“小扰动优先”配置和实验建议

## Capabilities

### New Capabilities

- `pose-jitter-refine`: 定义 FreeFix refine 在固定视角之外, 如何安全地采样附近 synthetic 相机、生成 synthetic supervision, 并把它写回当前高斯

### Modified Capabilities

- 无

## Impact

- 受影响代码:
  - `ours/refine_by_flux.py`
  - `ours/refine_by_sdxl.py`
  - `recon/refiner.py`
  - `exp_cfg/base.yaml`
  - 可能涉及新增 refine 相关测试
- 受影响行为:
  - refine 的相机来源
  - synthetic supervision 的相机绑定方式
  - benchmark / eval 与 refine source split 的关系
  - 视角越界时的回退与日志
- 需要补充:
  - pose jitter 采样边界测试
  - 小范围 smoke refine 实验
  - 配置说明和使用警告
