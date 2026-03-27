from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from plyfile import PlyData

from recon.datasets.colmap import Parser as ColmapParser


# =============================================================================
# FastGS -> FreeFix 桥接工具
# -----------------------------------------------------------------------------
# 这个脚本把 FastGS 的训练产物转换成 FreeFix 能直接读取的 checkpoint。
# 目标是尽量复用现有两套格式, 不额外发明第三套中间协议。
#
# 当前支持两类输入:
# 1. FastGS `checkpoints/ckpt_*.pth`
# 2. FastGS `point_cloud/iteration_*/point_cloud.ply`
#
# 重要前提:
# - 这个桥接默认面向 FreeFix 的 `app_opt=false` 训练 / refine 线。
# - 也就是输出的 `splats` 字段固定是:
#   `means / opacities / quats / scales / sh0 / shN`
# - 如果目标 FreeFix 配置启用了 `app_opt=true`, 它期望的是
#   `features / colors` 参数化, 不适合直接吃这里的输出。
# =============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 FastGS checkpoint 或 point_cloud.ply 转成 FreeFix checkpoint。"
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
        "--data-dir",
        type=Path,
        default=None,
        help="目标 FreeFix 使用的数据目录, 例如 data/my4_fullcolmap。",
    )
    parser.add_argument(
        "--colmap-path",
        type=Path,
        default=None,
        help="目标 COLMAP 场景目录。是 `--data-dir` 的直观别名。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 checkpoint 路径。默认写到 source 同目录, 文件名追加 _freefix.pt。",
    )
    parser.add_argument(
        "--data-factor",
        type=int,
        default=1,
        help="传给 FreeFix COLMAP parser 的 factor。默认 1。",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=None,
        help="显式覆盖输出 checkpoint 的 step。默认从 source 文件名推断。",
    )
    parser.add_argument(
        "--data-type",
        choices=["colmap"],
        default="colmap",
        help="当前只支持 colmap。",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="关闭 FreeFix 坐标归一化。仅当你明确知道源坐标已经和 FreeFix 对齐时使用。",
    )
    args = parser.parse_args()
    args.source = resolve_source_arg(args)
    args.data_dir = resolve_data_dir_arg(args)
    return args


def resolve_source_arg(args: argparse.Namespace) -> Path:
    for candidate in (args.source, args.ckpt_path, args.ply_path):
        if candidate is not None:
            return candidate
    raise ValueError("必须提供 `--source`、`--ckpt-path` 或 `--ply-path` 其中之一。")


def resolve_data_dir_arg(args: argparse.Namespace) -> Path:
    for candidate in (args.data_dir, args.colmap_path):
        if candidate is not None:
            return candidate
    raise ValueError("必须提供 `--data-dir` 或 `--colmap-path` 其中之一。")


def load_torch_payload(path: Path):
    # PyTorch 2.6+ 默认 `weights_only=True` 会拒绝加载这类包含 tuple / dict /
    # 优化器状态的老式 checkpoint。这里显式关闭, 前提是我们信任本地源文件。
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def infer_step_from_path(path: Path) -> int:
    # 只看文件名和直接父目录, 避免把 `/tmp/tmp1234/...` 这类临时目录数字误当成 step。
    for candidate in [path.name, path.stem]:
        match = re.search(r"ckpt_(\d+)", candidate)
        if match is not None:
            return int(match.group(1))
        match = re.search(r"iteration_(\d+)", candidate)
        if match is not None:
            return int(match.group(1))
        match = re.search(r"(\d+)", candidate)
        if match is not None:
            return int(match.group(1))

    for candidate in [path.parent.name]:
        match = re.search(r"ckpt_(\d+)", candidate)
        if match is not None:
            return int(match.group(1))
        match = re.search(r"iteration_(\d+)", candidate)
        if match is not None:
            return int(match.group(1))
    return 0


def clone_float_tensor(value: torch.Tensor) -> torch.Tensor:
    return value.detach().cpu().float().clone()


def normalize_quat_wxyz(quats: torch.Tensor) -> torch.Tensor:
    return quats / torch.linalg.norm(quats, dim=-1, keepdim=True).clamp_min(1e-12)


def quat_to_rotmat_wxyz(quats: torch.Tensor) -> torch.Tensor:
    # 这里沿用 Graphdeco / gsplat 常见的 `wxyz` 顺序。
    quats = normalize_quat_wxyz(quats)
    w, x, y, z = quats.unbind(dim=-1)

    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    return torch.stack(
        [
            torch.stack([1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)], dim=-1),
            torch.stack([2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)], dim=-1),
            torch.stack([2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)], dim=-1),
        ],
        dim=-2,
    )


def rotmat_to_quat_wxyz(rotmats: torch.Tensor) -> torch.Tensor:
    # 采用稳定的分支写法, 直接把旋转矩阵还原成 `wxyz` 四元数。
    # 这里输出已经归一化, 后续可以直接作为 FreeFix checkpoint 里的 `quats`。
    flat = rotmats.reshape(-1, 3, 3)
    quats = []
    for matrix in flat:
        trace = float(matrix[0, 0] + matrix[1, 1] + matrix[2, 2])
        if trace > 0.0:
            s = math.sqrt(trace + 1.0) * 2.0
            w = 0.25 * s
            x = float(matrix[2, 1] - matrix[1, 2]) / s
            y = float(matrix[0, 2] - matrix[2, 0]) / s
            z = float(matrix[1, 0] - matrix[0, 1]) / s
        elif matrix[0, 0] > matrix[1, 1] and matrix[0, 0] > matrix[2, 2]:
            s = math.sqrt(float(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2])) * 2.0
            w = float(matrix[2, 1] - matrix[1, 2]) / s
            x = 0.25 * s
            y = float(matrix[0, 1] + matrix[1, 0]) / s
            z = float(matrix[0, 2] + matrix[2, 0]) / s
        elif matrix[1, 1] > matrix[2, 2]:
            s = math.sqrt(float(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2])) * 2.0
            w = float(matrix[0, 2] - matrix[2, 0]) / s
            x = float(matrix[0, 1] + matrix[1, 0]) / s
            y = 0.25 * s
            z = float(matrix[1, 2] + matrix[2, 1]) / s
        else:
            s = math.sqrt(float(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1])) * 2.0
            w = float(matrix[1, 0] - matrix[0, 1]) / s
            x = float(matrix[0, 2] + matrix[2, 0]) / s
            y = float(matrix[1, 2] + matrix[2, 1]) / s
            z = 0.25 * s

        quats.append([w, x, y, z])

    return normalize_quat_wxyz(torch.tensor(quats, dtype=rotmats.dtype)).reshape(
        *rotmats.shape[:-2], 4
    )


def extract_fastgs_checkpoint_splats(path: Path) -> tuple[dict[str, torch.Tensor], int]:
    payload = load_torch_payload(path)
    if not (isinstance(payload, tuple) and len(payload) == 2):
        raise TypeError(f"不是预期的 FastGS checkpoint 结构: {path}")

    model_args, iteration = payload
    if not (isinstance(model_args, tuple) and len(model_args) >= 7):
        raise TypeError(f"FastGS checkpoint model_args 结构异常: {path}")

    splats = {
        "means": clone_float_tensor(model_args[1]),
        "sh0": clone_float_tensor(model_args[2]),
        "shN": clone_float_tensor(model_args[3]),
        "scales": clone_float_tensor(model_args[4]),
        "quats": normalize_quat_wxyz(clone_float_tensor(model_args[5])),
        "opacities": clone_float_tensor(model_args[6]).reshape(-1),
    }
    return splats, int(iteration)


def read_ply_property_matrix(
    vertex,
    property_names: Iterable[str],
) -> np.ndarray:
    return np.stack([np.asarray(vertex[name], dtype=np.float32) for name in property_names], axis=1)


def extract_fastgs_ply_splats(path: Path) -> tuple[dict[str, torch.Tensor], int]:
    ply = PlyData.read(path)
    vertex = ply["vertex"]

    means = read_ply_property_matrix(vertex, ["x", "y", "z"])
    opacities = np.asarray(vertex["opacity"], dtype=np.float32)
    scales = read_ply_property_matrix(vertex, ["scale_0", "scale_1", "scale_2"])
    quats = read_ply_property_matrix(vertex, ["rot_0", "rot_1", "rot_2", "rot_3"])
    sh0 = read_ply_property_matrix(vertex, ["f_dc_0", "f_dc_1", "f_dc_2"]).reshape(-1, 1, 3)

    rest_names = sorted(
        [prop.name for prop in vertex.properties if prop.name.startswith("f_rest_")],
        key=lambda name: int(name.split("_")[-1]),
    )
    rest_flat = read_ply_property_matrix(vertex, rest_names)
    if rest_flat.shape[1] % 3 != 0:
        raise ValueError(f"PLY 的 f_rest 字段数不是 3 的倍数: {path}")
    shn = rest_flat.reshape(rest_flat.shape[0], 3, -1).transpose(0, 2, 1)

    splats = {
        "means": torch.from_numpy(means),
        "sh0": torch.from_numpy(sh0),
        "shN": torch.from_numpy(shn),
        "scales": torch.from_numpy(scales),
        "quats": normalize_quat_wxyz(torch.from_numpy(quats)),
        "opacities": torch.from_numpy(opacities),
    }
    return splats, infer_step_from_path(path)


def load_fastgs_source(path: Path) -> tuple[dict[str, torch.Tensor], int, str]:
    suffix = path.suffix.lower()
    if suffix == ".pth":
        splats, step = extract_fastgs_checkpoint_splats(path)
        return splats, step, "fastgs_checkpoint"
    if suffix == ".ply":
        splats, step = extract_fastgs_ply_splats(path)
        return splats, step, "fastgs_ply"
    raise ValueError(f"暂不支持的 FastGS 输入格式: {path}")


def resolve_colmap_transform(data_dir: Path, factor: int) -> np.ndarray:
    parser = ColmapParser(
        data_dir=str(data_dir),
        factor=factor,
        normalize=True,
        test_every=1,
    )
    return parser.transform


def decompose_similarity_transform(transform: np.ndarray) -> tuple[torch.Tensor, float, torch.Tensor]:
    matrix = torch.as_tensor(transform, dtype=torch.float32)
    linear = matrix[:3, :3]
    translation = matrix[:3, 3]

    # 用奇异值确认这真的是“统一尺度 * 旋转”, 避免把任意仿射硬套到高斯形状上。
    singular_values = torch.linalg.svdvals(linear)
    scale = float(singular_values.mean().item())
    if scale <= 0.0:
        raise ValueError(f"非法 similarity scale: {scale}")
    if not torch.allclose(
        singular_values,
        torch.full_like(singular_values, scale),
        atol=1e-5,
        rtol=1e-4,
    ):
        raise ValueError(f"变换不是统一尺度 similarity: singular_values={singular_values.tolist()}")

    rotation = linear / scale
    if float(torch.linalg.det(rotation)) <= 0.0:
        raise ValueError("变换里的旋转部分不是右手系正旋转。")
    return rotation, scale, translation


def transform_splats_to_freefix(
    splats: dict[str, torch.Tensor],
    transform: np.ndarray,
) -> dict[str, torch.Tensor]:
    rotation, scale_factor, translation = decompose_similarity_transform(transform)
    log_scale_delta = math.log(scale_factor)

    means = splats["means"] @ rotation.T * scale_factor + translation

    # 先把局部四元数转成旋转矩阵, 再左乘全局旋转, 最后写回四元数。
    local_rotmats = quat_to_rotmat_wxyz(splats["quats"])
    rotated_rotmats = rotation.unsqueeze(0) @ local_rotmats
    quats = rotmat_to_quat_wxyz(rotated_rotmats)
    scales = splats["scales"] + log_scale_delta

    return {
        "means": means.contiguous(),
        "opacities": splats["opacities"].reshape(-1).contiguous(),
        "quats": quats.contiguous(),
        "scales": scales.contiguous(),
        "sh0": splats["sh0"].contiguous(),
        "shN": splats["shN"].contiguous(),
    }


def default_output_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}_freefix.pt")


def save_freefix_checkpoint(
    output_path: Path,
    splats: dict[str, torch.Tensor],
    step: int,
    source: Path,
    source_format: str,
    normalize_enabled: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "step": step,
            "splats": splats,
            "source_path": str(source),
            "source_format": source_format,
            "normalized_for_freefix": normalize_enabled,
        },
        output_path,
    )


def main() -> None:
    args = parse_args()
    source_path = args.source.expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"FastGS 输入不存在: {source_path}")

    splats, inferred_step, source_format = load_fastgs_source(source_path)
    step = inferred_step if args.step is None else args.step

    normalize_enabled = not args.no_normalize
    if normalize_enabled:
        transform = resolve_colmap_transform(args.data_dir.expanduser().resolve(), args.data_factor)
        splats = transform_splats_to_freefix(splats, transform)
    else:
        splats = {
            key: value.contiguous()
            for key, value in splats.items()
        }

    output_path = default_output_path(source_path) if args.output is None else args.output.expanduser()
    save_freefix_checkpoint(
        output_path=output_path,
        splats=splats,
        step=step,
        source=source_path,
        source_format=source_format,
        normalize_enabled=normalize_enabled,
    )

    print(f"source: {source_path}")
    print(f"source_format: {source_format}")
    print(f"step: {step}")
    print(f"normalize_enabled: {normalize_enabled}")
    print(f"output: {output_path}")
    print(f"gaussian_count: {splats['means'].shape[0]}")


if __name__ == "__main__":
    main()
