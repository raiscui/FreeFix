from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


# =============================================================================
# FastGS -> FreeFix refine 一条命令入口
# -----------------------------------------------------------------------------
# 这个脚本只做 orchestration:
# 1. 先把 FastGS checkpoint / ply 导入成 FreeFix bridge ckpt
# 2. 再调用现有的 Flux / SDXL refine 入口
#
# 设计原则:
# - 不复制 bridge 逻辑
# - 不复制 refine 逻辑
# - 优先复用已经验证过的脚本, 这里只负责把两步串起来
# =============================================================================


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="一条命令完成 FastGS 导入并启动 FreeFix refine。"
    )
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument(
        "--source",
        type=Path,
        default=None,
        help="FastGS 输入文件, 支持 ckpt_*.pth 或 point_cloud.ply。",
    )
    source_group.add_argument(
        "--ckpt-path",
        type=Path,
        default=None,
        help="FastGS checkpoint 路径。是 `--source` 的直观别名。",
    )
    source_group.add_argument(
        "--ply-path",
        type=Path,
        default=None,
        help="FastGS point_cloud.ply 路径。是 `--source` 的直观别名。",
    )
    parser.add_argument(
        "--colmap-path",
        type=Path,
        required=True,
        help="目标 COLMAP 场景目录, refine 会继续使用这里的图片和相机信息。",
    )
    parser.add_argument(
        "--exp-cfg",
        type=Path,
        required=True,
        help="refine 实验配置, 例如 exp_cfg/my4/flux_shinkai_museum_v2.yaml",
    )
    parser.add_argument(
        "--base-cfg",
        type=Path,
        default=Path("exp_cfg/base.yaml"),
        help="refine 基础配置路径。默认 exp_cfg/base.yaml",
    )
    parser.add_argument(
        "--refine-backend",
        choices=["flux", "sdxl"],
        default="flux",
        help="选择 refine 后端。默认 flux。",
    )
    parser.add_argument(
        "--bridge-output",
        type=Path,
        default=None,
        help="bridge ckpt 输出路径。默认写到 outputs/fastgs_bridge/ 下。",
    )
    parser.add_argument(
        "--data-factor",
        type=int,
        default=1,
        help="传给 bridge 阶段 COLMAP parser 的 factor。默认 1。",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=None,
        help="显式覆盖 bridge ckpt 里的 step。默认从输入文件名推断。",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="关闭 bridge 阶段的 FreeFix 坐标归一化。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要执行的命令, 不真正运行。",
    )
    return parser


def resolve_source_arg(args: argparse.Namespace) -> Path:
    for candidate in (args.source, args.ckpt_path, args.ply_path):
        if candidate is not None:
            return candidate.expanduser().resolve()
    raise ValueError("必须提供 `--source`、`--ckpt-path` 或 `--ply-path` 其中之一。")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def choose_bridge_label(source_path: Path) -> str:
    # `ckpt_30000.pth` 这种文件名本身已经足够表达来源。
    if source_path.stem != "point_cloud":
        return source_path.stem

    # `point_cloud.ply` 太通用, 默认带上迭代目录避免不同 run 混淆。
    parent_name = source_path.parent.name
    if parent_name:
        return f"{parent_name}_{source_path.stem}"
    return source_path.stem


def default_bridge_output_path(source_path: Path) -> Path:
    output_dir = repo_root() / "outputs" / "fastgs_bridge"
    return output_dir / f"{choose_bridge_label(source_path)}_freefix.pt"


def get_refine_module_name(backend: str) -> str:
    if backend == "flux":
        return "ours.refine_by_flux"
    if backend == "sdxl":
        return "ours.refine_by_sdxl"
    raise ValueError(f"不支持的 refine backend: {backend}")


def build_bridge_command(args: argparse.Namespace, source_path: Path, bridge_output_path: Path) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "recon.import_fastgs",
        "--colmap-path",
        str(args.colmap_path.expanduser().resolve()),
        "--output",
        str(bridge_output_path),
        "--data-factor",
        str(args.data_factor),
    ]

    if source_path.suffix.lower() == ".ply":
        command.extend(["--ply-path", str(source_path)])
    else:
        command.extend(["--ckpt-path", str(source_path)])

    if args.step is not None:
        command.extend(["--step", str(args.step)])
    if args.no_normalize:
        command.append("--no-normalize")
    return command


def build_refine_command(args: argparse.Namespace, bridge_output_path: Path) -> list[str]:
    command = [
        sys.executable,
        "-m",
        get_refine_module_name(args.refine_backend),
        "--exp_cfg",
        str(args.exp_cfg.expanduser().resolve()),
        "--base_cfg",
        str(args.base_cfg.expanduser().resolve()),
        "--colmap-path",
        str(args.colmap_path.expanduser().resolve()),
        "--ckpt-path",
        str(bridge_output_path),
    ]
    return command


def print_command(command: list[str]) -> None:
    print(f"+ {shlex.join(command)}")


def run_command(command: list[str]) -> None:
    print_command(command)
    try:
        subprocess.run(command, check=True, cwd=repo_root())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc


def run_pipeline(args: argparse.Namespace) -> tuple[Path, list[list[str]]]:
    source_path = resolve_source_arg(args)
    bridge_output_path = (
        args.bridge_output.expanduser().resolve()
        if args.bridge_output is not None
        else default_bridge_output_path(source_path)
    )

    commands = [
        build_bridge_command(args, source_path, bridge_output_path),
        build_refine_command(args, bridge_output_path),
    ]

    if args.dry_run:
        for command in commands:
            print_command(command)
        return bridge_output_path, commands

    for command in commands:
        run_command(command)
    return bridge_output_path, commands


def main() -> None:
    args = build_arg_parser().parse_args()
    bridge_output_path, _ = run_pipeline(args)
    print(f"bridge_output: {bridge_output_path}")


if __name__ == "__main__":
    main()
