from typing import Any

from recon.refine_view_plan import build_split_index_plan, coerce_named_splits


def build_real_train_pool(refiner, cfg) -> tuple[list[dict[str, Any]], list[float], dict[str, Any]]:
    """构造 refine 的真实监督池。

    兼容两种模式:
    - 旧模式: 继续使用 `train_start_idx / train_end_idx`
    - 新模式: `refine_train_splits` 显式指定多个 split, 并默认吃满全部镜头
    """
    raw_train_splits = getattr(cfg, "refine_train_splits", None)
    if raw_train_splits is None:
        train_cams = [refiner.train_dataset[j] for j in range(cfg.train_start_idx, cfg.train_end_idx)]
        train_prob = [1.0 for _ in train_cams]
        return train_cams, train_prob, {
            "mode": "legacy_range",
            "splits": ("train",),
            "count": len(train_cams),
        }

    train_splits = coerce_named_splits(raw_train_splits, default=("train",))
    split_lengths = {split: refiner.get_dataset_length(split) for split in train_splits}
    plan = build_split_index_plan(split_lengths, splits=train_splits, repeats_per_item=1)

    train_cams = [
        refiner.get_dataset_item(spec["source_index"], split=spec["source_split"])
        for spec in plan
    ]
    train_prob = [1.0 for _ in train_cams]
    return train_cams, train_prob, {
        "mode": "all_views_from_named_splits",
        "splits": train_splits,
        "count": len(train_cams),
    }


def build_refine_view_plan(refiner, cfg) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """构造中间 synthetic supervise 的渲染计划。"""
    raw_source_splits = getattr(cfg, "refine_camera_source_splits", None)
    if raw_source_splits is None:
        source_split = getattr(cfg, "refine_camera_source_split", "train")
        plan = [
            {
                "plan_index": i - cfg.refine_start_idx,
                "source_split": source_split,
                "source_index": i,
                "source_repeat_index": 0,
                "image_id": f"gen_{i - cfg.refine_start_idx}",
            }
            for i in range(cfg.refine_start_idx, cfg.refine_end_idx)
        ]
        return plan, {
            "mode": "legacy_range",
            "splits": (source_split,),
            "repeats_per_source": 1,
            "count": len(plan),
        }

    source_splits = coerce_named_splits(
        raw_source_splits,
        default=(getattr(cfg, "refine_camera_source_split", "train"),),
    )
    repeats_per_source = int(getattr(cfg, "pose_jitter_views_per_source", 1))
    split_lengths = {split: refiner.get_dataset_length(split) for split in source_splits}
    plan = build_split_index_plan(
        split_lengths,
        splits=source_splits,
        repeats_per_item=repeats_per_source,
    )
    return plan, {
        "mode": "all_views_from_named_splits",
        "splits": source_splits,
        "repeats_per_source": repeats_per_source,
        "count": len(plan),
    }
