import argparse
import os
import json
from pathlib import Path

from ours.refine_pipeline_runtime import (
    configure_pipeline_offload,
    normalize_pipeline_offload_mode,
    resolve_pipeline_execution_device,
)


def log_runtime_stage(message: str) -> None:
    """输出 refine 运行阶段, 让长冷启动不再是黑盒。"""
    print(f"[refine_by_sdxl] {message}", flush=True)


def append_pose_jitter_log(log_path: Path, *, frame_index: int, cam_param: dict) -> None:
    """把每轮 synthetic 相机采样结果追加到 jsonl, 方便后续排查 hallucination 风险。"""
    sample_log = cam_param.get("sample_log")
    if not isinstance(sample_log, dict):
        return

    record = {
        "frame_index": int(frame_index),
        "camera_mode": cam_param.get("camera_mode"),
        "source_split": cam_param.get("source_split"),
        "source_index": cam_param.get("source_index"),
        "source_image_name": cam_param.get("source_image_name"),
        "sample_log": sample_log,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def resolve_optional_checkpoint_path(cfg) -> str | None:
    raw_path = getattr(cfg, "load_ckpt_path", None)
    if raw_path is None:
        return None

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return str(candidate)

    if candidate.exists():
        return str(candidate.resolve())

    return str((Path(cfg.base_dir) / candidate).resolve())


def apply_runtime_path_overrides(cfg, config) -> str | None:
    colmap_path = getattr(cfg, "colmap_path", None)
    if colmap_path is not None:
        scene_dir = Path(colmap_path).expanduser().resolve()
        config.data_dir = str(scene_dir)
        partition_path = scene_dir / "partition.json"
        if partition_path.exists():
            config.partition = str(partition_path)

    return resolve_optional_checkpoint_path(cfg)


def refine(cfg):
    # 只在真正执行 refine 时再加载这些重依赖。
    # 这样命令行 `--help` 可以先快速返回, 不被模型/渲染相关 import 拖慢。
    log_runtime_stage("开始加载运行时依赖")
    import imageio
    import numpy as np
    import torch
    from torchvision.utils import save_image

    from ours.pipelines.sdxl_pipeline import StableDiffusionXLImg2ImgPipeline
    from ours.schedulers.euler_discrete_scheduler import EulerDiscreteScheduler
    from recon.refiner import Refiner, Config
    from recon.trainer import save_depth_map_visualization
    log_runtime_stage("运行时依赖加载完成")

    log_runtime_stage("开始读取底层 GS 配置")
    with open(os.path.join(cfg.base_dir, cfg.gs_cfg_file), "r") as f:
        config = Config(**json.load(f))
    load_ckpt_path = apply_runtime_path_overrides(cfg, config)
    pipeline_offload_mode = normalize_pipeline_offload_mode(
        getattr(cfg, "refine_pipeline_offload_mode", "none")
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

    log_runtime_stage("开始加载 SDXL pipeline")
    pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-refiner-1.0", torch_dtype=torch.float16
    )
    log_runtime_stage("SDXL from_pretrained 返回")
    pipe = configure_pipeline_offload(
        pipe,
        offload_mode=pipeline_offload_mode,
        target_device="cuda",
        log_fn=log_runtime_stage,
    )
    log_runtime_stage("开始替换 scheduler")
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    log_runtime_stage("scheduler 替换完成")
    execution_device = resolve_pipeline_execution_device(pipe)
    log_runtime_stage(f"pipeline execution device: {execution_device}")
    log_runtime_stage("SDXL pipeline 加载完成")

    output_dir = os.path.join(cfg.base_dir, cfg.exp_name)
    log_runtime_stage(f"开始创建输出目录: {output_dir}")
    os.makedirs(f'{output_dir}/before_refine', exist_ok=True)
    os.makedirs(f'{output_dir}/after_refine', exist_ok=True)
    os.makedirs(f'{output_dir}/refine/render', exist_ok=True)
    os.makedirs(f'{output_dir}/refine/gen', exist_ok=True)
    os.makedirs(f'{output_dir}/refine/depth', exist_ok=True)
    for c_exp in cfg.c_exp_index:
        os.makedirs(f'{output_dir}/refine/masks/{c_exp}', exist_ok=True)
    refine_camera_mode = getattr(cfg, "refine_camera_mode", "fixed")
    pose_jitter_log_path = Path(output_dir) / "refine" / "pose_jitter_log.jsonl"
    if refine_camera_mode == "pose_jitter":
        pose_jitter_log_path.write_text("", encoding="utf-8")
        print(f"Pose jitter log: {pose_jitter_log_path}")
    before_refine_writer = imageio.get_writer(f'{output_dir}/before_refine.mp4', fps=12)
    gen_writer = imageio.get_writer(f'{output_dir}/refine/gen.mp4', fps=12)
    after_refine_writer = imageio.get_writer(f'{output_dir}/after_refine.mp4', fps=12)
    log_runtime_stage("输出目录与 writer 初始化完成")

    generator = torch.manual_seed(64)
    infer_steps = int(cfg.num_inference_steps * cfg.strength)
    mask_scheduler=[int(infer_steps * cfg.c_scheduler[i]) for i in range(len(cfg.c_scheduler))]

    # render test images before refine
    for i in range(cfg.refine_start_idx, cfg.refine_end_idx):
        rgb, _, _, _, _, _ = refiner.render(i)
        save_image(rgb.permute(2,0,1), f'{output_dir}/before_refine/{i:03d}.jpg')
        before_refine_writer.append_data((rgb.detach().cpu().numpy() * 255).astype(np.uint8))
    before_refine_writer.close()

    # refine
    train_cams = [refiner.train_dataset[j] for j in range(cfg.train_start_idx, cfg.train_end_idx)]
    train_prob = [1 for _ in range(cfg.train_start_idx, cfg.train_end_idx)]
    for i in range(cfg.refine_start_idx, cfg.refine_end_idx):
        rgb, masks, alpha, depth, cam_param, _ = refiner.render(
            i,
            camera_mode=refine_camera_mode,
            camera_source_split=cfg.refine_camera_source_split,
        )
        masks = torch.stack(masks)
        # 统一走 execution device, 避免 offload 场景下被 `pipe.device` 误导。
        rgb_to_refine = rgb.permute(2, 0, 1).to(execution_device)  # (3, H, W)
        masks = masks.to(execution_device)
        H, W = rgb_to_refine.shape[1], rgb_to_refine.shape[2]

        if refine_camera_mode == "pose_jitter":
            append_pose_jitter_log(pose_jitter_log_path, frame_index=i, cam_param=cam_param)

        save_image(rgb_to_refine, f'{output_dir}/refine/render/{i:03d}.jpg')
        save_depth_map_visualization(depth[..., 0].cpu().numpy(), f'{output_dir}/refine/depth/{i:03d}.jpg')
        for j in range(masks.shape[0]):
            save_image(masks[j:j+1][None, ...], f'{output_dir}/refine/masks/{cfg.c_exp_index[j]}/{i:03d}.jpg')
        
        if i == cfg.refine_start_idx:
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
            "image_id": f"gen_{i - cfg.refine_start_idx}",
        }]

        refined_image.save(f'{output_dir}/refine/gen/image_{i:03d}.jpg')
        gen_writer.append_data(np.array(refined_image))

        refiner.refine(refine_cams, train_cams, train_prob, max_steps=refine_steps)

        train_cams.append(refine_cams[0])
        train_prob.append(cfg.gen_prob)

    gen_writer.close()

    # render test images after refine
    for i in range(cfg.refine_start_idx, cfg.refine_end_idx):
        rgb, _, _, _, _, _ = refiner.render(i)
        save_image(rgb.permute(2,0,1), f'{output_dir}/after_refine/{i:03d}.jpg')
        after_refine_writer.append_data((rgb.detach().cpu().numpy() * 255).astype(np.uint8))
    after_refine_writer.close()

    refiner.save(name=f"ckpt_{cfg.exp_name}")   


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
