# 任务计划: 执行 2026-04-02 的持续学习、经验沉淀与旧支线归档

## [2026-04-02 06:02:52] [Session ID: session-20260402T060252Z-continuous-learning] [记录类型]: 建立持续学习支线计划

## 目标

- 按 `continuous-learning` skill 的要求重新检索默认六文件与当前根目录支线六文件。
- 提炼本轮最值得长期保留的项目经验, 并同步回 `EXPERIENCE.md` 与相关文档。
- 把本次检索覆盖到、且已明确不再活跃的旧支线归档到 `archive/branch_contexts/`。

## 阶段

- [x] 阶段1: 列出并分组当前默认组六文件与支线文件
- [ ] 阶段2: 判定各支线活跃度并完成六文件摘要
- [ ] 阶段3: 沉淀经验并同步过期文档
- [ ] 阶段4: 归档旧支线并记录 manifest

## 关键问题

1. 当前哪些支线是真正活跃的?
   - 不能只看文件名, 要看最后一次追加记录日期和状态段落。
2. 本轮最值得沉淀的经验是什么?
   - 当前优先怀疑是 `pose_jitter_views_per_source` 的“采样密度语义”, 以及“文档要和代码语义同步”这两点。

## 做出的决定

- [采用] 先按支线分组阅读末尾状态, 再决定归档。
  - 理由: 同名后缀文件必须一起判断, 不能单看某一个文件。

## 遇到的错误

- 暂无

## 状态

**目前在阶段2** - 正在按支线分组做活跃度判定和六文件摘要。

## [2026-04-02 06:02:52] [Session ID: session-20260402T060252Z-continuous-learning] [记录类型]: 六文件摘要完成并开始文档同步

- 活跃度判定:
  - 活跃支线:
    - `__add_optional_flux_kontext_refine`
    - `__my5_refine_formal`
    - `__pose_jitter_fraction`
  - 未轮转旧支线:
    - `__fastgs_refine_probe`
    - `__flux_shinkai_ply_export`
    - `__nspr_eval`
- 已确认需要同步的长期载体:
  - `EXPERIENCE.md`
  - `README.md`
  - `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml`

## 阶段

- [x] 阶段1: 列出并分组当前默认组六文件与支线文件
- [x] 阶段2: 判定各支线活跃度并完成六文件摘要
- [ ] 阶段3: 沉淀经验并同步过期文档
- [ ] 阶段4: 归档旧支线并记录 manifest

## 状态

**目前在阶段3** - 正在把本轮经验回写到长期文件, 并修正已过期的 README / 配置注释。

## [2026-04-02 06:02:52] [Session ID: session-20260402T060252Z-continuous-learning] [记录类型]: 归档与沉淀完成

- 已完成文档与经验同步:
  - `EXPERIENCE.md` 已补入 `pose_jitter_views_per_source` 的“采样密度”语义
  - `README.md` 已补入分数模式说明与示例
  - `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 已修正过期注释
- 已完成归档:
  - `__fastgs_refine_probe`
  - `__flux_shinkai_ply_export`
  - `__nspr_eval`
  - manifest: `archive/manifests/2026-04-02_continuous_learning_branch_cleanup.md`
- 不新增 skill 的原因:
  - 本轮新增知识是项目内 refine 计划语义与上下文治理经验
  - 更适合沉淀到 `EXPERIENCE.md` 和仓库文档, 不属于跨项目通用 `self-learning.*` skill

## 阶段

- [x] 阶段1: 列出并分组当前默认组六文件与支线文件
- [x] 阶段2: 判定各支线活跃度并完成六文件摘要
- [x] 阶段3: 沉淀经验并同步过期文档
- [x] 阶段4: 归档旧支线并记录 manifest

## 状态

**目前已完成** - 本轮持续学习、文档同步与旧支线归档都已完成。
