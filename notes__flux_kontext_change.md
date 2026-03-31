## [2026-03-31 16:50:03] [Session ID: codex-flux-kontext-change-20260331] 笔记: 新建可选 FLUX.1-Kontext-dev change 的 OpenSpec 结论

## 来源

### 来源1: `openspec list`

- 位置: 仓库根目录终端命令
- 要点:
  - 当前已有 change:
    - `add-fastdropgs-checkpoint-bridge`
    - `add-pose-jitter-refine`
  - 两者都已完成, 不与本次 change 名冲突

### 来源2: `openspec new change add-optional-flux-kontext-refine`

- 位置: 仓库根目录终端命令
- 要点:
  - 成功创建 change
  - 路径为 `openspec/changes/add-optional-flux-kontext-refine/`
  - schema 为 `spec-driven`

### 来源3: `openspec status --change add-optional-flux-kontext-refine`

- 位置: 仓库根目录终端命令
- 要点:
  - 当前进度为 `0/4 artifacts complete`
  - artifact 顺序是:
    - `proposal`
    - `design`
    - `specs`
    - `tasks`
  - 第一份 ready artifact 是 `proposal`

### 来源4: `openspec instructions proposal --change add-optional-flux-kontext-refine`

- 位置: 仓库根目录终端命令
- 要点:
  - `proposal.md` 的写入路径已明确
  - 核心段落要求:
    - `Why`
    - `What Changes`
    - `Capabilities`
    - `Impact`
  - `Capabilities` 是 proposal 到 specs 的契约层, 需要明确列出新能力名

### 来源5: `find openspec/specs -maxdepth 2 -type f | sort`

- 位置: 仓库根目录终端命令
- 要点:
  - 当前不存在 `openspec/specs/` 主规格目录
  - 这意味着本次 proposal 更适合先声明 `New Capabilities`
  - `Modified Capabilities` 只有在后续明确存在主规格时才适合填写

## 综合发现

### 变更定位

- 本次 change 应明确表达为:
  - 新增可选 `FLUX.1-Kontext-dev` 路径
  - 与 `sdxl/flux` 并列
  - 不替代现有 `FLUX.1-dev`

### 命名结论

- `add-optional-flux-kontext-refine` 与用户意图一致
- 名称同时保留了:
  - optional
  - flux-kontext
  - refine

### Proposal 填写建议

- `Why` 应聚焦:
  - 当前只有 `sdxl/flux`
  - 缺少更适合图像编辑与多轮一致性的可选链路
  - 需要在不破坏现有 `flux` 工作流的前提下扩展能力
- `What Changes` 应强调:
  - 增加新的可选模型/后端选择
  - 保留现有 `sdxl/flux` 路径不变
  - 补充配置、加载和运行分流
- `Capabilities` 当前更适合先写 `New Capabilities`

## [2026-03-31 16:58:42] [Session ID: codex-flux-kontext-change-20260331] 笔记: fast-forward 产物内容与验证结果

## 来源

### 来源1: 新生成的 `proposal/design/spec/tasks`

- 位置:
  - `openspec/changes/add-optional-flux-kontext-refine/proposal.md`
  - `openspec/changes/add-optional-flux-kontext-refine/design.md`
  - `openspec/changes/add-optional-flux-kontext-refine/specs/optional-flux-kontext-refine/spec.md`
  - `openspec/changes/add-optional-flux-kontext-refine/tasks.md`
- 要点:
  - proposal 把口径锁为“新增 `kontext` backend, 不替代现有 `flux`”
  - design 明确了:
    - 独立 `ours/refine_by_kontext.py`
    - wrapper 新增 `kontext`
    - 独立 `kontext_model_path`
    - 官方 Kontext pipeline 兼容优先
    - source real image 作为独立参考输入
  - spec 把行为拆成:
    - backend 选择
    - refine runtime contract 复用
    - 独立模型来源
    - render 作为主输入
    - source real image 作为可选参考输入
    - 掩码兼容路径
    - 文档说明
  - tasks 已按实现依赖拆成 4 组

### 来源2: `openspec status --change add-optional-flux-kontext-refine`

- 位置: 仓库根目录终端命令
- 要点:
  - 返回 `Progress: 4/4 artifacts complete`
  - 显示 `All artifacts complete!`

### 来源3: `openspec validate add-optional-flux-kontext-refine`

- 位置: 仓库根目录终端命令
- 要点:
  - 返回 `Change 'add-optional-flux-kontext-refine' is valid`

## 综合发现

### 已锁定的产品边界

- `Kontext` 是第三种 backend
- 默认 backend 仍是 `flux`
- 这次 change 不是“替换 `FLUX.1-dev`”
- 这次 change 更适合服务:
  - 图像编辑
  - 多轮一致性
  - reference-guided repair

### 已锁定的实现边界

- 首版优先采用官方 `FluxKontextPipeline` / `FluxKontextInpaintPipeline` 兼容路线
- 首版允许和当前私有 `flux/sdxl` 扩展存在行为差异, 但差异必须文档化
- source real image 与当前 render 图必须分角色, 不能混成一个输入槽位
