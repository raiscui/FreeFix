## [2026-03-29 18:46:27] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] 问题: refined checkpoint 评估阶段把字符串型 `exp_name` 误当恢复步数

### 现象
- `ours.evaluation` 在基础模型评估完成后, 进入 refined eval 时崩溃
- 首轮报错:
  - `ValueError: invalid literal for int() with base 10: '<exp_name>'`
- 第二轮在补了第一层兜底后仍报:
  - `checkpoint 未记录有效 step, 且当前 load_step 也不是可转成整数的值`

### 原因
- refined checkpoint 的文件定位依赖 `exp_name`, 这是字符串
- `recon.refiner.Refiner` 又把同一个 `load_step` 参数传给 `resolve_strategy_resume_step(...)` 当恢复步数候选
- 当前这份 refined ckpt 没有 `step` 字段, 所以不能只靠 `payload_step` 兜底
- `Refiner` 当时只拿到 GS `cfg.json`, 并不知道 exp/refine 配置里的数值型基础 `load_step`

### 修复
- 在 `recon/refine_runtime.py` 中为恢复步数解析增加 `fallback_load_step`
- 在 `recon/refiner.py` 中新增显式参数 `resume_load_step`
- 在 `ours/evaluation.py` 中:
  - base eval 显式传 `resume_load_step=base_load_step`
  - refined eval 也显式传 `resume_load_step=base_load_step`
- 补测试:
  - `tests/test_refine_runtime.py`
    - payload step 优先
    - 字符串型 refined 名称可回退到数值型基础 step
    - 没有任何数值候选时给出清晰报错

### 验证
- `python3 -m py_compile recon/refiner.py ours/evaluation.py recon/refine_runtime.py`
- `timeout 120s ... python -m unittest tests.test_refine_runtime tests.test_evaluation_cli`
  - `Ran 13 tests`
  - `OK`
- `timeout 1800s ... python -m ours.evaluation --exp_cfg ...my8... --colmap-path /home/rais/FastGS/data/my8_colmap_fastgs_input_pruned_v1 --ckpt-path data/fastgs_bridge/my8_input_50k_from45k_resetopt/chkpnt50000_freefix.pt --eval_test`
  - 最终退出码 `0`
  - refined `*_test.json` 和 `*_train.json` 均成功落盘
