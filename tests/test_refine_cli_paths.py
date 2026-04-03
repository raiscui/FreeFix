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
from ours.refine_backend_runner import build_refiner_runtime_kwargs
from ours.refine_backend_common import resolve_refine_seed


class RefineCliPathTest(unittest.TestCase):
    def test_resolve_refine_seed_uses_common_default_when_backend_override_missing(self) -> None:
        cfg = SimpleNamespace(refine_seed=64, flux_seed=None, kontext_seed=None)
        self.assertEqual(resolve_refine_seed(cfg, backend_name="flux"), 64)
        self.assertEqual(resolve_refine_seed(cfg, backend_name="kontext"), 64)

    def test_resolve_refine_seed_prefers_backend_specific_override(self) -> None:
        cfg = SimpleNamespace(refine_seed=64, flux_seed=123, kontext_seed=456)
        self.assertEqual(resolve_refine_seed(cfg, backend_name="flux"), 123)
        self.assertEqual(resolve_refine_seed(cfg, backend_name="kontext"), 456)

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

    def test_build_refiner_runtime_kwargs_includes_strategy_overrides(self) -> None:
        cfg = SimpleNamespace(
            load_step=35000,
            test_split="test",
            test_trans=[0, 0, 0],
            test_rots=[0, 0, 0],
            c_exp_index=[0.001, 0.01, 0.1],
            hessian_attr=["means"],
            refine_end_idx=41,
            refine_start_idx=0,
            data_type="colmap",
            refine_virtual_step=100,
            refine_start_iter=100,
            refine_stop_iter=5000,
            reset_every=1500,
            refine_every=200,
            prune_opa=0.006,
            grow_grad2d=0.0003,
            grow_scale3d=0.01,
            prune_scale3d=0.1,
        )

        kwargs = build_refiner_runtime_kwargs(cfg, load_ckpt_path="/tmp/demo.pt")

        self.assertEqual(kwargs["load_ckpt_path"], "/tmp/demo.pt")
        self.assertEqual(kwargs["refine_virtual_step"], 100)
        self.assertEqual(kwargs["refine_start_iter"], 100)
        self.assertEqual(kwargs["refine_stop_iter"], 5000)
        self.assertEqual(kwargs["reset_every"], 1500)
        self.assertEqual(kwargs["refine_every"], 200)
        self.assertEqual(kwargs["prune_opa"], 0.006)
        self.assertEqual(kwargs["grow_grad2d"], 0.0003)
        self.assertEqual(kwargs["grow_scale3d"], 0.01)
        self.assertEqual(kwargs["prune_scale3d"], 0.1)


if __name__ == "__main__":
    unittest.main()
