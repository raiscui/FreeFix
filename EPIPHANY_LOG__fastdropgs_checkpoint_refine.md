## [2026-03-29 16:59:33] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] 主题: `fastdropgs` 当前更像“隐式已支持”, 不像“完全不兼容的新格式”

### 发现来源
- 读取 `recon/import_fastgs.py`、`ours/run_fastgs_refine.py`
- 动态检查 `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth`
- 对该样本做真实 bridge smoke 与 refine wrapper dry-run

### 核心问题
- 用户表述是“再支持一种 fastdropgs checkpoint”
- 但动态证据表明, 当前桥接主链已经能吃下这份样本
- 真正缺的是:
  - 显式命名
  - 来源语义
  - 自动化测试
  - 文档与 wrapper 话术

### 为什么重要
- 这能避免后续把任务误做成“大规模重写导入器”
- 也能让 proposal 更聚焦在正确的缺口上

### 未来风险
- 如果直接把当前“碰巧能用”的状态当成“正式支持”, 后续一旦 checkpoint 槽位或命名再漂移, 就会缺测试兜底
- 如果 proposal 没把“现象上能跑”和“产品化支持”区分开, 实施阶段很容易改重了

### 当前结论
- 当前 bridge 已能导入该样本
- 当前 wrapper 已能编排该样本进入 refine 的 dry-run
- 新 change 应优先定义“把 `fastdropgs` 支持正式化”的边界

### 后续讨论入口
- [notes__fastdropgs_checkpoint_refine.md](/root/autodl-tmp/home/rais/FreeFix/notes__fastdropgs_checkpoint_refine.md)
- [task_plan__fastdropgs_checkpoint_refine.md](/root/autodl-tmp/home/rais/FreeFix/task_plan__fastdropgs_checkpoint_refine.md)

## [2026-03-29 18:46:27] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] 主题: refined checkpoint 的“文件名标签”和“恢复步数”必须显式解耦

### 发现来源
- `my8` 真实 refine 跑通后执行 `ours.evaluation`
- refined eval 首次和二次都在恢复步数解析阶段报错

### 核心问题
- 当前 refined ckpt 的文件命名依赖 `exp_name`
- 但 strategy 恢复步数真正需要的是数值型基础训练步数
- 如果把两者混成一个参数, 一旦 refined ckpt 没有 `step` 字段, 就会在评估或恢复路径上炸掉

### 为什么重要
- 这不是 `my8` 特例
- 任何字符串命名的 refined checkpoint 都可能命中同一类 bug

### 未来风险
- 如果继续让底层逻辑“猜”字符串型 `load_step` 的含义, 后续不同调用方很容易再出现同类不一致

### 当前结论
- 恢复步数应该作为显式数值参数传递
- refined ckpt 的文件名标签只负责定位文件, 不应该承担训练时间轴语义

### 后续讨论入口
- [recon/refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py)
- [recon/refine_runtime.py](/root/autodl-tmp/home/rais/FreeFix/recon/refine_runtime.py)
- [ours/evaluation.py](/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py)
