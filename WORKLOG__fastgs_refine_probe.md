## [2026-03-27 09:37:59] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] 任务名称: 落地 FastGS -> FreeFix Refine 桥接脚本

### 任务内容
- 新增 [import_fastgs.py](/home/rais/FreeFix/recon/import_fastgs.py), 支持把 FastGS `.pth` 或 `point_cloud.ply` 转成 FreeFix `ckpt`
- 修改 [refiner.py](/home/rais/FreeFix/recon/refiner.py), 允许直接指定外部 `load_ckpt_path`
- 修改 [refine_by_flux.py](/home/rais/FreeFix/ours/refine_by_flux.py) 与 [refine_by_sdxl.py](/home/rais/FreeFix/ours/refine_by_sdxl.py), 把 `load_ckpt_path` 暴露给 refine 工作流
- 新增 [test_import_fastgs.py](/home/rais/FreeFix/tests/test_import_fastgs.py), 锁定 checkpoint 映射、PLY 恢复和 similarity 变换行为

### 完成过程
- 先确认 `FastGS` 的 `.pth` 和 `.ply` 都能还原出和 FreeFix SH checkpoint 同构的高斯字段
- 再确认同一份 `data/my4_fullcolmap` 在 FastGS 与 FreeFix 之间只差一层 `parser.transform` similarity 归一化
- 基于这层事实实现桥接:
  - `means` 应用平移 + 统一尺度 + 旋转
  - `quats` 通过旋转矩阵左乘全局旋转后再写回四元数
  - `scales` 增加 `log(scale)`
- 用 `unittest` 跑通 5 项测试, 再用合成 FastGS checkpoint 做两轮 CLI smoke:
  - `--no-normalize`
  - 默认 `normalize=True`

### 总结感悟
- 这次真正的阻塞点不是“FastGS 的点不能用”, 而是“容器格式 + 坐标归一化”这两层隐式契约没人显式写出来
- 只要目标 FreeFix 配置是 `app_opt=false`, FastGS 的 SH 训练产物就可以稳定桥接
- `FastGS/cameras.json` 不该被误当成 Refine 的直接相机输入; 真正应该复用的是底层数据目录, 再交给 FreeFix parser 自己做归一化

## [2026-03-27 18:04:10] [Session ID: codex-fastgs-path-args-verify] 任务名称: 补强桥接与 Refine 的路径参数入口

### 任务内容
- 继续改良 [import_fastgs.py](/root/autodl-tmp/home/rais/FreeFix/recon/import_fastgs.py), 让桥接脚本支持更直观的 `--ckpt-path / --ply-path / --colmap-path`
- 继续改良 [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py) 与 [refine_by_sdxl.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py), 让 refine 阶段也能直接收 `--colmap-path / --ckpt-path`
- 新增 [test_refine_cli_paths.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_refine_cli_paths.py), 锁定参数解析和运行时路径 override 行为

### 完成过程
- 先复核已有改动, 确认 `load_ckpt_path` 已经能从 refine 脚本一路传进 `Refiner`
- 再跑语法检查和单测, 把“代码里看起来对”升级成“已有动态证据”
- 验证过程中发现 `refine_by_flux.py --help` 和 `refine_by_sdxl.py --help` 会超时
- 顺手把两个脚本改成:
  - 先 `parse_args()`
  - 后加载 `OmegaConf`
  - 真正执行 refine 时再加载 pipeline / torch / Refiner 等重依赖
- 最后再次验证:
  - `unittest` 11 项通过
  - 两个 `--help` 都能在 10 秒内返回
  - `recon.import_fastgs --ckpt-path ... --colmap-path ...` 的真实 smoke 成功写出 bridge ckpt

### 总结感悟
- CLI 参数支持不该只停在“功能逻辑能跑”, 还要保证帮助页和入口本身是顺手可用的
- 对这种重依赖脚本, “先解析参数再加载大模块” 是非常实用的默认设计
- 这次用户要的其实不是再加一层新封装, 而是把现有脚本入口改得更直接、更省脑力

## [2026-03-27 18:20:00] [Session ID: codex-fastgs-one-shot-wrapper] 任务名称: 新增一条命令版 FastGS refine wrapper

### 任务内容
- 新增 [run_fastgs_refine.py](/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py), 一条命令串起 bridge 与 refine
- 新增 [test_run_fastgs_refine.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_run_fastgs_refine.py), 锁定 wrapper 的参数契约和 orchestration 行为

### 完成过程
- 先复核现有 bridge / refine 入口, 确认已经具备 `colmap path / ckpt path` 能力
- 再设计 wrapper:
  - 输入 FastGS source
  - 自动生成 bridge 输出路径
  - 默认调用 Flux refine
  - 可选切到 SDXL
- 实现时刻意不复制已有算法逻辑, 只做命令编排
- 中途发现一个静态风险:
  - 如果从仓库外目录执行 wrapper
  - `python -m recon.import_fastgs` 可能找不到模块
- 于是补上固定 `cwd=repo_root()` 的执行策略
- 最后完成验证:
  - `py_compile` 通过
  - 全部相关单测 `17` 项通过
  - `--help` 可用
  - `--dry-run` 能完整打印两条内部命令

### 总结感悟
- 这次最重要的不是“又多了一个脚本”, 而是把两步手工操作收敛成一个更可信的入口
- orchestration 脚本只要做薄, 就能降低维护成本, 同时保留原始入口的可调试性
- `--dry-run` 很值钱, 它让用户在真正跑重流程前就能先确认命令链路是不是自己想要的

## [2026-03-27 10:33:50] [Session ID: codex-refine-hessian-attr-explain] 任务名称: 解释 `hessian_attr` 与 refine 结构纠正配置

### 任务内容
- 回答 refine 配置里 `hessian_attr: ["means", "quats", "scales"]` 的真实含义
- 核实它是不是“保持这些属性不动”的配置
- 基于当前实现给出“想让 refine 更主动纠正结构”时的推荐配置

### 完成过程
- 先回读 `fastgs_refine_probe` 支线上下文, 确认本轮问题仍属于同一条 refine 分析链路
- 再静态追踪 `hessian_attr`:
  - 从 `ours/refine_by_flux.py / refine_by_sdxl.py`
  - 到 `recon/refiner.py`
  - 再到 scheduler 的 `fuse_latents()` 融合公式
- 最后补了一个最小数值验证, 确认 `mask=1` 时是保留 prior latent, `mask=0` 时是放开给新生成分支

### 总结感悟
- `hessian_attr` 这个名字很容易让人误会成“参与优化的参数列表”或“冻结列表”, 但当前实现里它更像“certainty 估计的属性来源”
- 想修结构时, 关键不是把属性“锁住”, 而是让结构相关区域在 guide mask 里被正确识别出来
- 这类配置解释必须把“生成阶段 mask”与“后续 GS 优化器更新”拆开讲, 不然非常容易反着理解

## [2026-03-28 17:26:01] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] 任务名称: 给 FastGS refine wrapper 补最终 3DGS PLY 导出

### 任务内容
- 修改 [run_fastgs_refine.py](/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py), 让 wrapper 在 bridge 和 refine 之后再自动导出最终 3DGS `.ply`
- 修改 [test_run_fastgs_refine.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_run_fastgs_refine.py), 锁定第三步导出命令、结果路径推导和 `--final-ply-output` 参数

### 完成过程
- 先静态核实 refine 结束后的产物仍停在 `ckpt_<exp_name>.pt`, 现有 wrapper 没有最终导出步骤
- 再把 wrapper 的命令链扩成三步:
  - `recon.import_fastgs`
  - `ours.refine_by_flux|sdxl`
  - `recon.export_3dgs_ply`
- 中途发现两个实际坑点:
  - 不能假设配置里一定显式有 `gs_cfg_file`
  - 不能为了推导最终路径而让 `--dry-run` 先依赖 `OmegaConf`
- 所以最终改成:
  - `gs_cfg_file` 缺失时回退到 `cfg.json`
  - 只轻量解析 `base_dir / exp_name / gs_cfg_file`
  - 再读 `cfg.json` 里的 `result_dir` 来确定 refined ckpt 与 `.ply` 默认输出位置
- 最后跑完:
  - `py_compile`
  - wrapper 单测
  - `--help`
  - 一条真实 `--dry-run`

### 总结感悟
- “最终输出”这种需求, 最容易漏在 orchestration 的尾巴上, 因为前两步都能跑时, 人很容易误以为链路已经闭环
- 如果 wrapper 只是为了读几个路径键就提前依赖重配置库, 那它的 dry-run 价值会被大幅削弱
- 对这类一条命令脚本, 最值得锁定的不是算法正确性, 而是命令顺序、默认输出路径和 dry-run 可读性

## [2026-03-29 10:53:59] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 任务名称: 探索“随机相机偏移 + Flux 图生图”是否适合作为 refine 分支

### 任务内容
- 回读当前 FastGS -> FreeFix refine 支线, 确认现有 Flux refine 的真实数据流
- 判断“从现有相机做随机小偏移, 渲染后交给 Flux 图生图, 再拿去 refine”这条想法在当前架构里的落点
- 输出适合继续写成 OpenSpec 的方案边界、风险与建议

### 完成过程
- 先静态核对 [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py) 和 [refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py), 确认当前系统已经是“render -> img2img -> synthetic supervise -> refine”闭环
- 再核对 [colmap.py](/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py) 与 [base.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml), 确认相机、内参和 refine 配置的当前契约
- 最后把方案拆成两条路:
  - 直接替换现有固定视角链路
  - 保留现有主链, 额外增加一个受控 synthetic camera 分支
- 结合当前代码结构, 选择了第二条作为更稳的方向, 并补出主要风险:
  - pose 偏移过大时的 hallucination 注入
  - benchmark test split 被训练增强污染
  - 只动 `c2w` 不动 `K` 的表达边界

### 总结感悟
- 这条想法不是“能不能接进去”的问题, 而是“应该把它视为 refine 小修, 还是 synthetic novel-view augmentation”这个定义问题
- 从当前代码看, 它完全有落点, 但第一版一定要把姿态扰动限制在很小范围, 否则 2D 扩散会开始替 3D 几何编故事
- 这类新分支最需要先守住评测口径, 否则很容易在观感变好的同时, 让 benchmark 失去解释力

## [2026-03-29 10:58:30] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 任务名称: 为 pose jitter refine 手工创建 OpenSpec change

### 任务内容
- 在当前仓库里创建一条新的 OpenSpec change
- 将刚刚收敛出来的“受控 pose jitter synthetic refine”方案写成 proposal、design、tasks 和 capability spec
- 让后续实现可以直接接着这套 artifacts 往下做

### 完成过程
- 先确认当前仓库还没有 `openspec/` 目录, 本机也缺少 `openspec` CLI
- 再去参考其他仓库的 OpenSpec change 目录结构, 对齐常见的 spec-driven 骨架
- 最后手工创建:
  - [proposal.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/proposal.md)
  - [design.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/design.md)
  - [tasks.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/tasks.md)
  - [spec.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/specs/pose-jitter-refine/spec.md)
- 文档里明确了几个关键边界:
  - 默认仍保留 fixed refine 主链
  - pose jitter 必须和 eval split 解耦
  - 第一版只做小幅 `c2w` 扰动
  - synthetic 视角必须有安全检查与 fallback
- 创建完成后, 又回读了一轮所有 artifacts, 确认这套 change 已经到了可继续实现的粒度

### 总结感悟
- OpenSpec CLI 缺失不该成为阻塞, 只要目录约定清楚, change 仍然可以先落地
- 这次最值钱的不是“新建了 4 个 md 文件”, 而是把探索阶段的风险边界真正固化成了实现前约束
- 对这种容易从“局部增广”滑向“hallucination 监督”的能力, 先把 change 写严一点, 后面实现反而更稳

## [2026-03-29 11:19:26] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 任务名称: 按 ff-change 口径确认 pose jitter change 已可进入实现

### 任务内容
- 按 `openspec-ff-change` 的要求复核 `add-pose-jitter-refine`
- 确认这条 change 是否已经具备实现前所需的完整工件
- 给出当前 change 的可执行状态判断

### 完成过程
- 先回读 [proposal.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/proposal.md)、[design.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/design.md)、[tasks.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/tasks.md) 和 [spec.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/specs/pose-jitter-refine/spec.md)
- 再对照常见 spec-driven OpenSpec 骨架, 确认当前 change 不缺实现前关键 artifacts
- 最后明确记录:
  - 这条 change 已经是 apply-ready
  - 当前唯一缺的是本机 `openspec` CLI, 不是 change 内容本身

### 总结感悟
- `ff-change` 的本质不是“必须用 CLI 跑过一遍”, 而是“把实现前的工件一次性准备齐”
- 这条 pose jitter change 现在已经满足这个目标, 后面最自然的下一步就是直接按 `tasks.md` 开始做

## [2026-03-29 11:45:09] [Session ID: codex-add-pose-jitter-apply] 任务名称: 落地 pose jitter refine 主链与轻量验证

### 任务内容
- 新增 [pose_jitter.py](/root/autodl-tmp/home/rais/FreeFix/recon/pose_jitter.py), 把 pose jitter 的纯采样 / fallback helper 从重依赖 `refiner.py` 中解耦
- 修改 [refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py), 接通 `fixed | pose_jitter` 相机模式、source split 选择、alpha 覆盖率过滤、fallback 与 `sample_log`
- 修改 [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py) 与 [refine_by_sdxl.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py), 让 synthetic supervise 真正吃到 pose jitter 相机, 并落 `pose_jitter_log.jsonl`
- 修改 [base.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml) 与 [README.md](/root/autodl-tmp/home/rais/FreeFix/README.md), 补默认配置、小扰动起步值和 benchmark 风险说明
- 新增 [test_pose_jitter_refine.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_pose_jitter_refine.py), 锁定采样边界、fallback 行为和日志落盘格式
- 回写 [tasks.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/tasks.md), 勾掉已有动态证据支撑的任务

### 完成过程
- 先复核 `recon/refiner.py` 已落下的 pose jitter 补丁, 确认主逻辑已经覆盖:
  - base camera 选择
  - bounded jitter 采样
  - alpha coverage 过滤
  - fallback 到 base camera
- 接着发现一个测试层面的真实问题:
  - `recon.refiner` 顶层导入太重, 不适合直接作为 helper 单测入口
- 所以先做了一次“改良而不是叠补丁”的拆分:
  - 把 pose jitter 纯函数抽成轻模块
  - 让运行时代码继续复用
  - 单测直接针对轻模块
- 然后把 Flux / SDXL refine 的中间 synthetic 渲染循环切到配置驱动的 `camera_mode`
- 同时补了一层 jsonl 日志, 把每轮采样、过滤和 fallback 证据留到输出目录
- 最后完成验证:
  - `py_compile` 通过
  - `unittest` 12 项通过
  - 两个 `--help` 都能快速返回
  - 真实 Flux smoke 已尝试, 但本轮只推进到初始化阶段, 未进入主循环

### 总结感悟
- 这次最关键的不是“让 pose jitter 能采样”, 而是把它从一个 `refiner.py` 里的局部补丁, 变成真正能穿过 render -> img2img -> refine 的完整链路
- 对这种重依赖模块, helper 和主流程拆层非常值钱。否则你以为自己在测采样边界, 实际上是在赌整条渲染栈的导入时序
- 真实模型 smoke 的口径一定要干净: 已尝试不等于已跑通, 没进入主循环就不能把 `4.2` 勾掉

## [2026-03-29 12:17:05] [Session ID: codex-add-pose-jitter-smoke] 任务名称: 继续定位真实 pose jitter smoke 的运行时阻塞边界

### 任务内容
- 继续执行 `add-pose-jitter-refine` 剩余的 OpenSpec `4.2`
- 对真实 `python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke.yaml` 做系统化分段观测
- 修改 [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py) 与 [refine_by_sdxl.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py), 新增最小阶段日志, 打开长冷启动的黑盒

### 完成过程
- 先用分段探针验证冷启动的真实耗时分布:
  - `import torch` 约 `45s`
  - `torchvision` 和 pipeline / refiner 相关导入累计把冷启动拉到约 `100s`
- 然后在 refine 入口补上阶段日志:
  - 运行时依赖加载开始/结束
  - `Refiner` 初始化开始/结束
  - `FluxPipeline.from_pretrained` 前后
  - `pipe.to(cuda)` 前后
  - scheduler 替换前后
- 再按模块方式重跑真实 smoke, 先确认它已经能越过:
  - 运行时依赖加载
  - `Refiner` 初始化
  - `FluxPipeline.from_pretrained`
- 最后把阻塞点收敛到:
  - `pipe.to(cuda)`
  - 并确认在 `420s` 时间窗口内它仍未返回

### 总结感悟
- 这次最有价值的不是“又等了一轮 timeout”, 而是把阻塞点从模糊的“初始化阶段”压缩成了一个非常具体的边界
- 对超大模型 refine 流程, 阶段日志不是锦上添花, 而是基本可观测性
- 现在我们已经知道 `4.2` 为什么还不能勾: 不是 pose jitter 主链先炸了, 而是真实 Flux 冷启动在 `pipe.to(cuda)` 这一步超出了当前 smoke 窗口

## [2026-03-29 12:40:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 任务名称: 用 offload 绕过 `pipe.to(cuda)` 阻塞, 完成 pose jitter 真实 smoke

### 任务内容
- 新增 [refine_pipeline_runtime.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_pipeline_runtime.py), 统一管理 Flux / SDXL refine 的 pipeline 放置策略
- 修改 [refine_by_flux.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py) 与 [refine_by_sdxl.py](/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py), 支持 `refine_pipeline_offload_mode`
- 修改 [base.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml) 与 [README.md](/root/autodl-tmp/home/rais/FreeFix/README.md), 补默认配置和运行提示
- 新增 [test_refine_pipeline_runtime.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_refine_pipeline_runtime.py), 锁定 `none | model_cpu | sequential_cpu` 三种放置语义
- 回写 [tasks.md](/root/autodl-tmp/home/rais/FreeFix/openspec/changes/add-pose-jitter-refine/tasks.md), 勾掉最后的 `4.2`

### 完成过程
- 先复核本地 pipeline 代码, 确认真正的设备语义在 `_execution_device`, 不是 `pipe.device`
- 再把默认 `pipe.to(cuda)` 与可选 offload hook 收成一个共享 helper
- 然后补了 19 项轻量单测 / 行为测试, 确保新配置不会把原来的 CLI 和 pose jitter helper 打坏
- 最后用 `/tmp/pose_jitter_smoke_model_cpu.yaml` 发起真实 Flux smoke:
  - 越过了旧的 `pipe.to(cuda)` 阻塞点
  - 成功创建输出目录
  - 成功写出 `pose_jitter_log.jsonl`
  - 成功跑完 1 帧并退出码 `0`

### 总结感悟
- 对 diffusers 这类大模型 pipeline, offload 不只是“省显存开关”, 它还会改变“应该把输入送到哪”的设备语义
- 这次真正有效的改法不是硬叠更多超时日志, 而是把“放置策略”和“执行设备”从一开始就分开表达
- 有了这条绕行路径后, pose jitter 主链终于拿到了真实 smoke 证据, OpenSpec change 也才能干净收尾

## [2026-03-29 14:00:17] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 任务名称: 用 `my5` 真实验证 `pose_jitter + train source split`

### 任务内容
- 基于 `/tmp/my5_pose_jitter_train_smoke_20260329.yaml` 跑 `my5` 的 Flux pose jitter smoke
- 验证 `refine_camera_mode: pose_jitter` 和 `refine_camera_source_split: train` 的真实数据流
- 收集 `pose_jitter_log.jsonl`、render/gen 输出和最终 refined ckpt 作为动态证据

### 完成过程
- 先确认 `my5_colmap_fastgs_stable_35k_dense` 的 `cfg.json` 与 `ckpt_34999.pt` 都还在
- 再按用户说明排除“上轮误删除”的干扰, 不改代码直接重跑真实命令
- 运行完成后, 直接核对:
  - `refine/render/*.jpg`
  - `refine/gen/image_*.jpg`
  - `refine/pose_jitter_log.jsonl`
  - `ckpts/ckpt_my5_pose_jitter_train_smoke_20260329.pt`
- 最后确认日志里连续 3 帧都来自:
  - `source_split: train`
  - `source_index: 0 / 1 / 2`

### 总结感悟
- 这轮最值钱的不是“又跑了一次 smoke”, 而是把用户脑子里的目标语义和代码当前真实行为对上了
- `pose_jitter_log.jsonl` 很关键, 它把“到底围绕谁在抖动”从感觉变成了证据
- 当用户明确说明外部误操作存在时, 及时回滚上一轮失败口径, 比死守错误诊断更重要

## [2026-03-29 14:50:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 任务名称: 修复 mature checkpoint refine 第一步误重置 opacity 导致的黑帧

### 任务内容
- 修改 [recon/refiner.py](/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py), 让 strategy callback 使用 checkpoint 恢复步数而不是从 `0` 重新计数
- 新增 [recon/refine_runtime.py](/root/autodl-tmp/home/rais/FreeFix/recon/refine_runtime.py), 收拢 refine strategy 的 resume-step 计算
- 新增 [test_refine_runtime.py](/root/autodl-tmp/home/rais/FreeFix/tests/test_refine_runtime.py), 锁定 payload step / load step / local step 的时间轴映射
- 复跑真实 `my5 pose_jitter + train` smoke, 验证黑帧不再出现

### 完成过程
- 先用离线重渲染推翻了“pose_jitter 位姿语义先错”的旧假设
- 再用最小动态实验证明:
  - 黑化发生在第一个 refine step 之后
  - 即使只跑真实 train step, 也会立刻黑掉
- 然后继续剥离:
  - 关掉 `use_affine` 无法解决
  - 把 Flux 图换成自渲染图也无法解决
  - 只有把 `DefaultStrategy` callback 静音, 黑化才立刻消失
- 最后直接读取 `gsplat` 源码, 确认:
  - `step % reset_every == 0` 会触发 `reset_opa`
  - 当前 `Refiner` 恰好从 `step=0` 开始
- 修复后又补了两层验证:
  - 单步最小复现不再黑化
  - `my5_pose_jitter_train_smoke_fix_20260329` 真实复跑 3 帧成功, `render / gen / after_refine` 全部保持正常亮度

### 总结感悟
- 这次最危险的误导是“黑图出现在 pose_jitter 输出里, 就以为一定是 pose_jitter 的锅”
- 对加载成熟 checkpoint 的继续训练流程, 任何和“step”有关的第三方 strategy 都必须先确认恢复语义
- 如果一个流程会在 `step=0` 做 destructive reset, 那么从 checkpoint 恢复时绝不能直接复用局部步数当全局训练步数
