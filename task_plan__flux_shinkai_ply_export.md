# 任务计划: 导出 flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330 的 3DGS PLY

## [2026-04-01 15:00:34] [Session ID: codex-flux-shinkai-ply-20260401] [记录类型]: 初始化导出计划

## 目标

找到 `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 的真实实验结果, 通过项目内正确链路导出 3DGS `ply`, 并确认产物路径可直接交付。

## 阶段

- [x] 阶段1: 读取项目经验与历史上下文
- [x] 阶段2: 定位实验目录与可用导出入口
- [x] 阶段3: 执行导出并检查产物
- [x] 阶段4: 记录交付与后续建议

## 关键问题

1. 这个名字对应的是训练输出目录、数据集目录, 还是某个中间配置名: 已确认是实验输出目录名, 位于 `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`。
2. 项目当前是否已经有稳定的 `3dgs -> ply` 导出脚本: 已确认有, 入口是 `python -m recon.export_3dgs_ply`。
3. 导出最稳的路径是什么:
   - 方案A(最佳方案): 复用项目现有的官方/既有导出链路, 直接从该实验的最终高斯状态导出标准 `ply`。
   - 方案B(先能用方案): 如果缺少一键导出入口, 则从现有 checkpoint 或高斯缓存中调用底层转换脚本, 先拿到可用 `ply`, 后续再补自动化闭环。

## 做出的决定

- 决定1: 先不猜导出命令, 先定位实验目录和已有导出脚本, 避免把错误 checkpoint 导成“看起来成功但对象不对”的 `ply`。
- 决定2: 优先走仓库内已有导出链路, 只有在它缺失或失效时, 才退回到底层转换办法。
- 决定3: 本轮输出口径先限定为“成功导出并确认产物路径”, 不先夸大为“整条训练/渲染链路都已验证完毕”。
- 决定4: 使用正式 refine checkpoint `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.pt` 作为导出输入, 不使用 `__resume_latest` 中间恢复点。

## 遇到错误

- 暂无新错误, 本轮导出顺利完成。

## 状态

**目前已完成** - `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 的 3DGS `ply` 已导出并完成头部与文件类型校验。
