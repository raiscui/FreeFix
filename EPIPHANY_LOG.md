## [2026-03-26 05:51:39] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 主题: pixi 的主环境 pin 住 setuptools, 不等于 isolated build 也会继承

### 发现来源
- 在修复 `pixi install` 构建 `mmcv==2.2.0` 时的 `pkg_resources` 崩溃链过程中发现

### 核心问题
- 项目已经声明 `setuptools = "==78.1.0"`, 但 `mmcv` 仍在构建阶段报 `No module named 'pkg_resources'`
- 根因不是项目没声明 `setuptools`, 而是 isolated build backend 没继承这份 pin

### 为什么重要
- 这类错误表面看像“少装了一个包”, 实际是“构建环境和运行环境脱钩”
- 如果误把缺失模块名直接当成 PyPI 包名去补, 很容易走进错误修复路径

### 未来风险
- 后续再接入旧式 `setup.py` 项目时, 只在主环境 pin 依赖可能仍然不够
- 看到 `pkg_resources`、`distutils`、`easy_install` 这类历史接口时, 要优先怀疑 build backend 兼容性

### 当前结论
- `setuptools==82.0.0` 已无法提供 `pkg_resources`
- `setuptools==78.1.0` 仍可导入 `pkg_resources`
- 对这类包, `pixi` 下优先考虑 `no-build-isolation` 或显式 build constraint, 不要直接迷信模块名提示

### 后续讨论入口
- 下次再遇到 `uv/pixi` 构建期 `ModuleNotFoundError` 时, 先看 `notes.md` 与 `ERRORFIX.md` 的这次案例

## [2026-03-26 07:20:13] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 主题: CUDA meta-package 版本看着对, 真实子包仍可能被高优先级 channel 偷换

### 发现来源
- 修复 `pytorch3d` 的 CUDA mismatch 过程中, 给项目加入 `cuda-toolkit 11.8.0` 后继续做版本核对时发现

### 核心问题
- 顶层 `cuda-toolkit` 明明是 `11.8.0`
- 但如果 `conda-forge` 比 `nvidia/label/cuda-11.8.0` 优先级更高, 求解器仍可能把 `cuda-nvcc`、`cuda-cudart` 等真实子包解到 `12.9`

### 为什么重要
- 这类问题非常有迷惑性
- 只看 manifest 或顶层包名, 很容易误判成“已经对齐 11.8”
- 真正参与编译的是 `nvcc`、headers、runtime dev libs, 不是 meta-package 名字本身

### 未来风险
- 以后项目里只要出现 `cuda-toolkit`、`cuda-compiler`、`cuda-nvcc` 这类组合, 就有再次发生“壳子版本对, 实体版本错”的风险
- 混合 channel 时尤其容易复发

### 当前结论
- 对 CUDA meta-package, 必须同时看:
  - `channels` 顺序
  - `conda-meta` 里的真实子包版本
  - `CUDA_HOME/bin/nvcc --version`
- 只看 `cuda-toolkit = 11.8.0` 远远不够

### 后续讨论入口
- 下次遇到 CUDA 相关编译失败, 先检查 `ERRORFIX.md` 里这次 `pytorch3d` 的记录

## [2026-03-26 08:45:50] [Session ID: 24cc3783-4a2b-4794-84b7-d2d4b7e7c6b6] 主题: 安装成功并不等于在 Blackwell 新卡上已经运行就绪

### 发现来源
- 在 `pixi install` 成功之后, 继续做最小 CUDA 张量实验和上游兼容矩阵核对时发现

### 核心问题
- 当前项目环境已经能装起来
- 关键原生扩展也能导入
- 但本机 GPU 是 `sm_120` Blackwell, `torch 2.5.1+cu118` 运行最小 CUDA 张量仍会报 `no kernel image is available for execution on the device`

### 为什么重要
- 如果把“安装成功”直接等价成“环境可用”, 在新 GPU 机器上会继续踩运行时雷
- 这类问题不会在求解阶段或 wheel 构建阶段暴露, 必须做最小运行实验才能看到

### 未来风险
- 后续谁只看 `pixi install` 通过, 很容易误以为整套项目已经准备好跑训练或推理
- 但 Blackwell 适配真正卡住的是版本栈:
  - PyTorch 官方支持从 `2.7 + cu128` 开始
  - 当前项目 pin 的 `xformers` 仍站在 `2.5.1`
  - `pytorch3d` 官方支持上限仍停在 `2.4.1`

### 当前结论
- 当前安装修复已经完成
- Blackwell 运行时适配是单独任务
- 它的本质是依赖栈迁移, 不是安装修复的尾部补丁

### 后续讨论入口
- 如果后续要做 Blackwell 适配, 先回看本条和 `notes.md` 里 `Blackwell 运行时边界与迁移成本评估`

## [2026-03-26 09:40:05] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 主题: 原生扩展的 source build 不能替代 Torch 底座对新 GPU 架构的支持

### 发现来源
- 在评估 `pytorch3d v0.7.9` 是否可以通过“升级 tag”或“自编译”解决 Blackwell `sm_120` 问题时发现

### 核心问题
- `pytorch3d` 的源码编译本身是可以启动的
- 但它通过 `torch.utils.cpp_extension` 生成的目标架构, 仍然受当前 Torch 安装的能力边界约束
- 在 `torch 2.5.1+cu118` 下, 实际编译参数持续只到 `compute_90/sm_90`

### 为什么重要
- 这类问题非常容易误判
- 很多人看到“那我从 source 重编一次”就会默认它能顺手吃到新 GPU
- 但如果底层 Torch wheel 本身不支持该架构, 上层扩展通常也不会凭空长出新目标码

### 未来风险
- 后续不只是 `pytorch3d`, 任何依赖 `torch.utils.cpp_extension` 的原生扩展都可能踩同类坑
- 如果跳过最小 CUDA 运行实验, 很容易把“扩展编出来了”误判成“整套环境已可运行”

### 当前结论
- 当前项目里,“自编译 pytorch3d”可以作为编译兼容性的验证手段
- 但它不是 Blackwell 适配的根修复
- 真正的第一优先级仍然是先把 Torch 迁到支持 `sm_120` 的版本线

### 后续讨论入口
- 下次再评估 `xformers`、`mmcv`、`fisher_rasterize` 一类原生扩展时, 先回看这条结论

## [2026-03-27 22:13:32] [Session ID: 019d2f6a-705e-7ca1-97af-342c1bf4e24d] 主题: `direnv` 里的 GitHub token 不等于普通 shell 里的 Git 凭据已经自动可用

### 发现来源
- 在把本地 `main` 推送到 `https://github.com/raiscui/FreeFix` 的过程中发现

### 核心问题
- `GITHUB_TOKEN` 在 `direnv exec .` 子会话里是可见的
- 但普通 `exec_command` shell 看不到它
- 即使 token 有效, Git 在当前环境下仍可能因为 `askpass` 链路不对而继续认证失败

### 为什么重要
- 这类问题很容易误判成“token 无效”或“仓库没权限”
- 实际上根因可能只是:
  - 环境变量注入范围不对
  - 或 Git 没从正确入口拿到用户名/密码

### 未来风险
- 后续凡是涉及 GitHub HTTPS push/pull, 如果又出现 `Authentication failed` 或 `could not read Username`, 可能会再次踩到同一类坑

### 当前结论
- 先用 GitHub API `/user` 验证 token 真伪
- 如果 token 只在 `direnv` 里可见, 就用 `direnv exec .` 包住 Git 命令
- 如果当前 `askpass` 链路损坏, 可用临时 `askpass` 脚本稳定喂给 Git:
  - `Username -> 账号名`
  - `Password -> GITHUB_TOKEN`

### 后续讨论入口
- 下次再做 GitHub 推送排障时, 先回看这条和 `notes.md` 里的本次记录

## [2026-03-26 10:39:48] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 主题: editable path package 的宽松依赖会把已经验证成功的 Torch 栈再次拖偏

### 发现来源
- 在 `torch 2.7.0+cu128` 的独立探针里尝试 `pip install -e submodules/UniDepth` 时发现

### 核心问题
- 我们已经验证 `torch 2.7.0+cu128` 是 Blackwell 可工作的底座
- 但 `UniDepth` 自己的 `requirements.txt` 只写了:
  - `torch>=2.4.0`
  - `torchvision>=0.19.0`
  - `torchaudio>=2.4.0`
- 结果 solver 会继续往更新版本漂, 试图把环境抬到 `torch 2.11.0`

### 为什么重要
- 这类问题非常隐蔽
- 人很容易以为“我已经在主项目 pin 了一个好版本, 那 path package 只会服从它”
- 但一旦顶层没有把相关伴生包一起钉住, editable package 的宽松下限会把整套 Torch 家族继续往前拉

### 未来风险
- 后续哪怕 `torch` 本身 pin 住了, 只要 `torchvision`、`torchaudio`、`xformers` 没一起锁住, 仍可能把求解拖进新的不兼容组合
- 这会把真正的根因从“Blackwell 适配”伪装成“为什么环境总是在随机爆别的包”

### 当前结论
- 做版本栈迁移时, 不能只 pin `torch`
- 必须把和它强耦合的家族包一起钉死:
  - `torchvision`
  - `torchaudio`
  - `xformers`
- 对 editable path package, 顶层 pin 是一等公民, 不能偷懒只看子包自己的 `requirements.txt`

### 后续讨论入口
- 下次再迁移 `unidepth`、`diffusers`、或其他带 dynamic dependencies 的 path package 时, 先回看这条

## [2026-04-01 07:13:47] [Session ID: 019d47d8-459e-7a31-bf25-470119af4082] 主题: 支线活跃度不能只靠 `task_plan` 勾选状态判断

### 发现来源
- 本轮持续学习在整理根目录支线六文件时, 对照了同后缀的 `task_plan`、`notes` 与 `WORKLOG`

### 核心问题
- 某些旧支线会出现:
  - `task_plan` 里还留着未勾选阶段
  - 但 `WORKLOG` 和 `notes` 已经写完真实交付与结论
- 这说明仅凭 task_plan 复选框, 可能把“收尾漏勾的旧支线”误判成“当前仍在推进的活跃任务”

### 为什么重要
- 持续学习、归档和回顾都依赖“活跃度判定”
- 如果这一步误判, 后果通常是两种:
  - 该归档的不归档, 根目录持续堆积旧上下文
  - 或者误把早已完成的支线当成当前待办, 污染后续判断

### 未来风险
- 后面只要支线越来越多, 这种“task_plan 落后于 WORKLOG”的情况就很容易再次出现
- 如果不先把判断口径写下来, 未来整理上下文时会持续反复踩坑

### 当前结论
- 判断支线是否活跃, 至少要同时看:
  - 同后缀文件组里的最新时间戳
  - `task_plan` 的状态
  - `WORKLOG` / `notes` 是否已经给出完整交付
- `__fastgs_colmap_compare` 这次就是典型例子:
  - `task_plan` 还有未勾选阶段
  - 但 `WORKLOG` 已经写出完成过程和总结

### 后续讨论入口
- 下次再做支线归档或持续学习时, 先看 `EXPERIENCE.md` 里的“上下文治理”章节和这条记录
