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

## [2026-03-29 11:31:35] [Session ID: codex-add-pose-jitter-apply] 笔记: pose jitter helper 单测需要从 `refiner.py` 解耦

## 来源

### 来源1: 最小导入探测

- 命令:
  - `timeout 20s python3 -c "from recon.refiner import coerce_pose_jitter_triplet; ..."`
  - `timeout 20s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -c "from recon.refiner import coerce_pose_jitter_triplet; ..."`
- 关键输出:
  - 系统 `python3` 直接报 `ModuleNotFoundError: No module named 'torchmetrics'`
  - 项目 `.pixi` 环境里的导入没有立刻失败, 但在 20 秒窗口内一直没返回, 最终 `timeout` 退出码 `124`

### 来源2: `recon/refiner.py` 当前依赖结构

- 顶层 import 会立即拉起:
  - `torchmetrics`
  - `viser`
  - `gsplat`
  - `recon.trainer`
  - `bootstrap_pixi_cuda_env()`
- 这些依赖对真正 refine 运行是合理的, 但对 helper 级单测过重

## 综合发现

### 现象

- 直接从 `recon.refiner` 导入 pose jitter 纯函数, 无法作为“轻量单测入口”使用。

### 当前假设

- 最稳的做法是把纯 pose jitter helper 抽成轻模块。
- `refiner.py` 运行时继续复用这些 helper。
- 单测直接导入轻模块, 避免被整条渲染 / viewer / metrics 依赖链拖慢。

### 最强备选解释

- 也可能不是单个 import 太重, 而是 `recon.trainer` 或 `bootstrap_pixi_cuda_env()` 带来的级联初始化在拖慢启动。
- 但无论根因落在哪一层, 对单测来说结论一样:
  - 不应直接依赖 `recon.refiner` 顶层导入来测试这批纯函数。

### 当前决定

- 后续实现中优先把 pose jitter 纯 helper 抽到轻量模块, 再补单测。

## [2026-03-29 11:44:06] [Session ID: codex-add-pose-jitter-apply] 笔记: pose jitter 真实 Flux smoke 已尝试, 但本轮未完成初始化

## 来源

### 来源1: 轻量动态验证

- 命令:
  - `python3 -m py_compile recon/pose_jitter.py recon/refiner.py ours/refine_by_flux.py ours/refine_by_sdxl.py tests/test_pose_jitter_refine.py tests/test_refine_cli_paths.py`
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_pose_jitter_refine tests.test_refine_cli_paths`
  - `timeout 10s python3 ours/refine_by_flux.py --help`
  - `timeout 10s python3 ours/refine_by_sdxl.py --help`
- 关键输出:
  - `py_compile` 通过
  - `Ran 12 tests in 1.306s`
  - `OK`
  - 两个 `--help` 都能在 10 秒内返回

### 来源2: 真实 smoke 尝试

- 第一次命令:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 ours/refine_by_flux.py --exp_cfg /tmp/pose_jitter_smoke.yaml`
- 关键输出:
  - `ModuleNotFoundError: No module named 'ours'`
- 解释:
  - 这是入口形式问题, 不是 pose jitter 本身出错
  - 该脚本需要按 README 里的模块方式调用:
    - `python3 -m ours.refine_by_flux ...`

### 来源3: 模块方式 smoke

- 第二次命令:
  - `timeout 300s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke.yaml`
- 观测事实:
  - 进程已启动并持续存活一段时间
  - 外部 `ps` 能看到模块进程
  - 但在观察窗口内:
    - 没有 stdout/stderr 新输出
    - 没有创建 `outputs/my5_colmap_fastgs_stable_35k_dense/pose_jitter_smoke_20260329/`
    - 也没有 `refine/pose_jitter_log.jsonl`
  - 为避免无意义长等, 已主动终止该进程

## 综合发现

### 现象

- pose jitter 的代码改动已经通过轻量验证。
- 真实 Flux smoke 这轮只推进到了初始化阶段, 没进入 refine 主循环。

### 当前假设

- 真实 smoke 的阻塞更像是大模型 / 数据 / 渲染栈的冷启动耗时问题。
- 目前没有证据表明 pose jitter 逻辑本身在真实 run 中已经失败。

### 最强备选解释

- 也不能排除还有更深的初始化阻塞, 只是当前没有新的 stdout/stderr 证据。
- 在没有 trace 或更细粒度 profiling 之前, 不能把“长时间无输出”直接定性成 bug。

### 当前结论

- 本轮可以确认:
  - 配置、调用链、fallback、日志写法和 helper 行为已经被动态测试覆盖
- 本轮不能确认:
  - 真实 Flux pose jitter smoke 已完整跑通
- 因此 OpenSpec `4.2` 应暂时保持未勾选

## [2026-03-29 12:17:05] [Session ID: codex-add-pose-jitter-smoke] 笔记: 真实 Flux pose jitter smoke 已定位到 `pipe.to(cuda)` 阶段超时

## 来源

### 来源1: 分段冷启动探针

- 命令:
  - 用 `.pixi` Python 分段导入 `ours.refine_by_flux`、`torch`、`torchvision`、`FluxPipeline`、`Refiner`
- 关键输出:
  - `import ours.refine_by_flux`: 约 `0.002s`
  - `load merged omega config`: 约 `0.492s`
  - `import imageio`: 约 `3.689s`
  - `import torch`: 约 `45.198s`
  - `import torchvision.utils.save_image`: 约 `63.094s`
  - `import FluxPipeline`: 约 `94.912s`
  - `import Refiner + Config`: 约 `100.705s`

### 来源2: 第一轮真实 smoke 加粗阶段日志

- 命令:
  - `timeout 420s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke.yaml`
- 关键输出:
  - `[refine_by_flux] 运行时依赖加载完成`
  - `[refine_by_flux] 开始初始化 Refiner`
  - `[Parser] 324 images, taken by 1 cameras.`
  - `[refine_by_flux] Refiner 初始化完成`
  - `[refine_by_flux] 开始加载 Flux pipeline: ...`
  - 后续看到 pipeline component / checkpoint shard 进度
  - 但在 `420s` 内没有看到:
    - `Flux pipeline 加载完成`
    - `开始创建输出目录`

### 来源3: 第二轮更细阶段日志

- 新增日志边界:
  - `FluxPipeline.from_pretrained 返回`
  - `开始执行 pipe.to(cuda)`
  - `pipe.to(cuda) 返回`
  - `开始替换 scheduler`
- 关键输出:
  - `FluxPipeline.from_pretrained 返回`
  - `开始执行 pipe.to(cuda)`
  - 然后直到 `timeout 420s` 退出
- 同轮现场证据:
  - 没有创建 `outputs/my5_colmap_fastgs_stable_35k_dense/pose_jitter_smoke_20260329/`
  - 没有 `pose_jitter_log.jsonl`
  - `nvidia-smi` 可见该进程占用约 `3650 MiB` 显存

## 综合发现

### 现象

- 真实 pose jitter smoke 不是卡在 CLI、配置合并、`Refiner` 初始化, 也不是卡在 `FluxPipeline.from_pretrained` 本体。
- 当前观测到的最窄阻塞边界是:
  - `pipe.to("cuda")`

### 当前假设

- 在这台机器和这组模型上, `pipe.to("cuda")` 的冷启动耗时本身已经足够长, 会把一个 `420s` 的最小 smoke 窗口吃完。

### 最强备选解释

- 也可能不是单纯“慢”, 而是 `pipe.to("cuda")` 内部某个子模块初始化 / 权重搬运阶段存在更细粒度阻塞。
- 但在当前证据下, 还不能把它直接定性成 bug。

### 当前结论

- OpenSpec `4.2` 这轮仍不能勾选。
- 现在可以非常明确地说:
  - 如果下一轮还要继续跑真实 smoke, 应优先围绕 `pipe.to("cuda")` 继续取证或放宽时间窗口
  - 当前 pose jitter 主链本身尚未拿到“真实首帧跑通”的动态证据
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

## [2026-03-29 12:40:28] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 用可选 offload 模式绕过 `pipe.to(cuda)` 阻塞, 完成 pose jitter 真实 smoke

## 来源

### 来源1: 本地 pipeline 与 diffusers 运行时语义复核

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/flux_pipeline.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/pipelines/sdxl_pipeline.py`
  - 已装包 `diffusers.DiffusionPipeline`
- 要点:
  - `FluxPipeline` 与 `StableDiffusionXLImg2ImgPipeline` 在真正推理时都使用 `self._execution_device`
  - 当前环境里的 `DiffusionPipeline` 也确实提供:
    - `enable_model_cpu_offload(self, gpu_id=None, device=None)`
    - `enable_sequential_cpu_offload(self, gpu_id=None, device=None)`
  - 这说明 offload 模式下不能再把 `pipe.device` 当成“实际执行设备”

### 来源2: 本轮实现

- 新增:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_pipeline_runtime.py`
- 修改:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_flux.py`
  - `/root/autodl-tmp/home/rais/FreeFix/ours/refine_by_sdxl.py`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/base.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/tests/test_refine_pipeline_runtime.py`
- 要点:
  - 新增 `refine_pipeline_offload_mode: none | model_cpu | sequential_cpu`
  - 默认 `none`, 保持旧行为
  - `model_cpu / sequential_cpu` 路径不再执行 `pipe.to(cuda)`
  - refine 输入张量改成跟随 `resolve_pipeline_execution_device(pipe)` 走

### 来源3: 轻量验证

- 语法检查:
  - `python3 -m py_compile ours/refine_pipeline_runtime.py ours/refine_by_flux.py ours/refine_by_sdxl.py tests/test_refine_pipeline_runtime.py tests/test_refine_cli_paths.py tests/test_pose_jitter_refine.py`
- 单测:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_refine_pipeline_runtime tests.test_refine_cli_paths tests.test_pose_jitter_refine`
- 关键输出:
  - `Ran 19 tests in 0.030s`
  - `OK`

### 来源4: 真实 smoke

- 临时配置:
  - `/tmp/pose_jitter_smoke_model_cpu.yaml`
- 命令:
  - `timeout 600s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/pose_jitter_smoke_model_cpu.yaml`
- 关键阶段输出:
  - `FluxPipeline.from_pretrained 返回`
  - `开始启用 enable_model_cpu_offload(device=cuda)`
  - `enable_model_cpu_offload 返回`
  - `pipeline execution device: cuda:0`
  - `开始创建输出目录: outputs/my5_colmap_fastgs_stable_35k_dense/pose_jitter_smoke_20260329_model_cpu`
  - `Pose jitter log: .../refine/pose_jitter_log.jsonl`
- 退出结果:
  - 进程退出码 `0`
- 落盘产物:
  - `before_refine/000.jpg`
  - `after_refine/000.jpg`
  - `refine/render/000.jpg`
  - `refine/gen/image_000.jpg`
  - `refine/pose_jitter_log.jsonl`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_pose_jitter_smoke_20260329_model_cpu.pt`

### 来源5: pose jitter 日志样本

- `pose_jitter_log.jsonl` 首条记录表明:
  - `attempt_count: 1`
  - `accepted_attempt_index: 1`
  - `used_fallback: false`
  - `alpha_coverage: 1.0`
  - 本轮 sample 围绕 `train` split 的 `source_index: 0`

## 综合发现

### 现象

- 默认整模 `pipe.to(cuda)` 路径在上一轮 `420s` 窗口里始终无法越过
- 改成 `model_cpu` offload 后, 同一条 Flux pose jitter refine 链路成功完成了 1 帧真实 smoke

### 已验证结论

- 当前能被证据支撑的结论是:
  - 本机的真实阻塞边界不在 pose jitter 主链本身
  - 而在默认 pipeline 放置路径
  - `refine_pipeline_offload_mode: model_cpu` 是一条可工作的绕行路径
- 这条路径已经足以支撑 OpenSpec `4.2` 收尾

### 仍然保留的边界

- 本轮 smoke 规模仍然很小, 只覆盖了 1 帧
- 它证明“链路能跑通且没有立刻出现明显遮挡越界”, 但不等于已经完成更大规模的视觉质量评测

## [2026-03-29 14:00:17] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: `my5` 上真实验证 `pose_jitter + train` 模式的数据流

## 来源

### 来源1: 临时 smoke 配置

- 文件:
  - `/tmp/my5_pose_jitter_train_smoke_20260329.yaml`
- 要点:
  - `base_dir: outputs/my5_colmap_fastgs_stable_35k_dense`
  - `refine_camera_mode: pose_jitter`
  - `refine_camera_source_split: train`
  - `refine_pipeline_offload_mode: model_cpu`
  - 小规模范围:
    - `refine_start_idx: 0`
    - `refine_end_idx: 3`

### 来源2: 真实运行命令

- 命令:
  - `timeout 900s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python3 -m ours.refine_by_flux --exp_cfg /tmp/my5_pose_jitter_train_smoke_20260329.yaml`
- 关键输出:
  - `Pose jitter log: outputs/my5_colmap_fastgs_stable_35k_dense/my5_pose_jitter_train_smoke_20260329/refine/pose_jitter_log.jsonl`
- 退出码:
  - `0`

### 来源3: 输出目录

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/my5_pose_jitter_train_smoke_20260329`
- 已落盘:
  - `before_refine/000.jpg~002.jpg`
  - `refine/render/000.jpg~002.jpg`
  - `refine/gen/image_000.jpg~002.jpg`
  - `after_refine/000.jpg~002.jpg`
  - `refine/pose_jitter_log.jsonl`
  - `outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_my5_pose_jitter_train_smoke_20260329.pt`

### 来源4: pose jitter 日志内容

- 首 3 条记录都明确写出:
  - `source_split: "train"`
  - `source_index: 0 / 1 / 2`
  - `used_fallback: false`
  - `accepted_attempt_index: 1`
- 对应 `source_image_name`:
  - `001_0_generated_videos_generated_video_0_000002.jpg`
  - `001_0_generated_videos_generated_video_0_000003.jpg`
  - `001_0_generated_videos_generated_video_0_000004.jpg`

## 综合发现

### 现象

- `my5` 上这条链路已经真实跑完
- 中间 `refine/render/*.jpg` 和 `refine/gen/image_*.jpg` 都成功写出
- `pose_jitter_log.jsonl` 清楚记录了它是围绕训练集镜头在做局部抖动

### 已验证结论

- 当前实现的真实语义就是:
  - 先取训练集已有镜头作为 base camera
  - 对这个镜头做小幅 pose jitter
  - 用 jitter 后的相机去 render 当前 GS
  - 再把 render 图送进 Flux 做 img2img
  - 最终生成图和 jitter 后的相机参数一起作为 `Gen` 样本送进 refine

### 口径修正

- 上一轮出现的 `FileNotFoundError` 这次没有复现
- 结合用户说明“刚才误删除了”, 当前更合理的口径是:
  - 上次失败不能再当作稳定代码 bug
  - 本轮无干扰重跑才是有效证据

## [2026-03-29 14:28:56] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: `my5` pose jitter smoke 中大面积黑图的来源定位

## 来源

### 来源1: `my5_pose_jitter_train_smoke_20260329` 输出统计

- 路径:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/my5_pose_jitter_train_smoke_20260329`
- 亮度统计结果:
  - `before_refine/001.jpg`
    - `mean ≈ 0.5025`
  - `refine/render/001.jpg`
    - `mean ≈ 0.0487`
  - `refine/gen/image_001.jpg`
    - `mean ≈ 0.0505`
  - `after_refine/001.jpg`
    - `mean ≈ 0.0418`
  - `refine/render/002.jpg`
    - `mean ≈ 0.0420`
  - `refine/gen/image_002.jpg`
    - `mean ≈ 0.0441`

### 来源2: 对应训练源图统计

- 源图路径:
  - `/home/rais/FastGS/data/my5_colmap_fastgs/images/001_0_generated_videos_generated_video_0_000002.jpg`
  - `/home/rais/FastGS/data/my5_colmap_fastgs/images/001_0_generated_videos_generated_video_0_000003.jpg`
  - `/home/rais/FastGS/data/my5_colmap_fastgs/images/001_0_generated_videos_generated_video_0_000004.jpg`
- 亮度统计:
  - 三张源图灰度均值都约 `0.50`
  - `<0.10` 像素占比都接近 `0`

### 来源3: pose jitter 日志

- `pose_jitter_log.jsonl`:
  - frame 1:
    - `source_split: train`
    - `source_index: 1`
    - `alpha_coverage: 0.9207`
  - frame 2:
    - `source_split: train`
    - `source_index: 2`
    - `alpha_coverage: 0.8289`
- 这说明:
  - 不是 fallback 到别的相机
  - 也不是“几乎什么都没看到”的空视角

### 来源4: certainty mask 统计

- `refine/masks/{0.001,0.01,0.1}/001.jpg` 与 `002.jpg`
  - 平均亮度约 `0.0079`
  - 接近全黑
- 对比 `000.jpg`:
  - mask 明显更亮

## 综合发现

### 现象

- 发黑不是从原始训练图开始的
- 发黑在 `refine/render` 阶段就已经出现
- `gen` 基本只是延续这个暗输入

### 当前假设

- 当前最强假设是:
  - jitter 后的相机虽然仍然看到了大量几何(`alpha_coverage` 高)
  - 但当前 GS 对这些局部新视角的颜色 / 外观重建非常差
  - 所以 novel-view render 本身已经塌成大面积暗图
- certainty mask 几乎全黑也支持这个方向:
  - 当前系统把这几帧视为低确定性区域

### 备选解释

- 也可能和相机局部旋转方向有关:
  - frame 1 / 2 的抖动把视线带向了室内更暗的表面或边界
  - 但这仍然属于“render 端已经先黑了”, 不是 Flux 单独造成的

### 已验证结论

- 当前能被证据支撑的结论是:
  - 大面积黑色的起点在 `refine/render`
  - 不是训练源图本来就黑
  - 也不是 Flux 把一张正常 render 单独压成黑图

## [2026-03-29 14:47:15] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 黑帧真正由 refine 第一步触发, 直接入口是 `DefaultStrategy` 在 `step=0` 重置 opacity

## 来源

### 来源1: 用日志里的同一组 jitter 参数离线重渲染

- 对 `frame 1 / 2` 使用 `pose_jitter_log.jsonl` 里的真实 `pose_jitter_trans` 和 `pose_jitter_rots`
- 枚举:
  - `base_c2w @ T`
  - `T @ base_c2w`
  - `base_c2w @ inv(T)`
  - `inv(T) @ base_c2w`
- 结果:
  - 所有组合的 render 亮度都在 `0.49 ~ 0.50`
  - 没有任何一种会直接渲染成黑图

### 来源2: 动态复现实验

- 先在初始 checkpoint 上渲染 `frame1` 的同一 jitter 相机:
  - `mean ≈ 0.5034`
- 然后只执行 `frame0` 对应的 4 个 refine step
- 再次渲染同一 `frame1` jitter 相机:
  - `mean ≈ 0.0485`
- 同时固定训练相机 `train[1]` 也一起掉到:
  - `mean ≈ 0.0487`

### 来源3: 剥离实验

- `max_steps=1` 且只跑一个真实 train step, 不进入 Gen 分支:
  - 亮度仍从 `0.5034` 掉到 `0.0393`
- 用自渲染图替代 Flux 图:
  - 仍然掉黑
- 关闭 `use_affine`:
  - 仍然掉黑
- 这说明:
  - 不是 Flux 图内容触发
  - 不是 affine 分支触发
  - 而是 refine 第一步本身就在破坏 GS

### 来源4: `DefaultStrategy` 对照实验

- 保持其它条件不变:
  - `strategy_enabled`
    - 亮度: `0.5034 -> 0.0393`
    - opacity 均值: `0.3388 -> 0.0081`
    - opacity 最大值: `1.0 -> 0.01`
  - `strategy_disabled`
    - 亮度: `0.5034 -> 0.5047`
    - opacity 基本不变
- 直接读取 `gsplat.strategy.DefaultStrategy.step_post_backward`:
  - 当 `step % reset_every == 0` 时会调用 `reset_opa(...)`
- 当前 `Refiner.refine()` 从 `step = 0` 开始计数
  - 因此成熟 checkpoint 在 refine 第一步就命中了 opacity reset

## 综合发现

### 现象

- 黑帧不是 `pose_jitter` 相机采样立刻造成的
- 它发生在第一个 refine step 之后
- 一旦第一步发生 opacity reset, 后续无论 jitter 相机还是固定训练相机都会一起发黑

### 上一主假设的回滚

- 上一条“pose jitter 变换方向可能错了”的主假设, 现在不成立
- 推翻它的证据是:
  - 同一组 jitter 参数离线重渲染并不黑
  - 真正触发发黑的是 refine 更新之后的 GS 状态

### 当前主假设

- 当前最强主假设是:
  - `Refiner` 加载的是成熟 checkpoint
  - 但 `DefaultStrategy` 的步数被从 `0` 重新开始
  - 导致 `step=0` 直接命中 `reset_every`, 把成熟 opacity 错误重置到 `0.01`

### 最强备选解释

- 备选解释是:
  - 除了 `reset_opa` 之外, 还有别的 strategy 状态初始化和成熟 checkpoint 不兼容
- 但当前最小对照里, 只要把 strategy callback 静音, 黑化立即消失
- 因此当前已经足够支撑“先修 strategy 步数语义”这一步

### 已验证结论

- 当前黑图的直接触发点已经能明确写成:
  - `DefaultStrategy.step_post_backward()` 在 `step=0` 执行了 `reset_opa`
  - 这不是 `pose_jitter` 独有问题
  - 而是 refine 从成熟 checkpoint 恢复时没有延续原训练时间轴

## [2026-03-29 14:58:52] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: `my5` 正式 100 镜头 jitter refine 已启动并进入主循环

## 来源

### 来源1: 正式运行配置

- 配置文件:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_100_20260329.yaml`
- 关键口径:
  - `refine_end_idx: 100`
  - `test_split: train`
  - `refine_camera_mode: pose_jitter`
  - `refine_camera_source_split: train`
  - `refine_pipeline_offload_mode: model_cpu`
  - `load_ckpt_path: outputs/my5_colmap_fastgs_stable_35k_dense/ckpts/ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt`

### 来源2: 首次启动失败后的修正

- 首次后台启动时碰到:
  - `FileNotFoundError: .../ckpts/ckpt_34999.pt`
- 复核工作区后确认:
  - 当前真实存在的是:
    - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000.pt`
    - `ckpt_flux_shinkai_museum_v2_fastgs_my5_nomask_v1_35000_fixsh_rerun.pt`
- 因此正式配置改成显式 `load_ckpt_path`, 不再依赖缺失的默认命名

### 来源3: 当前后台任务状态

- 进程:
  - `PID 326050`
- 日志:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_100_20260329.run.log`
- 已确认日志阶段:
  - `Refiner 初始化完成`
  - `FluxPipeline.from_pretrained 返回`
  - `enable_model_cpu_offload 返回`
  - `开始创建输出目录`
  - `Pose jitter log: .../refine/pose_jitter_log.jsonl`
  - 进度条已进入:
    - `0/32`

## 综合发现

### 现象

- 当前正式任务已经不是“只完成配置”
- 它已经真实进入 Flux 主循环
- 输出目录和 refine 子目录都已创建完成

### 当前结论

- 截至 `2026-03-29 14:58:52 UTC`
  - 正式 `my5` 100 镜头 jitter refine 正在后台运行
  - 当前没有新的启动期错误
  - 后续只需要继续观察运行进度和最终产物

## [2026-03-29 15:07:04] [Session ID: 019d3934-ae28-7011-acaa-2f5fa77d5f39] 笔记: 当前正式 jitter 太保守, 已切到更强 3x 配置重启

## 来源

### 来源1: 用户反馈与当前运行日志

- 用户明确反馈:
  - “抖动太小了, 我看图质量都很高”
- 对应运行目录:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_100_20260329`
- 对应 `pose_jitter_log.jsonl` 前几条:
  - 平移大多在 `0.003 ~ 0.019m`
  - 旋转基本在 `2 度` 内

### 来源2: 更强版本正式配置

- 新配置:
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my5/flux_shinkai_museum_v2_35k_pose_jitter_train_100_stronger_20260329.yaml`
- 关键变化:
  - `pose_jitter_trans_sigma: [0.03, 0.03, 0.03]`
  - `pose_jitter_trans_max: [0.06, 0.06, 0.06]`
  - `pose_jitter_rot_sigma_deg: [3.0, 3.0, 3.0]`
  - `pose_jitter_rot_max_deg: [6.0, 6.0, 6.0]`

### 来源3: 重启后的后台任务状态

- 旧任务:
  - 已发送 `SIGTERM` 停止
- 新任务:
  - `PID 331670`
- 日志:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my5_colmap_fastgs_stable_35k_dense/flux_shinkai_museum_v2_pose_jitter_train_100_stronger_20260329.run.log`
- 新 `pose_jitter_log.jsonl` 第 1 条:
  - `pose_jitter_trans = [-0.0434, -0.0336, 0.0120]`
  - `pose_jitter_rots = [1.026, 2.578, -0.513]`

## 综合发现

### 现象

- 更强版本的第一条采样已经明显大于上一轮
- 当前不是“看起来配大了”
- 而是动态日志里已经真实采到了 `4cm` 量级平移

### 当前结论

- 截至 `2026-03-29 15:07:04 UTC`
  - 更强 3x jitter 正式任务已经启动并在后台运行
  - 第一条实际采样已明显变大
  - 这轮更符合“不要太贴近原镜头”的目标
