import subprocess
import sys
import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ours.run_fastgs_refine import (
    build_arg_parser,
    build_bridge_command,
    build_export_command,
    build_refine_command,
    default_bridge_output_path,
    resolve_refined_artifact_paths,
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

    def test_parser_accepts_final_ply_output_arg(self) -> None:
        parser = build_arg_parser()
        args = parser.parse_args(
            [
                "--exp-cfg",
                "exp_cfg/demo.yaml",
                "--colmap-path",
                "/tmp/demo_scene",
                "--ckpt-path",
                "/tmp/demo_fastgs.pth",
                "--final-ply-output",
                "/tmp/final/demo.ply",
            ]
        )

        self.assertEqual(args.final_ply_output, Path("/tmp/final/demo.ply"))

    def test_default_bridge_output_path_uses_repo_outputs_dir(self) -> None:
        source_path = Path("/tmp/fastgs/ckpt_30000.pth")
        output_path = default_bridge_output_path(source_path)

        self.assertEqual(output_path.name, "ckpt_30000_freefix.pt")
        self.assertIn("outputs/fastgs_bridge", output_path.as_posix())

    def test_default_bridge_output_path_uses_parent_for_fastdropgs_checkpoint(self) -> None:
        source_path = Path("/tmp/fast-dropgs/my8_input_50k_from45k_resetopt/chkpnt50000.pth")
        output_path = default_bridge_output_path(source_path)

        self.assertEqual(
            output_path.name,
            "my8_input_50k_from45k_resetopt_chkpnt50000_freefix.pt",
        )
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

    def test_build_export_command_targets_export_cli(self) -> None:
        refined_ckpt = Path("/tmp/outputs/demo/ckpts/ckpt_flux_demo.pt")
        final_ply = Path("/tmp/outputs/demo/point_cloud_flux_demo.ply")

        command = build_export_command(refined_ckpt, final_ply)

        self.assertEqual(command[:3], [sys.executable, "-m", "recon.export_3dgs_ply"])
        self.assertEqual(command[-2:], ["--output", str(final_ply)])

    def test_resolve_refined_artifact_paths_prefers_result_dir_from_gs_cfg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            base_dir = tmp_path / "base"
            result_dir = tmp_path / "result"
            base_dir.mkdir()
            result_dir.mkdir()

            gs_cfg_path = base_dir / "cfg.json"
            gs_cfg_path.write_text(
                json.dumps({"result_dir": str(result_dir)}),
                encoding="utf-8",
            )

            base_cfg = tmp_path / "base.yaml"
            exp_cfg = tmp_path / "exp.yaml"
            base_cfg.write_text(
                "base_dir: {base_dir}\nexp_name: demo\n".format(base_dir=base_dir.as_posix()),
                encoding="utf-8",
            )
            exp_cfg.write_text("exp_name: flux_demo\n", encoding="utf-8")

            args = SimpleNamespace(
                base_cfg=base_cfg,
                exp_cfg=exp_cfg,
                final_ply_output=None,
            )

            refined_ckpt, final_ply = resolve_refined_artifact_paths(args)

            self.assertEqual(refined_ckpt, result_dir / "ckpts" / "ckpt_flux_demo.pt")
            self.assertEqual(final_ply, result_dir / "point_cloud_flux_demo.ply")

    def test_run_pipeline_runs_bridge_then_refine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_path = tmp_path / "ckpt_30000.pth"
            source_path.write_bytes(b"demo")
            scene_path = tmp_path / "scene"
            scene_path.mkdir()
            base_dir = tmp_path / "base"
            result_dir = tmp_path / "result"
            base_dir.mkdir()
            result_dir.mkdir(parents=True)
            (base_dir / "cfg.json").write_text(
                json.dumps({"result_dir": str(result_dir)}),
                encoding="utf-8",
            )

            args = SimpleNamespace(
                source=None,
                ckpt_path=source_path,
                ply_path=None,
                colmap_path=scene_path,
                exp_cfg=tmp_path / "demo.yaml",
                base_cfg=tmp_path / "base.yaml",
                refine_backend="flux",
                bridge_output=None,
                final_ply_output=None,
                data_factor=1,
                step=None,
                no_normalize=False,
                dry_run=False,
            )
            args.exp_cfg.write_text("exp_name: flux_demo\n", encoding="utf-8")
            args.base_cfg.write_text(
                "base_dir: {base_dir}\nexp_name: base_demo\ngs_cfg_file: cfg.json\n".format(
                    base_dir=base_dir.as_posix()
                ),
                encoding="utf-8",
            )

            executed_commands: list[list[str]] = []
            executed_cwds: list[Path] = []

            def fake_run(command, check, cwd):
                self.assertTrue(check)
                executed_commands.append(command)
                executed_cwds.append(cwd)
                return SimpleNamespace(returncode=0)

            with patch("ours.run_fastgs_refine.subprocess.run", side_effect=fake_run):
                bridge_output_path, final_ply_output_path, commands = run_pipeline(args)

            self.assertEqual(len(executed_commands), 3)
            self.assertEqual(executed_commands, commands)
            self.assertTrue(all(Path(cwd) == Path(__file__).resolve().parents[1] for cwd in executed_cwds))
            self.assertIn("recon.import_fastgs", executed_commands[0])
            self.assertEqual(executed_commands[1][:3], [sys.executable, "-m", "ours.refine_by_flux"])
            self.assertEqual(executed_commands[1][-1], str(bridge_output_path))
            self.assertEqual(executed_commands[2][:3], [sys.executable, "-m", "recon.export_3dgs_ply"])
            self.assertEqual(final_ply_output_path, result_dir / "point_cloud_flux_demo.ply")

    def test_direct_script_execution_can_reach_argparse_help(self) -> None:
        result = subprocess.run(
            ["python3", "ours/run_fastgs_refine.py", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("FastGS / fast-dropgs 导入并启动 FreeFix refine", result.stdout)


if __name__ == "__main__":
    unittest.main()
