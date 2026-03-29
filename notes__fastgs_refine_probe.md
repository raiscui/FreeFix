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

## [2026-03-28 17:18:41] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] 笔记: refined ckpt 与最终 3DGS PLY 导出缺口

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py` 与 `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`

- 要点:
  - 两个 refine 入口在流程结束时都只调用 `refiner.save(name=f"ckpt_{cfg.exp_name}")`
  - 当前没有继续触发 `.ply` 导出
  - 因此 refine 结束后的“最终可交换 3DGS 资产”目前仍停在 checkpoint 形态

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`

- 要点:
  - `Refiner.save()` 的落盘位置是:
    - `f"{self.cfg.result_dir}/ckpts/{name}.pt"`
  - 也就是说 refined 结果的标准路径是:
    - `<result_dir>/ckpts/ckpt_<exp_name>.pt`

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/recon/export_3dgs_ply.py`

- 要点:
  - 已具备完整的 checkpoint -> 3DGS PLY 导出逻辑
  - 当前脚本内部已经分离出:
    - `load_splats_from_checkpoint`
    - `build_ply_matrix`
    - `write_binary_ply`
  - 这意味着最佳改法不是复制导出逻辑, 而是把现有能力封成可复用函数, 再从 refine 流程复用

### 来源4: `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`

- 要点:
  - 当前 wrapper 只顺序执行:
    - `python -m recon.import_fastgs`
    - `python -m ours.refine_by_flux|sdxl`
  - wrapper 本身也没有“最终导出 refined ply”的第三步

## 综合发现

### 现象

- 当前链路已经能桥接 FastGS 输入, 也能完成 refine。
- 真正缺的是最后一跳:
  - refined checkpoint -> `.ply`

### 当前假设

- 只要把导出能力接到 refine 主入口, wrapper 自然就会跟着拿到最终 `.ply`。
- 如果再补一个明确的默认输出路径, 用户就不需要 refine 结束后再手工跑一条导出命令。

### 备选解释

- 如果实现时发现 `cfg.base_dir` 与 `cfg.result_dir` 并不总是同一目录, 就需要把 refined ckpt 路径与 `.ply` 输出路径拆开处理, 不能只靠字符串拼接猜位置。

## [2026-03-28 17:26:01] [Session ID: 019d33ba-5b20-7711-bf05-b3380d192c53] 笔记: wrapper 最终 `.ply` 输出的实现与验证证据

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`

- 要点:
  - 新增 `--final-ply-output`
  - 新增 `build_export_command()`
  - `run_pipeline()` 现在顺序执行:
    - `recon.import_fastgs`
    - `ours.refine_by_flux|sdxl`
    - `recon.export_3dgs_ply`
  - `main()` 结束后会同时打印:
    - `bridge_output`
    - `final_ply_output`

### 来源2: 路径推导策略

- 要点:
  - wrapper 只轻量解析 3 个键:
    - `base_dir`
    - `exp_name`
    - `gs_cfg_file`
  - 再读取 `<base_dir>/<gs_cfg_file>` 的 JSON `result_dir`
  - 最终 refined ckpt 路径:
    - `<result_dir>/ckpts/ckpt_<exp_name>.pt`
  - 最终默认 PLY 路径:
    - `<result_dir>/point_cloud_<exp_name>.ply`

### 来源3: 动态验证命令

- 语法检查:
  - `python3 -m py_compile ours/run_fastgs_refine.py tests/test_run_fastgs_refine.py`
- 单测:
  - `timeout 30s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_run_fastgs_refine`
- CLI 帮助页:
  - `timeout 10s python3 ours/run_fastgs_refine.py --help`
- dry run:
  - `python3 ours/run_fastgs_refine.py --ckpt-path /tmp/demo_fastgs.pth --colmap-path data/my4_fullcolmap --exp-cfg exp_cfg/my4/flux_shinkai_museum_v2.yaml --dry-run`

### 来源4: 关键输出

- 单测结果:
  - `Ran 9 tests in 1.812s`
  - `OK`
- dry run 输出了三条命令:
  - `recon.import_fastgs`
  - `ours.refine_by_flux`
  - `recon.export_3dgs_ply`
- dry run 还打印了:
  - `final_ply_output: /root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/point_cloud_flux_shinkai_museum_v2.ply`

## 综合发现

### 已验证结论

- 用户现在可以一条命令走完整链路:
  - FastGS 输入 -> FreeFix bridge ckpt -> refine -> 最终 3DGS `.ply`
- 最终导出路径不再靠硬编码猜 `base_dir`, 而是尊重底层 `cfg.json` 里的 `result_dir`
- `--dry-run` 不再依赖 `OmegaConf`, 因此即使在较轻的 `python3` 环境下也能直接看到完整命令链

### 边界

- 这次补的是 wrapper 的最终导出步骤
- 如果用户绕过 wrapper, 直接单独跑 `refine_by_flux.py / refine_by_sdxl.py`, 仍然不会自动导出 `.ply`

## [2026-03-29 10:52:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 随机相机偏移版 Flux refine 的现有插入点与主要风险

## 来源

### 来源1: `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`

- 要点:
  - 当前 refine 主循环对每个 `i` 先执行 `rgb, masks, alpha, depth, cam_param, _ = refiner.render(i)`。
  - 然后把 `rgb` 作为 `image=rgb_to_refine` 送入 `FluxPipeline`。
  - Flux 输出的 `refined_image` 会和同一轮的 `cam_param["c2w"] / cam_param["K"]` 组成 `refine_cams`。
  - 所以现有系统已经具备“渲染 -> 图生图 -> 回写监督”的闭环, 缺的不是框架能力, 而是新视角相机从哪里来、边界怎么控。

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/recon/refiner.py`

- 要点:
  - `Refiner.render(i)` 当前从 `test_dataset[idx]` 或 `train_dataset[idx]` 取原始 `camtoworld` 与 `K`。
  - 目前只支持一个全局的刚体偏移入口: `test_trans + test_rots`。
  - 这说明“相机偏移”概念并不是全无基础, 但现在是全局常量, 不是逐帧随机采样。
  - 生成后的 synthetic 样本会在 `refiner.refine(...)` 中和原始训练相机一起混合训练。

### 来源3: `/root/autodl-tmp/home/rais/FreeFix/recon/datasets/colmap.py`

- 要点:
  - 数据集返回的是严格绑定的一组 `image + K + camtoworld`。
  - 如果生成端改成随机新相机, 那就不再对应任何真实 `image_path/image_name`, 本质上已经不是“复用现成样本”, 而是在 parser 坐标系里新建 synthetic camera sample。

### 来源4: `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml`

- 要点:
  - 当前 refine 默认就暴露了 `test_split / test_trans / test_rots / strength / warp_ratio / gen_prob / gen_loss_weight`。
  - 这表明最自然的扩展位置仍在 refine config 层, 而不是再单独造一层完全平行的新脚本语义。

## 综合发现

### 现象

- 当前 FreeFix refine 已经不是“纯文本生图后再贴回去”, 而是明确的 img2img 闭环。
- 现有生成图 supervision 和使用它的相机参数是同一帧绑定的。
- 系统已经支持“相机统一偏移”, 但还不支持“每帧随机偏移”。

### 当前主假设

- 这条想法在工程上是可插入的。
- 最自然的做法不是替换掉现有 `refiner.render(i)` 主链, 而是新增一个 `sample_refine_camera(i)` 或 `sample_synthetic_refine_camera(base_cam)` 逻辑:
  - 先选一个 base camera
  - 在小范围位移 / 小角度旋转内采样新 `c2w`
  - 用该 `c2w + K` 渲染当前高斯
  - 再做 Flux img2img
  - 最后把生成图和这个新相机一起作为 synthetic refine cam 回写

### 最强备选解释

- 如果偏移太大, 这个链路就不再是“refine”, 而更像“让 2D 扩散模型替 3D 几何脑补未观测区域”。
- 这时它会把错误内容注入高斯, 尤其在遮挡关系、新暴露区域、薄结构和镜面区域更危险。

### 关键风险

- 风险1: 视角偏移一大, 生成图里的新显露区域没有真实多视图约束, 容易出现 hallucination 监督。
- 风险2: 如果继续沿用 `test_split=test`, 那这批 synthetic views 其实是围绕 benchmark 视角做训练增强, 会影响评测口径的纯净性。
- 风险3: 当前 `K` 默认复用原相机内参。如果平移/旋转扰动和视野变化耦合过强, 只动 `c2w` 不动 `K` 可能不够表达某些想要的相机扰动类型。

### 倾向结论

- 这条路线值得做, 但更适合定义成“受控的新视角 synthetic refine 分支”。
- 第一版应限制在“很小的 pose jitter + 原有可见区域附近”的 regime, 不要一上来做大幅 novel view。
- 如果要保持 benchmark 公平, 最好把它绑定到专门的 refine split 或 train-nearby cameras, 而不是直接围绕评测 test 视角采样。
