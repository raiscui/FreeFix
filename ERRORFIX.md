## [2026-03-26 05:51:39] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 任务名称: mmcv 构建阶段缺少 pkg_resources

### 问题现象
- 执行 `pixi install` 时, `mmcv==2.2.0` 在 `setuptools.build_meta:__legacy__.build_wheel` 阶段失败
- 关键报错是 `ModuleNotFoundError: No module named 'pkg_resources'`

### 原因分析
- `mmcv-2.2.0/setup.py` 顶部直接 `from pkg_resources import ...`
- `pkg_resources` 来自 `setuptools`, 但 `setuptools>=82` 已移除该模块
- `pixi` 的 isolated build 不会自动继承项目主环境里钉住的 `setuptools==78.1.0`
- 因此即使项目运行环境声明了老版本 `setuptools`, `mmcv` 的 isolated build 仍可能落到不兼容的 `setuptools` 上

### 修复方法
- 在 [pixi.toml](/root/autodl-tmp/home/rais/FreeFix/pixi.toml) 的 `[pypi-options]` 下, 将 `mmcv` 加入 `no-build-isolation`
- 让 `mmcv` 构建时复用项目主环境中的 `setuptools==78.1.0`

### 验证结果
- `.pixi/envs/default/bin/python` 中:
  - `setuptools` 版本为 `78.1.0`
  - `pkg_resources` 可正常导入
- 在 `.pixi` 主环境中直接运行 `mmcv-2.2.0/setup.py --version`:
  - 成功输出 `2.2.0`
  - 未再出现 `ModuleNotFoundError: No module named 'pkg_resources'`
- 临时虚拟环境对照实验:
  - `setuptools==82.0.0` -> `ModuleNotFoundError No module named 'pkg_resources'`
  - `setuptools==78.1.0` -> `pkg_resources OK`

### 避坑提醒
- `uv/pixi` 报错提示中的缺失模块名, 不一定就是可直接安装的 PyPI 分发包名
- 这次 `python3 -m pip index versions pkg_resources` 明确返回无匹配分发, 不能把 `pkg_resources` 当成普通依赖直接加到清单里

## [2026-03-26 07:20:13] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 任务名称: pytorch3d 构建阶段的 CUDA version mismatch

### 问题现象
- `pytorch3d` 构建时报:
  - `The detected CUDA version (12.8) mismatches the version that was used to compile PyTorch (11.8)`
- 同轮日志还有 `CUB_HOME` warning

### 原因分析
- `torch.utils.cpp_extension` 会读取 `CUDA_HOME/bin/nvcc` 的版本
- 原始环境里它实际落到的是宿主机 `/usr/local/cuda`, 对应 12.x
- 第一次补 `cuda-toolkit = 11.8.0` 后, 又因为 `conda-forge` 优先级更高, 把大量 CUDA 子包解析成了 12.9
- 所以真正的根因是“两层错位”:
  - 一层是误用宿主机 CUDA
  - 另一层是 channel 顺序导致 toolkit 子包混装成 12.x

### 修复方法
- 在 [pixi.toml](/root/autodl-tmp/home/rais/FreeFix/pixi.toml) 中:
  - 增加 `cuda-toolkit = { version = "==11.8.0", channel = "nvidia/label/cuda-11.8.0" }`
  - 将 `channels` 顺序调整为 `["nvidia/label/cuda-11.8.0", "conda-forge"]`
- 在 [.envrc](/root/autodl-tmp/home/rais/FreeFix/.envrc) 中:
  - 固定 `CONDA_PREFIX`
  - 固定 `CUDA_HOME`
  - 固定 `CUDA_PATH`

### 验证结果
- 最小 pixi 探针工程中, `conda-meta` 已收敛到整套 `11.8.x` CUDA 子包
- 项目环境中, 调整 channel 优先级后, `conda-meta` 也开始收敛到 `11.8.x`
- 用缓存中的 `cuda-nvcc 11.8.89` 作为 `CUDA_HOME` 进行 PyTorch 动态验证:
  - `torch.version.cuda == 11.8`
  - `torch.utils.cpp_extension._check_cuda_version(...) == PASS`

### 避坑提醒
- 看到 `cuda-toolkit == 11.8.0` 不能直接认定环境里所有 CUDA 子包都是 11.8
- 必须同时检查:
  - `conda-meta` 里的真实子包版本
  - `CUDA_HOME/bin/nvcc --version`
- `CUB_HOME` warning 在这轮里不是第一顺位根因, 不要先被它带偏

## [2026-03-26 08:45:50] [Session ID: 24cc3783-4a2b-4794-84b7-d2d4b7e7c6b6] 任务名称: unidepth 与项目级 numpy 约束冲突

### 问题现象
- `pixi install` 在求解 PyPI 依赖阶段失败
- 关键报错是:
  - `unidepth==0.1 depends on numpy>=2.0.0`
  - 但项目声明的是 `numpy>=1.24.3,<2`

### 原因分析
- `submodules/UniDepth/requirements.txt` 明确写了 `numpy>=2.0.0`
- `submodules/UniDepth/pyproject.toml` 通过 dynamic dependencies 直接读取这份 `requirements.txt`
- 因此这不是求解器误判, 而是本地 path package 的真实依赖声明与项目级 pin 冲突

### 修复方法
- 在 [pixi.toml](/root/autodl-tmp/home/rais/FreeFix/pixi.toml) 中将 `numpy` 约束调整为 `>=2.0.0`
- 保持项目级约束与 `unidepth` 的真实声明一致

### 验证结果
- `pixi install --no-progress` 最终成功
- 项目环境中:
  - `numpy.__version__ == 2.4.3`
  - `import unidepth.models` 成功
- `unidepth` 已从可编辑路径暴露到项目环境

### 避坑提醒
- 遇到本地 `path/editable` 包时, 不要只看主项目 `pixi.toml`
- 还要继续追到该包自己的 `pyproject.toml` 和 `requirements.txt`
- 这类动态依赖声明会直接参与求解, 比主项目的“期望版本”更硬
