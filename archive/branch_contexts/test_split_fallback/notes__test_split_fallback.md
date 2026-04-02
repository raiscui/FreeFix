## [${TS}] [Session ID: ${SESSION_ID}] 笔记: `test_every` fallback 划分现状

## 来源

### 来源1: `recon/trainer.py`

- 文件: `recon/trainer.py`
- 要点:
  - 如果 `cfg.partition` 非空, 会先拼成 `data_dir/<partition>`。
  - 如果 `cfg.partition` 为空, 但 `data_dir/partition.json` 存在, 会自动加载该文件。
  - 只有在两者都没有时, `Dataset` 才会走 fallback 划分。

### 来源2: `recon/datasets/colmap.py`

- 文件: `recon/datasets/colmap.py`
- 要点:
  - 有 `partition_file` 时, `train` 与 `test` 直接读取 JSON 中的两个数组。
  - 没有 `partition_file` 时:
    - `train = indices`
    - `test = indices[indices % test_every == 0]`
  - 这会导致 `test` 样本仍包含在 `train` 中。

## 综合发现

### 现象

- 当用户没有写 `partition`, 且数据目录下也没有 `partition.json` 时, fallback 逻辑会产生重叠的 train/test。

### 假设

- 这是一个历史遗留回退逻辑问题。
- 注释里保留的旧代码已经提示过正确方向: `train` 本应排除 `indices % test_every == 0` 的样本。

### 最小验证计划

- 修改 `Dataset` fallback 逻辑, 让 `train = indices[indices % test_every != 0]`。
- 补一个最小单测, 显式断言无 `partition_file` 且 `test_every = 2` 时:
  - `train = [1, 3]`
  - `test = [0, 2]`
  - 两者互斥。

## [2026-03-27 12:50:50] [Session ID: unknown] 笔记: 根因确认

## 来源

### 来源1: recon/datasets/colmap.py 静态代码路径

- 要点:
  - 无 partition_file 时, train 分支直接使用全部 indices。
  - test 分支使用 indices % test_every == 0 的子集。
  - 因此 test 集一定仍被 train 包含。

### 来源2: recon/trainer.py 自动补 partition 逻辑

- 要点:
  - cfg.partition 为空且 data_dir/partition.json 存在时, 训练器会自动启用该文件。
  - 所以这次修复命中的是真正没有 partition 文件的 fallback 情况。

## 综合发现

### 已验证结论

- 当前问题不是用户误配导致的假象, 而是 Dataset fallback 自身的集合划分逻辑有泄漏。
- 最直接且正确的修复是: train 使用 indices % test_every != 0。
