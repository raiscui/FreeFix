import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from recon.prepare_colmap_scene import (
    PAIR_ID_LIMIT,
    filter_existing_image_names,
    prune_database_to_images,
    read_partition_source_names,
)


def make_pair_id(image_id1: int, image_id2: int) -> int:
    # 按 COLMAP 的 pair_id 规则编码, 方便构造最小测试数据库。
    if image_id1 > image_id2:
        image_id1, image_id2 = image_id2, image_id1
    return PAIR_ID_LIMIT * image_id1 + image_id2


class PrepareColmapSceneTest(unittest.TestCase):
    def test_read_partition_source_names_falls_back_to_meta_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_dir = Path(tmp_dir)
            meta_dir = source_dir / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "partition_source_names.json").write_text(
                json.dumps(
                    {
                        "train": ["000001.png", "000003.png"],
                        "test": ["000002.png"],
                    }
                ),
                encoding="utf-8",
            )

            train_names, test_names, source_name = read_partition_source_names(
                source_dir
            )

            self.assertEqual(train_names, ["000001.png", "000003.png"])
            self.assertEqual(test_names, ["000002.png"])
            self.assertEqual(source_name, "meta/partition_source_names.json")

    def test_filter_existing_image_names_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_dir = Path(tmp_dir)
            for image_name in ["000003.png", "000001.png"]:
                (image_dir / image_name).write_bytes(b"fake")

            kept_names, missing_names = filter_existing_image_names(
                source_image_dir=image_dir,
                image_names=["000001.png", "000002.png", "000003.png"],
            )

            self.assertEqual(kept_names, ["000001.png", "000003.png"])
            self.assertEqual(missing_names, ["000002.png"])

    def test_prune_database_to_images_removes_stale_images_and_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            database_path = Path(tmp_dir) / "database.db"
            conn = sqlite3.connect(database_path)
            try:
                conn.executescript(
                    """
                    CREATE TABLE images (
                        image_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        name TEXT NOT NULL UNIQUE,
                        camera_id INTEGER NOT NULL
                    );
                    CREATE TABLE keypoints (
                        image_id INTEGER PRIMARY KEY NOT NULL,
                        rows INTEGER NOT NULL,
                        cols INTEGER NOT NULL,
                        data BLOB,
                        FOREIGN KEY(image_id) REFERENCES images(image_id) ON DELETE CASCADE
                    );
                    CREATE TABLE descriptors (
                        image_id INTEGER PRIMARY KEY NOT NULL,
                        type INTEGER NOT NULL,
                        rows INTEGER NOT NULL,
                        cols INTEGER NOT NULL,
                        data BLOB,
                        FOREIGN KEY(image_id) REFERENCES images(image_id) ON DELETE CASCADE
                    );
                    CREATE TABLE matches (
                        pair_id INTEGER PRIMARY KEY NOT NULL,
                        rows INTEGER NOT NULL,
                        cols INTEGER NOT NULL,
                        data BLOB
                    );
                    CREATE TABLE two_view_geometries (
                        pair_id INTEGER PRIMARY KEY NOT NULL,
                        rows INTEGER NOT NULL,
                        cols INTEGER NOT NULL,
                        data BLOB,
                        config INTEGER NOT NULL,
                        F BLOB,
                        E BLOB,
                        H BLOB,
                        qvec BLOB,
                        tvec BLOB
                    );
                    """
                )

                image_rows = [
                    (1, "000001.png", 1),
                    (2, "000002.png", 1),
                    (3, "000003.png", 1),
                ]
                conn.executemany(
                    "INSERT INTO images(image_id, name, camera_id) VALUES (?, ?, ?)",
                    image_rows,
                )
                conn.executemany(
                    "INSERT INTO keypoints(image_id, rows, cols, data) VALUES (?, 0, 0, NULL)",
                    [(1,), (2,), (3,)],
                )
                conn.executemany(
                    "INSERT INTO descriptors(image_id, type, rows, cols, data) VALUES (?, 0, 0, 0, NULL)",
                    [(1,), (2,), (3,)],
                )

                pair_ids = [
                    make_pair_id(1, 2),
                    make_pair_id(1, 3),
                    make_pair_id(2, 3),
                ]
                conn.executemany(
                    "INSERT INTO matches(pair_id, rows, cols, data) VALUES (?, 0, 0, NULL)",
                    [(pair_id,) for pair_id in pair_ids],
                )
                conn.executemany(
                    "INSERT INTO two_view_geometries(pair_id, rows, cols, data, config, F, E, H, qvec, tvec) "
                    "VALUES (?, 0, 0, NULL, 0, NULL, NULL, NULL, NULL, NULL)",
                    [(pair_id,) for pair_id in pair_ids],
                )
                conn.commit()
            finally:
                conn.close()

            result = prune_database_to_images(
                database_path=database_path,
                kept_image_names={"000001.png", "000003.png"},
            )

            self.assertEqual(
                result,
                {
                    "removed_images": 1,
                    "removed_matches": 2,
                    "removed_two_view_geometries": 2,
                },
            )

            conn = sqlite3.connect(database_path)
            try:
                remaining_images = conn.execute(
                    "SELECT image_id, name FROM images ORDER BY image_id"
                ).fetchall()
                remaining_keypoints = conn.execute(
                    "SELECT image_id FROM keypoints ORDER BY image_id"
                ).fetchall()
                remaining_descriptors = conn.execute(
                    "SELECT image_id FROM descriptors ORDER BY image_id"
                ).fetchall()
                remaining_matches = conn.execute(
                    "SELECT pair_id FROM matches ORDER BY pair_id"
                ).fetchall()
                remaining_geometries = conn.execute(
                    "SELECT pair_id FROM two_view_geometries ORDER BY pair_id"
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(remaining_images, [(1, "000001.png"), (3, "000003.png")])
            self.assertEqual(remaining_keypoints, [(1,), (3,)])
            self.assertEqual(remaining_descriptors, [(1,), (3,)])
            self.assertEqual(remaining_matches, [(make_pair_id(1, 3),)])
            self.assertEqual(remaining_geometries, [(make_pair_id(1, 3),)])


if __name__ == "__main__":
    unittest.main()
