## [2026-03-27 00:48:18] [Session ID: 78200] 主题: `my4` 训练时 `gsplat` CUDA 扩展无法加载

### 现象
- 用户执行:
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4 --result_dir outputs/my4 --data_type colmap`
- 先出现:
  - `gsplat: No CUDA toolkit found. gsplat will be disabled.`
- 随后报错:
  - `AttributeError: 'NoneType' object has no attribute 'fully_fused_projection_fwd'`

### 原因
- 第一层原因:
  - 入口脚本在用户没有加载 `.envrc` 的 shell 里运行时, `PATH` 里没有正确暴露 pixi CUDA 工具链
- 第二层原因:
  - 仅仅把 `.pixi/envs/default/bin/nvcc` 暴露出来还不够
  - pixi 当前的真实 CUDA toolkit 根在:
    - `.pixi/envs/default/targets/x86_64-linux`
  - `cicc` 又单独放在:
    - `.pixi/envs/default/nvvm/bin`
- 伴随发现的旧问题:
  - `recon.trainer` 把验证集也错误地构造成了 `split="train"`

### 修复
- 在 `recon/runtime_env.py` 中:
  - 自动探测 `.pixi/envs/default/targets/*`
  - 把真正包含 `include/cuda_runtime_api.h` 的目录作为 `CUDA_HOME` / `CUDA_PATH`
  - 把 `nvvm/bin`、toolkit `bin`、pixi `bin` 一并补进 `PATH`
  - 让 `CUB_HOME` 优先指向真实 toolkit 的 `include`
- 在 `.envrc` 中:
  - 同步采用相同的路径布局
- 在 `recon/trainer.py` 中:
  - 把 `valset` 改成 `split="test"`
- 在 `cmd.md` / `README.md` 中:
  - 补充 `direnv allow`
  - 补充 1 step smoke test 命令

### 验证
- JIT 最小导入验证:
  - 日志文件: `/tmp/gsplat_jit_fixed.log`
  - 关键输出:
    - `_C_is_none False`
    - `EXIT_CODE=0`
- 训练 smoke test:
  - 命令:
    - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4 --result_dir outputs/my4_smoke_split --data_type colmap --max_steps 1 --disable_viewer`
  - 关键输出:
    - `Trainset Size: 180`
    - `Test Size: 132`
    - `Step: 0 ...`
  - 结论:
    - 入口脚本无需手工补环境变量, 已能直接完成 1 step 训练

## [2026-03-27 01:27:18] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 主题: `colmap.Dataset` 缺少共享渲染路径需要的元数据字段

### 现象
- 用户目标:
  - 从 `outputs/my4/ckpts/ckpt_29999.pt` 直接导出视频
- 先执行:
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4 --result_dir outputs/my4 --data_type colmap --partition data/my4/partition.json --ckpt outputs/my4/ckpts/ckpt_29999.pt --disable_viewer`
- 第一条失败:
  - `FileNotFoundError: data/my4/data/my4/partition.json`
- 修正命令后再执行:
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4 --result_dir outputs/my4 --data_type colmap --ckpt outputs/my4/ckpts/ckpt_29999.pt --disable_viewer`
- 第二条失败:
  - 已进入 `Running trajectory rendering...`
  - 随后报:
    - `KeyError: 'image_path'`

### 原因
- 第一层原因:
  - `recon.trainer` 会把 `cfg.partition` 再拼到 `cfg.data_dir` 下
  - 因此不能把完整相对路径 `data/my4/partition.json` 再传进去
- 第二层原因:
  - `render_traj` 明确依赖:
    - `image_path`
    - `image_name`
    - `image_size`
  - 但 `recon/datasets/colmap.py` 的 `Dataset.__getitem__` 之前没有返回这些字段
- 根因判断证据:
  - 静态证据:
    - `render_traj` 的字段读取代码
    - `colmap.Dataset.__getitem__` 的返回字典
  - 动态证据:
    - 去掉 `--partition` 后, 报错稳定停在 `KeyError: 'image_path'`

### 修复
- 调整运行方式:
  - 省略 `--partition`, 让训练器自动拾取 `data/my4/partition.json`
- 修改 [colmap.py](/home/rais/FreeFix/recon/datasets/colmap.py):
  - 在 `Dataset.__getitem__` 中补上:
    - `image_path`
    - `image_name`
    - `image_size`
  - 其中 `image_size` 改为基于当前实际 `image.shape` 计算, 兼容去畸变或裁剪后的尺寸
- 新增 [test_colmap_dataset_contract.py](/home/rais/FreeFix/tests/test_colmap_dataset_contract.py):
  - 用最小假 parser 和临时图片锁住这层契约

### 验证
- 单测:
  - `.pixi/envs/default/bin/python -m unittest tests.test_colmap_dataset_contract`
  - 输出:
    - `Ran 1 test in 0.107s`
    - `OK`
- 动态导视频:
  - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4 --result_dir outputs/my4 --data_type colmap --ckpt outputs/my4/ckpts/ckpt_29999.pt --disable_viewer`
  - 关键输出:
    - `Rendering trajectory: 100%|...| 50/50`
- 产物验证:
  - `outputs/my4/to_refine/render.mp4`: `1280x720`, `12 fps`, `50` 帧
  - `outputs/my4/to_refine/alpha.mp4`: `1280x720`, `12 fps`, `50` 帧
  - `renders/alphas/depths/gts`: 各 `50` 个文件

## [2026-03-27 02:03:30] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 主题: `Flux` refine 被 Hugging Face gated repo 权限阻断

### 现象
- 执行:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my4/flux_shinkai_museum.yaml`
- 直接报错:
  - `GatedRepoError: 401 Client Error`
  - `Cannot access gated repo ... black-forest-labs/FLUX.1-dev`

### 原因
- 当前机器没有可用的 Hugging Face 登录态:
  - `~/.huggingface/token` 不存在
  - `~/.cache/huggingface/token` 不存在
  - `~/.cache/huggingface/stored_tokens` 不存在
- 因此 `black-forest-labs/FLUX.1-dev` 这种 gated repo 当前无法拉取

### 修复
- 没有直接改代码去绕过 gated repo
- 先补了可复用配置:
  - `exp_cfg/my4/flux_shinkai_museum.yaml`
  - `exp_cfg/my4/sdxl_shinkai_museum.yaml`
- 并用 `SDXL` 作为开放模型回退路线做了真实验证

### 验证
- `Flux` 路线:
  - 已稳定复现 401 gated repo 错误
- `SDXL` 路线:
  - 已成功进入公开模型下载流程
  - 中断前缓存约 `1.1G`
  - 说明当前真正的分叉是:
    - 要么补 `Flux` 访问权限
    - 要么接受 `SDXL` 首次大下载和更长运行时间

## [2026-03-27 01:32:19] [Session ID: 20260327T012145Z-main] 主题: `Flux` refine 默认走 HF gated repo, 但本机其实已经有可用的 ModelScope 本地快照

### 现象
- 用户已经手动执行:
  - `modelscope download black-forest-labs/FLUX.1-dev`
- 但 `ours.refine_by_flux` 仍默认写死:
  - `FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", ...)`
- 结果是:
  - 代码会继续尝试远端鉴权
  - 即便本地已经有完整模型快照, 也不会自动复用

### 原因
- 第一层原因:
  - refine 入口没有“模型来源解析”这一步
  - 只认固定 repo id, 不认本地目录
- 第二层原因:
  - 本机的可用模型不在 Hugging Face 默认缓存结构里
  - 而是在 ModelScope 缓存目录:
    - `/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`

### 修复
- 修改 [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py):
  - 新增 `resolve_flux_model_source(cfg)`
  - 支持 `cfg.flux_model_path`
  - 支持常见本地缓存目录自动探测
  - 命中本地目录时, 给 `FluxPipeline.from_pretrained(...)` 传入:
    - 本地路径
    - `local_files_only=True`
- 新增 [flux_shinkai_museum.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum.yaml):
  - 显式记录:
    - `flux_model_path: /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`

### 验证
- 最小验证:
  - 本地目录存在 `model_index.json`
  - 代码实际打印:
    - `Using Flux model source: /home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev`
- 动态验证:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my4/flux_shinkai_museum.yaml`
  - 进程 `exit code 0`
- 产物验证:
  - `outputs/my4/flux_shinkai_museum/after_refine.mp4`
  - `outputs/my4/flux_shinkai_museum/refine/gen.mp4`
  - `outputs/my4/ckpts/ckpt_flux_shinkai_museum.pt`
  - 逐帧图 `030.jpg` 到 `079.jpg` 已完整生成

## [2026-03-27 09:59:58] [Session ID: 429732-430781] 主题: 人工删图后 `prepare_colmap_scene` 仍引用旧数据库图片名并忽略真实 `--rebuild-sparse`

### 现象
- 用户在 `data/my4/images/` 中手工剔除了坏图后, 执行:
  - `python3 -m recon.prepare_colmap_scene --source-dir data/my4 --dest-dir /root/autodl-tmp/home/rais/FreeFix/data/my4_rebuild --rebuild-sparse --colmap-binary /home/rais/.local/opt/colmap-env/bin/colmap --force`
- 原始报错:
  - `FileNotFoundError: 源图片不存在: /root/autodl-tmp/home/rais/FreeFix/data/my4/images/000024.png`

### 原因
- 第一层原因:
  - `choose_image_names()` 优先读取 `database.db(images table)`
  - 但 `database.db` 仍保留删图前的 `312` 条记录
  - 磁盘上实际只剩 `264` 张图
- 第二层原因:
  - `meta/partition_source_names.json` 里也还残留旧的 train/test 名单
  - 不能只在拷图处做跳过
- 第三层原因:
  - 旧实现里即使显式传了 `--rebuild-sparse`
  - 只要源目录还有旧 `sparse/`, 仍会直接复制旧 sparse, 不会真的重建

### 修复
- 修改 [prepare_colmap_scene.py](/root/autodl-tmp/home/rais/FreeFix/recon/prepare_colmap_scene.py):
  - 新增 `read_partition_source_names()`:
    - 先读根级 `colmap_train_images.txt` / `colmap_test_images.txt`
    - 没有时回退到 `meta/partition_source_names.json`
  - 新增 `filter_existing_image_names()`:
    - 先按磁盘真实图片集合过滤旧名单
  - 新增 `prune_database_to_images()`:
    - 清理复制后的 `database.db`
    - 删除已失效的 `images`
    - 删除关联的 `matches`
    - 删除关联的 `two_view_geometries`
  - 调整主流程:
    - 检测到删图后, 自动过滤旧图片名
    - 自动过滤 train/test 旧名字
    - 显式传 `--rebuild-sparse` 时优先真实执行 mapper 重建, 不再复制旧 `sparse/`
- 新增回归测试 [test_prepare_colmap_scene.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_prepare_colmap_scene.py):
  - 锁住 `meta/partition_source_names.json` 回退读取
  - 锁住删图后数据库清理逻辑

### 验证
- 数据一致性验证:
  - `images/` 真实图片数: `264`
  - `database.db images` 表旧记录数: `312`
  - 缺失但仍被数据库引用的图片: `48`
- 单测:
  - `.pixi/envs/default/bin/python -m unittest tests.test_prepare_colmap_scene`
  - 输出:
    - `Ran 3 tests in 0.013s`
    - `OK`
  - `.pixi/envs/default/bin/python -m unittest tests.test_colmap_dataset_contract`
  - 输出:
    - `Ran 1 test in 0.070s`
    - `OK`
- 动态命中修复路径:
  - 重跑同一条 `prepare_colmap_scene` 命令后
  - `COLMAP` 日志显示:
    - `Loading images... 264`
  - 且已进入真实 mapper 重建与持续注册图像阶段
  - 不再复现原始 `FileNotFoundError`

## [2026-03-27 03:20:26] [Session ID: 20260327T032026Z-main] 主题: `convert.py` 在多 sparse model 场景下把小模型拿去 undistort

### 现象
- full COLMAP 已跑完 `feature_extractor / exhaustive_matcher / mapper`
- `mapper` 日志显示主模型已经成功注册大量图片
- 但最终 `data/my4_fullcolmap/images/` 只有 `2` 张图
- 同时根级 `data/my4_fullcolmap/sparse/0` 也只有:
  - `2` 张注册图
  - `296` 个点

### 原因
- 第一层原因:
  - `data/my4_fullcolmap/distorted/sparse/` 里同时存在多个模型:
    - `0`: `2` 张注册图, `296` 个点
    - `1`: `264` 张注册图, `27521` 个点
- 第二层原因:
  - `recon/convert.py` 之前把 `image_undistorter` 的 `--input_path` 固定写成:
    - `distorted/sparse/0`
  - 所以即便 `mapper` 真正的大模型在 `1`, 最终去畸变阶段仍只消费了 2 图小模型
- 伴随暴露的入口兼容问题:
  - 修复脚本时新增 `from recon.datasets.colmap_io ...`
  - 这会让 `python3 recon/convert.py ...` 这种直接执行方式在导入阶段报:
    - `ModuleNotFoundError: No module named 'recon'`

### 修复
- 修改 [convert.py](/root/autodl-tmp/home/rais/FreeFix/recon/convert.py):
  - 新增 `choose_best_sparse_model_dir()`
  - 自动扫描 `distorted/sparse/*`
  - 按“注册图数量优先, 点云数量次级”选择最佳模型
  - 再把选中的模型传给 `image_undistorter`
- 同时补 direct-script fallback:
  - 当脚本以 `python3 recon/convert.py ...` 直接运行时
  - 自动把仓库根目录补回 `sys.path`
- 修改 [test_convert.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_convert.py):
  - 新增多模型选择回归测试
  - 新增 direct-script `--help` 入口回归测试
- 更新 [cmd.md](/root/autodl-tmp/home/rais/FreeFix/cmd.md):
  - 补充 `--skip_matching` 的后处理修复命令

### 验证
- 单测:
  - `python3 -m unittest tests.test_convert`
  - 输出:
    - `Ran 7 tests`
    - `OK`
- 语法检查:
  - `python3 -m py_compile recon/convert.py tests/test_convert.py`
- direct-script 入口:
  - `python3 recon/convert.py --help`
  - `exit code 0`
- 动态修复验证:
  - 先清理错误产物:
    - `rm -rf data/my4_fullcolmap/images data/my4_fullcolmap/sparse`
  - 再执行:
    - `python3 recon/convert.py --source_path data/my4_fullcolmap --colmap_executable /home/rais/.local/opt/colmap-env/bin/colmap --skip_matching`
  - 关键输出:
    - `=> Reconstruction with 264 images and 27521 points`
    - `Undistorting image [264/264]`
    - `Done.`
- 结果验证:
  - `find data/my4_fullcolmap/images -maxdepth 1 -type f | wc -l` -> `264`
  - `root_sparse_0 264 27521`
  - `partition.json` 生成成功:
    - `train_count = 152`
    - `test_count = 112`
  - 训练 smoke test:
    - `.pixi/envs/default/bin/python -m recon.trainer --data_dir data/my4_fullcolmap --result_dir outputs/my4_fullcolmap_smoke --data_type colmap --max_steps 1 --disable_viewer`
    - 关键输出:
      - `Trainset Size: 152`
      - `Test Size: 112`
      - `Step: 0 ...`

## [2026-03-27 04:43:28] [Session ID: 20260327T041915Z-main] 主题: `Runner.eval()` 在 `app_opt=true` 场景下存在两处真实兼容 bug

### 现象
- 我为了评测:
  - `outputs/my4_fullcolmap_quality/ckpts/ckpt_9999.pt`
  手动调用 `Runner.eval(step=9999)`
- 第一轮直接报:
  - `NameError: name 'cfg' is not defined`
- 修掉后第二轮继续报:
  - `AttributeError: 'ParameterDict' object has no attribute 'sh0'`
- 再继续排查后, 又定位到 certainty 渲染分支还会进一步撞上:
  - `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`

### 原因
- 第一层原因:
  - `rasterize_splats_w_certainty()` 里错误使用了未定义的局部 `cfg`
  - 正确来源应当是 `self.cfg`
- 第二层原因:
  - 该函数清理梯度时无条件假设 `splats` 一定包含:
    - `sh0`
    - `shN`
  - 但在 `app_opt=true` 时, checkpoint 实际键是:
    - `features`
    - `colors`
- 第三层原因:
  - `rasterize_splats(..., override_color=...)` 虽然已经显式传入 certainty 颜色
  - 代码却仍先进入 `app_module` / SH 颜色分支
  - 当 certainty 分支把 `sh_degree=None` 传下来时, `app_module` 会在:
    - `(sh_degree + 1) ** 2`
    这里直接炸掉

### 修复
- 修改 [trainer.py](/root/autodl-tmp/home/rais/FreeFix/recon/trainer.py):
  - `rasterize_splats_w_certainty()` 先绑定 `cfg = self.cfg`
  - 清理梯度时改为按键存在性处理:
    - `means/quats/scales/opacities/sh0/shN/features/colors`
  - `rasterize_splats()` 在 `override_color is not None` 时直接跳过 `app_module / SH` 颜色计算
- 同步修改:
  - [refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
  - [refiner_uncertainty.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner_uncertainty.py)
- 新增回归测试:
  - [test_trainer_eval_path.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_trainer_eval_path.py)
  - 锁住:
    - `self.cfg` 引用
    - `override_color` 绕开 `app_module`

### 验证
- 单测:
  - `.pixi/envs/default/bin/python -m unittest tests.test_trainer_eval_path`
  - 输出:
    - `Ran 2 tests`
    - `OK`
- 语法检查:
  - `python3 -m py_compile recon/trainer.py recon/refiner.py recon/refiner_uncertainty.py tests/test_trainer_eval_path.py`
- 动态评测验证:
  - `ckpt_9999.pt` 手动评测成功
  - `ckpt_49999.pt` 手动评测成功
  - 两档都成功生成:
    - 指标 JSON
    - `concat/rgbs/alphas/certainties`
    - 总览拼图
