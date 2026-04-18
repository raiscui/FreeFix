from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ours.refine_backend_common import apply_runtime_path_overrides, append_pose_jitter_log
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


@dataclass
class BackendRuntime:
    """某条 refine backend 在主循环里真正需要的最小运行时集合。"""

    execution_device: object
    generate_image: Callable[..., Any]


def build_final_3dgs_ply_path(cfg) -> Path:
    """统一约定 refine 最终 3DGS PLY 的落盘位置。"""
    return (Path(cfg.base_dir) / f"point_cloud_{cfg.exp_name}.ply").resolve()


def export_final_3dgs_ply(
    *,
    ckpt_path: str | Path,
    output_path: str | Path,
    log_runtime_stage: Callable[[str], None],
) -> str:
    """把 refine 最终 checkpoint 导出成标准 3DGS PLY。"""
    from recon.export_3dgs_ply import build_ply_matrix, load_splats_from_checkpoint, write_binary_ply

    ckpt_path = Path(ckpt_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log_runtime_stage(f"开始导出最终 3DGS PLY: {output_path}")
    splats = load_splats_from_checkpoint(ckpt_path)
    matrix, property_names = build_ply_matrix(splats)
    write_binary_ply(output_path, matrix, property_names)
    log_runtime_stage(f"最终 3DGS PLY 已导出: {output_path}")
    return str(output_path)


def build_refiner_runtime_kwargs(cfg, *, load_ckpt_path: str | None) -> dict[str, Any]:
    """把 wrapper 配置整理成 `Refiner(...)` 的稳定参数集合。

    这里统一用 `getattr(..., default)` 做兜底。
    这样旧实验 yaml 就算还没声明新字段, 也不会在初始化阶段直接炸掉。
    """
    return {
        "load_step": cfg.load_step,
        "test_split": cfg.test_split,
        "test_trans": cfg.test_trans,
        "test_rots": cfg.test_rots,
        "c_exp_index": cfg.c_exp_index,
        "hessian_attr": cfg.hessian_attr,
        "test_len": cfg.refine_end_idx - cfg.refine_start_idx,
        "data_type": cfg.data_type,
        "load_ckpt_path": load_ckpt_path,
        "refine_camera_source_split": getattr(cfg, "refine_camera_source_split", "train"),
        "pose_jitter_trans_sigma": getattr(cfg, "pose_jitter_trans_sigma", (0.0, 0.0, 0.0)),
        "pose_jitter_trans_max": getattr(cfg, "pose_jitter_trans_max", (0.0, 0.0, 0.0)),
        "pose_jitter_rot_sigma_deg": getattr(cfg, "pose_jitter_rot_sigma_deg", (0.0, 0.0, 0.0)),
        "pose_jitter_rot_max_deg": getattr(cfg, "pose_jitter_rot_max_deg", (0.0, 0.0, 0.0)),
        "pose_jitter_max_attempts": getattr(cfg, "pose_jitter_max_attempts", 4),
        "pose_jitter_alpha_threshold": getattr(cfg, "pose_jitter_alpha_threshold", 0.05),
        "pose_jitter_min_alpha_coverage": getattr(cfg, "pose_jitter_min_alpha_coverage", 0.05),
        "pose_jitter_trans_radius_mode": getattr(cfg, "pose_jitter_trans_radius_mode", "disabled"),
        "pose_jitter_neighbor_window": getattr(cfg, "pose_jitter_neighbor_window", 1),
        "pose_jitter_neighbor_radius_scale": getattr(cfg, "pose_jitter_neighbor_radius_scale", 1.0),
        "refine_virtual_step": getattr(cfg, "refine_virtual_step", None),
        "refine_start_iter": getattr(cfg, "refine_start_iter", None),
        "refine_stop_iter": getattr(cfg, "refine_stop_iter", None),
        "reset_every": getattr(cfg, "reset_every", None),
        "refine_every": getattr(cfg, "refine_every", None),
        "prune_opa": getattr(cfg, "prune_opa", None),
        "grow_grad2d": getattr(cfg, "grow_grad2d", None),
        "grow_scale3d": getattr(cfg, "grow_scale3d", None),
        "prune_scale3d": getattr(cfg, "prune_scale3d", None),
    }


def run_backend_refine(
    cfg,
    *,
    log_runtime_stage: Callable[[str], None],
    build_backend_runtime: Callable[[Any, Callable[[str], None]], BackendRuntime],
) -> None:
    """执行一条 refine backend 的公共主循环。"""
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
            final_ply_output_path = build_final_3dgs_ply_path(cfg)
            if not final_ply_output_path.exists():
                export_final_3dgs_ply(
                    ckpt_path=final_ckpt_path,
                    output_path=final_ply_output_path,
                    log_runtime_stage=log_runtime_stage,
                )
            log_runtime_stage("检测到本次 refine 已完整完成, 且最终 checkpoint 已存在, 跳过重复执行")
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

    # 只在真正执行 refine 时再加载重依赖。
    # 这样 `python -m ours.refine_by_xxx --help` 仍然能保持秒回。
    log_runtime_stage("开始加载运行时依赖")
    import numpy as np
    import torch
    from torchvision.utils import save_image

    from recon.refiner import Config, Refiner
    from recon.trainer import save_depth_map_visualization

    log_runtime_stage("运行时依赖加载完成")

    log_runtime_stage("开始读取底层 GS 配置")
    with open(os.path.join(cfg.base_dir, cfg.gs_cfg_file), "r", encoding="utf-8") as handle:
        config = Config(**json.load(handle))
    load_ckpt_path = apply_runtime_path_overrides(cfg, config)
    load_ckpt_path = resolve_resume_checkpoint_path(
        resume_state=resume_state,
        initial_load_ckpt_path=load_ckpt_path,
    )

    log_runtime_stage("开始初始化 Refiner")
    refiner = Refiner(config, **build_refiner_runtime_kwargs(cfg, load_ckpt_path=load_ckpt_path))
    log_runtime_stage("Refiner 初始化完成")

    backend_runtime = build_backend_runtime(cfg, log_runtime_stage)
    execution_device = backend_runtime.execution_device

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
        f"repeats_per_source={refine_plan_info['repeats_per_source']} "
        f"source_skip_first_count={refine_plan_info.get('source_skip_first_count', 0)} "
        f"source_interleaved_count={refine_plan_info.get('source_interleaved_count', 1)} "
        f"count={refine_plan_info['count']}"
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

    for plan_entry in refine_view_plan[resume_next_plan_index:]:
        plan_index = int(plan_entry["plan_index"])
        rgb, masks, alpha, depth, cam_param, _ = refiner.render(
            plan_index,
            camera_mode=refine_camera_mode,
            camera_source_split=getattr(cfg, "refine_camera_source_split", "train"),
            camera_spec=plan_entry,
        )
        masks = torch.stack(masks)
        rgb_to_refine = rgb.permute(2, 0, 1).to(execution_device)
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
                masks[j : j + 1][None, ...],
                str(output_dir_path / "refine" / "masks" / str(cfg.c_exp_index[j]) / f"{plan_index:03d}.jpg"),
            )

        refined_image = backend_runtime.generate_image(
            plan_index=plan_index,
            rgb_to_refine=rgb_to_refine,
            masks=masks,
            alpha=alpha,
            height=H,
            width=W,
            cam_param=cam_param,
            refiner=refiner,
        )
        refined_image = refined_image.resize((W, H))

        torch_refined_image = torch.from_numpy(np.array(refined_image))
        ixt = cam_param["K"]
        c2w = cam_param["c2w"]
        refine_cams = [
            {
                "image": torch_refined_image,
                "camtoworld": c2w,
                "K": ixt,
                "Gen": True,
                "image_id": cam_param["image_id"],
            }
        ]

        refined_image.save(output_dir_path / "refine" / "gen" / f"image_{plan_index:03d}.jpg")
        append_generated_camera_record(
            generated_camera_log_path,
            plan_index=plan_index,
            cam_param=cam_param,
        )

        refiner.refine(
            refine_cams,
            train_cams,
            np.asarray(train_prob, dtype=np.float64),
            max_steps=cfg.refine_steps * 2 if plan_index == 0 else cfg.refine_steps,
            use_affine=cfg.affine,
        )

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
    export_final_3dgs_ply(
        ckpt_path=saved_ckpt_path,
        output_path=build_final_3dgs_ply_path(cfg),
        log_runtime_stage=log_runtime_stage,
    )
