## [2026-03-29 23:16:05] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] 笔记: 当前 Flux refine 的双图输入能力事实核对

## 来源

### 来源1: [ours/refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)

- 位置:
  - [ours/refine_by_flux.py:193](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py#L193C1)
  - [ours/refine_by_flux.py:223](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py#L223C1)
- 要点:
  - refine 循环里先从 `refiner.render(...)` 得到一张当前视角渲染图 `rgb`
  - 然后把它转成 `rgb_to_refine`
  - Flux 调用时只传了:
    - `image=rgb_to_refine`
    - `mask=masks`
    - `warp_image=rgb_to_refine`
    - `warp_mask=warp_mask`
  - 这里没有独立的 `reference_image` / `ref_image` / `ip_adapter_image` 传入

### 来源2: [ours/pipelines/flux_pipeline.py](/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py)

- 位置:
  - [ours/pipelines/flux_pipeline.py:682](/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py#L682C1)
  - [ours/pipelines/flux_pipeline.py:400](/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py#L400C1)
  - [ours/pipelines/flux_pipeline.py:411](/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py#L411C1)
- 要点:
  - 自定义 `FluxPipeline.__call__` 预留了:
    - `ip_adapter_image`
    - `ip_adapter_image_embeds`
    - `negative_ip_adapter_image`
    - `negative_ip_adapter_image_embeds`
  - 如果真的走这条图像条件分支, 代码会调用 `self.image_encoder` 和 `self.feature_extractor`
  - 所以这不是"接口名字上有参数就等于能用", 还要看模型资产里是否有视觉编码模块

### 来源3: [/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev/model_index.json](/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev/model_index.json)

- 位置:
  - [/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev/model_index.json:1](/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev/model_index.json#L1C1)
- 要点:
  - 当前本地权重清单只声明了:
    - `scheduler`
    - `text_encoder`
    - `text_encoder_2`
    - `tokenizer`
    - `tokenizer_2`
    - `transformer`
    - `vae`
  - 没有 `image_encoder`
  - 没有 `feature_extractor`
  - 这说明当前本地 `FLUX.1-dev` 资产并不是一个已经配好参考图编码器的组合

## 综合发现

### 现象

- 当前项目的 Flux refine 主链路只消费一张待修图
- 当前仓库代码里没有把"参考图 A"单独喂进 refine 调用

### 候选假设

- 假设A: 可以在现有自定义 `FluxPipeline` 上补接 IP-Adapter 风格的参考图条件分支
- 假设B: 即使 pipeline 代码有入口, 当前本地 `FLUX.1-dev` 模型资产也不足以直接跑通这条分支

### 当前结论

- 结论1: 当前项目实现层面, 不支持"两张图输入, 用 A 图去修 B 图"
- 结论2: 当前仓库代码层面, 存在图像条件扩展入口
- 结论3: 当前本地模型资产层面, 这条入口还没有配齐到可直接使用

## [2026-03-29 23:16:05] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] 笔记: `diffusers` 官方路线核对

## 来源

### 来源1: Context7 `/huggingface/diffusers` 文档 `docs/source/en/api/pipelines/flux.md`

- 要点:
  - 官方 `FluxPipeline` 文档给出了 FLUX + IP-Adapter 的用法示例
  - 示例核心步骤是:
    - `pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", ...)`
    - `pipe.load_ip_adapter("XLabs-AI/flux-ip-adapter", weight_name="ip_adapter.safetensors", image_encoder_pretrained_model_name_or_path="openai/clip-vit-large-patch14")`
    - `pipe.set_ip_adapter_scale(1.0)`
    - 调用时传 `ip_adapter_image=image`
  - 这说明从官方能力边界看, "FLUX 接参考图"是存在正统路线的
  - 但它依赖额外的 IP-Adapter 权重和图像编码器, 不是裸 `FLUX.1-dev` 自带

### 来源2: Context7 `/huggingface/diffusers` 文档 `docs/source/en/using-diffusers/ip_adapter.md`

- 要点:
  - 官方文档强调 `set_ip_adapter_scale(...)` 用来调参考图影响强度
  - 参考图条件是额外图像条件, 不会自动替代已有的 img2img / inpaint 输入图
  - 这和我们当前项目的需求更接近:
    - `image`: 继续当待修图 B
    - `ip_adapter_image`: 新增当参考图 A

## 综合发现

### 现象

- 官方 `diffusers` 已经承认 FLUX 存在参考图条件化路径
- 当前项目只差"模型资产接齐 + refine 调用接线 + 配置暴露"

### 结论

- 结论4: 最正确的改法不是滥改当前 `image` 语义, 而是保留 `image=待修图`, 新增 `ip_adapter_image=参考图`
- 结论5: 如果不想引入新的 IP-Adapter 资产, 当前这套 `FLUX.1-dev` refine 链很难优雅地做到真正的双图参考修复

## [2026-03-30 01:39:39] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] 笔记: 用户真实目标是 reference-guided pose-jitter repair

## 来源

### 来源1: 用户澄清需求

- 要点:
  - 图A不是任意参考图
  - 图A是当前训练原图, 也就是 pose jitter 的 base camera 对应真实观察
  - 图B不是任意待修图
  - 图B是围绕图A的小幅 jitter 后重新 render 出来的 synthetic 视角
  - 目标不是做风格迁移
  - 目标是让 Flux 参考图A里的真实内容证据, 去修补图B里因为新视角暴露而显得不完整、不合理的局部

### 来源2: [recon/refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)

- 位置:
  - [recon/refiner.py:493](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py#L493C1)
  - [recon/refiner.py:544](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py#L544C1)
- 要点:
  - `pose_jitter` 分支先通过 `_load_render_sample(...)` 取到源样本 `data`
  - 这个 `data` 就是 base camera 对应的真实训练样本
  - 后面再基于 `base_c2w` 采样 jitter 相机并渲染 `colors`
  - 最终 `cam_param` 里已经留下了 `source_image_name`
  - 这说明当前系统内部天然就有:
    - source real image
    - jitter render image
  - 缺的是把 source real image 往 Flux 条件输入继续传

### 来源3: [recon/datasets/colmap.py](/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py)

- 位置:
  - [recon/datasets/colmap.py:263](/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py#L263C1)
- 要点:
  - 数据集样本本身就包含:
    - `image`
    - `image_path`
    - `image_name`
  - 所以 reference image 并不需要额外去磁盘上重新猜测定位
  - 它已经是当前数据契约的一部分

### 来源4: [ours/refine_run_schedule.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_run_schedule.py)

- 位置:
  - [ours/refine_run_schedule.py:39](/root/autodl-tmp/home/rais/FreeFix/ours/refine_run_schedule.py#L39C1)
- 要点:
  - synthetic view plan 已经按 `source_split + source_index` 构造
  - 所以对每个 jitter render 来说, 它天然有一个明确的 source anchor
  - 这件事很重要, 因为它意味着:
    - reference image 不是模糊地"从训练集里找一张像的"
    - 而是"这个 jitter 样本对应的那张真实源图"

## 综合发现

### 问题重述

- 这不是普通双图编辑
- 这是一个"以真实源图为证据的局部修补"问题

### 三张图的真实语义

- `I_src`:
  - 真实训练原图
  - 提供可相信的内容证据
- `I_jitter_render`:
  - 当前高斯在 jitter 相机下的 render
  - 是待修对象
- `I_fixed`:
  - 不一定必须显式传给 Flux
  - 它只是提醒我们当前所有修补都必须服从同一套 3D/相机约束

### prompt 的职责边界

- prompt 应该表达:
  - 参照真实源图修补
  - 保持当前 jitter 视角
  - 不要凭空改变无关区域
  - 只修复不合理、不完整、破碎、拉伸、穿帮的内容
- prompt 不应该承担:
  - 单独存储桌子长什么样
  - 单独保证 identity consistency
  - 单独决定哪些内容是可信证据

### 当前最重要的设计判断

- 判断1:
  - 从系统语义上, 最合理的输入分工是:
    - `image = I_jitter_render`
    - `ip_adapter_image = I_src`
- 判断2:
  - 如果只有 prompt 没有 `I_src`, Flux 只能"猜一个完整桌子"
  - 但你要的是"参考真实源图里的桌子, 在新视角下补出更合理的桌子"
- 判断3:
  - 因为 `I_src` 和 `I_jitter_render` 来自同一个 source anchor, 这条设计比通用 reference editing 更稳, 也更容易做约束

## [2026-03-30 01:45:38] [Session ID: 83b49306-8fed-4524-947c-662aff798a0b] 笔记: OpenSpec 更适合新 change 修改既有 capability

## 来源

### 来源1: [openspec/changes/add-pose-jitter-refine/design.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/design.md)

- 位置:
  - [openspec/changes/add-pose-jitter-refine/design.md:27](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/design.md#L27C1)
- 要点:
  - 现有 design 的目标集中在:
    - 相机模式
    - source split
    - jitter 边界
    - 安全过滤与 fallback
  - non-goal 明确包含:
    - "本次不重写 Flux / SDXL pipeline 本身"

## 综合发现

### 结论

- 结论6:
  - `reference-guided pose-jitter repair` 不是单纯再补一条小 scenario
  - 它会改变生成阶段的条件输入语义:
    - 从单图 `image`
    - 变成 `image + reference evidence`
- 结论7:
  - 因此在 OpenSpec 上, 更自然的落法不是回改旧 change 的 design 边界
  - 而是新开一个 change, 去修改既有 `pose-jitter-refine` capability
