# 任务计划: 修复 `test_every` fallback 划分泄漏

## [${TS}] [Session ID: ${SESSION_ID}] [记录类型]: 初始化排查与修复计划

## 目标

让 `recon.datasets.colmap.Dataset` 在没有 `partition.json` 时, `train` 自动排除 `test_every` 抽到的 test 图, 使 train/test 真正互斥。

## 阶段

- [x] 阶段1: 回读相关代码并确认现象
- [ ] 阶段2: 形成根因假设并做最小可证伪验证
- [ ] 阶段3: 修改 fallback 划分逻辑并补回归测试
- [ ] 阶段4: 运行验证并整理交付记录

## 关键问题

1. 当前没有 `partition.json` 时, `train` 是否会排除 test 图: 不会。当前代码直接让 `train` 使用全部 `indices`。
2. 当前 `test` 是如何抽取的: `indices % self.parser.test_every == 0`。
3. 这是否会导致 `test ⊂ train`: 会, 因而产生数据泄漏。

## 做出的决定

- 决定1: 先基于现有代码与最小测试确认行为, 再做修复, 不凭感觉直接改。
- 决定2: 修复方式采用“恢复 train 排除 test”的逻辑, 而不是额外引入新配置项。
- 决定3: 必须补自动化测试, 锁住无 `partition.json` 时 train/test 互斥这一契约。

## 遇到错误

- 错误1: 当前 fallback 逻辑导致 `test_every` 抽到的 test 图仍参与 train。

## 状态

**目前在阶段2** - 已确认现象与静态证据, 正在组织最小验证并准备实施修复。

## [2026-03-27 12:50:50] [Session ID: unknown] [记录类型]: 完成根因确认, 准备改代码与补测试

## 阶段

- [x] 阶段1: 回读相关代码并确认现象
- [x] 阶段2: 形成根因假设并做最小可证伪验证
- [ ] 阶段3: 修改 fallback 划分逻辑并补回归测试
- [ ] 阶段4: 运行验证并整理交付记录

## 关键问题

1. 训练器是否会在配置缺失时自动补 data_dir/partition.json: 会, 只有真正不存在 partition 文件时才会进入 fallback。
2. 当前 fallback 是否真的让 train 与 test 重叠: 是。静态代码表明 train 直接取全部 indices, test 取按 test_every 抽样的子集。
3. 本次修复应改哪里: 改 Dataset 无 partition_file 时的 train 分支, 让它排除 test 索引。

## 做出的决定

- 决定4: 只修 recon/datasets/colmap.py 的 fallback 划分, 不改 trainer 的 partition 自动探测逻辑。
- 决定5: 新增最小 Dataset 单测, 显式锁住 test_every=2 且无 partition 时 train/test 互斥。

## 状态

**目前在阶段3** - 根因已确认, 下一步直接修改 fallback 划分逻辑并补测试。

## [2026-03-27 12:55:08] [Session ID: unknown] [记录类型]: 修复完成并完成验证

## 阶段

- [x] 阶段1: 回读相关代码并确认现象
- [x] 阶段2: 形成根因假设并做最小可证伪验证
- [x] 阶段3: 修改 fallback 划分逻辑并补回归测试
- [x] 阶段4: 运行验证并整理交付记录

## 关键问题

1. 修复后无 partition 时 train 是否还会包含 test 图: 不会。train 已改为排除 indices % test_every == 0 的样本。
2. 是否有自动化测试锁住新契约: 有。新增单测显式断言 test_every=2 时 train=[1,3], test=[0,2]。
3. 验证是否通过: 通过。py_compile 成功, unittest 2 项通过。

## 做出的决定

- 决定6: 保持 trainer 的 partition 自动探测逻辑不变, 只修 Dataset fallback 的集合划分。
- 决定7: 用最小回归测试锁住互斥划分, 防止以后再把 train 改回全量。

## 状态

**目前已完成** - 无 partition 文件时的 test_every fallback 划分已修复, train/test 互斥行为已由测试覆盖。
