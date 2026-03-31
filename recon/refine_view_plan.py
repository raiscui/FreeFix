from typing import Any, Mapping, Optional, Sequence, Tuple


def coerce_named_splits(
    raw_value: Optional[str | Sequence[str]],
    *,
    default: Sequence[str],
) -> Tuple[str, ...]:
    """把 split 配置统一整理成去重后的名称元组。

    支持:
    - `None` -> 回退默认值
    - `"train,test"` 这种逗号分隔字符串
    - `["train", "test"]` 这种显式列表
    - `"all"` -> 展开成 `("train", "test")`
    """
    if raw_value is None:
        tokens = [str(item).strip() for item in default]
    elif isinstance(raw_value, str):
        tokens = [item.strip() for item in raw_value.split(",")]
    else:
        tokens = [str(item).strip() for item in raw_value]

    expanded: list[str] = []
    for token in tokens:
        if not token:
            continue
        if token == "all":
            expanded.extend(["train", "test"])
            continue
        expanded.append(token)

    if not expanded:
        raise ValueError("split 配置不能为空")

    deduped: list[str] = []
    seen: set[str] = set()
    for token in expanded:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)

    return tuple(deduped)


def build_split_index_plan(
    split_lengths: Mapping[str, int],
    *,
    splits: Sequence[str],
    repeats_per_item: int = 1,
) -> list[dict[str, Any]]:
    """按照 split 长度构造稳定的渲染 / refine 计划。

    每个基镜头会展开成 `repeats_per_item` 条计划项。
    计划项顺序固定, 便于:
    - 输出文件命名
    - checkpoint 继续训练
    - 后续日志回放与复盘
    """
    repeat_count = int(repeats_per_item)
    if repeat_count < 1:
        raise ValueError(f"repeats_per_item 必须 >= 1, 当前得到: {repeats_per_item}")

    plan: list[dict[str, Any]] = []
    plan_index = 0
    for split in splits:
        if split not in split_lengths:
            raise KeyError(f"split_lengths 缺少 split={split} 的长度")
        split_length = int(split_lengths[split])
        if split_length < 0:
            raise ValueError(f"split={split} 的长度不能为负数, 当前得到: {split_length}")

        for source_index in range(split_length):
            for repeat_index in range(repeat_count):
                plan.append(
                    {
                        "plan_index": plan_index,
                        "source_split": split,
                        "source_index": source_index,
                        "source_repeat_index": repeat_index,
                        "image_id": f"gen_{plan_index}",
                    }
                )
                plan_index += 1

    return plan
