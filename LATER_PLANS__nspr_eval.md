## [2026-04-01 07:08:15] [Session ID: 4138] 主题: 后续补齐 `ours.evaluation` 的显式评估口径控制

### 待后续处理事项
- 当前 `ours.evaluation` 的 test 循环直接使用 `refine_start_idx/refine_end_idx`
- 当配置像 `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 这样:
  - 固定窗口是 `100` 张 train 图
  - 真实 test split 只有 `41` 张
- 默认脚本就会出现“固定窗口”和“benchmark test”口径缠在一起的问题
- 后续更合理的改造方向:
  - 增加显式参数, 区分 `fixed_window_eval` 与 `dataset_split_eval`
  - test 默认按 `len(test_dataset)` 走, 不再复用 fixed window 长度
  - 输出 JSON 里写入 `split`、`count`、`trans`、`source_semantics`
