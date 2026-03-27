## [2026-03-27 13:08:00] [Session ID: unknown] 任务名称: 对比 FastGS 与 FreeFix 的 COLMAP 流程

### 任务内容
- 回读 `/home/rais/FastGS` 与当前 `FreeFix` 仓库中负责 COLMAP 的关键入口与训练消费层。
- 对比两边在输入假设、COLMAP 命令链、目录组织和 train/test 划分上的异同。

### 完成过程
- 先定位两边关键文件:
  - FastGS: `convert.py`、`scripts/run_lyra_colmap_fastgs.sh`、`scene/dataset_readers.py`
  - FreeFix: `recon/prepare_colmap_scene.py`、`recon/convert.py`、`recon/datasets/colmap.py`
- 再逐条核对:
  - 两边是否都走 `feature_extractor -> exhaustive_matcher -> mapper -> image_undistorter`
  - 两边是否都支持“已准备好的 `images + sparse/0` 根目录”
  - 训练切分是 `llffhold/eval` 还是 `partition.json/test_every`
- 最后把共享骨架与真正影响训练口径的差异拆开整理。

### 总结感悟
- 两边的 COLMAP 核心命令链很接近, FreeFix 的 `recon/convert.py` 明显继承了 FastGS `convert.py` 的主骨架。
- 真正拉开差距的不是 COLMAP 四段命令本身, 而是外层工程职责:
  - FastGS 偏“从视频直接起流程”
  - FreeFix 偏“把外部场景导入后治理干净再训练”
- train/test 划分口径是最需要单独注意的差异, 因为它会直接影响评测可比性。
