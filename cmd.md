# my4 操作命令


  python3 -m recon.prepare_colmap_scene \
    --source-dir data/my4 \
    --dest-dir /root/autodl-tmp/home/rais/FreeFix/data/my4_rebuild \
    --rebuild-sparse \
    --colmap-binary /home/rais/.local/opt/colmap-env/bin/colmap \
    --force

  .pixi/envs/default/bin/python -m recon.train_from_yaml \
    --config exp_cfg/my4/recon_my4.yaml \
    --set result_dir=outputs/my4_quality_probe \
    --set disable_viewer=true \
    --set max_steps=50000 \
    --set eval_steps=[10000,30000,50000] \
    --set save_steps=[10000,30000,50000] \
    --set refine_stop_iter=30000 \
    --set pose_opt=true \
    --set app_opt=true




.pixi/envs/default/bin/python -m ours.refine_by_flux \
  --exp_cfg exp_cfg/dm7/flux_dm7_sr_30k_pose_jitter_v6-5.yaml

.pixi/envs/default/bin/python -m ours.refine_by_kontext \
--exp_cfg exp_cfg/nt6/flux_nt6_sr_35k_guarded_pose_jitter_v2.yaml

.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt7/flux_nt7_sr_35k_guarded_pose_jitter_v2_from_v1.yaml

.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt6/flux_nt6_sr_35k_guarded_pose_jitter_v2_from_v2.yaml

---------
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt1/flux_nt1_sr_35k_guarded_pose_jitter_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt2/flux_nt2_sr_35k_guarded_pose_jitter_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt3/flux_nt3_sr_35k_guarded_pose_jitter_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt4/flux_nt4_sr_35k_guarded_pose_jitter_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt5/flux_nt5_sr_35k_guarded_pose_jitter_v2.yaml

  第二轮

  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt1/flux_nt1_sr_35k_guarded_pose_jitter_v2_from_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt2/flux_nt2_sr_35k_guarded_pose_jitter_v2_from_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt3/flux_nt3_sr_35k_guarded_pose_jitter_v2_from_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt4/flux_nt4_sr_35k_guarded_pose_jitter_v2_from_v2.yaml
  ./.pixi/envs/default/bin/python -m ours.refine_by_kontext --exp_cfg exp_cfg/nt5/flux_nt5_sr_35k_guarded_pose_jitter_v2_from_v2.yaml



  cd /root/autodl-tmp/home/rais/FreeFix
  mkdir -p data/fastgs_bridge/nt7_sr_35000_guarded
  ./.pixi/envs/default/bin/python -m recon.import_fastgs \
    --ply-path /autodl-fs/data/fastgs/output/nt7_sr_35000_guarded/point_cloud/iteration_35000/point_cloud.ply \
    --data-dir /autodl-fs/data/fastgs/nt7_sr \
    --output data/fastgs_bridge/nt7_sr_35000_guarded/ckpt_35000_freefix.pt

    -------------



  CUDA_VISIBLE_DEVICES=0   TORCH_EXTENSIONS_DIR=/root/autodl-tmp/home/rais/.cache/torch_extensions \
  TORCH_CUDA_ARCH_LIST=12.0 \
  MAX_JOBS=1 \
  OMP_NUM_THREADS=8 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  .pixi/envs/default/bin/python3 -u -m ours.refine_by_kontext \
    --exp_cfg outputs/dm4_colmap_fastgs_stable_30k_dense/flux_dm4_sr_from_dm7_30k_pose_jitter_v6-5.yaml \
    --base_cfg exp_cfg/base.yaml \
    --colmap-path /autodl-fs/data/fastgs/dm4_sr \
    --ckpt-path data/fastgs_bridge/dm4_sr_35000_guarded/ckpt_35000_freefix.pt

  CUDA_VISIBLE_DEVICES=1   TORCH_EXTENSIONS_DIR=/root/autodl-tmp/home/rais/.cache/torch_extensions \
  TORCH_CUDA_ARCH_LIST=12.0 \
  MAX_JOBS=1 \
  OMP_NUM_THREADS=8 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  .pixi/envs/default/bin/python3 -u -m ours.refine_by_kontext \
    --exp_cfg outputs/dm5_colmap_fastgs_stable_30k_dense/flux_dm5_sr_from_dm7_30k_pose_jitter_v6-5.yaml \
    --base_cfg exp_cfg/base.yaml \
    --colmap-path /autodl-fs/data/fastgs/dm5_sr \
    --ckpt-path data/fastgs_bridge/dm5_sr_35000_guarded/ckpt_35000_freefix.pt


## 0. 让当前 shell 拿到项目自己的 CUDA 工具链

```bash
direnv allow
```

## 1. 查看系统 CUDA COLMAP

```bash
/home/rais/.local/opt/colmap-env/bin/colmap -h
```

## 2. 把外部 my4 数据导入到当前项目 data 目录

```bash
python3 -m recon.prepare_colmap_scene \
  --source-dir /home/rais/CoherentGS/data/my4 \
  --dest-dir /home/rais/FreeFix/data/my4 \
  --force
```

## 3. 如果以后源目录缺少 sparse, 用系统 CUDA COLMAP 在目标目录内重建

```bash
python3 -m recon.prepare_colmap_scene \
  --source-dir /home/rais/CoherentGS/data/my4 \
  --dest-dir /home/rais/FreeFix/data/my4 \
  --rebuild-sparse \
  --colmap-binary /home/rais/.local/opt/colmap-env/bin/colmap \
  --force
```

## 4. 重新导入到新的目标目录做对照验证

```bash
python3 -m recon.prepare_colmap_scene \
  --source-dir /home/rais/CoherentGS/data/my4 \
  --dest-dir /home/rais/FreeFix/data/my4_reimport \
  --force
```

## 5. 验证导入结果

```bash
python3 - <<'PY'
import json
from pathlib import Path

root = Path('/home/rais/FreeFix/data/my4')
report = json.loads((root / 'import_report.json').read_text())
partition = json.loads((root / 'partition.json').read_text())

print('copied_image_count =', report['copied_image_count'])
print('sparse_ready =', report['sparse_ready'])
print('partition_ready =', report['partition_ready'])
print('train_count =', len(partition['train']))
print('test_count =', len(partition['test']))
PY
```

## 6. 用项目环境验证 Parser 能直接读取 data/my4

```bash
.pixi/envs/default/bin/python - <<'PY'
from recon.datasets.colmap import Parser

parser = Parser(data_dir='data/my4', factor=1, normalize=True, test_every=1)
print('image_count', len(parser.image_names))
print('point_count', parser.points.shape[0])
print('camera_count', len(set(parser.camera_ids)))
print('first_image', parser.image_names[0])
print('scene_scale', float(parser.scene_scale))
PY
```

## 7. 用项目环境验证 Dataset 和 partition.json

```bash
.pixi/envs/default/bin/python - <<'PY'
from recon.datasets.colmap import Parser, Dataset

parser = Parser(data_dir='data/my4', factor=1, normalize=False, test_every=1)
dataset = Dataset(parser, split='train', partition_file='data/my4/partition.json')
item = dataset[0]

print('dataset_len', len(dataset))
print('image_shape', tuple(item['image'].shape))
print('K_shape', tuple(item['K'].shape))
print('c2w_shape', tuple(item['camtoworld'].shape))
print('image_id', int(item['image_id']))
PY
```

## 8. 先做 1 step smoke test

```bash
.pixi/envs/default/bin/python -m recon.trainer \
  --data_dir data/my4 \
  --result_dir outputs/my4_smoke \
  --data_type colmap \
  --max_steps 1 \
  --disable_viewer
```

## 9. 启动 my4 训练

```bash
.pixi/envs/default/bin/python -m recon.trainer \
  --data_dir data/my4 \
  --result_dir outputs/my4 \
  --data_type colmap
```

## 10. 用 YAML 配置复现 `outputs/my4` 训练

```bash
.pixi/envs/default/bin/python -m recon.train_from_yaml \
  --config exp_cfg/my4/recon_my4.yaml
```

## 11. 用 YAML 配置做 1 step smoke test

```bash
.pixi/envs/default/bin/python -m recon.train_from_yaml \
  --config exp_cfg/my4/recon_my4.yaml \
  --set disable_viewer=true \
  --set max_steps=1 \
  --set result_dir=outputs/my4_yaml_smoke
```

## 12. 从 `outputs/my4` 导出 3DGS PLY

```bash
.pixi/envs/default/bin/python -m recon.export_3dgs_ply \
  --result-dir outputs/my4
```

## 13. 如果要从原始图片重新跑 COLMAP convert 流程

```bash
python3 recon/convert.py \
  --source_path /path/to/your_scene \
  --colmap_executable /home/rais/.local/opt/colmap-env/bin/colmap
```

## 14. 当前精简版 `my4` 全量重跑 COLMAP 的实际命令

### 14.1 准备新的 full-COLMAP 工作目录

```bash
python3 - <<'PY'
from pathlib import Path
import json
import shutil
from recon.prepare_colmap_scene import read_partition_source_names, filter_existing_image_names

src = Path('data/my4')
dst = Path('data/my4_fullcolmap')

if dst.exists():
    raise SystemExit(f'destination already exists: {dst}')

(dst / 'input').mkdir(parents=True, exist_ok=False)
(dst / 'meta').mkdir(parents=True, exist_ok=True)

files = sorted([p for p in (src / 'images').iterdir() if p.is_file()])
for path in files:
    shutil.copy2(path, dst / 'input' / path.name)

train_names, test_names, source_name = read_partition_source_names(src)
train_names, missing_train = filter_existing_image_names(src / 'images', train_names)
test_names, missing_test = filter_existing_image_names(src / 'images', test_names)

(dst / 'meta' / 'partition_source_names.json').write_text(
    json.dumps({'train': train_names, 'test': test_names}, indent=2, ensure_ascii=False) + '\n',
    encoding='utf-8',
)
(dst / 'meta' / 'full_colmap_prep_report.json').write_text(
    json.dumps(
        {
            'source_dir': str(src.resolve()),
            'input_image_count': len(files),
            'partition_source': source_name,
            'filtered_train_count': len(train_names),
            'filtered_test_count': len(test_names),
            'dropped_train_names': missing_train,
            'dropped_test_names': missing_test,
        },
        indent=2,
        ensure_ascii=False,
    ) + '\n',
    encoding='utf-8',
)

print({
    'dest': str(dst),
    'input_image_count': len(files),
    'filtered_train_count': len(train_names),
    'filtered_test_count': len(test_names),
    'partition_source': source_name,
})
PY
```

### 14.2 如果之前跑失败过, 先清掉半成品输出

```bash
rm -rf \
  data/my4_fullcolmap/distorted \
  data/my4_fullcolmap/images \
  data/my4_fullcolmap/sparse \
  data/my4_fullcolmap/images_2 \
  data/my4_fullcolmap/images_4 \
  data/my4_fullcolmap/images_8
```

### 14.3 运行完整 COLMAP 流程

```bash
python3 recon/convert.py \
  --source_path data/my4_fullcolmap \
  --colmap_executable /home/rais/.local/opt/colmap-env/bin/colmap
```

说明:
最新的 `recon/convert.py` 会自动在 `distorted/sparse/*` 里选择“注册图数量最多”的模型做 undistort, 不再盲目固定使用 `distorted/sparse/0`。

### 14.3.1 如果 mapper 已经完成, 但之前 undistort 选错了小模型, 只重跑后处理

```bash
rm -rf data/my4_fullcolmap/images data/my4_fullcolmap/sparse

python3 recon/convert.py \
  --source_path data/my4_fullcolmap \
  --colmap_executable /home/rais/.local/opt/colmap-env/bin/colmap \
  --skip_matching
```

### 14.4 重建完成后, 基于保留图片重新生成 `partition.json`

```bash
python3 - <<'PY'
from pathlib import Path
import json
from recon.prepare_colmap_scene import build_partition
from recon.datasets.colmap_io import load_registered_image_names

root = Path('data/my4_fullcolmap')
meta = json.loads((root / 'meta' / 'partition_source_names.json').read_text())
registered_names = load_registered_image_names(root / 'sparse' / '0')
partition, warnings = build_partition(
    registered_image_names=registered_names,
    train_names=meta['train'],
    test_names=meta['test'],
)
print('warnings =', warnings)
if partition is None:
    raise SystemExit('partition.json could not be generated')
(root / 'partition.json').write_text(
    json.dumps(partition, indent=2, ensure_ascii=False) + '\n',
    encoding='utf-8',
)
print({
    'train_count': len(partition['train']),
    'test_count': len(partition['test']),
})
PY
```

## 15. 用增强参数在 `data/my4_fullcolmap` 上启动画质优先训练

```bash
.pixi/envs/default/bin/python -m recon.train_from_yaml \
  --config exp_cfg/my4/recon_my4_fullcolmap_quality.yaml
```

说明:
- 这份配置已经启用:
  - `max_steps=50000`
  - `refine_stop_iter=30000`
  - `pose_opt=true`
  - `app_opt=true`
  - `depth_loss=true`
- 第一份 checkpoint 会落成 `ckpt_999.pt`, 因为当前 trainer 的保存步号是 zero-based。

## 16. 先对增强参数做 1 step smoke test

```bash
rm -rf outputs/my4_fullcolmap_quality_smoke

.pixi/envs/default/bin/python -m recon.train_from_yaml \
  --config exp_cfg/my4/recon_my4_fullcolmap_quality.yaml \
  --set result_dir=outputs/my4_fullcolmap_quality_smoke \
  --set max_steps=1 \
  --set eval_steps=[1] \
  --set save_steps=[1]
```

## 17. 手动评测指定 checkpoint, 并导出测试集图片

```bash
rm -rf outputs/my4_fullcolmap_quality_eval_9999

.pixi/envs/default/bin/python - <<'PY'
from pathlib import Path
import torch
from recon.train_from_yaml import load_config
from recon.trainer import Runner

config_path = Path('exp_cfg/my4/recon_my4_fullcolmap_quality.yaml')
result_dir = 'outputs/my4_fullcolmap_quality_eval_9999'
ckpt_path = Path('outputs/my4_fullcolmap_quality/ckpts/ckpt_9999.pt')

cfg = load_config(config_path, [f'result_dir={result_dir}'])
runner = Runner(cfg)
ckpt = torch.load(ckpt_path, map_location=runner.device)
for key in runner.splats.keys():
    runner.splats[key].data = ckpt['splats'][key]
runner.eval(step=int(ckpt['step']))
print({'eval_result_dir': result_dir, 'step': int(ckpt['step'])})
PY
```

说明:
- 评测指标会落到:
  - `outputs/my4_fullcolmap_quality_eval_9999/stats/val_step9999.json`
- 图片会落到:
  - `renders/concat/`
  - `renders/rgbs/`
  - `renders/alphas/`
  - `renders/certainties/`

## 18. 生成评测图片总览图

```bash
python3 - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw

root = Path('outputs/my4_fullcolmap_quality_eval_9999/renders')
indices = [0, 14, 28, 42, 56, 70, 84, 98, 111]

for subdir, output_name in [('concat', 'preview_concat_grid.png'), ('rgbs', 'preview_rgb_grid.png')]:
    images = []
    for index in indices:
        path = root / subdir / f'{index:04d}.png'
        image = Image.open(path).convert('RGB')
        draw = ImageDraw.Draw(image)
        label = f'{index:04d}'
        draw.text((13, 13), label, fill=(0, 0, 0))
        draw.text((12, 12), label, fill=(255, 255, 255))
        images.append(image)

    tile_w, tile_h = images[0].size
    grid = Image.new('RGB', (tile_w * 3, tile_h * 3), color=(18, 18, 18))
    for i, image in enumerate(images):
        grid.paste(image, ((i % 3) * tile_w, (i // 3) * tile_h))
    grid.save(root / output_name)
    print(root / output_name)
PY
```

## 19. 手动评测 `ckpt_29999.pt`, 并导出测试集图片

```bash
.pixi/envs/default/bin/python - <<'PY'
from pathlib import Path
import shutil
import torch
from recon.train_from_yaml import load_config
from recon.trainer import Runner

config_path = Path('exp_cfg/my4/recon_my4_fullcolmap_quality.yaml')
result_dir = Path('outputs/my4_fullcolmap_quality_eval_29999')
ckpt_path = Path('outputs/my4_fullcolmap_quality/ckpts/ckpt_29999.pt')

if result_dir.exists():
    shutil.rmtree(result_dir)

cfg = load_config(config_path, [f'result_dir={result_dir.as_posix()}'])
runner = Runner(cfg)
ckpt = torch.load(ckpt_path, map_location=runner.device)
for key in runner.splats.keys():
    runner.splats[key].data = ckpt['splats'][key]
runner.eval(step=int(ckpt['step']))
print({'eval_result_dir': result_dir.as_posix(), 'step': int(ckpt['step'])})
PY
```

说明:
- 指标会落到:
  - `outputs/my4_fullcolmap_quality_eval_29999/stats/val_step29999.json`
- 图片会落到:
  - `outputs/my4_fullcolmap_quality_eval_29999/renders/`

## 20. 生成三档 checkpoint 对照总览图

```bash
python3 - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

base = Path('/root/autodl-tmp/home/rais/FreeFix')
out_dir = base / 'outputs' / 'my4_fullcolmap_quality_eval_compare'
out_dir.mkdir(parents=True, exist_ok=True)

columns = [
    ('9999', 'best so far', 'outputs/my4_fullcolmap_quality_eval_9999', 'PSNR 23.1868 | SSIM 0.8350 | LPIPS 0.2547', (70, 126, 85)),
    ('29999', 'mid checkpoint', 'outputs/my4_fullcolmap_quality_eval_29999', 'PSNR 22.7931 | SSIM 0.8258 | LPIPS 0.2675', (84, 104, 138)),
    ('49999', 'final checkpoint', 'outputs/my4_fullcolmap_quality_eval_49999', 'PSNR 22.8325 | SSIM 0.8253 | LPIPS 0.2585', (153, 92, 47)),
]

concat_images = []
rgb_images = []
for _, _, rel_dir, _, _ in columns:
    render_dir = base / rel_dir / 'renders'
    concat_images.append(Image.open(render_dir / 'preview_concat_grid.png').convert('RGB'))
    rgb_images.append(Image.open(render_dir / 'preview_rgb_grid.png').convert('RGB'))

concat_size = concat_images[0].size
rgb_size = rgb_images[0].size
margin = 24
header_h = 120
label_h = 62
section_gap = 26
col_gap = 18
canvas_w = margin * 2 + concat_size[0] * 3 + col_gap * 2
canvas_h = margin + header_h + label_h + concat_size[1] + section_gap + label_h + rgb_size[1] + margin
canvas = Image.new('RGB', (canvas_w, canvas_h), (246, 244, 238))
draw = ImageDraw.Draw(canvas)
try:
    font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
    font_sub = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    font_label = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
except Exception:
    font_title = font_sub = font_label = font_small = ImageFont.load_default()

header_box = (margin, margin, canvas_w - margin, margin + header_h)
draw.rounded_rectangle(header_box, radius=18, fill=(30, 47, 67))
draw.text((margin + 18, margin + 16), 'my4_fullcolmap_quality checkpoint comparison', fill=(255, 255, 255), font=font_title)
draw.text((margin + 18, margin + 58), 'Same test split, same manual eval path, three checkpoints side by side', fill=(224, 230, 239), font=font_sub)
draw.text((margin + 18, margin + 84), 'Observation: 9999 is still the strongest checkpoint on current test metrics', fill=(204, 244, 206), font=font_sub)

concat_label_y = margin + header_h
rgb_label_y = concat_label_y + label_h + concat_size[1] + section_gap
concat_y = concat_label_y + label_h
rgb_y = rgb_label_y + label_h

for idx, (step, note, _, metric, color) in enumerate(columns):
    x = margin + idx * (concat_size[0] + col_gap)
    draw.text((x + 6, concat_label_y + 10), f'Concat preview | ckpt_{step}', fill=(23, 26, 33), font=font_label)
    draw.text((x + 6, concat_label_y + 36), note, fill=(92, 98, 109), font=font_small)
    draw.text((x + 6, rgb_label_y + 10), f'RGB preview | ckpt_{step}', fill=(23, 26, 33), font=font_label)
    draw.text((x + 6, rgb_label_y + 36), metric, fill=(92, 98, 109), font=font_small)
    canvas.paste(concat_images[idx], (x, concat_y))
    canvas.paste(rgb_images[idx], (x, rgb_y))
    pill_x = x + 10
    for base_y in (concat_y, rgb_y):
        draw.rounded_rectangle((pill_x, base_y + 10, pill_x + 190, base_y + 46), radius=13, fill=color)
        draw.text((pill_x + 15, base_y + 18), f'ckpt_{step}', fill=(255, 255, 255), font=font_sub)

png_path = out_dir / 'summary_compare_3way.png'
canvas.save(png_path)

jpg = canvas.copy()
max_width = 3000
if jpg.width > max_width:
    ratio = max_width / jpg.width
    jpg = jpg.resize((int(jpg.width * ratio), int(jpg.height * ratio)))
jpg_path = out_dir / 'summary_compare_3way_web.jpg'
jpg.save(jpg_path, quality=88, optimize=True)
print(png_path)
print(jpg_path)
print(jpg.size)
PY
```

## 21. 当前已验证最佳方法: `my4_fullcolmap stable_12k_dense`

当前冻结口径:
- 数据目录: `data/my4_fullcolmap`
- 配置文件: `exp_cfg/my4/recon_my4_fullcolmap_stable_12k_dense.yaml`
- 关键参数:
  - `max_steps=12000`
  - `refine_stop_iter=9000`
  - `pose_opt=true`
  - `app_opt=false`
  - `depth_loss=true`
- 当前最佳 checkpoint:
  - `outputs/my4_fullcolmap_stable_12k_dense/ckpts/ckpt_11999.pt`
- 当前最佳指标:
  - `PSNR 25.9338`
  - `SSIM 0.8617`
  - `LPIPS 0.2216`

## 22. 当前最佳方法的 1 step smoke test

```bash
rm -rf outputs/my4_fullcolmap_stable_12k_dense_smoke

.pixi/envs/default/bin/python -m recon.train_from_yaml \
  --config exp_cfg/my4/recon_my4_fullcolmap_stable_12k_dense.yaml \
  --set result_dir=outputs/my4_fullcolmap_stable_12k_dense_smoke \
  --set max_steps=1 \
  --set eval_steps=[1] \
  --set save_steps=[1]
```

## 23. 当前最佳方法的正式训练命令

```bash
.pixi/envs/default/bin/python -m recon.train_from_yaml \
  --config exp_cfg/my4/recon_my4_fullcolmap_stable_12k_dense.yaml
```

说明:
- 这条命令会在:
  - `outputs/my4_fullcolmap_stable_12k_dense/`
  下落盘结果
- 保存点对应:
  - `ckpt_8999.pt`
  - `ckpt_9999.pt`
  - `ckpt_10999.pt`
  - `ckpt_11999.pt`

## 24. 当前最佳方法的四档手动评测命令

```bash
cat <<'PY' > /tmp/eval_my4_stable_12k_dense_best.py
from pathlib import Path
import json
import shutil
import torch
from recon.train_from_yaml import load_config
from recon.trainer import Runner

config_path = Path('exp_cfg/my4/recon_my4_fullcolmap_stable_12k_dense.yaml')
base = Path('outputs/my4_fullcolmap_stable_12k_dense')
steps = [8999, 9999, 10999, 11999]
summary = []

for step in steps:
    result_dir = Path(f'outputs/my4_fullcolmap_stable_12k_dense_eval_{step}')
    ckpt_path = base / 'ckpts' / f'ckpt_{step}.pt'
    if result_dir.exists():
        shutil.rmtree(result_dir)

    cfg = load_config(config_path, [f'result_dir={result_dir.as_posix()}'])
    runner = Runner(cfg)
    ckpt = torch.load(ckpt_path, map_location=runner.device)
    for key in runner.splats.keys():
        runner.splats[key].data = ckpt['splats'][key]
    runner.eval(step=int(ckpt['step']))

    stats_path = result_dir / 'stats' / f'val_step{step}.json'
    stats = json.loads(stats_path.read_text())
    stats['step'] = step
    summary.append(stats)

compare_dir = Path('outputs/my4_fullcolmap_stable_12k_dense_eval_compare')
compare_dir.mkdir(parents=True, exist_ok=True)
(compare_dir / 'summary_4way.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding='utf-8',
)

print(json.dumps(summary, ensure_ascii=False, indent=2))
PY

PYTHONPATH=/root/autodl-tmp/home/rais/FreeFix \
  .pixi/envs/default/bin/python /tmp/eval_my4_stable_12k_dense_best.py
```

说明:
- 评测汇总会落到:
  - `outputs/my4_fullcolmap_stable_12k_dense_eval_compare/summary_4way.json`
- 当前最佳一档对应:
  - `outputs/my4_fullcolmap_stable_12k_dense_eval_11999/stats/val_step11999.json`

## 25. 当前最佳 checkpoint 的导视频命令

```bash
.pixi/envs/default/bin/python -m recon.trainer \
  --data_dir data/my4_fullcolmap \
  --result_dir outputs/my4_fullcolmap_stable_12k_dense \
  --data_type colmap \
  --ckpt outputs/my4_fullcolmap_stable_12k_dense/ckpts/ckpt_11999.pt \
  --disable_viewer
```

说明:
- 视频会落到:
  - `outputs/my4_fullcolmap_stable_12k_dense/to_refine/render.mp4`
  - `outputs/my4_fullcolmap_stable_12k_dense/to_refine/alpha.mp4`

## 26. 当前最佳结果统一入口

- 人类可读入口:
  - `outputs/my4_fullcolmap_stable_12k_dense/BEST_RESULT.md`
- 机器可读入口:
  - `outputs/my4_fullcolmap_stable_12k_dense/best_result_manifest.json`

## 27. `my4_fullcolmap_v2 best` 的 Flux refine 观感检查命令

```bash
.pixi/envs/default/bin/python -m ours.refine_by_flux \
  --exp_cfg exp_cfg/my4/flux_shinkai_museum_v2.yaml
```

说明:
- 这条命令当前绑定的是:
  - 基础结果目录: `outputs/my4_fullcolmap_v2_stable_12k_dense`
  - 基础 checkpoint: `outputs/my4_fullcolmap_v2_stable_12k_dense/ckpts/ckpt_11999.pt`
- 当前这版 prompt 已经做过二次压缩:
  - 真实日志里不再出现 `CLIP 77 tokens` 截断 warning
- 主要产物会落到:
  - `outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/before_refine.mp4`
  - `outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/after_refine.mp4`
  - `outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2/refine/gen.mp4`
  - `outputs/my4_fullcolmap_v2_stable_12k_dense/ckpts/ckpt_flux_shinkai_museum_v2.pt`


## 配置里 怎么 改 才是用 refine_by_kontext


• 当前实现里, 只改配置文件还不够。

  真正决定走 refine_by_kontext 的开关, 现在在命令行参数这里:
  ours/run_fastgs_refine.py

  你有两种用法。

  1. 用 wrapper 跑
  这时要显式加:

  --refine-backend kontext

  例如:

  python ours/run_fastgs_refine.py \
    --ckpt-path /path/to/ckpt_30000.pth \
    --colmap-path /path/to/colmap_scene \
    --exp-cfg exp_cfg/<scene>/your.yaml \
    --refine-backend kontext

  2. 直接跑 Kontext 入口
  这时不用配 backend 参数, 直接调用:
  ours/refine_by_kontext.py

  python -m ours.refine_by_kontext --exp_cfg exp_cfg/<scene>/your.yaml

  配置文件里要改的, 是 Kontext 自己的参数
  这些键现在在 exp_cfg/base.yaml:

  kontext_model_path: /path/to/FLUX.1-Kontext-dev
  kontext_strength: 0.5
  kontext_num_inference_steps: 50
  kontext_guidance_scale: 2.5

  最关键的是:

  kontext_model_path: /你的/FLUX.1-Kontext-dev/目录

  注意两点:

  - 不要把 kontext_model_path 指到 FLUX.1-dev
  - flux_model_path 还是给旧的 flux backend 用的, 两个不要混