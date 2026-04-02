## [2026-03-27 12:59:46] [Session ID: unknown] 笔记: 已定位两边 COLMAP 相关入口

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix`

- 关键文件:
  - `recon/prepare_colmap_scene.py`
  - `recon/convert.py`
  - `recon/datasets/colmap.py`
  - `README.md`
  - `cmd.md`
- 初步观察:
  - FreeFix 同时支持“导入外部已存在 COLMAP 场景”和“从图片目录重新跑 COLMAP convert”两条路。
  - 训练侧额外支持 `partition.json` 控制 train/test 划分。

### 来源2: `/home/rais/FastGS`

- 关键文件:
  - `convert.py`
  - `scripts/run_lyra_colmap_fastgs.sh`
  - `scene/dataset_readers.py`
  - `scene/colmap_loader.py`
  - `README.md`
- 初步观察:
  - FastGS 的传统入口是 wrapper 脚本驱动 `convert.py -> train.py`。
  - 它也支持直接复用一个已经具备 `images + sparse/0` 的准备好目录。

## 综合发现

### 当前假设

- 两边共享的“核心 COLMAP 骨架”应该接近: feature extraction -> matching -> mapper -> image undistorter。
- 但 FreeFix 很可能比 FastGS 多了一层“外部场景导入 + partition 划分 + 自定义 parser”的数据治理逻辑。

### 下一步验证

- 继续核对:
  - FastGS wrapper 的 prepare / train / evaluate 具体串法
  - FreeFix `prepare_colmap_scene.py` 在何时复制 `database.db`、何时生成 `partition.json`
  - 两边训练时到底消费 `COLMAP` 的哪些文件

## [2026-03-27 13:06:00] [Session ID: unknown] 笔记: 两边 COLMAP 过程的已确认差异

## 来源

### 来源1: FastGS `convert.py` 与 wrapper

- 文件:
  - `/home/rais/FastGS/convert.py`
  - `/home/rais/FastGS/scripts/run_lyra_colmap_fastgs.sh`
  - `/home/rais/FastGS/scene/dataset_readers.py`
- 要点:
  - `convert.py` 既支持传统 `source_path/input` 图片模式, 也支持 `--video_path` 或自动探测视频目录后抽帧到 `input/`。
  - wrapper 会自动识别“已准备好的 `images + sparse/0` 根目录”, 否则串 `convert.py -> train.py -> render.py -> metrics.py`。
  - 训练切分由 `eval + llffhold=8` 控制, 不是独立的 partition 文件。

### 来源2: FreeFix `prepare_colmap_scene.py` / `convert.py` / `trainer.py`

- 文件:
  - `recon/prepare_colmap_scene.py`
  - `recon/convert.py`
  - `recon/datasets/colmap.py`
  - `recon/trainer.py`
- 要点:
  - `recon/convert.py` 基本仍是标准图片输入的 COLMAP convert, 不负责视频发现与抽帧。
  - `recon/prepare_colmap_scene.py` 负责把外部场景复制到仓库 `data/` 内, 同步复制 `database.db`、保留元数据、筛掉已删图片, 并按可验证条件生成 `partition.json`。
  - 训练侧优先读 `partition.json`; 如果没有, 才回退到 `test_every`。

### 来源3: 训练消费层

- FastGS:
  - `scene/dataset_readers.py::readColmapSceneInfo`
  - 直接读取 `sparse/0/{images,cameras}.{bin|txt}` 与 `images/`
  - `test` 由 `_split_train_test_cameras(..., llffhold=8)` 生成
- FreeFix:
  - `recon/datasets/colmap.py::Parser + Dataset`
  - 也读取 `sparse/0` 与 `images/`, 但额外支持 `partition_file`
  - parser 还能处理多种相机模型和必要时的去畸变

## 综合发现

### 已确认相同点

- 两边真正的 COLMAP 核心链路是一脉相承的:
  - feature extraction
  - exhaustive matching
  - mapper
  - image undistorter
- 两边都已经修过“不要盲信 `distorted/sparse/0`”的问题, 都会选注册图更多的 sparse 子模型去做 undistort。

### 已确认差异

- FastGS 更像“从原始视频/多视角生成目录直接开跑”的工程化 wrapper。
- FreeFix 更像“先把外部场景收敛成可控数据目录, 再训练”的数据治理版流程。
- FastGS 默认评测切分更接近经典 3DGS / LLFF 风格。
- FreeFix 明显更强调显式 train/test 划分和外部数据一致性。

### 影响判断

- 如果只看 COLMAP 四段命令, 两边很接近。
- 如果看实际工程使用方式, 差异很明显:
  - FastGS 优先解决“从视频到可训练目录”
  - FreeFix 优先解决“外部场景导入后如何保持图片、数据库、sparse、partition 一致”
