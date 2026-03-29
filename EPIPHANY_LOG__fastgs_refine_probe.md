## [2026-03-27 09:37:59] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] 主题: FastGS 桥接当前只应瞄准 FreeFix 的 `app_opt=false` 线

### 发现来源
- 在对齐 `my4_fullcolmap_quality`、`stable_12k_dense` 与 `Refiner` 实际读取字段时发现

### 核心问题
- `FastGS` 的训练产物天然是 SH 参数化:
  - `sh0`
  - `shN`
- 但 FreeFix 的 `app_opt=true` 训练线保存的是:
  - `features`
  - `colors`
- 因此“能桥接到 Refine”这句话如果不加限定, 很容易被误听成“所有 FreeFix 训练线都能直接接”

### 为什么重要
- 这不是一个小配置差异
- 它决定了 checkpoint 的颜色参数化结构
- 一旦桥接目标选错, 失败现象会看起来像“字段缺失”或“Refiner 加载坏了”, 但本质上是目标训练线选错了

### 未来风险
- 后续如果有人直接拿 `my4_fullcolmap_quality` 这类 `app_opt=true` 结果当桥接模板, 很可能会误以为 FastGS 导入脚本有 bug
- 也可能会进一步误判成“FastGS 不能接 Refine”

### 当前结论
- 当前已落地的桥接脚本稳定目标是 `app_opt=false` 的 FreeFix 训练 / refine 线
- 典型入口是 `stable_12k_dense` 这种 SH 参数化结果目录
- 若未来确实要支持 `app_opt=true`, 需要单独设计 SH -> `features/colors` 的转换口径, 不能靠这次脚本顺手兼容

### 后续讨论入口
- 下次若要扩展到 `app_opt=true`, 先看:
  - [import_fastgs.py](/home/rais/FreeFix/recon/import_fastgs.py)
  - [refiner.py](/home/rais/FreeFix/recon/refiner.py)
  - [cfg.json](/home/rais/FreeFix/outputs/my4_fullcolmap_quality/cfg.json)

## [2026-03-29 10:53:59] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 主题: 随机 pose 的 Flux refine 一旦越界, 本质上就从“修图”变成“2D 幻觉监督 3D”

### 发现来源
- 在回读 `ours/refine_by_flux.py`、`recon/refiner.py` 与当前 refine 配置后, 对“随机相机偏移 + 图生图”方案做静态对齐时发现

### 核心问题
- 当前 refine 的生成图会被直接绑定到相机参数, 再作为监督信号写回高斯
- 所以如果随机 pose 只是很小扰动, 它像局部增广
- 但如果偏移过大, Flux 生成的新显露区域没有真实多视图约束, 这些内容也会被当成“应该长成这样”的监督写回 3D

### 为什么重要
- 这不是单纯的“效果可能不稳定”
- 它会改变整个模块的语义边界:
  - 从 refinement
  - 变成 synthetic novel-view bootstrapping
- 一旦语义变了, 评测、配置命名、默认参数和风险控制都要跟着变

### 未来风险
- 如果直接围绕 `test_split=test` 做随机附近采样并训练, benchmark 纯净性会被破坏
- 如果没有 pose 扰动上限与可见性约束, 细薄结构、遮挡边界、镜面区域会优先出问题
- 如果后续只看生成图观感, 很容易误把 hallucination 当成 3D 提升

### 当前结论
- 这条路线值得做, 但第一版必须被定义成“受控的小幅 pose jitter synthetic refine”
- 需要显式和评测 split 解耦
- 需要先做最小证伪实验, 不能一上来大范围推广

### 后续讨论入口
- 下次若继续推进, 先看:
  - [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)
  - [refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
  - [base.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml)
  - [notes__fastgs_refine_probe.md](/root/autodl-tmp/home/rais/FreeFix/notes__fastgs_refine_probe.md)

## [2026-03-29 12:17:05] [Session ID: codex-add-pose-jitter-smoke] 主题: 大模型 refine 的“无输出长冷启动”会把 smoke 诊断直接带偏

### 发现来源
- 在为 `add-pose-jitter-refine` 执行真实 Flux smoke 时, 先后通过分段探针与阶段日志定位得到

### 核心问题
- 这条 refine 链路里, 真正的冷启动耗时非常大:
  - `torch` 等重依赖导入接近百秒
  - `FluxPipeline.from_pretrained` 之后, `pipe.to(cuda)` 还会继续长时间占用窗口
- 如果入口没有阶段日志, 人会天然把“几分钟没输出”误解成:
  - pose jitter 逻辑挂了
  - CLI 卡死了
  - 配置读错了

### 为什么重要
- 这会直接扭曲调试方向
- 本来应该继续观察模型冷启动, 最后却很容易演变成对 pose jitter 主链的误判和无意义改代码

### 未来风险
- 后续只要再跑:
  - Flux refine
  - SDXL refine
  - 或任何大模型 + GS 的冷启动链路
- 如果没有阶段日志, 同样会再次出现“黑盒超时”误诊

### 当前结论
- 对这类大模型 refine 入口, 阶段日志属于必要可观测性, 不是可有可无的调试打印
- 真实 smoke 的时间窗口也要基于冷启动事实来设, 不能沿用轻量脚本的心理预期

### 后续讨论入口
- 下次继续真实 smoke 时, 先看:
  - [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)
  - [refine_by_sdxl.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py)
  - [notes__fastgs_refine_probe.md](/root/autodl-tmp/home/rais/FreeFix/notes__fastgs_refine_probe.md)

## [2026-03-29 12:40:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 主题: diffusers 的 offload 一旦启用, “设备语义”就不再等于 `pipe.device`

### 发现来源
- 在把 Flux / SDXL refine 从默认 `pipe.to(cuda)` 切到 `enable_model_cpu_offload()` 的过程中, 回读本地 pipeline 实现与真实 smoke 日志后得到

### 核心问题
- 很多调用代码会天然写成:
  - `tensor.to(pipe.device)`
- 但 offload 模式下:
  - `pipe.device` 常常仍是 CPU
  - 真正的执行设备在 `_execution_device`
- 如果调用层没有跟着切语义, 就很容易出现:
  - 额外的 CPU/GPU 往返
  - 甚至把输入送错设备

### 为什么重要
- 这不是 Flux 特例
- 只要后面再接:
  - SDXL
  - SVD
  - 或别的 diffusers pipeline
- 同类问题都可能再出现

### 未来风险
- 后续如果有人只看 `pipe.device`, 会误以为 offload 已经“退回 CPU 推理”
- 然后继续在调用层补错误的 `.to(pipe.device)`, 把可工作的 offload 路径再次搞坏

### 当前结论
- 对接 diffusers offload 时, 调用层应该优先使用 execution device 语义
- `pipe.device` 只能表示“当前模块大致驻留位置”, 不能直接当成“本轮推理要把输入送到哪里”

### 后续讨论入口
- 以后再做相关接入, 优先先看:
  - [refine_pipeline_runtime.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_pipeline_runtime.py)
  - [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)
  - [refine_by_sdxl.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py)

## [2026-03-29 14:50:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 主题: 从成熟 checkpoint 恢复继续训练时, 绝不能把 strategy 的全局步数重置到 0

### 发现来源
- 在排查 `my5 pose_jitter + train` smoke 的黑帧时, 通过离线重渲染、最小动态复现、strategy 静音对照和 `gsplat` 源码阅读共同确认

### 核心问题
- 很多训练 strategy 会把:
  - `step=0`
  - `step % reset_every == 0`
  - 或 `step > refine_start_iter`
- 当成重要的调度边界
- 如果从成熟 checkpoint 恢复时, 误把局部 refine 步数直接当成全局训练步数, 这些 reset / prune / grow 逻辑就会在错误的时刻触发

### 为什么重要
- 这类 bug 很会伪装
- 现象会出现在:
  - 黑帧
  - 模型突然变空
  - opacity 集体变小
  - 细节突然蒸发
- 但表面上又很容易被误判成:
  - 相机位姿错了
  - 数据脏了
  - 生成图质量差

### 未来风险
- 以后只要再接:
  - GS densification/pruning strategy
  - EMA/重置类调度器
  - 任何依赖“全局 step”的训练策略
- 如果恢复时间轴没处理好, 同类问题还会复现

### 当前结论
- 恢复继续训练时必须明确区分:
  - 局部本轮步数
  - checkpoint 继承的全局训练步数
- 前者用于本轮节奏控制
- 后者用于 strategy / scheduler / reset 这类时间轴敏感逻辑

### 后续讨论入口
- 下次如果再出现“恢复后第一步就异常”的问题, 优先先看:
  - [recon/refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
  - [recon/refine_runtime.py](/root/autodl-tmp/home/rais/FreeFix/recon/refine_runtime.py)
  - [notes__fastgs_refine_probe.md](/root/autodl-tmp/home/rais/FreeFix/notes__fastgs_refine_probe.md)
