## [2026-03-28 11:41:10] [Session ID: 113355] 主题: 当前 `fixsh_rerun` 级别的 Flux refine 参数在 `my5` 与 `my6` 上都不适合直接当量化主线

### 发现来源
- 在 `my6_nomask_v1` 真实跑完 bridge + refine + eval 后, 与此前 `my5 fixsh rerun` 结果并排观察时发现

### 核心问题
- 同一组近似参数在两个场景上都出现了相同趋势:
  - 主观上有修补能力
  - 但 GT 指标整体下降

### 为什么重要
- 这说明问题已经不太像单场景偶发现象。
- 如果后续继续把这组参数直接复用到别的场景, 很可能会重复得到“看起来修了, 指标却变差”的结果。

### 未来风险
- 后面如果只看 refine 后视频观感, 很容易误把它当成整体更优。
- 但在需要保量化指标的任务里, 这会把默认主线带偏。

### 当前结论
- `my6` 当前已知事实:
  - bridge base:
    - `PSNR 26.7898`
    - `SSIM 0.8661`
    - `LPIPS 0.1905`
  - refined:
    - `PSNR 25.9604`
    - `SSIM 0.8538`
    - `LPIPS 0.2149`
- 结合此前 `my5` 结果, 当前更稳的口径是:
  - bridge base 负责量化基线
  - refine 负责探索主观修补

### 后续讨论入口
- 下次如果继续做 `my6` 或其他场景的 Flux refine, 先看:
  - `notes__colmap_my6.md`
  - `LATER_PLANS__colmap_my6.md`
  - `notes__colmap_my5.md` 里的 `fixsh_rerun` 结果
