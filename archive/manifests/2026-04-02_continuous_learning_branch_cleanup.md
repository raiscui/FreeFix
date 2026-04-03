# 2026-04-02 持续学习归档说明

## 背景

- 本轮由 `$continuous-learning` 显式触发
- 已先完成默认组六文件与当前根目录支线组六文件的检索、分组、阅读与摘要
- 归档对象只包含:
  - 本次已检索覆盖的支线
  - 且已判定为“未轮转旧支线”的对象

## 本轮判定结果

### 继续保留在根目录的活跃支线

- `__add_optional_flux_kontext_refine`
- `__my5_refine_formal`
- `__pose_jitter_fraction`
- `__continuous_learning`

### 本轮归档的未轮转旧支线

- `__fastgs_refine_probe`
- `__flux_shinkai_ply_export`
- `__nspr_eval`

## 归档清单

### `archive/branch_contexts/fastgs_refine_probe/`

- `task_plan__fastgs_refine_probe.md`
- `notes__fastgs_refine_probe.md`
- `WORKLOG__fastgs_refine_probe.md`
- `LATER_PLANS__fastgs_refine_probe.md`
- `ERRORFIX__fastgs_refine_probe.md`
- `EPIPHANY_LOG__fastgs_refine_probe.md`

### `archive/branch_contexts/flux_shinkai_ply_export/`

- `task_plan__flux_shinkai_ply_export.md`
- `notes__flux_shinkai_ply_export.md`
- `WORKLOG__flux_shinkai_ply_export.md`

### `archive/branch_contexts/nspr_eval/`

- `task_plan__nspr_eval.md`
- `notes__nspr_eval.md`
- `WORKLOG__nspr_eval.md`
- `LATER_PLANS__nspr_eval.md`
- `EPIPHANY_LOG__nspr_eval.md`

## 本轮沉淀到长期载体的内容

- `EXPERIENCE.md`
  - 新增 `pose_jitter_views_per_source` 的“整数重复 + 分数密度”语义说明
- `README.md`
  - 同步 `pose_jitter_views_per_source` 已支持分数模式
- `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml`
  - 修正 synthetic plan 数量注释

## 备注

- 本轮没有新增 `self-learning.*` skill
- 原因是新增知识主要是仓库内 refine 调度语义与上下文治理经验, 更适合保留在项目长期文件中
