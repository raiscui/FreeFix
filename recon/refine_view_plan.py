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


def coerce_views_per_source_fraction(
    raw_value: Any,
    *,
    name: str = "pose_jitter_views_per_source",
) -> tuple[int, int]:
    """把 `views_per_source` 统一解析成正分数。

    支持两类输入:
    - 正整数: `1`, `2`, `3`
    - 正分数字符串: `1/2`, `1/3`, `2/3`

    返回值始终是 `(numerator, denominator)`。
    例如:
    - `3` -> `(3, 1)`
    - `"1/4"` -> `(1, 4)`
    """
    if isinstance(raw_value, bool):
        raise ValueError(f"{name} 不能使用布尔值: {raw_value}")

    numerator: int
    denominator: int
    if isinstance(raw_value, int):
        numerator = raw_value
        denominator = 1
    elif isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            raise ValueError(f"{name} 不能为空字符串")
        if "/" in text:
            parts = [part.strip() for part in text.split("/")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(
                    f"{name} 分数格式只支持 `a/b`, 当前得到: {raw_value}"
                )
            numerator = int(parts[0])
            denominator = int(parts[1])
        else:
            numerator = int(text)
            denominator = 1
    else:
        raise ValueError(
            f"{name} 只支持正整数或 `a/b` 分数字符串, 当前得到: {raw_value!r}"
        )

    if numerator < 1 or denominator < 1:
        raise ValueError(f"{name} 必须是正整数或正分数, 当前得到: {raw_value}")

    return numerator, denominator


def coerce_positive_int(
    raw_value: Any,
    *,
    name: str,
) -> int:
    """把配置里的正整数参数统一解析出来。"""
    if isinstance(raw_value, bool):
        raise ValueError(f"{name} 不能使用布尔值: {raw_value}")

    if isinstance(raw_value, int):
        value = raw_value
    elif isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            raise ValueError(f"{name} 不能为空字符串")
        value = int(text)
    else:
        raise ValueError(f"{name} 只支持正整数或整数字符串, 当前得到: {raw_value!r}")

    if value < 1:
        raise ValueError(f"{name} 必须 >= 1, 当前得到: {raw_value}")

    return value


def coerce_non_negative_int(
    raw_value: Any,
    *,
    name: str,
) -> int:
    """把配置里的非负整数参数统一解析出来。"""
    if isinstance(raw_value, bool):
        raise ValueError(f"{name} 不能使用布尔值: {raw_value}")

    if isinstance(raw_value, int):
        value = raw_value
    elif isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            raise ValueError(f"{name} 不能为空字符串")
        value = int(text)
    else:
        raise ValueError(f"{name} 只支持非负整数或整数字符串, 当前得到: {raw_value!r}")

    if value < 0:
        raise ValueError(f"{name} 必须 >= 0, 当前得到: {raw_value}")

    return value


def format_views_per_source_fraction(numerator: int, denominator: int) -> str:
    """把 `(numerator, denominator)` 格式化成稳定字符串。"""
    if denominator == 1:
        return str(numerator)
    return f"{numerator}/{denominator}"


def _build_plan_entry(
    *,
    plan_index: int,
    source_split: str,
    source_index: int,
    source_repeat_index: int,
) -> dict[str, Any]:
    """构造一条稳定的 synthetic plan 记录。"""
    return {
        "plan_index": plan_index,
        "source_split": source_split,
        "source_index": source_index,
        "source_repeat_index": source_repeat_index,
        "image_id": f"gen_{plan_index}",
    }


def build_split_index_plan(
    split_lengths: Mapping[str, int],
    *,
    splits: Sequence[str],
    repeats_per_item: int = 1,
    start_offset: int = 0,
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
    source_start_offset = int(start_offset)
    if source_start_offset < 0:
        raise ValueError(f"start_offset 必须 >= 0, 当前得到: {start_offset}")

    plan: list[dict[str, Any]] = []
    plan_index = 0
    for split in splits:
        if split not in split_lengths:
            raise KeyError(f"split_lengths 缺少 split={split} 的长度")
        split_length = int(split_lengths[split])
        if split_length < 0:
            raise ValueError(f"split={split} 的长度不能为负数, 当前得到: {split_length}")

        for source_index in range(source_start_offset, split_length):
            for repeat_index in range(repeat_count):
                plan.append(
                    _build_plan_entry(
                        plan_index=plan_index,
                        source_split=split,
                        source_index=source_index,
                        source_repeat_index=repeat_index,
                    )
                )
                plan_index += 1

    return plan


def build_fractional_split_index_plan(
    split_lengths: Mapping[str, int],
    *,
    splits: Sequence[str],
    keep_numerator: int,
    keep_denominator: int,
    block_size: int = 1,
    start_offset: int = 0,
) -> list[dict[str, Any]]:
    """按固定比例稳定抽样 source pool, 构造 synthetic plan。

    语义是“每 `keep_denominator` 个 block, 保留前 `keep_numerator` 个 block”。
    每个 block 默认只含 1 个 source；当 `block_size > 1` 时, 会按连续 block 稳定保留。
    例如:
    - `1/2` -> 保留索引 `0, 2, 4, ...`
    - `1/2` 且 `block_size=12` -> 保留 `0-11, 24-35, ...`
    - `2/3` -> 保留索引 `0, 1, 3, 4, 6, 7, ...`

    这样能保持:
    - 结果完全确定
    - plan 顺序稳定
    - resume / log / image_id 契约不变
    """
    numerator = int(keep_numerator)
    denominator = int(keep_denominator)
    if numerator < 1 or denominator < 1:
        raise ValueError(
            "fractional split plan 的分子分母都必须 >= 1, "
            f"当前得到: {keep_numerator}/{keep_denominator}"
        )
    if numerator > denominator:
        raise ValueError(
            "fractional split plan 当前只支持 `0 < 分数 <= 1`, "
            f"当前得到: {keep_numerator}/{keep_denominator}"
        )
    keep_block_size = int(block_size)
    if keep_block_size < 1:
        raise ValueError(
            "fractional split plan 的 block_size 必须 >= 1, "
            f"当前得到: {block_size}"
        )
    source_start_offset = int(start_offset)
    if source_start_offset < 0:
        raise ValueError(
            "fractional split plan 的 start_offset 必须 >= 0, "
            f"当前得到: {start_offset}"
        )

    plan: list[dict[str, Any]] = []
    plan_index = 0
    for split in splits:
        if split not in split_lengths:
            raise KeyError(f"split_lengths 缺少 split={split} 的长度")
        split_length = int(split_lengths[split])
        if split_length < 0:
            raise ValueError(f"split={split} 的长度不能为负数, 当前得到: {split_length}")

        remaining_length = max(split_length - source_start_offset, 0)
        for local_block_start in range(0, remaining_length, keep_block_size):
            block_index = local_block_start // keep_block_size
            if block_index % denominator >= numerator:
                continue

            block_start = source_start_offset + local_block_start
            block_end = min(block_start + keep_block_size, split_length)
            for source_index in range(block_start, block_end):
                plan.append(
                    _build_plan_entry(
                        plan_index=plan_index,
                        source_split=split,
                        source_index=source_index,
                        source_repeat_index=0,
                    )
                )
                plan_index += 1

    return plan
