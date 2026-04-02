from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ours.refine_backend_common import (
    apply_runtime_path_overrides,
    append_pose_jitter_log,
    build_refine_arg_parser,
    build_stage_logger,
    resolve_local_model_source,
    resolve_optional_checkpoint_path,
)
from ours.refine_backend_runner import BackendRuntime, run_backend_refine
from ours.refine_pipeline_runtime import (
    configure_pipeline_offload,
    normalize_pipeline_offload_mode,
    resolve_pipeline_execution_device,
)


DEFAULT_KONTEXT_REPO_ID = "black-forest-labs/FLUX.1-Kontext-dev"
DEFAULT_LOCAL_KONTEXT_PATHS = [
    Path("/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-Kontext-dev"),
    Path("/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-Kontext-dev"),
]
KONTEXT_MASK_THRESHOLD = 0.05
DEFAULT_KONTEXT_REPAIR_PROMPT = (
    "Keep the current render clean, silky-smooth, soft, and natural. Preserve viewpoint and geometry. "
    "Remove only ghosting, haze, blur streaks, and dirt. Do not add detail or sharpen."
)
DEFAULT_KONTEXT_REFERENCE_PROMPT = (
    "Use the reference only for overall color and material."
)


@dataclass
class KontextGenerationRequest:
    """把 Kontext 单轮调用整理成可测试的轻量结构。"""

    mode: str
    kwargs: dict[str, Any]


def _normalize_prompt_text(value: Any) -> str:
    """把 prompt 配置统一规整成可安全拼接的单行文本。"""
    if value is None:
        return ""
    return str(value).strip()


def _join_prompt_parts(*parts: str) -> str:
    """把多个 prompt 片段压成稳定单行, 避免 YAML 多行和多余空格污染模型输入。"""
    normalized_parts = [" ".join(part.split()) for part in parts if part and part.strip()]
    return " ".join(normalized_parts)


def build_kontext_prompt(cfg, *, has_reference: bool) -> str:
    """构造 Kontext 专用 prompt。

    设计目标:
    - `kontext_prompt` 负责承载场景主题或用户显式覆盖的短提示。
    - 固定修复指令负责把“修瑕疵 + 保持当前视角/结构”的语义说清楚。
    - 有 reference 图时, 再补一句“只参考原素材外观, 不改视角/构图”。
    """
    base_prompt = _normalize_prompt_text(getattr(cfg, "kontext_prompt", None))
    if not base_prompt:
        base_prompt = _normalize_prompt_text(getattr(cfg, "prompt", None))

    prompt_parts = [base_prompt, DEFAULT_KONTEXT_REPAIR_PROMPT]
    if has_reference:
        prompt_parts.append(DEFAULT_KONTEXT_REFERENCE_PROMPT)
    return _join_prompt_parts(*prompt_parts)


def resolve_kontext_negative_prompt(cfg) -> str | None:
    """解析 Kontext 专用 negative prompt。

    优先允许 Kontext 单独覆盖。
    没配时再回退现有全局 `negative_prompt`, 保持兼容。
    """
    kontext_negative_prompt = _normalize_prompt_text(getattr(cfg, "kontext_negative_prompt", None))
    if kontext_negative_prompt:
        return kontext_negative_prompt

    fallback_negative_prompt = _normalize_prompt_text(getattr(cfg, "negative_prompt", None))
    return fallback_negative_prompt or None


def resolve_kontext_model_source(cfg) -> tuple[str, bool]:
    """解析 Kontext 模型来源, 与 `flux_model_path` 保持独立。"""
    return resolve_local_model_source(
        cfg,
        config_attr="kontext_model_path",
        default_repo_id=DEFAULT_KONTEXT_REPO_ID,
        default_local_paths=DEFAULT_LOCAL_KONTEXT_PATHS,
        label="Kontext",
    )


def resolve_kontext_reference_sample(refiner, cam_param: dict[str, Any]) -> dict[str, Any] | None:
    """从当前 synthetic plan 里解析 source real image。"""
    camera_mode = str(cam_param.get("camera_mode", "")).strip().lower()
    if camera_mode not in ("", "pose_jitter"):
        return None

    source_index = cam_param.get("source_index")
    source_split = cam_param.get("source_split")
    if source_index is None or source_split in (None, ""):
        return None

    try:
        return refiner.get_dataset_item(int(source_index), split=str(source_split))
    except Exception:
        return None


def _tensor_to_pil_image(image_tensor, *, mode: str = "RGB"):
    """把 HWC / CHW torch tensor 规范化成 PIL Image。"""
    import torch
    from PIL import Image

    tensor = image_tensor.detach().float().cpu()
    if tensor.ndim == 3 and tensor.shape[0] in (1, 3):
        tensor = tensor.permute(1, 2, 0)
    if tensor.ndim == 3 and tensor.shape[-1] == 1:
        tensor = tensor[..., 0]
    if tensor.ndim not in (2, 3):
        raise ValueError(f"不支持的图像 tensor 形状: {tuple(tensor.shape)}")

    if mode == "RGB":
        array = tensor.clamp(0.0, 1.0).mul(255).round().to(torch.uint8).numpy()
        return Image.fromarray(array)

    array = tensor.clamp(0.0, 1.0).mul(255).round().to(torch.uint8).numpy()
    return Image.fromarray(array)


def build_kontext_edit_mask(masks) -> Any | None:
    """把当前私有多掩码语义折叠成 Kontext 可接受的一张保守 union mask。"""
    import torch

    if masks is None:
        return None

    tensor = masks.detach().float().cpu()
    if tensor.numel() == 0:
        return None
    if tensor.ndim == 2:
        merged = tensor
    elif tensor.ndim == 3:
        merged = torch.amax(tensor, dim=0)
    else:
        raise ValueError(f"不支持的掩码形状: {tuple(tensor.shape)}")

    binary_mask = (merged > KONTEXT_MASK_THRESHOLD).float()
    if float(binary_mask.max().item()) <= 0.0:
        return None
    return _tensor_to_pil_image(binary_mask, mode="L")


def build_kontext_generation_request(
    *,
    prompt: str,
    negative_prompt: str | None,
    rgb_to_refine,
    masks,
    source_reference_sample: dict[str, Any] | None,
    guidance_scale: float,
    num_inference_steps: int,
    generator,
    strength: float,
    height: int,
    width: int,
) -> KontextGenerationRequest:
    """根据 render / mask / source image 选择 Kontext 的调用路径。"""
    request_kwargs: dict[str, Any] = {
        "prompt": prompt,
        "image": _tensor_to_pil_image(rgb_to_refine, mode="RGB"),
        "height": height,
        "width": width,
        "guidance_scale": guidance_scale,
        "num_inference_steps": num_inference_steps,
        "generator": generator,
    }
    if negative_prompt is not None:
        request_kwargs["negative_prompt"] = negative_prompt

    mask_image = build_kontext_edit_mask(masks)
    if mask_image is None:
        return KontextGenerationRequest(mode="edit", kwargs=request_kwargs)

    request_kwargs["mask_image"] = mask_image
    request_kwargs["strength"] = float(strength)
    if source_reference_sample is not None and "image" in source_reference_sample:
        request_kwargs["image_reference"] = _tensor_to_pil_image(
            source_reference_sample["image"] / 255.0,
            mode="RGB",
        ).resize((width, height))
    return KontextGenerationRequest(mode="inpaint", kwargs=request_kwargs)


def build_backend_runtime(cfg, log_runtime_stage) -> BackendRuntime:
    """加载 Kontext pipeline, 并返回单轮编辑闭包。"""
    import torch
    from diffusers import FluxKontextInpaintPipeline, FluxKontextPipeline

    kontext_model_source, local_files_only = resolve_kontext_model_source(cfg)
    pipeline_offload_mode = normalize_pipeline_offload_mode(
        getattr(cfg, "refine_pipeline_offload_mode", "none")
    )

    log_runtime_stage(f"开始加载 Kontext edit pipeline: {kontext_model_source}")
    edit_pipe = FluxKontextPipeline.from_pretrained(
        kontext_model_source,
        torch_dtype=torch.bfloat16,
        local_files_only=local_files_only,
    )
    log_runtime_stage("FluxKontextPipeline.from_pretrained 返回")
    edit_pipe = configure_pipeline_offload(
        edit_pipe,
        offload_mode=pipeline_offload_mode,
        target_device="cuda",
        log_fn=log_runtime_stage,
    )
    execution_device = resolve_pipeline_execution_device(edit_pipe)
    log_runtime_stage(f"Kontext edit pipeline execution device: {execution_device}")

    # 这里直接复用 edit pipeline 已经加载好的共享组件。
    # 这样不会重复读两份大模型权重, 但仍能在有 mask 时切到 inpaint 语义。
    log_runtime_stage("开始基于共享 components 构建 Kontext inpaint pipeline")
    inpaint_pipe = FluxKontextInpaintPipeline(**edit_pipe.components)
    if pipeline_offload_mode == "none":
        inpaint_pipe = inpaint_pipe.to(execution_device)
    else:
        setattr(inpaint_pipe, "_execution_device", execution_device)
    log_runtime_stage("Kontext inpaint pipeline 构建完成")

    generator = torch.manual_seed(64)
    guidance_scale = float(getattr(cfg, "kontext_guidance_scale", 2.5))
    num_inference_steps = int(getattr(cfg, "kontext_num_inference_steps", cfg.num_inference_steps))
    strength = float(getattr(cfg, "kontext_strength", cfg.strength))

    def generate_image(
        *,
        plan_index: int,
        rgb_to_refine,
        masks,
        alpha,
        height: int,
        width: int,
        cam_param: dict[str, Any],
        refiner,
    ):
        del plan_index, alpha
        source_reference_sample = resolve_kontext_reference_sample(refiner, cam_param)
        has_reference = source_reference_sample is not None and "image" in source_reference_sample
        request = build_kontext_generation_request(
            prompt=build_kontext_prompt(cfg, has_reference=has_reference),
            negative_prompt=resolve_kontext_negative_prompt(cfg),
            rgb_to_refine=rgb_to_refine,
            masks=masks,
            source_reference_sample=source_reference_sample,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            generator=generator,
            strength=strength,
            height=height,
            width=width,
        )
        if request.mode == "inpaint":
            return inpaint_pipe(**request.kwargs).images[0]
        return edit_pipe(**request.kwargs).images[0]

    return BackendRuntime(
        execution_device=execution_device,
        generate_image=generate_image,
    )


def refine(cfg) -> None:
    log_runtime_stage = build_stage_logger("refine_by_kontext")
    run_backend_refine(
        cfg,
        log_runtime_stage=log_runtime_stage,
        build_backend_runtime=build_backend_runtime,
    )


def build_arg_parser():
    return build_refine_arg_parser(
        description="Kontext refine 入口。复用现有 resume/output contract, 作为可选 backend 并列接入。"
    )


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    from omegaconf import OmegaConf

    base_cfg = OmegaConf.load(args.base_cfg)
    exp_cfg = OmegaConf.load(args.exp_cfg)
    cfg = OmegaConf.merge(base_cfg, exp_cfg)
    if args.colmap_path is not None:
        cfg.colmap_path = args.colmap_path
    if args.ckpt_path is not None:
        cfg.load_ckpt_path = args.ckpt_path
    refine(cfg)


if __name__ == "__main__":
    main()
