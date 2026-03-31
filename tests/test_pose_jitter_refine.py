import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from ours.refine_by_flux import append_pose_jitter_log as append_flux_pose_jitter_log
from ours.refine_by_sdxl import append_pose_jitter_log as append_sdxl_pose_jitter_log
from recon.pose_jitter import (
    coerce_pose_jitter_triplet,
    compute_alpha_coverage,
    sample_bounded_pose_jitter,
    select_pose_jitter_candidate,
)


class PoseJitterHelperTest(unittest.TestCase):
    def test_coerce_pose_jitter_triplet_accepts_scalar(self) -> None:
        self.assertEqual(
            coerce_pose_jitter_triplet(0.1, name="pose_jitter_trans_sigma"),
            (0.1, 0.1, 0.1),
        )

    def test_coerce_pose_jitter_triplet_rejects_non_triplet_sequence(self) -> None:
        with self.assertRaisesRegex(ValueError, "长度为 3"):
            coerce_pose_jitter_triplet([0.1, 0.2], name="pose_jitter_rot_max_deg")

    def test_sample_bounded_pose_jitter_clamps_long_tail_values(self) -> None:
        with patch(
            "recon.pose_jitter.np.random.normal",
            side_effect=[
                np.asarray([0.2, -0.3, 0.01], dtype=np.float64),
                np.asarray([10.0, -6.0, 1.0], dtype=np.float64),
            ],
        ):
            trans, rots = sample_bounded_pose_jitter(
                trans_sigma=(0.02, 0.02, 0.02),
                trans_max=(0.05, 0.05, 0.05),
                rot_sigma_deg=(1.5, 1.5, 1.5),
                rot_max_deg=(4.0, 4.0, 4.0),
            )

        self.assertEqual(trans, (0.05, -0.05, 0.01))
        self.assertEqual(rots, (4.0, -4.0, 1.0))

    def test_compute_alpha_coverage_counts_pixels_above_threshold(self) -> None:
        alpha = torch.tensor([[0.00, 0.10], [0.06, 0.01]], dtype=torch.float32)
        coverage = compute_alpha_coverage(alpha, alpha_threshold=0.05)
        self.assertAlmostEqual(coverage, 0.5)

    def test_select_pose_jitter_candidate_accepts_safe_candidate(self) -> None:
        base_c2w = torch.full((4, 4), 7.0)
        candidates = [
            (
                torch.full((4, 4), 3.0),
                {"pose_jitter_trans": [0.1, 0.0, 0.0], "pose_jitter_rots": [0.0, 0.0, 0.0]},
            ),
            (
                torch.full((4, 4), 5.0),
                {"pose_jitter_trans": [0.01, 0.0, 0.0], "pose_jitter_rots": [1.0, 0.0, 0.0]},
            ),
        ]

        def build_candidate():
            return candidates.pop(0)

        def render_candidate(candidate_c2w):
            if float(candidate_c2w[0, 0].item()) == 3.0:
                alpha = torch.tensor([[0.01, 0.00], [0.00, 0.00]], dtype=torch.float32)
            else:
                alpha = torch.tensor([[0.20, 0.20], [0.20, 0.20]], dtype=torch.float32)
            return torch.zeros((2, 2, 3)), [], alpha, torch.zeros((2, 2, 1))

        chosen_c2w, _, sample_log = select_pose_jitter_candidate(
            base_c2w=base_c2w,
            build_candidate_fn=build_candidate,
            render_candidate_fn=render_candidate,
            alpha_threshold=0.05,
            min_alpha_coverage=0.50,
            max_attempts=2,
        )

        self.assertEqual(float(chosen_c2w[0, 0].item()), 5.0)
        self.assertFalse(sample_log["used_fallback"])
        self.assertEqual(sample_log["accepted_attempt_index"], 2)
        self.assertEqual(sample_log["pose_jitter_trans"], [0.01, 0.0, 0.0])
        self.assertEqual(len(sample_log["attempts"]), 2)

    def test_select_pose_jitter_candidate_falls_back_to_base_camera(self) -> None:
        base_c2w = torch.full((4, 4), 9.0)
        candidates = [
            (
                torch.full((4, 4), 3.0),
                {"pose_jitter_trans": [0.1, 0.0, 0.0], "pose_jitter_rots": [0.0, 0.0, 0.0]},
            ),
            (
                torch.full((4, 4), 5.0),
                {"pose_jitter_trans": [0.2, 0.0, 0.0], "pose_jitter_rots": [2.0, 0.0, 0.0]},
            ),
        ]

        def build_candidate():
            return candidates.pop(0)

        def render_candidate(candidate_c2w):
            marker = float(candidate_c2w[0, 0].item())
            if marker == 9.0:
                alpha = torch.tensor([[0.5, 0.5], [0.5, 0.5]], dtype=torch.float32)
            else:
                alpha = torch.tensor([[0.01, 0.00], [0.00, 0.00]], dtype=torch.float32)
            return torch.zeros((2, 2, 3)), [], alpha, torch.zeros((2, 2, 1))

        chosen_c2w, _, sample_log = select_pose_jitter_candidate(
            base_c2w=base_c2w,
            build_candidate_fn=build_candidate,
            render_candidate_fn=render_candidate,
            alpha_threshold=0.05,
            min_alpha_coverage=0.50,
            max_attempts=2,
        )

        self.assertEqual(float(chosen_c2w[0, 0].item()), 9.0)
        self.assertTrue(sample_log["used_fallback"])
        self.assertEqual(sample_log["fallback_reason"], "alpha_coverage_below_threshold")
        self.assertEqual(sample_log["pose_jitter_trans"], [0.0, 0.0, 0.0])
        self.assertEqual(len(sample_log["attempts"]), 2)


class PoseJitterLoggingTest(unittest.TestCase):
    def test_flux_pose_jitter_log_is_jsonl_appendable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "pose_jitter_log.jsonl"
            append_flux_pose_jitter_log(
                log_path,
                frame_index=3,
                cam_param={
                    "plan_index": 3,
                    "camera_mode": "pose_jitter",
                    "source_split": "train",
                    "source_index": 3,
                    "source_repeat_index": 2,
                    "source_image_name": "0003.png",
                    "image_id": "gen_3",
                    "sample_log": {"used_fallback": False, "attempt_count": 1},
                },
            )

            record = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(record["frame_index"], 3)
            self.assertEqual(record["plan_index"], 3)
            self.assertEqual(record["source_split"], "train")
            self.assertEqual(record["source_repeat_index"], 2)
            self.assertEqual(record["source_image_name"], "0003.png")
            self.assertEqual(record["image_id"], "gen_3")
            self.assertFalse(record["sample_log"]["used_fallback"])

    def test_sdxl_pose_jitter_log_is_jsonl_appendable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "pose_jitter_log.jsonl"
            append_sdxl_pose_jitter_log(
                log_path,
                frame_index=8,
                cam_param={
                    "plan_index": 8,
                    "camera_mode": "pose_jitter",
                    "source_split": "train",
                    "source_index": 8,
                    "source_repeat_index": 1,
                    "source_image_name": "0008.png",
                    "image_id": "gen_8",
                    "sample_log": {"used_fallback": True, "attempt_count": 4},
                },
            )

            record = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(record["frame_index"], 8)
            self.assertEqual(record["plan_index"], 8)
            self.assertEqual(record["source_index"], 8)
            self.assertEqual(record["source_repeat_index"], 1)
            self.assertEqual(record["image_id"], "gen_8")
            self.assertTrue(record["sample_log"]["used_fallback"])


if __name__ == "__main__":
    unittest.main()
