# 任务计划: 使用 `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 正式跑 `refine my5`

## [2026-04-02 04:18:58] [Session ID: omx-1775103327604-vnl611] [记录类型]: 建立正式运行支线计划

## 目标

- 用 `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 启动一次干净、可追踪、可恢复的正式 `my5` Flux refine。
- 避免旧同名 final checkpoint 污染这次正式 run 的启动、失败判定与后续交付口径。
- 至少确认新 run 已成功进入主流程, 并把日志入口与运行状态记录清楚。

## 阶段

- [x] 阶段1: 回读经验、现有上下文、配置与旧产物状态
- [ ] 阶段2: 备份旧同名产物并准备正式启动环境
- [ ] 阶段3: 启动正式 refine run 并确认已进入主循环
- [ ] 阶段4: 记录结果入口、验证证据与交付说明

## 关键问题

1. 当前 `v3` 配置是否会因为旧同名 final checkpoint 而直接跳过执行?
   - 不会。代码里的“已 complete 直接退出”依赖 `refine_resume_state.json`。当前该文件不存在。
2. 当前最危险的污染点是什么?
   - 旧同名 final / resume checkpoint 仍在。如果新 run 半途失败, 会把旧 final 误留在现场, 干扰后续判断。

## 做出的决定

- [采用] 方案A: 备份旧同名 final / resume / ply, 然后按原配置原地正式重跑。
  - 理由: 用户明确指定了这份配置文件, 不改 `exp_name` 更符合当前请求, 但必须先做备份防污染。
- [未采用] 方案B: 直接修改配置换新 `exp_name` 再跑。
  - 理由: 这样更干净, 但会偏离用户明确指定的配置文件语义, 本轮不默认这么做。

## 遇到的错误

- 暂无

## 状态

**目前在阶段2** - 正在备份旧同名产物, 然后启动正式 `my5` refine。

## [2026-04-02 04:18:58] [Session ID: omx-1775103327604-vnl611] [记录类型]: 阶段2完成, 准备启动正式 run

- 已完成的预检:
  - 旧同名 final / resume / ply 已备份为 `__formal_rerun_backup_20260402_041941`
  - 已确认不能使用 `direnv exec . python3`, 必须改用 `.pixi/envs/default/bin/python3`
  - 已确认 `v3` 当前真实 `plan_count = 283`
- 下一步:
  - 预创建输出目录并接管 `run.log`
  - 用 `.pixi/envs/default/bin/python3` 正式启动 `ours.refine_by_flux`

## 状态

**目前在阶段3** - 正在启动正式 refine run, 并验证是否进入主循环。

## [2026-04-02 04:24:19] [Session ID: omx-1775103327604-vnl611] [记录类型]: 第一次正式启动失败, 切换到 ffmpeg 修正重跑

- 现象:
  - run 已进入 `before_refine` 导出
  - 失败于 `before_refine.mp4` writer 初始化
- 已验证结论:
  - `IMAGEIO_FFMPEG_EXE` 被错误设置成不存在的 `.pixi` 路径
  - 当前机器真实可用 ffmpeg 是 `/usr/bin/ffmpeg`
- 下一步:
  - 备份本次失败输出目录
  - 用 `/usr/bin/ffmpeg` 重新启动正式 run

## 状态

**目前在阶段3** - 正在修正 ffmpeg 路径并重启正式 refine run。

## [2026-04-02 04:26:38] [Session ID: omx-1775103327604-vnl611] [记录类型]: 阶段3与阶段4完成

- 启动入口:
  - `OMP_NUM_THREADS=1 IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg .pixi/envs/default/bin/python3 -u -m ours.refine_by_flux --exp_cfg exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml`
- 当前运行会话:
  - PTY session: `86828`
  - 进程: `timeout PID 35293`, `python PID 35295`
- 当前结果入口:
  - 输出目录: `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`
  - 日志: `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330/run.log`
- 动态验证证据:
  - 已越过第一次失败点 `before_refine.mp4`
  - 已进入主 refine 循环并持续输出 loss 进度

## 阶段

- [x] 阶段1: 回读经验、现有上下文、配置与旧产物状态
- [x] 阶段2: 备份旧同名产物并准备正式启动环境
- [x] 阶段3: 启动正式 refine run 并确认已进入主循环
- [x] 阶段4: 记录结果入口、验证证据与交付说明

## 状态

**目前已完成** - 本轮目标已完成: `my5` 正式 refine 已成功启动并进入主循环, 当前正在后台继续运行。

## [2026-04-02 04:51:11] [Session ID: omx-1775103327604-vnl611] [记录类型]: 根据用户选择 `1+2` 扩展完成标准

- 用户新要求:
  - 不只监控到 refine 结束
  - 还要在结束后补齐 evaluation 与 `ply` 导出
- 当前现场:
  - refine 进程仍在运行
  - 只有 rolling resume checkpoint, 还没有 final checkpoint
  - 也还没有新的 `point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
- 因此本支线新的完成标准改为:
  1. refine 进程完整结束
  2. final checkpoint 落盘
  3. evaluation 完成并有结果文件
  4. refined ply 成功导出

## 阶段

- [x] 阶段1: 回读经验、现有上下文、配置与旧产物状态
- [x] 阶段2: 备份旧同名产物并准备正式启动环境
- [x] 阶段3: 启动正式 refine run 并确认已进入主循环
- [ ] 阶段4: 监控直到 refine 完整结束并确认 final checkpoint 落盘
- [ ] 阶段5: 运行 evaluation 并核对输出
- [ ] 阶段6: 导出 refined ply 并做最终交付记录

## 状态

**目前在阶段4** - 正在持续监控正式 refine, 等待 final checkpoint 落盘后继续做 evaluation 与 ply 导出。

## [2026-04-02 05:29:08] [Session ID: omx-1775103327604-vnl611] [记录类型]: Flux 正式 run 已完成, 准备切 Kontext 对照跑

- 已验证 Flux 终态:
  - final checkpoint 已保存
  - 退出码 `0`
- 用户新增要求:
  - 基于同一份 `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 的实验口径
  - 先补跑一遍 Kontext
  - 再把 Flux 与 Kontext 一起评估和对比
- 当前决策:
  - 不直接用原 yaml 原地跑 Kontext, 因为原 yaml 的 `exp_name` 会覆盖已完成的 Flux 结果
  - 生成一份只改 `exp_name` 的 Kontext 临时配置, 保持其余参数和当前 yaml 一致

## 阶段

- [x] 阶段1: 回读经验、现有上下文、配置与旧产物状态
- [x] 阶段2: 备份旧同名产物并准备正式启动环境
- [x] 阶段3: 启动正式 Flux run 并确认已进入主循环
- [x] 阶段4: 监控直到 Flux 完整结束并确认 final checkpoint 落盘
- [ ] 阶段5: 生成 Kontext 对照配置并完成 Kontext 正式 run
- [ ] 阶段6: 运行 Flux/Kontext evaluation 并做对比
- [ ] 阶段7: 按交付需要补导出 refined ply

## 状态

**目前在阶段5** - 正在为 Kontext 生成不覆盖 Flux 结果的临时配置, 然后启动正式对照 run。

## [2026-04-02 05:32:05] [Session ID: omx-1775103327604-vnl611] [记录类型]: 回滚上一假设, 直接按原 yaml 跑 Kontext

- 上一假设:
  - 这份 yaml 仍在复用 Flux 的旧 `exp_name`, 需要临时派生 Kontext 配置
- 新证据:
  - 当前磁盘上的 `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 实际写的是:
    - `exp_name: kontext_pose_jitter_train_kontext`
- 结论:
  - 上一假设不成立
  - 当前 yaml 本身已经是安全的 Kontext 输出命名, 不会覆盖 Flux 结果
  - 因此直接按用户点名的原 yaml 跑 Kontext 即可

## 状态

**目前在阶段5** - 正在直接用原 yaml 启动 Kontext 正式 run。

## [2026-04-02 06:03:13] [Session ID: omx-1775103327604-vnl611] [记录类型]: 用户修改 `kontext_prompt`, 改为停旧进程后重跑

- 已验证事实:
  - 当前 `ours.refine_by_kontext` 进程组仍在运行
  - 它不会热更新读取新的 yaml
  - 当前磁盘上的 `kontext_prompt` 已被用户改写
- 决策:
  - 停掉旧 Kontext 进程组
  - 备份旧 prompt 下的半截输出与 rolling checkpoint
  - 直接按同一份 yaml 重跑 Kontext

## 状态

**目前在阶段5** - 正在终止旧 Kontext run, 然后按新 prompt 重跑。

## [2026-04-02 07:59:32] [Session ID: omx-1775103327604-vnl611] [记录类型]: Kontext 新 prompt 版已完成, 开始导出与对比

- 已验证终态:
  - `ckpt_kontext_pose_jitter_train_kontext.pt` 已落盘
  - `kontext process exit_code=0`
- 当前剩余交付:
  1. 导出 Flux refined ply
  2. 导出 Kontext refined ply
  3. 跑 Flux / Kontext evaluation
  4. 汇总指标对比

## 阶段

- [x] 阶段1: 回读经验、现有上下文、配置与旧产物状态
- [x] 阶段2: 备份旧同名产物并准备正式启动环境
- [x] 阶段3: 启动正式 Flux run 并确认已进入主循环
- [x] 阶段4: 监控直到 Flux 完整结束并确认 final checkpoint 落盘
- [x] 阶段5: 按最新 prompt 完成 Kontext 正式 run
- [ ] 阶段6: 导出 Flux / Kontext refined ply
- [ ] 阶段7: 运行 Flux / Kontext evaluation 并做对比
- [ ] 阶段8: 写回最终交付记录

## 状态

**目前在阶段6** - 正在导出两份 refined ply, 然后接 evaluation 对比。

## [2026-04-02 08:07:00] [Session ID: omx-1775103327604-vnl611] [记录类型]: 两份 refined ply 已导出, 开始跑 evaluation 对比

- 已完成:
  - `point_cloud_flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330.ply`
  - `point_cloud_kontext_pose_jitter_train_kontext.ply`
- 下一步:
  - 为 Flux 生成一份只用于 evaluation 的临时 yaml, 恢复其 `exp_name`
  - 分别运行 Flux / Kontext evaluation
  - 汇总 train/test 指标对比

## 阶段

- [x] 阶段1: 回读经验、现有上下文、配置与旧产物状态
- [x] 阶段2: 备份旧同名产物并准备正式启动环境
- [x] 阶段3: 启动正式 Flux run 并确认已进入主循环
- [x] 阶段4: 监控直到 Flux 完整结束并确认 final checkpoint 落盘
- [x] 阶段5: 按最新 prompt 完成 Kontext 正式 run
- [x] 阶段6: 导出 Flux / Kontext refined ply
- [ ] 阶段7: 运行 Flux / Kontext evaluation 并做对比
- [ ] 阶段8: 写回最终交付记录

## 状态

**目前在阶段7** - 正在生成 Flux evaluation 临时配置, 并开始两边评估。

## [2026-04-02 08:46:02] [Session ID: omx-1775103327604-vnl611] [记录类型]: 阶段6到阶段8完成

- 已完成:
  - Flux refined ply 导出
  - Kontext refined ply 导出
  - Flux evaluation 完成
  - Kontext evaluation 完成
  - Flux / Kontext 指标对比完成
- 关键结论:
  - 当前这组结果中, Kontext 在 train/test 的 `PSNR / SSIM / LPIPS` 三项上都优于 Flux

## 阶段

- [x] 阶段1: 回读经验、现有上下文、配置与旧产物状态
- [x] 阶段2: 备份旧同名产物并准备正式启动环境
- [x] 阶段3: 启动正式 Flux run 并确认已进入主循环
- [x] 阶段4: 监控直到 Flux 完整结束并确认 final checkpoint 落盘
- [x] 阶段5: 按最新 prompt 完成 Kontext 正式 run
- [x] 阶段6: 导出 Flux / Kontext refined ply
- [x] 阶段7: 运行 Flux / Kontext evaluation 并做对比
- [x] 阶段8: 写回最终交付记录

## 状态

**目前已完成** - Flux / Kontext 的 refined ply 与指标对比都已完成。
