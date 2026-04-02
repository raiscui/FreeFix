# 任务计划: 支持 `pose_jitter_views_per_source` 使用分数字面量控制采样比例

## [2026-04-02 05:27:15] [Session ID: session-20260402T052702Z-pose-jitter] [记录类型]: 建立支线计划

## 目标

- 让 `pose_jitter_views_per_source` 不只支持整数计数, 还支持 `1/2`、`1/3`、`1/4`、`1/6`、`1/8` 这类比例参数。
- 让 refine 的 synthetic train 图数量可以按 source pool 比例收缩, 避免即使设成 `1` 仍然在某些场景下显得过多。
- 为这条参数语义补上可验证测试, 防止后续再次回退到“只认整数”的行为。

## 阶段

- [x] 阶段1: 回读经验、上下文和相关配置现场
- [ ] 阶段2: 定位 `pose_jitter_views_per_source` 的解析与 plan 展开路径
- [ ] 阶段3: 实现比例参数支持并补齐测试
- [ ] 阶段4: 运行验证并记录交付

## 关键问题

1. 用户当前看到的“train 图还是太多”, 是参数根本没参与生效, 还是它只支持“每源固定次数”, 不支持按比例抽稀?
   - 当前先作为候选假设处理, 需要顺着解析路径和 plan 展开路径各自验证。
2. 最稳妥的实现方式是什么?
   - 方案A: 做成通用分数解析, 然后统一收敛成每个 source 是否保留的抽样规则。这是最佳方案, 语义更清楚。
   - 方案B: 只对白名单字符串 `1/2`、`1/3`、`1/4`、`1/6`、`1/8` 做分支特判。这能更快落地, 但后续更难维护。

## 做出的决定

- [暂定] 优先朝方案A排查和实现。
  - 理由: 这类参数本质上是“采样密度”, 不应继续绑死在“整数重复次数”的单一语义上。
- [保留备选] 如果现有代码路径强依赖整数, 再评估是否先用方案B保守落地。

## 遇到的错误

- 暂无

## 状态

**目前在阶段2** - 正在定位参数解析和 synthetic plan 展开路径, 先确认真实数量膨胀发生在哪一层。

## [2026-04-02 05:27:15] [Session ID: session-20260402T052702Z-pose-jitter] [记录类型]: 阶段2完成, 开始实现比例参数支持

- 已确认的现象:
  - `pose_jitter_views_per_source` 在 `ours/refine_run_schedule.py` 里被直接 `int(...)`
  - 传入 `1/2`、`1/3` 这类值时, 当前会直接抛 `ValueError`
- 已确认的动态证据:
  - 对 283 个 train source 做最小实验时:
    - `1` -> `count=283`
    - `1/2` -> `ValueError: invalid literal for int() with base 10: '1/2'`
- 实现决定:
  - 新增“正整数 / 正分数”解析
  - 整数继续表示“每个 source 重复 N 次”
  - 分数表示“按固定比例稳定抽样 source pool”, 例如 `1/2` 表示每 2 个 source 保留 1 个

## 阶段

- [x] 阶段1: 回读经验、上下文和相关配置现场
- [x] 阶段2: 定位 `pose_jitter_views_per_source` 的解析与 plan 展开路径
- [ ] 阶段3: 实现比例参数支持并补齐测试
- [ ] 阶段4: 运行验证并记录交付

## 状态

**目前在阶段3** - 正在修改 plan 构造逻辑, 让 `pose_jitter_views_per_source` 同时支持整数重复和分数抽样。

## [2026-04-02 05:31:57] [Session ID: session-20260402T052702Z-pose-jitter] [记录类型]: 阶段3与阶段4完成

- 已完成实现:
  - 新增 `pose_jitter_views_per_source` 的正整数 / 正分数字符串解析
  - 整数继续表示“每个 source 重复 N 次”
  - 分数改为“按固定比例稳定抽样 source pool”
- 已完成验证:
  - `python3 -m unittest tests.test_refine_view_plan`
  - `python3 -m unittest tests.test_refine_runtime`
  - `python3 -m unittest tests.test_pose_jitter_refine`
  - `python3 -m py_compile recon/refine_view_plan.py ours/refine_run_schedule.py tests/test_refine_view_plan.py`
  - 283 个 train source 的最小动态实验:
    - `1 -> 283`
    - `1/2 -> 142`
    - `1/3 -> 95`
    - `1/4 -> 71`
    - `1/6 -> 48`
    - `1/8 -> 36`

## 阶段

- [x] 阶段1: 回读经验、上下文和相关配置现场
- [x] 阶段2: 定位 `pose_jitter_views_per_source` 的解析与 plan 展开路径
- [x] 阶段3: 实现比例参数支持并补齐测试
- [x] 阶段4: 运行验证并记录交付

## 状态

**目前已完成** - `pose_jitter_views_per_source` 已支持整数重复与分数抽样, 且相关计划构造与运行时测试均已通过。
