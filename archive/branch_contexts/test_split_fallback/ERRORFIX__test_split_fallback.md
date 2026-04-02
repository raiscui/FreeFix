## [2026-03-27 12:55:08] [Session ID: unknown] 任务名称: COLMAP Dataset fallback 划分导致 test 参与 train

### 问题现象
- 当训练配置没有写 partition, 且数据目录下也没有 partition.json 时, colmap Dataset 会进入 fallback 划分。
- 此时 test 会按 indices % test_every == 0 抽样, 但 train 仍使用全部图片。
- 结果是 test 图仍参与 train, 形成数据泄漏。

### 原因分析
- 根因在 recon/datasets/colmap.py 的 fallback 分支。
- 该分支对 test 做了按 test_every 抽样, 但 train 没有同步排除这些样本。
- trainer 的自动补 partition.json 逻辑没有问题, 真正的问题只发生在 partition 文件确实不存在时。

### 修复方法
- 将 train fallback 从全量 indices 改为 indices[indices % self.parser.test_every != 0]。
- 保留 test fallback 为 indices[indices % self.parser.test_every == 0]。
- 补充回归测试, 锁住无 partition 时 train/test 必须互斥。

### 验证结果
- python3 -m py_compile recon/datasets/colmap.py tests/test_colmap_dataset_contract.py
  - 通过
- .pixi/envs/default/bin/python -m unittest tests.test_colmap_dataset_contract
  - Ran 2 tests in 1.509s
  - OK

### 避坑提醒
- 只要存在 fallback 划分, 就必须保证 train/test 互斥, 不能把 test_every 只当成“额外抽一份评测视角”。
- 如果后续再改 Dataset 回退逻辑, 要优先保住这个测试。
