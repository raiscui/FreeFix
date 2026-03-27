## [2026-03-27 22:21:03] [Session ID: 20260327T221426Z-main] 主题: 基于 my5 的 `11999` checkpoint 继续做 Flux refine 与评测

### 待后续处理事项
- 直接使用已准备好的配置启动 Flux refine:
  - `.pixi/envs/default/bin/python -m ours.refine_by_flux --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml`
- refine 完成后继续做评测:
  - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml --eval_test`
- 如需自定义 train/test 切分, 优先先补 `partition.json`, 再重新计算:
  - `refine_start_idx`
  - `refine_end_idx`
  - `train_start_idx`
  - `train_end_idx`

## [2026-03-27 22:31:22] [Session ID: 20260327T221426Z-main] 主题: 基础模型评估已完成, 当前只剩 refined 路径待补

### 待后续处理事项
- 当前已完成:
  - `my5 stable_12k_dense @ 11999` 的基础模型评估
- 当前仍待完成:
  - 运行 Flux refine, 生成 `ckpt_flux_shinkai_museum_v2.pt`
  - refine 完成后再次执行:
    - `.pixi/envs/default/bin/python -m ours.evaluation --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2.yaml --eval_test`

## [2026-03-27 15:07:17] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 主题: refine 与 refined 评估已完成, 当前转入参数调优备忘

### 当前状态
- 已完成:
  - `ckpt_flux_shinkai_museum_v2.pt`
  - refined 评估
- 当前不再有“必须先补齐”的 refine 主链路待办

### 如果后续继续优化
- 优先做一次小范围超参数对照:
  - `strength`
  - `warp_ratio`
  - `refine_steps`
- 目标不是单看 `PSNR`, 而是重点观察能否把 `LPIPS` 拉回去

## [2026-03-27 15:36:37] [Session ID: 20260327T153637Z-main] 主题: `30k base` 已证明更优, 后续 refine 只值得做轻量参数搜索

### 当前状态
- 已完成:
  - `30k` 训练
  - `30k` 基础评估
  - `30k refine`
  - `30k refined` 评估
- 当前结论:
  - `30k base` 是目前最优结果
  - 当前这组 Flux 参数会把 `30k base` 拉差

### 如果后续继续优化
- 只建议做小范围、轻量 refine 参数搜索:
  - `strength` 往下试, 例如小于 `0.65`
  - `warp_ratio` 往下试, 例如小于 `0.3`
  - `refine_steps` 往下试, 避免过长修正
- 对照口径建议固定:
  - 基础入口始终用 `ckpt_29999.pt`
  - 重点看 `test LPIPS` 是否能回到 `0.20` 以下, 同时不明显伤 `PSNR / SSIM`

## [2026-03-27 18:09:34] [Session ID: 20260327T175741Z-main] 主题: 如果以后继续研究 split 规则, 应先固定一份独立 benchmark partition

### 待后续处理事项
- 当前 `test_every: 8` vs `test_every: 7` 的默认 test 集不同, 已经证明直接横比会混入 benchmark 差异。
- 如果后面还要继续研究:
  - `test_every`
  - 自定义 partition
  - 更长训练步数
  这类变量, 建议先固定一份独立 `partition.json` 作为所有实验共用 holdout。
- 这样后续所有对比都能直接看同一批 test 图, 不用每次再补“共同交集”校正。

## [2026-03-27 18:54:03] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 主题: `50k + 长 densify` 之后, base 路线的下一轮优先级

### 待后续处理事项
- 当前 `50k + 长 densify` 已确认有效, 但收益已经进入边际区间。
- 如果后面继续优化 base, 更推荐按下面顺序推进:
  - 固定 `test_every: 8`, 小范围搜索 densify 窗口而不是继续盲加总步数
  - 回看最明显 artifact 对应的原图、位姿和 COLMAP 质量
  - 若只关注主观观感, 再考虑单独做渲染侧小实验
- 当前不建议重新打开:
  - `app_opt=true`
  这条线, 因为用户已经明确不希望它影响 checkpoint 迁移兼容性

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 主题: 给外部 bridge ckpt 的评估入口补 `--ckpt-path` override

### 待后续处理事项
- 当前外部 FastGS -> FreeFix refine 已跑通。
- 但 `ours.evaluation` 的基础模型评估仍默认从:
  - `cfg.base_dir/ckpts/ckpt_<load_step>.pt`
  读取基础 checkpoint。
- 如果后面要对这条 `my5_nomask_v1` bridge 线补定量评估, 更稳的做法是:
  - 给 evaluation 也补一个和 refine 一样的 `--ckpt-path` override
  - 避免为了评估去手工挪动或伪装 `ckpt_35000.pt`

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 主题: 调查为什么 bridge base 明显低于 FastGS 原始结果

### 待后续处理事项
- 当前现象已经明确:
  - FastGS 原始 `results.json`:
    - `PSNR 27.2039`
    - `SSIM 0.8910`
    - `LPIPS 0.2026`
  - bridge base:
    - `PSNR 23.9542`
    - `SSIM 0.8489`
    - `LPIPS 0.2550`
- refined 已经把这条线明显拉回:
  - `PSNR 26.6134`
  - `SSIM 0.8804`
  - `LPIPS 0.2211`
- 但还需要后续继续验证:
  - `import_fastgs` 的 similarity 归一化是否对这份 `my5` checkpoint 仍存在契约偏差
  - FastGS 与 FreeFix 的 test 图顺序 / 相机排序 / 渲染约定是否完全一致
  - 是否需要补一个 `--no-normalize` 或不同 `test_every` 口径下的最小对照实验

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 主题: 外部 bridge 评估入口已补齐, 当前只保留 bridge fidelity 原因验证

### 当前状态
- 已完成:
  - `ours.evaluation` 的:
    - `--ckpt-path`
    - `--colmap-path`
  - 外部 bridge base 的真实评估
  - refined 的真实评估
  - 与 FastGS 原始 `results.json` 的对比
- 因此下面这个旧待办已经闭环:
  - “给外部 bridge ckpt 的评估入口补 `--ckpt-path` override”

### 待后续处理事项
- 如果后面继续查“为什么 bridge base 低于 FastGS 原始结果”, 优先按最小验证顺序推进:
  - 做一次 `import_fastgs` 的 `--no-normalize` 对照导入并重评估
  - 核对 FastGS 与 FreeFix 的:
    - test split
    - 相机顺序
    - 图像命名对应
  - 对同一帧补一次单帧指标复算, 排除 benchmark 口径差异
- 在这些最小验证完成前, 不要把当前现象直接表述成:
  - 已确认是导入脚本问题
  - 已确认是 benchmark 不一致

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 主题: `import_fastgs` 需要补高阶 SH rotation

### 当前状态
- 已完成验证:
  - benchmark 一致
  - checkpoint 解析一致
  - FreeFix renderer 在 raw 状态下可以复现 FastGS 指标
  - 掉分发生在 normalized transform 后
- 当前已验证主结论:
  - `transform_splats_to_freefix()` 在大角度全局旋转后, 没有同步旋转高阶 SH 系数

### 待后续处理事项
- 后续真正的代码修复优先级:
  - 在 `recon.import_fastgs` 里给 `shN` 增加 SH basis rotation
- 修完后的最小回归:
  - raw + raw cameras 的 full SH 评估
  - normalized + normalized cameras 的 full SH 评估
  - 两者应该重新接近
- 可以补的测试:
  - 给一个已知旋转的 SH 系数构造回归用例
  - 至少锁住:
    - `L=0` 不变
    - 纯 DC-only 场景在旋转前后结果一致
