## [2026-03-26 05:43:06] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 笔记: mmcv 构建失败根因候选与证据

## 来源

### 来源1: 用户提供的 `pixi install` 失败日志

- 要点:
  - 失败发生在 `mmcv==2.2.0` 的 `setuptools.build_meta:__legacy__.build_wheel`。
  - 异常是 `ModuleNotFoundError: No module named 'pkg_resources'`。
  - 失败点位于隔离构建临时环境: `/home/rais/.cache/rattler/cache/uv-cache/builds-v0/...`

### 来源2: 项目内 [pixi.toml](/root/autodl-tmp/home/rais/FreeFix/pixi.toml)

- 要点:
  - 已显式声明 `setuptools = "==78.1.0"`。
  - 已对 `pytorch3d`、`fisher_rasterize`、`unidepth`、`xformers` 使用 `[pypi-options] no-build-isolation = [...]`。
  - `mmcv = ">=2.2.0, <3"` 当前仍走默认隔离构建路径。

### 来源3: `mmcv-2.2.0` sdist 的 `setup.py`

- 关键原文:
  - `from pkg_resources import DistributionNotFound, get_distribution, parse_version`
- 结论:
  - `mmcv` 的构建脚本在 very early 阶段就直接依赖 `pkg_resources`。
  - 这不是运行时导入, 而是构建脚本导入, 所以一旦隔离构建环境里没有该模块, 构建会立刻中断。

### 来源4: Pixi 官方文档 `docs/reference/pixi_manifest.md`

- 关键原文:
  - `One can choose to not isolate the build for a certain package name, this allows the build to access the pixi environment.`
  - `Packages are installed in that order: ... packages with build isolation ... packages without build isolation installed in the order they are added to no-build-isolation`
- 结论:
  - `pixi.toml` 官方公开支持的直接手段是 `no-build-isolation`。
  - 文档中没有查到 `extra-build-dependencies` 的 `pixi.toml` 等价写法。

### 来源5: 额外验证

- `python3 -m pip index versions pkg_resources` 返回 `ERROR: No matching distribution found for pkg_resources`
- 本机 Python 中 `pkg_resources` 来自 `setuptools`
- 结论:
  - 报错提示里建议的 `mmcv = ["pkg_resources"]` 对当前项目并不可靠, 因为 `pkg_resources` 不是一个可直接解析的 PyPI 分发包名。

## 综合发现

### 现象

- `pixi install` 在构建 `mmcv==2.2.0` 时失败。
- 错误是隔离构建环境缺少 `pkg_resources`。

### 当前主假设

- `mmcv` 的 sdist 构建脚本依赖 `pkg_resources`, 但没有在自己的构建依赖里声明。
- `pixi` 走隔离构建时没有把项目里钉住的 `setuptools==78.1.0` 带进去, 导致构建环境拿不到兼容的 `pkg_resources` 提供者。

### 最强备选解释

- 不只是“缺少 setuptools”, 还有可能是隔离构建环境拉到了较新的 `setuptools`, 而这些新版本已经移除了 `pkg_resources`, 所以即使 build backend 本身能工作, `mmcv` 的旧式导入仍会失败。

### 什么证据会推翻主假设

- 如果把 `mmcv` 改成 `no-build-isolation` 后仍然报同一个 `pkg_resources` 错误, 那就说明主环境里的 `setuptools` 也不提供该模块, 或者根本没进入预期构建路径。
- 如果 `pixi` 其实支持 package-specific extra build dependencies, 且能把 `setuptools<82` 注入到 `mmcv` 的 isolated build 中, 那么“只能改成 no-build-isolation”这个方案就不是最佳方案。

### 当前倾向结论

- 现阶段最稳妥的项目内修复, 是把 `mmcv` 加进 `[pypi-options].no-build-isolation`。
- 这样 `mmcv` 会在现有 `pixi` 环境里构建, 可直接使用项目已声明的 `setuptools==78.1.0`。
- 这个方案也和项目里 `xformers`、`unidepth` 等源码构建包的处理方式一致。

## [2026-03-26 05:51:39] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 笔记: 根因对照实验与最终验证

## 来源

### 来源1: 临时虚拟环境对照实验

- 验证命令:
  - `setuptools==82.0.0` 环境中执行 `import pkg_resources`
  - `setuptools==78.1.0` 环境中执行 `import pkg_resources`
- 关键输出:
  - `setuptools82: 82.0.0 | ModuleNotFoundError No module named 'pkg_resources'`
  - `setuptools78: 78.1.0 | pkg_resources OK`
- 结论:
  - `pkg_resources` 在 `setuptools>=82` 的环境里已不可用。
  - 这和用户日志里的报错形态完全一致。

### 来源2: `.pixi` 环境直接执行 `mmcv-2.2.0/setup.py --version`

- 验证命令:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python setup.py --version`
- 关键输出:
  - `from pkg_resources import ...` 仅产生 deprecation warning, 没有 `ModuleNotFoundError`
  - `Skip building ext ops due to the absence of torch.`
  - `2.2.0`
- 结论:
  - 在项目的 `.pixi` 主环境中, `mmcv` 的失败入口已经可以顺利通过。
  - 这证明“切换到 no-build-isolation + 使用主环境里的 setuptools 78.1.0”确实解决了原始的 `pkg_resources` 崩溃链。

## 综合发现

### 已验证结论

- 原始报错不是普通的“包没装上”, 而是 `mmcv` 的老式构建脚本和较新 `setuptools` 的兼容性问题。
- `pixi.toml` 里单独声明 `setuptools = "==78.1.0"` 并不能自动约束 isolated build backend。
- 把 `mmcv` 放进 `no-build-isolation` 后, 它可以使用项目主环境里的 `setuptools 78.1.0`, 从而恢复 `pkg_resources`。

## [2026-03-26 07:20:13] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 笔记: pytorch3d 的 CUDA mismatch 排查与修复口径

## 来源

### 来源1: 用户提供的 `pytorch3d` 构建日志

- 现象:
  - `RuntimeError: The detected CUDA version (12.8) mismatches the version that was used to compile PyTorch (11.8)`
  - 同轮日志还有 `CUB_HOME` warning

### 来源2: 本地环境与 PyTorch 动态检查

- 验证结果:
  - `torch.__version__ == 2.5.1+cu118`
  - `torch.version.cuda == 11.8`
  - `torch.utils.cpp_extension.CUDA_HOME == /usr/local/cuda`
  - `/usr/local/cuda/bin/nvcc --version` 为 `12.8`
- 结论:
  - 原始失败确实来自 `torch.utils.cpp_extension` 误用宿主机 `/usr/local/cuda`

### 来源3: `pytorch3d v0.7.7` 的 `setup.py`

- 关键原文:
  - `from torch.utils.cpp_extension import CppExtension, CUDA_HOME, CUDAExtension`
  - `if (not force_no_cuda and torch.cuda.is_available() and CUDA_HOME is not None) or force_cuda:`
  - `warnings.warn("The environment variable CUB_HOME was not found...")`
- 结论:
  - 真正的阻塞条件是 `CUDA_HOME` 指到了错误版本的 toolkit
  - `CUB_HOME` 在这版 `setup.py` 里提示比较激进, 但它不是这次第一顺位的阻塞点

### 来源4: 最小 pixi 探针工程

- 探针配置:
  - `channels = ["nvidia/label/cuda-11.8.0", "conda-forge"]`
  - `cuda-toolkit = { version = "==11.8.0", channel = "nvidia/label/cuda-11.8.0" }`
- 关键发现:
  - 当 `conda-forge` 在前时, 真实安装会混入 `cuda-nvcc 12.9` 等 12.x 子包
  - 调整成 `nvidia/label/cuda-11.8.0` 在前后, `conda-meta` 收敛到整套 `11.8.x`

### 来源5: 包缓存与 PyTorch 版本检查

- 包缓存里已存在:
  - `~/.cache/rattler/cache/pkgs/.cuda-nvcc-11.8.89-*/bin/nvcc`
- 验证命令:
  - 将 `CUDA_HOME` 指到缓存中的 `cuda-nvcc 11.8.89`
  - 调用 `torch.utils.cpp_extension._check_cuda_version(...)`
- 关键输出:
  - `torch_cuda= 11.8`
  - `check_cuda_version=PASS`
- 结论:
  - 原始 `12.x vs 11.8` 的 mismatch 链在 11.8 toolchain 下已经可以通过

## 综合发现

### 现象

- `pytorch3d` 构建阶段误用了宿主机 `/usr/local/cuda`
- 初次补 `cuda-toolkit` 时, 又因为 channel 顺序问题混入了 `conda-forge` 的 `12.9` CUDA 子包

### 被新证据推翻的上一假设

- 上一假设: “只要加 `cuda-toolkit = 11.8.0` 就够了”
- 推翻证据:
  - `.pixi/envs/default/bin/nvcc --version` 一度变成了 `12.9`
  - `conda-meta` 显示 `cuda-toolkit 11.8.0` 旁边配套的却是大量 `conda-forge` 的 `12.9.x` 子包
- 回滚后的结论:
  - 只加 meta-package 不够
  - 还必须控制 channel 优先级, 让整套 CUDA 子包从同一条 `11.8` 线解析

### 当前已验证结论

- 本轮最正确的项目内修复是两步一起做:
  - 在 `pixi.toml` 中引入 `cuda-toolkit = 11.8.0`
  - 把 `nvidia/label/cuda-11.8.0` 提到 `conda-forge` 前面
- `.envrc` 中把 `CUDA_HOME` 固定到 `.pixi/envs/default`, 是为了让 no-build-isolation 的源码构建不要继续误探测宿主机 `/usr/local/cuda`

### 当前剩余风险

- `pytorch3d v0.7.7` 官方 `INSTALL.md` 只列到 Python 3.10 和 PyTorch 2.3.1
- 当前项目是 Python 3.11.10 与 Torch 2.5.1
- 这不是本轮确认的根因, 但如果后续还有新的编译/ABI 错误, 这是最值得优先回看的兼容性风险

## [2026-03-26 08:45:50] [Session ID: 24cc3783-4a2b-4794-84b7-d2d4b7e7c6b6] 笔记: Blackwell 运行时边界与迁移成本评估

## 来源

### 来源1: 当前项目环境里的动态运行验证

- 验证命令:
  - `direnv exec . pixi run python -c "import torch; x = torch.tensor([1.0], device='cuda'); y = x + 1; print(y.tolist())"`
- 关键输出:
  - PyTorch warning 明确写出当前 wheel 仅支持到 `sm_90`
  - 本机 GPU 为 `NVIDIA RTX PRO 6000 Blackwell Server Edition`
  - 实际报错: `RuntimeError: CUDA error: no kernel image is available for execution on the device`
- 结论:
  - 当前项目环境在本机 Blackwell GPU 上不是“有 warning 但能跑”, 而是最小 CUDA 张量实验直接失败

### 来源2: PyTorch 官方 `PyTorch 2.7` 发布说明

- 链接: https://pytorch.org/blog/pytorch-2-7/
- 关键要点:
  - 官方把 Blackwell 支持写进 `PyTorch 2.7`
  - 同时点名 `CUDA 12.8` 预编译 wheel
  - 官方给出的安装口径是 `pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/cu128`
- 结论:
  - 从官方口径看, Blackwell 不是 `2.5.1+cu118` 这条线的目标平台
  - 如果要让本机 GPU 真正跑起来, 需要进入 `2.7+/cu128` 及以上的版本线

### 来源3: PyTorch 官方历史安装页

- 链接: https://pytorch.org/get-started/previous-versions/
- 关键要点:
  - `v2.7.0` 与 `v2.7.1` 都提供 `cu128` wheel
  - 更高版本 `2.8/2.9/2.10` 也继续提供 `cu128`
- 结论:
  - Blackwell 所需的官方 wheel 线是连续存在的, 不是某个临时 nightly

### 来源4: `xformers v0.0.28.post3` 官方 README

- 链接: https://raw.githubusercontent.com/facebookresearch/xformers/v0.0.28.post3/README.md
- 关键要点:
  - 该版本稳定安装口径仍要求 `PyTorch 2.5.1`
  - 对应的 pip wheel 线是 `cu118/cu121/cu124`
  - 若要配别的 PyTorch 版本, 官方建议从 source 安装
- 结论:
  - 项目当前 pin 的 `xformers` 与 `torch 2.5.1` 是同一代栈
  - 一旦迁移到 Blackwell 支持线, `xformers` 也要跟着改

### 来源5: `xformers main` 官方 README

- 链接: https://raw.githubusercontent.com/facebookresearch/xformers/main/README.md
- 关键要点:
  - 当前稳定安装口径已经要求 `PyTorch 2.10.0`
  - 提供 `cu126/cu128/cu130`
  - 若使用别的 PyTorch 版本, 仍建议 source build
- 结论:
  - `xformers` 上游主线在继续前进
  - 这进一步说明“把项目从 `2.5.1` 拉到 Blackwell 线”会进入依赖栈重配, 不是原地小修

### 来源6: `pytorch3d v0.7.9` 官方 INSTALL

- 链接: https://raw.githubusercontent.com/facebookresearch/pytorch3d/v0.7.9/INSTALL.md
- 关键要点:
  - 即使是 `v0.7.9`, 官方列出的支持矩阵仍只到 `PyTorch 2.4.1`
- 结论:
  - `PyTorch3D` 是当前迁移里最硬的上游约束
  - 若项目要上 Blackwell 支持线, `pytorch3d` 需要单独评估: 保留并打补丁、升级到未官方声明支持的组合, 或替换掉

### 来源7: 项目代码与依赖使用面

- 验证命令:
  - `rg -n 'pytorch3d' .`
  - `rg -n 'xformers' .`
- 关键发现:
  - 项目直接 pin 了 `pytorch3d = { rev = "v0.7.7" }`
  - 项目直接 pin 了 `xformers = { rev = "v0.0.28.post3" }`
  - 本地还带 `submodules/xformers`
  - `submodules/UniDepth/unidepth/ops/knn/src/knn.h` 引入了 `pytorch3d_cutils.h`
- 结论:
  - 这不是“删一个 pip 包就完”的依赖关系
  - `unidepth` 本身也已经和 `pytorch3d` 的原生部分发生耦合

### 来源8: 独立临时探针

- 探针动作:
  - 在 `/tmp/ff-blackwell-probe.Rl4Sui` 创建独立 venv
  - 启动 `pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128`
- 动态现象:
  - 除了主 `torch` wheel 外, 还连续拉取多份大型 `cu12` 运行时依赖
  - 在确认“这是整套 CUDA 12.8 运行时切换”之后, 主动停止下载
- 结论:
  - 这次适配不是轻量验证
  - 即使不碰项目代码, 光最小 Blackwell 探针也会引出整套新运行时栈

## 综合发现

### 现象

- `pixi install` 已成功
- 关键包导入也已通过
- 但当前 `torch 2.5.1+cu118` 在本机 `sm_120` GPU 上无法完成最小 CUDA 张量运算

### 已验证结论

- 安装问题已经解决
- 运行时问题也已经有动态证据, 不是猜测
- Blackwell 的官方支持入口在 `PyTorch 2.7 + cu128`
- 迁移到这条线会同时碰到:
  - `xformers` 版本线迁移
  - `pytorch3d` 官方支持上限
  - `unidepth` 对 `pytorch3d` 原生代码的耦合

### 当前结论

- “修复安装失败”这件事已经闭环
- “让项目在本机 Blackwell GPU 上跑起来”是下一个独立任务
- 这第二个任务的本质是版本栈迁移, 不是安装尾部的小补丁

## [2026-03-26 09:40:05] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 笔记: pytorch3d 升级 tag 与自编译路线的边界判断

## 来源

### 来源1: `pytorch3d` 官方 Releases / INSTALL / README

- 链接:
  - https://github.com/facebookresearch/pytorch3d/releases
  - https://raw.githubusercontent.com/facebookresearch/pytorch3d/v0.7.9/INSTALL.md
  - https://github.com/facebookresearch/pytorch3d
- 关键要点:
  - GitHub Releases 显示当前最新 release 是 `v0.7.9`
  - `v0.7.8` release note 明确写了 `This version supports PyTorch 2.1 to 2.4`
  - `v0.7.9` release note是 `Miscellaneous fixes and improvements`
  - `v0.7.9` 的 `INSTALL.md` 仍只列到 `PyTorch 2.4.1`
  - README 明确写了: `main branch: actively developed, without any guarantee`
- 结论:
  - 目前没有官方公开证据表明 `v0.7.9` 把支持线正式推进到 `PyTorch 2.5/2.7`
  - 直接切 `main` 不是“更稳的最新兼容版”, 而是“无兼容保证的开发线”

### 来源2: `v0.7.7..v0.7.9` 上游 diff

- 验证命令:
  - `git -C /tmp/pytorch3d-inspect diff --stat v0.7.7..v0.7.9 -- setup.py INSTALL.md .circleci/config.yml`
  - `git -C /tmp/pytorch3d-inspect diff v0.7.7..v0.7.9 -- setup.py INSTALL.md .circleci/config.yml`
- 关键发现:
  - `.circleci/config.yml` 新增了 `PyTorch 2.4.0/2.4.1`
  - `INSTALL.md` 从旧矩阵抬到 `2.4.1`
  - `setup.py` 只有小修:
    - `BuildExtension` 参数顺序修正
    - `install_requires` 去掉 `fvcore`
- 结论:
  - `v0.7.9` 相比 `v0.7.7` 更像“保守增量升级”
  - 这轮 diff 没看到能直接解释 `PyTorch 2.5` 或 Blackwell 兼容跃迁的证据

### 来源3: `main` 分支 `setup.py`

- 链接:
  - https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/setup.py
- 验证命令:
  - `curl -L --max-time 20 https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/setup.py | sed -n '60,120p'`
- 关键原文:
  - `# CUDA 13.0+ compatibility flags for pulsar.`
  - `if major >= 13:`
  - `--device-entity-has-hidden-visibility=false`
  - `-static-global-template-stub=false`
- 结论:
  - `main` 的确继续在向新 CUDA 工具链前进
  - 但这只能说明“源码有人在维护 CUDA 13 兼容补丁”
  - 不能把它推导成“官方已经支持 `torch 2.7+/cu128` 或 Blackwell”

### 来源4: 当前项目与 `UniDepth` 的真实使用面

- 验证命令:
  - `rg -n "pytorch3d|from pytorch3d|import pytorch3d" -S .`
  - `rg -n "pytorch3d" submodules/UniDepth -S`
  - `rg -n "unidepth\\.ops\\.knn|ops\\.knn|KNearestNeighbor|knn_points|knn_gather" submodules/UniDepth -S`
- 关键发现:
  - 主仓库几乎没有直接 `import pytorch3d`
  - `submodules/UniDepth` 内唯一直接出现 `pytorch3d` 的地方是:
    - `submodules/UniDepth/unidepth/ops/knn/src/knn.h`
    - 它只 `#include "utils/pytorch3d_cutils.h"`
  - `pytorch3d_cutils.h` 很薄, 只保留了几个 `CHECK_*` 宏
  - `UniDepth` 实际调用的是自己的 `unidepth.ops.knn`
- 结论:
  - 当前项目对 `pytorch3d` 的 Python 级运行时依赖比看上去浅
  - 后续除了“升级”与“自编译”, 还保留第三条路线:
    - 评估是否可以降耦甚至移除 `pytorch3d` 依赖

### 来源5: `v0.7.9` 在当前项目栈上的最小源码编译探针

- 验证命令:
  - `direnv exec . bash -lc 'cd /tmp/pytorch3d-inspect && rm -rf build pytorch3d/_C*.so && MAX_JOBS=8 "$PIXI_DEFAULT_ENV/bin/python" setup.py build_ext --inplace'`
- 动态现象:
  - 构建真实进入了 `nvcc` 与 `g++` 编译链
  - 没有一上来就在 `setup.py` 或 ABI 检查阶段崩掉
  - 但编译参数持续是:
    - `-gencode=arch=compute_90,code=compute_90`
    - `-gencode=arch=compute_90,code=sm_90`
  - 同时 PyTorch 继续发出 Blackwell 警告:
    - 当前安装只支持到 `sm_90`
  - 本轮在拿到足够动态证据后主动 `Ctrl-C` 停止, 不是编译自然失败
- 结论:
  - 在当前 `torch 2.5.1+cu118` 栈上, `v0.7.9` 的 source build 路径是活的
  - 但它依然受 Torch 的架构支持上限约束
  - 这条路能回答“可不可以自编译”
  - 不能回答“自编译后 Blackwell 就能跑”

### 来源6: 自编译时的 `ninja` 路径细节

- 验证命令:
  - `command -v ninja`
  - `ls .pixi/envs/default/bin/ninja`
  - `direnv exec . pixi run which ninja`
- 关键发现:
  - `ninja` 实际存在于 `.pixi/envs/default/bin/ninja`
  - 但前面的探针直接调用 `"$PIXI_DEFAULT_ENV/bin/python"` 时, `PATH` 没把 env bin 放进去, 所以 `BuildExtension` 误以为找不到 `ninja`
- 结论:
  - 如果后续真的要自编译, 应优先用:
    - `direnv exec . pixi run python setup.py build_ext --inplace`
    - 或 `direnv exec . pixi run pip install -e .`
  - 这样才能让 `ninja` 正常参与, 编译会快很多

## 综合发现

### 现象

- `v0.7.9` 是当前已发布的最新 tag
- `v0.7.9` 在当前项目栈上可以进入真实源码编译
- 但其编译目标架构仍跟随当前 Torch, 只到 `sm_90`

### 当前主假设

- `pytorch3d` 的“能不能自编译”与“能不能支持 Blackwell”是两层问题
- 当前真正限制 Blackwell 的, 主要不是 `pytorch3d v0.7.7` 这个 tag 本身
- 而是当前底座 `torch 2.5.1+cu118` 对 `sm_120` 不提供可执行目标

### 最强备选解释

- 也可能存在一种情况:
  - 切到 `torch 2.7+/cu128` 后
  - `pytorch3d v0.7.9` 或 `main` 仍然会因为头文件、ABI 或 API 演进而继续报错
- 这会把问题从“Torch 架构上限”推进成“未官方支持组合下的源码维护”

### 什么证据会推翻当前主假设

- 如果在 `torch 2.7+/cu128` 环境里, `pytorch3d v0.7.9` 或 `main` 仍然只生成 `sm_90`
- 或者在新 Torch 线里, 即使最小 CUDA 张量实验已通过, `pytorch3d` 还是在源码编译阶段稳定失败
- 那就说明“只要先换 Torch 再自编译”这个判断还不够, 需要进入更深的补丁维护

### 已验证结论

- 可以升级到 `v0.7.9`, 但它更像保守小升级, 不是 Blackwell 解决方案
- 可以自编译 `pytorch3d`, 当前栈下源码路径是活的
- 但“在当前 `torch 2.5.1+cu118` 栈上自编译 `pytorch3d`”并不能突破 `sm_90` 上限
- 若目标是本机 Blackwell 真正可跑, 下一步必须先进入 `torch 2.7+/cu128` 或更高版本线

## [2026-03-26 10:04:34] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 笔记: 用户提供的 Blackwell 已验证工作方案

## 来源

### 来源1: 用户提供的真实工作环境与命令

- 用户提供的已验证环境:
  - GPU: `NVIDIA RTX PRO 5000 Blackwell`
  - `sm_120`
  - Driver: `580.82.07`
  - `nvcc`: `CUDA 12.9 (12.9.41)`
  - `PyTorch`: `2.7.0+cu128`
  - `PyTorch3D`: `0.7.8` source build
- 用户提供的关键命令要点:
  - `python -m pip install cmake`
  - `python -m pip install ninja`
  - `export CC=/usr/bin/g++`
  - `export CXX=/usr/bin/g++`
  - `export CUDAHOSTCXX=/usr/bin/g++`
  - `export CUDA_HOME=/usr/local/cuda-12.9`
  - `export TORCH_CUDA_ARCH_LIST="12.0"`
  - `python -m pip install -v --no-build-isolation "git+https://github.com/facebookresearch/pytorch3d.git@stable"`
- 结论:
  - 这不是理论建议, 而是一条已经在 Blackwell `sm_120` 上跑通过的实战路线
  - 其中最有信息量的变量是:
    - `TORCH_CUDA_ARCH_LIST="12.0"`
    - 系统 CUDA 12.8+
    - `PyTorch 2.7 + cu128`
    - `PyTorch3D stable` source build

### 来源2: 本机系统条件核对

- 验证命令:
  - `ls -ld /usr/local/cuda*`
  - `for p in /usr/local/cuda /usr/local/cuda-12.8 /usr/local/cuda-12.9; do ...; done`
  - `nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv,noheader`
- 关键输出:
  - `/usr/local/cuda -> CUDA 12.8`
  - `/usr/local/cuda-12.8` 存在
  - 没有 `/usr/local/cuda-12.9`
  - GPU: `NVIDIA RTX PRO 6000 Blackwell Server Edition`
  - Driver: `580.95.05`
  - `compute_cap = 12.0`
- 结论:
  - 虽然本机不是用户的 `12.9`, 但属于 `12.8+`
  - 就当前已知证据看, 本机基础条件与用户路线是相容的

### 来源3: 用户提到的 `FoundationPose` PR `#369`

- 用户描述:
  - 该 PR 专门面向 RTX 50 / `sm_120` 兼容
  - 依赖 `PyTorch 2.7 / CUDA 12.8`
  - 含多项 build / runtime 修复
- 当前结论:
  - 这进一步支撑了“Blackwell 需要新 Torch 线 + source build 扩展”这个方向
  - 若后续需要细化 patch 点, 应继续回读该 PR 的具体改动

## 综合发现

### 现象

- 我们之前的独立探针只是在验证“新 Torch 底座”
- 用户给出了一条更贴近最终目标的完整工作方案
- 本机系统 CUDA / 驱动 / `sm_120` 条件与这条方案兼容

### 已验证结论

- 当前最有价值的下一步, 不再是继续泛化下载 `torch 2.7.1`
- 而是直接按用户方案做一个更贴近最终形态的独立探针:
  - 新 Torch
  - 系统 CUDA 12.8
  - `TORCH_CUDA_ARCH_LIST=12.0`
  - source build `PyTorch3D stable`

## [2026-03-26 10:39:48] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 笔记: Blackwell 探针中的 PyTorch3D 源码编译与最小 CUDA 验证

## 来源

### 来源1: 独立探针环境 `/tmp/ff-blackwell-probe`

- 关键安装命令:
  - `python -m pip install --index-url https://download.pytorch.org/whl/cu128 torch==2.7.0`
  - `python -m pip install --no-build-isolation "git+https://github.com/facebookresearch/pytorch3d.git@stable"`
- 关键环境变量:
  - `CC=/usr/bin/g++`
  - `CXX=/usr/bin/g++`
  - `CUDAHOSTCXX=/usr/bin/g++`
  - `CUDA_HOME=/usr/local/cuda-12.8`
  - `TORCH_CUDA_ARCH_LIST=12.0`
  - `MAX_JOBS=8`
- 关键输出:
  - `Created wheel for pytorch3d: filename=pytorch3d-0.7.8-cp312-cp312-linux_x86_64.whl`
  - `Successfully installed ... pytorch3d-0.7.8`
- 结论:
  - `pytorch3d@stable` 在这条新底座上已经真实完成 source build, 不是停留在“进入编译链”阶段

### 来源2: 编译过程中的动态证据

- 关键进程参数:
  - `-gencode=arch=compute_120,code=sm_120`
  - `__CUDA_ARCH__=1200`
  - 最终进入 `_C.cpython-312-x86_64-linux-gnu.so` 的链接阶段
- 结论:
  - 这次不是像旧栈那样只编到 `sm_90`
  - 新组合已经真实在为 Blackwell `sm_120` 生成目标码并完成链接

### 来源3: 编译后导入与最小运行验证

- 验证命令:
  - `python -c "import torch; print('torch', torch.__version__, 'torch CUDA', torch.version.cuda)"`
  - `python -c "import pytorch3d; print('pytorch3d OK', pytorch3d.__version__)"`
  - `python -m pip install numpy`
  - 最小 CUDA KNN 脚本:
    - `import torch`
    - `from pytorch3d.ops import knn_points`
    - 在 `device='cuda'` 上构造两个小点云
    - 调 `knn_points(x, y, K=1)`
- 关键输出:
  - `torch 2.7.0+cu128 torch CUDA 12.8`
  - `pytorch3d OK 0.7.8`
  - `cuda_available True`
  - `device_capability (12, 0)`
  - `knn_idx [[[0], [0]]]`
  - `knn_dists [[[0.0], [1.0]]]`
- 结论:
  - 这条 Blackwell 探针已经完成了“编译成功 -> 导入成功 -> CUDA 算子真实运行成功”的闭环

## 综合发现

### 现象

- 新组合下, `pytorch3d` 已经能编、能装、能导入
- `pytorch3d.ops` 首次导入失败, 但报错是 `ModuleNotFoundError: No module named 'numpy'`

### 当前主假设

- 首次 `ops` 导入失败不是 `pytorch3d` 编译问题
- 而是因为这套最小探针环境里一开始只装了 `torch` 和构建工具, 没装 `numpy`

### 最强备选解释

- 除了 `numpy` 缺失之外, 还有可能存在更深一层的运行时动态库问题
- 例如 `pytorch3d._C` 直接导入时曾出现过 `ImportError: libc10.so: cannot open shared object file`

### 什么证据推翻了备选解释

- 在真实使用路径里先 `import torch`, 再 `from pytorch3d.ops import knn_points`, 并补装 `numpy` 之后:
  - 导入成功
  - CUDA KNN 调用成功
- 这说明前面的 `_C` 直导入报错不能直接当成“扩展损坏”结论

### 已验证结论

- `torch 2.7.0+cu128 + pytorch3d 0.7.8 source build` 已在本机 Blackwell `sm_120` 上完成闭环验证
- 探针层面已经足够支撑后续项目级迁移评估
- 但项目主环境仍未迁到这条版本线, 不能把探针成功等价成“项目已修好”

## [2026-03-26 10:39:48] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 笔记: 项目级迁移边界, `xformers` 轮子验证与 `UniDepth` 依赖漂移

## 来源

### 来源1: 仓库内静态搜索

- 关键命令:
  - `rg -n "(import|from) pytorch3d|pytorch3d\\." ...`
  - `rg -n "(import|from) mmcv|mmcv\\." ...`
  - `rg -n "(import|from) xformers|xformers" ...`
- 关键发现:
  - 主仓库没有直接 `import pytorch3d`
  - 主仓库没有直接 `import mmcv`
  - `recon/depth_model.py` 使用的是 `UniDepthV2`
  - `UniDepth` 的 `metadinov2` 里多处 `xformers` 导入都带 `try/except` fallback
  - `UniDepth` 的 KNN 只依赖本地 `utils/pytorch3d_cutils.h`
- 结论:
  - `mmcv` 和 `pytorch3d` 至少不是当前仓库的直系 Python 运行依赖
  - `xformers` 更像性能和部分模块能力增强, 不是所有路径的绝对硬门槛

### 来源2: `xformers 0.0.30` 独立探针

- 验证命令:
  - `python -m pip install xformers==0.0.30 --index-url https://download.pytorch.org/whl/cu128`
  - `python -c "import xformers; print(...)" `
  - `python -c "from xformers.ops import memory_efficient_attention; print(...)" `
- 关键输出:
  - 安装的是官方 wheel: `xformers-0.0.30-cp312-cp312-manylinux_2_28_x86_64.whl`
  - `xformers 0.0.30`
  - `xformers ops OK memory_efficient_attention`
- 结论:
  - 在 `torch 2.7.0+cu128` 底座上, `xformers 0.0.30` 这条线是活的
  - 因此主项目没有必要继续扛着老的 git `v0.0.28.post3`

### 来源3: `UniDepth` 自身依赖声明与安装探针

- 文件:
  - `submodules/UniDepth/requirements.txt`
  - `submodules/UniDepth/pyproject.toml`
- 关键原文:
  - `torch>=2.4.0`
  - `torchvision>=0.19.0`
  - `torchaudio>=2.4.0`
  - `xformers>=0.0.26`
- 动态验证:
  - 在 `torch 2.7.0+cu128` 探针里执行 `pip install -e submodules/UniDepth --extra-index-url https://download.pytorch.org/whl/cu128`
  - 安装过程中它开始尝试拉:
    - `torch-2.11.0+cu128`
    - `torchvision-0.26.0+cu128`
    - `torchaudio-2.11.0+cu128`
    - `nvidia-cudnn-cu12-9.19.0.56`
- 结论:
  - `UniDepth` 自己的宽松依赖在新源上会把整套 Torch 栈继续向前漂
  - 如果项目顶层不主动 pin, solver 不会自动停在我们刚验证成功的 `2.7.0` 组合

### 来源4: `FoundationPose #369` 与上游版本线

- 关键来源:
  - `NVlabs/FoundationPose#369`
  - PyTorch 官方 previous versions 页面
  - xFormers 官方 releases
- 关键发现:
  - `FoundationPose #369` 明确把 Blackwell 兼容线拉到 `PyTorch 2.7 / CUDA 12.8`
  - PyTorch 官方 `2.7.0` 对应 `torchvision 0.22.0`
  - xFormers 官方 `0.0.30` 明确面向 `PyTorch 2.7.0`
- 结论:
  - 顶层 pin 到 `2.7.0 / 0.22.0 / 2.7.0 / 0.0.30 / cu128` 是有一手上游依据的

## 综合发现

### 现象

- 独立探针里, `torch 2.7.0+cu128`、`pytorch3d 0.7.8`、`xformers 0.0.30` 都已经分别跑通
- 但 `UniDepth` 自己的动态依赖仍会把 Torch 栈往 `2.11` 漂

### 当前主假设

- 项目级迁移真正需要的不是“再找一个能装上的包组合”
- 而是“把已经验证成功的组合显式钉死, 不让 path package 的宽松依赖带偏”

### 最强备选解释

- 即使顶层 pin 住版本, 后续仍可能在本地 CUDA 扩展编译阶段遇到旧 API 兼容问题
- 例如 `UniDepth` 的 `extract_patches` 还在用 `images.type().is_cuda()`

### 什么证据会推翻当前主假设

- 如果顶层 pin 住版本后, `pixi install` 仍然在没有版本漂移的前提下失败
- 且第一条真实错误来自本地扩展编译
- 那就说明下一层根因不在 solver, 而在扩展源码兼容性

### 当前已验证结论

- 项目级第一轮补丁应该至少包含:
  - `torch 2.7.0 + cu128`
  - `torchvision 0.22.0 + cu128`
  - `torchaudio 2.7.0 + cu128`
  - `xformers 0.0.30 + cu128`
  - `cuda-toolkit 12.8.1`
- `mmcv` 与 `pytorch3d` 从主依赖栈中移除, 是合理且有静态证据支撑的降变量动作

## [2026-03-27 21:44:03] [Session ID: 019d2f6a-705e-7ca1-97af-342c1bf4e24d] 笔记: 推送到 `raiscui/FreeFix` 的认证链路验证

## 来源

### 来源1: 当前仓库与目标仓库状态核对

- 命令: `git status --short --branch`
- 要点:
  - 当前工作区原本没有代码改动需要提交
  - 本地 `main` 相对 `origin/main` 超前 1 个提交

### 来源2: 目标仓库存在性验证

- 命令: `git ls-remote https://github.com/raiscui/FreeFix.git HEAD`
- 要点:
  - 目标仓库存在
  - 返回的远端 `HEAD` 为 `e0ec6a858a0ba644325d8ca4bbb2f7f8b74caad2`

### 来源3: HTTPS 推送失败证据

- 命令: `git push raiscui main:main`
- 要点:
  - 首次报错里出现 `Missing or invalid credentials`
  - 后续明确退出为 `remote: No anonymous write access.` 与 `fatal: Authentication failed for 'https://github.com/raiscui/FreeFix.git/'`

### 来源4: 本机认证工具与 SSH 验证

- 命令: `gh auth status`
- 要点:
  - `gh` 未安装, 无法走 GitHub CLI 登录链路
- 命令: `ssh -o BatchMode=yes -T git@github.com`
- 要点:
  - 返回 `Permission denied (publickey)`
- 命令: `ls -la ~/.ssh`
- 要点:
  - 当前只有 `known_hosts`, 没有可见私钥文件
- 命令: `printenv | rg '^(GIT_ASKPASS|SSH_AUTH_SOCK|SSH_AGENT_PID)='`
- 要点:
  - 仅看到 `GIT_ASKPASS` 指向 VS Code Server 的 `askpass.sh`
  - 没有看到可用的 `SSH_AUTH_SOCK`

## 综合发现

### 现象

- 目标仓库存在
- 当前本机 Git 身份配置为 `raiscui <vdcoolzi@gmail.com>`
- 但无论 HTTPS 还是 SSH, 当前会话都没有可用的 GitHub 写权限凭据

### 当前假设

- 主假设: 当前阻塞点是“本机没有可用的 GitHub 认证凭据”, 不是仓库地址错误, 也不是分支冲突
- 备选解释: 目标仓库对当前账号没有写权限
- 推翻主假设所需证据:
  - 提供可用 PAT / GitHub CLI 登录 / SSH key 后, 推送仍然被拒绝

## [2026-03-27 22:13:32] [Session ID: 019d2f6a-705e-7ca1-97af-342c1bf4e24d] 笔记: `GITHUB_TOKEN` 有效, 但 Git 需要显式 askpass 才能完成 HTTPS push

## 来源

### 来源1: Token 有效性验证

- 命令: `direnv exec . bash -lc 'curl ... https://api.github.com/user'`
- 要点:
  - 返回 `HTTP_200`
  - `login=raiscui`

### 来源2: 两轮失败与一轮成功的 Git 验证

- 失败验证1:
  - 现象: `direnv` 中可见 `GITHUB_TOKEN`, 但直接额外塞 HTTP auth header 后, Git 报 `Invalid username or token`
- 失败验证2:
  - 现象: 改成 `raiscui:GITHUB_TOKEN` 的 Basic header 后, Git 仍进入“读用户名”路径
- 成功验证:
  - 做法: 用 `direnv exec .` 注入 token, 临时生成 `askpass` 脚本, 对 Git 分别返回:
    - `Username -> raiscui`
    - `Password -> $GITHUB_TOKEN`
  - 关键输出:
    - `To https://github.com/raiscui/FreeFix.git`
    - `e0ec6a8..3fb6b57  main -> main`

### 来源3: 远端回读验证

- 命令: `git ls-remote https://github.com/raiscui/FreeFix.git refs/heads/main`
- 要点:
  - 返回 `3fb6b57b6007c36c5b0ea39e9832094727e2db52 refs/heads/main`

## 综合发现

### 现象

- `GITHUB_TOKEN` 本身有效
- 直接 shell 看不到 token, 但 `direnv` 子会话里能看到
- 真正卡住推送的不是权限本身, 而是 Git 在当前环境下如何拿到 HTTPS 用户名和密码

### 已验证结论

- 这次成功链路是:
  - `direnv exec .`
  - 临时 `askpass`
  - `git push raiscui main:main`
- 远端 `raiscui/FreeFix` 的 `main` 已经更新到本地 `HEAD`
