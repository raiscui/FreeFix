## [2026-03-27 01:32:19] [Session ID: 20260327T012145Z-main] 主题: 如果要二次 refine, 先压缩 prompt 避免 `CLIP` 截断

### 暂缓原因
- 这次主目标已经完成:
  - 本地 `FLUX` 路径接通
  - `my4` refine 已完整跑完
- 当前 warning 不是 fatal error
- 在没有先重写 prompt 前直接重跑, 很可能只是重复消耗时间和算力

### 后续建议
- 下次若要继续提升“体积光 / God rays / 光束 / 镜头光晕 / high detail”这些风格词的命中率:
  - 先把 prompt 压到 `CLIP` 可接受长度
  - 优先保留最关键的 4-6 个语义锚点
  - 再决定是否重跑 refine

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`
  - 本次日志里出现的 `CLIP can only handle sequences up to 77 tokens` warning

## [2026-03-27 09:39:13] [Session ID: 429732-430781] 主题: 若要真正提升 `my4` 画质, 先做 reconstruction 对照实验而不是继续堆 refine

### 暂缓原因
- 本轮用户主要是在问“为什么 reconstruction 感觉质量不高, 怎么提高”
- 已经完成诊断, 但还没有进入新的长时间训练任务
- 真正最值钱的下一步是做对照实验, 这会消耗显存、时间和新的输出目录

### 后续建议
- 优先顺序建议:
  - 先做一轮“快速增强配置”对照训练
  - 如果提升明显, 再做“重建更高质量 COLMAP + 画质优先训练”
- 快速增强配置建议重点:
  - `max_steps` 提到 `50000`
  - `refine_stop_iter` 提到 `30000`
  - 打开 `pose_opt=true`
  - 打开 `app_opt=true`
  - 打开 `depth_loss=true`
- 如果快速配置仍提升有限, 下一步再回到源数据侧:
  - 用系统 `CUDA COLMAP` 重建更干净的 `sparse`
  - 清理模糊帧、重复帧、严重曝光漂移帧

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/cmd.md`

## [2026-03-27 03:20:26] [Session ID: 20260327T032026Z-main] 主题: 用 `data/my4_fullcolmap` 做画质对照训练

### 暂缓原因
- 这轮主目标是把 full COLMAP 数据目录真正修到“可训练”
- 该目标已经完成:
  - `264` 图 undistort 正常
  - `partition.json` 已生成
  - `1 step` 训练已通过
- 但完整重训和评测会继续消耗较长时间与显存

### 后续建议
- 下一轮最值钱的动作:
  - 用 `data/my4_fullcolmap` 跑一轮和 `outputs/my4` 同口径的训练
  - 再和原 `data/my4` 的结果做 `PSNR / SSIM / LPIPS` 对照
- 建议优先级:
  - 先做 `max_steps=30000` 或 `50000` 的对照训练
  - 若提升明显, 再考虑继续叠加 `pose_opt / app_opt / depth_loss`

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/data/my4_fullcolmap/partition.json`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/cmd.md`

## [2026-03-27 04:22:05] [Session ID: 20260327T041915Z-main] 主题: 当前增强训练完成后, 补手动评测或恢复自动 eval

### 暂缓原因
- 本轮重点是先把“更优参数 + 更干净数据”的长训练真正跑起来
- 这一步已经完成
- 但训练器当前的自动 eval 代码仍处于注释态, 所以不会自动生成 `eval/*.json`

### 后续建议
- 长训练跑到关键 checkpoint 后, 二选一:
  - 方案A: 写一条手动评测 checkpoint 的命令, 直接产出 `PSNR / SSIM / LPIPS`
  - 方案B: 恢复 `trainer` 的自动 eval 路径, 让后续所有训练都自动落评测文件
- 如果只想尽快看这轮增强参数有没有价值:
  - 优先对 `ckpt_999.pt` 或后续 `ckpt_9999.pt` 做一次手动评测

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/trainer.py`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality/ckpts/`
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`

## [2026-03-27 04:43:28] [Session ID: 20260327T041915Z-main] 主题: 在 `my4_fullcolmap_quality` 上做 checkpoint 选择而不是只看最终步数

### 暂缓原因
- 本轮已经完成:
  - `9999` 手动评测
  - `49999` 手动评测
  - 图片导出
- 并且已经拿到一个新的动态结论:
  - `9999` 的 test 指标优于 `49999`

### 后续建议
- 下一轮更值得做的不是继续无脑加步数
- 而是沿 checkpoint 维度做选择:
  - 优先比较 `9999`
  - 再补 `29999`
  - 视情况比较 `49999`
- 如果 `29999` 也不如 `9999`, 下轮应优先考虑:
  - 提前保存和 early stop
  - 收紧 densify 窗口
  - 重新平衡 `depth_loss` 或 appearance 优化强度

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality/ckpts/`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_9999/`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_49999/`

## [2026-03-27 04:55:05] [Session ID: 20260327T045120Z-main] 主题: 三档对照已确认 `9999` 最优, 下一轮应围绕 early stop 与更细 checkpoint 保存展开

### 暂缓原因
- 本轮已经完成三档真实评测:
  - `9999`
  - `29999`
  - `49999`
- 当前证据已经足够支持阶段性结论, 不必立刻再开一轮长训练

### 后续建议
- 优先顺序建议:
  - 下轮先把保存频率加密, 捕捉 `9999` 附近更细的 checkpoint
  - 同时考虑把默认交付 checkpoint 从“最终步”改成“最佳验证指标步”
- 如果继续改训练策略:
  - 优先考虑更早 early stop
  - 或收紧 densify 窗口, 避免后半程继续膨胀到 `373083` 个 GS 后 test 指标反而回落

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_29999/stats/val_step29999.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_compare/summary_compare_3way_web.jpg`
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`

## [2026-03-27 06:55:58] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 主题: 若继续优化 `app_opt=false` 线, 下一轮优先把扫描窗口延到 `12000` 之后

### 暂缓原因
- 本轮已经完成 `8999/9999/10999/11999` 四档真实评测
- 证据已经足够支持当前阶段结论:
  - `11999` 是这次扫描区间内的统一最优点
- 但继续往后训练和评测还会继续消耗时间与显存

### 后续建议
- 下一轮优先顺序建议:
  - 方案A: 保持 `app_opt=false` 与现有训练窗口逻辑不变, 把 `max_steps` 延到 `14000` 或 `16000`
  - 方案B: 在 `12000` 后继续加密保存, 例如 `12000/13000/14000/16000`
  - 方案C: 如果想确认稳定性, 对当前配置再重复跑 `2-3` 次, 看 best checkpoint 是否稳定停在末段
- 当前不推荐直接回头做:
  - “更早 early stop” 作为默认下一步
  - 再次打开 `app_opt=true`

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_dense_eval_compare/summary_4way.json`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_dense_eval_11999/stats/val_step11999.json`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_stable_12k_dense.yaml`

## [2026-03-27 08:30:49] [Session ID: 20260327T074108Z-main] 主题: `my4_fullcolmap_v2` 已证明保守清洗有效, 下一轮优先做更激进的 train-only blur 清洗

### 暂缓原因
- 本轮已经完整完成:
  - 审计
  - `v2` 生成
  - COLMAP 重建
  - `stable_12k_dense` 训练
  - 四档真实评测
- 当前已经有足够证据说明:
  - 保 test 不动
  - 只清 train blur outlier
  的确能推高 PSNR

### 后续建议
- 下一轮优先顺序建议:
  - 方案A: 继续沿 train-only 清洗, 追加第二梯队 blur 候选, 生成 `my4_fullcolmap_v3`
  - 方案B: 如果要兼顾 LPIPS, 在 `v2` 或 `v3` 上尝试新的 appearance / rendering 调节, 不要只继续删图
- 当前建议优先纳入 `v3` 复核池的候选:
  - `000125.png`
  - `000412.png`
  - `000369.png`
  - `000248.png`
  - `000330.png`
  - `000371.png`
  - `000043.png`

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense_eval_compare/summary_4way.json`
  - `/root/autodl-tmp/home/rais/FreeFix/data/my4_fullcolmap/meta/frame_audit_recommended_drop_v1.md`
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`

## [2026-03-27 09:31:56] [Session ID: 20260327T091216Z-main] 主题: 如果要继续这条 `v2 refine` 线, 下一步优先做“对照观看”或“量化评测”, 不要立刻再改 prompt

### 暂缓原因
- 本轮已经完成:
  - `v2 best` 的独立 Flux refine
  - prompt 截断修复
  - `before / after / gen` 三套视频与逐帧图落盘
- 当前最缺的不是“再来一个 prompt”
- 而是把这次结果和 `before refine` 真正做对照

### 后续建议
- 优先顺序建议:
  - 方案A: 抽 `3-5` 个代表帧做并排对照图, 快速看结构保持和光效命中率
  - 方案B: 如果要量化, 用 `ours.evaluation` 对 `ckpt_flux_shinkai_museum_v2.pt` 跑一次 train/test 指标
- 当前不建议:
  - 立刻继续写第三版 prompt 再重跑
  - 因为现在最大不确定点已经从“prompt 是否截断”切换成“观感到底值不值”

### 继续入口
- 继续前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/before_refine.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/after_refine.mp4`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`
