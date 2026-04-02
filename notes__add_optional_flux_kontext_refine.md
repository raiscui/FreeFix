## [2026-04-01 11:06:15] [Session ID: session-20260401T110504Z-113863] 笔记: OpenSpec 变更上下文与已锁定边界

## 来源

### 来源1: `openspec status --change "add-optional-flux-kontext-refine" --json`

- 位置: 仓库根目录终端命令
- 要点:
  - schema 为 `spec-driven`
  - artifacts 已全部完成
  - 当前 apply 入口可直接执行

### 来源2: `openspec instructions apply --change "add-optional-flux-kontext-refine" --json`

- 位置: 仓库根目录终端命令
- 要点:
  - 当前进度 `0/11`
  - 上下文文件包括:
    - `proposal.md`
    - `design.md`
    - `spec.md`
    - `tasks.md`
  - 需要逐项完成任务并回写勾选

### 来源3: `openspec/changes/add-optional-flux-kontext-refine/{proposal,design,specs,tasks}`

- 位置: 仓库内 change 文件
- 要点:
  - `kontext` 是新增第三种 refine backend
  - 默认 backend 仍保持 `flux`
  - `kontext_model_path` 必须与 `flux_model_path` 独立
  - `ours/refine_by_kontext.py` 要复用现有 refine runtime contract
  - source real image 在可用时要作为独立参考输入
  - 当前 render 图必须保持主编辑输入语义

### 来源4: `archive/branch_contexts/flux_kontext_change/*`

- 位置: 历史支线归档
- 要点:
  - 旧支线已经把这次 change 的产品口径锁定为“optional backend”
  - 首版优先走官方 `FluxKontextPipeline` / `FluxKontextInpaintPipeline`
  - 首版允许与现有私有 `warp/mask_scheduler` 语义存在文档化差异

## 综合发现

### 已验证事实

- 当前 OpenSpec change 已经 apply-ready, 不是缺 artifact 的阻塞状态。
- 任务拆分覆盖了:
  - wrapper/backend 接线
  - Kontext refine 实现
  - 测试验证
  - 文档补充

### 当前主假设

- 仓库已经有足够多的 `flux` / `sdxl` 复用结构。
- 本次实现更像是沿着现有模式增开第三条 backend, 而不是重写整个 refine 系统。

### 备选解释

- 如果当前 `flux` 路径把太多私有逻辑直接写死在脚本里, 可能需要先抽一点公共辅助函数, 否则 `kontext` 会难以接入。

### 推翻主假设需要的证据

- 读完 `ours/refine_by_flux.py` 和 `ours/run_fastgs_refine.py` 后发现:
  - resume / output / wrapper 契约大量耦合在 Flux 专属对象上
  - 或 source real image / mask 语义没有可复用入口

## [2026-04-01 11:16:55] [Session ID: session-20260401T110504Z-113863] 笔记: 实现结构与动态验证结果

## 来源

### 来源1: 当前代码实现

- 位置:
  - `ours/refine_backend_common.py`
  - `ours/refine_backend_runner.py`
  - `ours/refine_by_flux.py`
  - `ours/refine_by_sdxl.py`
  - `ours/refine_by_kontext.py`
- 要点:
  - `flux/sdxl` 的公共运行时已被抽到共用 runner
  - `kontext` 沿用同一套 resume / output / synthetic supervision 契约
  - `kontext` 的模型来源独立于 `flux_model_path`
  - `FluxKontextInpaintPipeline` 通过 `edit_pipe.components` 共享组件构建, 避免重复加载整套权重

### 来源2: 官方文档与动态签名验证

- 位置:
  - Context7 `/huggingface/diffusers`
  - `direnv exec . python3 -c \"import inspect; ...\"`
- 要点:
  - `FluxKontextPipeline` 适合普通编辑
  - `FluxKontextInpaintPipeline` 明确支持 `mask_image` 与 `image_reference`
  - 当前环境里的 `diffusers` 已暴露这两个类和对应签名

### 来源3: 本轮验证命令

- 位置: 仓库根目录终端命令
- 要点:
  - `python3 -m unittest ...` 33 tests 通过
  - `python3 ours/run_fastgs_refine.py --help` 正常展示 `kontext`
  - `python3 -m ours.refine_by_kontext --help` 正常返回
  - wrapper `--dry-run --refine-backend kontext` 已实际拼出 `ours.refine_by_kontext`

## 综合发现

### 已验证结论

- 主假设成立:
  - 当前仓库确实已经具备足够清晰的 backend 扩展骨架
  - 不需要重写整个 refine 系统
- `kontext` 已经作为独立可选 backend 接入:
  - wrapper 层
  - 独立 CLI
  - 测试层
  - README / 配置注释
- v1 的保守映射方式是:
  - render 图始终作为主编辑输入
  - 多掩码折叠成 union mask
  - source real image 可用时, 只在 inpaint 路径下作为 `image_reference`
  - 无兼容 mask 时退回普通 edit pipeline

## [2026-04-01 14:06:21] [Session ID: session-20260401T110504Z-113863] 笔记: `my5` Kontext 重跑前的现象与执行决策

## 来源

### 来源1: `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v2.yaml`

- 位置: 仓库配置文件
- 要点:
  - 当前配置已经带:
    - `kontext_model_path`
    - `kontext_strength: 0.65`
    - `refine_steps: 400`
  - 但 `exp_name` 仍写成:
    - `flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`

### 来源2: 目标输出目录检查

- 位置: `outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_test_x3_20260330`
- 要点:
  - 已存在:
    - `before_refine.mp4`
    - `after_refine.mp4`
    - `refine/generated_cams.jsonl`
    - `refine_resume_state.json`
    - `eval/*.json`

### 来源3: `refine_resume_state.json`

- 位置: 目标输出目录
- 要点:
  - `status = complete`
  - `plan_total = 566`
  - `next_plan_index = 566`
  - `final_ckpt_path` 已存在

### 来源4: 现有评估结果

- 位置: 目标输出目录下 `eval/*.json`
- 要点:
  - 基础模型:
    - test: `psnr 27.1882`, `ssim 0.8907`, `lpips 0.2037`
    - train: `psnr 27.3025`, `ssim 0.8928`, `lpips 0.2025`
  - 已完成 refined:
    - test: `psnr 27.5590`, `ssim 0.8939`, `lpips 0.1960`
    - train: `psnr 27.7455`, `ssim 0.8964`, `lpips 0.1943`

## 综合发现

### 已验证事实

- 直接使用当前 `exp_name` 原地重跑, 高概率不会进入真实计算, 而是被恢复逻辑短路。

### 当前执行决策

- 为了满足“重新跑下”而不是“读旧结果”, 本轮改用运行时配置副本。
- 只改 `exp_name`, 保留原配置参数口径不变。

## [2026-04-01 14:13:37] [Session ID: session-20260401T141047Z-kontext-eval] 笔记: 运行中实验的动态证据与当前结论

## 来源

### 来源1: 运行中 PTY 会话 `32179`

- 位置: 仓库根目录后台运行命令
- 要点:
  - 命令仍在运行:
    - `timeout 6h direnv exec . python3 -m ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_rerun_20260401T140621Z.yaml`
  - 动态输出持续出现:
    - `33/33` 图像生成进度
    - `400/400` refine 优化进度
  - 运行没有提前退出, 也没有出现新的 error

### 来源2: 新实验目录落盘状态

- 位置:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_shinkai_museum_v2_pose_jitter_train_v2_20260401T140621Z`
- 要点:
  - 已存在:
    - `before_refine.mp4`
    - `refine/generated_cams.jsonl`
    - `refine/pose_jitter_log.jsonl`
    - `refine_resume_state.json`
  - `generated_cams.jsonl` 当前行为 `10`
  - `pose_jitter_log.jsonl` 当前行为 `11`
  - 最新 `pose_jitter_log` 已写到:
    - `plan_index = 10`

### 来源3: `refine_resume_state.json`

- 位置: 新实验目录根部
- 要点:
  - `status = synthetic_in_progress`
  - `plan_total = 283`
  - `latest_completed_plan_index = -1`
  - `next_plan_index = 0`
  - `updated_at_utc = 2026-04-01T14:07:59.029778+00:00`

## 综合发现

### 已观察到的现象

- 真实 `kontext` rerun 已经启动并持续推进。
- synthetic 相关日志正在增长。
- 但 `refine_resume_state.json` 目前还没有刷新成“已完成若干 plan”的状态。

### 当前主假设

- 当前实现的进度真相源不能只看 `refine_resume_state.json`。
- 在 synthetic 过程中, `pose_jitter_log.jsonl` 的增长更能证明主循环仍在推进。

### 最强备选解释

- 也可能不是“状态文件延迟写入”, 而是当前执行路径只会在某个更晚的阶段统一刷新 `next_plan_index`。

### 当前结论

- 这轮 rerun 不是空跑, 也不是被旧目录 resume 短路。
- 但截至当前时刻, refine 仍未完成, 还不能启动最终 evaluation。

## [2026-04-01 14:19:09] [Session ID: session-20260401T141047Z-kontext-eval] 笔记: 用户改参后的新 rerun 启动证据

## 来源

### 来源1: 用户修改后的主配置

- 位置:
  - `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v2.yaml`
- 要点:
  - 主配置内容已发生调整
  - 但 `exp_name` 仍保留旧实验名
  - 因此本轮继续采用运行时配置副本策略

### 来源2: 新的运行时配置副本

- 位置:
  - `/tmp/freefix_my5_kontext_rerun_20260401T141823Z.yaml`
- 要点:
  - 仅重写:
    - `exp_name: kontext_shinkai_museum_v2_pose_jitter_train_v2_20260401T141823Z`
  - 其余参数保持用户刚修改后的口径

### 来源3: 新运行会话 `15870`

- 位置: 仓库根目录后台运行命令
- 要点:
  - 实际命令:
    - `timeout 6h direnv exec . env OMP_NUM_THREADS=1 python3 -m ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_rerun_20260401T141823Z.yaml`
  - 已通过的启动阶段:
    - `Refiner` 初始化
    - Kontext edit pipeline 加载
    - `pipe.to(cuda)`
    - inpaint pipeline 构建
    - 输出目录创建
    - `before_refine` 导出开始

## 综合发现

### 已验证事实

- 本轮新的 rerun 已成功起跑。
- 当前新实验目录是:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_shinkai_museum_v2_pose_jitter_train_v2_20260401T141823Z`
- 运行日志明确显示:
  - `real train pool count = 283`
  - `synthetic plan repeats_per_source = 1`
  - `synthetic plan count = 283`

### 额外提醒

- 主配置顶部注释仍写着“每个基镜头当前抖出 2 个视角”, 但当前实际运行参数是:
  - `pose_jitter_views_per_source: 1`
- 这说明注释和真实参数目前不一致。

## [2026-04-01 14:56:49] [Session ID: omx-1775055181169-iytve2] 笔记: `kontext_model` 图文输入与多图输入边界核对

## 来源

### 来源1: 当前项目实现 `ours/refine_by_kontext.py`

- 位置:
  - `ours/refine_by_kontext.py:113-145`
- 要点:
  - 当前请求参数固定包含:
    - `prompt`
    - `image`
  - 有兼容 mask 时, 才会进入 inpaint 路径并追加:
    - `mask_image`
    - `image_reference`
  - 代码里字段名是单数 `image_reference`, 不是 `image_references`
  - 当前 `source_reference_sample` 也只解析单个 dataset item, 没有多参考图聚合逻辑

### 来源2: 当前项目测试 `tests/test_kontext_refine.py`

- 位置:
  - `tests/test_kontext_refine.py:48-73`
- 要点:
  - 测试显式断言 inpaint 请求里包含单个 `image_reference`
  - 没有任何测试覆盖“4 张参考图同时输入”的项目语义

### 来源3: README

- 位置:
  - `README.md:183`
- 要点:
  - 文档写明:
    - 当前 render 图始终是主编辑输入
    - source real image 只在有兼容 mask 时作为 `image_reference`

### 来源4: 本地动态签名验证

- 位置:
  - `direnv exec . python3` + `inspect.signature(...)`
- 要点:
  - `FluxKontextPipeline.__call__(image, prompt, ...)`
  - `FluxKontextInpaintPipeline.__call__(image, image_reference, mask_image, prompt, ...)`
  - 已安装 `diffusers` 的类型签名里, `image` 和 `image_reference` 都接受:
    - 单张图
    - `list[...]`
  - 但这条证据本身只能证明 API 接受列表对象, 不能单独证明“单个样本语义下可融合 4 张参考图”

### 来源5: Context7 `/huggingface/diffusers`

- 位置:
  - `docs/source/en/api/pipelines/flux.md`
  - `examples/community/README.md`
- 要点:
  - 官方 API 文档明确 `FluxKontextPipeline` 是 text + image 编辑
  - `FluxKontextInpaintPipeline` 是 text + image + mask, 可选 `image_reference`
  - 文档里真正展示“multiple references”的是 community custom pipeline:
    - `custom_pipeline="pipeline_flux_kontext_multiple_images"`
    - 调用参数是 `multiple_images=[(...)]`
  - 这说明“多参考图单样本语义”不是当前项目在用的标准调用路径

## 综合发现

### 已验证事实

- 当前 FreeFix 仓库的 `kontext` 接入, 确实支持图文输入:
  - 主编辑输入是 `image`
  - 指令输入是 `prompt`
- 当前 FreeFix 仓库只实现了:
  - 1 张主编辑图
  - 0 或 1 张 `image_reference`
- 当前 FreeFix 仓库没有实现:
  - 4 张参考图同时参与同一条 edit/inpaint 请求的项目语义

### 当前主结论

- 如果用户说的“4 张图片输入”是“单个样本同时喂 4 张参考图”, 当前项目答案是否定的。
- 如果用户说的是“API 参数能不能传 list”, 上游 `diffusers` 签名层面是可以接受列表对象的, 但这更像 batch / 扩展入口, 不是当前 FreeFix 已实现并验证的 4-reference 工作流。

### 最强备选解释

- 后续也许可以基于 community `pipeline_flux_kontext_multiple_images` 做多参考图扩展。
- 但那会是新能力接入, 不是当前仓库现成能力。

## [2026-04-01 15:18:30] [Session ID: omx-1775055181169-iytve2] 笔记: 单参考图 Kontext 收敛前的静态证据与改动方向

## 来源

### 来源1: `ours/refine_run_schedule.py` + `recon/refiner.py`

- 要点:
  - `pose_jitter` synthetic plan 由 `source_split/source_index` 展开
  - `Refiner.render(..., camera_spec=plan_entry)` 会把:
    - `source_split`
    - `source_index`
    - `source_image_name`
    - `camera_mode`
    写进 `cam_param`

### 来源2: `ours/refine_by_kontext.py`

- 要点:
  - 当前参考图读取是:
    - `refiner.get_dataset_item(int(source_index), split=str(source_split))`
  - 当前 prompt 来源是:
    - 直接使用 `cfg.prompt`

### 来源3: `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v2.yaml`

- 要点:
  - 当前 prompt 偏“泛化图像增强 / 错误修复”
  - 但没有明确约束:
    - 保持主图当前视角
    - 只把原素材图作为 appearance reference

## 现象 -> 假设 -> 验证计划 -> 当前结论

### 现象

- 当前 `kontext` 已经能拿到 `pose_jitter` 对应的原相机位训练图。
- 当前 `kontext` 还没有把“修复主图瑕疵, 参考原素材细节, 但不要改视角/构图”的意图显式写进 prompt。

### 当前主假设

- 主要问题不在 reference 图来源, 而在 prompt 语义过宽。
- 只要补一个 Kontext 专用 prompt builder, 并把 reference 使用场景显式锁到 `pose_jitter`, 就更符合用户想要的工作流。

### 最强备选解释

- 如果后续验证发现 fixed 模式也需要 reference image, 那说明“reference 只给 pose_jitter”过于保守。

### 验证计划

- 改完后补单测验证:
  - `pose_jitter` 下 reference sample 会返回原 dataset item
  - 非 `pose_jitter` 下 reference sample 不会误启用
  - prompt 在有 / 无 reference 时能正确拼装

### 当前结论

- 当前最合适的实现方向是:
  - 保持 jitter render 作为主图
  - 保持原相机位训练图作为 `pose_jitter` 单参考图
  - 新增 Kontext 专用 prompt builder 和配置覆盖点

## [2026-04-01 15:45:30] [Session ID: omx-1775055181169-iytve2] 笔记: `same viewpoint` 歧义已收紧为“保持当前主图视角”

## 来源

### 来源1: 用户反馈

- 要点:
  - `same viewpoint` 容易让人误读成“主图和参考图同视角”
  - 但当前工作流里:
    - 主图是 jitter render
    - 参考图是原相机位训练图
    - 两者并非同一视角

### 来源2: 更新后的 Kontext 默认 prompt

- 位置:
  - `ours/refine_by_kontext.py`
- 要点:
  - 已去掉 `same viewpoint`
  - 改为:
    - 保持 `current input render` 的 viewpoint / composition / perspective / structure
    - reference image 可能来自 `nearby original training camera`
    - reference 只作 `appearance guidance`

### 来源3: 动态验证

- 命令:
  - `direnv exec . python3 -m unittest tests.test_kontext_refine`
  - `direnv exec . python3 - <<'PY' ... build_kontext_prompt(...) ... PY`
- 要点:
  - 9 个 Kontext helper 单测通过
  - 最终 prompt 文本已明确区分:
    - 当前主图视角
    - 参考图外观指导

## 当前结论

- 用户指出的问题成立。
- 这不是推理链路 bug, 而是 prompt 契约的歧义风险。
- 现在文案已经更精确:
  - 保主图视角
  - 借参考图外观
  - 不再暗示两张图本来同视角

## [2026-04-01 15:56:10] [Session ID: omx-1775055181169-iytve2] 笔记: 预览三联图导出脚本首轮失败的原因

## 现象

- 运行 preview 导出脚本时, `PIL.Image.fromarray(...)` 报:
  - `TypeError: Cannot handle this data type: (1, 1, 3), <f4`

## 判断

- `Dataset` 返回的 `image` 在当前实现里是 float32, 不是可直接喂给 PIL 的 uint8
- 这是补充导出脚本的类型归一化缺失, 不是 Kontext 主流程错误

## 修正

- 导出 reference 图时先做:
  - 若是浮点图, 判断是否在 0..1 范围内
  - 再缩放 / clip / 转 uint8

## [2026-04-01 15:59:10] [Session ID: omx-1775055181169-iytve2] 笔记: 3 图 Kontext preview 的动态证据与产物路径

## 来源

### 来源1: 真实 preview 运行

- 命令:
  - `timeout 2h direnv exec . python3 -m ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_preview_20260401T154956Z.yaml`
- 要点:
  - 已完成 3 条 synthetic plan
  - 输出目录:
    - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_20260401T154956Z`
  - 运行中出现动态告警:
    - CLIP 77 token 上限被超出, 当前自动 prompt 被截断

### 来源2: preview 产物整理脚本

- 要点:
  - 已导出 reference 图
  - 已导出三联图:
    - render / reference / kontext gen
  - summary:
    - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_20260401T154956Z/preview/summary.json`

### 来源3: 基础像素差统计

- 要点:
  - plan 0:
    - render->gen MAE = 6.016
    - reference->gen MAE = 30.718
  - plan 1:
    - render->gen MAE = 6.177
    - reference->gen MAE = 31.249
  - plan 2:
    - render->gen MAE = 5.517
    - reference->gen MAE = 19.929

## 当前结论

- 这 3 张图已经真实跑完, 不是 dry-run。
- 从像素差看, 当前 gen 仍明显更贴近 jitter render 主图, 没有直接塌成 reference copy。
- 但 prompt 截断是下一轮必须优先收紧的问题, 否则 reference 约束语义不能完整送进模型。

## [2026-04-01 16:12:20] [Session ID: omx-1775055181169-iytve2] 笔记: 第二轮更克制 prompt 的 3 图 preview 结果

## 来源

### 来源1: 第二轮真实 preview 运行

- 命令:
  - `timeout 2h direnv exec . python3 -m ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_preview_clean_20260401T160434Z.yaml`
- 要点:
  - 已完成 3 条 synthetic plan
  - 输出目录:
    - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_clean_20260401T160434Z`
  - 本轮未再出现 CLIP 77 token 截断告警

### 来源2: 第二轮三联图与 summary

- 位置:
  - `preview/summary.json`
  - `preview/triptych/000_triptych.jpg`
  - `preview/triptych/001_triptych.jpg`
  - `preview/triptych/002_triptych.jpg`
- 要点:
  - 中列 reference 图可直接见于三联图
  - `summary.json` 记录了每张图对应的 reference 路径

### 来源3: 第二轮基础像素差

- 要点:
  - plan 0:
    - render->gen MAE = 6.298
    - reference->gen MAE = 17.082
  - plan 1:
    - render->gen MAE = 5.876
    - reference->gen MAE = 24.178
  - plan 2:
    - render->gen MAE = 6.021
    - reference->gen MAE = 15.418

## 当前结论

- 第二轮 prompt/negative_prompt 方案至少解决了一个已验证问题:
  - 不再触发 prompt 截断
- 从三联图的人工观察看:
  - 第二轮 `gen` 相比第一轮更克制
  - 额外细碎细节和脏乱感有所减轻
  - 但仍不是“完全不动, 只做极轻修补”的极限保守状态

## [2026-04-02 00:23:40] [Session ID: omx-1775055181169-iytve2] 笔记: 第五轮超短版 silky/clean prompt 结果

## 来源

### 来源1: 第五轮真实 preview 运行

- 命令:
  - `timeout 2h direnv exec . python3 -m ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_preview_ultrashort_20260401T161837Z.yaml`
- 要点:
  - 已完成 3 条 synthetic plan
  - 输出目录:
    - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_ultrashort_20260401T161837Z`
  - 运行中未出现 prompt 截断告警

### 来源2: 第五轮 summary 与 triptych

- 位置:
  - `preview/summary.json`
  - `preview/triptych/000_triptych.jpg`
  - `preview/triptych/001_triptych.jpg`
  - `preview/triptych/002_triptych.jpg`
- 要点:
  - 当前使用的 prompt:
    - `Clean silky polish. Delicate, soft, natural.`
  - 当前使用的 negative prompt:
    - `gritty, rough, harsh, crunchy, oversharpened, overprocessed, busy texture, extra detail, clutter, reflections, patterns, text, noise`

### 来源3: 第五轮基础像素差

- 要点:
  - plan 0:
    - render->gen MAE = 5.581
    - reference->gen MAE = 17.468
  - plan 1:
    - render->gen MAE = 6.364
    - reference->gen MAE = 25.229
  - plan 2:
    - render->gen MAE = 6.019
    - reference->gen MAE = 20.230

## 当前结论

- 第五轮是当前最稳的版本:
  - 不再截断
  - 语义直接锚定“clean / silky / delicate”
  - 仍然更贴近主图 render, 没有塌成 reference copy
- 从人工观察看, 第五轮比第一轮更干净, 也比第四轮更可信, 因为它的 prompt 约束被完整送进了模型

## [2026-04-02 00:31:40] [Session ID: omx-1775055181169-iytve2] 笔记: 当前 preview render 太正常的动态证据

## 来源

### 来源1: 第五轮 `pose_jitter_log.jsonl`

- 要点:
  - plan 0:
    - trans ~= [-0.30, 0.09, 0.11]
    - rots ~= [2.08, 1.62, 0.62]
  - plan 1:
    - trans ~= [0.09, 0.10, -0.19]
    - rots ~= [3.29, -2.91, -0.90]
  - plan 2:
    - trans ~= [-0.10, 0.07, 0.25]
    - rots ~= [-0.19, 0.10, 4.00]
  - 三条样本的 `alpha_coverage` 全是 `1.0`

## 当前结论

- 对当前 preview 样本来说, jitter 幅度仍然偏温和。
- 这解释了用户看到的“render 太正常, 没有明显缺陷”。
- 下一轮应优先放大 jitter, 而不是继续纠缠 prompt 文案。

## [2026-04-02 00:46:20] [Session ID: omx-1775055181169-iytve2] 笔记: 更猛 jitter + 更柔和少浮尘 prompt 的 preview 结果

## 来源

### 来源1: 新一轮真实 preview

- 命令:
  - `timeout 2h direnv exec . python3 -m ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_preview_ultrashort_jitterhard_softclean_20260401T172600Z.yaml`
- 要点:
  - 已完成 3 条 synthetic plan
  - 输出目录:
    - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_ultrashort_jitterhard_softclean_20260401T172600Z`
  - 本轮未出现 prompt 截断告警

### 来源2: 本轮 prompt

- 要点:
  - `kontext_prompt`:
    - `Soft clean polish. Gentle, airy, smooth.`
  - `kontext_negative_prompt`:
    - `airborne dust, floating particles, dirty speckles, dirty spots, grain, grime, gritty, rough, harsh, crunchy, oversharpened, overprocessed, busy texture, clutter, reflections, patterns, text, noise`

### 来源3: 本轮 sample_log

- 要点:
  - plan 0:
    - trans ~= [-2.77, -3.07, -0.52]
    - rots ~= [-2.85, 3.96, 5.11]
  - plan 1:
    - trans ~= [-0.77, -1.04, -2.38]
    - rots ~= [13.28, 3.64, 8.06]
  - plan 2:
    - trans ~= [0.17, 0.59, 0.28]
    - rots ~= [14.45, 3.10, 8.60]
- 结论:
  - 本轮 render 已明显比旧 preview 更坏、更有缺陷, 尤其 plan 0 / 1

## 当前结论

- 这轮终于同时满足:
  - prompt 不截断
  - render 样本足够坏
  - gen 仍保持较柔和的清理风格
- 从人工观察看, 本轮比旧的“温和样本”更适合判断 Kontext 真正的修复能力。

## [2026-04-02 01:12:10] [Session ID: omx-1775055181169-iytve2] 笔记: 用户指定强训练参数后, before/after 差异已变得更可见

## 来源

### 来源1: 强训练版真实运行

- 命令:
  - `timeout 3h direnv exec . python3 -m ours.refine_by_kontext --exp_cfg /tmp/freefix_my5_kontext_preview_strongtrain_20260401T174137Z.yaml`
- 关键参数:
  - `refine_steps = 400`
  - `synthetic plan = 10`
  - `gen_prob = 0.2`
  - `kontext_strength = 0.55`

### 来源2: before/after 差异统计

- 要点:
  - frame 0:
    - MAE = 1.9861
    - changed_ratio_gt8 = 0.032236
  - frame 1:
    - MAE = 2.2412
    - changed_ratio_gt8 = 0.043147
  - frame 2:
    - MAE = 2.5827
    - changed_ratio_gt8 = 0.061264
  - frame 6:
    - MAE = 3.1301
    - changed_ratio_gt8 = 0.094110
- 对照旧轻 preview:
  - 旧轮次大致是 MAE 1.48~1.65, changed_ratio 0.7%~1.36%
  - 当前强训练版已提高到 MAE 1.99~3.13, changed_ratio 3.2%~9.4%

### 来源3: 固定视角 diff 三联图

- 位置:
  - `preview/fixed_compare/000_before_after_diff.jpg`
  - `preview/fixed_compare/001_before_after_diff.jpg`
  - `preview/fixed_compare/002_before_after_diff.jpg`
- 要点:
  - 右侧 diff x4 图里已经能清楚看到局部变化区域
  - before/after 本体仍然不是“整张画面翻新”, 而是偏局部细修与表面质感变化

## 当前结论

- 用户指定的强训练参数确实让 `before_refine / after_refine` 比之前更可见了。
- 但变化仍然主要集中在局部区域, 不是整张构图层面的巨大改写。
- 这与当前任务目标是一致的:
  - 让模型更偏“柔和清理 / 质感整理”
  - 而不是重做整个 fixed-view 画面

## [2026-04-02 01:46:20] [Session ID: omx-1775055181169-iytve2] 笔记: `strongtrain_refcolor` 与 `strongtrain_softfinish` 的对照结论

## 来源

### 来源1: `strongtrain_refcolor` 运行

- 配置:
  - `kontext_prompt: Clean dust-free finish. Soft, gentle. Match brightness and color to the reference.`
  - `kontext_negative_prompt: dust, airborne particles, floating particles, speckles, dirty spots, grain, grime, dirty film, gritty texture, harsh edges, crunchy detail, oversharpened, overprocessed, clutter`
- 输出目录:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_strongtrain_refcolor_20260401T181818Z`

### 来源2: `strongtrain_softfinish` 作为对照

- 配置:
  - `kontext_prompt: Soft clean finish. Gentle, calm, smooth air.`
- 输出目录:
  - `outputs/my5_colmap_fastgs_stable_35k_dense/kontext_preview_my5_strongtrain_softfinish_20260401T175832Z`

### 来源3: before/after 差异对照

- 要点:
  - `softfinish` 前 5 帧 MAE:
    - 1.8698 / 2.0057 / 2.3160 / 2.6267 / 2.0492
  - `strongtrain` 前 5 帧 MAE:
    - 1.9861 / 2.2412 / 2.5827 / 2.7962 / 2.1827
- 当前判断:
  - `softfinish` 相比上一轮更收、更柔一些
  - 变化幅度略降, 说明 prompt 的确在把结果往更克制方向推

## 当前结论

- 当前 prompt 微调方向是有效的:
  - 加入 `dust-free` 与“brightness/color to reference”之后, 仍保持不截断
  - 并继续把结果往更柔、更净方向轻推
- 但变化幅度比上一轮 `strongtrain` 稍微更收, 这属于“更柔和、更克制”的代价。
