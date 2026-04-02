from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import roma
import torch
from torch import Tensor


def coerce_pose_jitter_triplet(
    raw_value: Optional[Sequence[float] | float],
    *,
    name: str,
    default: float = 0.0,
) -> Tuple[float, float, float]:
    """把 pose jitter 配置统一整理成 xyz 三元组。"""
    if raw_value is None:
        return (default, default, default)

    if isinstance(raw_value, (int, float)):
        scalar = float(raw_value)
        return (scalar, scalar, scalar)

    values = tuple(float(v) for v in raw_value)
    if len(values) != 3:
        raise ValueError(f"{name} 需要是长度为 3 的列表或单个标量, 当前得到: {raw_value}")
    return values


def build_local_camera_transform(
    trans_xyz: Sequence[float],
    rot_xyz_deg: Sequence[float],
    *,
    device: torch.device | str | None = None,
    dtype: torch.dtype = torch.float32,
) -> Tensor:
    """构造相机局部坐标系下的 4x4 扰动矩阵。"""
    transform = torch.eye(4, device=device, dtype=dtype)
    transform[:3, :3] = roma.euler_to_rotmat(
        "xyz",
        torch.tensor(tuple(rot_xyz_deg), device=device, dtype=dtype),
        degrees=True,
    )
    transform[:3, 3] = torch.tensor(tuple(trans_xyz), device=device, dtype=dtype)
    return transform


def sample_bounded_pose_jitter(
    trans_sigma: Sequence[float],
    trans_max: Sequence[float],
    rot_sigma_deg: Sequence[float],
    rot_max_deg: Sequence[float],
    trans_radius_max: Optional[float] = None,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """按高斯分布采样 pose jitter, 再用硬上限裁剪长尾样本。"""
    trans_sigma_arr = np.abs(np.asarray(tuple(trans_sigma), dtype=np.float64))
    trans_max_arr = np.abs(np.asarray(tuple(trans_max), dtype=np.float64))
    rot_sigma_arr = np.abs(np.asarray(tuple(rot_sigma_deg), dtype=np.float64))
    rot_max_arr = np.abs(np.asarray(tuple(rot_max_deg), dtype=np.float64))

    sampled_trans = np.random.normal(loc=0.0, scale=trans_sigma_arr)
    sampled_rot = np.random.normal(loc=0.0, scale=rot_sigma_arr)

    clipped_trans = np.clip(sampled_trans, -trans_max_arr, trans_max_arr)
    clipped_rot = np.clip(sampled_rot, -rot_max_arr, rot_max_arr)

    # ------------------------------------------------------------------
    # 某些场景下, 用户更希望 jitter 的“总位移半径”跟随相邻镜头间距。
    # 这里在保留逐轴高斯采样习惯的同时, 再附加一个球形半径上限。
    # 这样 direction 仍来自当前分布, 但不会跑出邻近镜头实际覆盖太远。
    # ------------------------------------------------------------------
    if trans_radius_max is not None:
        normalized_radius_max = float(max(0.0, trans_radius_max))
        trans_radius = float(np.linalg.norm(clipped_trans))
        if normalized_radius_max > 0.0 and trans_radius > normalized_radius_max:
            clipped_trans = clipped_trans * (normalized_radius_max / trans_radius)

    return (
        tuple(float(v) for v in clipped_trans),
        tuple(float(v) for v in clipped_rot),
    )


def compute_neighbor_average_radius(
    camtoworlds: Sequence[Tensor],
    *,
    source_index: int,
    neighbor_window: int,
) -> Optional[float]:
    """计算当前镜头与相邻镜头之间的平均平移半径。

    这里的“前后两个镜头”默认解释成:
    - `neighbor_window=1` 时, 取前一个和后一个
    - `neighbor_window=2` 时, 取前后各两个
    """
    normalized_window = max(0, int(neighbor_window))
    normalized_source_index = int(source_index)
    if normalized_window < 1:
        return None
    if normalized_source_index < 0 or normalized_source_index >= len(camtoworlds):
        return None

    base_c2w = camtoworlds[normalized_source_index]
    base_center = base_c2w[:3, 3]
    radii: List[float] = []

    for offset in range(1, normalized_window + 1):
        prev_index = normalized_source_index - offset
        next_index = normalized_source_index + offset

        if prev_index >= 0:
            prev_center = camtoworlds[prev_index][:3, 3]
            radii.append(float(torch.linalg.norm(prev_center - base_center).item()))
        if next_index < len(camtoworlds):
            next_center = camtoworlds[next_index][:3, 3]
            radii.append(float(torch.linalg.norm(next_center - base_center).item()))

    if not radii:
        return None
    return float(np.mean(radii))


def compute_alpha_coverage(alpha: Tensor, alpha_threshold: float) -> float:
    """统计 alpha 图里“有效覆盖区域”占整张图的比例。"""
    if alpha.numel() == 0:
        return 0.0
    coverage = (alpha > alpha_threshold).float().mean()
    return float(coverage.item())


def select_pose_jitter_candidate(
    *,
    base_c2w: Tensor,
    build_candidate_fn: Callable[[], Tuple[Tensor, Dict[str, Any]]],
    render_candidate_fn: Callable[[Tensor], Tuple[Tensor, List[Tensor], Tensor, Tensor]],
    alpha_threshold: float,
    min_alpha_coverage: float,
    max_attempts: int,
) -> Tuple[Tensor, Tuple[Tensor, List[Tensor], Tensor, Tensor], Dict[str, Any]]:
    """从多个 jitter 候选里挑出安全视角, 否则回退到 base camera。"""

    # ------------------------------------------------------------------
    # 这里故意把每次采样都记进 attempt_logs。
    # 后续无论命中还是 fallback, 上层都能把这批证据直接落到 jsonl。
    # ------------------------------------------------------------------
    attempt_logs: List[Dict[str, Any]] = []
    total_attempts = max(1, int(max_attempts))

    for attempt_index in range(total_attempts):
        candidate_c2w, jitter_meta = build_candidate_fn()
        render_result = render_candidate_fn(candidate_c2w)
        alpha_coverage = compute_alpha_coverage(render_result[2], alpha_threshold)
        accepted = alpha_coverage >= min_alpha_coverage

        attempt_log = {
            "attempt_index": attempt_index + 1,
            "pose_jitter_trans": list(jitter_meta["pose_jitter_trans"]),
            "pose_jitter_rots": list(jitter_meta["pose_jitter_rots"]),
            "alpha_coverage": alpha_coverage,
            "accepted": accepted,
        }
        attempt_logs.append(attempt_log)

        if accepted:
            return candidate_c2w, render_result, {
                "camera_mode": "pose_jitter",
                "attempt_count": attempt_index + 1,
                "accepted_attempt_index": attempt_index + 1,
                "used_fallback": False,
                "fallback_reason": None,
                "pose_jitter_trans": attempt_log["pose_jitter_trans"],
                "pose_jitter_rots": attempt_log["pose_jitter_rots"],
                "alpha_coverage": alpha_coverage,
                "attempts": attempt_logs,
            }

    fallback_render = render_candidate_fn(base_c2w)
    fallback_coverage = compute_alpha_coverage(fallback_render[2], alpha_threshold)
    return base_c2w, fallback_render, {
        "camera_mode": "pose_jitter",
        "attempt_count": total_attempts,
        "accepted_attempt_index": None,
        "used_fallback": True,
        "fallback_reason": "alpha_coverage_below_threshold",
        "pose_jitter_trans": [0.0, 0.0, 0.0],
        "pose_jitter_rots": [0.0, 0.0, 0.0],
        "alpha_coverage": fallback_coverage,
        "fallback_target": "base_camera",
        "attempts": attempt_logs,
    }
