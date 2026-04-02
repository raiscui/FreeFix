import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from ours.refine_by_kontext import (
    KONTEXT_MASK_THRESHOLD,
    build_kontext_edit_mask,
    build_kontext_generation_request,
    build_kontext_prompt,
    resolve_kontext_model_source,
    resolve_kontext_negative_prompt,
    resolve_kontext_reference_sample,
)


class KontextRefineHelperTest(unittest.TestCase):
    def test_resolve_kontext_model_source_prefers_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_dir = Path(tmp_dir) / "kontext"
            model_dir.mkdir()
            (model_dir / "model_index.json").write_text("{}", encoding="utf-8")

            cfg = SimpleNamespace(kontext_model_path=str(model_dir))
            source, local_files_only = resolve_kontext_model_source(cfg)

            self.assertEqual(source, str(model_dir))
            self.assertTrue(local_files_only)

    def test_build_kontext_edit_mask_uses_union_mask(self) -> None:
        masks = torch.tensor(
            [
                [[0.00, KONTEXT_MASK_THRESHOLD + 0.01], [0.00, 0.00]],
                [[0.00, 0.00], [KONTEXT_MASK_THRESHOLD + 0.02, 0.00]],
            ],
            dtype=torch.float32,
        )

        mask_image = build_kontext_edit_mask(masks)

        self.assertIsNotNone(mask_image)
        mask_array = np.asarray(mask_image)
        self.assertEqual(int(mask_array[0, 1]), 255)
        self.assertEqual(int(mask_array[1, 0]), 255)
        self.assertEqual(int(mask_array[0, 0]), 0)

    def test_build_kontext_generation_request_uses_inpaint_and_reference_when_available(self) -> None:
        rgb_to_refine = torch.zeros((3, 2, 2), dtype=torch.float32)
        masks = torch.tensor([[[0.0, 1.0], [0.0, 0.0]]], dtype=torch.float32)
        source_reference_sample = {
            "image": torch.full((2, 2, 3), 255, dtype=torch.uint8),
        }

        request = build_kontext_generation_request(
            prompt="repair",
            negative_prompt="",
            rgb_to_refine=rgb_to_refine,
            masks=masks,
            source_reference_sample=source_reference_sample,
            guidance_scale=2.5,
            num_inference_steps=28,
            generator=torch.Generator().manual_seed(7),
            strength=0.8,
            height=2,
            width=2,
        )

        self.assertEqual(request.mode, "inpaint")
        self.assertIn("mask_image", request.kwargs)
        self.assertIn("image_reference", request.kwargs)
        self.assertEqual(request.kwargs["image"].size, (2, 2))
        self.assertEqual(request.kwargs["image_reference"].size, (2, 2))

    def test_build_kontext_generation_request_uses_inpaint_without_reference_when_missing(self) -> None:
        rgb_to_refine = torch.zeros((3, 2, 2), dtype=torch.float32)
        masks = torch.tensor([[[0.0, 1.0], [0.0, 0.0]]], dtype=torch.float32)

        request = build_kontext_generation_request(
            prompt="repair",
            negative_prompt=None,
            rgb_to_refine=rgb_to_refine,
            masks=masks,
            source_reference_sample=None,
            guidance_scale=2.5,
            num_inference_steps=28,
            generator=torch.Generator().manual_seed(7),
            strength=0.8,
            height=2,
            width=2,
        )

        self.assertEqual(request.mode, "inpaint")
        self.assertNotIn("image_reference", request.kwargs)

    def test_build_kontext_generation_request_falls_back_to_edit_when_mask_is_empty(self) -> None:
        rgb_to_refine = torch.zeros((3, 2, 2), dtype=torch.float32)
        masks = torch.zeros((1, 2, 2), dtype=torch.float32)

        request = build_kontext_generation_request(
            prompt="repair",
            negative_prompt=None,
            rgb_to_refine=rgb_to_refine,
            masks=masks,
            source_reference_sample={
                "image": torch.full((2, 2, 3), 255, dtype=torch.uint8),
            },
            guidance_scale=2.5,
            num_inference_steps=28,
            generator=torch.Generator().manual_seed(7),
            strength=0.8,
            height=2,
            width=2,
        )

        self.assertEqual(request.mode, "edit")
        self.assertNotIn("mask_image", request.kwargs)
        self.assertNotIn("image_reference", request.kwargs)

    def test_build_kontext_prompt_prefers_kontext_prompt_override(self) -> None:
        cfg = SimpleNamespace(
            prompt="global prompt",
            kontext_prompt="clean silky polish",
        )

        prompt = build_kontext_prompt(cfg, has_reference=False)

        self.assertIn("clean silky polish", prompt)
        self.assertNotIn("global prompt", prompt)
        self.assertIn("Keep the current render clean", prompt)
        self.assertIn("silky-smooth", prompt)
        self.assertNotIn("Use the reference image only", prompt)

    def test_build_kontext_prompt_adds_reference_clause_when_reference_exists(self) -> None:
        cfg = SimpleNamespace(prompt="museum scene restoration")

        prompt = build_kontext_prompt(cfg, has_reference=True)

        self.assertIn("museum scene restoration", prompt)
        self.assertIn("Do not add detail or sharpen", prompt)
        self.assertIn("overall color and material", prompt)

    def test_resolve_kontext_negative_prompt_prefers_override(self) -> None:
        cfg = SimpleNamespace(
            negative_prompt="global blurry low quality",
            kontext_negative_prompt="extra details, oversharpening, busy texture",
        )

        negative_prompt = resolve_kontext_negative_prompt(cfg)

        self.assertEqual(
            negative_prompt,
            "extra details, oversharpening, busy texture",
        )

    def test_resolve_kontext_negative_prompt_falls_back_to_global_prompt(self) -> None:
        cfg = SimpleNamespace(negative_prompt="global blurry low quality")

        negative_prompt = resolve_kontext_negative_prompt(cfg)

        self.assertEqual(negative_prompt, "global blurry low quality")

    def test_resolve_kontext_reference_sample_reads_source_dataset_item(self) -> None:
        class FakeRefiner:
            def get_dataset_item(self, idx: int, *, split: str):
                return {"split": split, "index": idx}

        sample = resolve_kontext_reference_sample(
            FakeRefiner(),
            {
                "camera_mode": "pose_jitter",
                "source_index": 3,
                "source_split": "train",
            },
        )

        self.assertEqual(sample, {"split": "train", "index": 3})

    def test_resolve_kontext_reference_sample_skips_fixed_camera_mode(self) -> None:
        class FakeRefiner:
            def get_dataset_item(self, idx: int, *, split: str):
                return {"split": split, "index": idx}

        sample = resolve_kontext_reference_sample(
            FakeRefiner(),
            {
                "camera_mode": "fixed",
                "source_index": 3,
                "source_split": "train",
            },
        )

        self.assertIsNone(sample)


if __name__ == "__main__":
    unittest.main()
