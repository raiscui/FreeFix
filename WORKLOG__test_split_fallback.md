## [2026-03-27 12:55:08] [Session ID: unknown] 任务名称: 修复无 partition 时的 test_every 数据泄漏

### 任务内容
- 修改 recon/datasets/colmap.py 中无 partition_file 时的 fallback 划分逻辑。
- 更新 tests/test_colmap_dataset_contract.py, 补充 train/test 互斥的最小回归测试。

### 完成过程
- 先沿 trainer -> Dataset 代码路径确认: 只有配置未传 partition 且 data_dir 下也没有 partition.json 时, 才会进入 fallback。
- 再确认当前 fallback 的真实行为是 train 取全量, test 取按 test_every 抽样子集, 因而产生 test 仍参与 train 的泄漏。
- 将 train fallback 改为排除 indices % test_every == 0 的样本。
- 补充最小单测, 显式验证 test_every=2 时 train=[1,3], test=[0,2] 且两者互斥。
- 运行 python3 -m py_compile 和 unittest 做针对性验证。

### 总结感悟
- 没有显式 partition 文件时, fallback 逻辑也必须遵守训练集与测试集互斥这个基本约束。
- 这种回退路径很容易长期不被注意, 最稳妥的办法就是用最小契约测试把行为锁死。
