## [2026-04-02 05:31:57] [Session ID: session-20260402T052702Z-pose-jitter] 任务名称: 支持 `pose_jitter_views_per_source` 使用分数比例控制 synthetic plan 密度

### 任务内容
- 修改 `pose_jitter_views_per_source` 的解析与 synthetic plan 展开逻辑
- 让 refine 支持 `1/2`、`1/3`、`1/4`、`1/6`、`1/8` 这类比例参数
- 补充针对整数模式与分数模式的回归测试
- 同步更新 `exp_cfg/base.yaml` 的注释口径

### 完成过程
- 先定位到 `ours/refine_run_schedule.py` 当前直接对该参数做 `int(...)`, 证明确实现只支持整数重复次数
- 再做最小动态实验, 确认 `1/2`、`1/3` 等值当前会直接抛 `ValueError`, 不是“悄悄按 1 处理”
- 在 `recon/refine_view_plan.py` 新增:
  - 正整数 / 正分数字符串解析 helper
  - 稳定抽样的 fractional plan builder
- 在 `ours/refine_run_schedule.py` 中把该参数改成双语义:
  - 整数 -> 每个 source 重复 N 次
  - 分数 -> 每 `b` 个 source 保留前 `a` 个
- 在 `tests/test_refine_view_plan.py` 补了分数解析、稳定抽样和 `build_refine_view_plan(...)` 分数模式测试
- 继续运行运行时与 pose jitter 相关测试, 确认没有破坏 resume / log / render 相关契约

### 总结感悟
- 这次最关键的不是“支持几个字符串”, 而是把参数从“固定重复次数”升级成“采样密度”语义
- 只做白名单特判虽然也能过, 但后面一旦再冒出 `2/3`、`3/4` 这类需求, 还会重复改同一层
- 用稳定抽样而不是随机抽样, 对这种带 resume / plan_index / image_id 的链路更安全
