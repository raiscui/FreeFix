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
