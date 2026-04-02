## [2026-04-02 05:31:57] [Session ID: session-20260402T052702Z-pose-jitter] 任务名称: `pose_jitter_views_per_source` 无法表达低于 1 的 synthetic plan 密度

### 问题现象
- 用户希望继续降低 refine 阶段的 synthetic train 图数量
- 当前把 `pose_jitter_views_per_source` 写成 `1/2`、`1/3`、`1/4`、`1/6`、`1/8` 时, 程序不会按比例收缩
- 最小动态实验显示, 它会直接报:
  - `ValueError: invalid literal for int() with base 10: '1/2'`

### 原因分析
- `ours/refine_run_schedule.py` 当前直接执行:
  - `int(getattr(cfg, "pose_jitter_views_per_source", 1))`
- `recon/refine_view_plan.py` 的底层 helper 也只支持 `repeats_per_item >= 1` 的整数重复语义
- 所以问题不是“比例参数没调好”, 而是“分数语义从未被实现”

### 修复方法
- 在 `recon/refine_view_plan.py` 增加正整数 / 正分数字符串解析
- 保留旧整数语义:
  - `3` = 每个 source 重复 3 次
- 新增分数语义:
  - `1/2` = 每 2 个 source 保留 1 个
  - `1/3` = 每 3 个 source 保留 1 个
- 在 `ours/refine_run_schedule.py` 中按解析结果分流到:
  - 整数重复 builder
  - 分数稳定抽样 builder

### 验证结果
- `tests.test_refine_view_plan` 通过
- `tests.test_refine_runtime` 通过
- `tests.test_pose_jitter_refine` 通过
- 283 个 train source 的最小动态实验结果:
  - `1 -> 283`
  - `1/2 -> 142`
  - `1/3 -> 95`
  - `1/4 -> 71`
  - `1/6 -> 48`
  - `1/8 -> 36`

### 避坑提醒
- 这类带 resume / plan_index / image_id 的链路, 抽样逻辑不要用随机数
- 随机抽样会让断点恢复、日志回放和图像命名变得不可预测
- 固定比例的稳定抽样更适合这种计划驱动型管线
