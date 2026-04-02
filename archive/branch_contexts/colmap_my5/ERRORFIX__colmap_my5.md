## [2026-03-27 22:31:22] [Session ID: 20260327T221426Z-main] 问题: `ours.evaluation` 写死 `29999` 与 refined 评估入口, 导致短训场景无法直接评估

### 现象
- `my5` 的真实训练 checkpoint 是 `11999`
- refined checkpoint 目前还不存在
- 但旧 `ours/evaluation.py` 的 CLI 会固定执行:
  - `eval(cfg, 29999, ...)`
  - `eval(cfg, cfg.exp_name, ...)`

### 原因
- 评估入口把某条长训工作流的默认假设写死到了 CLI 主流程里。
- 这个假设没有跟 `cfg.load_step` 对齐, 也没有在 refined checkpoint 缺失时做显式分流。

### 修复
- 新增辅助逻辑:
  - `resolve_base_load_step`
  - `refined_checkpoint_path`
  - `has_refined_checkpoint`
- 主流程改为:
  - 基础模型默认评估 `cfg.load_step`
  - 支持 `--load-step` 覆盖
  - refined checkpoint 不存在时打印跳过信息并继续成功退出
- 新增回归测试:
  - `tests/test_evaluation_cli.py`

### 验证
- `python3 -m py_compile ours/evaluation.py tests/test_evaluation_cli.py`
- `.pixi/envs/default/bin/python -m unittest tests.test_evaluation_cli`
- `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml --eval_test`
- 真实结果:
  - 基础评估成功生成:
    - `11999_test.json`
    - `11999_train.json`
  - refined 缺失时输出:
    - `Skip refined evaluation because checkpoint does not exist: outputs/my5_colmap_fastgs_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`

## [2026-03-27 14:43:43] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 问题: `render_traj()` 被 `@torch.no_grad()` 包住后, certainty 视频导出直接失败

### 现象
- 为了减少训练期视频导出的显存压力, 我一开始给 `render_traj()` 加了 `@torch.no_grad()`
- 第一轮真实短测命令:
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my5/recon_my5_colmap_fastgs_stable_12k_dense.yaml --set max_steps=1 --set save_steps=[1] --set render_video_steps=[1] --set render_video_start_idx=0 --set render_video_end_idx=2 --set result_dir=outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke`
- 真实报错:
  - `RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn`

### 原因
- `render_traj()` 不是纯前向渲染。
- 它内部调用 `rasterize_splats_w_certainty()`, 其中会执行:
  - `rgbs[..., :3].backward(...)`
- 这一步就是 certainty 可视化所依赖的动态证据链, 被 `no_grad` 包住后自然会失效。

### 修复
- 移除 `render_traj()` 上新增的 `@torch.no_grad()`
- 保留 `render_to_refine_video()` 的 `@torch.no_grad()`, 因为那条路径只做普通前向渲染

### 验证
- 重新运行:
  - `.pixi/envs/default/bin/python -m py_compile recon/trainer.py tests/test_trainer_video_export.py`
  - `.pixi/envs/default/bin/python -m unittest tests.test_trainer_video_export`
  - `.pixi/envs/default/bin/python -m recon.train_from_yaml --config exp_cfg/my5/recon_my5_colmap_fastgs_stable_12k_dense.yaml --set max_steps=1 --set save_steps=[1] --set render_video_steps=[1] --set render_video_start_idx=0 --set render_video_end_idx=2 --set result_dir=outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke_r2`
- 复验结果:
  - 命令正常退出 `code 0`
  - 成功生成:
    - `outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke_r2/to_refine/render_ckpt_0.mp4`
    - `outputs/my5_colmap_fastgs_stable_12k_dense_video_smoke_r2/to_refine/alpha_ckpt_0.mp4`

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 问题: `run_fastgs_refine` 用脚本路径实跑 refine 时, 会报 `ModuleNotFoundError: No module named 'ours'`

### 现象
- 在这次真实 `my5_nomask_v1` bridge refine 里, 我最初执行的是:
  - `.pixi/envs/default/bin/python ours/refine_by_flux.py ...`
- 实际报错:
  - `ModuleNotFoundError: No module named 'ours'`
- 但同一环境下:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --help`
  是正常的

### 原因
- 根因不在环境, 而在启动方式。
- 当 refine 用脚本路径 `ours/refine_by_flux.py` 启动时, 运行时模块搜索路径会把 `ours/` 当成脚本目录。
- 后续脚本内部再执行:
  - `from ours.pipelines.flux_pipeline import FluxPipeline`
  就找不到仓库根层级上的 `ours` 包了。
- `run_fastgs_refine.py` 原先也是按这种脚本路径拼命令, 所以它在真实执行 refine 时存在同样缺陷。

### 修复
- 把 `ours/run_fastgs_refine.py` 里的 refine 命令改成模块调用:
  - `python -m ours.refine_by_flux`
  - `python -m ours.refine_by_sdxl`
- 同步更新:
  - `tests/test_run_fastgs_refine.py`

### 验证
- `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py`
- `.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine`
- 真实复验:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.yaml --colmap-path /home/rais/FastGS/data/my5_colmap_fastgs --ckpt-path /root/autodl-tmp/home/rais/FreeFix/data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
- 复验结果:
  - refine 正常完成并退出 `code 0`
  - 成功生成:
    - `before_refine.mp4`
    - `after_refine.mp4`
    - `gen.mp4`
    - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.pt`

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 问题: `ours.evaluation` 无法像 refine 一样直接评估外部 bridge checkpoint

### 现象
- bridge refine 已经跑通, 但补评估时发现:
  - `ours.evaluation` 只能从 `cfg.base_dir/ckpts/ckpt_<load_step>.pt` 读取基础模型
- 这导致外部 bridge base:
  - `data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt`
  没法直接进入真实评估流程

### 原因
- 评估入口比 refine 入口少了一层运行时路径 override。
- refine 已经有:
  - `--colmap-path`
  - `--ckpt-path`
- evaluation 还停留在“只认 result_dir 里的标准 checkpoint 命名”这一旧假设上。

### 修复
- 在 [evaluation.py](/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py) 增加:
  - `resolve_optional_checkpoint_path`
  - `apply_runtime_path_overrides`
  - `--colmap-path`
  - `--ckpt-path`
- 同时显式区分:
  - 基础评估:
    - `use_ckpt_override=True`
  - refined 评估:
    - `use_ckpt_override=False`
- 新增并扩展回归测试:
  - [test_evaluation_cli.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_evaluation_cli.py)

### 验证
- `python3 -m py_compile ours/evaluation.py tests/test_evaluation_cli.py`
- `.pixi/envs/default/bin/python -m unittest tests.test_evaluation_cli`
- `.pixi/envs/default/bin/python -m ours.evaluation --help`
- 真实复验:
  - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.yaml --colmap-path /home/rais/FastGS/data/my5_colmap_fastgs --ckpt-path /root/autodl-tmp/home/rais/FreeFix/data/fastgs_bridge/my5_nomask_v1/ckpt_35000_freefix.pt --eval_test`
- 复验结果:
  - 成功生成:
    - `35000_test.json`
    - `35000_train.json`
    - `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_test.json`
    - `flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_train.json`

## [2026-03-27 21:19:24] [Session ID: 20260327T194314Z-main] 问题: `import_fastgs` 只旋转了几何参数, 没有同步旋转高阶 SH, 导致 bridge base 大幅掉分

### 现象
- `my5_nomask_v1` 的 FastGS 原始结果大约是:
  - `PSNR 27.2039`
  - `SSIM 0.8910`
  - `LPIPS 0.2026`
- 但旧 bridge base 只有:
  - `PSNR 23.9542`
  - `SSIM 0.8489`
  - `LPIPS 0.2550`
- 同时又观察到:
  - raw checkpoint + raw cameras + FreeFix renderer 可以算到 `PSNR 27.1882`
  - 说明问题不在 benchmark, 也不在 renderer 本身

### 原因
- `transform_splats_to_freefix()` 旧逻辑只处理了:
  - `means`
  - `quats`
  - `scales`
- 却把:
  - `sh0`
  - `shN`
  原样带到了新坐标系里。
- 对这份 `my5` 场景来说, FreeFix normalization 带有约 `86.79` 度全局旋转。
- `shN` 是 view-dependent 高阶 SH 系数, 不跟着旋转就会直接破坏外观函数。

### 修复
- 在 [import_fastgs.py](/root/autodl-tmp/home/rais/FreeFix/recon/import_fastgs.py) 新增 real SH rotation 逻辑:
  - 基于 `gsplat` 当前实际 basis 数值构造每一阶的旋转块矩阵
  - 用 `rotate_real_sh_coefficients()` 把 `sh0 + shN` 一起变换到新坐标系
- 同步新增回归测试:
  - `DC-only` 不变
  - full SH 函数在“旋转方向 + 旋转系数”后保持一致

### 验证
- `python3 -m py_compile recon/import_fastgs.py tests/test_import_fastgs.py`
- `.pixi/envs/default/bin/python -m unittest tests.test_import_fastgs`
- 真实 bridge 复验:
  - 修复后:
    - `PSNR 27.188240097790228`
    - `SSIM 0.8906744631325326`
    - `LPIPS 0.2037334242245046`
  - 相比修复前:
    - `PSNR +3.2340`
    - `SSIM +0.04180`
    - `LPIPS -0.05130`
  - 相比 FastGS 原始结果:
    - `PSNR -0.0157`
    - `SSIM -0.00034`
    - `LPIPS +0.00111`
- 当前结论:
  - 这次 bridge 掉分 bug 已经实质修复

## [2026-03-27 21:19:24] [Session ID: 20260327T194314Z-main] 问题: 调试脚本里误用系统 `python3`, 导致把环境缺包误看成实现问题

### 现象
- 在调查 bridge 掉分时, 我有两次直接用系统 `python3` 跑仓库脚本。
- 结果分别遇到:
  - `ModuleNotFoundError: No module named 'plyfile'`
  - `ModuleNotFoundError: No module named 'imageio'`

### 原因
- 这些脚本依赖的是项目 `.pixi` 环境里的包, 不是系统 Python 环境。
- 当时失败的是解释器选择, 不是逻辑路径本身。

### 修复
- 后续同类验证统一切回:
  - `.pixi/envs/default/bin/python`

### 验证
- 切回 `.pixi` 后, 同样的检查脚本都能正常执行并产出有效证据。
