from __future__ import annotations

from pathlib import Path

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


DEFAULT_FLUX_REPO_ID = "black-forest-labs/FLUX.1-dev"
DEFAULT_LOCAL_FLUX_PATHS = [
    Path("/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev"),
    Path("/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev"),
]


def resolve_flux_model_source(cfg):
    """解析 Flux 模型来源, 优先使用本地已下载快照。"""
    return resolve_local_model_source(
        cfg,
        config_attr="flux_model_path",
        default_repo_id=DEFAULT_FLUX_REPO_ID,
        default_local_paths=DEFAULT_LOCAL_FLUX_PATHS,
        label="Flux",
    )


def build_backend_runtime(cfg, log_runtime_stage) -> BackendRuntime:
    import torch

    from ours.pipelines.flux_pipeline import FluxPipeline
    from ours.schedulers.flow_match_euler_discrete_scheduler import (
        FlowMatchEulerDiscreteScheduler,
    )

    flux_model_source, local_files_only = resolve_flux_model_source(cfg)
    pipeline_offload_mode = normalize_pipeline_offload_mode(
        getattr(cfg, "refine_pipeline_offload_mode", "none")
    )

    log_runtime_stage(f"开始加载 Flux pipeline: {flux_model_source}")
    pipe = FluxPipeline.from_pretrained(
        flux_model_source,
        torch_dtype=torch.bfloat16,
        local_files_only=local_files_only,
    )
    log_runtime_stage("FluxPipeline.from_pretrained 返回")
    pipe = configure_pipeline_offload(
        pipe,
        offload_mode=pipeline_offload_mode,
        target_device="cuda",
        log_fn=log_runtime_stage,
    )
    log_runtime_stage("开始替换 scheduler")
    pipe.scheduler = FlowMatchEulerDiscreteScheduler.from_config(pipe.scheduler.config)
    log_runtime_stage("scheduler 替换完成")
    execution_device = resolve_pipeline_execution_device(pipe)
    log_runtime_stage(f"pipeline execution device: {execution_device}")
    log_runtime_stage("Flux pipeline 加载完成")

    generator = torch.manual_seed(64)
    infer_steps = int(cfg.num_inference_steps * cfg.strength)
    mask_scheduler = [int(infer_steps * cfg.c_scheduler[i]) for i in range(len(cfg.c_scheduler))]

    def generate_image(
        *,
        plan_index: int,
        rgb_to_refine,
        masks,
        alpha,
        height: int,
        width: int,
        cam_param,
        refiner,
    ):
        del cam_param, refiner, height, width
        if plan_index == 0:
            warp_until = -1
            warp_mask = None
        else:
            warp_until = infer_steps * cfg.warp_ratio
            warp_mask = alpha

        return pipe(
            cfg.prompt,
            negative_prompt=getattr(cfg, "negative_prompt", None),
            image=rgb_to_refine,
            mask=masks,
            mask_scheduler=mask_scheduler,
            guide_until=infer_steps * cfg.guide_ratio,
            warp_image=rgb_to_refine,
            warp_until=warp_until,
            warp_mask=warp_mask,
            height=rgb_to_refine.shape[1],
            width=rgb_to_refine.shape[2],
            guidance_scale=3.5,
            num_inference_steps=cfg.num_inference_steps,
            generator=generator,
            strength=cfg.strength,
        ).images[0]

    return BackendRuntime(
        execution_device=execution_device,
        generate_image=generate_image,
    )


def refine(cfg) -> None:
    log_runtime_stage = build_stage_logger("refine_by_flux")
    run_backend_refine(
        cfg,
        log_runtime_stage=log_runtime_stage,
        build_backend_runtime=build_backend_runtime,
    )


def build_arg_parser():
    return build_refine_arg_parser(
        description="Flux refine 入口。复用现有 resume/output contract。"
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
