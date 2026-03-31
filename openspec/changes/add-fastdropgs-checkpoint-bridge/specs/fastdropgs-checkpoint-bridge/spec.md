# Capability: Fastdropgs Checkpoint Bridge

## Purpose

定义 FreeFix 如何把 `fast-dropgs` 训练保存的 `chkpnt*.pth` checkpoint 转成可被当前 FreeFix refine 链路继续消费的 checkpoint, 同时保证来源语义、默认输出和后续 wrapper 行为都清晰可解释。

## Requirements

### Requirement: Bridge explicitly supports fast-dropgs checkpoints

系统 SHALL 显式支持 `fast-dropgs` 保存的 `chkpnt*.pth` checkpoint, 而不是只依赖“只要刚好能解析就算支持”。

#### Scenario: User imports a fast-dropgs checkpoint saved by upstream training

- **WHEN** 用户把 `fast-dropgs` 训练产物 `chkpnt50000.pth` 传给 bridge
- **THEN** 系统 SHALL 成功读取其 `(capture_tuple, iteration)` 结构, 并导出 FreeFix checkpoint

#### Scenario: Existing FastGS checkpoint support remains intact

- **WHEN** 用户继续传入现有 `FastGS` 的 `ckpt_*.pth`
- **THEN** 系统 SHALL 保持当前 FastGS checkpoint bridge 行为不变

### Requirement: Source metadata distinguishes fast-dropgs from other checkpoint sources

系统 SHALL 在 bridge 输出里显式记录 `fast-dropgs` 来源语义, 而不是把所有 `.pth` 都笼统记成同一类。

#### Scenario: Imported checkpoint came from a fast-dropgs `chkpnt*.pth`

- **WHEN** bridge 输入路径符合 `fast-dropgs` 的已支持命名或来源识别规则
- **THEN** 系统 SHALL 在输出 metadata 中把该来源标记为 `fastdropgs_checkpoint`

#### Scenario: Imported checkpoint came from an existing FastGS `ckpt_*.pth`

- **WHEN** bridge 输入仍是当前已支持的 FastGS checkpoint
- **THEN** 系统 SHALL 继续把该来源标记为 `fastgs_checkpoint`

### Requirement: Step inference explicitly supports `chkpnt{iteration}.pth`

系统 SHALL 为 `fast-dropgs` 的 checkpoint 命名提供正式的 step 推断规则。

#### Scenario: User imports `chkpnt50000.pth`

- **WHEN** 用户导入名为 `chkpnt50000.pth` 的 checkpoint
- **THEN** 系统 SHALL 把输出 step 识别为 `50000`

### Requirement: Default bridge output naming avoids ambiguous fast-dropgs checkpoint collisions

系统 SHALL 对 `chkpnt*.pth` 这类过于通用的 fast-dropgs 文件名提供更稳的默认输出命名。

#### Scenario: Multiple runs each contain a `chkpnt50000.pth`

- **WHEN** 用户未显式提供 `--bridge-output`, 且来源 checkpoint basename 过于通用
- **THEN** 系统 SHALL 在默认 bridge 输出名里纳入足够的来源上下文, 降低不同 run 之间的输出撞名风险

### Requirement: One-shot refine wrapper accepts fast-dropgs checkpoints as bridge sources

系统 SHALL 允许用户把 `fast-dropgs` checkpoint 直接交给 one-shot wrapper, 并继续进入现有 refine 编排。

#### Scenario: User starts from a fast-dropgs checkpoint and requests refine

- **WHEN** 用户使用 `ours/run_fastgs_refine.py` 传入 `fast-dropgs` 的 `chkpnt*.pth`
- **THEN** 系统 SHALL 先执行 bridge, 再把 bridge 输出继续传给当前选择的 refine backend

### Requirement: Documentation explains the bridge-to-refine contract for fast-dropgs

项目 SHALL 为 `fast-dropgs checkpoint -> FreeFix bridge -> refine` 提供清晰的命令示例和前置条件说明。

#### Scenario: User follows the documented fast-dropgs refine flow for the first time

- **WHEN** 用户第一次尝试把 `fast-dropgs` checkpoint 接到 FreeFix refine
- **THEN** 项目 SHALL 明确说明:
  - 需要匹配的 `--colmap-path`
  - 需要匹配的 `--exp-cfg`
  - 以及何时建议显式设置 `--bridge-output`
