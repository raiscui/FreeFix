from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import torch


# =============================================================================
# FreeFix 3DGS PLY 导出工具
# -----------------------------------------------------------------------------
# 这个脚本把训练得到的 checkpoint 还原成常见 3DGS PLY 格式。
# 输出字段顺序尽量对齐 Graphdeco / 常见查看器, 这样别的工具链更容易直接读取。
# =============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 FreeFix / gsplat checkpoint 导出成标准 3DGS PLY 文件。"
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=None,
        help="训练输出目录, 例如 outputs/my4。若提供, 会自动选择最新 ckpt。",
    )
    parser.add_argument(
        "--ckpt",
        type=Path,
        default=None,
        help="显式指定 checkpoint 文件, 例如 outputs/my4/ckpts/ckpt_29999.pt。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 ply 路径。默认写到 checkpoint 同级目录或 result_dir 根目录。",
    )
    return parser.parse_args()


def extract_step_from_name(path: Path) -> int:
    match = re.search(r"(\d+)", path.stem)
    if match is None:
        return -1
    return int(match.group(1))


def find_latest_checkpoint(result_dir: Path) -> Path:
    ckpt_dir = result_dir / "ckpts"
    if not ckpt_dir.exists():
        raise FileNotFoundError(f"找不到 checkpoint 目录: {ckpt_dir}")

    candidates = sorted(
        ckpt_dir.glob("ckpt_*.pt"),
        key=lambda path: (extract_step_from_name(path), path.name),
    )
    if not candidates:
        raise FileNotFoundError(f"在 {ckpt_dir} 下没有找到 ckpt_*.pt")
    return candidates[-1]


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.ckpt is None and args.result_dir is None:
        raise ValueError("必须至少提供 --ckpt 或 --result-dir 其中之一。")

    ckpt_path = args.ckpt
    if ckpt_path is None:
        ckpt_path = find_latest_checkpoint(args.result_dir)

    if not ckpt_path.exists():
        raise FileNotFoundError(f"checkpoint 不存在: {ckpt_path}")

    if args.output is not None:
        output_path = args.output
    elif args.result_dir is not None:
        step = extract_step_from_name(ckpt_path)
        output_path = args.result_dir / f"point_cloud_{step}.ply"
    else:
        output_path = ckpt_path.with_suffix(".ply")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return ckpt_path, output_path


def flatten_sh_features(sh_tensor: np.ndarray) -> np.ndarray:
    # 标准 3DGS PLY 会先把通道维换到前面, 再展开为一维属性。
    # 这样 `f_dc_0..2` 与 `f_rest_*` 的顺序会和常见实现保持一致。
    return np.transpose(sh_tensor, (0, 2, 1)).reshape(sh_tensor.shape[0], -1)


def to_numpy_float32(tensor: torch.Tensor) -> np.ndarray:
    return tensor.detach().cpu().numpy().astype(np.float32, copy=False)


def load_splats_from_checkpoint(ckpt_path: Path) -> dict[str, np.ndarray]:
    payload = torch.load(ckpt_path, map_location="cpu")
    if "splats" not in payload:
        raise KeyError(f"checkpoint 缺少 splats 字段: {ckpt_path}")

    splats = payload["splats"]
    required_keys = {"means", "opacities", "quats", "scales", "sh0", "shN"}
    missing = sorted(required_keys - set(splats.keys()))
    if missing:
        raise KeyError(f"checkpoint 缺少导出所需字段: {missing}")

    return {
        "means": to_numpy_float32(splats["means"]),
        "opacities": to_numpy_float32(splats["opacities"]).reshape(-1, 1),
        "quats": to_numpy_float32(splats["quats"]),
        "scales": to_numpy_float32(splats["scales"]),
        "sh0": flatten_sh_features(to_numpy_float32(splats["sh0"])),
        "shN": flatten_sh_features(to_numpy_float32(splats["shN"])),
    }


def build_property_names(num_rest: int) -> list[str]:
    property_names = [
        "x",
        "y",
        "z",
        "nx",
        "ny",
        "nz",
        "f_dc_0",
        "f_dc_1",
        "f_dc_2",
    ]
    property_names.extend(f"f_rest_{index}" for index in range(num_rest))
    property_names.extend(
        [
            "opacity",
            "scale_0",
            "scale_1",
            "scale_2",
            "rot_0",
            "rot_1",
            "rot_2",
            "rot_3",
        ]
    )
    return property_names


def build_ply_matrix(splats: dict[str, np.ndarray]) -> tuple[np.ndarray, list[str]]:
    means = splats["means"]
    num_gaussians = means.shape[0]
    normals = np.zeros((num_gaussians, 3), dtype=np.float32)

    parts = [
        means,
        normals,
        splats["sh0"],
        splats["shN"],
        splats["opacities"],
        splats["scales"],
        splats["quats"],
    ]
    matrix = np.concatenate(parts, axis=1).astype(np.float32, copy=False)
    property_names = build_property_names(num_rest=splats["shN"].shape[1])
    if matrix.shape[1] != len(property_names):
        raise ValueError(
            f"字段数不匹配: matrix={matrix.shape[1]}, properties={len(property_names)}"
        )
    return matrix, property_names


def build_header(num_gaussians: int, property_names: Iterable[str]) -> bytes:
    header_lines = [
        "ply",
        "format binary_little_endian 1.0",
        f"element vertex {num_gaussians}",
    ]
    header_lines.extend(f"property float {name}" for name in property_names)
    header_lines.append("end_header")
    return ("\n".join(header_lines) + "\n").encode("ascii")


def write_binary_ply(output_path: Path, matrix: np.ndarray, property_names: list[str]) -> None:
    dtype = np.dtype([(name, "<f4") for name in property_names])
    structured = np.empty(matrix.shape[0], dtype=dtype)
    for index, name in enumerate(property_names):
        structured[name] = matrix[:, index]

    with output_path.open("wb") as file:
        file.write(build_header(matrix.shape[0], property_names))
        structured.tofile(file)


def main() -> None:
    args = parse_args()
    ckpt_path, output_path = resolve_paths(args)
    splats = load_splats_from_checkpoint(ckpt_path)
    matrix, property_names = build_ply_matrix(splats)
    write_binary_ply(output_path, matrix, property_names)

    print(f"checkpoint: {ckpt_path}")
    print(f"output: {output_path}")
    print(f"gaussian_count: {matrix.shape[0]}")
    print(f"property_count: {matrix.shape[1]}")


if __name__ == "__main__":
    main()
