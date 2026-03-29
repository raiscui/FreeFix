## Context

当前 refine 主链路已经具备这几个关键事实:

- `ours/refine_by_flux.py` 会先调用 `refiner.render(i)` 渲染当前高斯
- 渲染图会作为 `image=rgb_to_refine` 送入 Flux img2img
- Flux 生成结果会和同一轮的 `cam_param["c2w"] / cam_param["K"]` 一起进入 `refiner.refine(...)`

换句话说, 现在系统已经不是“拿文字 prompt 修图”那么简单。  
它本来就是一条“3D 渲染 -> 2D 生成 -> 回写 3D”的闭环。

这也是为什么“随机相机偏移 + 图生图”不是异构想法。  
真正的问题不在于能不能插进去, 而在于应该把它定义成什么:

- 是替换当前固定视角 refine 的主流程
- 还是作为一条受控 synthetic augmentation 分支

前一轮探索给出的结论很明确:

- 小幅 jitter 有机会带来更有价值的近邻视角监督
- 大幅 jitter 会把模块语义从 refinement 推向 novel-view hallucination bootstrapping
- 如果不把 refine source split 和 eval split 拆开, benchmark 很容易失真

所以这次 design 的重点, 不是“多做一点随机”。  
而是给这条分支建立安全边界。

## Goals / Non-Goals

**Goals:**

- 在不破坏当前 fixed refine 主链的前提下, 新增 `pose_jitter` refine 模式
- 让 pose jitter 的 base camera 来源可以和 eval split 解耦
- 为 pose jitter 提供受控的平移 / 旋转采样语义和硬边界
- 为越界 synthetic view 提供明确的回退策略
- 给出第一版小扰动实验的推荐口径

**Non-Goals:**

- 本次不把 refine 改造成大范围 novel-view generation 系统
- 本次不重写 Flux / SDXL pipeline 本身
- 本次不在第一版里引入复杂的内参随机扰动
- 本次不承诺“只要开了 pose jitter 就一定比 fixed 更好”
- 本次不允许通过训练增强去污染 benchmark 评测口径

## Decisions

### 决策1: 保留 fixed 主链, 将 pose jitter 作为显式可选模式

- 决定:
  - refine 新增 `refine_camera_mode`
  - 第一版至少支持:
    - `fixed`
    - `pose_jitter`
  - 默认仍然走 `fixed`
- 理由:
  - 当前 fixed 流程已经可用, 也是现有结果可复现的基线
  - pose jitter 是能力扩展, 不是对旧流程的否定
- 备选方案:
  - 直接用 pose jitter 替换当前 fixed render 逻辑
- 为什么不选:
  - 这样会把所有现有实验口径一起改掉
  - 一旦新分支有 hallucination 问题, 连基线都不剩

### 决策2: pose jitter 的 base camera 来源必须和 eval split 解耦

- 决定:
  - 新增 `refine_camera_source_split`
  - 它负责决定 pose jitter 围绕哪一组真实相机采样
  - 推荐第一版优先围绕 `train` 或专门的 refine split 工作
- 理由:
  - 当前 refine 本来就直接消费 split 样本
  - 如果继续围绕 eval / benchmark 视角近邻做训练增强, 评测解释力会明显下降
- 备选方案:
  - 沿用当前 `test_split` 语义, 让 pose jitter 也默认围绕 test 相机工作
- 为什么不选:
  - 太容易污染 benchmark
  - 后面即使结果更好, 也很难说清到底是模型更强, 还是评测口径更松

### 决策3: 第一版只做小幅 pose jitter, 并使用硬上限约束

- 决定:
  - 新增平移和旋转的采样尺度字段, 例如:
    - `pose_jitter_trans_sigma`
    - `pose_jitter_rot_sigma_deg`
  - 同时新增硬上限字段, 例如:
    - `pose_jitter_trans_max`
    - `pose_jitter_rot_max_deg`
  - 第一版的推荐值应明显偏保守
- 理由:
  - 小扰动更接近局部增广
  - 大扰动会把未观测区域暴露给 2D 扩散去脑补, 风险过高
- 备选方案:
  - 只提供 sigma, 不提供 clamp
- 为什么不选:
  - 只靠分布参数不够稳
  - 长尾样本一旦越界, 很容易把整轮 synthetic supervision 带偏

### 决策4: 第一版默认复用原始 `K`, 只扰动 `c2w`

- 决定:
  - pose jitter 第一版只改外参
  - 默认复用 base camera 的内参 `K`
- 理由:
  - 这是最贴近当前实现的数据契约
  - 也最容易解释“生成图应该回写到哪一个相机上”
- 备选方案:
  - 同时做视场变化或主点扰动
- 为什么不选:
  - 第一版复杂度不值得
  - 只改 `c2w` 已经足够验证“近邻 pose synthetic supervision”是否有价值

### 决策5: synthetic 相机必须有安全检查, 失败时允许回退

- 决定:
  - pose jitter 模式下, 系统在正式把 synthetic 视角送进 img2img 之前, 需要做基础安全检查
  - 第一版至少支持一种轻量过滤信号, 例如:
    - 渲染 alpha 覆盖率
    - 渲染有效区域比例
  - 若连续多次采样都不满足阈值, 系统可以:
    - 回退到 base camera
    - 或跳过该 synthetic 样本
- 理由:
  - 这条链路最危险的地方不是“生成得不好看”
  - 而是把明显越界的 hallucination 当真监督写回 3D
- 备选方案:
  - 不做过滤, 只靠小 jitter 默认值兜底
- 为什么不选:
  - 不够稳
  - 同样的 sigma 在不同场景尺度上不一定有同样的安全性

### 决策6: 生成图监督必须绑定采样后的相机, 不能偷回原固定视角

- 决定:
  - 一旦 synthetic 相机被接受, 后续生成图 supervision 必须使用采样后的 `c2w + K`
  - 不允许“用 jitter 相机渲染, 但回写时偷偷挂回原相机”
- 理由:
  - 否则 supervision 语义会前后不一致
  - 训练看到的图像内容和相机几何不匹配, 反而更容易破坏结果
- 备选方案:
  - 只把 jitter 结果当成 2D 参考图, 回写仍沿用 base camera
- 为什么不选:
  - 这会直接破坏现有 refine 的核心假设
  - 属于更危险的“看起来省事, 实际更错”

## Risks / Trade-offs

- [jitter 过小] → 增广收益可能不明显, 但这比一开始越界更可接受
- [jitter 过大] → 2D 扩散会在新显露区域编故事, 并把错误写回 3D
- [source split 选错] → benchmark 口径会被污染
- [只动 `c2w` 不动 `K`] → 表达范围有限, 但第一版更稳
- [安全过滤过严] → synthetic 样本命中率下降, 需要 fallback
- [安全过滤过松] → hallucination 会混进训练

## Migration Plan

1. 在 `exp_cfg/base.yaml` 中新增 refine camera mode、source split 和 jitter 参数语义。
2. 在 `recon/refiner.py` 中抽出 base camera 选取与 jitter 相机采样逻辑, 让 fixed / pose_jitter 共享同一套下游渲染接口。
3. 在 `ours/refine_by_flux.py` 和 `ours/refine_by_sdxl.py` 中接入新相机模式, 确保 synthetic supervise 使用采样后的相机参数。
4. 增加基础安全过滤和 fallback 逻辑, 避免明显越界样本直接进入监督。
5. 先跑小规模 smoke experiment, 再补推荐配置与使用文档。

回滚策略:

- 如果 pose jitter 分支表现不稳, 保留配置字段和采样骨架, 先回退默认值到 `fixed`
- 不回退 fixed 主链, 保证现有流程始终可用

## Open Questions

- 第一版安全过滤最值得优先落哪一个信号:
  - alpha 覆盖率
  - certainty 掩码面积
  - 邻近真实视角重投影差异
- 是否需要单独引入 `refine` 专用 split, 而不是只在 `train` 上采样
- 后续是否值得扩展到轻量 `K` 扰动, 还是继续坚持“只改外参”
