## [2026-04-01 11:16:55] [Session ID: session-20260401T110504Z-113863] 任务名称: 实现可选 `FLUX.1-Kontext-dev` refine backend

### 任务内容
- 新增 `kontext` refine backend, 与现有 `flux` / `sdxl` 并列存在
- 为 wrapper、独立 CLI、配置注释、README 和测试补齐 `kontext` 语义
- 保持现有 refine 的 resume / output / synthetic supervision 契约不变

### 完成过程
- 先读取 OpenSpec change、历史 `flux_kontext` 支线和当前代码, 确认 `flux/sdxl` 主循环高度同构
- 抽取:
  - `ours/refine_backend_common.py`
  - `ours/refine_backend_runner.py`
  让三条 backend 共用 CLI、路径覆盖、阶段日志和主循环
- 重写 `ours/refine_by_flux.py` 与 `ours/refine_by_sdxl.py`, 改为挂到共用 runner 上
- 新建 `ours/refine_by_kontext.py`:
  - 独立 `kontext_model_path`
  - `FluxKontextPipeline`
  - `FluxKontextInpaintPipeline`
  - source real image -> `image_reference`
  - union mask / no-mask fallback
- 更新:
  - `ours/run_fastgs_refine.py`
  - `exp_cfg/base.yaml`
  - `README.md`
  - `tests/test_run_fastgs_refine.py`
  - `tests/test_refine_cli_paths.py`
  - `tests/test_pose_jitter_refine.py`
  - `tests/test_kontext_refine.py`
  - `openspec/.../tasks.md`
- 做了动态验证:
  - 33 个相关单测通过
  - `--help` 正常
  - `--dry-run --refine-backend kontext` 已实际路由到 `ours.refine_by_kontext`

### 总结感悟
- 这次最值钱的不是单独加了 `kontext`, 而是把 refine backend 扩展路径整理成了可持续复用的形状
- 官方 Kontext 的 `image_reference` 明确站在 inpaint 路径上, 所以“有参考图但没有兼容 mask”时, 明确 fallback 比伪装成完全等价更稳

## [2026-04-01 14:56:49] [Session ID: omx-1775055181169-iytve2] 任务名称: 核对 `kontext_model` 的图文输入与多图输入边界

### 任务内容
- 读取当前 `kontext` backend 实现、README 与测试
- 用本地 `diffusers` 动态签名和 Context7 官方文档确认 API 边界
- 区分“当前项目已支持”与“上游理论可扩展”两层语义

### 完成过程
- 确认 `ours/refine_by_kontext.py` 当前只传:
  - `image`
  - `prompt`
  - 可选单个 `image_reference`
- 确认测试只覆盖单参考图路径, 没有 4 参考图工作流
- 确认官方文档里多参考图示例依赖 community custom pipeline, 不是当前 FreeFix 在用的标准调用路径

### 总结感悟
- “函数签名接受 list” 不等于 “当前项目已经支持单样本 4 图语义”
- 回答这类问题时, 必须把:
  - 当前仓库实现
  - 上游 API 类型
  - 官方示例工作流
  三层证据拆开讲, 才不会误导用户

## [2026-04-01 15:25:20] [Session ID: omx-1775055181169-iytve2] 任务名称: 收敛单参考图 Kontext 工作流到“jitter 主图 + 原素材参考图”

### 任务内容
- 把 Kontext 的 reference image 语义收紧到 `pose_jitter` 主循环
- 为 Kontext 增加专用 prompt builder, 明确“修瑕疵 + 保持主图视角/结构 + 参考原素材外观”
- 补测试、配置注释与 README 说明

### 完成过程
- 先确认 `source_split/source_index` 已经从 `pose_jitter` plan 传到 `cam_param`, 且可回取原 dataset item
- 在 `ours/refine_by_kontext.py` 中新增:
  - `build_kontext_prompt(...)`
  - `pose_jitter` 专属 reference sample 选择逻辑
- 在 `exp_cfg/base.yaml` 中补 `kontext_prompt` 注释
- 在 `exp_cfg/my5/...yaml` 中补更保守的 `kontext_prompt`
- 在 `README.md` 中同步记录 Kontext 现在的单参考图工作流
- 通过单测、CLI 与最小运行时打印验证最终语义

### 总结感悟
- 当前问题的本质不是“reference 图没接上”, 而是“Kontext 没有被明确告知该如何使用主图和参考图”
- 对多模态编辑模型来说, prompt 不是装饰, 而是 workflow 契约的一部分

## [2026-04-01 15:45:30] [Session ID: omx-1775055181169-iytve2] 任务名称: 修正 Kontext prompt 中 `same viewpoint` 的歧义

### 任务内容
- 收紧 Kontext 默认 prompt 的对象指代
- 避免把“当前主图视角”误说成“主图与参考图同视角”
- 重新验证 helper 测试与最终 prompt 文本

### 完成过程
- 将 `same camera viewpoint` 改成:
  - 保持 `current input render` 的 viewpoint / composition / perspective / structure
- 将 reference 说明改成:
  - 可能来自 `nearby original training camera`
  - 仅作 appearance guidance
  - 不复制其 viewpoint / geometry / composition
- 同步更新 `my5` 的 `kontext_prompt` 与 README 文案
- 运行 `tests.test_kontext_refine` 通过, 并打印最终 prompt 做动态确认

### 总结感悟
- 对多图条件 prompt, “相对表述”很容易埋歧义
- 更稳的做法是始终把动作对象说全:
  - 保谁的视角
  - 借谁的外观
  - 明确禁止复制谁的几何/构图

## [2026-04-01 15:59:10] [Session ID: omx-1775055181169-iytve2] 任务名称: 完成 3 图 Kontext 真实预览并导出三联图

### 任务内容
- 基于当前 `my5` Kontext 配置跑 3 张真实 preview 图
- 保持真实生成参数, 只把 synthetic plan 压缩到 3 条
- 导出 render / reference / gen 三联对照图

### 完成过程
- 生成 `/tmp/freefix_my5_kontext_preview_20260401T154956Z.yaml`
- 用 `ours.refine_by_kontext` 跑完 3 条 synthetic plan
- 导出到:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_20260401T154956Z`
- 额外整理出:
  - `preview/reference/*.jpg`
  - `preview/triptych/*.jpg`
  - `preview/summary.json`
- 顺手做了基础像素差统计, 证明当前 gen 更贴近主图 render, 没有明显塌成 reference copy

### 总结感悟
- 当前单参考图工作流已经能稳定产出 preview 图
- 但 prompt 太长被 CLIP 截断, 是下一轮最值得优先处理的问题

## [2026-04-01 16:12:20] [Session ID: omx-1775055181169-iytve2] 任务名称: 完成第二轮更克制 prompt 的 3 图 preview

### 任务内容
- 缩短 Kontext 正向 prompt
- 新增 `kontext_negative_prompt` 抑制额外细节、乱纹理与过锐化
- 重新跑 3 图真实 preview 并导出新的三联图

### 完成过程
- 在 `ours/refine_by_kontext.py` 中改短默认 repair/reference prompt
- 新增 `resolve_kontext_negative_prompt(...)`
- 在 `exp_cfg/my5/...yaml` 中设置:
  - `kontext_prompt: Minimal cleanup of the current render. Keep it clean, soft, and stable.`
  - `kontext_negative_prompt: extra details, busy texture, oversharpening, added reflections, added patterns, clutter, text, noise`
- 第二轮 preview 输出到:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_clean_20260401T160434Z`
- 已导出新的 reference 图与 triptych 对照图
- 运行中确认不再出现 CLIP prompt 截断

### 总结感悟
- 对 Kontext 这类编辑模型, “更短、更具体、更克制”的 prompt 往往比“更完整、更解释型”的 prompt 更有效
- 把 negative prompt 从“反模糊增强”改成“禁止额外细节”后, 结果更容易往干净方向收敛

## [2026-04-02 00:23:40] [Session ID: omx-1775055181169-iytve2] 任务名称: 完成第五轮超短版 silky/clean prompt preview

### 任务内容
- 将 Kontext prompt 收敛成超短版:
  - `Clean silky polish. Delicate, soft, natural.`
- 保留更针对“脏 / 粗糙 / 过锐化”的 negative prompt
- 跑第五轮 3 图 preview 并导出三联图

### 完成过程
- 缩短 `ours/refine_by_kontext.py` 默认 repair/reference clause
- 更新 `my5` 配置为超短 prompt + 聚焦 negative prompt
- 第五轮 preview 输出到:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_ultrashort_20260401T161837Z`
- 已确认本轮运行不再触发 CLIP 77 token 截断
- 已导出新的 reference 与 triptych 对照图

### 总结感悟
- 对这个场景, “更短但更准”的 prompt 比“更完整更优美”的 prompt 更有效
- 只要再次触发截断, 前面再漂亮的审美词都不可靠; 先保证约束完整送达模型, 再谈风格微调

## [2026-04-02 00:46:20] [Session ID: omx-1775055181169-iytve2] 任务名称: 完成“更猛 jitter + 更柔和少浮尘 prompt” preview

### 任务内容
- 在保持超短 prompt 稳定不截断的前提下
- 提高 jitter 强度, 让 render 真正出现明显缺陷
- 同时把 prompt 收紧到“更柔和、更干净、少浮尘”方向

### 完成过程
- `my5` 配置里的 Kontext 提示词更新为:
  - `kontext_prompt: Soft clean polish. Gentle, airy, smooth.`
  - `kontext_negative_prompt: airborne dust, floating particles, dirty speckles, dirty spots, grain, grime, gritty, rough, harsh, crunchy, oversharpened, overprocessed, busy texture, clutter, reflections, patterns, text, noise`
- preview 使用更猛 jitter 配置运行:
  - 平移 sigma 1.2
  - 旋转 sigma 6.0
  - 关闭邻居半径约束
  - 降低 coverage 门槛
- 产出目录:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_ultrashort_jitterhard_softclean_20260401T172600Z`
- 已导出 reference 图与 triptych 对照图

### 总结感悟
- 只有当 render 真正坏得明显时, 才能有意义地评价“修复后是否柔和、干净、少浮尘”
- 本轮是当前最有判别力的一轮: 样本够坏, prompt 也够稳

## [2026-04-02 01:12:10] [Session ID: omx-1775055181169-iytve2] 任务名称: 跑完用户指定强训练参数并确认 before/after 更可见

### 任务内容
- 按用户指定参数运行强化版 preview:
  - `refine_steps = 400`
  - `synthetic plan = 10`
  - `gen_prob = 0.2`
  - `kontext_strength = 0.55`
- 验证 `before_refine / after_refine` 是否比轻 preview 更明显

### 完成过程
- 生成并运行:
  - `/tmp/freefix_my5_kontext_preview_strongtrain_20260401T174137Z.yaml`
- 输出目录:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_strongtrain_20260401T174137Z`
- 导出:
  - synthetic `render/reference/gen` triptych
  - fixed-view `before/after/diff` triptych
- 统计确认:
  - 当前强训练版的 `before/after` 差异明显高于旧轻 preview

### 总结感悟
- 当 `refine_steps`、synthetic plan 数量和 `gen_prob` 同时提升后, `before/after` 才开始变得更容易被肉眼看到
- 但如果目标仍是“柔和、干净的局部整理”, 那 before/after 依然更像局部变化, 不会自然长成全图大改写

## [2026-04-02 01:46:20] [Session ID: omx-1775055181169-iytve2] 任务名称: 完成 `strongtrain_refcolor` 对照运行

### 任务内容
- 在 `kontext_strength = 0.55` 不变前提下
- 继续把 prompt 往“更干净、无尘、参考 ref 图亮度颜色”方向微调
- 与上一轮 `strongtrain_softfinish` 做对照

### 完成过程
- 生成并运行:
  - `/tmp/freefix_my5_kontext_preview_strongtrain_refcolor_20260401T181818Z.yaml`
- 输出目录:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_strongtrain_refcolor_20260401T181818Z`
- 确认:
  - prompt 未截断
  - before/after 差异仍存在
  - 与上一轮相比, 结果继续往更收、更柔方向移动

### 总结感悟
- 当 `strength` 固定时, prompt 仍然足以细调“空气感 / 尘点感 / 柔和度”
- 但 prompt 往“更柔、更净”推, 通常也会把整体变化幅度一起压小一点
