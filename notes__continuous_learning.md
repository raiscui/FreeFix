## [2026-04-02 06:02:52] [Session ID: session-20260402T060252Z-continuous-learning] 笔记: 2026-04-02 持续学习六文件摘要与归档判定

## 六文件摘要（用于决定如何沉淀知识）

- 涉及的上下文集（默认 / 支线后缀）：
  - 默认组
  - `__add_optional_flux_kontext_refine`
  - `__fastgs_refine_probe`
  - `__flux_shinkai_ply_export`
  - `__my5_refine_formal`
  - `__nspr_eval`
  - `__pose_jitter_fraction`
- 任务目标（task_plan.md）：
  - 默认主线当前没有独立未完成任务, 主要作用是给当天支线建立索引。
- 关键决定（task_plan.md）：
  - 当天继续保留 `__add_optional_flux_kontext_refine`、`__my5_refine_formal`、`__pose_jitter_fraction`
  - 本轮连续学习新建 `__continuous_learning` 专门处理知识沉淀与归档
- 关键发现（notes.md）：
  - 默认组已有 refine / resume / evaluation / 环境修复等长期经验
  - 当前最值得新增的经验是 `pose_jitter_views_per_source` 已升级成“采样密度”语义
- 实际变更（WORKLOG.md）：
  - 默认组最近一次主线工作仍停在 2026-04-01 的持续学习与归档整理
- 支线组摘要（如有, 按后缀分别写）：
  - `__add_optional_flux_kontext_refine`:
    - 2026-04-02 仍在继续做 Kontext prompt 微调
    - 最新状态是“保持 `kontext_strength = 0.55`, 继续只调 prompt”
  - `__my5_refine_formal`:
    - 2026-04-02 仍在推进
    - Flux 正式 run 已完成, 当前正在直接按原 yaml 跑 Kontext 正式对照
  - `__pose_jitter_fraction`:
    - 2026-04-02 已完成
    - 新增了分数比例参数支持与测试
  - `__fastgs_refine_probe`:
    - 最新记录停在 2026-04-01 21:30
    - 调参已落盘完成, 可视为未轮转旧支线
  - `__flux_shinkai_ply_export`:
    - 最新记录停在 2026-04-01 15:04
    - PLY 导出任务已明确完成
  - `__nspr_eval`:
    - 最新记录停在 2026-04-01 07:08
    - 指标口径核对与重算已完成
- 支线组活跃度判定（活跃 / 未轮转旧支线 / 历史版本）：
  - 活跃:
    - `__add_optional_flux_kontext_refine`
    - `__my5_refine_formal`
    - `__pose_jitter_fraction`
  - 未轮转旧支线:
    - `__fastgs_refine_probe`
    - `__flux_shinkai_ply_export`
    - `__nspr_eval`
- 暂缓事项 / 后续方向（LATER_PLANS.md，如有）：
  - 默认组仍保留 Blackwell 版本栈迁移相关待办
  - `__fastgs_refine_probe` 里仍有“若后续还觉得重影偏重, 可继续升级采样分布”的后续方向
  - `__nspr_eval` 里仍有“拆分 fixed window 和 dataset split 评估口径”的后续改造
- 错误与根因（ERRORFIX.md，如有）：
  - 当前最有新增价值的是 `__pose_jitter_fraction`:
    - 根因是 `pose_jitter_views_per_source` 被直接 `int(...)`
    - 不是“参数调不对”, 而是“分数语义从未被实现”
- 重大风险 / 灾难点 / 重要规律（EPIPHANY_LOG.md，如有）：
  - 已有结论仍成立:
    - 支线活跃度不能只看 `task_plan` 复选框
  - `__nspr_eval` 的口径风险仍值得保留, 但这次不需要再新增新的风险文件
- 可复用点候选（1-3 条）：
  - `pose_jitter_views_per_source` 应被当成“采样密度配置”, 不是单纯重复次数
  - 对带 `plan_index / image_id / resume` 契约的计划链路, 抽样必须保持确定性
  - 代码语义升级后要立即同步 README 和实验配置注释, 否则下次还会被旧口径误导
- 最适合写到哪里：
  - `EXPERIENCE.md`
  - `README.md`
  - 相关实验 yaml 注释
  - 归档 manifest
- 需要同步的现有 `docs/` / `specs/` / plan 文档：
  - `README.md`
  - `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml`
  - `task_plan.md` 的根目录支线索引
- 是否需要新增或更新 `docs/` / `specs/` / plan 文档：是
  - 更新 `README.md`
  - 更新相关 yaml 注释
  - 更新默认主线索引
- 是否提取/更新 skill：否
  - 这轮新增知识更偏项目内 refine 计划语义, 不适合提炼成跨项目通用 skill

## 来源

### 来源1: `self-learning.*` 检索

- 验证命令:
  - `rg -n "self-learning\\.|^name: self-learning" ~/.codex/skills ~/.agents/skills -g 'SKILL.md'`
- 结论:
  - 已完成去重检索
  - 当前没有与“refine 计划分数采样密度”高度重合的现成 skill
  - 但本轮知识仍然更适合落在仓库内长期文件, 不新建 skill

### 来源2: 文档搜索

- 验证命令:
  - `rg -n "pose_jitter_views_per_source|source_density|fractional_views_from_named_splits|synthetic plan" README.md openspec *.md exp_cfg -g '!archive/**'`
- 结论:
  - `README.md` 仍按旧语义描述 `pose_jitter_views_per_source`
  - `exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_v3.yaml` 的注释也已过期
  - 仓库内没有独立 `docs/` / `specs/` / `plans/` 目录需要同步
