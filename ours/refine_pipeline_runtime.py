from __future__ import annotations

from typing import Callable, Literal


PipelineOffloadMode = Literal["none", "model_cpu", "sequential_cpu"]
VALID_PIPELINE_OFFLOAD_MODES = ("none", "model_cpu", "sequential_cpu")


def normalize_pipeline_offload_mode(raw_mode: str | None) -> PipelineOffloadMode:
    """把配置里的 offload 模式规范化成稳定的小集合。"""
    mode = "none" if raw_mode is None else str(raw_mode).strip().lower()
    if mode not in VALID_PIPELINE_OFFLOAD_MODES:
        supported = ", ".join(VALID_PIPELINE_OFFLOAD_MODES)
        raise ValueError(
            f"不支持的 refine_pipeline_offload_mode: {raw_mode}. "
            f"可选值只有: {supported}"
        )
    return mode  # type: ignore[return-value]


def resolve_pipeline_execution_device(pipe) -> object:
    """优先取 diffusers 的 execution device, 兼容 offload hook。"""
    # `pipe.device` 在 offload 场景下常常仍然停在 CPU。
    # 真正参与推理的设备语义在 `_execution_device` 上。
    execution_device = getattr(pipe, "_execution_device", None)
    if execution_device is not None:
        return execution_device
    return getattr(pipe, "device", "cuda")


def configure_pipeline_offload(
    pipe,
    *,
    offload_mode: str | None,
    target_device: str = "cuda",
    log_fn: Callable[[str], None] | None = None,
):
    """按配置放置 pipeline, 同时保留统一日志边界。"""
    mode = normalize_pipeline_offload_mode(offload_mode)

    def emit(message: str) -> None:
        if log_fn is not None:
            log_fn(message)

    # `none` 保持旧行为, 这样老实验默认口径完全不变。
    if mode == "none":
        emit(f"开始执行 pipe.to({target_device})")
        pipe = pipe.to(target_device)
        emit(f"pipe.to({target_device}) 返回")
        return pipe

    # 这里故意不再调用 `pipe.to(cuda)`。
    # offload hook 会自己接管模块的迁移与回收。
    if mode == "model_cpu":
        emit(f"开始启用 enable_model_cpu_offload(device={target_device})")
        pipe.enable_model_cpu_offload(device=target_device)
        emit("enable_model_cpu_offload 返回")
        return pipe

    emit(f"开始启用 enable_sequential_cpu_offload(device={target_device})")
    pipe.enable_sequential_cpu_offload(device=target_device)
    emit("enable_sequential_cpu_offload 返回")
    return pipe
