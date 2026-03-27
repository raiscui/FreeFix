## [2026-03-26 13:42:05] [Session ID: 10c9113d-607a-4438-ac65-f643b71d367d] 笔记: FreeFix 对 COLMAP 数据目录的真实要求

## 来源

### 来源1: `README.md`

- 文件: `/home/rais/FreeFix/README.md`
- 要点:
  - 重建入口是 `python -m recon.trainer --data_dir <data_directory> --data_type colmap`
  - README 没有提供外部数据导入脚本

### 来源2: `recon/datasets/colmap.py`

- 文件: `/home/rais/FreeFix/recon/datasets/colmap.py`
- 要点:
  - `Parser` 会优先读取 `data_dir/sparse/0`, 不存在时回退到 `data_dir/sparse`
  - 解析器依赖 `pycolmap.SceneManager` 读取 COLMAP 模型
  - 图像目录固定看 `images/` 和可选 `images_<factor>/`
  - `Dataset` 若给 `partition_file`, 只认 JSON 里的 `train` 和 `test` 两个索引数组

### 来源3: `recon/trainer.py`

- 文件: `/home/rais/FreeFix/recon/trainer.py`
- 要点:
  - 若 `cfg.partition` 未显式指定, 训练器会自动尝试 `data_dir/partition.json`
  - 也就是说, 只要把 `partition.json` 放在数据目录根部, 就能直接生效

## 综合发现

### 目录结构层

- `FreeFix` 真正直接消费的核心资产只有:
  - `images/`
  - `sparse/` 或 `sparse/0`
  - 可选 `partition.json`
- `ref_image/`、`images_test/`、`prepared_multishot_manifest.json` 这类文件, 当前仓库没有任何代码直接读取

### my4 源目录现象

- `images/` 有 `492` 张图
- `images_test/` 有 `132` 张图
- `ref_image/` 有 `180` 张图
- `sparse/` 文件数为 `0`
- `colmap_text/` 文件数为 `0`

### 数据库证据

- `database.db` 里有:
  - `images: 312`
  - `keypoints: 312`
  - `descriptors: 312`
  - `matches: 1851`
  - `two_view_geometries: 1851`
- `colmap_train_images.txt` 共 `180` 张
- `colmap_test_images.txt` 共 `132` 张
- `colmap_feature_images.txt` 共 `312` 张
- 已验证:
  - `train ∪ test == database images`
  - `train ∩ test == ∅`
  - `feature_images == database images`

### 当前判断口径

- 现象:
  - `my4` 有可复制的图像和 COLMAP 数据库
  - 但缺少 `FreeFix` 直接读取所需的 sparse model
- 当前主假设:
  - 这份目录更像“COLMAP 前处理和划分清单还在, 但最终稀疏模型文件丢了或没导出”
- 最强备选解释:
  - sparse model 可能原本在别的目录, `my4` 这里只保留了数据库与切分信息
- 推翻主假设的证据:
  - 如果在源目录或明确的旁路目录里找到 `cameras/images/points3D` 模型文件, 主假设就要回滚

### 实施含义

- 值得做导入脚本
- 脚本至少要负责:
  - 从源目录复制出 `FreeFix` 需要的最小资产
  - 生成 `partition.json`
  - 明确标记“当前是否已训练就绪”
  - 如果未来系统里有 `colmap` CLI, 支持从复制后的 `database.db` 重新生成 `sparse/`

## [2026-03-26 13:50:58] [Session ID: 10c9113d-607a-4438-ac65-f643b71d367d] 笔记: 新证据推翻了“sparse 缺失”假设

## 来源

### 来源1: 重新展开 `/home/rais/CoherentGS/data/my4/sparse`

- 要点:
  - 当前真实存在:
    - `sparse/0/cameras.bin`
    - `sparse/0/images.bin`
    - `sparse/0/points3D.bin`
  - 还存在:
    - `sparse/registered/*`
    - `sparse/train_mapper/0/*`

### 来源2: 第二轮脚本验证

- 文件: `/home/rais/FreeFix/recon/prepare_colmap_scene.py`
- 要点:
  - 补上了对 COLMAP `images.bin` 的直接解析
  - 重新导入后, `import_report.json` 显示:
    - `copied_image_count = 312`
    - `sparse_ready = true`
    - `partition_ready = true`

## 综合发现

### 假设回滚

- 上一条主假设“不存在 sparse model”已被新证据推翻
- 推翻它的直接证据:
  - 源目录 `sparse/0` 中实际存在标准 COLMAP 二进制模型文件

### 当前目标目录状态

- `data/my4/images/`: `312` 张图
- `data/my4/database.db`: 已通过 SQLite backup 复制
- `data/my4/sparse/0`: 已复制二进制模型
- `data/my4/partition.json`: 已生成
- `data/my4/import_report.json`: 已生成
- `data/my4/meta/`: 已保留原始 train/test/manifest 清单

### 剩余边界

- 目录层和脚本层已经完成验证
- 运行时层仍有一个独立环境问题:
  - 当前 `.pixi` 环境导入 `pycolmap` 报 `OverflowError('Python integer -1 out of bounds for uint64')`
  - 因此这次没有继续执行 `recon.trainer` 做真实加载 smoke test

### 结论

- 这次任务的根本产出不是“再造一套数据”, 而是把外部数据集安全搬运到项目内, 并用项目自己能识别的结构把它落稳
- 对当前这份 `my4`, 现在已经具备清晰、可追溯、可复用的导入结果

## [2026-03-26 14:00:40] [Session ID: 10c9113d-607a-4438-ac65-f643b71d367d] 笔记: 系统 CUDA COLMAP 已接入, parser smoke test 通过

## 来源

### 来源1: 系统 COLMAP 位置核对

- 命令:
  - `find /usr /usr/local /opt /home/rais -maxdepth 5 -type f \( -name 'colmap' -o -name 'COLMAP' \)`
- 关键输出:
  - `/home/rais/.local/opt/colmap-env/bin/colmap`
- 版本验证:
  - `COLMAP 4.0.2`
  - `Commit d927f7e on 2026-03-18 with CUDA`

### 来源2: `.pixi` 环境下 parser smoke test

- 命令:
  - `Parser(data_dir='data/my4', factor=1, normalize=True, test_every=1)`
  - `Dataset(parser, split='train', partition_file='data/my4/partition.json')`
- 关键输出:
  - `[Parser] 312 images, taken by 1 cameras.`
  - `point_count 16062`
  - `dataset_len 180`
  - `image_shape (720, 1280, 3)`

## 综合发现

### 结构层

- 系统 `colmap` CLI 和 Python 侧 `pycolmap` 是两条不同依赖面
- 用户补充“别的都用系统 CUDA COLMAP”之后, 正确动作不是只记住路径, 而是把项目读取路径也改成直接消费标准模型文件

### 代码层

- 新增:
  - [colmap_io.py](/home/rais/FreeFix/recon/datasets/colmap_io.py)
- 修改:
  - [colmap.py](/home/rais/FreeFix/recon/datasets/colmap.py)
  - [prepare_colmap_scene.py](/home/rais/FreeFix/recon/prepare_colmap_scene.py)
  - [convert.py](/home/rais/FreeFix/recon/convert.py)

### 结论

- 当前项目对 `my4` 的读取已经不再依赖 `pycolmap`
- 系统 `CUDA COLMAP` 负责“产出模型”
- 项目代码现在可以自己“消费模型”

## [2026-03-27 01:32:19] [Session ID: 20260327T012145Z-main] 笔记: 本地 ModelScope `FLUX.1-dev` 已接入并完成 `my4` 全量 refine

## 来源

### 来源1: `ours/refine_by_flux.py` 与 `flux_shinkai_museum.yaml`

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum.yaml`
- 要点:
  - 新增 `resolve_flux_model_source(cfg)`
  - 优先读取 `cfg.flux_model_path`
  - 若未显式配置, 自动尝试:
    - `/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`
    - `/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev`
  - 命中本地目录时, `FluxPipeline.from_pretrained(...)` 会带 `local_files_only=True`

### 来源2: refine 真实运行 session `72743`

- 命令:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my4/flux_shinkai_museum.yaml`
- 关键输出:
  - `Using Flux model source: /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`
  - 中途持续完成多轮:
    - `32` 步生成
    - `400` 步 refine
  - 进程最终 `exit code 0`
- 非 fatal warning:
  - `CLIP can only handle sequences up to 77 tokens`
  - 被截断的后半段包含:
    - `体积光 / god rays`
    - `光束、光柱`
    - `镜头光晕`
    - `辉光`
    - `slight camera motion`
    - `high detail`

## [2026-03-27 03:20:26] [Session ID: 20260327T032026Z-main] 笔记: `my4_fullcolmap` 的真正问题是 undistort 选错了 sparse model

## 来源

### 来源1: `data/my4_fullcolmap/distorted/sparse/*` 实测规模

- 命令:
  - `.pixi/envs/default/bin/python - <<'PY' ... load_registered_image_names/read_points3d ... PY`
- 关键输出:
  - `0 2 296`
  - `1 264 27521`

### 来源2: 当前根目录去畸变产物

- 命令:
  - `find data/my4_fullcolmap/images -maxdepth 1 -type f | wc -l`
  - `.pixi/envs/default/bin/python - <<'PY' ... root_sparse_0 ... PY`
- 关键输出:
  - `images/` 当前只有 `2` 张图
  - `root_sparse_0 2 296`

### 来源3: `recon/convert.py`

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/convert.py`
- 要点:
  - `image_undistorter` 当前固定使用:
    - `os.path.join(distorted_sparse_path, "0")`

## 综合发现

### 现象

- `mapper` 已经成功产出了至少两个 sparse model
- 其中 `distorted/sparse/1` 才是主模型
- 但最终 `images/` 和根级 `sparse/0` 都只对应那个 2 图小模型

### 当前主假设

- `convert.py` 的固定 `distorted/sparse/0` 行为, 正是这次错误产物的直接来源

### 最强备选解释

- `COLMAP image_undistorter` 自己也可能存在“默认只消费第一个模型”的行为
- 但这不会推翻脚本层的问题
- 因为当前脚本已经显式把 `0` 传给了它

### 当前结论

- 这不是 `mapper` 失败
- 也不是“数据本身只重建出 2 张”
- 已验证结论是:
  - undistort 输入模型选错了
  - 正确模型应当优先选择注册图数最多的 `distorted/sparse/1`

## [2026-03-27 03:20:26] [Session ID: 20260327T032026Z-main] 笔记: `my4_fullcolmap` 修复后已完成三层动态验证

## 来源

### 来源1: 修复后的 `convert.py` 动态执行

- 命令:
  - `python3 recon/convert.py --source_path data/my4_fullcolmap --colmap_executable /home/rais/.local/opt/colmap-env/bin/colmap --skip_matching`
- 关键输出:
  - `=> Reconstruction with 264 images and 27521 points`
  - `Undistorting image [264/264]`
  - `Done.`

### 来源2: 修复后的场景目录核对

- 命令:
  - `find data/my4_fullcolmap/images -maxdepth 1 -type f | wc -l`
  - `.pixi/envs/default/bin/python - <<'PY' ... root_sparse_0 ... PY`
- 关键输出:
  - `264`
  - `root_sparse_0 264 27521`

### 来源3: parser / dataset / trainer smoke test

- 命令:
  - `.pixi/envs/default/bin/python - <<'PY' ... Parser + Dataset ... PY`
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4_fullcolmap --result_dir outputs/my4_fullcolmap_smoke --data_type colmap --max_steps 1 --disable_viewer`
- 关键输出:
  - `dataset_len = 152`
  - `image_shape = (687, 1228, 3)`
  - `Trainset Size: 152`
  - `Test Size: 112`
  - `Step: 0 ...`

## 综合发现

### 结果层

- `data/my4_fullcolmap` 现在已经是可训练场景
- 当前有效数据规模是:
  - 注册图 `264`
  - 稀疏点 `27521`
  - 训练划分 `152`
  - 测试划分 `112`

### 兼容性层

- 修完“选错 sparse model”后, 还必须顾到脚本入口形式
- 否则代码逻辑虽然对了, 用户原来的 `python3 recon/convert.py ...` 命令会直接死在 import 阶段

### 当前结论

- 这轮 full COLMAP 的主阻塞点已经收口
- 后面如果要继续提升重建质量, 可以直接基于 `data/my4_fullcolmap` 做新一轮训练对照, 不需要再先修数据目录

## [2026-03-27 04:22:05] [Session ID: 20260327T041915Z-main] 笔记: 画质优先增强参数已在 `my4_fullcolmap` 上进入正式训练

## 来源

### 来源1: 增强版 YAML

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_quality.yaml`
- 关键参数:
  - `max_steps: 50000`
  - `refine_stop_iter: 30000`
  - `pose_opt: true`
  - `app_opt: true`
  - `depth_loss: true`
  - `eval_steps/save_steps: [1000, 10000, 30000, 50000]`

### 来源2: 1 step smoke test

- 命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my4/recon_my4_fullcolmap_quality.yaml --set result_dir=outputs/my4_fullcolmap_quality_smoke --set max_steps=1 --set eval_steps=[1] --set save_steps=[1]`
- 关键输出:
  - `Trainset Size: 152`
  - `Test Size: 112`
  - `depth loss=1.331720`
- 落盘配置验证:
  - `pose_opt = True`
  - `app_opt = True`
  - `depth_loss = True`

### 来源3: 正式长训练

- 命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my4/recon_my4_fullcolmap_quality.yaml`
- 进程:
  - PTY session `41521`
- 当前证据:
  - 已落盘 `cfg.json`
  - 已落盘 `ckpt_999.pt`
  - 已落盘 `train_step0999.json`
  - 实时日志已越过 `step 2200`

### 来源4: `recon/trainer.py`

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/trainer.py`
- 要点:
  - 保存条件使用:
    - `if step in [i - 1 for i in cfg.save_steps]`
  - 自动 eval 代码当前被注释:
    - `# if step in [i - 1 for i in cfg.eval_steps] ...`

## 综合发现

### 训练状态层

- 这轮不是“准备要跑”, 而是已经正式开始跑
- 当前增强参数组合在 `my4_fullcolmap` 上没有暴露新的运行时错误
- `depth_loss` 已有动态证据确认参与优化

### 保存与评测口径层

- 当前训练器的保存是 zero-based
- 所以 `save_steps=[1000,...]` 的第一份 checkpoint 会叫:
  - `ckpt_999.pt`
- 当前没有自动 `eval/*.json`
- 不是因为训练没到点, 而是因为 trainer 里这段逻辑被注释了

### 当前结论

- “更干净 COLMAP + 更积极训练参数” 这条路线已经进入真实执行阶段
- 后续如果要拿量化指标, 需要:
  - 要么等后面手动评测 checkpoint
  - 要么单独恢复 trainer 的自动 eval 路径

## [2026-03-27 04:24:12] [Session ID: 20260327T041915Z-main] 笔记: 增强训练已完成第一阶段 checkpoint 落盘

## 来源

### 来源1: 训练目录实时核对

- 命令:
  - `find outputs/my4_fullcolmap_quality -maxdepth 2 -type f | sort | rg 'ckpt_9999|train_step9999|ckpt_999|train_step0999|cfg.json'`
- 关键输出:
  - `ckpt_999.pt`
  - `ckpt_9999.pt`
  - `train_step0999.json`
  - `train_step9999.json`

### 来源2: `train_step9999.json`

- 命令:
  - `python3 - <<'PY' ... print(train_step9999.json) ... PY`
- 关键输出:
  - `mem = 0.8800015449523926`
  - `ellipse_time = 177.09205508232117`
  - `num_GS = 300253`

### 来源3: PTY 实时日志

- 进程:
  - session `41521`
- 关键输出:
  - 已越过 `step 10500`
  - 当前仍在持续优化, 未退出

## 综合发现

### 进度层

- 这轮训练已经跨过“只是启动成功”的阶段
- 当前已经拿到第一份真正可复用的阶段 checkpoint:
  - `outputs/my4_fullcolmap_quality/ckpts/ckpt_9999.pt`

### 模型规模层

- `num_GS` 从:
  - `27058` (`step 999`)
- 增长到:
  - `300253` (`step 9999`)
- 说明当前 densify 窗口确实在积极扩张模型容量

### 当前结论

- 当前增强配置不是空跑
- 它已经在更干净的 `my4_fullcolmap` 上形成了一份可后续手动评测的 10k checkpoint

## [2026-03-27 04:43:28] [Session ID: 20260327T041915Z-main] 笔记: `9999` 与 `49999` 两档手动评测已完成, 且 `9999` test 指标更优

## 来源

### 来源1: `ckpt_9999.pt` 手动评测

- 输出目录:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_9999`
- 关键结果:
  - `PSNR = 23.186845779418945`
  - `SSIM = 0.8350304961204529`
  - `LPIPS = 0.2546704411506653`

### 来源2: `ckpt_49999.pt` 手动评测

- 输出目录:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_49999`
- 关键结果:
  - `PSNR = 22.832536697387695`
  - `SSIM = 0.8252953886985779`
  - `LPIPS = 0.2585321366786957`

### 来源3: 输出图片目录

- 两档评测都已生成:
  - `renders/concat/*.png`
  - `renders/rgbs/*.png`
  - `renders/alphas/*.png`
  - `renders/certainties/...`
  - `renders/preview_concat_grid.png`
  - `renders/preview_rgb_grid.png`

### 来源4: 评测路径修复

- 本轮修复了两类真实 bug:
  - `rasterize_splats_w_certainty()` 里错误引用未定义 `cfg`
  - `override_color` certainty 渲染分支未跳过 `app_module`, 且 `app_opt=true` 时错误假设必有 `sh0/shN`

## 综合发现

### 指标层

- 在当前这条“更干净 COLMAP + 增强参数”训练线上
- 已评测的两档 checkpoint 中:
  - `9999` 的 test 指标优于 `49999`

### 训练判断层

- 这不等于已经证明“训练越久一定越差”
- 但至少当前动态证据表明:
  - 从 `9999` 到 `49999` 继续训练, 没有带来更好的 test 指标
- 所以下一轮如果继续调质量:
  - 应把“更早保存点 / early stop”纳入主选项

### 当前结论

- 这轮用户要的“评估 + 输出图片”已经完整落地
- 并且我们拿到了一个新的重要判断:
  - 当前增强配置下, `9999` 比最终 `49999` 更值得优先看

### 来源3: 产物核对

- 视频元数据:
  - `before_refine.mp4`
  - `after_refine.mp4`
  - `refine/gen.mp4`
- `ffprobe` 关键输出:
  - 都是 `h264`
  - 都是 `1280x720`
  - 都是 `12 fps`
  - 都是 `50` 帧
  - 时长都约 `4.167` 秒
- checkpoint 与目录:
  - `outputs/my4/ckpts/ckpt_flux_shinkai_museum.pt`
  - `outputs/my4/flux_shinkai_museum/after_refine/030.jpg` 到 `079.jpg`
  - `outputs/my4/flux_shinkai_museum` 总体积约 `31M`

## 综合发现

### 接入层

- 这次真正有效的修法不是“改 repo id”
- 而是把 refine 入口改成:
  - 优先吃本地快照
  - 找到本地快照时强制 `local_files_only=True`
- 这样同一套代码既能兼容:
  - 本地已下载模型
  - 未来仍可能存在的远端默认 repo

### 运行层

- 本轮真实 refine 已完成 `50` 个视角
- 输出链条完整:
  - `before_refine/*.jpg`
  - `refine/render/*.jpg`
  - `refine/gen/image_*.jpg`
  - `after_refine/*.jpg`
  - `before_refine.mp4`
  - `refine/gen.mp4`
  - `after_refine.mp4`
  - `ckpt_flux_shinkai_museum.pt`

### 仍需留意的边界

- 这次没有再被模型下载权限阻断
- 但 prompt 语义并没有被完整送进 `CLIP`
- 如果以后要追求“体积光 / God rays / 镜头光晕”这些词的更稳定保留, 应优先做 prompt 压缩, 而不是重复沿用当前长 prompt 盲目重跑

## [2026-03-27 00:43:01] [Session ID: 78200] 笔记: `gsplat` JIT 失败的真实根因链路已收窄到 pixi CUDA 工具链路径

## 来源

### 来源1: 用户原始训练报错

- 命令:
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4 --result_dir outputs/my4 --data_type colmap`
- 现象:
  - 先报 `gsplat: No CUDA toolkit found. gsplat will be disabled.`
  - 随后在 `fully_fused_projection_fwd` 处因 `_C is None` 崩溃

### 来源2: 第一轮 JIT 日志 `/tmp/gsplat_jit_py311.log`

- 静态证据:
  - `torch.utils.cpp_extension` 在当前环境下使用了:
    - `-isystem /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/include`
  - 但真正的 CUDA 头文件存在于:
    - `.pixi/envs/default/targets/x86_64-linux/include/cuda_runtime_api.h`
- 动态证据:
  - 第一条真实失败是:
    - `fatal error: cuda_runtime_api.h: No such file or directory`

### 来源3: 本地 pixi CUDA 目录结构核查

- `nvcc` 可执行文件:
  - `.pixi/envs/default/targets/x86_64-linux/bin/nvcc`
- 真实 toolkit 根:
  - `.pixi/envs/default/targets/x86_64-linux`
- `cicc` 所在位置:
  - `.pixi/envs/default/nvvm/bin/cicc`

### 来源4: 最小证伪实验

- 实验1:
  - 手动把 `CUDA_HOME` / `CUDA_PATH` 改到 `.pixi/envs/default/targets/x86_64-linux`
  - 结果:
    - `cuda_runtime_api.h` 缺失错误消失
    - 新的第一条失败变为 `sh: 1: cicc: not found`
- 实验2:
  - 在实验1基础上, 再把 `.pixi/envs/default/nvvm/bin` 加入 `PATH`
  - 结果:
    - `cicc` 进程真实启动
    - `ninja -v -j 2` 持续编译多个 `compute_120` 目标
    - 到当前记录时, 还未看到新的即时编译错误

## 综合发现

### 现象

- 用户直接运行 `.pixi/envs/default/bin/python` 时, `gsplat` 会误判“没有 CUDA toolkit”
- 即便代码层先把 `nvcc` 暴露出来, 如果 `CUDA_HOME` 仍指向 `.pixi/envs/default` 根目录, `torch` 仍会把 CUDA include 路径拼错
- 当 `CUDA_HOME` 改正后, `nvcc` 还需要 `nvvm/bin` 中的 `cicc`

### 当前主假设

- `gsplat` 当前失败的主因不是版本不兼容, 而是 pixi CUDA 工具链被拆成了两段路径:
  - toolkit 根在 `targets/x86_64-linux`
  - NVVM 编译器在 `nvvm/bin`

### 最强备选解释

- 还有更深层的 `sm_120` 或 `gsplat 1.1.1` 兼容问题, 但它至少不是第一层失败点

### 会推翻主假设的证据

- 如果在把:
  - `CUDA_HOME=.pixi/envs/default/targets/x86_64-linux`
  - `PATH+=.pixi/envs/default/nvvm/bin`
  固化之后, JIT 仍立刻报新的结构性失败, 那就要继续排查版本兼容或链接参数

### 当前结论

- 已验证结论1:
  - 旧修复只补 `nvcc` 还不够
- 已验证结论2:
  - pixi CUDA 根路径必须指向 `targets/x86_64-linux`
- 已验证结论3:
  - `PATH` 里必须包含 `nvvm/bin`, 否则 `cicc` 找不到

## [2026-03-27 01:24:56] [Session ID: 78200] 笔记: `outputs/my4` 已成功导出标准 3DGS PLY

## 来源

### 来源1: `outputs/my4` 结果目录核对

- 当前存在:
  - `outputs/my4/ckpts/ckpt_6999.pt`
  - `outputs/my4/ckpts/ckpt_29999.pt`
- `ckpt_29999.pt` 中的 `splats` 键已验证包含:
  - `means`
  - `opacities`
  - `quats`
  - `scales`
  - `sh0`
  - `shN`

### 来源2: 标准 3DGS PLY 字段顺序核对

- 参考口径:
  - 常见 3DGS / Graphdeco 风格字段顺序
  - `f_dc_0..2`
  - `f_rest_0..44`
  - `opacity`
  - `scale_0..2`
  - `rot_0..3`
- 对当前 checkpoint:
  - `sh0` 形状是 `(251404, 1, 3)`
  - `shN` 形状是 `(251404, 15, 3)`
  - 对应 `sh_degree=3`, 因此 `f_rest` 共 `15 * 3 = 45` 个

### 来源3: 实际导出验证

- 命令:
  - `.pixi/envs/default/bin/python -m recon.export_3dgs_ply --result-dir outputs/my4`
- 关键输出:
  - `checkpoint: outputs/my4/ckpts/ckpt_29999.pt`
  - `output: outputs/my4/point_cloud_29999.ply`
  - `gaussian_count: 251404`
  - `property_count: 62`
- 头部验证:
  - `element vertex 251404`
  - `property float f_rest_44`
  - `property float rot_3`
  - `end_header`
- 文件大小:
  - `62349723` bytes
  - 约 `60M`

## 综合发现

### 代码层

- 已新增:
  - [export_3dgs_ply.py](/root/autodl-tmp/home/rais/FreeFix/recon/export_3dgs_ply.py)
- 脚本支持:
  - `--result-dir` 自动选择最新 checkpoint
  - `--ckpt` 显式指定 checkpoint
  - `--output` 自定义输出文件名

### 产物层

- 已实际生成:
  - [point_cloud_29999.ply](/root/autodl-tmp/home/rais/FreeFix/outputs/my4/point_cloud_29999.ply)

### 结论

- `outputs/my4` 已经成功导出为标准 3DGS PLY
- 当前这份 PLY 不是 COLMAP 稀疏点云, 而是训练后 Gaussian 模型本体

## [2026-03-27 01:41:05] [Session ID: 78200] 笔记: `outputs/my4` 对应的可复现训练 YAML 已落地

## 来源

### 来源1: `outputs/my4/cfg.json`

- 当前保存的是训练结束时写回的 JSON
- 其中 `partition` 已经被训练器展开成:
  - `data/my4/partition.json`

### 来源2: 训练入口代码

- `recon.trainer` 当前入口是:
  - `cfg = tyro.cli(Config)`
- 这说明它默认只吃 CLI 参数, 不能直接加载 YAML
- 同时 `Runner.__init__` 会把:
  - `partition`
  再拼到 `data_dir` 下

### 来源3: 实际恢复策略

- 新建:
  - [recon_my4.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4.yaml)
- 新增:
  - [train_from_yaml.py](/root/autodl-tmp/home/rais/FreeFix/recon/train_from_yaml.py)
- 关键还原点:
  - 把 YAML 中的 `partition` 写回输入态 `partition.json`
  - 不再沿用训练后 JSON 里的已展开路径

### 来源4: 动态验证

- 验证命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my4/recon_my4.yaml --set disable_viewer=true --set max_steps=1 --set result_dir=outputs/my4_yaml_smoke`
- 关键输出:
  - `Trainset Size: 180`
  - `Test Size: 132`
  - `Step: 0 ...`
- 验证后已清理:
  - `outputs/my4_yaml_smoke`

## 综合发现

### 代码层

- YAML 启动入口支持:
  - `--config`
  - `--set key=value` 形式的少量覆盖
- 这样既能保留可读配置, 也能快速做 smoke test

### 结论

- `exp_cfg/my4/recon_my4.yaml` 现在不是“展示用配置”, 而是可实际驱动训练的配置
- `outputs/my4/cfg.json` 更像训练落盘快照
- `exp_cfg/my4/recon_my4.yaml` 才是更适合继续编辑和复现的输入配置

## [2026-03-27 01:27:18] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 笔记: `render_traj` 与 `colmap.Dataset` 的样本字段契约不一致

## 来源

### 来源1: 从 checkpoint 直接导视频的真实失败日志

- 命令:
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4 --result_dir outputs/my4 --data_type colmap --ckpt outputs/my4/ckpts/ckpt_29999.pt --disable_viewer`
- 第一轮现象:
  - 传入 `--partition data/my4/partition.json` 时, 报:
    - `FileNotFoundError: data/my4/data/my4/partition.json`
- 第二轮现象:
  - 去掉 `--partition` 后成功进入 `Running trajectory rendering...`
  - 随后报:
    - `KeyError: 'image_path'`

### 来源2: `recon/trainer.py`

- 关键代码:
  - `render_traj` 在循环里读取:
    - `data["image_path"]`
    - `data["image_name"]`
    - `data["image_size"]`
- 结论:
  - 上层渲染逻辑明确依赖这 3 个字段

### 来源3: `recon/datasets/colmap.py` 与 `recon/datasets/hugsim.py`

- `hugsim.Dataset.__getitem__` 已返回:
  - `image_path`
  - `image_name`
  - `image_size`
- `colmap.Dataset.__getitem__` 在本次修复前只返回:
  - `K`
  - `camtoworld`
  - `image`
  - `image_id`

## 综合发现

### 现象

- 视频导出入口本身是通的
- 真正阻断导出的不是渲染器或 checkpoint, 而是 `colmap.Dataset` 少了共享渲染路径需要的元数据字段

### 当前主假设

- 共享渲染路径默认假设“不同数据集的样本字典结构大体一致”
- `colmap.Dataset` 长期缺字段, 只是之前没有被这条路径打中

### 最强备选解释

- 也可能是 `render_traj` 应该只依赖 `parser` 而不该依赖 `Dataset`
- 但当前最小修复面仍然是补齐数据集字段, 因为:
  - 其他数据集已经是这套契约
  - 上层逻辑无需再分支

### 最小验证

- 新增单测:
  - `tests/test_colmap_dataset_contract.py`
- 验证命令:
  - `.pixi/envs/default/bin/python -m unittest tests.test_colmap_dataset_contract`
- 关键输出:
  - `Ran 1 test in 0.107s`
  - `OK`

### 动态结果

- 重跑导视频命令后:
  - 成功完成 `50/50` 帧渲染
- `ffprobe` 验证:
  - `render.mp4`: `h264`, `1280x720`, `12 fps`, `50` 帧
  - `alpha.mp4`: `h264`, `1280x720`, `12 fps`, `50` 帧

## 结论

- 这次真正被证实的问题, 不是 checkpoint 无法渲染
- 而是 `colmap.Dataset` 与共享渲染路径之间存在一个此前未被覆盖到的字段契约缺口
- 补齐字段并加单测后, `outputs/my4/ckpts/ckpt_29999.pt` 已成功导出视频

## [2026-03-27 02:03:30] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 笔记: `my4` refine 的真实分叉是“Flux 权限”与“SDXL 首次大下载”

## 来源

### 来源1: `Flux` 真实失败日志

- 命令:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my4/flux_shinkai_museum.yaml`
- 关键输出:
  - `GatedRepoError: 401 Client Error`
  - `Cannot access gated repo ... black-forest-labs/FLUX.1-dev`

### 来源2: 机器上的 Hugging Face 登录态核对

- 结果:
  - `~/.huggingface/token`: 不存在
  - `~/.cache/huggingface/token`: 不存在
  - `~/.cache/huggingface/stored_tokens`: 不存在
- 结论:
  - 这不是“环境变量没导出来”那么简单
  - 当前机器确实没有可用 HF 登录态

### 来源3: `SDXL` 回退路线执行

- 命令:
  - `.pixi/envs/default/bin/python -m ours.refine_by_sdxl --exp_cfg exp_cfg/my4/sdxl_shinkai_museum.yaml`
- 现象:
  - 成功进入 `stabilityai/stable-diffusion-xl-refiner-1.0` 下载流程
  - 没有再出现权限错误
- 中断前缓存证据:
  - `~/.cache/huggingface/hub/models--stabilityai--stable-diffusion-xl-refiner-1.0`: 约 `1.1G`
  - `blobs` 文件数: `13`

## 综合发现

### 现象

- 用户给的 prompt 已经可以被本地配置承接
- 真正卡 refine 的不是 prompt 或数据, 而是模型供应链

### 当前主假设

- 如果用户能提供 `FLUX.1-dev` 访问权限, 最贴近当前仓库意图的路线仍是 `Flux`

### 最强备选解释

- 如果用户不想处理 HF gated repo, 那就继续跑 `SDXL`
- 这条路技术上可行, 但首次下载和后续 refine 都会比较久

### 结论

- 当前已经完成:
  - `Flux` 配置落盘
  - `SDXL` 回退配置落盘
  - 两条路的真实运行边界都已用动态证据确认
- 当前尚未完成:
  - 最终 refine 产物

## [2026-03-27 09:39:13] [Session ID: 429732-430781] 笔记: `my4` reconstruction 质量偏低更像“前端几何偏弱 + 训练欠拟合”, 不是单纯 overfit

## 来源

### 来源1: 当前 reconstruction 配置

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4.yaml`
- 关键事实:
  - `max_steps: 30000`
  - `refine_stop_iter: 15000`
  - `strategy: default`
  - `pose_opt: false`
  - `app_opt: false`
  - `depth_loss: false`
  - `data_factor: 1`

### 来源2: 当前数据与 COLMAP 稀疏模型

- 验证命令:
  - `python3 - <<'PY' ... partition.json + PIL ... PY`
  - `.pixi/envs/default/bin/python - <<'PY' from recon.datasets.colmap import Parser ... PY`
- 关键输出:
  - `train_count = 180`
  - `test_count = 132`
  - 图像分辨率 `1280x720`
  - `Parser` 读取到:
    - `312 images`
    - `16062` 个稀疏点
    - `reproj_err_mean = 1.7004`
    - `reproj_err_p90 = 3.1272`
  - 运行时还打印:
    - `Warning: COLMAP Camera is not PINHOLE. Images have distortion.`

### 来源3: reconstruction 与 refine 的量化评测

- 验证命令:
  - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my4/flux_shinkai_museum.yaml --eval_test`
- 产物:
  - `outputs/my4/flux_shinkai_museum/eval/29999_test.json`
  - `outputs/my4/flux_shinkai_museum/eval/29999_train.json`
  - `outputs/my4/flux_shinkai_museum/eval/flux_shinkai_museum_test.json`
  - `outputs/my4/flux_shinkai_museum/eval/flux_shinkai_museum_train.json`
- 关键结果:
  - 原始 reconstruction:
    - test: `PSNR 24.14 / SSIM 0.8197 / LPIPS 0.3309`
    - train: `PSNR 23.93 / SSIM 0.8477 / LPIPS 0.3183`
  - Flux refine:
    - test: `PSNR 20.48 / SSIM 0.7376 / LPIPS 0.3159`
    - train: `PSNR 33.26 / SSIM 0.9513 / LPIPS 0.0860`

### 来源4: `recon.trainer` 与 `colmap.Dataset` 的代码路径

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/trainer.py`
  - `/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py`
- 关键事实:
  - `init_type: sfm` 时, 训练初始化直接依赖 COLMAP 稀疏点
  - `depth_loss` 打开后, 使用的是投影到图像上的 COLMAP 稀疏点深度监督, 不是 `UniDepth`
  - `pose_opt` 会启用相机位姿优化
  - `app_opt` 会启用按图像的 appearance embedding
  - `refine_stop_iter` 控制 GS densify / prune 的结束时刻, 当前只到 `15000`

## 综合发现

### 现象

- `my4` 原始 reconstruction 主观观感“不够锐、不够稳”是合理的, 因为量化结果只有中等水平。
- 原始 reconstruction 在当前评测子集上的 train / test 指标非常接近。
- `Flux refine` 明显提升了 train 指标, 但 test 指标反而下降, 说明它更像风格化和重绘, 不是在补足可泛化的几何。

### 当前主假设

- 当前 reconstruction 质量不高, 更像两个因素叠加:
  - 前端 COLMAP 几何先验偏弱
  - 后端 3DGS 配置偏保守, 导致模型本体仍在欠拟合

### 最强备选解释

- 也可能不是“模型容量不够”, 而是 `my4` 这组评测子集本身视角跨度大、遮挡强, 导致 `24dB` 左右已经接近该数据的现实上限。
- 但当前还缺和“重建后更高质量 COLMAP 版本”或“更长训练版本”的对照证据, 不能直接把它当结论。

### 为什么当前更像欠拟合而不是 overfit

- 原始 reconstruction 的 train / test 指标没有出现明显鸿沟。
- 如果是典型 overfit, 训练视角通常会显著高于测试视角。
- 现在更像“训练视角自己都还没拟合到足够细”, 所以先该想的是补几何和补训练, 不是先压正则。

## 结论

- 优先级最高的提升方向不是继续调 `Flux prompt`, 而是先把 reconstruction 本体做强。
- 最有把握的三个杠杆是:
  - 提升 COLMAP 稀疏模型质量
  - 延长 densify / prune 有效窗口并增加总训练步数
  - 对 `my4` 这种自采集场景尝试 `pose_opt` / `app_opt` / `depth_loss`
- 其中:
  - `pose_opt` 更偏向修相机位姿误差
  - `app_opt` 更偏向修曝光或颜色不一致
  - `depth_loss` 更偏向在稀疏点基础上补一点几何约束

## [2026-03-27 09:59:58] [Session ID: 429732-430781] 笔记: 人工删图后的 `prepare_colmap_scene` 需要同时收敛图片目录、数据库和 partition 名单

## 来源

### 来源1: 用户复现命令与原始报错

- 命令:
  - `python3 -m recon.prepare_colmap_scene --source-dir data/my4 --dest-dir /root/autodl-tmp/home/rais/FreeFix/data/my4_rebuild --rebuild-sparse --colmap-binary /home/rais/.local/opt/colmap-env/bin/colmap --force`
- 原始错误:
  - `FileNotFoundError: 源图片不存在: /root/autodl-tmp/home/rais/FreeFix/data/my4/images/000024.png`

### 来源2: 现有 `data/my4` 的动态核对

- 验证命令:
  - `python3 - <<'PY' ... images vs database.db vs partition_source_names.json ... PY`
- 关键输出:
  - `images/` 真实图片数: `264`
  - `database.db images` 表记录数: `312`
  - 缺失文件但仍残留在数据库里的图片: `48`
  - `meta/partition_source_names.json` 中:
    - train 旧名残留: `28`
    - test 旧名残留: `20`

### 来源3: `prepare_colmap_scene.py` 旧逻辑

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/prepare_colmap_scene.py`
- 旧行为:
  - `choose_image_names()` 优先使用 `database.db(images table)`
  - `copy_selected_images()` 遇到缺图直接抛异常
  - 读取 partition 名单时只认源目录根级 `colmap_train_images.txt` / `colmap_test_images.txt`
  - 即使传了 `--rebuild-sparse`, 只要源目录还有旧 `sparse/`, 仍会直接复制旧模型

## 综合发现

### 现象

- 这次不是单个图片路径写错。
- 而是用户删图后, 三份状态已经分叉:
  - `images/`
  - `database.db`
  - `meta/partition_source_names.json`

### 当前主假设

- 原始报错的直接触发点是 `database.db` 仍保留旧图名。
- 但真正需要修复的是“删图后的数据一致性收敛”, 不是在拷图时简单跳过异常。

### 最强备选解释

- 即使只修掉 `FileNotFoundError`, 如果 `--rebuild-sparse` 仍继续复制旧 `sparse/`, 最终结果还是会继续吃到过期模型。
- 因此这次必须连 `--rebuild-sparse` 的优先级一起修。

## 结论

- 对“已经导入到 FreeFix、后来又手工删图”的场景, 正确处理应该是:
  - 先按磁盘真实图片过滤旧清单
  - 同步清理复制后的 `database.db`
  - 从 `meta/partition_source_names.json` 回退读取原 train/test 名单
  - 显式传 `--rebuild-sparse` 时, 强制走 mapper 重建, 不再复制旧 `sparse/`
- 动态验证已经证明修复命中真实失败路径:
  - 修复后 `COLMAP` 加载阶段显示的图片数变成 `264`
  - mapper 已持续进入真实重建和图像注册过程, 没有再回到原始缺图报错

## [2026-03-27 04:46:05] [Session ID: 20260327T044605Z-main] 笔记: `my4_fullcolmap_quality` 两档评测结果与总览图已整理完成

## 来源

### 来源1: 两套评测指标文件

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_9999/stats/val_step9999.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_49999/stats/val_step49999.json`
- 关键结果:
  - `ckpt_9999.pt`
    - `PSNR = 23.186845779418945`
    - `SSIM = 0.8350304961204529`
    - `LPIPS = 0.2546704411506653`
    - `num_GS = 300253`
  - `ckpt_49999.pt`
    - `PSNR = 22.832536697387695`
    - `SSIM = 0.8252953886985779`
    - `LPIPS = 0.2585321366786957`
    - `num_GS = 373083`

### 来源2: 两套评测图片目录计数

- 验证命令:
  - `find outputs/my4_fullcolmap_quality_eval_9999/renders/{concat,rgbs,alphas} -maxdepth 1 -type f | wc -l`
  - `find outputs/my4_fullcolmap_quality_eval_49999/renders/{concat,rgbs,alphas} -maxdepth 1 -type f | wc -l`
- 关键结果:
  - `9999`: `concat=112`, `rgbs=112`, `alphas=112`
  - `49999`: `concat=112`, `rgbs=112`, `alphas=112`

### 来源3: 本轮新整理的总览图

- 新产物:
  - [summary_compare.png](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_compare/summary_compare.png)
  - [summary_compare_web.jpg](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_compare/summary_compare_web.jpg)
- 组成方式:
  - 上半部分对比两档 `preview_concat_grid.png`
  - 下半部分对比两档 `preview_rgb_grid.png`
  - 头部直接写入两档的 `PSNR / SSIM / LPIPS`

## 综合发现

### 现象

- 当前这条“更干净 COLMAP + 更积极训练参数”的线上, 已评测的两档 checkpoint 都能稳定出图。
- 但最终步 `49999` 没有继续提升测试集指标。
- 从总览图肉眼看, 两者整体风格接近, 但 `9999` 这一档在当前对照里更值得保留。

### 当前结论

- 这是已验证结论, 不是猜测:
  - 在当前已评测的两档里, `ckpt_9999.pt` 优于 `ckpt_49999.pt`
- 当前最适合直接给用户查看的图片是:
  - [summary_compare_web.jpg](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_compare/summary_compare_web.jpg)
  - [preview_concat_grid.png](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_9999/renders/preview_concat_grid.png)
  - [preview_rgb_grid.png](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_9999/renders/preview_rgb_grid.png)

### 实施含义

- 下一轮不要默认“训练更久就更好”。
- 更合理的方向是:
  - 继续补中间 checkpoint 对照, 例如 `29999`
  - 或者直接把 `9999` 作为当前更推荐的交付 checkpoint

## [2026-03-27 05:42:42] [Session ID: 20260327T012145Z-main] 笔记: `my4_fullcolmap_quality` 的 `ckpt_49999.pt` 已导出轨迹视频

## 来源

### 来源1: YAML 导出入口

- 命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my4/recon_my4_fullcolmap_quality.yaml --set ckpt=outputs/my4_fullcolmap_quality/ckpts/ckpt_49999.pt`
- 关键输出:
  - `[Parser] 264 images`
  - `Trainset Size: 152`
  - `Test Size: 112`
  - `Running trajectory rendering...`
  - `Rendering trajectory: 100%|...| 50/50`

### 来源2: 输出目录核对

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality/to_refine`
- 核对结果:
  - `render.mp4`
  - `alpha.mp4`
  - `renders`: `50`
  - `alphas`: `50`
  - `depths`: `50`
  - `gts`: `50`

### 来源3: 视频元数据

- `ffprobe` 结果:
  - `render.mp4`
    - `1232x688`
    - `12 fps`
    - `50` 帧
    - `4.167s`
  - `alpha.mp4`
    - `1232x688`
    - `12 fps`
    - `50` 帧
    - `4.167s`
- 运行时 warning:
  - 原始输入尺寸 `1228x687`
  - `imageio/ffmpeg` 自动补到 `1232x688`

## 综合发现

### 当前结论

- `ckpt_49999.pt` 的轨迹视频已经成功导出
- 这次视频导出没有暴露新的 `app_opt` / `pose_opt` 兼容 bug
- 唯一需要记住的是:
  - 编码输出尺寸不是原始渲染尺寸
  - 为了视频兼容性, 编码层自动补齐到了 16 的倍数

### 实施含义

- 如果后面还要继续导 `9999` 或 `29999` 的轨迹视频, 最好都保留带 checkpoint 名的副本文件
- 否则 `to_refine/render.mp4` 这类默认文件名会互相覆盖

## [2026-03-27 05:42:42] [Session ID: 20260327T012145Z-main] 笔记: `49999` 视频的重影和结构问题, 当前更像 checkpoint 退化而不是导出失败

## 来源

### 来源1: 三档 checkpoint 评测结果

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_9999/stats/val_step9999.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_29999/stats/val_step29999.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_49999/stats/val_step49999.json`
- 已验证结论:
  - `PSNR`: `9999 > 49999 > 29999`
  - `LPIPS`: `9999 < 49999 < 29999`
  - `9999` 明显优于后两档
- 伴随现象:
  - `num_GS`
    - `9999 = 300253`
    - `29999 = 373083`
    - `49999 = 373083`
  - 高斯数量继续增大后, 指标没有跟着变好

### 来源2: `49999` 视频导出结果

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality/to_refine/render_ckpt_49999.mp4`
- 动态证据:
  - 导出命令成功跑完 `50/50`
  - `ffprobe` 正常
  - 没有出现新的渲染报错
- 结论:
  - “视频文件坏了” 这条解释缺少证据支持
  - 当前更像是 checkpoint 本身已经不理想

### 来源3: 当前增强训练配置

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_quality.yaml`
- 关键配置:
  - `max_steps: 50000`
  - `refine_stop_iter: 30000`
  - `pose_opt: true`
  - `app_opt: true`
  - `depth_loss: true`

## 综合发现

### 现象

- 用户看到的“重影、结构不好”与现有指标退化方向一致
- 说明这不是纯视觉错觉, 也不是单纯视频编码导致

### 当前主假设

- 这条增强训练线在 `9999` 之后已经进入退化区
- 后半程的继续优化没有换来更好的结构, 反而更可能把几何和外观拉松

### 最强备选解释

- `app_opt` 和 `pose_opt` 在长窗口里放大了跨视角漂移
- 但这是候选假设, 还缺少消融实验来把责任归到单一模块

### 当前结论

- 这是当前最稳的已验证结论:
  - 先不要继续围绕 `49999` 做 refine 或继续导出更多结果
  - 当前更应该回退到 `9999`
- 如果还要进一步提质量, 下一轮最值得做的是:
  - 缩短训练窗口
  - 提前保存更多 checkpoint
  - 先关掉 `app_opt`, 再看重影是否明显下降

## [2026-03-27 04:55:05] [Session ID: 20260327T045120Z-main] 笔记: `ckpt_29999.pt` 已完成同口径评测, 三档 checkpoint 排名已明确

## 来源

### 来源1: `ckpt_29999.pt` 手动评测

- 命令入口:
  - `.pixi/envs/default/bin/python`
  - `load_config(...) + Runner.eval(step)`
- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_29999/stats/val_step29999.json`
- 关键结果:
  - `PSNR = 22.793073654174805`
  - `SSIM = 0.8258392810821533`
  - `LPIPS = 0.26746416091918945`
  - `num_GS = 373083`

### 来源2: `29999` 图片目录与预览图

- 验证命令:
  - `find outputs/my4_fullcolmap_quality_eval_29999/renders/{concat,rgbs,alphas} -maxdepth 1 -type f | wc -l`
- 关键结果:
  - `concat = 112`
  - `rgbs = 112`
  - `alphas = 112`
- 新产物:
  - [preview_concat_grid.png](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_29999/renders/preview_concat_grid.png)
  - [preview_rgb_grid.png](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_29999/renders/preview_rgb_grid.png)

### 来源3: 三档汇总排序与总览图

- 排序验证命令:
  - `python3 - <<'PY' ... sorted(items, key=lambda x: x['psnr'], reverse=True) ... PY`
- 排序结果:
  - `by_psnr`
    - `9999 > 49999 > 29999`
  - `by_lpips`
    - `9999 > 49999 > 29999`
- 新产物:
  - [summary_compare_3way.png](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_compare/summary_compare_3way.png)
  - [summary_compare_3way_web.jpg](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_compare/summary_compare_3way_web.jpg)

## 综合发现

### 现象

- 三档 checkpoint 都能稳定完成同一 test split 的手动评测。
- `29999` 没有追平 `9999`。
- `29999` 和 `49999` 的 `num_GS` 都是 `373083`, 说明至少从高斯数量上看, 后半程没有再出现新的结构优势。

### 当前结论

- 这是已验证结论:
  - 在当前可比的三档里, `ckpt_9999.pt` 最好。
- 具体排名:
  - `PSNR`: `9999 (23.1868) > 49999 (22.8325) > 29999 (22.7931)`
  - `LPIPS`: `9999 (0.2547) < 49999 (0.2585) < 29999 (0.2675)`
  - `SSIM`: `9999 (0.8350)` 明显高于另外两档, 而 `29999` 与 `49999` 很接近

### 实施含义

- 当前证据已经足够支持:
  - 这条增强训练线不该默认取最终步
  - `9999` 更适合作为当前交付候选 checkpoint
- 如果还要继续提质量, 更值得做的是:
  - 调整 checkpoint 保存频率, 把更早阶段保留得更细
  - 重新审视 densify 窗口和后半程优化强度

## [2026-03-27 14:21:07] [Session ID: 20260327T141244Z-main] 笔记: `stable_12k` 对照实验已完成, 组合策略显著优于旧 `quality` 线

## 来源

### 来源1: `9999` 轨迹视频导出

- 命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my4/recon_my4_fullcolmap_quality.yaml --set ckpt=outputs/my4_fullcolmap_quality/ckpts/ckpt_9999.pt`
- 关键产物:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality/to_refine/render_ckpt_9999.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality/to_refine/alpha_ckpt_9999.mp4`
- 元数据:
  - `h264`
  - `1232x688`
  - `12 fps`
  - `50` 帧
  - `4.166667s`

### 来源2: `stable_12k` 配置、smoke test 与真实训练

- 配置文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_stable_12k.yaml`
- 本轮修改:
  - `max_steps: 12000`
  - `eval_steps/save_steps: [3000, 6000, 9000, 12000]`
  - `refine_stop_iter: 9000`
  - `app_opt: false`
  - 保留 `pose_opt: true`
  - 保留 `depth_loss: true`
- smoke test 命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my4/recon_my4_fullcolmap_stable_12k.yaml --set result_dir=outputs/my4_fullcolmap_stable_12k_smoke --set max_steps=1 --set eval_steps=[1] --set save_steps=[1]`
- smoke test 关键输出:
  - `loss=0.259`
  - `depth loss=3.990623`
  - `Step 0 {'num_GS': 27521, ...}`
- 真实训练关键结果:
  - `outputs/my4_fullcolmap_stable_12k/ckpts/ckpt_2999.pt`
  - `outputs/my4_fullcolmap_stable_12k/ckpts/ckpt_5999.pt`
  - `outputs/my4_fullcolmap_stable_12k/ckpts/ckpt_8999.pt`
  - `outputs/my4_fullcolmap_stable_12k/ckpts/ckpt_11999.pt`
  - `outputs/my4_fullcolmap_stable_12k/stats/train_step11999.json`
- 最终训练统计:
  - `num_GS = 268776`
  - `ellipse_time = 129.38757491111755`

### 来源3: `stable_12k` 最终视频与手动评测

- 轨迹视频:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k/to_refine/render_ckpt_11999.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k/to_refine/alpha_ckpt_11999.mp4`
- 视频元数据:
  - `h264`
  - `1232x688`
  - `12 fps`
  - `50` 帧
  - `4.166667s`
- 手动评测目录:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_eval_11999`
- 指标文件:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_eval_11999/stats/val_step11999.json`
- 关键结果:
  - `PSNR = 25.949283599853516`
  - `SSIM = 0.8617827892303467`
  - `LPIPS = 0.22198344767093658`
  - `num_GS = 268776`
- 图片完整性:
  - `concat/rgbs/alphas` 共 `336` 个文件
  - 对应 `112` 张 test 图 * `3` 个子目录

## 综合发现

### 现象

- 在同一 `data/my4_fullcolmap`、同一 test split 下, 新的 `stable_12k` 组合实验显著优于旧 `quality` 线里已经评过的三档 checkpoint。
- 已验证对比:
  - `stable_12k @ 11999`: `PSNR 25.9493 / SSIM 0.8618 / LPIPS 0.2220 / GS 268776`
  - `quality @ 9999`: `PSNR 23.1868 / SSIM 0.8350 / LPIPS 0.2547 / GS 300253`
  - `quality @ 29999`: `PSNR 22.7931 / SSIM 0.8258 / LPIPS 0.2675 / GS 373083`
  - `quality @ 49999`: `PSNR 22.8325 / SSIM 0.8253 / LPIPS 0.2585 / GS 373083`
- 从结果上看, 这次不仅 test 指标更高, 高斯数量也更收敛。

### 当前假设

- 当前主假设:
  - “更短训练窗口 + 更早收住 densify + 关闭 `app_opt`” 这组组合, 更适合 `my4_fullcolmap` 这条线。
- 最强备选解释:
  - 主要收益也可能来自“训练别拖到后半程退化区”和“densify 提前停”, `app_opt` 只是次要因素。
- 能推翻当前主假设的证据:
  - 如果后续做消融时发现:
    - 只缩短训练窗口, 不关 `app_opt`, 结果同样达到当前水平
    - 或只关 `app_opt`, 但维持旧长窗口, 仍然明显退化
  - 那就说明这次不能把收益直接归到 `app_opt` 本身。

### 当前结论

- 这是已验证结论:
  - `stable_12k` 这套组合策略目前是这条线里最好的已验证结果。
  - 当前主交付候选应该从旧 `quality 9999` 进一步切换到:
    - `stable_12k 11999`
- 这也是已验证结论:
  - 本轮实验证明了“继续长训 + 保持 `app_opt=true`”并不是当前这条线的优先方向。
- 这还不是已验证结论:
  - “根因就是 `app_opt`”
  - 因为这轮同时改了多个变量, 还缺单因素消融证据。

### 实施含义

- 当前最实用的下一步不是继续做 refine。
- 更值钱的是:
  - 先围绕 `9000-12000` 做更细 checkpoint 扫描
  - 再单独拆分:
    - `app_opt`
    - `refine_stop_iter`
    - `max_steps`
  做消融

## [2026-03-27 14:33:22] [Session ID: 20260327T142526Z-main] 笔记: `app_opt` 单因素消融已完成, 当前证据已能直接说明它是主要影响因素

## 来源

### 来源1: `app_opt` 单因素消融配置

- 配置文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_stable_12k_app.yaml`
- 这轮与上一轮 `stable_12k` 的静态差异:
  - 只改:
    - `app_opt: false -> true`
- 保持不变:
  - `max_steps = 12000`
  - `refine_stop_iter = 9000`
  - `pose_opt = true`
  - `depth_loss = true`
  - `save/eval = [3000, 6000, 9000, 12000]`

### 来源2: smoke test 与真实训练

- smoke test 命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my4/recon_my4_fullcolmap_stable_12k_app.yaml --set result_dir=outputs/my4_fullcolmap_stable_12k_app_smoke --set max_steps=1 --set eval_steps=[1] --set save_steps=[1]`
- smoke test 关键输出:
  - `loss=0.314`
  - `depth loss=1.331720`
  - `Step 0 {'num_GS': 27521, ...}`
- 真实训练产物:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app/ckpts/ckpt_2999.pt`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app/ckpts/ckpt_5999.pt`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app/ckpts/ckpt_8999.pt`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app/ckpts/ckpt_11999.pt`
- 最终训练统计:
  - `num_GS = 269035`
  - `ellipse_time = 168.34088015556335`

### 来源3: 最终视频与手动评测

- 轨迹视频:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app/to_refine/render_ckpt_11999.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app/to_refine/alpha_ckpt_11999.mp4`
- 视频元数据:
  - `h264`
  - `1232x688`
  - `12 fps`
  - `50` 帧
  - `4.166667s`
- 手动评测目录:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app_eval_11999`
- 指标文件:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app_eval_11999/stats/val_step11999.json`
- 关键结果:
  - `PSNR = 23.263328552246094`
  - `SSIM = 0.8354071378707886`
  - `LPIPS = 0.24856092035770416`
  - `num_GS = 269035`
- 图片完整性:
  - `concat/rgbs/alphas` 共 `336` 个文件

## 综合发现

### 现象

- 同样是 `12000 / refine_stop_iter=9000` 这一套短窗设置:
  - `app_opt=false` 时:
    - `PSNR 25.9493`
    - `SSIM 0.8618`
    - `LPIPS 0.2220`
    - `GS 268776`
  - `app_opt=true` 时:
    - `PSNR 23.2633`
    - `SSIM 0.8354`
    - `LPIPS 0.2486`
    - `GS 269035`
- 两轮的高斯数量很接近。
- 但 test 指标出现了明显回落。

### 假设验证

- 上一轮主假设:
  - `app_opt=false` 可能是大收益来源之一
- 当前静态证据:
  - 两轮配置只差 `app_opt`
- 当前动态证据:
  - `PSNR` 从 `25.9493` 回落到 `23.2633`
  - `SSIM` 从 `0.8618` 回落到 `0.8354`
  - `LPIPS` 从 `0.2220` 恶化到 `0.2486`
- 当前结论:
  - 在当前这组实验里, `app_opt` 不是边缘因素
  - 它就是主要影响因素

### 当前结论

- 这是已验证结论:
  - 在 `my4_fullcolmap` 这条线上, 保持短窗口不变时, `app_opt=true` 会显著拉低 test 质量
  - `app_opt=false` 是上一轮大幅提升的主要来源
- 这也是已验证结论:
  - “只缩短训练窗口” 本身不够
  - 因为 `app_opt=true` 的这轮结果:
    - 只比旧 `quality 9999` 略好一点
    - 但远远追不上 `stable_12k app_opt=false`
- 仍未确认的部分:
  - 这种结论在别的场景上是否同样成立
  - 当前还只是 `my4_fullcolmap` 这一条线的证据

### 实施含义

- 这条线后续默认不该再开 `app_opt=true`。
- 更值得继续做的是:
  - 在 `app_opt=false` 前提下, 细扫 `9000-12000`
  - 再视需要拆 `refine_stop_iter` 和 `max_steps`

## [2026-03-27 06:55:58] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 笔记: `stable_12k_dense` 四档 checkpoint 手动评测结果

## 来源

### 来源1: 四档手动评测脚本

- 命令:
  - `PYTHONPATH=/root/autodl-tmp/home/rais/FreeFix .pixi/envs/default/bin/python /tmp/eval_my4_dense_4way.py`
- 产物:
  - `outputs/my4_fullcolmap_stable_12k_dense_eval_8999/stats/val_step8999.json`
  - `outputs/my4_fullcolmap_stable_12k_dense_eval_9999/stats/val_step9999.json`
  - `outputs/my4_fullcolmap_stable_12k_dense_eval_10999/stats/val_step10999.json`
  - `outputs/my4_fullcolmap_stable_12k_dense_eval_11999/stats/val_step11999.json`
  - `outputs/my4_fullcolmap_stable_12k_dense_eval_compare/summary_4way.json`

## 综合发现

### 现象

- 四档真实评测结果如下:
  - `8999`: `PSNR 25.609825 / SSIM 0.857044 / LPIPS 0.235052`
  - `9999`: `PSNR 25.758595 / SSIM 0.859877 / LPIPS 0.228324`
  - `10999`: `PSNR 25.851439 / SSIM 0.860771 / LPIPS 0.224138`
  - `11999`: `PSNR 25.933811 / SSIM 0.861717 / LPIPS 0.221569`
- `num_GS` 四档都保持 `272245`
- 在这次扫描窗口内:
  - `PSNR` 持续上升
  - `SSIM` 持续上升
  - `LPIPS` 持续下降

### 当前主假设

- 当前主假设:
  - 这条 `app_opt=false` 线的更优点可能还在 `12000` 之后的一小段

### 最强备选解释

- 备选解释:
  - `11999` 已经非常接近平台期
  - 即便继续往后走, 收益也可能很小

### 已验证结论

- 在本次真实扫描区间 `8999/9999/10999/11999` 中:
  - `11999` 是 `PSNR` 最优
  - `11999` 是 `SSIM` 最优
  - `11999` 是 `LPIPS` 最优
- 因此当前默认最佳 checkpoint 应保持为:
  - `outputs/my4_fullcolmap_stable_12k_dense/ckpts/ckpt_11999.pt`

### 仍未确认的部分

- 还没有动态证据证明:
  - `12000` 之后会继续提升
  - 或者已经开始进入平台期
- 如果要把“是否值得超过 12000”说死, 还需要做下一段扩展扫描

## [2026-03-27 07:20:45] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 笔记: `stable_12k_dense` 最佳结果入口已补齐

## 来源

### 来源1: `stable_12k_dense` 结果目录核对

- 目录:
  - `outputs/my4_fullcolmap_stable_12k_dense/`
- 现象:
  - 原先只有 `cfg/ckpts/stats/tb`
  - 没有自己的 `to_refine/`
  - 也没有“最佳结果入口文件”

### 来源2: `ckpt_11999` 轨迹视频导出

- 命令:
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4_fullcolmap --result_dir outputs/my4_fullcolmap_stable_12k_dense --data_type colmap --ckpt outputs/my4_fullcolmap_stable_12k_dense/ckpts/ckpt_11999.pt --disable_viewer`
- 动态结果:
  - 成功完成 `50/50` 帧 trajectory rendering
  - 实际生成:
    - `to_refine/render.mp4`
    - `to_refine/alpha.mp4`

### 来源3: 文档与 manifest 落盘

- 新增:
  - `outputs/my4_fullcolmap_stable_12k_dense/BEST_RESULT.md`
  - `outputs/my4_fullcolmap_stable_12k_dense/best_result_manifest.json`
- 修正:
  - `cmd.md` 中 best checkpoint 导视频产物名

## 综合发现

### 现象

- 当前 best 方法已经不再只是“一个好 checkpoint”
- 它现在有了完整交付入口:
  - 视频
  - json 指标
  - summary
  - 可读文档
  - 机器可读 manifest

### 已验证结论

- `stable_12k_dense` 目录现在已经可以直接作为这条方法线的主交付目录
- 之后如果只想找当前 best, 直接从这两个入口进入就够了:
  - `BEST_RESULT.md`
  - `best_result_manifest.json`

### 额外发现

- 标准 `recon.trainer --ckpt` 导视频的默认产物名是:
  - `render.mp4`
  - `alpha.mp4`
- 不是 checkpoint 名字拼进文件名的形式
- 这次已经把 `cmd.md` 的旧口径修正了

## [2026-03-27 07:26:36] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 笔记: 把 `PSNR 25.93` 推到 `28-29` 的现有抓手判断

## 来源

### 来源1: 最近两天的真实实验结论

- 已验证:
  - `quality 9999`: `PSNR 23.1868`
  - `stable_12k 11999`: `PSNR 25.9493`
  - `stable_12k_dense 11999`: `PSNR 25.9338`
- 含义:
  - 大收益来自“更干净数据 + 更稳训练窗口 + `app_opt=false`”
  - 不是单纯把训练步数拉长

### 来源2: 当前代码抓手扫描

- `recon/convert.py` 里已有:
  - COLMAP feature/matching/mapper/undistort 流程
  - `--resize`
  - `Mapper.ba_global_function_tolerance`
- 当前没有看到针对 `colmap` 训练集直接消费现成前景/动态遮罩的通路
- 当前训练已在:
  - `data_factor=1`
  - 原分辨率 undistort 图
  下运行

## 综合发现

### 现象

- 当前 best 是 `PSNR 25.9338`
- 距离 `28` 还差约 `2.07 dB`
- 距离 `29` 还差约 `3.07 dB`

### 当前主假设

- 如果目标真的是 `28-29`, 主收益不太像会来自“把 12k 继续拉到 16k”
- 更像会来自:
  - 更干净的帧集合
  - 更强的 COLMAP 重建
  - 动态/坏帧处理
  - 在此基础上的二轮训练细调

### 最强备选解释

- 也有一种可能:
  - 当前 test split 本身更难
  - 单一改动很难贡献 `2-3 dB`
  - 需要多项优化叠加才行

### 当前结论

- 已验证结论:
  - 继续小修小补训练窗口, 很适合追最后 `0.1-0.4 dB`
  - 但如果目标是直接冲 `28-29`, 不能只盯着训练步数
- 当前仍未验证:
  - 哪一种“数据侧提升”在 `my4_fullcolmap` 上最值钱

## [2026-03-27 07:46:05] [Session ID: 20260327T074108Z-main] 笔记: `my4_fullcolmap` 坏帧审计的第一版保守删图口径

## 来源

### 来源1: `data/my4_fullcolmap/meta/frame_audit_report.json`

- 要点:
  - 总候选统计:
    - `blur=32`
    - `dark=27`
    - `bright=27`
    - `duplicate=12`
  - 自动候选总并集是 `95`, 明显偏大
  - 交集里最醒目的帧:
    - `000289.png`: `blur + dark`
    - `000409.png`: `blur + dark`
    - `000087.png`: `blur + duplicate`

### 来源2: `data/my4_fullcolmap/meta/partition_source_names.json`

- 要点:
  - 当前 split 是:
    - `train=152`
    - `test=112`
  - 自动候选并不是全在 train:
    - `blur`: train `26`, test `6`
    - `dark`: train `15`, test `12`
    - `bright`: train `14`, test `13`
    - `duplicate`: train `8`, test `4`

### 来源3: 邻帧拼图复核与 blur 相对邻帧比值

- 复核方式:
  - 把重点候选和前后邻帧并排
  - 再补算 `当前帧 blur / 前后邻帧 blur 均值`
- 关键现象:
  - `000164.png`: `ratio=0.7969`
  - `000084.png`: `ratio=0.8051`
  - `000328.png`: `ratio=0.8387`
  - `000002.png`: `ratio=0.8755`
  - `000166.png`: `ratio=0.8802`
  - `000207.png`: `ratio=0.8860`
  - `000289.png`: `ratio=0.8864`, 同时 `blur + dark`
  - `000087.png`: `ratio=0.9614`, 但它是 `blur + duplicate`

## 综合发现

### 现象

- 自动报告能快速给出候选池, 但 `95` 张并不能直接拿来删。
- 如果 test 帧也一起删, 后续 PSNR 将失去和当前 best 的直接可比性。
- 一批 train 帧在视觉上确实比前后邻帧更糊, 而且 blur 比值也同步偏低。

### 当前假设

- 第一轮只移除少量 train blur outlier, 有机会同时改善:
  - COLMAP 注册与稀疏重建稳定性
  - 后续训练的几何一致性
- 但这还只是“值得验证的方向”, 不是已确认根因。

### 最强备选解释

- 当前 PSNR 上不去, 也可能主要不是坏帧数量问题。
- 更大的瓶颈可能在:
  - 原始相机轨迹质量
  - 动态物体干扰
  - 或当前场景本身的 test 难度

### 会推翻当前假设的证据

- 如果 `v2` 重建和复训后, 指标没有改善, 或者几何更差, 那说明这套 v1 删图口径不成立。

### 当前结论

- 第一版先采用 train-only 的保守删图名单:
  - `000002.png`
  - `000084.png`
  - `000087.png`
  - `000164.png`
  - `000166.png`
  - `000207.png`
  - `000289.png`
  - `000328.png`
- 暂列 hold:
  - `000125.png`
- 明确保留:
  - `000409.png`, 因为它在 test split

## [2026-03-27 08:13:45] [Session ID: 20260327T074108Z-main] 笔记: `my4_fullcolmap_v2` 已完成第一轮动态验证

## 来源

### 来源1: `python3 recon/convert.py --source_path data/my4_fullcolmap_v2 ...`

- 动态结果:
  - COLMAP 完成:
    - feature extraction
    - exhaustive matching
    - mapper
    - image undistorter
  - mapper 结束日志包含:
    - `Keeping successful reconstruction`
    - `Reconstruction with 256 images and 27135 points`
- 过程警告:
  - 多次出现 `Linear solver failure`
  - 但没有导致最终 reconstruction 被丢弃

### 来源2: 原场景与 `v2` 的 sparse 对比

- `data/my4_fullcolmap`:
  - `registered_images=264`
  - `points3d=27521`
- `data/my4_fullcolmap_v2`:
  - `registered_images=256`
  - `points3d=27135`

### 来源3: `v2 partition` 与 parser smoke test

- `partition.json`:
  - `warnings=[]`
  - `train=144`
  - `test=112`
- parser / dataset smoke test:
  - `[Parser] 256 images, taken by 1 cameras.`
  - `point_count=27135`
  - `train_len=144`
  - `test_len=112`
  - `image_shape=(689, 1227, 3)`

## 综合发现

### 现象

- 删掉 8 张保守 train 帧后, `v2` 仍然把全部 `256` 张保留图都注册进去了。
- 点云规模只比原场景少了 `386` 个 points3D。
- test split 完整保留, 没有在 partition 生成时掉图。

### 当前假设

- 这版保守清洗至少没有破坏几何入口。
- 因此现在最值得做的下一步, 已经不是继续挑图, 而是直接看训练指标是否有正向变化。

### 最强备选解释

- 即使重建层面稳定, 训练指标也未必会更好。
- 因为删掉的 8 张图, 也可能本来就对最终 test 误差影响不大。

### 会推翻当前假设的证据

- 如果 `v2` smoke test 或正式训练出现:
  - 读取异常
  - 明显更差的 early eval
  - 或最终指标不升反降
- 那就说明“保守删图 v1”还不够值钱, 甚至方向不对。

### 当前结论

- `v2` 已经通过了“可重建、可分区、可读取”这三关。
- 下一步应该直接进入训练验证。

## [2026-03-27 08:30:49] [Session ID: 20260327T074108Z-main] 笔记: `v2 stable_12k_dense` 的完整训练与四档评测结论

## 来源

### 来源1: `outputs/my4_fullcolmap_v2_stable_12k_dense`

- 动态结果:
  - `stable_12k_dense` 在 `v2` 上完整跑到 `12000` 步
  - 保存了四档 checkpoint:
    - `8999`
    - `9999`
    - `10999`
    - `11999`
  - 还补导了 `11999` 的轨迹视频

### 来源2: `outputs/my4_fullcolmap_v2_stable_12k_dense_eval_compare/summary_4way.json`

- 四档真实 test 指标:
  - `8999`: `25.8214 / 0.8585 / 0.2367`
  - `9999`: `25.9327 / 0.8607 / 0.2335`
  - `10999`: `26.0303 / 0.8613 / 0.2285`
  - `11999`: `26.0887 / 0.8617 / 0.2257`

### 来源3: 与原 `stable_12k_dense` 的逐档对照

- `8999`: `PSNR +0.2115`, `SSIM +0.0014`, `LPIPS +0.0017`
- `9999`: `PSNR +0.1741`, `SSIM +0.0008`, `LPIPS +0.0052`
- `10999`: `PSNR +0.1789`, `SSIM +0.0005`, `LPIPS +0.0044`
- `11999`: `PSNR +0.1549`, `SSIM -0.0000`, `LPIPS +0.0041`

## 综合发现

### 现象

- 这轮保守删图在四档 checkpoint 上都稳定抬高了 PSNR。
- `11999` 依旧是新线里最好的 PSNR 点。
- 但 `LPIPS` 没跟着一起变好, 反而略差。

### 当前假设

- train-only blur cleanup 更像是在帮:
  - 几何一致性
  - 平均像素误差
- 但它未必天然改善感知质量。

### 最强备选解释

- `LPIPS` 变差也可能不是清洗本身的问题。
- 也可能是当前训练策略在更干净数据上, 还缺少另一类 appearance 调节。

### 会推翻当前假设的证据

- 如果下一轮更激进清洗后:
  - PSNR 不再继续涨
  - 或 LPIPS 明显恶化
- 那就说明当前这条路的边际收益已经快到头了。

### 当前结论

- 这轮结论可以明确说成:
  - “保 test 不动, 只清 train blur outlier, 会稳定抬高 PSNR”
- 但还不能说成:
  - “这种清洗会让整体画质全面变好”
- 因为当前证据显示:
  - `PSNR` 变好
  - `SSIM` 基本持平
  - `LPIPS` 略差

## [2026-03-27 09:12:16] [Session ID: 20260327T091216Z-main] 笔记: `v2 best` 已具备直接平移旧 Flux refine 配置的条件

## 来源

### 来源1: `outputs/my4_fullcolmap_v2_stable_12k_dense`

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/cfg.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/ckpts/ckpt_11999.pt`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/to_refine/render.mp4`
- 要点:
  - `cfg.json` 已完整存在, `gs_cfg_file` 继续用默认 `cfg.json` 即可。
  - 当前 best checkpoint 是 `ckpt_11999.pt`。
  - `to_refine/render.mp4` 元数据是:
    - `1232x704`
    - `12 fps`
    - `50` 帧

### 来源2: 旧 `my4` refine 配置与历史记录

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`
  - `/root/autodl-tmp/home/rais/FreeFix/WORKLOG__colmap_my4.md`
- 要点:
  - 旧 refine 已验证本地 `ModelScope FLUX` 路径可用:
    - `/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`
  - 旧配置的视角范围是:
    - `train_start_idx: 0`
    - `train_end_idx: 30`
    - `refine_start_idx: 30`
    - `refine_end_idx: 80`
  - 历史动态证据已经记录过:
    - 长 prompt 触发过 `CLIP can only handle sequences up to 77 tokens`

## 综合发现

### 配置平移关系

- 这轮不需要重写 refine 流程。
- 可以直接沿用旧配置骨架, 只替换:
  - `base_dir -> outputs/my4_fullcolmap_v2_stable_12k_dense`
  - `exp_name -> 新的 v2 名称`
  - `load_step -> 11999`

### 当前假设

- 当前观察到的现象是:
  - 旧 prompt 已经跑通过流程
  - 但它被 `CLIP` 截断过
- 当前假设是:
  - 如果这轮继续原样照搬, 风格词后半段仍可能被截断
  - 更稳的做法是把最重要的风格词前置并压缩长度

### 下一步最小验证

- 用压缩后的 prompt 跑一次真实 refine。
- 直接看运行日志里是否还出现 `77 tokens` warning。

## [2026-03-27 09:17:57] [Session ID: 20260327T091216Z-main] 笔记: 第一版压缩 prompt 仍超出 `CLIP 77 tokens`, 需要进一步收短

## 来源

### 来源1: `flux_shinkai_museum_v2` 第一轮真实日志

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2_run.log`
- 动态证据:
  - `Token indices sequence length is longer than the specified maximum sequence length for this model (126 > 77)`
  - `The following part of your input was truncated because CLIP can only handle sequences up to 77 tokens`
  - 被截断的后半段包含:
    - `god rays`
    - `光束光柱`
    - `镜头光晕`
    - `辉光`
    - `high detail`

## 综合发现

### 现象

- 第一版“中英混合 + 关键语义前置”的压缩还不够短。
- 日志已经明确说明:
  - 被截断的不是边缘词
  - 而是本轮最想保住的核心光效词

### 当前假设

- 中文长串在 CLIP 里会被切成更碎的 token。
- 对这类 prompt, 用更短的英文主锚点更容易把关键语义完整送进去。

### 当前结论

- 这件事现在已经不是“可能截断”的猜测。
- 已经被真实运行日志验证为:
  - “当前第一版压缩 prompt 仍然过长”
- 因此下一轮应直接改成更短英文主锚点, 不要继续沿用这版 prompt 完整跑完。

## [2026-03-27 09:31:56] [Session ID: 20260327T091216Z-main] 笔记: 第二轮 `v2` refine 已验证“更短英文主锚点”可稳定避开截断

## 来源

### 来源1: 第二轮真实日志

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2_run.log`
- 要点:
  - `rg` 只命中了:
    - `Using Flux model source: /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`
  - 没再命中:
    - `Token indices sequence length`
    - `truncated because CLIP`
    - `77 tokens`

### 来源2: 产物元数据与文件计数

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/before_refine.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/after_refine.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/refine/gen.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
- 要点:
  - 三个 mp4 都是:
    - `1232x704`
    - `12 fps`
    - `50` 帧
  - 三套 jpg 都完整覆盖:
    - `030..079`

## 综合发现

### 现象

- 第二轮更短 prompt 已经不再触发 CLIP 截断。
- 同一轮里, `before / gen / after` 三套结果全部落齐。

### 当前结论

- 对这条 `Flux refine` 路径来说:
  - “先用最小动态验证确认有没有截断”
  - 明显比“盲目整轮跑完再回头看”更省时间
- 对这类中英混合风格 prompt 来说:
  - 如果关键语义很多, 英文主锚点通常比中文长串更稳

## [2026-03-27 19:07:29] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 笔记: 用户修改 prompt 后, `flux_shinkai_museum_v2` refine 已完成且未再触发截断

## 来源

### 来源1: `exp_cfg/my4/flux_shinkai_museum_v2.yaml`

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum_v2.yaml`
- 要点:
  - 本轮 prompt 已改为:
    - `high detail. Refine images, repair visual errors and blurriness in AI-generated images, perform defogging and enhance clarity. Correct unreasonable elements, data errors and illogical content in the images, remove ghosting, and boost details, textures and edges.`
  - 本轮仍沿用:
    - `base_dir: outputs/my4_fullcolmap_v2_stable_12k_dense`
    - `exp_name: flux_shinkai_museum_v2`
    - `load_step: 11999`

### 来源2: refine 运行记录与日志

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2_run.log`
- 动态证据:
  - 运行会话 `25279` 的上一轮执行记录已返回:
    - `exit code 0`
  - 本轮再次扫描日志关键字:
    - `rg -n "Traceback|Error|RuntimeError|Token indices sequence length|truncated because CLIP|77 tokens" ...`
  - 结果:
    - 无命中
    - `rg` 退出码 `1`

### 来源3: 输出文件时间戳、视频参数与逐帧计数

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/after_refine.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/refine/gen.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/refine/gen/image_079.jpg`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/refine/render/079.jpg`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/before_refine.mp4`
- 要点:
  - 刷新时间:
    - `after_refine.mp4`: `2026-03-27 19:04:16 +0800`
    - `gen.mp4`: `2026-03-27 19:02:29 +0800`
    - `ckpt_flux_shinkai_museum_v2.pt`: `2026-03-27 19:04:17 +0800`
    - `gen/image_079.jpg`: `2026-03-27 19:02:02 +0800`
    - `render/079.jpg`: `2026-03-27 19:01:27 +0800`
  - 未刷新的旧输入视频:
    - `before_refine.mp4`: `2026-03-27 17:49:15 +0800`
  - `ffprobe` 核对:
    - `before_refine.mp4`: `1232x704`, `12 fps`, `50` 帧
    - `after_refine.mp4`: `1232x704`, `12 fps`, `50` 帧
    - `refine/gen.mp4`: `1232x704`, `12 fps`, `50` 帧
  - 逐帧数量:
    - `before_refine = 50`
    - `after_refine = 50`
    - `gen = 50`

## 综合发现

### 现象

- 用户修改后的新 prompt 已经真实进入这轮 `v2 refine`。
- 运行会话记录、时间戳刷新、视频参数和逐帧数量彼此一致。
- 日志里没有再出现:
  - `Token indices sequence length`
  - `truncated because CLIP`
  - `77 tokens`

### 当前假设与备选解释

- 当前主假设:
  - 这轮 prompt 已避开上一次那类 `CLIP` 超长截断问题
  - 结果目录中的 `gen / after / ckpt` 都对应本轮新输出
- 最强备选解释:
  - `before_refine.mp4` 未刷新, 可能让人误以为重跑未生效
- 推翻主假设所需证据:
  - 如果 `after / gen / ckpt` 没有新时间戳
  - 或日志里重新出现 `77 tokens` / `truncated because CLIP`

### 已验证结论

- 这轮 refine 已经完整结束, 且没有扫描到显式错误关键字。
- 这轮没有再次触发先前已经确认过的 `CLIP 77` 截断告警。
- `before_refine.mp4` 没更新是正常现象, 因为这次改的是 refine prompt, 基础输入渲染并没有重新生成。
- 当前能确认的是“流程成功 + 产物已刷新”, 还不能直接推出“量化指标一定更好”, 因为本轮尚未做新的评测。
