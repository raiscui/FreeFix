## [2026-03-29 23:16:05] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] 主题: FLUX refine 的"接口预留"和"能力落地"必须分开判断

### 发现来源
- 在排查当前项目是否支持双图参考修复时发现

### 核心问题
- 自定义 `FluxPipeline` 代码里虽然有 `ip_adapter_image` 入口
- 但当前 refine 没接这条线, 当前本地 `FLUX.1-dev` 资产也没配 `image_encoder` / `feature_extractor`

### 为什么重要
- 这类问题最容易让人产生误判:
  - 看到接口, 误以为功能已经能跑
  - 看到模型名, 误以为所有官方扩展默认都已装齐

### 未来风险
- 后续如果直接在当前分支上盲加 `ip_adapter_image`, 很可能会在运行时才撞到模型组件缺失
- 如果跳过最小 smoke run, 很容易把"代码能调"误认为"效果可用"

### 当前结论
- 当前仓库不支持双图参考修复
- 官方正统扩展路线存在, 但需要额外模型资产和接线

### 后续讨论入口
- 下次若要真正实现这条能力, 先看:
  - [notes__flux_reference_refine.md](/root/autodl-tmp/home/rais/FreeFix/notes__flux_reference_refine.md)
  - [LATER_PLANS__flux_reference_refine.md](/root/autodl-tmp/home/rais/FreeFix/LATER_PLANS__flux_reference_refine.md)
