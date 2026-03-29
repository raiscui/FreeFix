from typing import Optional


def resolve_strategy_resume_step(
    *,
    payload_step: Optional[int],
    load_step: int,
) -> int:
    """解析 refine 恢复时应该沿用的训练步数基线。"""
    if payload_step is not None:
        normalized_payload_step = int(payload_step)
        if normalized_payload_step >= 0:
            return normalized_payload_step

    return max(0, int(load_step))


def resolve_strategy_step(
    *,
    strategy_resume_step: int,
    local_step: int,
) -> int:
    """把 refine 局部步数映射回原训练时间轴上的真实步数。"""
    return max(0, int(strategy_resume_step)) + max(0, int(local_step))
