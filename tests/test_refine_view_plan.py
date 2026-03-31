import unittest
from types import SimpleNamespace

from ours.refine_run_schedule import build_real_train_pool, build_refine_view_plan
from recon.refine_view_plan import build_split_index_plan, coerce_named_splits


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


if __name__ == "__main__":
    unittest.main()
