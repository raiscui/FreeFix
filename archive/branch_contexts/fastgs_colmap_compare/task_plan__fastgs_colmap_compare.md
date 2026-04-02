# 任务计划: 对比 FastGS 与 FreeFix 的 COLMAP 流程

## [2026-03-27 12:59:46] [Session ID: unknown] [记录类型]: 初始化对比计划

## 目标

- 对齐 `/home/rais/FastGS` 和 `/root/autodl-tmp/home/rais/FreeFix` 中实际负责 COLMAP 的入口与流程。
- 给出两边在输入假设、COLMAP 命令链、产物布局、训练消费方式上的相同点与差异点。
- 说明这些差异会不会影响数据准备、训练行为或评测口径。

## 阶段

- [x] 阶段1: 回读当前主线尾部与相关上下文
- [ ] 阶段2: 抓取两边 COLMAP 入口与脚本
- [ ] 阶段3: 对齐命令链、目录结构与切分逻辑
- [ ] 阶段4: 输出对比结论与影响分析

## 关键问题

1. FastGS 的 COLMAP 流程入口是什么: 初步看到是 `convert.py` 与 `scripts/run_lyra_colmap_fastgs.sh`。
2. FreeFix 的 COLMAP 流程入口是什么: 初步看到是 `recon/prepare_colmap_scene.py`、`recon/convert.py` 与 `recon/datasets/colmap.py`。
3. 两边是否都只是“标准 COLMAP -> undistort -> train”: 还不能直接下结论, 需要继续核对 wrapper 逻辑与数据契约。

## 做出的决定

- 决定1: 先读真实代码和 README, 不先信名称相似就当流程相同。
- 决定2: 输出时按“现象 -> 差异 -> 影响”来讲, 避免把推测写成已确认结论。

## 状态

**目前在阶段2** - 已定位关键文件, 正在逐个读取两边的 COLMAP 主路径实现。

## [2026-03-27 13:06:00] [Session ID: unknown] [记录类型]: 入口与主流程已对齐

## 阶段

- [x] 阶段1: 回读当前主线尾部与相关上下文
- [x] 阶段2: 抓取两边 COLMAP 入口与脚本
- [x] 阶段3: 对齐命令链、目录结构与切分逻辑
- [ ] 阶段4: 输出对比结论与影响分析

## 关键问题

1. 两边的 COLMAP 核心命令链是否一致: 基本一致, 都是 feature_extractor -> exhaustive_matcher -> mapper -> image_undistorter。
2. 两边的数据准备职责是否一致: 不一致。FastGS 自带视频抽帧 wrapper, FreeFix 多了外部场景导入与 partition 治理。
3. 两边训练时的 train/test 划分是否一致: 不一致。FastGS 主要靠 eval + llffhold, FreeFix 优先使用 partition.json, 无 partition 时才回退 test_every。

## 做出的决定

- 决定3: 最终输出要把“共享骨架”和“数据治理差异”分开讲, 否则容易误以为两边完全不同或完全一样。
- 决定4: 明确标出哪些差异是流程包装层, 哪些差异会真正影响训练/评测口径。

## 状态

**目前在阶段4** - 关键证据已齐, 正在整理最终对比结论。
