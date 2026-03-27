# 任务计划: 分析 FastGS 训练点是否可用于 FreeFix Refine

## [2026-03-27 09:19:56] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] [记录类型]: 初始化支线分析计划

## 目标

确认 `/home/rais/FastGS` 的训练输出中, 哪些“点”或 checkpoint 资产可以被 `/home/rais/FreeFix` 的 Refine 流程复用; 如果当前不能直接复用, 明确阻塞点, 并评估修改脚本支持的可行路径与改动范围。

## 阶段

- [x] 阶段1: 收集两边仓库的输出结构与入口脚本
- [ ] 阶段2: 查证 FastGS 训练产物的真实数据契约
- [ ] 阶段3: 查证 FreeFix Refine 的输入契约与最小必需字段
- [ ] 阶段4: 对齐差异, 给出“能否直接用 / 如何改造”的结论

## 关键问题

1. `FastGS` 当前真实输出的是 `point_cloud/*.ply` 还是和 `FreeFix` 一样的 `ckpt_*.pt`: 目前观察到两者都有可能存在, 但常规训练产物最稳定可见的是 `point_cloud/iteration_x/point_cloud.ply`, 少数 run 还带 `checkpoints/*.pth`。
2. `FreeFix` 的 `Refiner` 入口最先读取什么: 目前静态代码显示它直接读取 `result_dir/ckpts/ckpt_<step>.pt` 并取其中的 `splats` 参数字典。
3. 当前最重要的兼容性疑点是什么: `FastGS` 的导出格式和 `FreeFix` 的 checkpoint 契约看起来不一致, 需要继续验证是否能通过已有导出脚本或小改脚本完成桥接。

## 做出的决定

- 决定1: 先不猜“PLY 一定能不能用”, 先把 `FastGS` 实际输出文件和 `FreeFix` 真正读取的字段逐项对齐。
- 决定2: 分析口径固定为“现象 -> 假设 -> 验证计划 -> 结论”, 没有动态证据前不把某个差异直接说成根因。
- 决定3: 如果发现只是格式桥接问题, 优先评估“改良胜过新增”的路线, 尽量复用现有导出/加载逻辑, 而不是再平行新增一套格式。

## [2026-03-27 09:28:12] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] [记录类型]: 阶段2/3证据收敛, 准备落地桥接脚本

## 阶段

- [x] 阶段1: 收集两边仓库的输出结构与入口脚本
- [x] 阶段2: 查证 FastGS 训练产物的真实数据契约
- [x] 阶段3: 查证 FreeFix Refine 的输入契约与最小必需字段
- [ ] 阶段4: 对齐差异, 给出“能否直接用 / 如何改造”的结论

## 关键问题

1. `FastGS` 的 `.pth` 和 `FreeFix` 的 `.pt` 是否只是容器不同: 是。动态读取显示 `FastGS` checkpoint 是 `(capture_tuple, iteration)`; 其中 `_xyz/_features_dc/_features_rest/_scaling/_rotation/_opacity` 的形状分别和 `FreeFix` 的 `means/sh0/shN/scales/quats/opacities` 一一对应。
2. `FastGS` 的 `point_cloud.ply` 是否和 `FreeFix` 导出的 3DGS PLY 同构: 是。两边头部字段顺序都对齐到 `x/y/z/nx/ny/nz/f_dc_*/f_rest_*/opacity/scale_*/rot_*`。
3. 为什么还不能直接喂给 `Refiner`: 目前至少有两层不兼容:
   - 存档容器不同: `Refiner` 只认 `{"step": ..., "splats": ...}`。
   - 坐标系不同: `FastGS` 保存的是原始 COLMAP 坐标; `FreeFix` parser 会对同一数据集额外做 similarity + principal-axis 归一化。
4. 坐标系差异是否可解: 是。对 `data/my4_fullcolmap` 做动态验证后, `FastGS cameras.json` 到 `FreeFix parser.camtoworlds` 可以被 `parser.transform` 精确解释; 该矩阵的 3x3 部分是“统一尺度 * 旋转”, 适合同时作用到 `means/quats/scales`。
5. 哪条 FreeFix 训练线最适合作为桥接目标: `app_opt=false` 的训练线, 例如 `my4_fullcolmap_stable_12k_dense`。`app_opt=true` 的 `quality` 线会使用 `features/colors` 参数化, 不适合直接拿 `FastGS` 的 SH checkpoint 硬接。

## 做出的决定

- 决定4: 直接落地桥接脚本, 支持把 `FastGS` 的 `.pth` 或 `point_cloud.ply` 转成 `FreeFix` 的标准 `ckpt`。
- 决定5: 同时给 `Refiner` 增加 `load_ckpt_path` 可选入口, 避免用户必须把桥接产物放进旧结果目录才能试跑。
- 决定6: 桥接脚本默认按 `FreeFix` 的 `Parser(..., normalize=True)` 计算归一化矩阵, 而不是复用 `FastGS/cameras.json` 作为 Refine 相机来源。

## [2026-03-27 09:37:59] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] [记录类型]: 桥接脚本与 Refine 入口支持已落地

## 阶段

- [x] 阶段1: 收集两边仓库的输出结构与入口脚本
- [x] 阶段2: 查证 FastGS 训练产物的真实数据契约
- [x] 阶段3: 查证 FreeFix Refine 的输入契约与最小必需字段
- [x] 阶段4: 对齐差异, 给出“能否直接用 / 如何改造”的结论

## 关键问题

1. 是否已经把“可以桥接”落成可执行脚本: 是。新增 `recon/import_fastgs.py`, 支持把 FastGS `.pth` 或 `point_cloud.ply` 转成 FreeFix `ckpt`。
2. 是否还需要把桥接产物硬塞进旧 `result_dir/ckpts`: 不需要。`Refiner` 与 `refine_by_flux.py / refine_by_sdxl.py` 已新增 `load_ckpt_path` 可选入口。
3. 动态验证是否完成: 已完成两层:
   - `unittest` 5 项通过
   - 合成 FastGS checkpoint 的 CLI smoke 在 `normalize=False` 与 `normalize=True` 两种模式下都成功落盘
4. 当前剩余边界是什么:
   - `app_opt=true` 训练线仍不是本次桥接目标
   - 当前机器上的 `/home/rais/FastGS/output` 在收尾阶段已被清空, 因此没能再对“真实现存 run 文件”做一次最终 smoke import

## 做出的决定

- 决定7: 本次交付口径限定为“已支持 SH 参数化 FastGS 产物桥接到 FreeFix Refine”。
- 决定8: 对真实 run 的最终导入示例, 等用户重新提供或恢复具体 `.pth/.ply` 文件后再补一轮真实 smoke。

## 状态

**目前已完成** - `FastGS -> FreeFix Refine` 的桥接分析、脚本支持和单测验证都已完成, 可以直接交付结论与使用方法。

## [2026-03-27 09:37:59] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] [记录类型]: 按用户反馈补强脚本参数入口

## 目标

- 让桥接 / refine 脚本直接支持更直观的 `colmap path` 与 `ckpt path` 参数输入, 降低使用门槛。

## 阶段

- [ ] 阶段1: 梳理当前脚本参数语义与用户期待的命名
- [ ] 阶段2: 修改脚本, 新增直观参数别名与 CLI override
- [ ] 阶段3: 重新验证导入脚本与 refine 脚本的语法/单测

## 做出的决定

- 决定9: 优先“改良已有脚本”, 不额外再造一套新入口。
- 决定10: `import_fastgs.py` 增加 `--colmap-path` / `--ckpt-path` 这类直观别名。
- 决定11: `refine_by_flux.py / refine_by_sdxl.py` 也增加同名 CLI override, 让 refine 阶段直接按路径启动。

## 状态

**目前在阶段1** - 正在把用户希望的路径参数语义落进现有脚本接口。

## [2026-03-27 10:05:00] [Session ID: codex-fastgs-path-args-verify] [记录类型]: 接手参数别名改动并进入验证阶段

## 目标

- 确认新补的 `--colmap-path` 与 `--ckpt-path` 参数已经在桥接脚本和 refine 脚本里真正可用。
- 如果验证中暴露回归, 当场修掉, 不把“看起来差不多”当成交付。

## 阶段

- [x] 阶段1: 回读支线上下文, 接手当前任务链路
- [ ] 阶段2: 复核 `import_fastgs.py / refine_by_flux.py / refine_by_sdxl.py / refiner.py` 的参数落点
- [ ] 阶段3: 跑单测、语法检查与 CLI smoke
- [ ] 阶段4: 同步支线记录并整理最终使用命令

## 关键问题

1. 现象: 上一轮已经把参数入口补进代码, 但这批改动还没有重新验证。
2. 当前假设: 参数别名本身大概率方向正确, 但仍需确认 `argparse` 入口、路径解析和 `OmegaConf` override 没有引入新回归。
3. 验证计划:
   - 先做静态复核, 看参数是否真的传到 `Refiner`
   - 再跑 `unittest` 与 `py_compile`
   - 最后做一轮轻量 CLI smoke, 至少确认新参数可解析、可进入目标代码路径

## 做出的决定

- 决定12: 继续沿用这条支线的上下文文件, 不切回默认六文件。
- 决定13: 优先验证已有实现, 只有在证据显示有问题时才继续改代码。

## 状态

**目前在阶段2** - 已经接手历史上下文, 正在复核代码并准备做动态验证。

## [2026-03-27 10:12:00] [Session ID: codex-fastgs-path-args-verify] [记录类型]: 动态验证发现 refine CLI 顶层 import 过重

## 阶段

- [x] 阶段1: 回读支线上下文, 接手当前任务链路
- [x] 阶段2: 复核 `import_fastgs.py / refine_by_flux.py / refine_by_sdxl.py / refiner.py` 的参数落点
- [ ] 阶段3: 跑单测、语法检查与 CLI smoke
- [ ] 阶段4: 同步支线记录并整理最终使用命令

## 关键问题

1. 已验证事实:
   - `python3 -m py_compile ...` 通过
   - `python -m unittest tests.test_import_fastgs tests.test_trainer_eval_path` 7 项通过
2. 新观察到的现象:
   - `timeout 15s python3 ours/refine_by_flux.py --help` 超时
   - `timeout 15s python3 ours/refine_by_sdxl.py --help` 超时
3. 当前主假设:
   - 帮助页卡住主要是因为脚本在解析 CLI 之前就加载了 `torch`、pipeline、`Refiner` 等重依赖
4. 最强备选解释:
   - 也可能不是“重 import”本身, 而是某个顶层 import 触发了额外初始化或 I/O
5. 下一步最小验证 / 修复:
   - 把重依赖后移到 `refine()` 或 `main` 之后
   - 再重新跑 `--help` 看是否恢复秒级响应

## 做出的决定

- 决定14: 顺手修复 refine CLI 启动时机, 让新参数不仅“代码里存在”, 而且命令行入口真的好用。

## 状态

**目前在阶段3** - 单测和语法已过, 正在修复 refine CLI 帮助页超时并继续做 smoke。

## [2026-03-27 18:04:10] [Session ID: codex-fastgs-path-args-verify] [记录类型]: 路径参数入口补强已验证完成

## 阶段

- [x] 阶段1: 回读支线上下文, 接手当前任务链路
- [x] 阶段2: 复核 `import_fastgs.py / refine_by_flux.py / refine_by_sdxl.py / refiner.py` 的参数落点
- [x] 阶段3: 跑单测、语法检查与 CLI smoke
- [x] 阶段4: 同步支线记录并整理最终使用命令

## 关键问题

1. 用户要的“`colmap path` 和 `ckpt path` 直接传入”是否已经落地: 是, 桥接脚本和两个 refine 脚本都已支持。
2. 动态验证是否充分:
   - `python3 -m py_compile ...` 通过
   - `/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_import_fastgs tests.test_refine_cli_paths tests.test_trainer_eval_path` 通过, 共 `11` 项
   - `timeout 10s python3 ours/refine_by_flux.py --help` 输出了新参数
   - `timeout 10s python3 ours/refine_by_sdxl.py --help` 输出了新参数
   - 合成 FastGS checkpoint + 真实 `data/my4_fullcolmap` 的 smoke import 成功写出 bridge ckpt
3. 中间修掉了什么额外问题:
   - refine CLI 帮助页会被顶层重依赖卡住
   - `OmegaConf` 必须后移到 `parse_args()` 之后, 才不会让 `--help` 先撞环境依赖

## 做出的决定

- 决定15: 保持“改良已有脚本”的路线, 不再额外增加一层包装脚本。
- 决定16: 以后这类重依赖 CLI, 默认采用“先 parse 参数, 后加载运行时依赖”的结构。

## 状态

**目前已完成** - 路径参数入口、帮助页可用性、单测和 bridge smoke 都已验证完成, 可以交付给用户直接使用。

## [2026-03-27 18:15:00] [Session ID: codex-fastgs-one-shot-wrapper] [记录类型]: 用户同意增加一条命令串起 bridge + refine

## 目标

- 新增一个尽量薄的 orchestration 脚本, 让用户可以一条命令完成:
  - FastGS checkpoint / ply 导入
  - FreeFix refine 启动

## 阶段

- [x] 阶段1: 回读支线历史上下文, 明确当前可复用入口
- [ ] 阶段2: 设计 wrapper 的参数契约与默认行为
- [ ] 阶段3: 实现脚本并补回归测试
- [ ] 阶段4: 跑 CLI smoke, 确认一条命令链路可用

## 关键问题

1. 当前现象:
   - 现在 bridge 与 refine 已经都能直接吃 `colmap path / ckpt path`
   - 但用户仍需要手工执行两条命令
2. 当前主假设:
   - 最合适的做法不是再复制一份 refine 逻辑, 而是做一个薄 wrapper, 内部顺序调用现有入口
3. 最强备选解释:
   - 如果简单子进程串联太脆, 也可以把 `import_fastgs.main()` 与 `refine_by_flux.main()` 进一步模块化后做函数级联动
4. 验证计划:
   - 先实现“子进程串联 + fail-fast”
   - 再跑 `--help` 和最小 smoke

## 做出的决定

- 决定19: 优先走“先能用, 后面再优雅”的薄封装路线, 复用现有脚本, 降低侵入性。
- 决定20: wrapper 默认优先支持 Flux, 但保留 `--refine-backend` 切换到 SDXL。

## 状态

**目前在阶段2** - 正在设计一条命令版 wrapper 的参数契约与落点。

## [2026-03-27 18:20:00] [Session ID: codex-fastgs-one-shot-wrapper] [记录类型]: one-shot wrapper 已实现并验证

## 阶段

- [x] 阶段1: 回读支线历史上下文, 明确当前可复用入口
- [x] 阶段2: 设计 wrapper 的参数契约与默认行为
- [x] 阶段3: 实现脚本并补回归测试
- [x] 阶段4: 跑 CLI smoke, 确认一条命令链路可用

## 关键问题

1. 是否已经有“一条命令”入口: 是。新增 `ours/run_fastgs_refine.py`。
2. 它做的是哪种路线:
   - 不是重写 bridge
   - 不是重写 refine
   - 而是薄 wrapper 顺序调现有入口
3. 动态验证结果:
   - `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py` 通过
   - `/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine tests.test_import_fastgs tests.test_refine_cli_paths tests.test_trainer_eval_path` 通过, 共 `17` 项
   - `timeout 10s python3 ours/run_fastgs_refine.py --help` 成功输出帮助文本
   - `--dry-run` 成功打印 bridge 与 refine 两条内部命令
4. 中途补强了什么:
   - 子进程固定 `cwd=repo_root()`
   - 避免从仓库外调用时 `python -m recon.import_fastgs` 模块解析失败

## 做出的决定

- 决定21: 当前 wrapper 默认后端保留为 `flux`, 因为这是用户当前最直接的使用路径。
- 决定22: 保留 `--refine-backend sdxl` 作为切换开关, 但先不继续扩展更多 pass-through 参数, 以保持入口简单。

## 状态

**目前已完成** - one-shot wrapper、回归测试和 CLI 证据都已完成, 可以直接交付可执行命令。

## [2026-03-27 10:29:26] [Session ID: codex-refine-hessian-attr-explain] [记录类型]: 回答 refine 中 `hessian_attr` 语义与结构纠正配置

## 目标

- 查清 `hessian_attr: ["means", "quats", "scales"]` 在 FreeFix refine 里的真实作用。
- 明确这些字段是不是“保持不动”的意思, 还是“允许被结构优化器更新”的意思。
- 结合当前代码给出一套“希望 refine 主动纠正结构”时的推荐配置口径。

## 阶段

- [x] 阶段1: 回读 `fastgs_refine_probe` 支线历史上下文
- [ ] 阶段2: 静态定位 `hessian_attr` 在配置与实现中的流向
- [ ] 阶段3: 提炼“字段含义 / 是否保持 / 如何配置”的结论
- [ ] 阶段4: 同步支线记录并输出建议

## 关键问题

1. 当前现象: 用户对 `hessian_attr` 的直觉是“是不是表示保持这些属性”, 但这需要代码证据确认。
2. 当前主假设: `hessian_attr` 更像是“哪些属性参与 Hessian 引导的 refine 更新”, 而不是“冻结列表”。
3. 最强备选解释: 也有可能它只是某个正则化或缓存开关名, 真正是否更新还受别的白名单或优化器参数控制。
4. 验证计划:
   - 先查配置文件里的默认值
   - 再查 `Refiner` / optimizer / loss 里这个字段到底喂给了谁
   - 最后结合 refine 流程语义, 给出“想修结构”时应优先开的属性

## 做出的决定

- 决定17: 本轮先回答清楚现有语义, 不在没有证据前直接建议改代码。
- 决定18: 输出口径继续遵循“现象 -> 假设 -> 验证 -> 结论”, 避免把字段名望文生义。

## 状态

**目前在阶段2** - 已完成支线上下文回读, 正在定位 `hessian_attr` 的代码流向与 refine 配置语义。

## [2026-03-27 10:33:50] [Session ID: codex-refine-hessian-attr-explain] [记录类型]: `hessian_attr` 语义与结构纠正配置已完成核实

## 阶段

- [x] 阶段1: 回读 `fastgs_refine_probe` 支线历史上下文
- [x] 阶段2: 静态定位 `hessian_attr` 在配置与实现中的流向
- [x] 阶段3: 提炼“字段含义 / 是否保持 / 如何配置”的结论
- [x] 阶段4: 同步支线记录并输出建议

## 关键问题

1. `hessian_attr` 是不是“保持这些参数不动”: 不是。已验证它只参与 certainty / mask 估计, 不参与优化器冻结。
2. `means / quats / scales` 分别是什么:
   - `means`: 高斯中心位置
   - `quats`: 高斯旋转四元数
   - `scales`: 高斯尺度的 log 参数
3. 想让 refine 纠正结构时该怎么配:
   - 保守纠偏: `["means"]`
   - 更主动纠偏: `["means", "quats", "scales"]`
4. 风险边界:
   - 这会让结构相关区域“更容易被放开编辑”
   - 不等于绝对更稳, 仍要配合较克制的 `strength / warp_ratio / prompt`

## 做出的决定

- 决定19: 向用户明确区分“参数本身被优化”与“guide mask 如何生成”是两层不同机制。
- 决定20: 推荐口径以“想纠正结构”优先使用 `["means", "quats", "scales"]`, 但同时提醒风格化过强会带来几何漂移风险。

## 状态

**目前已完成** - `hessian_attr` 的语义、字段含义和“想让 refine 纠正结构时如何配置”的建议都已用代码证据核实完成。
