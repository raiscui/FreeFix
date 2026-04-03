## [2026-03-27 18:04:10] [Session ID: codex-fastgs-path-args-verify] 问题: refine 脚本帮助页被顶层重依赖拖慢

### 现象
- 命令:
  - `timeout 15s python3 ours/refine_by_flux.py --help`
  - `timeout 15s python3 ours/refine_by_sdxl.py --help`
- 两条命令在修复前都没有及时返回帮助文本

### 原因
- `refine_by_flux.py / refine_by_sdxl.py` 在模块顶层就加载了:
  - `torch`
  - pipeline
  - `Refiner`
  - `OmegaConf`
- 这导致即使用户只是想看 CLI 帮助, 也要先经过整条重 import 链
- 另外, 初次修复时我把 `OmegaConf` 仍然放在 `parse_args()` 之前, 造成 `python3 ... --help` 仍会先要求环境里有 `omegaconf`

### 修复
- 把模型 / 渲染 / 训练相关重依赖后移到 `refine()` 内部
- 把 `OmegaConf` 后移到 `args = parser.parse_args()` 之后
- 抽出 `build_arg_parser()`, 让参数定义和运行时重逻辑解耦

### 验证
- `timeout 10s python3 ours/refine_by_flux.py --help`
  - 成功输出:
    - `--colmap-path COLMAP_PATH`
    - `--ckpt-path CKPT_PATH`
- `timeout 10s python3 ours/refine_by_sdxl.py --help`
  - 成功输出:
    - `--colmap-path COLMAP_PATH`
    - `--ckpt-path CKPT_PATH`
- `/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_import_fastgs tests.test_refine_cli_paths tests.test_trainer_eval_path`
  - `Ran 11 tests in 0.049s`
  - `OK`

## [2026-03-28 17:26:01] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] 问题: wrapper 最终 `.ply` 路径推导过早依赖配置细节

### 现象
- 在新增“refine 后自动导出 `.ply`”时, 首轮实现暴露出两个问题:
  - `tests.test_run_fastgs_refine` 报错:
    - `Missing key gs_cfg_file`
  - `python3 ours/run_fastgs_refine.py ... --dry-run` 报错:
    - `ModuleNotFoundError: No module named 'omegaconf'`

### 原因
- 我一开始直接假设:
  - 合并后的 refine 配置里一定显式存在 `gs_cfg_file`
  - 推导最终产物路径时可以直接依赖 `OmegaConf`
- 这两点都不稳:
  - `gs_cfg_file` 在很多场景只是来自 `exp_cfg/base.yaml` 的默认值
  - wrapper 的 `--dry-run` 只需要少量路径键, 不该先撞上完整配置依赖

### 修复
- `gs_cfg_file` 缺失时默认回退到 `cfg.json`
- 移除 wrapper 对 `OmegaConf` 的提前依赖
- 改为轻量解析 YAML 里的:
  - `base_dir`
  - `exp_name`
  - `gs_cfg_file`
- 再读取 `<base_dir>/<gs_cfg_file>` 的 JSON `result_dir`, 推导:
  - refined ckpt 路径
  - 最终 `.ply` 默认输出路径

### 验证
- `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py`
  - 通过
- `timeout 30s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine`
  - `Ran 9 tests in 1.812s`
  - `OK`
- `python3 ours/run_fastgs_refine.py --ckpt-path /tmp/demo_fastgs.pth --colmap-path data/my4_fullcolmap --exp-cfg exp_cfg/my4/flux_shinkai_museum_v2.yaml --dry-run`
  - 成功输出三条命令
  - 成功打印 `final_ply_output: .../point_cloud_flux_shinkai_museum_v2.ply`

## [2026-03-29 12:40:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 问题: 真实 Flux pose jitter smoke 卡在默认 `pipe.to(cuda)` 路径

### 现象
- 上一轮真实命令:
  - `timeout 420s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke.yaml`
- 日志能稳定打印到:
  - `FluxPipeline.from_pretrained 返回`
  - `开始执行 pipe.to(cuda)`
- 但在 `420s` 窗口内始终没有出现:
  - `pipe.to(cuda) 返回`
  - `开始创建输出目录`

### 原因
- 当前能被证据支撑的口径不是“diffusers 内部已经定位出唯一根因”
- 当前已验证的是:
  - 默认整模搬到 GPU 的 pipeline 放置路径会在本机长时间阻塞
  - 同时 refine 入口原先还把输入张量绑定到 `pipe.device`
  - 这和 diffusers / 本地 pipeline 实际使用的 `_execution_device` 语义并不一致

### 修复
- 新增 `ours/refine_pipeline_runtime.py`
  - 统一支持:
    - `none`
    - `model_cpu`
    - `sequential_cpu`
- 在 `ours/refine_by_flux.py / ours/refine_by_sdxl.py` 中:
  - 引入 `refine_pipeline_offload_mode`
  - `model_cpu / sequential_cpu` 路径不再执行 `pipe.to(cuda)`
  - 输入张量改成跟随 `resolve_pipeline_execution_device(pipe)`
- 在 `exp_cfg/base.yaml` 中补默认配置:
  - `refine_pipeline_offload_mode: none`

### 验证
- 语法检查:
  - `python3 -m py_compile ours/refine_pipeline_runtime.py ours/refine_by_flux.py ours/refine_by_sdxl.py tests/test_refine_pipeline_runtime.py tests/test_refine_cli_paths.py tests/test_pose_jitter_refine.py`
  - 通过
- 单测:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_refine_pipeline_runtime tests.test_refine_cli_paths tests.test_pose_jitter_refine`
  - `Ran 19 tests in 0.030s`
  - `OK`
- 真实 smoke:
  - `timeout 600s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke_model_cpu.yaml`
  - 关键输出:
    - `enable_model_cpu_offload 返回`
    - `开始创建输出目录`
    - `Pose jitter log: .../refine/pose_jitter_log.jsonl`
  - 退出码:
    - `0`
  - 已落盘:
    - `before_refine/000.jpg`
    - `after_refine/000.jpg`
    - `refine/render/000.jpg`
    - `refine/gen/image_000.jpg`
    - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_pose_jitter_smoke_20260329_model_cpu.pt`

## [2026-03-29 14:50:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 问题: mature checkpoint 进入 refine 时 `DefaultStrategy` 在 `step=0` 错误重置 opacity, 导致后续 render 几乎全黑

### 现象
- `my5 pose_jitter + train` smoke 中:
  - `refine/render/001.jpg` 与 `002.jpg` 大面积发黑
  - `after_refine/001.jpg` 与 `002.jpg` 也继续发黑
- 进一步最小复现显示:
  - 即使只执行一个真实 train step
  - 亮度也会从约 `0.5034` 直接掉到约 `0.0393`

### 原因
- 初看像是 `pose_jitter` 相机变换问题, 但离线重放同一组 jitter 参数后发现 render 本身并不黑
- 真正的直接原因是:
  - `Refiner` 加载成熟 checkpoint 后, strategy 仍从局部 `step=0` 开始
  - `gsplat.strategy.DefaultStrategy.step_post_backward()` 在 `step % reset_every == 0` 时会执行 `reset_opa`
  - 因此第一个 refine step 直接把成熟模型的 opacity 重置到 `prune_opa * 2 = 0.01`
- 动态证据:
  - strategy 开启时:
    - opacity 均值 `0.3388 -> 0.0081`
    - opacity 最大值 `1.0 -> 0.01`
  - strategy 静音时:
    - 亮度和 opacity 都保持正常

### 修复
- 新增 `recon/refine_runtime.py`
  - 统一解析:
    - checkpoint payload 里的 `step`
    - 命令行 / 配置传入的 `load_step`
    - 当前 refine 的局部 `local_step`
- 在 `recon/refiner.py` 中:
  - 记录 `self.strategy_resume_step`
  - 保留局部 `step` 给 train/refine 采样节奏
  - 但把 `strategy.step_pre_backward()` 和 `strategy.step_post_backward()` 的 `step` 改成:
    - `strategy_resume_step + local_step`
- 这样成熟 checkpoint 会继续沿用原训练时间轴
  - 不再在 refine 第一步误触发 `reset_opa`

### 验证
- 语法检查:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m py_compile recon/refine_runtime.py recon/refiner.py tests/test_refine_runtime.py tests/test_pose_jitter_refine.py`
  - 通过
- 单测:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m unittest tests.test_refine_runtime tests.test_pose_jitter_refine`
  - `Ran 11 tests in 0.009s`
  - `OK`
- 最小动态复现:
  - 修复后单步 train:
    - `before_mean ≈ 0.5034`
    - `after_mean ≈ 0.5047`
    - `strategy_resume_step = 34999`
- 真实 smoke:
  - `timeout 900s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/my5_pose_jitter_train_smoke_fix_20260329.yaml`
  - 退出码:
    - `0`
  - 关键输出亮度:
    - `refine/render/001.jpg mean ≈ 0.5033`
    - `refine/render/002.jpg mean ≈ 0.5056`
    - `after_refine/001.jpg mean ≈ 0.5070`
    - `after_refine/002.jpg mean ≈ 0.5106`
  - 最终 ckpt:
    - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_my5_pose_jitter_train_smoke_fix_20260329.pt`
