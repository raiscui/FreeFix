import json
import tempfile
import unittest
from pathlib import Path

import torch
from PIL import Image

from recon.refine_runtime import (
    append_generated_camera_record,
    build_generated_camera_log_path,
    build_refine_resume_checkpoint_path,
    build_refine_resume_state,
    build_refine_resume_state_path,
    cleanup_stale_resume_artifacts,
    load_refine_resume_state,
    resolve_strategy_resume_step,
    resolve_strategy_step,
    restore_completed_generated_cams,
    save_refine_resume_state,
)


class RefineRuntimeStepTest(unittest.TestCase):
    def test_payload_step_has_priority_when_checkpoint_records_real_step(self) -> None:
        self.assertEqual(
            resolve_strategy_resume_step(payload_step=34999, load_step=12000),
            34999,
        )

    def test_negative_payload_step_falls_back_to_load_step(self) -> None:
        self.assertEqual(
            resolve_strategy_resume_step(payload_step=-1, load_step=29999),
            29999,
        )

    def test_string_load_step_is_allowed_when_payload_step_is_present(self) -> None:
        self.assertEqual(
            resolve_strategy_resume_step(payload_step=50000, load_step="flux_demo"),
            50000,
        )

    def test_string_load_step_can_fall_back_to_numeric_cfg_step(self) -> None:
        self.assertEqual(
            resolve_strategy_resume_step(
                payload_step=None,
                load_step="flux_demo",
                fallback_load_step=50000,
            ),
            50000,
        )

    def test_non_numeric_string_load_step_raises_clear_error_without_payload_step(self) -> None:
        with self.assertRaisesRegex(ValueError, "checkpoint 未记录有效 step"):
            resolve_strategy_resume_step(payload_step=None, load_step="flux_demo")

    def test_strategy_step_continues_original_training_timeline(self) -> None:
        resume_step = resolve_strategy_resume_step(payload_step=34999, load_step=12000)
        self.assertEqual(
            resolve_strategy_step(strategy_resume_step=resume_step, local_step=0),
            34999,
        )
        self.assertEqual(
            resolve_strategy_step(strategy_resume_step=resume_step, local_step=4),
            35003,
        )


class RefineRuntimeStateTest(unittest.TestCase):
    def test_path_helpers_follow_expected_layout(self) -> None:
        output_dir = Path("/tmp/freefix/outputs/demo")
        self.assertEqual(
            build_refine_resume_state_path(output_dir),
            output_dir / "refine_resume_state.json",
        )
        self.assertEqual(
            build_generated_camera_log_path(output_dir),
            output_dir / "refine" / "generated_cams.jsonl",
        )
        self.assertEqual(
            build_refine_resume_checkpoint_path("/tmp/freefix", "demo"),
            Path("/tmp/freefix/ckpts/ckpt_demo__resume_latest.pt"),
        )

    def test_build_refine_resume_state_marks_complete_when_final_ckpt_exists(self) -> None:
        state = build_refine_resume_state(
            exp_name="demo",
            plan_total=6,
            next_plan_index=6,
            before_refine_complete=True,
            synthetic_complete=True,
            after_refine_complete=True,
            resume_ckpt_path="/tmp/resume.pt",
            final_ckpt_path="/tmp/final.pt",
        )

        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["latest_completed_plan_index"], 5)
        self.assertTrue(state["after_refine_complete"])
        self.assertEqual(state["final_ckpt_path"], "/tmp/final.pt")

    def test_save_and_load_resume_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = build_refine_resume_state_path(tmp_dir)
            expected_state = build_refine_resume_state(
                exp_name="demo",
                plan_total=3,
                next_plan_index=1,
                before_refine_complete=True,
                synthetic_complete=False,
                after_refine_complete=False,
                resume_ckpt_path="/tmp/demo_resume.pt",
            )

            save_refine_resume_state(state_path, expected_state)
            loaded_state = load_refine_resume_state(state_path)

            self.assertEqual(loaded_state["exp_name"], "demo")
            self.assertEqual(loaded_state["next_plan_index"], 1)
            self.assertEqual(loaded_state["resume_ckpt_path"], "/tmp/demo_resume.pt")
            self.assertEqual(loaded_state["status"], "synthetic_in_progress")


class RefineRuntimeArtifactCleanupTest(unittest.TestCase):
    def _write_frame(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (2, 2), (120, 10, 30)).save(path)

    def _write_jsonl(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )

    def test_cleanup_stale_resume_artifacts_truncates_files_after_resume_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            for stem in ("000", "001", "002"):
                self._write_frame(output_dir / "refine" / "render" / f"{stem}.jpg")
                self._write_frame(output_dir / "refine" / "depth" / f"{stem}.jpg")
                self._write_frame(output_dir / "refine" / "masks" / "0.1" / f"{stem}.jpg")
                self._write_frame(output_dir / "refine" / "masks" / "0.2" / f"{stem}.jpg")
                self._write_frame(output_dir / "refine" / "gen" / f"image_{stem}.jpg")

            gen_video_path = output_dir / "refine" / "gen.mp4"
            gen_video_path.parent.mkdir(parents=True, exist_ok=True)
            gen_video_path.write_bytes(b"fake-video")

            self._write_jsonl(
                output_dir / "refine" / "pose_jitter_log.jsonl",
                [
                    {"plan_index": 0, "value": "keep"},
                    {"plan_index": 1, "value": "keep"},
                    {"plan_index": 2, "value": "drop"},
                ],
            )
            self._write_jsonl(
                build_generated_camera_log_path(output_dir),
                [
                    {"plan_index": 0, "value": "keep"},
                    {"plan_index": 1, "value": "keep"},
                    {"plan_index": 2, "value": "drop"},
                ],
            )

            cleanup_stale_resume_artifacts(
                output_dir,
                next_plan_index=2,
                c_exp_index=[0.1, 0.2],
            )

            self.assertTrue((output_dir / "refine" / "render" / "000.jpg").exists())
            self.assertTrue((output_dir / "refine" / "render" / "001.jpg").exists())
            self.assertFalse((output_dir / "refine" / "render" / "002.jpg").exists())
            self.assertFalse((output_dir / "refine" / "gen" / "image_002.jpg").exists())
            self.assertFalse(gen_video_path.exists())

            pose_records = [
                json.loads(line)
                for line in (output_dir / "refine" / "pose_jitter_log.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            generated_records = [
                json.loads(line)
                for line in build_generated_camera_log_path(output_dir).read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["plan_index"] for record in pose_records], [0, 1])
            self.assertEqual([record["plan_index"] for record in generated_records], [0, 1])


class RefineRuntimeGeneratedCameraTest(unittest.TestCase):
    def _write_gen_image(self, output_dir: Path, plan_index: int, color: tuple[int, int, int]) -> None:
        image_path = output_dir / "refine" / "gen" / f"image_{plan_index:03d}.jpg"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (3, 2), color).save(image_path)

    def test_append_and_restore_generated_cams_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            log_path = build_generated_camera_log_path(output_dir)

            append_generated_camera_record(
                log_path,
                plan_index=0,
                cam_param={
                    "image_id": "gen_0",
                    "camera_mode": "pose_jitter",
                    "source_split": "train",
                    "source_index": 0,
                    "source_repeat_index": 0,
                    "source_image_name": "0000.png",
                    "K": torch.eye(3, dtype=torch.float32),
                    "c2w": torch.eye(4, dtype=torch.float32),
                },
            )
            append_generated_camera_record(
                log_path,
                plan_index=1,
                cam_param={
                    "image_id": "gen_1",
                    "camera_mode": "pose_jitter",
                    "source_split": "train",
                    "source_index": 1,
                    "source_repeat_index": 0,
                    "source_image_name": "0001.png",
                    "K": torch.eye(3, dtype=torch.float32) * 2.0,
                    "c2w": torch.eye(4, dtype=torch.float32) * 3.0,
                },
            )

            self._write_gen_image(output_dir, 0, (255, 0, 0))
            self._write_gen_image(output_dir, 1, (0, 255, 0))

            restored_cams = restore_completed_generated_cams(
                log_path,
                output_dir / "refine" / "gen",
                keep_before_plan_index=1,
            )

            self.assertEqual(len(restored_cams), 1)
            restored = restored_cams[0]
            self.assertEqual(restored["image_id"], "gen_0")
            self.assertTrue(restored["Gen"])
            self.assertEqual(tuple(restored["image"].shape), (2, 3, 3))
            self.assertTrue(torch.equal(restored["K"], torch.eye(3, dtype=torch.float32)))
            self.assertTrue(torch.equal(restored["camtoworld"], torch.eye(4, dtype=torch.float32)))


if __name__ == "__main__":
    unittest.main()
