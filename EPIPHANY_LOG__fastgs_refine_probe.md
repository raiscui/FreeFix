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
