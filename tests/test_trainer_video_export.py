import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from recon.trainer import (
    Runner,
    is_scheduled_training_step,
    publish_render_videos,
    resolve_render_traj_range,
)


class TrainerVideoExportTest(unittest.TestCase):
    def test_is_scheduled_training_step_uses_one_based_config_steps(self) -> None:
        self.assertTrue(is_scheduled_training_step(8999, [9000, 12000]))
        self.assertTrue(is_scheduled_training_step(11999, [9000, 12000]))
        self.assertFalse(is_scheduled_training_step(9000, [9000, 12000]))
        self.assertFalse(is_scheduled_training_step(11999, []))

    def test_resolve_render_traj_range_clamps_end_to_dataset_length(self) -> None:
        selected = list(resolve_render_traj_range(41, start_idx=30, end_idx=80))

        self.assertEqual(selected[0], 30)
        self.assertEqual(selected[-1], 40)
        self.assertEqual(len(selected), 11)

    def test_resolve_render_traj_range_rejects_empty_slice(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid render trajectory range"):
            resolve_render_traj_range(41, start_idx=41, end_idx=41)

    def test_publish_render_videos_keeps_latest_and_checkpoint_named_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_dir = Path(tmp_dir)
            ckpt_dir = save_dir / "ckpt_11999"
            ckpt_dir.mkdir()

            render_path = ckpt_dir / "render.mp4"
            alpha_path = ckpt_dir / "alpha.mp4"
            render_path.write_bytes(b"render-demo")
            alpha_path.write_bytes(b"alpha-demo")

            published = publish_render_videos(
                render_path=str(render_path),
                alpha_path=str(alpha_path),
                save_dir=str(save_dir),
                checkpoint_step=11999,
            )

            self.assertEqual((save_dir / "render.mp4").read_bytes(), b"render-demo")
            self.assertEqual((save_dir / "alpha.mp4").read_bytes(), b"alpha-demo")
            self.assertEqual((save_dir / "render_ckpt_11999.mp4").read_bytes(), b"render-demo")
            self.assertEqual((save_dir / "alpha_ckpt_11999.mp4").read_bytes(), b"alpha-demo")
            self.assertEqual(published["render"], str(save_dir / "render_ckpt_11999.mp4"))
            self.assertEqual(published["alpha"], str(save_dir / "alpha_ckpt_11999.mp4"))

    def test_maybe_render_training_video_uses_configured_schedule_and_paths(self) -> None:
        runner = Runner.__new__(Runner)
        runner.cfg = SimpleNamespace(
            render_video_steps=[9000],
            result_dir="outputs/demo",
            render_video_interp=2,
            render_video_start_idx=3,
            render_video_end_idx=9,
        )

        calls = []

        def fake_render_traj(**kwargs):
            calls.append(kwargs)

        runner.render_traj = fake_render_traj

        self.assertFalse(Runner.maybe_render_training_video(runner, 100))
        self.assertEqual(calls, [])

        self.assertTrue(Runner.maybe_render_training_video(runner, 8999))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["save_dir"], os.path.join("outputs/demo", "to_refine"))
        self.assertEqual(calls[0]["interp"], 2)
        self.assertEqual(calls[0]["checkpoint_step"], 8999)
        self.assertEqual(calls[0]["start_idx"], 3)
        self.assertEqual(calls[0]["end_idx"], 9)


if __name__ == "__main__":
    unittest.main()
