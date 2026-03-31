import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from plyfile import PlyData, PlyElement

from recon.import_fastgs import (
    build_default_output_label,
    eval_real_sh_bases,
    extract_fastgs_checkpoint_splats,
    extract_fastgs_ply_splats,
    infer_checkpoint_source_format,
    infer_step_from_path,
    load_fastgs_source,
    rotate_real_sh_coefficients,
    quat_to_rotmat_wxyz,
    resolve_data_dir_arg,
    resolve_source_arg,
    save_freefix_checkpoint,
    transform_splats_to_freefix,
)


def write_minimal_fastgs_ply(path: Path) -> None:
    # 这里构造一个最小 FastGS / 3DGS PLY, 字段顺序和真实导出保持一致。
    dtype = [
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("nx", "f4"),
        ("ny", "f4"),
        ("nz", "f4"),
        ("f_dc_0", "f4"),
        ("f_dc_1", "f4"),
        ("f_dc_2", "f4"),
        ("f_rest_0", "f4"),
        ("f_rest_1", "f4"),
        ("f_rest_2", "f4"),
        ("f_rest_3", "f4"),
        ("f_rest_4", "f4"),
        ("f_rest_5", "f4"),
        ("opacity", "f4"),
        ("scale_0", "f4"),
        ("scale_1", "f4"),
        ("scale_2", "f4"),
        ("rot_0", "f4"),
        ("rot_1", "f4"),
        ("rot_2", "f4"),
        ("rot_3", "f4"),
    ]
    vertices = np.array(
        [
            (
                1.0,
                2.0,
                3.0,
                0.0,
                0.0,
                0.0,
                0.1,
                0.2,
                0.3,
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
                6.0,
                -1.5,
                0.4,
                0.5,
                0.6,
                1.0,
                0.0,
                0.0,
                0.0,
            )
        ],
        dtype=dtype,
    )
    PlyData([PlyElement.describe(vertices, "vertex")]).write(path)


class ImportFastGSTest(unittest.TestCase):
    def test_rotate_real_sh_coefficients_keeps_dc_only_unchanged(self) -> None:
        angle = math.pi / 3.0
        rotation = torch.tensor(
            [
                [math.cos(angle), -math.sin(angle), 0.0],
                [math.sin(angle), math.cos(angle), 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=torch.float32,
        )
        colors = torch.zeros((2, 16, 3), dtype=torch.float32)
        colors[:, 0, :] = torch.tensor(
            [[0.2, -0.4, 0.6], [1.0, 2.0, 3.0]],
            dtype=torch.float32,
        )

        rotated = rotate_real_sh_coefficients(colors, rotation)

        self.assertTrue(torch.allclose(rotated, colors, atol=1e-5))

    def test_rotate_real_sh_coefficients_preserves_view_dependent_function(self) -> None:
        angle = math.pi / 2.0
        rotation = torch.tensor(
            [
                [math.cos(angle), -math.sin(angle), 0.0],
                [math.sin(angle), math.cos(angle), 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=torch.float32,
        )
        generator = torch.Generator(device="cpu")
        generator.manual_seed(0)

        dirs = torch.randn((64, 3), dtype=torch.float32, generator=generator)
        dirs = dirs / torch.linalg.norm(dirs, dim=-1, keepdim=True).clamp_min(1e-12)
        rotated_dirs = dirs @ rotation.T

        colors = torch.randn((1, 16, 3), dtype=torch.float32, generator=generator)
        rotated_colors = rotate_real_sh_coefficients(colors, rotation)

        bases = eval_real_sh_bases(16, dirs)
        rotated_bases = eval_real_sh_bases(16, rotated_dirs)
        original_rgb = torch.einsum("mk,nkc->nmc", bases, colors)
        rotated_rgb = torch.einsum("mk,nkc->nmc", rotated_bases, rotated_colors)

        self.assertTrue(torch.allclose(rotated_rgb, original_rgb, atol=1e-4, rtol=1e-4))

    def test_resolve_source_arg_accepts_ckpt_path_alias(self) -> None:
        args = type(
            "Args",
            (),
            {
                "source": None,
                "ckpt_path": Path("/tmp/demo_ckpt.pth"),
                "ply_path": None,
            },
        )()
        self.assertEqual(resolve_source_arg(args), Path("/tmp/demo_ckpt.pth"))

    def test_resolve_data_dir_arg_accepts_colmap_path_alias(self) -> None:
        args = type(
            "Args",
            (),
            {
                "data_dir": None,
                "colmap_path": Path("/tmp/demo_colmap"),
            },
        )()
        self.assertEqual(resolve_data_dir_arg(args), Path("/tmp/demo_colmap"))

    def test_infer_step_from_path_supports_fastdropgs_checkpoint_name(self) -> None:
        self.assertEqual(
            infer_step_from_path(Path("/tmp/my8_input_50k_from45k_resetopt/chkpnt50000.pth")),
            50000,
        )

    def test_infer_checkpoint_source_format_marks_fastdropgs_checkpoint(self) -> None:
        source_format = infer_checkpoint_source_format(
            Path("/home/rais/fast-dropgs/output/demo/chkpnt50000.pth")
        )
        self.assertEqual(source_format, "fastdropgs_checkpoint")

    def test_build_default_output_label_uses_parent_for_fastdropgs_checkpoint(self) -> None:
        label = build_default_output_label(
            Path("/tmp/my8_input_50k_from45k_resetopt/chkpnt50000.pth"),
            "fastdropgs_checkpoint",
        )
        self.assertEqual(label, "my8_input_50k_from45k_resetopt_chkpnt50000")

    def test_extract_fastgs_checkpoint_splats_maps_capture_tuple(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ckpt_path = Path(tmp_dir) / "ckpt_12.pth"
            model_args = (
                3,
                torch.tensor([[1.0, 2.0, 3.0]], dtype=torch.float32),
                torch.tensor([[[0.1, 0.2, 0.3]]], dtype=torch.float32),
                torch.tensor([[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]], dtype=torch.float32),
                torch.tensor([[0.4, 0.5, 0.6]], dtype=torch.float32),
                torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32),
                torch.tensor([[-1.5]], dtype=torch.float32),
                torch.zeros((1,), dtype=torch.float32),
                torch.zeros((1, 1), dtype=torch.float32),
                torch.zeros((1, 1), dtype=torch.float32),
                torch.zeros((1, 1), dtype=torch.float32),
                {"state": {}, "param_groups": []},
                {"state": {}, "param_groups": []},
                np.float32(1.0),
            )
            torch.save((model_args, 12), ckpt_path)

            splats, step = extract_fastgs_checkpoint_splats(ckpt_path)

            self.assertEqual(step, 12)
            self.assertEqual(tuple(splats["means"].shape), (1, 3))
            self.assertEqual(tuple(splats["sh0"].shape), (1, 1, 3))
            self.assertEqual(tuple(splats["shN"].shape), (1, 2, 3))
            self.assertEqual(tuple(splats["scales"].shape), (1, 3))
            self.assertEqual(tuple(splats["quats"].shape), (1, 4))
            self.assertEqual(tuple(splats["opacities"].shape), (1,))

    def test_load_fastgs_source_marks_chkpnt_name_as_fastdropgs_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "my8_input_50k_from45k_resetopt"
            run_dir.mkdir()
            ckpt_path = run_dir / "chkpnt50000.pth"
            model_args = (
                3,
                torch.tensor([[1.0, 2.0, 3.0]], dtype=torch.float32),
                torch.tensor([[[0.1, 0.2, 0.3]]], dtype=torch.float32),
                torch.tensor([[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]], dtype=torch.float32),
                torch.tensor([[0.4, 0.5, 0.6]], dtype=torch.float32),
                torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32),
                torch.tensor([[-1.5]], dtype=torch.float32),
                torch.zeros((1,), dtype=torch.float32),
                torch.zeros((1, 1), dtype=torch.float32),
                torch.zeros((1, 1), dtype=torch.float32),
                torch.zeros((1, 1), dtype=torch.float32),
                {"state": {}, "param_groups": []},
                {"state": {}, "param_groups": []},
                np.float32(1.0),
            )
            torch.save((model_args, 50000), ckpt_path)

            splats, step, source_format = load_fastgs_source(ckpt_path)

            self.assertEqual(step, 50000)
            self.assertEqual(source_format, "fastdropgs_checkpoint")
            self.assertEqual(tuple(splats["means"].shape), (1, 3))

    def test_save_freefix_checkpoint_keeps_fastdropgs_source_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "out.pt"
            source_path = Path("/tmp/my8_input_50k_from45k_resetopt/chkpnt50000.pth")
            splats = {
                "means": torch.zeros((1, 3), dtype=torch.float32),
                "opacities": torch.zeros((1,), dtype=torch.float32),
                "quats": torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32),
                "scales": torch.zeros((1, 3), dtype=torch.float32),
                "sh0": torch.zeros((1, 1, 3), dtype=torch.float32),
                "shN": torch.zeros((1, 15, 3), dtype=torch.float32),
            }

            save_freefix_checkpoint(
                output_path=output_path,
                splats=splats,
                step=50000,
                source=source_path,
                source_format="fastdropgs_checkpoint",
                normalize_enabled=False,
            )
            payload = torch.load(output_path, map_location="cpu", weights_only=False)

            self.assertEqual(payload["source_format"], "fastdropgs_checkpoint")
            self.assertEqual(payload["step"], 50000)
            self.assertFalse(payload["normalized_for_freefix"])

    def test_extract_fastgs_ply_splats_restores_sh_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ply_path = Path(tmp_dir) / "point_cloud.ply"
            write_minimal_fastgs_ply(ply_path)

            splats, step = extract_fastgs_ply_splats(ply_path)

            self.assertEqual(step, 0)
            self.assertEqual(tuple(splats["means"].shape), (1, 3))
            self.assertEqual(tuple(splats["sh0"].shape), (1, 1, 3))
            self.assertEqual(tuple(splats["shN"].shape), (1, 2, 3))
            self.assertEqual(splats["shN"][0, 0, 0].item(), 1.0)
            self.assertEqual(splats["shN"][0, 1, 2].item(), 6.0)

    def test_transform_splats_to_freefix_applies_similarity_to_geometry(self) -> None:
        angle = math.pi / 2.0
        rotation = np.array(
            [
                [math.cos(angle), -math.sin(angle), 0.0],
                [math.sin(angle), math.cos(angle), 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )
        scale = 2.0
        translation = np.array([10.0, 20.0, 30.0], dtype=np.float32)
        transform = np.eye(4, dtype=np.float32)
        transform[:3, :3] = rotation * scale
        transform[:3, 3] = translation

        source = {
            "means": torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32),
            "opacities": torch.tensor([-1.0], dtype=torch.float32),
            "quats": torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32),
            "scales": torch.tensor([[0.0, 0.0, 0.0]], dtype=torch.float32),
            "sh0": torch.zeros((1, 1, 3), dtype=torch.float32),
            "shN": torch.zeros((1, 3, 3), dtype=torch.float32),
        }

        transformed = transform_splats_to_freefix(source, transform)

        self.assertTrue(
            torch.allclose(
                transformed["means"],
                torch.tensor([[10.0, 22.0, 30.0]], dtype=torch.float32),
                atol=1e-5,
            )
        )
        self.assertTrue(
            torch.allclose(
                transformed["scales"],
                torch.full((1, 3), math.log(2.0), dtype=torch.float32),
                atol=1e-5,
            )
        )
        expected_rot = torch.tensor(rotation, dtype=torch.float32).unsqueeze(0)
        actual_rot = quat_to_rotmat_wxyz(transformed["quats"])
        self.assertTrue(torch.allclose(actual_rot, expected_rot, atol=1e-5))

    def test_transform_splats_to_freefix_rotates_high_order_sh_with_geometry(self) -> None:
        angle = math.pi / 2.0
        rotation = np.array(
            [
                [math.cos(angle), -math.sin(angle), 0.0],
                [math.sin(angle), math.cos(angle), 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )
        transform = np.eye(4, dtype=np.float32)
        transform[:3, :3] = rotation

        generator = torch.Generator(device="cpu")
        generator.manual_seed(1)
        source = {
            "means": torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32),
            "opacities": torch.tensor([-1.0], dtype=torch.float32),
            "quats": torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32),
            "scales": torch.tensor([[0.0, 0.0, 0.0]], dtype=torch.float32),
            "sh0": torch.randn((1, 1, 3), dtype=torch.float32, generator=generator),
            "shN": torch.randn((1, 15, 3), dtype=torch.float32, generator=generator),
        }

        transformed = transform_splats_to_freefix(source, transform)

        dirs = torch.randn((64, 3), dtype=torch.float32, generator=generator)
        dirs = dirs / torch.linalg.norm(dirs, dim=-1, keepdim=True).clamp_min(1e-12)
        rotated_dirs = dirs @ torch.tensor(rotation, dtype=torch.float32).T

        original_colors = torch.cat([source["sh0"], source["shN"]], dim=1)
        transformed_colors = torch.cat([transformed["sh0"], transformed["shN"]], dim=1)
        bases = eval_real_sh_bases(16, dirs)
        rotated_bases = eval_real_sh_bases(16, rotated_dirs)
        original_rgb = torch.einsum("mk,nkc->nmc", bases, original_colors)
        transformed_rgb = torch.einsum("mk,nkc->nmc", rotated_bases, transformed_colors)

        self.assertTrue(
            torch.allclose(transformed_rgb, original_rgb, atol=1e-4, rtol=1e-4)
        )


if __name__ == "__main__":
    unittest.main()
