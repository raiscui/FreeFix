
## [2026-03-29 10:53:59] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 主题: 随机相机偏移版 Flux refine 的后续实施候选

### 延后事项
- 候选1: 在 refine config 中新增受控 synthetic camera 采样开关
  - 示例方向:
    - `refine_camera_mode: fixed | pose_jitter`
    - `refine_camera_source_split: train | refine | test`
    - `pose_jitter_trans_sigma`
    - `pose_jitter_rot_sigma_deg`
    - `pose_jitter_trans_max`
    - `pose_jitter_rot_max_deg`
- 候选2: 先做最小验证实验
  - 只在 5-10 个视角上做很小 jitter
  - 比较 before/after render 的多视角一致性与 hallucination 情况
- 候选3: 在 benchmark 体系里拆出独立 refine split
  - 避免继续直接围绕 `test_split=test` 做训练增强
- 候选4: 给 synthetic 视角增加安全阈值
  - 例如 alpha 覆盖率、深度跳变、与邻近真实视角的重投影差异等过滤条件

### 当前不做的原因
- 这轮任务是 explore, 目标是先把语义边界和风险讲清楚
- 在还没有最小实验前, 直接实现大版本很容易把“看起来更丰富”误当成“真的更正确”

## [2026-03-29 11:46:57] [Session ID: codex-add-pose-jitter-apply] 主题: 补一轮真实 Flux pose jitter smoke, 给 `4.2` 收尾

### 延后事项
- 用模块方式重新发起真实 smoke:
  - `python3 -m ours.refine_by_flux --exp_cfg <smoke_yaml>`
- 优先确认它能真正进入主循环并创建:
  - `before_refine/`
  - `refine/render/`
  - `refine/pose_jitter_log.jsonl`
- 如果仍长时间无输出, 下一轮直接围绕 `pipe.to(cuda)` 继续取证:
  - 单独测 `pipe.to(cuda)` 时间窗口
  - 观察显存变化曲线
  - 必要时再把 `pipe.to(cuda)` 内部拆到更细
- 只有在真实 smoke 至少跑完 1 帧后, 再考虑把 OpenSpec `4.2` 勾掉

### 当前不做的原因
- 本轮已经完成代码、单测、CLI smoke 和任务回写
- 真实 Flux smoke 的阻塞点已经收敛到 `pipe.to(cuda)`, 但本轮还没有拿到它返回后的动态证据

## [2026-03-29 12:40:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 主题: `4.2` 的真实 smoke 延后项已完成, 后续只保留更大规模视觉回归

### 延后事项
- 候选1: 用 `refine_pipeline_offload_mode: model_cpu` 再补一轮 5-10 帧 smoke
  - 重点看 fixed-view `before_refine / after_refine` 的一致性变化
  - 留意薄结构、遮挡边界和镜面区域
- 候选2: 如果后续要恢复默认 `none` 路径, 需要单独继续取证 `pipe.to(cuda)` 在本机为什么会长时间阻塞
  - 当前已知的是“阻塞边界”
  - 不是对 diffusers 内部具体实现的最终根因结论

### 当前不做的原因
- OpenSpec `add-pose-jitter-refine` 的任务已经全部完成
- 这两个方向都属于“进一步增强证据”而不是当前 change 的收尾前提

## [2026-03-30 00:44:35] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 主题: 补查 stronger 正式 run 为什么没有最终 refined checkpoint

### 延后事项
- 复核 `ours/refine_by_flux.py` 长跑结束后的保存阶段
  - 目标文件按代码应为:
    - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_pose_jitter_train_100_stronger_20260329.pt`
- 优先做最小取证:
  - 给 `refiner.save()` 前后补阶段日志
  - 再跑一轮更小规模 refine, 看是:
    - 根本没走到 save
    - save 抛错但没进当前日志
    - 还是保存到了别的路径

### 当前不做的原因
- 本轮用户先要的是“评估下”
- 图像结果已经可以独立评估
- 但 checkpoint 持久化问题属于另一个收尾排查任务

## [2026-03-31 00:25:00] [Session ID: 019d436e-9bf6-7313-ab99-623578ee4ecf] 主题: 补查 `train_test_x3_20260330` 为什么停在 `plan_index=326`

### 延后事项
- 给 `ours/refine_by_flux.py` 的 refine 主循环补更细的阶段日志
  - 至少记录:
    - 每个 `plan_index` 开始
    - `pipe(...)` 返回
    - `refiner.refine(...)` 返回
- 给 watcher 补最终退出状态记录
  - 包括:
    - 进程退出时间
    - exit code / signal
    - 是否真正开始执行 `ours.evaluation`
- 如果要最小复现, 优先做一轮缩小版配置
  - 保留同样的 `pose_jitter` 语义
  - 但把 synthetic plan 压到几十帧
  - 看是否仍会在“无 traceback”的情况下提前停掉

### 当前不做的原因
- 当前用户问题只是在问“为什么没有 `after_refine.mp4`”
- 这个问题已经能用现有证据回答:
  - run 没有走完整个收尾链路
- 但“为何中途停掉”的最终根因, 还需要下一轮专门取证
## [2026-03-31 00:42:00] [Session ID: codex-refine-resume-speed-20260331] 主题: GPU 机器上补 refine render 动态 benchmark

### 待办事项
- 在有可用 NVIDIA driver 的机器上, 对比 fixed-view 导出两条路径的真实耗时:
  - 旧路径: 单视角逐帧 render
  - 新路径: `render_fixed_rgb_batch(...)`
- 如果还要继续追求 synthetic 主循环速度, 下一步先做 profile, 不直接做多 plan 并发

### 原因
- 当前机器只能完成静态验证和纯 Python 测试
- 用户已经明确关心“render 图片是否能多个同时生成”
- 这个问题后续需要 GPU 实测数据, 不能只靠静态阅读下结论

## [2026-04-01 18:17:27] [Session ID: 37900] 主题: 若后续每轮 refine 都需要交付 `ply`, 可把导出动作接进主收尾链路

### 延后事项
- 在 `refine` 完成保存 final ckpt 后, 复用现有 [export_3dgs_ply.py](/root/autodl-tmp/home/rais/FreeFix/recon/export_3dgs_ply.py) 自动补导出 refined `point_cloud`
- 如果同时希望收尾更可读, 可以让 watcher 在 `evaluation` 结束后直接打印 `PSNR/SSIM/LPIPS` 摘要, 减少人工再读 `json`

### 当前不做的原因
- 本轮用户目标是先把新配置口径下的一整套重跑和评估拿出来
- 当前已有现成导出入口, 手动补导出足以完成交付, 不必在收尾阶段再改主流程代码

## [2026-04-01 21:14:00] [Session ID: 2a213fb2-1d29-4f62-9c76-68a7700db14c] 主题: 如果后面还觉得重影偏重, 可把“邻居平均半径”从 cap 升级成真正的采样分布

### 延后事项
- 评估是否把当前 `neighbor_average_radius` 语义从:
  - “高斯方向采样后再做总半径 cap”
  升级成:
  - “半径本身也围绕邻居距离统计量采样”
- 候选方向:
  - 用邻居距离均值/分位数直接决定半径
  - 先采方向, 再单独采一个半径标量
  - 或按局部相机速度做各向异性 jitter

### 当前不做的原因
- 用户这轮需求是先把“前后相邻镜头平均半径”真正接进现有 pose jitter 链路
- 当前第一版已经满足这个目标, 而且对旧行为破坏更小
- 如果现在直接升成全新分布, 变量会一下变多, 不利于判断重影变化到底来自哪里
