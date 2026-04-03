## [2026-04-01 07:08:15] [Session ID: 4138] 主题: 固定对比窗口和 benchmark test 共用一套索引, 会把评估口径悄悄搞乱

### 发现来源
- 在评估 `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 的 `PSNR` 时, 对照 `ours.evaluation.py`、`ours.refine_by_flux.py` 和真实数据划分发现

### 核心问题
- `ours.refine_by_flux.py` 的 `before_refine/after_refine` 固定窗口使用 `refine_start_idx/refine_end_idx`
- `ours.evaluation.py` 的 test 循环也复用了同一段索引
- 一旦配置里:
  - `test_split=train`
  - 或 `refine_end_idx` 大于真实 test split 长度
- “固定观察窗口”和“benchmark test”就不再是同一回事

### 为什么重要
- 这类问题很危险, 因为它不会自动报“你的指标语义错了”
- 人很容易看到脚本名和输出文件名, 就误以为自己拿到的是标准 test 指标

### 未来风险
- 后续任何为了可视化方便把 fixed window 设大、改成 train、或混入自定义 split 的实验
- 都可能继续产生“数字看起来正常, 口径其实不对”的结果

### 当前结论
- 评估脚本需要把“固定窗口导出”和“dataset split 评估”明确拆开
- 在改造前, 对这类实验只能用自定义重算脚本或手工说明口径

### 后续讨论入口
- 下次再看 refine 指标时, 先回看 [ours/evaluation.py](/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py) 和这条记录
