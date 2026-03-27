from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


# =============================================================================
# COLMAP 模型文件读取
# -----------------------------------------------------------------------------
# 这里专门负责把标准 COLMAP 的 `cameras/images/points3D` 模型读成 Python 结构。
# 目标很明确:
# 1. 不依赖 pycolmap
# 2. 兼容 binary / text 两种模型格式
# 3. 输出尽量贴近旧的 SceneManager 使用方式, 方便现有训练代码平滑迁移
# =============================================================================

CAMERA_MODEL_IDS = {
    0: ("SIMPLE_PINHOLE", 3),
    1: ("PINHOLE", 4),
    2: ("SIMPLE_RADIAL", 4),
    3: ("RADIAL", 5),
    4: ("OPENCV", 8),
    5: ("OPENCV_FISHEYE", 8),
    6: ("FULL_OPENCV", 12),
    7: ("FOV", 5),
    8: ("SIMPLE_RADIAL_FISHEYE", 4),
    9: ("RADIAL_FISHEYE", 5),
    10: ("THIN_PRISM_FISHEYE", 12),
}

CAMERA_MODEL_NAMES = {
    name: (model_id, num_params) for model_id, (name, num_params) in CAMERA_MODEL_IDS.items()
}


@dataclass
class ColmapCamera:
    camera_id: int
    model_id: int
    model_name: str
    width: int
    height: int
    params: np.ndarray

    @property
    def camera_type(self) -> str:
        return self.model_name

    @property
    def fx(self) -> float:
        # 常见 pinhole 家族都能归一到 fx / fy / cx / cy 这套接口。
        if self.model_name in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL", "SIMPLE_RADIAL_FISHEYE", "RADIAL_FISHEYE"}:
            return float(self.params[0])
        if self.model_name in {"PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV", "FOV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[0])
        raise ValueError(f"暂不支持的相机模型: {self.model_name}")

    @property
    def fy(self) -> float:
        if self.model_name in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL", "SIMPLE_RADIAL_FISHEYE", "RADIAL_FISHEYE"}:
            return float(self.params[0])
        if self.model_name in {"PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV", "FOV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[1])
        raise ValueError(f"暂不支持的相机模型: {self.model_name}")

    @property
    def cx(self) -> float:
        if self.model_name in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL", "SIMPLE_RADIAL_FISHEYE", "RADIAL_FISHEYE"}:
            return float(self.params[1])
        if self.model_name in {"PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV", "FOV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[2])
        raise ValueError(f"暂不支持的相机模型: {self.model_name}")

    @property
    def cy(self) -> float:
        if self.model_name in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL", "SIMPLE_RADIAL_FISHEYE", "RADIAL_FISHEYE"}:
            return float(self.params[2])
        if self.model_name in {"PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV", "FOV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[3])
        raise ValueError(f"暂不支持的相机模型: {self.model_name}")

    @property
    def k1(self) -> float:
        if self.model_name == "SIMPLE_RADIAL":
            return float(self.params[3])
        if self.model_name in {"RADIAL", "OPENCV", "OPENCV_FISHEYE", "RADIAL_FISHEYE"}:
            return float(self.params[4])
        if self.model_name in {"FULL_OPENCV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[4])
        return 0.0

    @property
    def k2(self) -> float:
        if self.model_name == "RADIAL":
            return float(self.params[4])
        if self.model_name in {"OPENCV", "OPENCV_FISHEYE", "RADIAL_FISHEYE"}:
            return float(self.params[5])
        if self.model_name in {"FULL_OPENCV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[5])
        return 0.0

    @property
    def p1(self) -> float:
        if self.model_name in {"OPENCV", "FULL_OPENCV"}:
            return float(self.params[6])
        return 0.0

    @property
    def p2(self) -> float:
        if self.model_name in {"OPENCV", "FULL_OPENCV"}:
            return float(self.params[7])
        return 0.0

    @property
    def k3(self) -> float:
        if self.model_name == "OPENCV_FISHEYE":
            return float(self.params[6])
        if self.model_name in {"FULL_OPENCV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[8])
        return 0.0

    @property
    def k4(self) -> float:
        if self.model_name == "OPENCV_FISHEYE":
            return float(self.params[7])
        if self.model_name in {"FULL_OPENCV", "THIN_PRISM_FISHEYE"}:
            return float(self.params[9])
        return 0.0


@dataclass
class ColmapImage:
    image_id: int
    qvec: np.ndarray
    tvec: np.ndarray
    camera_id: int
    name: str

    def R(self) -> np.ndarray:
        # qvec 顺序是 [qw, qx, qy, qz]。
        # 这里直接转成旋转矩阵, 保持和 pycolmap 的调用口径一致。
        qw, qx, qy, qz = self.qvec
        return np.array(
            [
                [1 - 2 * qy * qy - 2 * qz * qz, 2 * qx * qy - 2 * qw * qz, 2 * qx * qz + 2 * qw * qy],
                [2 * qx * qy + 2 * qw * qz, 1 - 2 * qx * qx - 2 * qz * qz, 2 * qy * qz - 2 * qw * qx],
                [2 * qx * qz - 2 * qw * qy, 2 * qy * qz + 2 * qw * qx, 1 - 2 * qx * qx - 2 * qy * qy],
            ],
            dtype=np.float64,
        )


@dataclass
class ColmapPoint3D:
    point3d_id: int
    xyz: np.ndarray
    rgb: np.ndarray
    error: float
    track: list[tuple[int, int]]


class SimpleSceneManager:
    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.cameras: dict[int, ColmapCamera] = {}
        self.images: dict[int, ColmapImage] = {}
        self.name_to_image_id: dict[str, int] = {}
        self.points3D = np.empty((0, 3), dtype=np.float32)
        self.point3D_errors = np.empty((0,), dtype=np.float32)
        self.point3D_colors = np.empty((0, 3), dtype=np.uint8)
        self.point3D_id_to_images: dict[int, list[tuple[int, int]]] = {}
        self.point3D_id_to_point3D_idx: dict[int, int] = {}

    def load_cameras(self) -> None:
        self.cameras = read_cameras(self.model_dir)

    def load_images(self) -> None:
        self.images = read_images(self.model_dir)
        self.name_to_image_id = {
            image.name: image_id for image_id, image in self.images.items()
        }

    def load_points3D(self) -> None:
        points = read_points3d(self.model_dir)
        ordered_points = list(points.values())
        if not ordered_points:
            self.points3D = np.empty((0, 3), dtype=np.float32)
            self.point3D_errors = np.empty((0,), dtype=np.float32)
            self.point3D_colors = np.empty((0, 3), dtype=np.uint8)
            self.point3D_id_to_images = {}
            self.point3D_id_to_point3D_idx = {}
            return

        self.points3D = np.stack([point.xyz for point in ordered_points]).astype(np.float32)
        self.point3D_errors = np.array([point.error for point in ordered_points], dtype=np.float32)
        self.point3D_colors = np.stack([point.rgb for point in ordered_points]).astype(np.uint8)
        self.point3D_id_to_images = {
            point.point3d_id: point.track for point in ordered_points
        }
        self.point3D_id_to_point3D_idx = {
            point.point3d_id: index for index, point in enumerate(ordered_points)
        }


def _read_uint64(handle) -> int:
    return struct.unpack("<Q", handle.read(8))[0]


def _read_next_bytes(handle, num_bytes: int, fmt: str):
    data = handle.read(num_bytes)
    if len(data) != num_bytes:
        raise ValueError("读取 COLMAP 模型文件时遇到异常 EOF。")
    return struct.unpack(fmt, data)


def _find_model_file(model_dir: Path, basename: str) -> Path | None:
    binary_path = model_dir / f"{basename}.bin"
    if binary_path.exists():
        return binary_path
    text_path = model_dir / f"{basename}.txt"
    if text_path.exists():
        return text_path
    return None


def _read_cameras_binary(path: Path) -> dict[int, ColmapCamera]:
    cameras: dict[int, ColmapCamera] = {}
    with path.open("rb") as handle:
        num_cameras = _read_uint64(handle)
        for _ in range(num_cameras):
            camera_id, model_id, width, height = _read_next_bytes(handle, 24, "<iiQQ")
            model_name, num_params = CAMERA_MODEL_IDS[model_id]
            params = np.array(
                _read_next_bytes(handle, 8 * num_params, "<" + "d" * num_params),
                dtype=np.float64,
            )
            cameras[camera_id] = ColmapCamera(
                camera_id=camera_id,
                model_id=model_id,
                model_name=model_name,
                width=int(width),
                height=int(height),
                params=params,
            )
    return cameras


def _read_cameras_text(path: Path) -> dict[int, ColmapCamera]:
    cameras: dict[int, ColmapCamera] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        camera_id = int(fields[0])
        model_name = fields[1]
        model_id, _ = CAMERA_MODEL_NAMES[model_name]
        width = int(fields[2])
        height = int(fields[3])
        params = np.array([float(value) for value in fields[4:]], dtype=np.float64)
        cameras[camera_id] = ColmapCamera(
            camera_id=camera_id,
            model_id=model_id,
            model_name=model_name,
            width=width,
            height=height,
            params=params,
        )
    return cameras


def read_cameras(model_dir: str | Path) -> dict[int, ColmapCamera]:
    model_path = Path(model_dir)
    file_path = _find_model_file(model_path, "cameras")
    if file_path is None:
        raise FileNotFoundError(f"在 {model_path} 中找不到 cameras.bin 或 cameras.txt")
    if file_path.suffix == ".bin":
        return _read_cameras_binary(file_path)
    return _read_cameras_text(file_path)


def _read_images_binary(path: Path) -> dict[int, ColmapImage]:
    images: dict[int, ColmapImage] = {}
    with path.open("rb") as handle:
        num_images = _read_uint64(handle)
        for _ in range(num_images):
            fields = _read_next_bytes(handle, 64, "<idddddddi")
            image_id = int(fields[0])
            qvec = np.array(fields[1:5], dtype=np.float64)
            tvec = np.array(fields[5:8], dtype=np.float64)
            camera_id = int(fields[8])

            name_bytes = bytearray()
            while True:
                char = handle.read(1)
                if not char:
                    raise ValueError(f"读取 {path} 时在 image name 处提前结束。")
                if char == b"\x00":
                    break
                name_bytes.extend(char)
            name = name_bytes.decode("utf-8")

            num_points2d = _read_uint64(handle)
            # 这里只消费掉字节, 不在这里保存 2D 点列表。
            handle.seek(num_points2d * 24, 1)

            images[image_id] = ColmapImage(
                image_id=image_id,
                qvec=qvec,
                tvec=tvec,
                camera_id=camera_id,
                name=name,
            )
    return images


def _read_images_text(path: Path) -> dict[int, ColmapImage]:
    images: dict[int, ColmapImage] = {}
    lines = path.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("#"):
            continue

        fields = line.split(maxsplit=9)
        image_id = int(fields[0])
        qvec = np.array([float(value) for value in fields[1:5]], dtype=np.float64)
        tvec = np.array([float(value) for value in fields[5:8]], dtype=np.float64)
        camera_id = int(fields[8])
        name = fields[9]

        # images.txt 是两行一组, 第二行是 2D 点观测。
        # 这里训练侧不直接依赖这部分数据, 所以只把游标推进过去。
        if index < len(lines):
            index += 1

        images[image_id] = ColmapImage(
            image_id=image_id,
            qvec=qvec,
            tvec=tvec,
            camera_id=camera_id,
            name=name,
        )
    return images


def read_images(model_dir: str | Path) -> dict[int, ColmapImage]:
    model_path = Path(model_dir)
    file_path = _find_model_file(model_path, "images")
    if file_path is None:
        raise FileNotFoundError(f"在 {model_path} 中找不到 images.bin 或 images.txt")
    if file_path.suffix == ".bin":
        return _read_images_binary(file_path)
    return _read_images_text(file_path)


def _read_points3d_binary(path: Path) -> dict[int, ColmapPoint3D]:
    points: dict[int, ColmapPoint3D] = {}
    with path.open("rb") as handle:
        num_points = _read_uint64(handle)
        for _ in range(num_points):
            point3d_id = _read_next_bytes(handle, 8, "<Q")[0]
            xyz = np.array(_read_next_bytes(handle, 24, "<ddd"), dtype=np.float64)
            rgb = np.array(_read_next_bytes(handle, 3, "<BBB"), dtype=np.uint8)
            error = float(_read_next_bytes(handle, 8, "<d")[0])
            track_length = _read_uint64(handle)
            track_raw = _read_next_bytes(handle, 8 * track_length, "<" + "ii" * track_length)
            track = [
                (int(track_raw[index]), int(track_raw[index + 1]))
                for index in range(0, len(track_raw), 2)
            ]
            points[int(point3d_id)] = ColmapPoint3D(
                point3d_id=int(point3d_id),
                xyz=xyz,
                rgb=rgb,
                error=error,
                track=track,
            )
    return points


def _read_points3d_text(path: Path) -> dict[int, ColmapPoint3D]:
    points: dict[int, ColmapPoint3D] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        point3d_id = int(fields[0])
        xyz = np.array([float(value) for value in fields[1:4]], dtype=np.float64)
        rgb = np.array([int(value) for value in fields[4:7]], dtype=np.uint8)
        error = float(fields[7])
        track_values = [int(value) for value in fields[8:]]
        track = [
            (track_values[index], track_values[index + 1])
            for index in range(0, len(track_values), 2)
        ]
        points[point3d_id] = ColmapPoint3D(
            point3d_id=point3d_id,
            xyz=xyz,
            rgb=rgb,
            error=error,
            track=track,
        )
    return points


def read_points3d(model_dir: str | Path) -> dict[int, ColmapPoint3D]:
    model_path = Path(model_dir)
    file_path = _find_model_file(model_path, "points3D")
    if file_path is None:
        raise FileNotFoundError(f"在 {model_path} 中找不到 points3D.bin 或 points3D.txt")
    if file_path.suffix == ".bin":
        return _read_points3d_binary(file_path)
    return _read_points3d_text(file_path)


def load_registered_image_names(model_dir: str | Path) -> list[str]:
    # 这个辅助函数给导入脚本复用。
    # 它只关心“模型里到底注册了哪些图”, 不关心别的字段。
    images = read_images(model_dir)
    return [image.name for image in images.values()]
