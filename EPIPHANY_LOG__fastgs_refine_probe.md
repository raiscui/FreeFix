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
