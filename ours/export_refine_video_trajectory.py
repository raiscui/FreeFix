from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from omegaconf import OmegaConf
from scipy.spatial.transform import Rotation


# =============================================================================
# FreeFix refine 视频镜头轨迹导出工具
# -----------------------------------------------------------------------------
# 这个脚本的目标不是“从 mp4 像素反推相机”。
# 它会回到 refine 真实使用的配置和数据集, 把逐帧相机参数按和视频一致的顺序导出。
# 这样拿到的 JSON 可以再次渲染、再次校验, 也更适合喂给外部动画工具链。
# =============================================================================


@dataclass(frozen=True)
class VideoMetadata:
    path: Path
    width: int
    height: int
    fps: float
    frame_count: int


@dataclass(frozen=True)
class ExportConfig:
    repo_root: Path
    exp_cfg_path: Path
    base_cfg_path: Path
    base_dir: Path
    exp_name: str
    data_dir: Path
    data_factor: int
    test_every: int
    partition_path: Path | None
    test_split: str
    test_trans: tuple[float, float, float]
    test_rots: tuple[float, float, float]
    refine_start_idx: int
    refine_end_idx: int
    load_step: int | None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="为 FreeFix 的 before/after_refine.mp4 导出逐帧镜头轨迹动画数据。"
    )
    parser.add_argument(
        "--video-path",
        type=Path,
        required=True,
        help="目标视频路径, 例如 outputs/.../after_refine.mp4。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 JSON 路径。默认写到视频同目录, 文件名追加 _camera_trajectory.json。",
    )
    parser.add_argument(
        "--exp-cfg",
        type=Path,
        default=None,
        help="显式指定 refine exp 配置。默认按视频目录自动在 exp_cfg/ 下查找。",
    )
    parser.add_argument(
        "--base-cfg",
        type=Path,
        default=Path("exp_cfg/base.yaml"),
        help="基础配置路径。默认 exp_cfg/base.yaml。",
    )
    parser.add_argument(
        "--exp-cfg-root",
        type=Path,
        default=Path("exp_cfg"),
        help="自动发现 exp cfg 时扫描的根目录。默认 exp_cfg。",
    )
    return parser


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_cli_path(path: Path, *, repo_dir: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if candidate.exists():
        return candidate.resolve()
    return (repo_dir / candidate).resolve()


def resolve_existing_path(raw_path: str | None, *, base_dir: Path, repo_dir: Path) -> Path | None:
    if raw_path in (None, ""):
        return None

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()

    # 先尊重当前工作目录下就能成立的相对路径。
    if candidate.exists():
        return candidate.resolve()

    repo_candidate = (repo_dir / candidate).resolve()
    if repo_candidate.exists():
        return repo_candidate

    return (base_dir / candidate).resolve()


def load_omegaconf_dict(path: Path) -> dict[str, Any]:
    loaded = OmegaConf.load(path)
    data = OmegaConf.to_container(loaded, resolve=True)
    if not isinstance(data, dict):
        raise TypeError(f"配置不是字典: {path}")
    return data


def load_refine_config(exp_cfg_path: Path, base_cfg_path: Path) -> dict[str, Any]:
    base_cfg = OmegaConf.load(base_cfg_path)
    exp_cfg = OmegaConf.load(exp_cfg_path)
    merged = OmegaConf.merge(base_cfg, exp_cfg)
    data = OmegaConf.to_container(merged, resolve=True)
    if not isinstance(data, dict):
        raise TypeError(f"合并后的 refine 配置不是字典: {exp_cfg_path}")
    return data


def discover_exp_cfg_path(
    *,
    video_path: Path,
    exp_cfg_root: Path,
    base_cfg_path: Path,
    repo_dir: Path,
) -> Path:
    output_dir = video_path.parent.resolve()
    exp_name = output_dir.name
    base_dir = output_dir.parent.resolve()

    if not exp_cfg_root.exists():
        raise FileNotFoundError(f"exp cfg 根目录不存在: {exp_cfg_root}")

    matches: list[Path] = []
    for candidate in sorted(exp_cfg_root.rglob("*.yaml")):
        if candidate.resolve() == base_cfg_path.resolve():
            continue

        try:
            merged_cfg = load_refine_config(candidate, base_cfg_path)
        except Exception:
            continue

        if merged_cfg.get("exp_name") != exp_name:
            continue

        candidate_base_dir = resolve_existing_path(
            str(merged_cfg.get("base_dir")),
            base_dir=repo_dir,
            repo_dir=repo_dir,
        )
        if candidate_base_dir is None:
            continue

        if candidate_base_dir.resolve() == base_dir:
            matches.append(candidate.resolve())

    if not matches:
        raise FileNotFoundError(
            "自动定位 exp cfg 失败。"
            f" video={video_path}, exp_name={exp_name}, base_dir={base_dir}"
        )
    if len(matches) > 1:
        raise ValueError(
            "自动定位 exp cfg 时发现多个候选, 请改用 --exp-cfg 显式指定: "
            + ", ".join(str(path) for path in matches)
        )
    return matches[0]


def load_export_config(args: argparse.Namespace) -> ExportConfig:
    repo_dir = repo_root()
    video_path = args.video_path.expanduser().resolve()
    base_cfg_path = resolve_cli_path(args.base_cfg, repo_dir=repo_dir)
    exp_cfg_root = resolve_cli_path(args.exp_cfg_root, repo_dir=repo_dir)

    exp_cfg_path = (
        resolve_cli_path(args.exp_cfg, repo_dir=repo_dir)
        if args.exp_cfg is not None
        else discover_exp_cfg_path(
            video_path=video_path,
            exp_cfg_root=exp_cfg_root,
            base_cfg_path=base_cfg_path,
            repo_dir=repo_dir,
        )
    )
    refine_cfg = load_refine_config(exp_cfg_path, base_cfg_path)

    base_dir = resolve_existing_path(
        str(refine_cfg.get("base_dir")),
        base_dir=repo_dir,
        repo_dir=repo_dir,
    )
    if base_dir is None:
        raise ValueError(f"refine 配置缺少 base_dir: {exp_cfg_path}")

    output_dir = (base_dir / str(refine_cfg["exp_name"])).resolve()
    if video_path.parent != output_dir:
        raise ValueError(
            "视频路径和 refine 配置不一致: "
            f"video_parent={video_path.parent}, expected_output_dir={output_dir}"
        )

    cfg_json_path = base_dir / "cfg.json"
    if not cfg_json_path.exists():
        raise FileNotFoundError(f"找不到训练 cfg.json: {cfg_json_path}")
    training_cfg = json.loads(cfg_json_path.read_text(encoding="utf-8"))

    data_dir = resolve_existing_path(
        training_cfg.get("data_dir"),
        base_dir=base_dir,
        repo_dir=repo_dir,
    )
    if data_dir is None:
        raise ValueError(f"cfg.json 缺少 data_dir: {cfg_json_path}")

    partition_path = resolve_existing_path(
        training_cfg.get("partition"),
        base_dir=base_dir,
        repo_dir=repo_dir,
    )

    return ExportConfig(
        repo_root=repo_dir,
        exp_cfg_path=exp_cfg_path,
        base_cfg_path=base_cfg_path,
        base_dir=base_dir,
        exp_name=str(refine_cfg["exp_name"]),
        data_dir=data_dir,
        data_factor=int(training_cfg.get("data_factor", 1)),
        test_every=int(training_cfg["test_every"]),
        partition_path=partition_path,
        test_split=str(refine_cfg.get("test_split", "test")),
        test_trans=tuple(float(x) for x in refine_cfg.get("test_trans", [0.0, 0.0, 0.0])),
        test_rots=tuple(float(x) for x in refine_cfg.get("test_rots", [0.0, 0.0, 0.0])),
        refine_start_idx=int(refine_cfg["refine_start_idx"]),
        refine_end_idx=int(refine_cfg["refine_end_idx"]),
        load_step=int(refine_cfg["load_step"]) if refine_cfg.get("load_step") is not None else None,
    )


def probe_video(video_path: Path) -> VideoMetadata:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"无法打开视频: {video_path}")

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()

    if width <= 0 or height <= 0:
        raise ValueError(f"视频分辨率无效: {video_path}")
    if fps <= 0:
        raise ValueError(f"视频 FPS 无效: {video_path}")
    if frame_count <= 0:
        raise ValueError(f"视频帧数无效: {video_path}")

    return VideoMetadata(
        path=video_path,
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
    )


def build_test_transform(
    test_trans: tuple[float, float, float],
    test_rots: tuple[float, float, float],
) -> np.ndarray:
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = Rotation.from_euler("xyz", test_rots, degrees=True).as_matrix()
    transform[:3, 3] = np.asarray(test_trans, dtype=np.float64)
    return transform


def build_frame_record(
    *,
    frame_index: int,
    dataset_index: int,
    parser_index: int,
    fps: float,
    image_name: str,
    image_path: str,
    image_size: tuple[int, int],
    intrinsics: np.ndarray,
    camera_to_world: np.ndarray,
) -> dict[str, Any]:
    rotation = camera_to_world[:3, :3]
    position = camera_to_world[:3, 3]

    # SciPy 默认导出 xyzw。
    # 这里显式改成项目里更常见的 wxyz, 方便后续和现有 FreeFix / gsplat 口径对齐。
    quat_xyzw = Rotation.from_matrix(rotation).as_quat()
    quat_wxyz = [float(quat_xyzw[3]), float(quat_xyzw[0]), float(quat_xyzw[1]), float(quat_xyzw[2])]

    return {
        "frame_index": frame_index,
        "time_sec": frame_index / fps,
        "dataset_index": dataset_index,
        "parser_index": parser_index,
        "image_name": image_name,
        "image_path": image_path,
        "image_size": [int(image_size[0]), int(image_size[1])],
        "position": position.astype(np.float64).tolist(),
        "rotation_matrix": rotation.astype(np.float64).tolist(),
        "quaternion_xyzw": quat_xyzw.astype(np.float64).tolist(),
        "quaternion_wxyz": quat_wxyz,
        "camera_to_world": camera_to_world.astype(np.float64).tolist(),
        "intrinsics": intrinsics.astype(np.float64).tolist(),
    }


def extract_step_from_path(path: Path) -> int:
    match = re.search(r"(\d+)", path.name)
    if match is None:
        return -1
    return int(match.group(1))


def find_render_traj_sidecar(base_dir: Path, frame_count: int, load_step: int | None) -> Path | None:
    sidecar_root = base_dir / "to_refine"
    if not sidecar_root.exists():
        return None

    candidates: list[tuple[int, str, Path]] = []
    for candidate in sidecar_root.glob("ckpt_*/refine_c2ws.npy"):
        try:
            shape = np.load(candidate, mmap_mode="r").shape
        except Exception:
            continue
        if len(shape) != 3 or shape[0] != frame_count:
            continue

        step = extract_step_from_path(candidate.parent)
        if load_step is None:
            distance = 0
        else:
            # 训练期导出的 `ckpt_34999` 和 refine 常写的 `load_step=35000`
            # 语义上往往只差一次 0-based / 1-based 计数。
            distance = min(abs(step - load_step), abs(step - (load_step - 1)))
        candidates.append((distance, candidate.as_posix(), candidate))

    if not candidates:
        return None

    candidates.sort()
    return candidates[0][2].resolve()


def compare_camera_trajectories(actual_c2ws: np.ndarray, sidecar_c2ws: np.ndarray) -> dict[str, Any]:
    if actual_c2ws.shape != sidecar_c2ws.shape:
        raise ValueError(
            "轨迹矩阵形状不一致: "
            f"actual={actual_c2ws.shape}, sidecar={sidecar_c2ws.shape}"
        )

    translation_diff = np.linalg.norm(
        actual_c2ws[:, :3, 3] - sidecar_c2ws[:, :3, 3],
        axis=1,
    )
    rotation_diff = np.linalg.norm(
        actual_c2ws[:, :3, :3] - sidecar_c2ws[:, :3, :3],
        axis=(1, 2),
    )

    return {
        "frame_count": int(actual_c2ws.shape[0]),
        "translation_diff_min": float(translation_diff.min()),
        "translation_diff_max": float(translation_diff.max()),
        "translation_diff_mean": float(translation_diff.mean()),
        "rotation_matrix_diff_min": float(rotation_diff.min()),
        "rotation_matrix_diff_max": float(rotation_diff.max()),
        "rotation_matrix_diff_mean": float(rotation_diff.mean()),
    }


def export_frames(config: ExportConfig, video: VideoMetadata) -> tuple[np.ndarray, list[dict[str, Any]]]:
    # 数据集和 refine 渲染的契约要保持一致。
    # 所以这里直接复用 `recon.datasets.colmap.Dataset` 的 sample 结构, 不额外猜路径和内参。
    from recon.datasets.colmap import Dataset, Parser

    parser = Parser(
        data_dir=str(config.data_dir),
        factor=config.data_factor,
        normalize=True,
        test_every=config.test_every,
    )
    dataset = Dataset(
        parser,
        split=config.test_split,
        patch_size=None,
        load_depths=False,
        partition_file=str(config.partition_path) if config.partition_path is not None else None,
    )

    dataset_indices = list(range(config.refine_start_idx, config.refine_end_idx))
    if len(dataset_indices) != video.frame_count:
        raise ValueError(
            "视频帧数和 refine 索引长度不一致: "
            f"frames={video.frame_count}, refine_range={len(dataset_indices)}"
        )

    test_transform = build_test_transform(config.test_trans, config.test_rots)
    actual_c2ws: list[np.ndarray] = []
    frame_records: list[dict[str, Any]] = []

    for frame_index, dataset_index in enumerate(dataset_indices):
        sample = dataset[dataset_index]
        parser_index = int(dataset.indices[dataset_index])
        camera_to_world = sample["camtoworld"].numpy().astype(np.float64) @ test_transform
        intrinsics = sample["K"].numpy().astype(np.float64)
        image_size = tuple(int(x) for x in sample["image_size"])

        actual_c2ws.append(camera_to_world)
        frame_records.append(
            build_frame_record(
                frame_index=frame_index,
                dataset_index=dataset_index,
                parser_index=parser_index,
                fps=video.fps,
                image_name=str(sample["image_name"]),
                image_path=str(sample["image_path"]),
                image_size=image_size,
                intrinsics=intrinsics,
                camera_to_world=camera_to_world,
            )
        )

    return np.stack(actual_c2ws, axis=0), frame_records


def build_payload(
    *,
    config: ExportConfig,
    video: VideoMetadata,
    output_path: Path,
    frame_records: list[dict[str, Any]],
    sidecar_comparison: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "exporter": "ours.export_refine_video_trajectory",
        "trajectory_source": "refiner_test_dataset",
        "video": {
            "path": str(video.path),
            "name": video.path.name,
            "width": video.width,
            "height": video.height,
            "fps": video.fps,
            "frame_count": video.frame_count,
        },
        "refine": {
            "exp_cfg_path": str(config.exp_cfg_path),
            "base_cfg_path": str(config.base_cfg_path),
            "base_dir": str(config.base_dir),
            "exp_name": config.exp_name,
            "data_dir": str(config.data_dir),
            "test_split": config.test_split,
            "test_trans": list(config.test_trans),
            "test_rots": list(config.test_rots),
            "refine_start_idx": config.refine_start_idx,
            "refine_end_idx": config.refine_end_idx,
            "load_step": config.load_step,
        },
        "output": {
            "path": str(output_path),
        },
        "frames": frame_records,
    }

    if sidecar_comparison is not None:
        payload["training_render_sidecar_comparison"] = sidecar_comparison

    return payload


def flatten_row_major(matrix: list[list[float]]) -> list[float]:
    return [float(value) for row in matrix for value in row]


def flatten_column_major(matrix: list[list[float]]) -> list[float]:
    array = np.asarray(matrix, dtype=np.float64)
    return array.T.reshape(-1).astype(float).tolist()


def build_unity_payload(
    *,
    source_payload: dict[str, Any],
    unity_output_path: Path,
) -> dict[str, Any]:
    unity_frames: list[dict[str, Any]] = []
    for frame in source_payload["frames"]:
        unity_frames.append(
            {
                "frameIndex": frame["frame_index"],
                "timeSec": frame["time_sec"],
                "datasetIndex": frame["dataset_index"],
                "parserIndex": frame["parser_index"],
                "imageName": frame["image_name"],
                "imagePath": frame["image_path"],
                "imageSize": frame["image_size"],
                "position": frame["position"],
                # Unity 的 Quaternion 构造顺序是 x, y, z, w。
                # 这里直接给出 `xyzw`, 避免在 Unity 侧再手工换位。
                "quaternionXyzw": frame["quaternion_xyzw"],
                "cameraToWorldRowMajor": flatten_row_major(frame["camera_to_world"]),
                "cameraToWorldColumnMajor": flatten_column_major(frame["camera_to_world"]),
                "intrinsicsRowMajor": flatten_row_major(frame["intrinsics"]),
            }
        )

    return {
        "schemaVersion": 1,
        "exporter": "ours.export_refine_video_trajectory",
        "sourceJson": source_payload["output"]["path"],
        "outputPath": str(unity_output_path),
        "coordinateSpace": "freefix_colmap_normalized",
        "axisConversionApplied": False,
        "note": (
            "This Unity payload keeps the original FreeFix/COLMAP-normalized world space. "
            "Use it when your Unity scene uses the same imported geometry space."
        ),
        "video": source_payload["video"],
        "refine": source_payload["refine"],
        "frames": unity_frames,
    }


def resolve_output_path(video_path: Path, output_path: Path | None) -> Path:
    if output_path is not None:
        resolved = output_path.expanduser().resolve()
    else:
        resolved = video_path.with_name(f"{video_path.stem}_camera_trajectory.json").resolve()

    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def resolve_unity_output_path(output_path: Path) -> Path:
    if output_path.stem.endswith("_camera_trajectory"):
        unity_name = output_path.stem.replace("_camera_trajectory", "_camera_trajectory_unity")
    else:
        unity_name = f"{output_path.stem}_unity"
    return output_path.with_name(f"{unity_name}{output_path.suffix}")


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    video_path = args.video_path.expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    config = load_export_config(args)
    video = probe_video(video_path)
    output_path = resolve_output_path(video_path, args.output)
    actual_c2ws, frame_records = export_frames(config, video)

    sidecar_path = find_render_traj_sidecar(
        config.base_dir,
        frame_count=video.frame_count,
        load_step=config.load_step,
    )
    sidecar_comparison = None
    if sidecar_path is not None:
        sidecar_c2ws = np.load(sidecar_path)
        sidecar_comparison = compare_camera_trajectories(actual_c2ws, sidecar_c2ws)
        sidecar_comparison["sidecar_path"] = str(sidecar_path)

    payload = build_payload(
        config=config,
        video=video,
        output_path=output_path,
        frame_records=frame_records,
        sidecar_comparison=sidecar_comparison,
    )
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    unity_output_path = resolve_unity_output_path(output_path)
    unity_payload = build_unity_payload(
        source_payload=payload,
        unity_output_path=unity_output_path,
    )
    unity_output_path.write_text(
        json.dumps(unity_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"video: {video.path}")
    print(f"exp_cfg: {config.exp_cfg_path}")
    print(f"output: {output_path}")
    print(f"unity_output: {unity_output_path}")
    print(f"frame_count: {video.frame_count}")
    print(f"trajectory_source: refiner_test_dataset")
    if sidecar_comparison is not None:
        print(f"sidecar_path: {sidecar_comparison['sidecar_path']}")
        print(
            "sidecar_translation_diff_mean: "
            f"{sidecar_comparison['translation_diff_mean']:.6f}"
        )
        print(
            "sidecar_rotation_diff_max: "
            f"{sidecar_comparison['rotation_matrix_diff_max']:.6f}"
        )


if __name__ == "__main__":
    main()
