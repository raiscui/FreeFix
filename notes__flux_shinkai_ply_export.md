## [2026-04-01 15:00:34] [Session ID: codex-flux-shinkai-ply-20260401] 笔记: `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 的导出入口确认

## 来源

### 来源1: 目标实验目录检索

- 目录:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`
- 现场事实:
  - 目录内已有 `before_refine/`、`after_refine/`、`refine/`、`run.log`
  - 已存在 `before_refine.mp4` 和 `after_refine.mp4`
- 结论:
  - 该实验不是“还没跑完的空壳目录”, 而是已经完成 refine 渲染输出的正式结果目录。

### 来源2: 仓库内导出代码

- 文件:
  - `ours/run_fastgs_refine.py`
  - `recon/export_3dgs_ply.py`
- 关键静态证据:
  - `ours/run_fastgs_refine.py` 的 `build_export_command(...)` 会调用 `python -m recon.export_3dgs_ply --ckpt <refined_ckpt> --output <final_ply>`
  - `resolve_refined_artifact_paths(...)` 约定 refine 最终 checkpoint 为 `result_dir/ckpts/ckpt_<exp_name>.pt`
  - `recon/export_3dgs_ply.py` 会读取 checkpoint 里的 `splats` 并导出标准 binary little-endian 3DGS `ply`
- 结论:
  - 当前仓库已经有稳定的“FreeFix checkpoint -> 3DGS ply”导出链路, 不需要临时写脚本。

### 来源3: 运行日志与 checkpoint 时间戳

- 文件:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/run.log`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330__resume_latest.pt`
- 关键动态证据:
  - `run.log` 末尾显示:
    - `已保存恢复 checkpoint: plan=972/972 ... __resume_latest.pt`
    - `开始导出 after_refine`
    - `开始保存 refine checkpoint: ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`
    - `refine checkpoint 已保存: outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`
  - 文件时间戳:
    - 正式 checkpoint: `2026-04-01 04:59`, 约 `37M`
    - `__resume_latest`: `2026-04-01 04:58`, 约 `37M`
- 结论:
  - 正式 refine 终态是 `ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`
  - `__resume_latest` 只是恢复用中间态, 不应作为本次交付的首选导出源。

## 综合发现

### 已验证结论

- 目标实验目录已完成 refine 产物输出。
- 正式导出入口是 `python -m recon.export_3dgs_ply`。
- 本次最稳妥的输入 checkpoint 是:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`

### 下一步

- 直接执行导出命令, 把结果写到:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
- 导出后校验:
  - 文件存在
  - 大小非零
  - 导出脚本输出的 `gaussian_count` 与 `property_count`

## [2026-04-01 15:04:00] [Session ID: codex-flux-shinkai-ply-20260401] 笔记: 导出结果校验

## 来源

### 来源4: `recon.export_3dgs_ply` 实际导出

- 执行命令:
  - `direnv exec . env OMP_NUM_THREADS=1 pixi run python3 -m recon.export_3dgs_ply --ckpt outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt --output outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
- 动态结果:
  - `checkpoint: outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt`
  - `output: outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
  - `gaussian_count: 159281`
  - `property_count: 62`
- 结论:
  - 导出命令成功执行, 没有出现 checkpoint 结构错误或写文件失败。

### 来源5: 导出产物文件校验

- 文件:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
- 动态结果:
  - `ls -lh`: `38M`, 修改时间 `2026-04-01 15:04`
  - `file`: `PLY model, binary, little endian, version 1.0`
  - 头部包含:
    - `element vertex 159281`
    - `property float f_dc_0`
    - `property float f_rest_44`
    - `property float opacity`
    - `property float rot_3`
- 结论:
  - 当前产物是标准 binary little-endian 3DGS `ply`
  - 顶点数和脚本输出的 `gaussian_count` 一致
  - 可以作为本次交付结果直接使用

## 综合发现

### 已验证结论

- 已成功导出 `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 的 3DGS `ply`
- 交付文件路径是:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
- 当前导出结果的关键统计为:
  - `gaussian_count = 159281`
  - `property_count = 62`
