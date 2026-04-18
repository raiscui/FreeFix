import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch

from ours.refine_backend_runner import (
    build_final_3dgs_ply_path,
    export_final_3dgs_ply,
    run_backend_refine,
)


class RefineBackendRunnerPlyTest(unittest.TestCase):
    def test_build_final_3dgs_ply_path_follows_base_dir_and_exp_name(self) -> None:
        cfg = SimpleNamespace(base_dir="/tmp/freefix/demo", exp_name="scene_flux_demo")

        output_path = build_final_3dgs_ply_path(cfg)

        self.assertEqual(output_path, Path("/tmp/freefix/demo/point_cloud_scene_flux_demo.ply"))

    def test_export_final_3dgs_ply_writes_binary_ply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            ckpt_path = tmp_path / "ckpt_demo.pt"
            output_path = tmp_path / "point_cloud_demo.ply"

            torch.save(
                {
                    "splats": {
                        "means": torch.zeros((2, 3), dtype=torch.float32),
                        "opacities": torch.zeros((2,), dtype=torch.float32),
                        "quats": torch.tensor(
                            [[1.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]],
                            dtype=torch.float32,
                        ),
                        "scales": torch.zeros((2, 3), dtype=torch.float32),
                        "sh0": torch.zeros((2, 1, 3), dtype=torch.float32),
                        "shN": torch.zeros((2, 15, 3), dtype=torch.float32),
                    }
                },
                ckpt_path,
            )

            exported_path = export_final_3dgs_ply(
                ckpt_path=ckpt_path,
                output_path=output_path,
                log_runtime_stage=lambda _message: None,
            )

            self.assertEqual(exported_path, str(output_path))
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)
            self.assertEqual(output_path.read_bytes()[:3], b"ply")

    def test_completed_resume_state_exports_missing_ply_before_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            final_ckpt_path = tmp_path / "ckpt_demo.pt"
            final_ckpt_path.write_bytes(b"demo")
            cfg = SimpleNamespace(
                base_dir=str(tmp_path / "result"),
                exp_name="scene_demo",
            )

            exported: list[tuple[str, Path]] = []

            def fake_export(*, ckpt_path, output_path, log_runtime_stage):
                exported.append((str(ckpt_path), Path(output_path)))
                return str(output_path)

            with patch(
                "ours.refine_backend_runner.load_refine_resume_state",
                return_value={
                    "status": "complete",
                    "exp_name": "scene_demo",
                    "final_ckpt_path": str(final_ckpt_path),
                },
            ), patch(
                "ours.refine_backend_runner.export_final_3dgs_ply",
                side_effect=fake_export,
            ):
                run_backend_refine(
                    cfg,
                    log_runtime_stage=lambda _message: None,
                    build_backend_runtime=lambda *_args, **_kwargs: None,
                )

            self.assertEqual(len(exported), 1)
            self.assertEqual(exported[0][0], str(final_ckpt_path))
            self.assertEqual(
                exported[0][1],
                tmp_path / "result" / "point_cloud_scene_demo.ply",
            )


if __name__ == "__main__":
    unittest.main()
