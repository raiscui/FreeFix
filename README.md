<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">
  <h1>FreeFix: Boosting 3D Gaussian Splatting via Fine-Tuning-Free Diffusion Models</h1>
  
  <p>
    <a href="https://xdimlab.github.io/freefix/">
      <img src="https://img.shields.io/badge/Project-Page-green?style=for-the-badge" alt="Project Page" height="20">
    </a>
    <a href="https://arxiv.org/abs/2601.20857">
      <img src="https://img.shields.io/badge/arXiv-Paper-red?style=for-the-badge" alt="arXiv Paper" height="20">
    </a>
  </p>
  
  > Hongyu Zhou<sup>1</sup>, Zisen Saho<sup>2</sup>, Sheng Miao<sup>1</sup>, Pan Wang<sup>3</sup>, Dongfeng Bai<sup>3</sup>, Bingbing Liu<sup>3</sup>, Yiyi Liao<sup>1,†</sup> <br>
  > <sup>1</sup> Zhejiang University <sup>2</sup> University of Maryland, College Park <sup>3</sup> Huawei
  > <sup>†</sup> Corresponding Authors

  <img src="assets/teaser.png" width="800" style="display: block; margin: 0 auto;">

  <br>

  <p align="left">
    This is the official project repository of the paper <b>FreeFix: Boosting 3D Gaussian Splatting via Fine-Tuning-Free Diffusion Models</b>.
  </p>
  
</div>

---

# Installation

First, install [pixi](https://pixi.sh/latest/):

``` bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Then, install the environment by running:
```bash
pixi install
```

If you plan to build local CUDA extensions from this shell, run:

```bash
direnv allow
```

The reconstruction entrypoints in `recon/` also bootstrap the same pixi CUDA paths automatically, so direct commands such as `.pixi/envs/default/bin/python -m recon.trainer ...` keep working even when the shell has not loaded `direnv`.


# Data Preparation

Download the sample data from [here](https://huggingface.co/datasets/hyzhou404/FreeFix) and save it to the `data/` directory.

If you already have an external COLMAP-style scene directory and do not want to write back into that source directory, you can stage it into this repo with:

```bash
python -m recon.prepare_colmap_scene \
  --source-dir /path/to/external_scene \
  --dest-dir data/<scene_name>
```

The importer will:

- copy the minimum image subset needed by the COLMAP database into this repo
- copy metadata and build `meta/partition_source_names.json`
- copy an existing sparse model when available
- write `partition.json` only when it can verify the registered image list against the sparse model

If the source directory does not contain `sparse/` or `sparse/0`, you can rebuild it in the destination directory with:

```bash
python -m recon.prepare_colmap_scene \
  --source-dir /path/to/external_scene \
  --dest-dir data/<scene_name> \
  --rebuild-sparse \
  --colmap-binary /path/to/colmap \
  --force
```

If `colmap` is not in your `PATH`, the importer also tries common local locations automatically, including `/home/rais/.local/opt/colmap-env/bin/colmap`.

After the importer reports `"sparse_ready": true`, the scene can be used with the normal reconstruction command below.

# Reconstruction & Refine

## 1. Reconstruction

Train a 3D Gaussian Splatting model on the training views using the command:

```bash
python -m recon.trainer --data_dir <data_directory> --result_dir <result_directory> --data_type <colmap, hugsim>

# Example
python -m recon.trainer --data_dir data/mipnerf/bicycle_v2 --result_dir outputs/mipnerf/bicycle_v2 --data_factor 4 --data_type colmap
```

If you want a quick smoke test before a long run:

```bash
python -m recon.trainer \
  --data_dir <data_directory> \
  --result_dir <result_directory>_smoke \
  --data_type colmap \
  --max_steps 1 \
  --disable_viewer
```
<details>
  <summary>optional arguments</summary>

```text
--data_type <str>  # dataset type, choose from ['colmap', 'hugsim'] (default: colmap)
--data_factor <int>  # downsample factor for the input images
--prune_scale3d <float>  # scale3d threshold for pruning
--partition <str>  # partition file for training and validation
--strategy <str>  # training strategy, choose from ['mcmc', 'default']
```
</details>

The training results, including checkpoints and configuration files, will be saved in `<result_directory>`.

## 2. Refine

Refine the reconstructed model using a diffusion model (e.g., Flux). This step uses the pre-trained 3DGS model from the reconstruction step.

```bash
python -m ours.refine_by_flux --exp_cfg <exp_cfg_path>

# Example
python -m ours.refine_by_flux --exp_cfg exp_cfg/mipnerf/flux_bicycle_v2.yaml

# Kontext example
python -m ours.refine_by_kontext --exp_cfg exp_cfg/mipnerf/flux_bicycle_v2.yaml
```

**Note:**
- Ensure that the `base_dir` in your experiment configuration file matches the `<result_directory>` from the reconstruction step.
- You can find and customize configuration files in the `exp_cfg/` directory.
- Other refinement methods are also available (e.g., `ours/refine_by_sdxl.py`, `ours/refine_by_kontext.py`).
- `kontext` is an optional backend for image-edit / reference-guided repair scenarios. It does not replace the default `flux` path.
- `kontext` uses its own `kontext_model_path` config key. Do not point it at the `FLUX.1-dev` snapshot used by `flux_model_path`.

### External checkpoint bridge -> refine

If you already have a compatible 3DGS checkpoint from FastGS or fast-dropgs, you can bridge it into FreeFix and continue with the existing refine pipeline in one command:

```bash
python ours/run_fastgs_refine.py \
  --ckpt-path /path/to/ckpt_30000.pth \
  --colmap-path /path/to/colmap_scene \
  --exp-cfg exp_cfg/<scene>/flux_<scene>.yaml
```

To try the optional Kontext backend with the same wrapper:

```bash
python ours/run_fastgs_refine.py \
  --ckpt-path /path/to/ckpt_30000.pth \
  --colmap-path /path/to/colmap_scene \
  --exp-cfg exp_cfg/<scene>/flux_<scene>.yaml \
  --refine-backend kontext
```

The same entrypoint also accepts fast-dropgs checkpoints such as:

```bash
python ours/run_fastgs_refine.py \
  --ckpt-path /path/to/chkpnt50000.pth \
  --colmap-path /path/to/colmap_scene \
  --exp-cfg exp_cfg/<scene>/flux_<scene>.yaml
```

Notes:

- `--colmap-path` must match the scene that the checkpoint was trained on.
- `--exp-cfg` must point to a FreeFix refine config whose `base_dir` and runtime contract match the target scene.
- If the upstream checkpoint name is very generic, such as `chkpnt50000.pth`, prefer setting `--bridge-output` explicitly when you want a stable custom output path.
- Use `--dry-run` first if you want to inspect the bridge / refine / export commands before launching a real run.
- If you choose `--refine-backend kontext`, prepare a `FLUX.1-Kontext-dev` snapshot via `kontext_model_path` or the local cache path. Do not reuse `flux_model_path`.
- `kontext` keeps the current render as the primary edit image.
- In `pose_jitter` mode, FreeFix uses the original source camera image from the training dataset as the single `image_reference` when a conservative union edit mask can be derived. This keeps the jitter render as the composition anchor while borrowing faithful appearance cues from the original capture.
- `kontext` now auto-builds a shorter, more conservative prompt aimed at minimal cleanup rather than aggressive detail synthesis. When a reference image is present, it is framed as broad color / material guidance only.
- If the scene gets too “busy” or over-sharpened, prefer setting `kontext_prompt` and `kontext_negative_prompt` instead of reusing the main `flux` prompt pair unchanged.
- If no compatible mask can be derived, FreeFix falls back to plain `FluxKontextPipeline`.
- `kontext` does not currently promise one-to-one parity with the private `mask_scheduler` / `warp_*` behavior used by the custom `flux` / `sdxl` pipelines.

**Pose jitter quick start:**
- In `exp_cfg/base.yaml` or your experiment yaml, set `refine_camera_mode: pose_jitter`.
- Recommended first-pass values:
  - `refine_camera_source_split: train`
  - `pose_jitter_trans_sigma: [0.02, 0.02, 0.02]`
  - `pose_jitter_trans_max: [0.05, 0.05, 0.05]`
  - `pose_jitter_rot_sigma_deg: [1.5, 1.5, 1.5]`
  - `pose_jitter_rot_max_deg: [4.0, 4.0, 4.0]`
- `before_refine` / `after_refine` stay on the fixed comparison views from `refine_start_idx` to `refine_end_idx`.
- If you want every source camera to branch into multiple synthetic views, set `pose_jitter_views_per_source`.
- If you want pose jitter to draw from multiple named splits, use:
  - `refine_camera_source_splits: [train, test]`
  - `refine_train_splits: [train, test]`
- Example: if `train + test` gives `324` source cameras and `pose_jitter_views_per_source: 3`, the synthetic supervise plan becomes `972` views.
- Leaving `refine_train_splits` / `refine_camera_source_splits` unset keeps the old range-based behavior.
- Do not include benchmark eval cameras unless you explicitly accept that the refine run will change the evaluation semantics.
- Each run writes `refine/pose_jitter_log.jsonl`, which records sampling attempts, alpha-coverage filtering, and fallback decisions.
- Each run also writes `refine_resume_state.json` and keeps a rolling resume checkpoint at `ckpts/ckpt_<exp_name>__resume_latest.pt`, so interrupted refine runs can resume instead of starting from scratch.
- `before_refine` / `after_refine` now use batched fixed-view RGB rasterization controlled by `refine_fixed_render_batch_size`, rather than writing those comparison videos one camera at a time.
- Resume behavior is controlled by:
  - `refine_resume_enabled`
  - `refine_resume_save_every_plans`
  - `refine_fixed_render_batch_size`
- If Flux or SDXL refine appears to stall around pipeline placement, try `refine_pipeline_offload_mode: model_cpu` before assuming the pose-jitter path is broken.

## 3. Evaluation

Evaluate the quantitative results (PSNR, SSIM, LPIPS) of both the reconstructed and refined models.

```bash
python -m ours.evaluation --exp_cfg <exp_cfg_path> --eval_test

# Example
python -m ours.evaluation --exp_cfg exp_cfg/mipnerf/flux_bicycle_v2.yaml --eval_test
```

The evaluation results will be saved in `<result_directory>/<exp_name>/eval/`:
- `29999_test.json`: Metrics for the original reconstruction (step 29999).
- `<exp_name>_test.json`: Metrics for the refined model (e.g., `flux_test.json`).

# Citation

If you find our paper and codes useful, please kindly cite us via:

```bibtex
@inproceedings{zhou2026freefix,
  title={FreeFix: Boosting 3D Gaussian Splatting via Fine-Tuning-Free Diffusion Models},
  author={Zhou, Hongyu and Shao, Zisen and Miao, Sheng and Wang, Pan and Bai, Dongfeng and Liu, Bingbing and Liao, Yiyi},
  booktitle={Thirteenth International Conference on 3D Vision},
  year={2026}
}
```
