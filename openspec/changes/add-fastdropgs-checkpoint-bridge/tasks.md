## 1. bridge 来源识别与 metadata

- [x] 1.1 在 `recon/import_fastgs.py` 中为 `fast-dropgs` checkpoint 增加显式来源识别, 让 `chkpnt*.pth` 不再只被笼统记为 `fastgs_checkpoint`。
- [x] 1.2 为 step 推断补正式的 `chkpnt(\\d+)` 规则, 不再只依赖任意数字片段兜底。
- [x] 1.3 保证现有 FastGS checkpoint 和 `point_cloud.ply` 支持不回退。

## 2. 默认输出与后续 refine 编排

- [x] 2.1 调整 `fast-dropgs` checkpoint 的默认 bridge 输出命名, 降低 `chkpnt50000.pth` 这类通用文件名的撞名风险。
- [x] 2.2 更新 `ours/run_fastgs_refine.py`, 确保 wrapper 的帮助文本和 dry-run 语义明确支持 `FastGS / fast-dropgs` 两类来源。
- [x] 2.3 保持“bridge 后继续 refine”的现有编排不变, 只改良来源语义和默认体验, 不复制 refine 逻辑。

## 3. 测试与验证

- [x] 3.1 在 `tests/test_import_fastgs.py` 中补 `chkpnt*.pth` 风格样本, 覆盖来源识别、step 推断和 metadata 输出。
- [x] 3.2 在 `tests/test_run_fastgs_refine.py` 中补 wrapper 对 `fast-dropgs` checkpoint 的默认输出路径和命令拼接测试。
- [x] 3.3 跑一组最小验证, 至少覆盖:
  - 定向单测
  - `ours/run_fastgs_refine.py --dry-run`
  - 必要时用真实 `fast-dropgs` 样本做一次 bridge smoke

## 4. 文档

- [x] 4.1 更新 `README.md`, 给出 `fast-dropgs checkpoint -> FreeFix bridge -> refine` 的最小命令示例。
- [x] 4.2 明确写出使用前提: refine 仍然需要匹配的 `--colmap-path` 和 `--exp-cfg`。
- [x] 4.3 说明何时应显式指定 `--bridge-output`, 避免不同 run 的默认输出路径互相覆盖。
