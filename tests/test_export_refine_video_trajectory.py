import tempfile
import unittest
from pathlib import Path

import numpy as np

from ours.export_refine_video_trajectory import (
    build_arg_parser,
    build_frame_record,
    build_unity_payload,
    compare_camera_trajectories,
    discover_exp_cfg_path,
    resolve_cli_path,
    resolve_output_path,
    resolve_unity_output_path,
)


class ExportRefineVideoTrajectoryTest(unittest.TestCase):
    def test_parser_accepts_video_and_optional_exp_cfg(self) -> None:
        parser = build_arg_parser()
        args = parser.parse_args(
            [
                "--video-path",
                "outputs/demo/after_refine.mp4",
                "--exp-cfg",
                "exp_cfg/demo.yaml",
            ]
        )

        self.assertEqual(args.video_path, Path("outputs/demo/after_refine.mp4"))
        self.assertEqual(args.exp_cfg, Path("exp_cfg/demo.yaml"))

    def test_discover_exp_cfg_prefers_matching_base_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            repo_dir = tmp_path / "repo"
            repo_dir.mkdir()

            outputs_dir = repo_dir / "outputs"
            target_base_dir = outputs_dir / "demo_base"
            target_output_dir = target_base_dir / "demo_exp"
            target_output_dir.mkdir(parents=True)
            video_path = target_output_dir / "after_refine.mp4"
            video_path.write_bytes(b"demo")

            exp_cfg_root = repo_dir / "exp_cfg"
            exp_cfg_root.mkdir()
            base_cfg_path = exp_cfg_root / "base.yaml"
            base_cfg_path.write_text("base_dir: outputs/default\nexp_name: default\n", encoding="utf-8")

            wrong_cfg = exp_cfg_root / "wrong.yaml"
            wrong_cfg.write_text(
                "base_dir: outputs/other_base\nexp_name: demo_exp\n",
                encoding="utf-8",
            )
            right_cfg = exp_cfg_root / "right.yaml"
            right_cfg.write_text(
                "base_dir: outputs/demo_base\nexp_name: demo_exp\n",
                encoding="utf-8",
            )

            discovered = discover_exp_cfg_path(
                video_path=video_path,
                exp_cfg_root=exp_cfg_root,
                base_cfg_path=base_cfg_path,
                repo_dir=repo_dir,
            )

            self.assertEqual(discovered, right_cfg.resolve())

    def test_compare_camera_trajectories_reports_translation_only_offset(self) -> None:
        actual = np.repeat(np.eye(4, dtype=np.float64)[None, ...], 3, axis=0)
        sidecar = actual.copy()
        sidecar[:, 0, 3] -= 2.5

        comparison = compare_camera_trajectories(actual, sidecar)

        self.assertAlmostEqual(comparison["translation_diff_mean"], 2.5, places=6)
        self.assertAlmostEqual(comparison["rotation_matrix_diff_max"], 0.0, places=6)

    def test_build_frame_record_contains_expected_time_and_quaternion(self) -> None:
        c2w = np.eye(4, dtype=np.float64)
        intrinsics = np.array(
            [
                [1000.0, 0.0, 640.0],
                [0.0, 1000.0, 360.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

        record = build_frame_record(
            frame_index=3,
            dataset_index=5,
            parser_index=17,
            fps=12.0,
            image_name="frame_017.png",
            image_path="/tmp/frame_017.png",
            image_size=(1280, 720),
            intrinsics=intrinsics,
            camera_to_world=c2w,
        )

        self.assertAlmostEqual(record["time_sec"], 0.25, places=6)
        self.assertEqual(record["quaternion_wxyz"], [1.0, 0.0, 0.0, 0.0])
        self.assertEqual(record["image_size"], [1280, 720])

    def test_resolve_output_path_defaults_to_video_sidecar_json(self) -> None:
        video_path = Path("/tmp/demo/after_refine.mp4")

        output_path = resolve_output_path(video_path, None)

        self.assertEqual(output_path.name, "after_refine_camera_trajectory.json")

    def test_resolve_unity_output_path_appends_unity_suffix(self) -> None:
        output_path = Path("/tmp/demo/after_refine_camera_trajectory.json")

        unity_output_path = resolve_unity_output_path(output_path)

        self.assertEqual(unity_output_path.name, "after_refine_camera_trajectory_unity.json")

    def test_resolve_cli_path_falls_back_to_repo_relative_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir)
            target = repo_dir / "configs" / "demo.yaml"
            target.parent.mkdir(parents=True)
            target.write_text("demo: true\n", encoding="utf-8")

            resolved = resolve_cli_path(Path("configs/demo.yaml"), repo_dir=repo_dir)

            self.assertEqual(resolved, target.resolve())

    def test_build_unity_payload_uses_xyzw_and_flattened_matrices(self) -> None:
        source_payload = {
            "output": {"path": "/tmp/after_refine_camera_trajectory.json"},
            "video": {"name": "after_refine.mp4"},
            "refine": {"exp_name": "demo"},
            "frames": [
                {
                    "frame_index": 0,
                    "time_sec": 0.0,
                    "dataset_index": 0,
                    "parser_index": 1,
                    "image_name": "000.png",
                    "image_path": "/tmp/000.png",
                    "image_size": [1280, 720],
                    "position": [1.0, 2.0, 3.0],
                    "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                    "camera_to_world": [
                        [1.0, 0.0, 0.0, 1.0],
                        [0.0, 1.0, 0.0, 2.0],
                        [0.0, 0.0, 1.0, 3.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                    "intrinsics": [
                        [1000.0, 0.0, 640.0],
                        [0.0, 1000.0, 360.0],
                        [0.0, 0.0, 1.0],
                    ],
                }
            ],
        }

        payload = build_unity_payload(
            source_payload=source_payload,
            unity_output_path=Path("/tmp/after_refine_camera_trajectory_unity.json"),
        )

        frame = payload["frames"][0]
        self.assertEqual(frame["quaternionXyzw"], [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(
            frame["cameraToWorldRowMajor"],
            [1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 2.0, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, 0.0, 1.0],
        )
        self.assertEqual(
            frame["cameraToWorldColumnMajor"],
            [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 2.0, 3.0, 1.0],
        )


if __name__ == "__main__":
    unittest.main()
