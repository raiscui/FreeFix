import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ours.refine_by_flux import (
    apply_runtime_path_overrides as apply_flux_runtime_path_overrides,
    build_arg_parser as build_flux_arg_parser,
)
from ours.refine_by_kontext import (
    apply_runtime_path_overrides as apply_kontext_runtime_path_overrides,
    build_arg_parser as build_kontext_arg_parser,
)
from ours.refine_by_sdxl import (
    apply_runtime_path_overrides as apply_sdxl_runtime_path_overrides,
    build_arg_parser as build_sdxl_arg_parser,
)


class RefineCliPathTest(unittest.TestCase):
    def test_flux_parser_accepts_colmap_and_ckpt_path_args(self) -> None:
        parser = build_flux_arg_parser()
        args = parser.parse_args(
            [
                "--exp_cfg",
                "exp_cfg/demo.yaml",
                "--colmap-path",
                "/tmp/demo_scene",
                "--ckpt-path",
                "/tmp/demo_ckpt.pt",
            ]
        )

        self.assertEqual(args.colmap_path, "/tmp/demo_scene")
        self.assertEqual(args.ckpt_path, "/tmp/demo_ckpt.pt")

    def test_sdxl_parser_accepts_colmap_and_ckpt_path_args(self) -> None:
        parser = build_sdxl_arg_parser()
        args = parser.parse_args(
            [
                "--exp_cfg",
                "exp_cfg/demo.yaml",
                "--colmap-path",
                "/tmp/demo_scene",
                "--ckpt-path",
                "/tmp/demo_ckpt.pt",
            ]
        )

        self.assertEqual(args.colmap_path, "/tmp/demo_scene")
        self.assertEqual(args.ckpt_path, "/tmp/demo_ckpt.pt")

    def test_kontext_parser_accepts_colmap_and_ckpt_path_args(self) -> None:
        parser = build_kontext_arg_parser()
        args = parser.parse_args(
            [
                "--exp_cfg",
                "exp_cfg/demo.yaml",
                "--colmap-path",
                "/tmp/demo_scene",
                "--ckpt-path",
                "/tmp/demo_ckpt.pt",
            ]
        )

        self.assertEqual(args.colmap_path, "/tmp/demo_scene")
        self.assertEqual(args.ckpt_path, "/tmp/demo_ckpt.pt")

    def test_flux_runtime_override_updates_scene_and_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            base_dir = tmp_path / "base"
            scene_dir = tmp_path / "scene"
            base_dir.mkdir()
            scene_dir.mkdir()

            partition_path = scene_dir / "partition.json"
            partition_path.write_text(json.dumps({"train": [0], "test": [1]}), encoding="utf-8")

            ckpt_rel_path = Path("bridges/demo.pt")
            ckpt_abs_path = base_dir / ckpt_rel_path
            ckpt_abs_path.parent.mkdir(parents=True)
            ckpt_abs_path.write_bytes(b"demo")

            cfg = SimpleNamespace(
                colmap_path=str(scene_dir),
                load_ckpt_path=str(ckpt_rel_path),
                base_dir=str(base_dir),
            )
            config = SimpleNamespace(data_dir="old_scene", partition=None)

            resolved_ckpt_path = apply_flux_runtime_path_overrides(cfg, config)

            self.assertEqual(config.data_dir, str(scene_dir.resolve()))
            self.assertEqual(config.partition, str(partition_path))
            self.assertEqual(resolved_ckpt_path, str(ckpt_abs_path.resolve()))

    def test_sdxl_runtime_override_updates_scene_and_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            base_dir = tmp_path / "base"
            scene_dir = tmp_path / "scene"
            base_dir.mkdir()
            scene_dir.mkdir()

            partition_path = scene_dir / "partition.json"
            partition_path.write_text(json.dumps({"train": [0], "test": [1]}), encoding="utf-8")

            ckpt_rel_path = Path("bridges/demo.pt")
            ckpt_abs_path = base_dir / ckpt_rel_path
            ckpt_abs_path.parent.mkdir(parents=True)
            ckpt_abs_path.write_bytes(b"demo")

            cfg = SimpleNamespace(
                colmap_path=str(scene_dir),
                load_ckpt_path=str(ckpt_rel_path),
                base_dir=str(base_dir),
            )
            config = SimpleNamespace(data_dir="old_scene", partition=None)

            resolved_ckpt_path = apply_sdxl_runtime_path_overrides(cfg, config)

            self.assertEqual(config.data_dir, str(scene_dir.resolve()))
            self.assertEqual(config.partition, str(partition_path))
            self.assertEqual(resolved_ckpt_path, str(ckpt_abs_path.resolve()))

    def test_kontext_runtime_override_updates_scene_and_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            base_dir = tmp_path / "base"
            scene_dir = tmp_path / "scene"
            base_dir.mkdir()
            scene_dir.mkdir()

            partition_path = scene_dir / "partition.json"
            partition_path.write_text(json.dumps({"train": [0], "test": [1]}), encoding="utf-8")

            ckpt_rel_path = Path("bridges/demo.pt")
            ckpt_abs_path = base_dir / ckpt_rel_path
            ckpt_abs_path.parent.mkdir(parents=True)
            ckpt_abs_path.write_bytes(b"demo")

            cfg = SimpleNamespace(
                colmap_path=str(scene_dir),
                load_ckpt_path=str(ckpt_rel_path),
                base_dir=str(base_dir),
            )
            config = SimpleNamespace(data_dir="old_scene", partition=None)

            resolved_ckpt_path = apply_kontext_runtime_path_overrides(cfg, config)

            self.assertEqual(config.data_dir, str(scene_dir.resolve()))
            self.assertEqual(config.partition, str(partition_path))
            self.assertEqual(resolved_ckpt_path, str(ckpt_abs_path.resolve()))


if __name__ == "__main__":
    unittest.main()
