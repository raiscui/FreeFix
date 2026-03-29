
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
