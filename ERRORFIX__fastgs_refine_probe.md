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
