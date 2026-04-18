import unittest
from types import SimpleNamespace

from ours.refine_run_schedule import build_real_train_pool, build_refine_view_plan
from recon.refine_view_plan import (
    build_fractional_split_index_plan,
    build_split_index_plan,
    coerce_named_splits,
    coerce_non_negative_int,
    coerce_positive_int,
    coerce_views_per_source_fraction,
)


class RefineViewPlanHelperTest(unittest.TestCase):
    def test_coerce_named_splits_supports_all_and_dedup(self) -> None:
        self.assertEqual(
            coerce_named_splits("train,all,test", default=("train",)),
            ("train", "test"),
        )

    def test_build_split_index_plan_expands_repeats_per_item(self) -> None:
        plan = build_split_index_plan(
            {"train": 2, "test": 1},
            splits=("train", "test"),
            repeats_per_item=3,
        )

        self.assertEqual(len(plan), 9)
        self.assertEqual(plan[0], {
            "plan_index": 0,
            "source_split": "train",
            "source_index": 0,
            "source_repeat_index": 0,
            "image_id": "gen_0",
        })
        self.assertEqual(plan[4]["source_repeat_index"], 1)
        self.assertEqual(plan[-1], {
            "plan_index": 8,
            "source_split": "test",
            "source_index": 0,
            "source_repeat_index": 2,
            "image_id": "gen_8",
        })

    def test_coerce_views_per_source_fraction_supports_integer_and_fraction(self) -> None:
        self.assertEqual(coerce_views_per_source_fraction(3), (3, 1))
        self.assertEqual(coerce_views_per_source_fraction("1/4"), (1, 4))

    def test_coerce_positive_int_supports_int_and_string(self) -> None:
        self.assertEqual(coerce_positive_int(12, name="demo"), 12)
        self.assertEqual(coerce_positive_int("3", name="demo"), 3)

    def test_coerce_non_negative_int_supports_zero(self) -> None:
        self.assertEqual(coerce_non_negative_int(0, name="demo"), 0)
        self.assertEqual(coerce_non_negative_int("4", name="demo"), 4)

    def test_build_fractional_split_index_plan_keeps_stable_subset(self) -> None:
        plan = build_fractional_split_index_plan(
            {"train": 5, "test": 4},
            splits=("train", "test"),
            keep_numerator=1,
            keep_denominator=2,
        )

        self.assertEqual(
            plan,
            [
                {
                    "plan_index": 0,
                    "source_split": "train",
                    "source_index": 0,
                    "source_repeat_index": 0,
                    "image_id": "gen_0",
                },
                {
                    "plan_index": 1,
                    "source_split": "train",
                    "source_index": 2,
                    "source_repeat_index": 0,
                    "image_id": "gen_1",
                },
                {
                    "plan_index": 2,
                    "source_split": "train",
                    "source_index": 4,
                    "source_repeat_index": 0,
                    "image_id": "gen_2",
                },
                {
                    "plan_index": 3,
                    "source_split": "test",
                    "source_index": 0,
                    "source_repeat_index": 0,
                    "image_id": "gen_3",
                },
                {
                    "plan_index": 4,
                    "source_split": "test",
                    "source_index": 2,
                    "source_repeat_index": 0,
                    "image_id": "gen_4",
                },
            ],
        )

    def test_build_fractional_split_index_plan_supports_interleaved_blocks(self) -> None:
        plan = build_fractional_split_index_plan(
            {"train": 36},
            splits=("train",),
            keep_numerator=1,
            keep_denominator=2,
            block_size=12,
        )

        self.assertEqual(
            [entry["source_index"] for entry in plan],
            list(range(0, 12)) + list(range(24, 36)),
        )

    def test_build_fractional_split_index_plan_applies_start_offset_before_blocks(self) -> None:
        plan = build_fractional_split_index_plan(
            {"train": 40},
            splits=("train",),
            keep_numerator=1,
            keep_denominator=2,
            block_size=12,
            start_offset=5,
        )

        self.assertEqual(
            [entry["source_index"] for entry in plan],
            list(range(5, 17)) + list(range(29, 40)),
        )


class RefineRunScheduleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.refiner = SimpleNamespace()
        self.refiner.get_dataset_length = lambda split: {"train": 3, "test": 2}[split]
        self.refiner.get_dataset_item = lambda idx, *, split: {
            "split": split,
            "source_index": idx,
        }

    def test_build_real_train_pool_uses_all_named_splits(self) -> None:
        cfg = SimpleNamespace(
            refine_train_splits=("train", "test"),
            train_start_idx=0,
            train_end_idx=0,
        )

        train_cams, train_prob, info = build_real_train_pool(self.refiner, cfg)

        self.assertEqual(info["mode"], "all_views_from_named_splits")
        self.assertEqual(info["splits"], ("train", "test"))
        self.assertEqual(info["count"], 5)
        self.assertEqual(
            train_cams,
            [
                {"split": "train", "source_index": 0},
                {"split": "train", "source_index": 1},
                {"split": "train", "source_index": 2},
                {"split": "test", "source_index": 0},
                {"split": "test", "source_index": 1},
            ],
        )
        self.assertEqual(train_prob, [1.0, 1.0, 1.0, 1.0, 1.0])

    def test_build_refine_view_plan_uses_named_splits_and_repeat_count(self) -> None:
        cfg = SimpleNamespace(
            refine_camera_source_splits=("train", "test"),
            refine_camera_source_split="train",
            pose_jitter_views_per_source=3,
            refine_start_idx=0,
            refine_end_idx=2,
        )

        plan, info = build_refine_view_plan(self.refiner, cfg)

        self.assertEqual(info["mode"], "all_views_from_named_splits")
        self.assertEqual(info["splits"], ("train", "test"))
        self.assertEqual(info["repeats_per_source"], 3)
        self.assertEqual(info["count"], 15)
        self.assertEqual(plan[0]["image_id"], "gen_0")
        self.assertEqual(plan[2]["source_repeat_index"], 2)
        self.assertEqual(plan[3]["source_split"], "train")
        self.assertEqual(plan[-1], {
            "plan_index": 14,
            "source_split": "test",
            "source_index": 1,
            "source_repeat_index": 2,
            "image_id": "gen_14",
        })

    def test_build_refine_view_plan_supports_fractional_source_density(self) -> None:
        cfg = SimpleNamespace(
            refine_camera_source_splits=("train", "test"),
            refine_camera_source_split="train",
            pose_jitter_views_per_source="1/2",
            pose_jitter_source_interleaved_count=1,
            refine_start_idx=0,
            refine_end_idx=2,
        )

        plan, info = build_refine_view_plan(self.refiner, cfg)

        self.assertEqual(info["mode"], "fractional_views_from_named_splits")
        self.assertEqual(info["splits"], ("train", "test"))
        self.assertEqual(info["repeats_per_source"], "1/2")
        self.assertEqual(info["source_density"], "1/2")
        self.assertEqual(info["source_interleaved_count"], 1)
        self.assertEqual(info["count"], 3)
        self.assertEqual(
            plan,
            [
                {
                    "plan_index": 0,
                    "source_split": "train",
                    "source_index": 0,
                    "source_repeat_index": 0,
                    "image_id": "gen_0",
                },
                {
                    "plan_index": 1,
                    "source_split": "train",
                    "source_index": 2,
                    "source_repeat_index": 0,
                    "image_id": "gen_1",
                },
                {
                    "plan_index": 2,
                    "source_split": "test",
                    "source_index": 0,
                    "source_repeat_index": 0,
                    "image_id": "gen_2",
                },
            ],
        )

    def test_build_refine_view_plan_supports_fractional_interleaved_blocks(self) -> None:
        refiner = SimpleNamespace()
        refiner.get_dataset_length = lambda split: {"train": 36}[split]
        refiner.get_dataset_item = lambda idx, *, split: {"split": split, "source_index": idx}
        cfg = SimpleNamespace(
            refine_camera_source_splits=("train",),
            refine_camera_source_split="train",
            pose_jitter_views_per_source="1/2",
            pose_jitter_source_interleaved_count=12,
            refine_start_idx=0,
            refine_end_idx=2,
        )

        plan, info = build_refine_view_plan(refiner, cfg)

        self.assertEqual(info["mode"], "fractional_views_from_named_splits")
        self.assertEqual(info["source_density"], "1/2")
        self.assertEqual(info["source_interleaved_count"], 12)
        self.assertEqual(info["count"], 24)
        self.assertEqual(
            [entry["source_index"] for entry in plan],
            list(range(0, 12)) + list(range(24, 36)),
        )

    def test_build_refine_view_plan_skips_prefix_before_fractional_interleaved_sampling(self) -> None:
        refiner = SimpleNamespace()
        refiner.get_dataset_length = lambda split: {"train": 40}[split]
        refiner.get_dataset_item = lambda idx, *, split: {"split": split, "source_index": idx}
        cfg = SimpleNamespace(
            refine_camera_source_splits=("train",),
            refine_camera_source_split="train",
            pose_jitter_source_skip_first_count=5,
            pose_jitter_views_per_source="1/2",
            pose_jitter_source_interleaved_count=12,
            refine_start_idx=0,
            refine_end_idx=2,
        )

        plan, info = build_refine_view_plan(refiner, cfg)

        self.assertEqual(info["mode"], "fractional_views_from_named_splits")
        self.assertEqual(info["source_skip_first_count"], 5)
        self.assertEqual(info["source_interleaved_count"], 12)
        self.assertEqual(info["count"], 23)
        self.assertEqual(
            [entry["source_index"] for entry in plan],
            list(range(5, 17)) + list(range(29, 40)),
        )


if __name__ == "__main__":
    unittest.main()
