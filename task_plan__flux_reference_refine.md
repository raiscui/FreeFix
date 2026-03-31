# 任务计划: Flux refine 双图参考修复能力评估

## [2026-03-29 23:16:05] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] [记录类型]: 初始化支线计划

## 目标

确认当前项目里的 Flux refine 是否支持"参考图 A + 待修图 B"双图输入, 并给出两条可落地的改造路线:
- 方案1: 不惜代价, 结构最正确的长期方案
- 方案2: 先能用, 后面再优雅的短路径方案

## 阶段

- [x] 阶段1: 读取现有上下文与代码入口
- [x] 阶段2: 验证当前 Flux refine 实际输入形态
- [x] 阶段3: 设计双图改造路线
- [x] 阶段4: 向用户交付路线建议与下一步

## 关键问题

1. 当前项目的 refine 调用里, 是否真的存在第二张参考图输入:
   - 当前结论: 没有。主调用只传了 `image=rgb_to_refine`, `warp_image=rgb_to_refine`, `mask=masks`。
2. 底层自定义 `FluxPipeline` 是否预留了图像条件入口:
   - 当前结论: 有。存在 `ip_adapter_image` / `ip_adapter_image_embeds` 入口, 但当前 refine 没有使用。
3. 当前本地加载的 `FLUX.1-dev` 模型资产, 是否已经包含运行这条参考图入口所需的视觉编码组件:
   - 当前结论: 没有。`model_index.json` 中未声明 `image_encoder` 和 `feature_extractor`。

## 做出的决定

- 决定1: 这次先不改代码, 先把"当前做不到"和"理论上可扩展"这两层边界说清楚。
- 决定2: 给用户两条路线, 不把"接 IP-Adapter"和"换模型链路"混成一条模糊建议。
- 决定3: 输出时严格区分:
  - 现象: 当前 refine 只吃一张图
  - 假设: 可以用 IP-Adapter 把参考图接进来
  - 结论: 当前仓库和当前本地权重组合下, 双图参考修复没有打通

## 遇到错误

- 暂无代码执行错误。

## 状态

**目前已完成** - 当前能力边界、官方扩展路径和两套改造方案都已整理完毕, 可直接交付给用户做实施决策。

## [2026-03-30 01:39:39] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] [记录类型]: 用户澄清真实目标, 重新收口探索口径

## 目标

澄清用户真正需要的不是泛化的"双图编辑", 而是:
- 图A: 真实训练原图, 作为内容证据
- 图B: 以图A相机为锚点做 pose jitter 后的 render, 作为待修对象
- 目标: 让 Flux 参照图A, 修补图B中因视角暴露而出现的不完整或不合理内容

## 阶段

- [x] 阶段1: 对齐用户真实需求语义
- [x] 阶段2: 核对现有数据流里两张图是否天然共存
- [x] 阶段3: 评估 prompt 在这条链路中的职责边界
- [x] 阶段4: 交付更精确的设计建议

## 关键问题

1. 当前 pose-jitter 路径里, 真实训练图和 jitter render 是否本来就在同一轮上下文里:
   - 当前结论: 是。`refiner.render(...)` 在 `pose_jitter` 分支里先取到源样本 `data`, 再基于它采样 jitter 相机并渲染 `colors`。
2. 当前 Flux 调用缺的到底是什么:
   - 当前结论: 不是"第二张图从哪里找", 而是"如何把源样本 `data[\"image\"]` 作为 reference condition 继续传给 Flux"。
3. prompt 能不能单独承担"把桌子补完整"这件事:
   - 当前结论: 不够。prompt 适合表达修复意图和保守约束, 但训练原图里的桌子细节本身应该由 reference image 承担证据角色。

## 做出的决定

- 决定4: 之后讨论这件事时, 统一把它叫做"reference-guided pose-jitter repair", 避免和普通双图风格编辑混淆。
- 决定5: 设计上把 prompt 定义为"修复规则", 把训练原图定义为"内容证据", 两者职责分开。
- 决定6: 这项需求更像对现有 `add-pose-jitter-refine` 的语义增强, 而不是完全独立的新世界观。

## 状态

**目前已完成** - 已根据用户新澄清的目标重新收口设计口径, 可以给出更贴近实际需求的探索结论。

## [2026-03-30 01:45:38] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] [记录类型]: 判断 OpenSpec 应以新 change 形式承接

## 关键问题

1. 这项需求更适合直接回填到现有 `add-pose-jitter-refine` 吗:
   - 当前结论: 不太适合。现有 design 的 non-goal 明确写了"本次不重写 Flux / SDXL pipeline 本身", 而 reference-guided repair 会直接碰到 pipeline 条件输入语义。
2. 更合适的 OpenSpec 落法是什么:
   - 当前结论: 新开一个 change, 修改既有 `pose-jitter-refine` capability 的语义, 比硬改旧 change 更清晰。

## 做出的决定

- 决定7: 在探索表达上, 推荐把这项需求表述为:
  - 一个新的 change
  - 修改现有 `pose-jitter-refine` capability
  - 新增 reference-guided repair 的 requirement / scenarios

## 状态

**目前已完成** - 已明确 OpenSpec 承接方式, 接下来可以直接产出 proposal / design / spec 草案语言。
