## Why

当前 FreeFix 已经有一条成熟的 `FastGS -> FreeFix bridge -> refine` 链路:

- `recon.import_fastgs.py` 负责把外部 3DGS checkpoint / PLY 转成 FreeFix checkpoint
- `ours/run_fastgs_refine.py` 负责把 bridge、refine 和最终 PLY 导出串起来

但用户现在给的是另一支来源的 checkpoint:

- `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth`

这次核对里, 我们拿到的事实很明确。

- `fast-dropgs` 自己训练时默认保存的是 `chkpnt{iteration}.pth`, 不是 `ckpt_{iteration}.pth`
- 它内部保存的 `(gaussians.capture(), iteration)` 结构, 和当前 bridge 已能处理的 FastGS checkpoint 是同型的
- 当前 `recon.import_fastgs.py` 已经能把这份样本转成 FreeFix checkpoint
- 当前 `ours/run_fastgs_refine.py --dry-run` 也已经能把这份样本串进后续 refine

问题不在“完全不兼容”。

真正的缺口是, 这条支持还停留在“隐式可用”:

- bridge / wrapper / help 文案还都只写 `FastGS`
- `source_format` 仍然会把这类来源统称成 `fastgs_checkpoint`
- 测试还没有覆盖 `chkpnt*.pth` 这类 fast-dropgs 命名
- wrapper 对 `chkpnt50000.pth` 的默认 bridge 输出名过于通用, 容易和其他 run 撞名

所以这次 change 的目标, 不是发明第三套桥接协议。
而是把 `fast-dropgs checkpoint -> FreeFix bridge -> refine` 正式定义成项目支持的能力, 并补齐它的来源语义、默认行为、测试和文档。

## What Changes

- 为 bridge 显式支持 `fast-dropgs` checkpoint 这一类来源语义
- 为 `chkpnt{iteration}.pth` 这类命名补正式的 step 识别与来源标记
- 改良默认 bridge 输出命名, 降低 `chkpnt50000.pth` 这类通用文件名的撞名风险
- 让 one-shot refine wrapper 的帮助文本、命令示例和默认行为明确覆盖 `fast-dropgs`
- 补自动化测试, 锁定 `fast-dropgs` checkpoint 转换和后续 refine 编排口径

## Capabilities

### New Capabilities

- `fastdropgs-checkpoint-bridge`: 定义 FreeFix 如何把 `fast-dropgs` 保存的 `chkpnt*.pth` checkpoint 转成可被当前 refine 链路继续消费的 FreeFix checkpoint

### Modified Capabilities

- 无

## Impact

- 受影响代码:
  - `recon/import_fastgs.py`
  - `ours/run_fastgs_refine.py`
  - `tests/test_import_fastgs.py`
  - `tests/test_run_fastgs_refine.py`
  - `README.md`
- 受影响行为:
  - bridge 对 `.pth` 来源的识别与 metadata 输出
  - `chkpnt*.pth` 的 step 推断和默认输出命名
  - wrapper 对 `fast-dropgs` 输入的用户口径
  - “转换后继续 refine”这条链路的文档说明
- 需要补充验证:
  - `fast-dropgs` 风格 checkpoint 的单测
  - wrapper 的 dry-run 验证
  - 匹配真实场景数据时的最小 smoke 说明
