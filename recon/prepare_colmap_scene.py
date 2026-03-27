from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from recon.datasets.colmap_io import load_registered_image_names


# =============================================================================
# FreeFix 外部 COLMAP 数据导入工具
# -----------------------------------------------------------------------------
# 这个脚本解决的是“外部目录已经有图片、数据库、切分清单, 但我不想污染原目录”的问题。
# 它只往当前项目的 data/ 里写结果, 并且尽量把 FreeFix 真正需要的骨架补齐。
# =============================================================================

MODEL_FILES = {
    "cameras.bin",
    "images.bin",
    "points3D.bin",
    "cameras.txt",
    "images.txt",
    "points3D.txt",
}

PAIR_ID_LIMIT = 2147483647

COMMON_COLMAP_BINARIES = [
    "colmap",
    "/home/rais/.local/opt/colmap-env/bin/colmap",
]

METADATA_FILES = [
    "colmap_feature_images.txt",
    "colmap_train_images.txt",
    "colmap_test_images.txt",
    "frame_selection.txt",
    "train_indices.txt",
    "eval_ids_test.txt",
    "eval_ids_val.txt",
    "prepared_multishot_manifest.json",
    "prepared_multishot_signature.json",
]


@dataclass
class PreparationReport:
    source_dir: str
    dest_dir: str
    copied_image_count: int
    copied_database: bool
    source_sparse_found: bool
    source_sparse_dir: str | None
    sparse_ready: bool
    partition_ready: bool
    selected_image_source: str
    skipped_extra_image_count: int
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把外部 COLMAP 场景复制到 FreeFix data/ 目录, 并尽量整理成可训练结构。"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="外部数据目录, 例如 /home/rais/CoherentGS/data/my4",
    )
    parser.add_argument(
        "--dest-dir",
        type=Path,
        default=None,
        help="目标目录, 默认是 data/<source-dir-name>",
    )
    parser.add_argument(
        "--rebuild-sparse",
        action="store_true",
        help="当源目录没有 sparse model 时, 尝试在目标目录里调用 COLMAP mapper 重建。",
    )
    parser.add_argument(
        "--colmap-binary",
        type=str,
        default="colmap",
        help="COLMAP 可执行文件路径或命令名。仅在需要重建 sparse 或导出文本模型时使用。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="若目标目录已存在, 先删除再重建。",
    )
    return parser.parse_args()


def ensure_clean_directory(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise FileExistsError(
                f"目标目录已存在: {path}. 如需覆盖, 请加上 --force。"
            )
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def find_source_sparse_dir(source_dir: Path) -> Path | None:
    candidates = [source_dir / "sparse" / "0", source_dir / "sparse"]
    for candidate in candidates:
        if not candidate.exists():
            continue
        existing = {path.name for path in candidate.iterdir() if path.is_file()}
        if existing & MODEL_FILES:
            return candidate
    return None


def read_image_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def read_partition_source_names(source_dir: Path) -> tuple[list[str], list[str], str | None]:
    # 先兼容“原始外部目录”的根级清单文件。
    # 如果当前 source_dir 已经是 FreeFix 导入后的目录, 再回退到 meta 里的保留名单。
    train_names = read_image_list(source_dir / "colmap_train_images.txt")
    test_names = read_image_list(source_dir / "colmap_test_images.txt")
    if train_names or test_names:
        return train_names, test_names, "colmap_train_images.txt + colmap_test_images.txt"

    meta_partition_path = source_dir / "meta" / "partition_source_names.json"
    if meta_partition_path.exists():
        payload = json.loads(meta_partition_path.read_text())
        train_names = [str(name).strip() for name in payload.get("train", []) if str(name).strip()]
        test_names = [str(name).strip() for name in payload.get("test", []) if str(name).strip()]
        return train_names, test_names, "meta/partition_source_names.json"

    return [], [], None


def backup_sqlite_database(source_db: Path, dest_db: Path) -> None:
    # 用 SQLite 原生 backup API 做一致性备份, 可以避开直接复制 wal/shm 的歧义。
    source_conn = sqlite3.connect(source_db)
    try:
        dest_conn = sqlite3.connect(dest_db)
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        source_conn.close()


def load_database_image_names(database_path: Path) -> list[str]:
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT name FROM images ORDER BY name").fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def choose_image_names(source_dir: Path) -> tuple[list[str], str]:
    database_path = source_dir / "database.db"
    if database_path.exists():
        return load_database_image_names(database_path), "database.db(images table)"

    train_names, test_names, source_name = read_partition_source_names(source_dir)
    if train_names or test_names:
        merged = sorted(set(train_names) | set(test_names))
        return merged, source_name or "partition source names"

    image_dir = source_dir / "images"
    if not image_dir.exists():
        raise FileNotFoundError(f"源目录缺少 images/: {image_dir}")
    merged = sorted(
        str(path.relative_to(image_dir)).replace("\\", "/")
        for path in image_dir.rglob("*")
        if path.is_file()
    )
    return merged, "images/ directory scan"


def copy_selected_images(source_image_dir: Path, dest_image_dir: Path, image_names: Iterable[str]) -> int:
    copied = 0
    for image_name in image_names:
        source_path = source_image_dir / image_name
        if not source_path.exists():
            raise FileNotFoundError(f"源图片不存在: {source_path}")
        dest_path = dest_image_dir / image_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)
        copied += 1
    return copied


def filter_existing_image_names(
    source_image_dir: Path, image_names: Iterable[str]
) -> tuple[list[str], list[str]]:
    # 用户手工删图后, 数据库或旧清单里常会残留过期名字。
    # 这里先按磁盘上的真实图片集合过滤一遍, 保持顺序不变。
    existing_names = {
        str(path.relative_to(source_image_dir)).replace("\\", "/")
        for path in source_image_dir.rglob("*")
        if path.is_file()
    }

    kept_names: list[str] = []
    missing_names: list[str] = []
    for image_name in image_names:
        normalized_name = image_name.replace("\\", "/")
        if normalized_name in existing_names:
            kept_names.append(normalized_name)
        else:
            missing_names.append(normalized_name)
    return kept_names, missing_names


def pair_id_to_image_ids(pair_id: int) -> tuple[int, int]:
    image_id2 = pair_id % PAIR_ID_LIMIT
    image_id1 = (pair_id - image_id2) // PAIR_ID_LIMIT
    return int(image_id1), int(image_id2)


def prune_database_to_images(
    database_path: Path, kept_image_names: set[str]
) -> dict[str, int]:
    # 这里不是“跳过缺图”这么简单。
    # 如果继续保留数据库里的过期 image row, mapper 和后续 pair 数据都会失真。
    conn = sqlite3.connect(database_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        image_rows = conn.execute(
            "SELECT image_id, name FROM images ORDER BY image_id"
        ).fetchall()
        stale_rows = [
            (image_id, name)
            for image_id, name in image_rows
            if name not in kept_image_names
        ]
        if not stale_rows:
            return {
                "removed_images": 0,
                "removed_matches": 0,
                "removed_two_view_geometries": 0,
            }

        stale_image_ids = {image_id for image_id, _ in stale_rows}

        removed_pair_counts: dict[str, int] = {}
        for table_name in ["matches", "two_view_geometries"]:
            pair_rows = conn.execute(f"SELECT pair_id FROM {table_name}").fetchall()
            stale_pair_ids = []
            for (pair_id,) in pair_rows:
                image_id1, image_id2 = pair_id_to_image_ids(pair_id)
                if image_id1 in stale_image_ids or image_id2 in stale_image_ids:
                    stale_pair_ids.append((pair_id,))
            if stale_pair_ids:
                conn.executemany(
                    f"DELETE FROM {table_name} WHERE pair_id = ?", stale_pair_ids
                )
            removed_pair_counts[table_name] = len(stale_pair_ids)

        conn.executemany(
            "DELETE FROM images WHERE image_id = ?",
            [(image_id,) for image_id, _ in stale_rows],
        )
        conn.commit()
        return {
            "removed_images": len(stale_rows),
            "removed_matches": removed_pair_counts["matches"],
            "removed_two_view_geometries": removed_pair_counts["two_view_geometries"],
        }
    finally:
        conn.close()


def copy_metadata_files(source_dir: Path, dest_meta_dir: Path) -> None:
    dest_meta_dir.mkdir(parents=True, exist_ok=True)
    for filename in METADATA_FILES:
        source_path = source_dir / filename
        if source_path.exists():
            shutil.copy2(source_path, dest_meta_dir / filename)


def copy_sparse_model(source_sparse_dir: Path, dest_dir: Path) -> Path:
    dest_sparse_root = dest_dir / "sparse"
    if source_sparse_dir.name == "0":
        dest_model_dir = dest_sparse_root / "0"
    else:
        dest_model_dir = dest_sparse_root
    shutil.copytree(source_sparse_dir, dest_model_dir, dirs_exist_ok=True)
    return dest_model_dir


def resolve_colmap_binary(colmap_binary: str) -> str | None:
    candidates = [colmap_binary, *COMMON_COLMAP_BINARIES]
    for candidate in candidates:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return str(candidate_path)
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved
    return None


def run_colmap_mapper(colmap_binary: str, database_path: Path, image_path: Path, output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    command = [
        colmap_binary,
        "mapper",
        "--database_path",
        str(database_path),
        "--image_path",
        str(image_path),
        "--output_path",
        str(output_path),
        "--Mapper.ba_global_function_tolerance=0.000001",
    ]
    subprocess.run(command, check=True)


def build_partition(
    registered_image_names: list[str],
    train_names: list[str],
    test_names: list[str],
) -> tuple[dict[str, list[int]] | None, list[str]]:
    warnings: list[str] = []
    sorted_names = sorted(registered_image_names)
    name_to_index = {name: index for index, name in enumerate(sorted_names)}

    missing_train = sorted(set(train_names) - set(sorted_names))
    missing_test = sorted(set(test_names) - set(sorted_names))
    if missing_train:
        warnings.append(
            f"已有 {len(missing_train)} 张 train 图不在当前 sparse model 中, 暂不写 partition.json。"
        )
    if missing_test:
        warnings.append(
            f"已有 {len(missing_test)} 张 test 图不在当前 sparse model 中, 暂不写 partition.json。"
        )
    if missing_train or missing_test:
        return None, warnings

    partition = {
        "train": [name_to_index[name] for name in train_names],
        "test": [name_to_index[name] for name in test_names],
    }
    return partition, warnings


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()

    source_dir = args.source_dir.expanduser().resolve()
    if args.dest_dir is None:
        dest_dir = (Path.cwd() / "data" / source_dir.name).resolve()
    else:
        dest_dir = args.dest_dir.expanduser().resolve()

    source_image_dir = source_dir / "images"
    if not source_image_dir.exists():
        raise FileNotFoundError(f"源目录缺少 images/: {source_image_dir}")

    ensure_clean_directory(dest_dir, args.force)
    (dest_dir / "images").mkdir(parents=True, exist_ok=True)

    image_names, image_name_source = choose_image_names(source_dir)
    image_names, missing_selected_images = filter_existing_image_names(
        source_image_dir=source_image_dir,
        image_names=image_names,
    )
    if not image_names:
        raise FileNotFoundError(
            f"在 {source_image_dir} 中没有找到任何可用图片。"
        )

    warnings: list[str] = []
    if missing_selected_images:
        warnings.append(
            f"{image_name_source} 中有 {len(missing_selected_images)} 张图片在 images/ 里已经不存在, 已自动跳过这些旧记录。"
        )
    copied_image_count = copy_selected_images(
        source_image_dir=source_image_dir,
        dest_image_dir=dest_dir / "images",
        image_names=image_names,
    )

    copied_database = False
    source_database_path = source_dir / "database.db"
    if source_database_path.exists():
        backup_sqlite_database(source_database_path, dest_dir / "database.db")
        copied_database = True
        if missing_selected_images:
            prune_result = prune_database_to_images(
                dest_dir / "database.db", set(image_names)
            )
            warnings.append(
                "已同步清理复制后的 database.db: "
                f"删除 {prune_result['removed_images']} 条过期 images, "
                f"{prune_result['removed_matches']} 条 matches, "
                f"{prune_result['removed_two_view_geometries']} 条 two_view_geometries。"
            )

    copy_metadata_files(source_dir, dest_dir / "meta")

    # 为后续核对保留源划分名单, 即使当前还写不出最终 partition.json 也不丢上下文。
    train_names, test_names, partition_source_name = read_partition_source_names(
        source_dir
    )
    train_names, missing_train_names = filter_existing_image_names(
        source_image_dir=source_image_dir,
        image_names=train_names,
    )
    test_names, missing_test_names = filter_existing_image_names(
        source_image_dir=source_image_dir,
        image_names=test_names,
    )
    if missing_train_names:
        warnings.append(
            f"train 名单里有 {len(missing_train_names)} 张已删图片, 已从新场景划分中移除。"
        )
    if missing_test_names:
        warnings.append(
            f"test 名单里有 {len(missing_test_names)} 张已删图片, 已从新场景划分中移除。"
        )
    write_json(
        dest_dir / "meta" / "partition_source_names.json",
        {
            "train": train_names,
            "test": test_names,
        },
    )
    (dest_dir / "meta" / "selected_images.txt").write_text("\n".join(image_names) + "\n")

    source_sparse_dir = find_source_sparse_dir(source_dir)
    resolved_colmap_binary = resolve_colmap_binary(args.colmap_binary)
    prepared_model_dir: Path | None = None

    if args.rebuild_sparse:
        if resolved_colmap_binary is None:
            raise FileNotFoundError(
                "源目录没有 sparse model, 且当前找不到可用的 COLMAP 可执行文件。"
            )
        if not copied_database:
            raise FileNotFoundError(
                "源目录没有 sparse model 时, 还需要 database.db 才能重建 sparse。"
            )
        run_colmap_mapper(
            colmap_binary=resolved_colmap_binary,
            database_path=dest_dir / "database.db",
            image_path=dest_dir / "images",
            output_path=dest_dir / "sparse",
        )
        rebuilt_model_dir = find_source_sparse_dir(dest_dir)
        if rebuilt_model_dir is None:
            raise RuntimeError("COLMAP mapper 已运行, 但目标目录里仍未发现 sparse model。")
        prepared_model_dir = rebuilt_model_dir
    elif source_sparse_dir is not None:
        if missing_selected_images:
            warnings.append(
                "检测到源目录曾手工删图, 旧 sparse 很可能已经和 images/ 不一致。"
                "当前未复制旧 sparse; 如需可训练结果, 请加上 --rebuild-sparse。"
            )
        else:
            prepared_model_dir = copy_sparse_model(source_sparse_dir, dest_dir)
    else:
        warnings.append(
            "源目录缺少 sparse model, 当前只完成了图片/数据库/元数据导入。要真正训练, 还需要后续补 sparse。"
        )

    partition_ready = False
    if prepared_model_dir is not None and train_names and test_names:
        registered_names = load_registered_image_names(
            prepared_model_dir,
        )
        partition, partition_warnings = build_partition(
            registered_image_names=registered_names,
            train_names=train_names,
            test_names=test_names,
        )
        warnings.extend(partition_warnings)
        if partition is not None:
            write_json(dest_dir / "partition.json", partition)
            partition_ready = True
    elif train_names or test_names:
        warnings.append(
            "已保留 train/test 名单到 meta/partition_source_names.json, 但因为当前还没有可解析的 sparse model, 暂不生成 partition.json。"
        )

    source_images_total = sum(1 for path in source_image_dir.rglob("*") if path.is_file())
    skipped_extra_image_count = max(source_images_total - copied_image_count, 0)

    report = PreparationReport(
        source_dir=str(source_dir),
        dest_dir=str(dest_dir),
        copied_image_count=copied_image_count,
        copied_database=copied_database,
        source_sparse_found=source_sparse_dir is not None,
        source_sparse_dir=str(source_sparse_dir) if source_sparse_dir is not None else None,
        sparse_ready=prepared_model_dir is not None,
        partition_ready=partition_ready,
        selected_image_source=image_name_source
        if partition_source_name is None
        else f"{image_name_source}; partition source={partition_source_name}",
        skipped_extra_image_count=skipped_extra_image_count,
    )

    if prepared_model_dir is not None:
        report.next_steps.append(
            "可以直接用 python -m recon.trainer --data_dir <dest_dir> --result_dir <result_dir> --data_type colmap 继续。"
        )
    else:
        report.next_steps.append(
            "后续请安装 COLMAP, 然后重新执行本脚本并加上 --rebuild-sparse。"
        )
    if not partition_ready and train_names and test_names:
        report.next_steps.append(
            "当 sparse model 准备好后, 重新运行本脚本可继续生成 partition.json。"
        )

    report.warnings.extend(warnings)
    write_json(dest_dir / "import_report.json", asdict(report))

    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
