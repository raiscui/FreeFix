## [2026-03-28 16:22:55] [Session ID: 75b3a1b3-0719-49e9-adc0-80fc3ad65971] 主题: 若继续优化 my7 refine, 优先做轻量参数回归

### 待后续处理事项
- 当前 `my7` 已经完成可复用的一轮 bridge + refine + eval。
- 如果后续继续追求更平衡的量化结果, 优先尝试:
  - 略降 `strength`
  - 略调 `warp_ratio`
  - 收紧 prompt 的修复强度
- 目标不是盲目追更高 `PSNR`, 而是看能否在保住 `PSNR` 提升的同时, 把 `SSIM / LPIPS` 拉回去。
