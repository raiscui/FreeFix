# 归档说明: fastgs_refine_probe task_plan 续档

## 时间

- 2026-03-31 15:03:13 UTC

## 涉及文件

- 归档前:
  - `task_plan__fastgs_refine_probe.md`
- 归档后:
  - `archive/branch_contexts/fastgs_refine_probe/snapshots/2026-03-31_150313/task_plan__fastgs_refine_probe_2026-03-31_150313.md`

## 触发原因

- 活跃支线 `fastgs_refine_probe` 的 `task_plan` 已超过 1000 行。
- 为避免继续把当前行动记录淹没在超长历史里, 按项目规则执行续档。

## 六文件摘要

- 涉及的上下文集:
  - `__fastgs_refine_probe`
- 任务目标:
  - 围绕 FastGS -> FreeFix refine、pose jitter、Flux/SDXL 运行链、恢复能力、rerun 排障持续推进
- 关键决定:
  - refine 入口要保留恢复能力
  - fixed-view 导出优先 batch render
  - synthetic 主循环不直接做多 plan 并行
  - `FLUX.1-dev` 当前优先走 ModelScope, 不走 Hugging Face gated repo
- 关键发现:
  - `refine_resume_state.json`、rolling ckpt、jpg 序列与 generated cams 已构成恢复闭环
  - `OMP_NUM_THREADS=0` 会触发 `libgomp` 环境变量报错
  - 当前 rerun 的直接阻塞是 `flux_model_path` 指向失效本地目录
- 实际变更:
  - 本轮将超长 `task_plan` 续档
  - 同时把已稳定的经验沉淀到 `EXPERIENCE.md`
- 支线组活跃度判定:
  - 活跃
- 暂缓事项:
  - 更深层的 synthetic 主循环性能优化仍需 GPU profile
  - `train_test_x3_20260330` 中途停在 `plan_index=326` 的最终根因还要继续取证
- 错误与根因:
  - rerun 当前已确认不是仍在运行, 而是因失效 `flux_model_path` 提前退出
- 重大风险 / 重要规律:
  - 不能把“图像导出完整”误当成“最终 checkpoint 必然已保存”
  - 不能把“GPU 可用”误推成“render 与 Flux gen 就适合并行”
- 可复用点候选:
  - refine 恢复链的真相源组合
  - ModelScope 替代 HF gated repo 的下载路径
  - `OMP_NUM_THREADS=1` 的环境稳定性要求
- 最适合写到哪里:
  - `EXPERIENCE.md`
- 是否提取/更新 skill:
  - 否。本轮更适合沉淀项目经验, 还没上升到跨项目通用 skill。

## 当前任务的后续行动建议

- 先确认之前的 ModelScope 下载会话 `86411` 是否还活着。
- 再核对 `/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev` 目录状态, 判断是继续补齐还是改为精简下载。
- 下载可用后, 重新拉起 `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` rerun, 并至少确认越过 `开始加载 Flux pipeline`。
