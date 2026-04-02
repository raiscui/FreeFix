## [2026-04-01 07:08:15] [Session ID: 4138] 任务名称: 评估 `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330` 的 `NSPR/PSNR`

### 任务内容
- 回读当前实验的配置、输出目录和历史支线记录
- 核对项目里到底有没有 `NSPR` 这个指标
- 在不改代码的前提下, 按项目同口径逻辑重算该实验的质量指标

### 完成过程
- 先确认实验配置与输出目录真实存在, 并且 refined checkpoint 已经成功落盘
- 再读取 [ours/evaluation.py](/root/autodl-tmp/home/rais/FreeFix/ours/evaluation.py)、[recon/refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py) 和 [ours/refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py)
- 静态确认项目原生指标只有 `PSNR / SSIM / LPIPS`, 没有 `NSPR`
- 动态确认当前 `my5` 场景数据划分是:
  - `train=283`
  - `test=41`
- 使用项目环境里的 `Refiner.render(..., eval=True)` 分别对 base/refined checkpoint 重算:
  - 原 `test` split `41` 张
  - 固定窗口 `100` 张 train 图
  - 全量 `283` 张 train 图

### 总结感悟
- 这次真正要避免的不是“算不出一个数”, 而是“在错误口径上算出一个看起来很像正确答案的数”
- 对这种配置已经污染 benchmark 的 refine 实验, 交付时必须把:
  - 指标名
  - split
  - 样本数
  - 是否污染
- 一起说清楚, 不然数字会非常误导人
