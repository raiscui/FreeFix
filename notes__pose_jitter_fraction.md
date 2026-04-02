## [2026-04-02 05:27:15] [Session ID: session-20260402T052702Z-pose-jitter] 笔记: `pose_jitter_views_per_source` 当前只支持整数重复, 不支持比例抽样

## 来源

### 来源1: `ours/refine_run_schedule.py`

- 要点:
  - `build_refine_view_plan(...)` 里当前直接执行:
    - `repeats_per_source = int(getattr(cfg, "pose_jitter_views_per_source", 1))`
  - 随后把这个整数传给 `build_split_index_plan(..., repeats_per_item=repeats_per_source)`
- 结论:
  - 当前实现的真实语义只有一种:
    - 每个 source 展开多少次
  - 还没有“按比例抽稀 source pool”的入口

### 来源2: `recon/refine_view_plan.py`

- 要点:
  - `build_split_index_plan(...)` 会对每个 `source_index` 固定展开 `repeats_per_item` 次
  - 当 `repeats_per_item < 1` 时直接报错
- 结论:
  - 底层 helper 同样只覆盖“整数重复次数”
  - 如果要支持 `1/2`、`1/3`, 需要在计划构造层新增新的解析语义

### 来源3: 最小动态实验

- 验证命令:
  - `OMP_NUM_THREADS=1 .pixi/envs/default/bin/python3 - <<'PY' ... build_refine_view_plan(...) ... PY`
- 关键输出:
  - `1 -> count=283, repeats_per_source=1`
  - `1/2 -> ValueError invalid literal for int() with base 10: '1/2'`
  - `1/3 -> ValueError invalid literal for int() with base 10: '1/3'`
  - `1/4 -> ValueError invalid literal for int() with base 10: '1/4'`
  - `1/6 -> ValueError invalid literal for int() with base 10: '1/6'`
  - `1/8 -> ValueError invalid literal for int() with base 10: '1/8'`

## 综合发现

### 现象

- 用户想把 refine 里的 synthetic train 图继续压低
- 当前参数 `pose_jitter_views_per_source` 只能表达“每个 source 复制几次”
- 当用户写 `1/2`、`1/3` 这类比例值时, 不是“数量不对”, 而是直接报错

### 当前主假设

- 最正确的修复, 是把该参数升级成“正整数或正分数”的统一采样密度配置:
  - 整数 `N` = 每个 source 重复 `N` 次
  - 分数 `a/b` = 对 source pool 做稳定抽样, 每 `b` 个 source 保留前 `a` 个

### 最强备选解释

- 也可以只对白名单 `1/2`、`1/3`、`1/4`、`1/6`、`1/8` 做特判, 快速绕过去
- 但这种方案会把语义继续硬编码在分支里, 后面扩新比例时还会再次改代码

### 什么证据会推翻当前主假设

- 如果后续发现恢复逻辑、日志结构或下游渲染强依赖“每个 source 都必须至少出现一次”, 那就不能直接按 source 抽样
- 目前静态检查里, `source_repeat_index` 只被日志和记录链路被动携带, 还没有看到这种强依赖

### 当前倾向结论

- 继续走“通用分数解析 + 稳定抽样”是最稳的
- 这样既能满足用户要的 `1/2`、`1/3`、`1/4`、`1/6`、`1/8`
- 也能保持 plan 顺序稳定, 不破坏 resume / log / image_id 的确定性

## [2026-04-02 05:31:57] [Session ID: session-20260402T052702Z-pose-jitter] 笔记: 实现后验证结果

## 来源

### 来源1: 单元测试与语法检查

- 验证命令:
  - `OMP_NUM_THREADS=1 .pixi/envs/default/bin/python3 -m unittest tests.test_refine_view_plan`
  - `OMP_NUM_THREADS=1 .pixi/envs/default/bin/python3 -m unittest tests.test_refine_runtime`
  - `OMP_NUM_THREADS=1 .pixi/envs/default/bin/python3 -m unittest tests.test_pose_jitter_refine`
  - `OMP_NUM_THREADS=1 .pixi/envs/default/bin/python3 -m py_compile recon/refine_view_plan.py ours/refine_run_schedule.py tests/test_refine_view_plan.py`
- 关键输出:
  - `test_refine_view_plan` -> `Ran 7 tests ... OK`
  - `test_refine_runtime` -> `Ran 11 tests ... OK`
  - `test_pose_jitter_refine` -> `Ran 13 tests ... OK`
  - `py_compile` 无报错

### 来源2: 283 个 train source 的最小动态实验

- 验证命令:
  - `OMP_NUM_THREADS=1 .pixi/envs/default/bin/python3 - <<'PY' ... build_refine_view_plan(...) ... PY`
- 关键输出:
  - `1: count=283 preview=[0, 1, 2, 3, ...]`
  - `1/2: count=142 preview=[0, 2, 4, 6, ...]`
  - `1/3: count=95 preview=[0, 3, 6, 9, ...]`
  - `1/4: count=71 preview=[0, 4, 8, 12, ...]`
  - `1/6: count=48 preview=[0, 6, 12, 18, ...]`
  - `1/8: count=36 preview=[0, 8, 16, 24, ...]`

## 综合发现

### 已验证结论

- 当前修复已经把 `pose_jitter_views_per_source` 的语义扩成两类:
  - 整数 -> 重复次数
  - 分数 -> 稳定抽样比例
- 分数模式下, 计划顺序仍然稳定, `plan_index / image_id / source_repeat_index` 契约保持可预测
- 对当前用户最关心的“train 图还是太多”, 现在已经有直接的比例收缩手段, 不再需要继续用“1 但还是嫌多”的方式硬扛
