## [2026-03-27 09:28:12] [Session ID: 69645671-16e4-4f3c-8daa-df8f86b651f4] 笔记: FastGS 与 FreeFix checkpoint / PLY / 坐标系契约对齐

## 来源

### 来源1: `/home/rais/FastGS/train.py` 与 `/home/rais/FastGS/scene/gaussian_model.py`

- 要点:
  - `FastGS` 保存 checkpoint 的语句是 `torch.save((gaussians.capture(...), iteration), checkpoint_path)`。
  - `capture()` 的核心训练态字段顺序是:
    - `active_sh_degree`
    - `_xyz`
    - `_features_dc`
    - `_features_rest`
    - `_scaling`
    - `_rotation`
    - `_opacity`
    - 后面再跟优化器状态和 `spatial_lr_scale`
  - `save_ply()` 写出的字段顺序是:
    - `x/y/z`
    - `nx/ny/nz`
    - `f_dc_*`
    - `f_rest_*`
    - `opacity`
    - `scale_*`
    - `rot_*`

### 来源2: `/home/rais/FreeFix/recon/refiner.py` 与 `/home/rais/FreeFix/recon/trainer.py`

- 要点:
  - `Refiner` 当前默认读取 `cfg.result_dir/ckpts/ckpt_<step>.pt`。
  - 它期望的最小 SH 参数化字段是:
    - `means`
    - `opacities`
    - `quats`
    - `scales`
    - `sh0`
    - `shN`
  - `app_opt=true` 的训练线不会保存 `sh0/shN`, 而是保存:
    - `features`
    - `colors`

### 来源3: 动态样本 `/home/rais/FastGS/output/my4_mask_guarded_v4/checkpoints/ckpt_30000.pth`

- 要点:
  - 动态读取结果:
    - `_xyz`: `(55441, 3)`
    - `_features_dc`: `(55441, 1, 3)`
    - `_features_rest`: `(55441, 15, 3)`
    - `_scaling`: `(55441, 3)`
    - `_rotation`: `(55441, 4)`
    - `_opacity`: `(55441, 1)`
  - 这些形状和 `FreeFix` 的 SH checkpoint 结构是同构的, 只差命名、`opacity` 维度和外层容器。

### 来源4: 动态样本 `/home/rais/FastGS/output/my4_mask_guarded_v4/point_cloud/iteration_30000/point_cloud.ply`

- 要点:
  - 头部字段与 `FreeFix` 的 [export_3dgs_ply.py](/home/rais/FreeFix/recon/export_3dgs_ply.py) 导出产物同构。
  - 这意味着即使只有 `point_cloud.ply`, 也能恢复为 `means/sh0/shN/scales/quats/opacities` 这类高斯参数。

### 来源5: 动态相机对齐验证

- 要点:
  - `FastGS` run `my4_mask_guarded_v4` 使用的数据源是 `/home/rais/FreeFix/data/my4_fullcolmap`。
  - 直接比较 `FastGS/output/.../cameras.json` 与 `FreeFix Parser(data_dir=my4_fullcolmap, normalize=True)` 的 `camtoworlds`:
    - 平均位置误差约 `9.698`
    - 平均旋转矩阵差约 `2.108`
  - 但把 `FastGS` 相机先经过 `parser.transform` 后:
    - 位置误差均值降到接近 `0`
    - 旋转误差均值降到接近 `0`
  - `parser.transform[:3, :3]` 的奇异值三者相同, 说明它是“统一尺度 * 旋转”, 可以稳定作用到高斯位置、旋转、尺度。

## 综合发现

### 现象

- `FastGS` 的高斯内容本身和 `FreeFix` 的 SH 训练线是同类数据。
- `Refiner` 目前只是入口写死了 `FreeFix` 自家的 checkpoint 容器和路径。
- `FastGS` 的 run 里如果有 `.pth`, 可以无损度更高地桥接。
- 如果只有 `point_cloud.ply`, 也仍然有一条可行桥接路线。

### 当前假设

- 对 `app_opt=false` 的 FreeFix 训练线, 可以通过一个小型导入脚本把 `FastGS` 的 `.pth` 或 `.ply` 转成 `FreeFix` `ckpt`。
- 导入时必须同步做一层坐标归一化变换:
  - `means`: 应用 `parser.transform`
  - `quats`: 左乘归一化旋转部分
  - `scales`: 加上统一尺度的 `log(scale)`
- 只要目标 Refine 配置指向相同的数据源, 就不需要复用 `FastGS/cameras.json`。

### 备选解释

- 如果桥接后渲染仍有明显错位, 备选解释不是“字段映射错了”, 而是:
  - 目标 FreeFix 配置用了不同的数据目录
  - 或者用了 `app_opt=true` / 其他不兼容参数化
  - 或者用户想桥接的是只有 PLY、但 PLY 里已经丢失了一部分训练态信息的 run

### 最小实施方向

- 新增 `recon/import_fastgs.py`:
  - 输入 `FastGS` `.pth` 或 `.ply`
  - 输入目标 `data_dir`
  - 输出 `FreeFix` 风格 `ckpt`
- 给 `Refiner` 增加 `load_ckpt_path`
  - 让 `Flux/SDXL` refine 直接吃桥接产物
  - 不必污染已有 `outputs/*/ckpts`

## [2026-03-27 18:04:10] [Session ID: codex-fastgs-path-args-verify] 笔记: 路径参数入口补强后的验证结论

## 来源

### 来源1: 代码复核

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/import_fastgs.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`
- 要点:
  - `import_fastgs.py` 已支持:
    - `--ckpt-path`
    - `--ply-path`
    - `--colmap-path`
  - `refine_by_flux.py / refine_by_sdxl.py` 已支持:
    - `--colmap-path`
    - `--ckpt-path`
  - CLI 传入的 checkpoint 会一路落到 `Refiner(..., load_ckpt_path=...)`

### 来源2: 动态验证命令

- 语法检查:
  - `python3 -m py_compile recon/import_fastgs.py ours/refine_by_flux.py ours/refine_by_sdxl.py recon/refiner.py tests/test_import_fastgs.py tests/test_refine_cli_paths.py`
- 单测:
  - `/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_import_fastgs tests.test_refine_cli_paths tests.test_trainer_eval_path`
- CLI 帮助页:
  - `timeout 10s python3 ours/refine_by_flux.py --help`
  - `timeout 10s python3 ours/refine_by_sdxl.py --help`
- 桥接 smoke:
  - 用临时合成 `ckpt_34.pth`
  - 调用 `python -m recon.import_fastgs --ckpt-path <tmp_ckpt> --colmap-path /root/autodl-tmp/home/rais/FreeFix/data/my4_fullcolmap --output <tmp_out>`

### 来源3: 关键输出

- 单测结果:
  - `Ran 11 tests in 0.049s`
  - `OK`
- `--help` 输出已包含:
  - `--colmap-path COLMAP_PATH`
  - `--ckpt-path CKPT_PATH`
- 桥接 smoke 输出:
  - `[Parser] 264 images, taken by 1 cameras.`
  - `source_format: fastgs_checkpoint`
  - `step: 34`
  - `normalize_enabled: True`
  - `gaussian_count: 1`
  - `{'output_exists': True, 'step': 34, 'normalized_for_freefix': True, 'means_shape': (1, 3)}`

## 综合发现

### 现象

- 参数别名不只是静态存在, 已经被动态验证打通。
- `refine_by_flux.py / refine_by_sdxl.py` 原本存在 CLI 帮助页卡住的问题。

### 已验证结论

- 用户现在可以直接传:
  - `colmap path`
  - `ckpt path`
- 这组参数在桥接脚本和 refine 脚本里都已经可用。
- 为了让帮助页可用, 需要把 `OmegaConf` 以及模型 / 渲染相关重依赖延后到 `parse_args()` 之后再加载。

### 剩余边界

- 这次 bridge/refine 入口仍然是面向 `app_opt=false` 的 SH 训练线。
- “转过来的 ckpt 做 refine” 依然需要目标场景的原始图片和 COLMAP 目录, 因为 FreeFix 仍要自己建 parser、相机和归一化矩阵。

## [2026-03-27 18:20:00] [Session ID: codex-fastgs-one-shot-wrapper] 笔记: one-shot wrapper 的参数契约与验证结果

## 来源

### 来源1: 新增脚本

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`
- 要点:
  - wrapper 只负责 orchestration
  - 内部不会复制 bridge 或 refine 的实现
  - 顺序调用:
    - `python -m recon.import_fastgs`
    - `python ours/refine_by_flux.py` 或 `python ours/refine_by_sdxl.py`

### 来源2: 新增回归测试

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/tests/test_run_fastgs_refine.py`
- 要点:
  - 覆盖参数解析
  - 覆盖默认 bridge 输出路径
  - 覆盖 bridge / refine 命令拼接
  - 覆盖按顺序执行与 fail-fast 的 orchestration 行为
  - 覆盖 `python3 ours/run_fastgs_refine.py --help`

### 来源3: 动态验证命令

- 语法检查:
  - `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py`
- 单测:
  - `/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine tests.test_import_fastgs tests.test_refine_cli_paths tests.test_trainer_eval_path`
- CLI 帮助页:
  - `timeout 10s python3 ours/run_fastgs_refine.py --help`
- dry run:
  - `/home/rais/FreeFix/.pixi/envs/default/bin/python ours/run_fastgs_refine.py --ckpt-path <tmp> --colmap-path data/my4_fullcolmap --exp-cfg exp_cfg/my4/flux_shinkai_museum_v2.yaml --dry-run`

### 来源4: 关键输出

- 单测结果:
  - `Ran 17 tests in 0.087s`
  - `OK`
- `--help` 输出已包含:
  - `--ckpt-path`
  - `--ply-path`
  - `--colmap-path`
  - `--exp-cfg`
  - `--refine-backend`
  - `--dry-run`
- dry run 输出了两条内部命令:
  - 先 `recon.import_fastgs`
  - 后 `ours/refine_by_flux.py`

## 综合发现

### 现象

- 现在用户已经不需要再手工执行“先 bridge, 再 refine”两条命令。
- wrapper 如果不显式固定 `cwd`, 从仓库外目录调用时会有 `python -m recon.import_fastgs` 找不到模块的风险。

### 已验证结论

- `ours/run_fastgs_refine.py` 已经可以作为一条命令入口使用。
- 它默认走 `flux`, 也支持 `--refine-backend sdxl`。
- 子进程现在固定在仓库根目录执行, 因此入口对外部工作目录更稳。

### 当前边界

- wrapper 当前仍然面向 FastGS -> FreeFix `app_opt=false` 这条桥接链路。
- 如果未来要支持 `app_opt=true`, 应该扩展 bridge 参数化本身, 不是只改这个 wrapper。

## [2026-03-27 10:33:50] [Session ID: codex-refine-hessian-attr-explain] 笔记: `hessian_attr` 控制 certainty 掩码的属性来源, 不是冻结列表

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`

- 要点:
  - `Refiner.__init__()` 只是把 `hessian_attr` 保存到 `self.hessian_attr`。
  - 真正使用点在 `rasterize_splats_w_certainty()`:
    - 先对渲染出的 `rgbs[..., :3]` 反传
    - 再取 `self.splats[k].grad.detach() ** 2`
    - 最后把这些属性的 Hessian 近似量拼起来, 生成 `inv_H_gaussian = exp(-exp_index * H)`
  - `_init_optimizer()` 里 `means / scales / quats / opacities / sh0 / shN` 都各自建了优化器, 没有根据 `hessian_attr` 做冻结或白名单裁剪。

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py` 与 `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`

- 要点:
  - `refiner.render(i)` 返回的 `masks` 就是上一步 certainty 渲染产物。
  - 这些 `masks` 会直接传给 Flux / SDXL pipeline 的 `mask=` 参数。

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/ours/schedulers/euler_discrete_scheduler.py` 与 `/root/autodl-tmp/home/rais/FreeFix/ours/schedulers/flow_match_euler_discrete_scheduler.py`

- 要点:
  - guide 阶段融合公式是:
    - `x0 = prior_latents * mask + (1 - mask) * (...)`
  - 这意味着:
    - `mask` 越大, 越偏向保留原始渲染 latent
    - `mask` 越小, 越放开给生成模型 / warp 去改

### 来源4: 最小数值验证

- 命令:
  - `python3 - <<'PY' ... fused = prior*mask + (1-mask)*(warp*0.8 + x0*0.2) ... PY`
- 关键输出:
  - `mask=1.00 -> fused=10.00`
  - `mask=0.00 -> fused=22.00`
  - `mask=0.25 -> fused=19.00`
  - `mask=0.75 -> fused=13.00`
- 结论:
  - `mask=1` 时完全保留 prior
  - `mask=0` 时完全放开到新结果分支

## 综合发现

### 已验证结论

- `hessian_attr` 不是“保持这些参数不动”的配置。
- 它真正表达的是:
  - “在计算 certainty / guide mask 时, 哪些高斯属性的敏感度要算进去”
- 三个字段的真实含义是:
  - `means`: 高斯中心位置, 也就是空间坐标
  - `quats`: 高斯朝向四元数, 控制椭球旋转
  - `scales`: 高斯尺度参数, 当前存的是 log-scale, 渲染前会 `exp()` 成真实尺寸

### 语义推导

- 如果某个像素对 `means/quats/scales` 很敏感, 那么对应 Hessian 近似更大。
- Hessian 越大, `exp(-exp_index * H)` 越小, 最终 certainty 越低。
- certainty 越低, guide mask 越小, 生成阶段就越不“保原图”, 越允许修改。

### 对“想纠正结构”的配置含义

- 如果你只写 `["means"]`:
  - 只把“位置偏差”当成结构敏感来源
  - 修改会相对保守
- 如果你写 `["means", "quats", "scales"]`:
  - 把位置、朝向、尺寸都当成结构敏感来源
  - 几何相关区域更容易被放开编辑
  - 更适合“我怀疑结构本身就歪了, 想让 refine 更主动纠正”

### 风险提醒

- 这套逻辑放大的不是“稳稳修正”, 而是“更敢动结构相关区域”。
- 如果 prompt 很风格化、`strength` 太高、`warp_ratio` 太低, 也可能把结构一起带跑。
