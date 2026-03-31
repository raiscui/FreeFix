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
# 当前支持三类用户视角下的输入:
# 1. FastGS `checkpoints/ckpt_*.pth`
# 2. fast-dropgs `chkpnt*.pth`
# 3. FastGS / 3DGS `point_cloud/iteration_*/point_cloud.ply`
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
        description="把 FastGS / fast-dropgs checkpoint 或 point_cloud.ply 转成 FreeFix checkpoint。"
    )
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument(
        "--source",
        type=Path,
        default=None,
        help="FastGS / fast-dropgs 输入文件, 支持 ckpt_*.pth、chkpnt*.pth 或 point_cloud.ply。",
    )
    source_group.add_argument(
        "--ckpt-path",
        type=Path,
        default=None,
        help="FastGS / fast-dropgs checkpoint 路径。是 `--source` 的直观别名。",
    )
    source_group.add_argument(
        "--ply-path",
        type=Path,
        default=None,
        help="FastGS / 3DGS point_cloud.ply 路径。是 `--source` 的直观别名。",
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
        match = re.search(r"chkpnt(\d+)", candidate)
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
        match = re.search(r"chkpnt(\d+)", candidate)
        if match is not None:
            return int(match.group(1))
        match = re.search(r"iteration_(\d+)", candidate)
        if match is not None:
            return int(match.group(1))
    return 0


def infer_checkpoint_source_format(path: Path) -> str:
    # -----------------------------------------------------------------------------
    # `fast-dropgs` 和当前 FastGS 的 checkpoint tuple 结构是同型的。
    # 这里区分的不是“能不能解析”, 而是“来源语义该怎么记”。
    #
    # 当前采用两层显式证据:
    # 1. 路径里直接出现 `fast-dropgs`
    # 2. 文件名符合上游真实保存格式 `chkpnt{iter}.pth`
    # -----------------------------------------------------------------------------
    lower_parts = [part.lower() for part in path.parts]
    if "fast-dropgs" in lower_parts:
        return "fastdropgs_checkpoint"
    if re.fullmatch(r"chkpnt\d+", path.stem.lower()) is not None:
        return "fastdropgs_checkpoint"
    return "fastgs_checkpoint"


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


def infer_sh_degree(num_bases: int) -> int:
    # -----------------------------------------------------------------------------
    # SH 系数是按完整平方数展开的:
    # - l=0 -> 1
    # - l<=1 -> 4
    # - l<=2 -> 9
    # - l<=3 -> 16
    # 这里把系数维度还原成 SH 阶数, 后面旋转块矩阵时会用到。
    # -----------------------------------------------------------------------------
    side = math.isqrt(num_bases)
    if side * side != num_bases:
        raise ValueError(f"SH basis 数量必须是完全平方数, got {num_bases}")
    return side - 1


def eval_real_sh_bases(basis_dim: int, dirs: torch.Tensor) -> torch.Tensor:
    # -----------------------------------------------------------------------------
    # 不手写另一套 SH basis 公式, 直接复用 gsplat 当前 renderer 实际使用的实现。
    # 这样 bridge 时旋转的 basis 和真正渲染时的 basis 保持同一份契约。
    # -----------------------------------------------------------------------------
    from gsplat.cuda._torch_impl import _eval_sh_bases_fast

    dirs = dirs / torch.linalg.norm(dirs, dim=-1, keepdim=True).clamp_min(1e-12)
    return _eval_sh_bases_fast(basis_dim, dirs)


def build_real_sh_rotation_matrix(
    rotation: torch.Tensor,
    sh_degree: int,
    sample_count: int = 128,
) -> torch.Tensor:
    # -----------------------------------------------------------------------------
    # 对 real SH 来说, 每个 l 阶都会在自身的 (2l+1) 维子空间里做正交旋转。
    # 这里不手抄 Wigner-D 闭式公式, 而是用 gsplat 的同一套 SH basis 数值拟合:
    #   Y_l(R d) = D_l(R) @ Y_l(d)
    # 再把每一阶的块矩阵拼成总的 block-diagonal 旋转矩阵。
    #
    # 这么做的好处是:
    # - 和当前 renderer 的 basis 顺序完全一致
    # - 对我们当前只需要支持的 l<=3 已经足够稳定
    # -----------------------------------------------------------------------------
    if sh_degree < 0:
        raise ValueError(f"非法 SH 阶数: {sh_degree}")

    rotation = torch.as_tensor(rotation, dtype=torch.float64)
    if rotation.shape != (3, 3):
        raise ValueError(f"rotation 必须是 3x3, got {tuple(rotation.shape)}")

    basis_dim = (sh_degree + 1) ** 2
    if basis_dim == 0:
        raise ValueError("basis_dim 不能为 0")

    generator = torch.Generator(device="cpu")
    generator.manual_seed(0)
    dirs = torch.randn(sample_count, 3, dtype=torch.float64, generator=generator)
    dirs = dirs / torch.linalg.norm(dirs, dim=-1, keepdim=True).clamp_min(1e-12)

    # `rotation` 是列向量语义下的主动旋转。
    # 当前代码里点坐标都是行向量, 因此这里要乘 `rotation.T`。
    rotated_dirs = dirs @ rotation.T

    bases = eval_real_sh_bases(basis_dim, dirs)
    rotated_bases = eval_real_sh_bases(basis_dim, rotated_dirs)

    matrix = torch.eye(basis_dim, dtype=torch.float64)
    for degree in range(1, sh_degree + 1):
        start = degree * degree
        end = (degree + 1) * (degree + 1)

        lhs = bases[:, start:end]
        rhs = rotated_bases[:, start:end]

        # 先最小二乘求出块矩阵, 再用 SVD 拉回最近的正交矩阵。
        # 这样数值误差不会把本应纯旋转的变换拖成带缩放 / 剪切的矩阵。
        solution = torch.linalg.lstsq(lhs, rhs).solution
        block = solution.T
        u, _, vh = torch.linalg.svd(block)
        matrix[start:end, start:end] = u @ vh

    return matrix


def rotate_real_sh_coefficients(
    coeffs: torch.Tensor,
    rotation: torch.Tensor,
) -> torch.Tensor:
    # -----------------------------------------------------------------------------
    # `coeffs` 形状约定:
    #   [..., K, C]
    # 其中:
    # - K 是 SH basis 数量
    # - C 是颜色通道(通常是 3)
    #
    # 对于颜色函数:
    #   f(d) = Y(d)^T c
    # 当全局方向坐标被旋转为 `R d` 后, 想保持同一真实外观, 系数必须同步做:
    #   c' = D(R) c
    # -----------------------------------------------------------------------------
    sh_degree = infer_sh_degree(coeffs.shape[-2])
    if sh_degree == 0:
        return coeffs.clone()

    rotation_matrix = build_real_sh_rotation_matrix(rotation, sh_degree).to(
        device=coeffs.device,
        dtype=coeffs.dtype,
    )
    return torch.einsum("ij,...jc->...ic", rotation_matrix, coeffs)


def extract_fastgs_checkpoint_splats(path: Path) -> tuple[dict[str, torch.Tensor], int]:
    payload = load_torch_payload(path)
    if not (isinstance(payload, tuple) and len(payload) == 2):
        raise TypeError(f"不是预期的 FastGS / fast-dropgs checkpoint 结构: {path}")

    model_args, iteration = payload
    if not (isinstance(model_args, tuple) and len(model_args) >= 7):
        raise TypeError(f"FastGS / fast-dropgs checkpoint model_args 结构异常: {path}")

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
        return splats, step, infer_checkpoint_source_format(path)
    if suffix == ".ply":
        splats, step = extract_fastgs_ply_splats(path)
        return splats, step, "fastgs_ply"
    raise ValueError(f"暂不支持的 FastGS / fast-dropgs 输入格式: {path}")


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

    # 高阶 SH 不是“纯颜色常数”, 它依赖观察方向。
    # 当整个场景坐标系被全局旋转后, 这些系数也必须在同一 real-SH basis 下同步旋转。
    colors = torch.cat([splats["sh0"], splats["shN"]], dim=1)
    rotated_colors = rotate_real_sh_coefficients(colors, rotation)
    sh0 = rotated_colors[:, :1, :]
    shN = rotated_colors[:, 1:, :]

    return {
        "means": means.contiguous(),
        "opacities": splats["opacities"].reshape(-1).contiguous(),
        "quats": quats.contiguous(),
        "scales": scales.contiguous(),
        "sh0": sh0.contiguous(),
        "shN": shN.contiguous(),
    }


def build_default_output_label(source: Path, source_format: str) -> str:
    # -----------------------------------------------------------------------------
    # 对 `chkpnt50000.pth` 这类过于通用的名字, 默认输出要带上父目录上下文,
    # 否则不同 run 很容易写出一堆同名 `_freefix.pt`。
    # -----------------------------------------------------------------------------
    stem = source.stem
    if source_format == "fastdropgs_checkpoint" and re.fullmatch(r"chkpnt\d+", stem.lower()):
        parent_name = source.parent.name
        if parent_name:
            return f"{parent_name}_{stem}"
    return stem


def default_output_path(source: Path, source_format: str) -> Path:
    label = build_default_output_label(source, source_format)
    return source.with_name(f"{label}_freefix.pt")


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
        raise FileNotFoundError(f"FastGS / fast-dropgs 输入不存在: {source_path}")

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

    output_path = (
        default_output_path(source_path, source_format)
        if args.output is None
        else args.output.expanduser()
    )
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
