import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ours.run_fastgs_refine import (
    build_arg_parser,
    build_bridge_command,
    build_refine_command,
    default_bridge_output_path,
    run_pipeline,
)


class RunFastGSRefineTest(unittest.TestCase):
    def test_parser_accepts_user_facing_path_args(self) -> None:
        parser = build_arg_parser()
        args = parser.parse_args(
            [
                "--exp-cfg",
                "exp_cfg/demo.yaml",
                "--colmap-path",
                "/tmp/demo_scene",
                "--ckpt-path",
                "/tmp/demo_fastgs.pth",
            ]
        )

        self.assertEqual(args.colmap_path, Path("/tmp/demo_scene"))
        self.assertEqual(args.ckpt_path, Path("/tmp/demo_fastgs.pth"))
        self.assertEqual(args.refine_backend, "flux")

    def test_default_bridge_output_path_uses_repo_outputs_dir(self) -> None:
        source_path = Path("/tmp/fastgs/ckpt_30000.pth")
        output_path = default_bridge_output_path(source_path)

        self.assertEqual(output_path.name, "ckpt_30000_freefix.pt")
        self.assertIn("outputs/fastgs_bridge", output_path.as_posix())

    def test_build_bridge_command_uses_ply_alias_for_ply_source(self) -> None:
        args = SimpleNamespace(
            colmap_path=Path("/tmp/scene"),
            data_factor=2,
            step=123,
            no_normalize=True,
        )
        source_path = Path("/tmp/run/point_cloud.ply")
        bridge_output = Path("/tmp/bridge.pt")

        command = build_bridge_command(args, source_path, bridge_output)

        self.assertEqual(command[:3], [sys.executable, "-m", "recon.import_fastgs"])
        self.assertIn("--ply-path", command)
        self.assertNotIn("--ckpt-path", command)
        self.assertIn("--no-normalize", command)

    def test_build_refine_command_uses_selected_backend(self) -> None:
        args = SimpleNamespace(
            refine_backend="sdxl",
            exp_cfg=Path("exp_cfg/demo.yaml"),
            base_cfg=Path("exp_cfg/base.yaml"),
            colmap_path=Path("/tmp/scene"),
        )
        bridge_output = Path("/tmp/bridge.pt")

        command = build_refine_command(args, bridge_output)

        self.assertEqual(command[:3], [sys.executable, "-m", "ours.refine_by_sdxl"])
        self.assertEqual(command[-1], str(bridge_output))

    def test_run_pipeline_runs_bridge_then_refine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_path = tmp_path / "ckpt_30000.pth"
            source_path.write_bytes(b"demo")
            scene_path = tmp_path / "scene"
            scene_path.mkdir()

            args = SimpleNamespace(
                source=None,
                ckpt_path=source_path,
                ply_path=None,
                colmap_path=scene_path,
                exp_cfg=tmp_path / "demo.yaml",
                base_cfg=tmp_path / "base.yaml",
                refine_backend="flux",
                bridge_output=None,
                data_factor=1,
                step=None,
                no_normalize=False,
                dry_run=False,
            )
            args.exp_cfg.write_text("demo: true\n", encoding="utf-8")
            args.base_cfg.write_text("demo: true\n", encoding="utf-8")

            executed_commands: list[list[str]] = []
            executed_cwds: list[Path] = []

            def fake_run(command, check, cwd):
                self.assertTrue(check)
                executed_commands.append(command)
                executed_cwds.append(cwd)
                return SimpleNamespace(returncode=0)

            with patch("ours.run_fastgs_refine.subprocess.run", side_effect=fake_run):
                bridge_output_path, commands = run_pipeline(args)

            self.assertEqual(len(executed_commands), 2)
            self.assertEqual(executed_commands, commands)
            self.assertTrue(all(Path(cwd) == Path(__file__).resolve().parents[1] for cwd in executed_cwds))
            self.assertIn("recon.import_fastgs", executed_commands[0])
            self.assertEqual(executed_commands[1][:3], [sys.executable, "-m", "ours.refine_by_flux"])
            self.assertEqual(executed_commands[1][-1], str(bridge_output_path))

    def test_direct_script_execution_can_reach_argparse_help(self) -> None:
        result = subprocess.run(
            ["python3", "ours/run_fastgs_refine.py", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("FastGS 导入并启动 FreeFix refine", result.stdout)


if __name__ == "__main__":
    unittest.main()
