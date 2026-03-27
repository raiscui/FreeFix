import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recon.convert import (
    choose_best_sparse_model_dir,
    choose_feature_extraction_use_gpu_option,
    choose_feature_matching_use_gpu_option,
)


class ConvertCompatibilityTest(unittest.TestCase):
    def test_feature_extraction_prefers_new_colmap_4_option(self) -> None:
        help_text = """
        --FeatureExtraction.use_gpu arg (=1)
        --SiftExtraction.max_num_features arg (=8192)
        """
        self.assertEqual(
            choose_feature_extraction_use_gpu_option(help_text),
            "--FeatureExtraction.use_gpu",
        )

    def test_feature_extraction_falls_back_to_legacy_option(self) -> None:
        help_text = """
        --SiftExtraction.use_gpu arg (=1)
        --SiftExtraction.max_num_features arg (=8192)
        """
        self.assertEqual(
            choose_feature_extraction_use_gpu_option(help_text),
            "--SiftExtraction.use_gpu",
        )

    def test_feature_matching_prefers_new_colmap_4_option(self) -> None:
        help_text = """
        --FeatureMatching.use_gpu arg (=1)
        --SiftMatching.max_ratio arg (=0.8)
        """
        self.assertEqual(
            choose_feature_matching_use_gpu_option(help_text),
            "--FeatureMatching.use_gpu",
        )

    def test_feature_matching_falls_back_to_legacy_option(self) -> None:
        help_text = """
        --SiftMatching.use_gpu arg (=1)
        --SiftMatching.max_ratio arg (=0.8)
        """
        self.assertEqual(
            choose_feature_matching_use_gpu_option(help_text),
            "--SiftMatching.use_gpu",
        )

    def test_choose_best_sparse_model_dir_prefers_more_registered_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_zero = root / "0"
            model_one = root / "1"
            model_zero.mkdir()
            model_one.mkdir()
            (model_zero / "images.bin").touch()
            (model_zero / "points3D.bin").touch()
            (model_one / "images.bin").touch()
            (model_one / "points3D.bin").touch()

            with patch("recon.convert.load_registered_image_names") as mock_load_registered_image_names, patch(
                "recon.convert.read_points3d"
            ) as mock_read_points3d:
                mock_load_registered_image_names.side_effect = (
                    lambda model_dir: ["a", "b"]
                    if Path(model_dir).name == "0"
                    else [f"image_{index}" for index in range(264)]
                )
                mock_read_points3d.side_effect = (
                    lambda model_dir: [None] * 296
                    if Path(model_dir).name == "0"
                    else [None] * 27521
                )

                self.assertEqual(choose_best_sparse_model_dir(root), model_one)

    def test_choose_best_sparse_model_dir_accepts_model_files_directly_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "images.bin").touch()
            (root / "points3D.bin").touch()

            with patch("recon.convert.load_registered_image_names", return_value=["a", "b", "c"]), patch(
                "recon.convert.read_points3d",
                return_value=[None] * 10,
            ):
                self.assertEqual(choose_best_sparse_model_dir(root), root)

    def test_direct_script_execution_can_reach_argparse_help(self) -> None:
        result = subprocess.run(
            ["python3", "recon/convert.py", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Colmap converter", result.stdout)


if __name__ == "__main__":
    unittest.main()
