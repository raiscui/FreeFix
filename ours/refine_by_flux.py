import argparse
import os
import json
from pathlib import Path

from ours.refine_pipeline_runtime import (
    configure_pipeline_offload,
    normalize_pipeline_offload_mode,
    resolve_pipeline_execution_device,
)
from ours.refine_run_schedule import build_real_train_pool, build_refine_view_plan
from recon.refine_runtime import (
    append_generated_camera_record,
    build_generated_camera_log_path,
    build_refine_resume_checkpoint_path,
    build_refine_resume_state,
    build_refine_resume_state_path,
    chunk_items,
    cleanup_stale_resume_artifacts,
    clear_after_refine_outputs,
    load_refine_resume_state,
    rebuild_video_from_frame_dir,
    resolve_resume_checkpoint_path,
    restore_completed_generated_cams,
    save_refine_resume_state,
)

DEFAULT_FLUX_REPO_ID = "black-forest-labs/FLUX.1-dev"
DEFAULT_LOCAL_FLUX_PATHS = [
    Path("/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX___1-dev"),
    Path("/home/rais/.cache/modelscope/hub/models/black-forest-labs/FLUX.1-dev"),
]


def log_runtime_stage(message: str) -> None:
    """输出 refine 运行阶段, 让长冷启动不再是黑盒。"""
    print(f"[refine_by_flux] {message}", flush=True)


def append_pose_jitter_log(log_path: Path, *, frame_index: int, cam_param: dict) -> None:
    """把每轮 synthetic 相机采样结果追加到 jsonl, 方便后续排查 hallucination 风险。"""
    sample_log = cam_param.get("sample_log")
    if not isinstance(sample_log, dict):
        return

    record = {
        "frame_index": int(frame_index),
        "plan_index": cam_param.get("plan_index"),
        "camera_mode": cam_param.get("camera_mode"),
        "source_split": cam_param.get("source_split"),
        "source_index": cam_param.get("source_index"),
        "source_repeat_index": cam_param.get("source_repeat_index"),
        "source_image_name": cam_param.get("source_image_name"),
        "image_id": cam_param.get("image_id"),
        "sample_log": sample_log,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def resolve_flux_model_source(cfg):
    """解析 Flux 模型来源, 优先使用本地已下载快照。"""
    configured_path = getattr(cfg, "flux_model_path", None)
    if configured_path is not None:
        candidate = Path(configured_path).expanduser()
        if not candidate.exists():
            raise FileNotFoundError(f"配置里的 flux_model_path 不存在: {candidate}")
        if not (candidate / "model_index.json").exists():
            raise FileNotFoundError(f"本地 Flux 目录缺少 model_index.json: {candidate}")
        return str(candidate), True

    for candidate in DEFAULT_LOCAL_FLUX_PATHS:
        if candidate.exists() and (candidate / "model_index.json").exists():
            return str(candidate), True

    return DEFAULT_FLUX_REPO_ID, False


def resolve_optional_checkpoint_path(cfg) -> str | None:
    raw_path = getattr(cfg, "load_ckpt_path", None)
    if raw_path is None:
        return None

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return str(candidate)

    # 先尊重用户从仓库根目录运行时写的相对路径。
    if candidate.exists():
        return str(candidate.resolve())

    # 如果仓库相对路径不存在, 再回退成相对 `base_dir` 的路径。
    return str((Path(cfg.base_dir) / candidate).resolve())


def apply_runtime_path_overrides(cfg, config) -> str | None:
    colmap_path = getattr(cfg, "colmap_path", None)
    if colmap_path is not None:
        scene_dir = Path(colmap_path).expanduser().resolve()
        config.data_dir = str(scene_dir)

        # 如果目标场景目录里已经有 partition, 优先直接跟过去。
        # 这样用户只传一个 `--colmap-path`, 不必再手工同步旧配置里的分片路径。
        partition_path = scene_dir / "partition.json"
        if partition_path.exists():
            config.partition = str(partition_path)

    return resolve_optional_checkpoint_path(cfg)


def refine(cfg):
    output_dir = os.path.join(cfg.base_dir, cfg.exp_name)
    output_dir_path = Path(output_dir)
    resume_enabled = bool(getattr(cfg, "refine_resume_enabled", True))
    resume_save_every_plans = int(getattr(cfg, "refine_resume_save_every_plans", 25))
    fixed_render_batch_size = max(1, int(getattr(cfg, "refine_fixed_render_batch_size", 8)))
    resume_state_path = build_refine_resume_state_path(output_dir_path)
    generated_camera_log_path = build_generated_camera_log_path(output_dir_path)
    resume_state = load_refine_resume_state(resume_state_path) if resume_enabled else None
    if resume_state is not None and resume_state.get("exp_name") not in (None, cfg.exp_name):
        raise ValueError(
            "恢复状态里的 exp_name 与当前配置不一致: "
            f"{resume_state.get('exp_name')} != {cfg.exp_name}"
        )
    if resume_state is not None:
        final_ckpt_path = resume_state.get("final_ckpt_path")
        if (
            resume_state.get("status") == "complete"
            and isinstance(final_ckpt_path, str)
            and Path(final_ckpt_path).expanduser().exists()
        ):
            log_runtime_stage(
                "检测到本次 refine 已完整完成, 且最终 checkpoint 已存在, 跳过重复执行"
            )
            return

    if resume_state is not None:
        next_plan_index = int(resume_state.get("next_plan_index", 0))
        recorded_resume_ckpt = resume_state.get("resume_ckpt_path")
        if next_plan_index > 0 and (
            not isinstance(recorded_resume_ckpt, str)
            or not Path(recorded_resume_ckpt).expanduser().exists()
        ):
            raise FileNotFoundError(
                "检测到 refine 恢复状态, 但缺少对应的恢复 checkpoint: "
                f"{recorded_resume_ckpt}"
            )
    pipeline_offload_mode = normalize_pipeline_offload_mode(
        getattr(cfg, "refine_pipeline_offload_mode", "none")
    )

    # 这里把重依赖延后到真正执行 refine 时再加载。
    # 这样 `python ours/refine_by_flux.py --help` 不会因为顶层 import 太重而长时间无响应。
    log_runtime_stage("开始加载运行时依赖")
    import numpy as np
    import torch
    from torchvision.utils import save_image

    from ours.pipelines.flux_pipeline import FluxPipeline
    from ours.schedulers.flow_match_euler_discrete_scheduler import (
        FlowMatchEulerDiscreteScheduler,
    )
    from recon.refiner import Refiner, Config
    from recon.trainer import save_depth_map_visualization
    log_runtime_stage("运行时依赖加载完成")

    log_runtime_stage("开始读取底层 GS 配置")
    with open(os.path.join(cfg.base_dir, cfg.gs_cfg_file), "r") as f:
        config = Config(**json.load(f))
    load_ckpt_path = apply_runtime_path_overrides(cfg, config)
    load_ckpt_path = resolve_resume_checkpoint_path(
        resume_state=resume_state,
        initial_load_ckpt_path=load_ckpt_path,
    )
    log_runtime_stage("开始初始化 Refiner")
    refiner = Refiner(
        config, 
        load_step=cfg.load_step,
        test_split=cfg.test_split, 
        test_trans=cfg.test_trans, 
        test_rots=cfg.test_rots, 
        c_exp_index=cfg.c_exp_index,
        hessian_attr=cfg.hessian_attr,
        test_len = cfg.refine_end_idx - cfg.refine_start_idx,
        data_type=cfg.data_type,
        load_ckpt_path=load_ckpt_path,
        refine_camera_source_split=cfg.refine_camera_source_split,
        pose_jitter_trans_sigma=cfg.pose_jitter_trans_sigma,
        pose_jitter_trans_max=cfg.pose_jitter_trans_max,
        pose_jitter_rot_sigma_deg=cfg.pose_jitter_rot_sigma_deg,
        pose_jitter_rot_max_deg=cfg.pose_jitter_rot_max_deg,
        pose_jitter_max_attempts=cfg.pose_jitter_max_attempts,
        pose_jitter_alpha_threshold=cfg.pose_jitter_alpha_threshold,
        pose_jitter_min_alpha_coverage=cfg.pose_jitter_min_alpha_coverage,
    )
    log_runtime_stage("Refiner 初始化完成")

    flux_model_source, local_files_only = resolve_flux_model_source(cfg)
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

    log_runtime_stage(f"开始创建输出目录: {output_dir}")
    os.makedirs(output_dir_path / "before_refine", exist_ok=True)
    os.makedirs(output_dir_path / "after_refine", exist_ok=True)
    os.makedirs(output_dir_path / "refine" / "render", exist_ok=True)
    os.makedirs(output_dir_path / "refine" / "gen", exist_ok=True)
    os.makedirs(output_dir_path / "refine" / "depth", exist_ok=True)
    for c_exp in cfg.c_exp_index:
        os.makedirs(output_dir_path / "refine" / "masks" / str(c_exp), exist_ok=True)
    refine_camera_mode = getattr(cfg, "refine_camera_mode", "fixed")
    pose_jitter_log_path = output_dir_path / "refine" / "pose_jitter_log.jsonl"
    log_runtime_stage("输出目录初始化完成")

    refine_view_plan, refine_plan_info = build_refine_view_plan(refiner, cfg)
    total_plan_count = len(refine_view_plan)
    train_cams, train_prob, train_pool_info = build_real_train_pool(refiner, cfg)
    log_runtime_stage(
        f"真实训练池: mode={train_pool_info['mode']} splits={list(train_pool_info['splits'])} "
        f"count={train_pool_info['count']}"
    )
    log_runtime_stage(
        f"synthetic plan: mode={refine_plan_info['mode']} splits={list(refine_plan_info['splits'])} "
        f"repeats_per_source={refine_plan_info['repeats_per_source']} count={refine_plan_info['count']}"
    )
    if "test" in train_pool_info["splits"] or "test" in refine_plan_info["splits"]:
        log_runtime_stage("警告: 当前 refine 已把 test split 纳入训练或 synthetic source pool, benchmark 将被污染")

    if resume_state is not None and int(resume_state.get("plan_total", total_plan_count)) != total_plan_count:
        raise ValueError(
            "恢复状态里的 synthetic plan 总数与当前配置不一致: "
            f"{resume_state.get('plan_total')} != {total_plan_count}"
        )

    resume_ckpt_path = build_refine_resume_checkpoint_path(cfg.base_dir, cfg.exp_name)
    initial_resume_ckpt_path = load_ckpt_path
    if initial_resume_ckpt_path is None:
        initial_resume_ckpt_path = str(
            (Path(cfg.base_dir) / "ckpts" / f"ckpt_{cfg.load_step}.pt").resolve()
        )
    resume_next_plan_index = int(resume_state.get("next_plan_index", 0)) if resume_state is not None else 0
    before_refine_complete = bool(resume_state.get("before_refine_complete", False)) if resume_state is not None else False
    synthetic_complete = bool(resume_state.get("synthetic_complete", False)) if resume_state is not None else False
    after_refine_complete = bool(resume_state.get("after_refine_complete", False)) if resume_state is not None else False

    def persist_resume_state(
        *,
        next_plan_index: int,
        before_done: bool,
        synthetic_done: bool,
        after_done: bool,
        current_resume_ckpt_path: str | None,
        final_ckpt_path: str | None = None,
    ) -> None:
        nonlocal resume_state
        if not resume_enabled:
            return
        resume_state = build_refine_resume_state(
            exp_name=cfg.exp_name,
            plan_total=total_plan_count,
            next_plan_index=next_plan_index,
            before_refine_complete=before_done,
            synthetic_complete=synthetic_done,
            after_refine_complete=after_done,
            resume_ckpt_path=current_resume_ckpt_path,
            final_ckpt_path=final_ckpt_path,
        )
        save_refine_resume_state(resume_state_path, resume_state)

    def render_fixed_sequence(frame_dir: Path, video_path: Path) -> None:
        comparison_indices = list(range(cfg.refine_start_idx, cfg.refine_end_idx))
        for batch_indices in chunk_items(comparison_indices, fixed_render_batch_size):
            for rendered in refiner.render_fixed_rgb_batch(batch_indices):
                save_image(
                    rendered["rgb"].permute(2, 0, 1),
                    str(frame_dir / f"{rendered['index']:03d}.jpg"),
                )
        rebuild_video_from_frame_dir(frame_dir, video_path, fps=12)

    if resume_state is not None and resume_next_plan_index > 0:
        cleanup_stale_resume_artifacts(
            output_dir_path,
            next_plan_index=resume_next_plan_index,
            c_exp_index=cfg.c_exp_index,
        )
        if not after_refine_complete:
            clear_after_refine_outputs(output_dir_path)

        restored_generated_cams = restore_completed_generated_cams(
            generated_camera_log_path,
            output_dir_path / "refine" / "gen",
            keep_before_plan_index=resume_next_plan_index,
        )
        train_cams.extend(restored_generated_cams)
        train_prob.extend([cfg.gen_prob for _ in restored_generated_cams])
        log_runtime_stage(
            f"恢复 synthetic train pool: restored={len(restored_generated_cams)} "
            f"next_plan_index={resume_next_plan_index}/{total_plan_count}"
        )
    elif resume_state is not None:
        cleanup_stale_resume_artifacts(
            output_dir_path,
            next_plan_index=0,
            c_exp_index=cfg.c_exp_index,
        )
        clear_after_refine_outputs(output_dir_path)

    if resume_next_plan_index == 0:
        generated_camera_log_path.write_text("", encoding="utf-8")
        if refine_camera_mode == "pose_jitter":
            pose_jitter_log_path.write_text("", encoding="utf-8")
            print(f"Pose jitter log: {pose_jitter_log_path}")
    elif refine_camera_mode == "pose_jitter" and pose_jitter_log_path.exists():
        print(f"Pose jitter log(resume): {pose_jitter_log_path}")

    if before_refine_complete:
        log_runtime_stage("检测到 before_refine 已完成, 跳过固定视角前对比渲染")
        rebuild_video_from_frame_dir(output_dir_path / "before_refine", output_dir_path / "before_refine.mp4", fps=12)
    else:
        log_runtime_stage(
            f"开始导出 before_refine, batch_size={fixed_render_batch_size} "
            f"views={cfg.refine_end_idx - cfg.refine_start_idx}"
        )
        render_fixed_sequence(output_dir_path / "before_refine", output_dir_path / "before_refine.mp4")
        before_refine_complete = True
        persist_resume_state(
            next_plan_index=resume_next_plan_index,
            before_done=True,
            synthetic_done=synthetic_complete,
            after_done=after_refine_complete,
            current_resume_ckpt_path=initial_resume_ckpt_path,
        )

    generator = torch.manual_seed(64)
    infer_steps = int(cfg.num_inference_steps * cfg.strength)
    mask_scheduler=[int(infer_steps * cfg.c_scheduler[i]) for i in range(len(cfg.c_scheduler))]

    # refine
    for plan_entry in refine_view_plan[resume_next_plan_index:]:
        plan_index = int(plan_entry["plan_index"])
        rgb, masks, alpha, depth, cam_param, _ = refiner.render(
            plan_index,
            camera_mode=refine_camera_mode,
            camera_source_split=cfg.refine_camera_source_split,
            camera_spec=plan_entry,
        )
        masks = torch.stack(masks)
        # 这里改成 execution device 语义。
        # offload 模式下 `pipe.device` 往往停在 CPU, 但实际推理设备仍是 GPU。
        rgb_to_refine = rgb.permute(2, 0, 1).to(execution_device)  # (3, H, W)
        masks = masks.to(execution_device)
        H, W = rgb_to_refine.shape[1], rgb_to_refine.shape[2]

        if refine_camera_mode == "pose_jitter":
            append_pose_jitter_log(pose_jitter_log_path, frame_index=plan_index, cam_param=cam_param)

        save_image(rgb_to_refine, str(output_dir_path / "refine" / "render" / f"{plan_index:03d}.jpg"))
        save_depth_map_visualization(
            depth[..., 0].cpu().numpy(),
            str(output_dir_path / "refine" / "depth" / f"{plan_index:03d}.jpg"),
        )
        for j in range(masks.shape[0]):
            save_image(
                masks[j:j+1][None, ...],
                str(output_dir_path / "refine" / "masks" / str(cfg.c_exp_index[j]) / f"{plan_index:03d}.jpg"),
            )
        
        if plan_index == 0:
            warp_until = -1
            warp_mask = None
            refine_steps = cfg.refine_steps * 2
        else:
            warp_until = infer_steps*cfg.warp_ratio
            warp_mask = alpha
            refine_steps = cfg.refine_steps

        refined_image = pipe(
            cfg.prompt,
            negative_prompt=cfg.negative_prompt if "negative_prompt" in cfg else None,
            image=rgb_to_refine,
            mask=masks,
            mask_scheduler=mask_scheduler,
            guide_until=infer_steps*cfg.guide_ratio,
            warp_image=rgb_to_refine,
            warp_until=warp_until,
            warp_mask=warp_mask,
            height=H,
            width=W,
            guidance_scale=3.5,
            num_inference_steps=cfg.num_inference_steps,
            generator=generator,
            strength=cfg.strength,
        ).images[0]

        refined_image = refined_image.resize((W, H))
        torch_refined_image = torch.from_numpy(np.array(refined_image))
        ixt = cam_param["K"]
        c2w = cam_param["c2w"]
        refine_cams = [{
            "image": torch_refined_image,
            "camtoworld": c2w,
            "K": ixt,
            "Gen": True,
            "image_id": cam_param["image_id"],
        }]

        refined_image.save(output_dir_path / "refine" / "gen" / f"image_{plan_index:03d}.jpg")
        append_generated_camera_record(
            generated_camera_log_path,
            plan_index=plan_index,
            cam_param=cam_param,
        )

        refiner.refine(refine_cams, train_cams, train_prob, max_steps=refine_steps, use_affine=cfg.affine)

        train_cams.append(refine_cams[0])
        train_prob.append(cfg.gen_prob)

        completed_plan_count = plan_index + 1
        should_save_resume_ckpt = resume_enabled and (
            completed_plan_count == total_plan_count
            or (
                resume_save_every_plans > 0
                and completed_plan_count % resume_save_every_plans == 0
            )
        )
        if should_save_resume_ckpt:
            saved_resume_ckpt_path = refiner.save(name=resume_ckpt_path.stem)
            log_runtime_stage(
                f"已保存恢复 checkpoint: plan={completed_plan_count}/{total_plan_count} "
                f"path={saved_resume_ckpt_path}"
            )
            persist_resume_state(
                next_plan_index=completed_plan_count,
                before_done=True,
                synthetic_done=completed_plan_count == total_plan_count,
                after_done=False,
                current_resume_ckpt_path=saved_resume_ckpt_path,
            )

    rebuild_video_from_frame_dir(output_dir_path / "refine" / "gen", output_dir_path / "refine" / "gen.mp4", fps=12)
    synthetic_complete = True
    resume_next_plan_index = total_plan_count

    if after_refine_complete:
        log_runtime_stage("检测到 after_refine 已完成, 跳过固定视角后对比渲染")
        rebuild_video_from_frame_dir(output_dir_path / "after_refine", output_dir_path / "after_refine.mp4", fps=12)
    else:
        log_runtime_stage(
            f"开始导出 after_refine, batch_size={fixed_render_batch_size} "
            f"views={cfg.refine_end_idx - cfg.refine_start_idx}"
        )
        render_fixed_sequence(output_dir_path / "after_refine", output_dir_path / "after_refine.mp4")
        after_refine_complete = True
        persist_resume_state(
            next_plan_index=resume_next_plan_index,
            before_done=True,
            synthetic_done=True,
            after_done=True,
            current_resume_ckpt_path=str(resume_ckpt_path.resolve()) if resume_ckpt_path.exists() else initial_resume_ckpt_path,
        )

    log_runtime_stage(f"开始保存 refine checkpoint: ckpt_{cfg.exp_name}")
    saved_ckpt_path = refiner.save(name=f"ckpt_{cfg.exp_name}")
    log_runtime_stage(f"refine checkpoint 已保存: {saved_ckpt_path}")
    persist_resume_state(
        next_plan_index=resume_next_plan_index,
        before_done=True,
        synthetic_done=True,
        after_done=True,
        current_resume_ckpt_path=str(resume_ckpt_path.resolve()) if resume_ckpt_path.exists() else saved_ckpt_path,
        final_ckpt_path=saved_ckpt_path,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--exp_cfg', type=str, required=True, help='exp cfg path')
    parser.add_argument('--base_cfg', type=str, default="exp_cfg/base.yaml", help='base cfg path')
    parser.add_argument('--colmap-path', type=str, default=None, help='运行时覆盖数据集路径, 直接指向 COLMAP 场景目录')
    parser.add_argument('--ckpt-path', type=str, default=None, help='运行时覆盖初始高斯 checkpoint 路径')
    return parser


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
