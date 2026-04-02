
## [2026-04-02 00:35:20] [Session ID: omx-1775055181169-iytve2] 问题: 想把 preview 样本切到 `80..82`, 结果 `before_refine` 越界

### 现象
- 运行 `ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_preview_ultrashort_jitterhard_20260401T163327Z.yaml` 时, 在 `before_refine` 阶段报:
  - `IndexError: index 80 is out of bounds for axis 0 with size 41`

### 原因
- 当前 preview 流程里, `refine_start_idx/refine_end_idx` 不只控制 synthetic source plan
- 它还驱动 fixed-view 的 `before_refine / after_refine` 对比渲染
- 当前 fixed-view 可用索引窗口大小只有 41, 不能直接改到 80 以上

### 修复
- 撤回“切换到 80..82 样本”这个假设
- 保持 `refine_start_idx/refine_end_idx = 0..3`
- 仅提高 pose jitter 的平移 / 旋转 / coverage 宽容度, 用更猛的扰动制造缺陷

### 验证
- 错误堆栈已明确落在 `refiner.render_fixed_rgb_batch -> _load_render_sample -> dataset[idx]`
- 下一轮将使用保守索引窗口重新运行, 不再复现这个越界条件
