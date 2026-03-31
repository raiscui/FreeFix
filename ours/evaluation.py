import argparse
import os
import json
from pathlib import Path
import torch
import numpy as np
from ours.utils import read_images, query_warp, project_warp, eval
from torchvision.utils import save_image
from recon.refiner import Refiner, Config
from omegaconf import OmegaConf
from recon.trainer import save_depth_map_visualization
from PIL import Image
from torchmetrics.image.fid import FrechetInceptionDistance
from torchvision.transforms.functional import to_pil_image


def resolve_base_load_step(cfg, cli_load_step=None):
    # -----------------------------------------------------------------------------
    # 基础模型评估默认应跟训练配置里的 `load_step` 走。
    # 这样短训场景就不再被写死到 `29999`。
    # -----------------------------------------------------------------------------
    if cli_load_step is not None:
        return cli_load_step
    return getattr(cfg, "load_step", 29999)


def refined_checkpoint_path(cfg):
    # refined checkpoint 的命名规则和 refine 保存逻辑保持一致:
    # `ckpt_<exp_name>.pt`
    return os.path.join(cfg.base_dir, "ckpts", f"ckpt_{cfg.exp_name}.pt")


def has_refined_checkpoint(cfg) -> bool:
    return os.path.exists(refined_checkpoint_path(cfg))


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


def apply_runtime_path_overrides(cfg, config, include_ckpt_override=True) -> str | None:
    # -----------------------------------------------------------------------------
    # 评估阶段和 refine 阶段保持同一套路径 override 语义:
    # - `--colmap-path` 负责覆盖场景目录, 并自动跟随其中的 `partition.json`
    # - `--ckpt-path` 只在基础模型评估时作为显式 checkpoint override 使用
    # -----------------------------------------------------------------------------
    colmap_path = getattr(cfg, "colmap_path", None)
    if colmap_path is not None:
        scene_dir = Path(colmap_path).expanduser().resolve()
        config.data_dir = str(scene_dir)

        partition_path = scene_dir / "partition.json"
        if partition_path.exists():
            config.partition = str(partition_path)

    if include_ckpt_override:
        return resolve_optional_checkpoint_path(cfg)
    return None


def eval(
    cfg,
    load_step,
    eval_test=False,
    test_from_train=False,
    use_ckpt_override=False,
    resume_load_step=None,
):

    with open(os.path.join(cfg.base_dir, cfg.gs_cfg_file), "r") as f:
        config = Config(**json.load(f))
    load_ckpt_path = apply_runtime_path_overrides(
        cfg,
        config,
        include_ckpt_override=use_ckpt_override,
    )
    refiner = Refiner(
        config, 
        load_step=load_step,
        resume_load_step=resume_load_step,
        test_split=cfg.test_split, 
        test_trans=cfg.test_trans, 
        test_rots=cfg.test_rots, 
        c_exp_index=cfg.c_exp_index,
        hessian_attr=cfg.hessian_attr,
        test_len = cfg.refine_end_idx - cfg.refine_start_idx,
        data_type=cfg.data_type,
        load_ckpt_path=load_ckpt_path,
    )

    output_dir = os.path.join(cfg.base_dir, cfg.exp_name)
    os.makedirs(f'{output_dir}/eval/{load_step}_test', exist_ok=True)
    os.makedirs(f'{output_dir}/eval/{load_step}_train', exist_ok=True)

    # eval test images
    test_eval_results = {
        "psnr": [],
        "ssim": [],
        "lpips": [],
    }
    # test_images = []
    for i in range(cfg.refine_start_idx, cfg.refine_end_idx):
        if test_from_train:
            rgb, _, _, _, _, eval_results = refiner.render(i, split='train', eval=True, trans=True)
        else:
            rgb, _, _, _, _, eval_results = refiner.render(i, split='test', eval=True, trans=True)
        if eval_test:
            test_eval_results["psnr"].append(eval_results["psnr"])
            test_eval_results["ssim"].append(eval_results["ssim"])
            test_eval_results["lpips"].append(eval_results["lpips"])
        save_image(rgb.permute(2,0,1), f'{output_dir}/eval/{load_step}_test/{i:03d}.jpg')
        
    #     fid_img = to_pil_image(rgb.permute(2,0,1))
    #     # fid_img = fid_img.resize((299, 299), Image.LANCZOS)
    #     fid_img = np.array(fid_img)
    #     test_images.append(torch.from_numpy(fid_img))
    # test_images = torch.stack(test_images).permute(0, 3, 1, 2).to(rgb.device)
    if eval_test:
        for k in test_eval_results:
            test_eval_results[k] = np.mean(test_eval_results[k])
        with open(f"{output_dir}/eval/{load_step}_test.json", "w") as f:
            json.dump(test_eval_results, f, indent=2)

    # eval train images
    train_eval_results = {
        "psnr": [],
        "ssim": [],
        "lpips": [],
    }
    # train_images = []
    for i in range(cfg.train_start_idx, cfg.train_end_idx):
        if test_from_train:
            rgb, _, _, _, _, eval_results = refiner.render(i, split='train', eval=True, trans=False)
        else:
            rgb, _, _, _, _, eval_results = refiner.render(i, split='train', eval=True, trans=False)
        train_eval_results["psnr"].append(eval_results["psnr"])
        train_eval_results["ssim"].append(eval_results["ssim"])
        train_eval_results["lpips"].append(eval_results["lpips"])
        save_image(rgb.permute(2,0,1), f'{output_dir}/eval/{load_step}_train/{i:03d}.jpg')

    #     fid_img = to_pil_image((refiner.train_dataset[i]['image'] / 255.).numpy())
    #     # fid_img = fid_img.resize((299, 299), Image.LANCZOS)
    #     fid_img = np.array(fid_img)
    #     train_images.append(torch.from_numpy(fid_img))
    # train_images = torch.stack(train_images).permute(0, 3, 1, 2).to(rgb.device)
    for k in train_eval_results:
        train_eval_results[k] = np.mean(train_eval_results[k])
    with open(f"{output_dir}/eval/{load_step}_train.json", "w") as f:
        json.dump(train_eval_results, f, indent=2)

    # fid = FrechetInceptionDistance(feature=64).to(refiner.device)
    # fid.reset()
    # fid.update(train_images, real=True)
    # fid.update(test_images, real=False)
    # fid_score = fid.compute()
    # with open(f"{output_dir}/eval/{load_step}_test_fid.json", "w") as f:
    #         json.dump({"fid": fid_score.item()}, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--exp_cfg', type=str, required=True, help='exp cfg path')
    parser.add_argument('--base_cfg', type=str, default="exp_cfg/base.yaml", help='base cfg path')
    parser.add_argument('--colmap-path', type=str, default=None, help='运行时覆盖数据集路径, 直接指向 COLMAP 场景目录')
    parser.add_argument('--ckpt-path', type=str, default=None, help='运行时覆盖基础模型 checkpoint 路径')
    parser.add_argument('--eval_test', action='store_true', help='eval test images')
    parser.add_argument('--test_from_train', action='store_true', help='test from train images')
    parser.add_argument('--load-step', type=int, default=None, help='覆盖基础模型评估用的 checkpoint step')
    parser.add_argument('--skip-refined', action='store_true', help='只评估基础模型, 跳过 refined checkpoint')
    args = parser.parse_args()
    base_cfg = OmegaConf.load(args.base_cfg)
    exp_cfg = OmegaConf.load(args.exp_cfg)
    cfg = OmegaConf.merge(base_cfg, exp_cfg)
    if args.colmap_path is not None:
        cfg.colmap_path = args.colmap_path
    if args.ckpt_path is not None:
        cfg.load_ckpt_path = args.ckpt_path

    base_load_step = resolve_base_load_step(cfg, args.load_step)
    eval(
        cfg,
        base_load_step,
        args.eval_test,
        args.test_from_train,
        use_ckpt_override=True,
        resume_load_step=base_load_step,
    )

    if args.skip_refined:
        print("Skip refined evaluation because --skip-refined was provided.")
    elif has_refined_checkpoint(cfg):
        eval(
            cfg,
            cfg.exp_name,
            args.eval_test,
            args.test_from_train,
            use_ckpt_override=False,
            resume_load_step=base_load_step,
        )
    else:
        print(
            "Skip refined evaluation because checkpoint does not exist: "
            f"{refined_checkpoint_path(cfg)}"
        )
