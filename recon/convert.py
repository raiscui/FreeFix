#
# Copyright (C) 2023, Inria
# GRAPHDECO research group, https://team.inria.fr/graphdeco
# All rights reserved.
#
# This software is free for non-commercial, research and evaluation use
# under the terms of the LICENSE.md file.
#
# For inquiries contact  george.drettakis@team.inria.fr
#

import logging
import os
import shutil
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

try:
    from recon.datasets.colmap_io import load_registered_image_names, read_points3d
except ModuleNotFoundError:
    # 兼容 `python3 recon/convert.py ...` 这种直接脚本执行方式。
    # 这时 `sys.path[0]` 是 `recon/`, 需要把仓库根目录补回搜索路径。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from recon.datasets.colmap_io import load_registered_image_names, read_points3d


def resolve_colmap_executable(explicit_path: str) -> str:
    # 优先尊重用户显式传入的路径。
    # 如果没有传, 再按 PATH 和常见本地安装位置兜底。
    if explicit_path:
        return explicit_path

    candidates = [
        shutil.which("colmap"),
        "/home/rais/.local/opt/colmap-env/bin/colmap",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return "colmap"


def choose_feature_extraction_use_gpu_option(help_text: str) -> str:
    # COLMAP 4.x 把“是否用 GPU”的总开关挪到了 FeatureExtraction 命名空间。
    # 旧版本则只认 SiftExtraction.use_gpu。
    if "--FeatureExtraction.use_gpu" in help_text:
        return "--FeatureExtraction.use_gpu"
    return "--SiftExtraction.use_gpu"


def choose_feature_matching_use_gpu_option(help_text: str) -> str:
    # 同理, matching 的 GPU 总开关在新版本里属于 FeatureMatching 命名空间。
    if "--FeatureMatching.use_gpu" in help_text:
        return "--FeatureMatching.use_gpu"
    return "--SiftMatching.use_gpu"


def get_colmap_help(colmap_command: str, subcommand: str) -> str:
    result = subprocess.run(
        [colmap_command, subcommand, "-h"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def run_command(command: list[str], failure_message: str) -> None:
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        logging.error("%s failed with code %s. Exiting.", failure_message, exc.returncode)
        raise SystemExit(exc.returncode) from exc


def is_colmap_model_dir(path: str | Path) -> bool:
    model_dir = Path(path)
    return any(
        (model_dir / file_name).exists()
        for file_name in ("images.bin", "images.txt")
    )


def choose_best_sparse_model_dir(distorted_sparse_path: str | Path) -> Path:
    model_root = Path(distorted_sparse_path)
    candidates: list[Path] = []

    # 兼容两种目录形态:
    # 1. `mapper` 产出的 `sparse/0`, `sparse/1`, ...
    # 2. 已经直接把模型文件放在 `sparse/` 根目录
    if is_colmap_model_dir(model_root):
        candidates.append(model_root)
    if model_root.exists():
        candidates.extend(
            path for path in sorted(model_root.iterdir()) if path.is_dir() and is_colmap_model_dir(path)
        )

    if not candidates:
        raise FileNotFoundError(f"在 {model_root} 下没有找到可用的 COLMAP sparse model")

    model_stats: list[tuple[int, int, Path]] = []
    for candidate in candidates:
        registered_image_count = len(load_registered_image_names(candidate))
        point_count = len(read_points3d(candidate))
        model_stats.append((registered_image_count, point_count, candidate))

    best_registered_count, best_point_count, best_model_dir = max(
        model_stats,
        key=lambda item: (item[0], item[1], item[2].name),
    )
    logging.info(
        "Selected sparse model %s with %s registered images and %s points3D.",
        best_model_dir,
        best_registered_count,
        best_point_count,
    )
    return best_model_dir


def parse_args() -> Namespace:
    parser = ArgumentParser("Colmap converter")
    parser.add_argument("--no_gpu", action="store_true")
    parser.add_argument("--skip_matching", action="store_true")
    parser.add_argument("--source_path", "-s", required=True, type=str)
    parser.add_argument("--camera", default="OPENCV", type=str)
    parser.add_argument("--colmap_executable", default="", type=str)
    parser.add_argument("--resize", action="store_true")
    parser.add_argument("--magick_executable", default="", type=str)
    return parser.parse_args()


def main() -> None:
    # This Python script is based on the shell converter script provided in the MipNerF 360 repository.
    args = parse_args()
    colmap_command = resolve_colmap_executable(args.colmap_executable)
    magick_command = args.magick_executable if len(args.magick_executable) > 0 else "magick"
    use_gpu = 0 if args.no_gpu else 1

    source_path = args.source_path
    input_path = os.path.join(source_path, "input")
    distorted_path = os.path.join(source_path, "distorted")
    distorted_sparse_path = os.path.join(distorted_path, "sparse")
    distorted_database_path = os.path.join(distorted_path, "database.db")

    if not args.skip_matching:
        os.makedirs(distorted_sparse_path, exist_ok=True)

        feature_help = get_colmap_help(colmap_command, "feature_extractor")
        matching_help = get_colmap_help(colmap_command, "exhaustive_matcher")
        feature_use_gpu_option = choose_feature_extraction_use_gpu_option(feature_help)
        matching_use_gpu_option = choose_feature_matching_use_gpu_option(matching_help)

        # Feature extraction
        run_command(
            [
                colmap_command,
                "feature_extractor",
                "--database_path",
                distorted_database_path,
                "--image_path",
                input_path,
                "--ImageReader.single_camera",
                "1",
                "--ImageReader.camera_model",
                args.camera,
                feature_use_gpu_option,
                str(use_gpu),
            ],
            "Feature extraction",
        )

        # Feature matching
        run_command(
            [
                colmap_command,
                "exhaustive_matcher",
                "--database_path",
                distorted_database_path,
                matching_use_gpu_option,
                str(use_gpu),
            ],
            "Feature matching",
        )

        # Bundle adjustment / mapping
        # The default Mapper tolerance is unnecessarily large,
        # decreasing it speeds up bundle adjustment steps.
        run_command(
            [
                colmap_command,
                "mapper",
                "--database_path",
                distorted_database_path,
                "--image_path",
                input_path,
                "--output_path",
                distorted_sparse_path,
                "--Mapper.ba_global_function_tolerance",
                "0.000001",
            ],
            "Mapper",
        )

    # Image undistortion
    # We need to undistort our images into ideal pinhole intrinsics.
    best_sparse_model_dir = choose_best_sparse_model_dir(distorted_sparse_path)
    run_command(
        [
            colmap_command,
            "image_undistorter",
            "--image_path",
            input_path,
            "--input_path",
            str(best_sparse_model_dir),
            "--output_path",
            source_path,
            "--output_type",
            "COLMAP",
        ],
        "Image undistorter",
    )

    files = os.listdir(os.path.join(source_path, "sparse"))
    os.makedirs(os.path.join(source_path, "sparse", "0"), exist_ok=True)
    # Copy each file from the source directory to the destination directory
    for file in files:
        if file == "0":
            continue
        source_file = os.path.join(source_path, "sparse", file)
        destination_file = os.path.join(source_path, "sparse", "0", file)
        shutil.move(source_file, destination_file)

    if args.resize:
        print("Copying and resizing...")

        # Resize images.
        os.makedirs(os.path.join(source_path, "images_2"), exist_ok=True)
        os.makedirs(os.path.join(source_path, "images_4"), exist_ok=True)
        os.makedirs(os.path.join(source_path, "images_8"), exist_ok=True)
        # Get the list of files in the source directory
        files = os.listdir(os.path.join(source_path, "images"))
        # Copy each file from the source directory to the destination directory
        for file in files:
            source_file = os.path.join(source_path, "images", file)

            destination_file = os.path.join(source_path, "images_2", file)
            shutil.copy2(source_file, destination_file)
            run_command(
                [magick_command, "mogrify", "-resize", "50%", destination_file],
                "50% resize",
            )

            destination_file = os.path.join(source_path, "images_4", file)
            shutil.copy2(source_file, destination_file)
            run_command(
                [magick_command, "mogrify", "-resize", "25%", destination_file],
                "25% resize",
            )

            destination_file = os.path.join(source_path, "images_8", file)
            shutil.copy2(source_file, destination_file)
            run_command(
                [magick_command, "mogrify", "-resize", "12.5%", destination_file],
                "12.5% resize",
            )

    print("Done.")


if __name__ == "__main__":
    main()
