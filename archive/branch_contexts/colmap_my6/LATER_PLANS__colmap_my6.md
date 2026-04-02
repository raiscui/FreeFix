## [2026-03-28 11:41:10] [Session ID: 113355] 计划: 为 `my6` 追加一轮轻量 Flux refine 参数扫描

### 背景
- 当前 `fixsh_rerun` 参数:
  - `strength: 0.65`
  - `refine_steps: 400`
  - `warp_ratio: 0.3`
- 在 `my6` 上会造成:
  - `test PSNR -0.8293`
  - `test SSIM -0.0123`
  - `test LPIPS +0.0244`

### 建议方向
- 先做 1 到 2 条轻量对照线, 不要一下子扫很多组合。
- 优先尝试:
  - 降低 `strength`
  - 降低 `refine_steps`
  - 保持 `warp_ratio` 不变, 先减少变量

### 为什么值得以后做
- 当前 bridge base 已经能稳定保住量化质量。
- 如果后续要在 `my6` 上追更好的主观观感, 应该先找“更轻”的 refine 区间, 而不是继续沿用当前这组偏强参数。
