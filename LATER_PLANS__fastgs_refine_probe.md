
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
