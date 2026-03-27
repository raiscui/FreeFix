from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional


# =============================================================================
# 运行时环境引导
# -----------------------------------------------------------------------------
# 这个模块解决一个很具体的问题:
# 用户直接执行 `.pixi/envs/default/bin/python -m recon.trainer` 时,
# Python 解释器来自 pixi 环境, 但 shell 的 PATH / CUDA_HOME 并不会自动切到该环境。
# 再加上 pixi 的 CUDA toolkit 在当前仓库里不是平铺在环境根目录,
# 而是拆成了:
#   - `.pixi/envs/default/targets/x86_64-linux` 这一段真正的 toolkit 根
#   - `.pixi/envs/default/nvvm/bin` 这一段 `cicc` 所在目录
# 如果不把这两段都补齐, `gsplat` 会先误判“没有 CUDA”, 或者在 JIT 时继续因为
# `cuda_runtime_api.h` / `cicc` 缺失而失败。
# =============================================================================


def _prepend_env_paths(name: str, entries: Iterable[Path]) -> None:
    current_entries = [item for item in os.environ.get(name, "").split(os.pathsep) if item]
    known_entries = set(current_entries)
    new_entries = []

    for entry in entries:
        entry_str = str(entry)
        if not entry.exists() or entry_str in known_entries:
            continue
        known_entries.add(entry_str)
        new_entries.append(entry_str)

    if new_entries:
        os.environ[name] = os.pathsep.join(new_entries + current_entries)


def _find_pixi_cuda_toolkit_root(pixi_env: Path) -> Optional[Path]:
    targets_dir = pixi_env / "targets"
    if targets_dir.exists():
        for candidate in sorted(targets_dir.iterdir()):
            if not candidate.is_dir():
                continue
            if (candidate / "bin" / "nvcc").exists() and (candidate / "include" / "cuda_runtime_api.h").exists():
                return candidate

    # 兼容未来可能改回“环境根目录就是 toolkit 根”的布局。
    if (pixi_env / "bin" / "nvcc").exists() and (pixi_env / "include" / "cuda_runtime_api.h").exists():
        return pixi_env

    return None


def bootstrap_pixi_cuda_env() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    pixi_env = repo_root / ".pixi" / "envs" / "default"
    pixi_bin = pixi_env / "bin"
    cuda_toolkit_root = _find_pixi_cuda_toolkit_root(pixi_env)
    cuda_toolkit_bin = cuda_toolkit_root / "bin" if cuda_toolkit_root else None
    nvvm_bin = pixi_env / "nvvm" / "bin"

    if not pixi_env.exists() or not pixi_bin.exists():
        return

    # `cicc` 不在 toolkit_root/bin, 而在 `nvvm/bin`, 所以这里要把两段一起补进 PATH。
    # 同时保留 pixi 自己的 `bin`, 让 `ninja`、`python` 等同目录工具也能被找到。
    _prepend_env_paths(
        "PATH",
        [
            nvvm_bin,
            cuda_toolkit_bin if cuda_toolkit_bin is not None else Path("/__missing_cuda_toolkit_bin__"),
            pixi_bin,
        ],
    )

    # 只有在用户没有显式提供 CUDA_HOME/CUDA_PATH 时才兜底。
    # 这里必须指向“真实 toolkit 根”, 不能再指向 pixi 环境根目录。
    if cuda_toolkit_root is not None and not os.environ.get("CUDA_HOME"):
        os.environ["CUDA_HOME"] = str(cuda_toolkit_root)
    if cuda_toolkit_root is not None and not os.environ.get("CUDA_PATH"):
        os.environ["CUDA_PATH"] = str(cuda_toolkit_root)

    # 一些旧的 torch 扩展或 setup.py 仍然会读取 CONDA_PREFIX。
    if not os.environ.get("CONDA_PREFIX"):
        os.environ["CONDA_PREFIX"] = str(pixi_env)

    cub_home = None
    if cuda_toolkit_root is not None and (cuda_toolkit_root / "include" / "cub").exists():
        cub_home = cuda_toolkit_root / "include"
    elif (pixi_env / "include" / "cub").exists():
        cub_home = pixi_env / "include"

    if cub_home is not None and not os.environ.get("CUB_HOME"):
        os.environ["CUB_HOME"] = str(cub_home)
