import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import json

from ours.evaluation import (
    apply_runtime_path_overrides,
    has_refined_checkpoint,
    refined_checkpoint_path,
    resolve_optional_checkpoint_path,
    resolve_base_load_step,
)


class EvaluationCliTest(unittest.TestCase):
    def test_resolve_base_load_step_prefers_cli_override(self) -> None:
        cfg = SimpleNamespace(load_step=11999)

        self.assertEqual(resolve_base_load_step(cfg, 7777), 7777)

    def test_resolve_base_load_step_falls_back_to_cfg(self) -> None:
        cfg = SimpleNamespace(load_step=11999)

        self.assertEqual(resolve_base_load_step(cfg), 11999)

    def test_resolve_base_load_step_falls_back_to_legacy_default(self) -> None:
        cfg = SimpleNamespace()

        self.assertEqual(resolve_base_load_step(cfg), 29999)

    def test_refined_checkpoint_helpers_follow_exp_name_convention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            ckpt_dir = base_dir / "ckpts"
            ckpt_dir.mkdir()
            cfg = SimpleNamespace(base_dir=str(base_dir), exp_name="flux_demo")

            expected_path = ckpt_dir / "ckpt_flux_demo.pt"
            self.assertEqual(refined_checkpoint_path(cfg), str(expected_path))
            self.assertFalse(has_refined_checkpoint(cfg))

            expected_path.write_bytes(b"demo")
            self.assertTrue(has_refined_checkpoint(cfg))

    def test_resolve_optional_checkpoint_path_prefers_base_dir_for_relative_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            bridge_path = tmp_path / "base" / "bridges" / "demo.pt"
            bridge_path.parent.mkdir(parents=True)
            bridge_path.write_bytes(b"demo")

            cfg = SimpleNamespace(
                load_ckpt_path="bridges/demo.pt",
                base_dir=str(tmp_path / "base"),
            )

            self.assertEqual(resolve_optional_checkpoint_path(cfg), str(bridge_path.resolve()))

    def test_apply_runtime_path_overrides_updates_scene_and_partition_for_base_eval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            base_dir = tmp_path / "base"
            scene_dir = tmp_path / "scene"
            base_dir.mkdir()
            scene_dir.mkdir()

            partition_path = scene_dir / "partition.json"
            partition_path.write_text(json.dumps({"train": [0], "test": [1]}), encoding="utf-8")

            bridge_path = base_dir / "bridges" / "demo.pt"
            bridge_path.parent.mkdir(parents=True)
            bridge_path.write_bytes(b"demo")

            cfg = SimpleNamespace(
                colmap_path=str(scene_dir),
                load_ckpt_path="bridges/demo.pt",
                base_dir=str(base_dir),
            )
            config = SimpleNamespace(data_dir="old_scene", partition=None)

            resolved_ckpt_path = apply_runtime_path_overrides(cfg, config, include_ckpt_override=True)

            self.assertEqual(config.data_dir, str(scene_dir.resolve()))
            self.assertEqual(config.partition, str(partition_path))
            self.assertEqual(resolved_ckpt_path, str(bridge_path.resolve()))

    def test_apply_runtime_path_overrides_skips_ckpt_override_for_refined_eval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            scene_dir = tmp_path / "scene"
            scene_dir.mkdir()

            cfg = SimpleNamespace(
                colmap_path=str(scene_dir),
                load_ckpt_path="/tmp/should_not_be_used.pt",
                base_dir=str(tmp_path / "base"),
            )
            config = SimpleNamespace(data_dir="old_scene", partition="old_partition")

            resolved_ckpt_path = apply_runtime_path_overrides(cfg, config, include_ckpt_override=False)

            self.assertEqual(config.data_dir, str(scene_dir.resolve()))
            self.assertEqual(resolved_ckpt_path, None)
            self.assertEqual(config.partition, "old_partition")


if __name__ == "__main__":
    unittest.main()
