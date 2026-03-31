## Context

这次需求表面上看像“再支持一种新的 checkpoint 格式”。
但实际核对下来, 真相没有那么极端。

当前 FreeFix 的 bridge 入口 `recon.import_fastgs.py` 已经具备这几个关键事实:

- 对 `.pth` 输入, 它会统一走 `extract_fastgs_checkpoint_splats(...)`
- 这个解析逻辑只要求 payload 是 `(model_args, iteration)`, 且 `model_args` 至少包含高斯主参数槽位
- `fast-dropgs` 的 `GaussianModel.capture()` 返回值和当前 FastGS checkpoint 在核心 tuple 结构上同型

我们已经拿到了动态证据:

- `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth`
  已能被当前 bridge 真实导出成 FreeFix checkpoint
- 当前 wrapper `ours/run_fastgs_refine.py --dry-run`
  已能把这份文件串进 `bridge -> refine -> export ply`

所以这次 design 的重点, 不是“如何从零支持一种完全不兼容的新二进制格式”。
真正要定义清楚的是:

- 如何把 `fast-dropgs` 作为一种显式来源正式支持
- 如何让命名、metadata、默认输出和帮助文本跟上这种来源语义
- 如何在不破坏现有 FastGS / PLY 链路的前提下, 把这条支持从“碰巧能跑”升级到“项目承诺支持”

## Goals / Non-Goals

**Goals:**

- 显式支持 `fast-dropgs` 保存的 `chkpnt*.pth` checkpoint
- 保留当前共享的 tuple 解析主链, 不重复造桥接逻辑
- 让 bridge 输出 metadata 能区分 `fastgs_checkpoint` 和 `fastdropgs_checkpoint`
- 让 wrapper 的帮助文本和示例明确覆盖“转换后继续 refine”
- 为 `chkpnt*.pth` 的 step 推断、默认输出命名和后续 dry-run 补测试

**Non-Goals:**

- 本次不把 bridge 重构成通用插件系统
- 本次不承诺支持任意第三方 `.pth` checkpoint
- 本次不新增 `my8` 之类场景专用训练配置文件
- 本次不改写 refine 主链本身, 只保证 bridge 输出能继续接入现有 refine

## Decisions

### 决策1: 继续复用现有 tuple 解析逻辑, 不为 `fast-dropgs` 另起一套导入器

- 决定:
  - `fast-dropgs` checkpoint 继续走当前 `.pth -> capture tuple -> splats` 这条解析主链
  - 不新增第二套“专门给 fast-dropgs 用”的 tensor 映射代码
- 理由:
  - 结构证据已经足够强
  - 当前样本和 FastGS 样本在关键槽位上同型
- 备选方案:
  - 单独新增 `extract_fastdropgs_checkpoint_splats(...)`
- 为什么不选:
  - 会制造重复逻辑
  - 以后两边一旦分叉, 维护成本更高

### 决策2: 把“来源语义”从“结构解析”里拆出来, 单独显式表达

- 决定:
  - bridge 继续共用一套解析逻辑
  - 但输出 metadata 里的 `source_format` 需要能显式区分:
    - `fastgs_checkpoint`
    - `fastdropgs_checkpoint`
    - `fastgs_ply`
- 理由:
  - 当前真正缺的是“项目怎么称呼这份输入”
  - 结构兼容不等于用户语义已经被正式接住
- 备选方案:
  - 所有 `.pth` 仍然一律记成 `fastgs_checkpoint`
- 为什么不选:
  - 这会让“已支持 fast-dropgs”永远停留在暗箱里
  - 也不利于后续日志、调试和测试断言

### 决策3: `chkpnt*.pth` 要有显式的 step 识别规则, 不再只靠兜底数字匹配

- 决定:
  - `infer_step_from_path(...)` 需要把 `chkpnt(\\d+)` 当成正式支持模式
  - 通用数字回退可以保留, 但不能再是唯一支撑
- 理由:
  - 现在虽然“碰巧也能识别到 50000”, 但那只是靠通用数字回退
  - 正式支持应该把上游真实命名写进显式规则
- 备选方案:
  - 继续只靠任意数字片段兜底
- 为什么不选:
  - 可读性和可维护性太差
  - 也不利于单测表达“这就是 fast-dropgs 的已支持命名”

### 决策4: 对 `chkpnt*.pth` 这类通用文件名, 默认 bridge 输出名需要更稳

- 决定:
  - 当来源是 `fastdropgs_checkpoint` 且 basename 类似 `chkpnt50000.pth` 时
  - 默认 bridge 输出 label 应包含额外来源上下文, 例如父目录名
  - 显式 `--bridge-output` 继续拥有最高优先级
- 理由:
  - `chkpnt50000.pth` 这种名字在多个 run 中高度重复
  - 当前 dry-run 给出的 `outputs/fastgs_bridge/chkpnt50000_freefix.pt` 太容易撞名
- 备选方案:
  - 保持现状, 完全依赖用户手工指定 `--bridge-output`
- 为什么不选:
  - 这会让“正式支持 fast-dropgs”在默认体验上仍然很脆
  - 用户不应该每次都先理解内部撞名风险, 才能安全使用

### 决策5: 保持现有脚本名不变, 只扩展它们的用户口径

- 决定:
  - 继续使用 `recon.import_fastgs.py` 和 `ours/run_fastgs_refine.py`
  - 但帮助文本、README 和命令示例要改成 “FastGS / fast-dropgs”
- 理由:
  - 现有脚本名和调用方式已经在仓库里沉淀下来了
  - 这次更适合改良语义, 不适合大规模重命名入口
- 备选方案:
  - 把脚本整体改名成更抽象的 `import_gaussian_checkpoint.py`
- 为什么不选:
  - 范围过大
  - 会带来不必要的迁移和兼容成本

## Risks / Trade-offs

- [误判来源] 如果只靠路径和文件名判断 `fast-dropgs`, 未来第三方 checkpoint 可能被误标
- [默认输出名变更] 对部分依赖旧默认路径的调用来说, 新 label 可能带来预期差异
- [帮助文本扩展] 文案写清了“支持 fast-dropgs”, 用户会自然期待完整 refine 也开箱即用
- [真实场景依赖] 实际 refine 仍然需要匹配的 `--colmap-path` 与 `--exp-cfg`, 这不是 bridge 本身能自动解决的

## Migration Plan

1. 在 `recon.import_fastgs.py` 中补 `fast-dropgs` 来源识别和 `chkpnt` 命名规则。
2. 调整 bridge metadata 与默认输出 label, 让 `fastdropgs_checkpoint` 有明确表现。
3. 在 `ours/run_fastgs_refine.py` 中更新帮助文本和默认桥接输出语义, 确保 dry-run 口径清晰。
4. 在 `tests/test_import_fastgs.py` 和 `tests/test_run_fastgs_refine.py` 中补 `fast-dropgs` 风格样本测试。
5. 更新 `README.md`, 给出“转换后继续 refine”的最小命令示例和注意事项。

回滚策略:

- 如果 `fast-dropgs` 来源识别引发兼容问题, 先保留共享解析逻辑
- 把 metadata / 默认输出名的增强收回到更保守的行为
- 不回退现有 FastGS / PLY 主链

## Open Questions

- `source_format` 是否只需要区分 `fastdropgs_checkpoint`, 还是还要额外补一个更稳定的 `source_family`
- 默认 bridge 输出 label 应该在什么范围内引入父目录:
  - 只对 `chkpnt*.pth`
  - 还是对所有过于通用的 checkpoint 文件名都启用
- README 是给出通用命令模板就够, 还是顺手补一个面向 `my8` 的具体示例
