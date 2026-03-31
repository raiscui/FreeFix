## [2026-03-29 16:58:25] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] 笔记: fastdropgs checkpoint 与现有 bridge/refine 链路兼容性核对

## 来源

### 来源1: 现有 OpenSpec 与支线历史

- 文件:
  - `WORKLOG__fastgs_refine_probe.md`
  - `task_plan__fastgs_refine_probe.md`
- 要点:
  - 这台机器之前创建 `add-pose-jitter-refine` 时, 已确认没有 `openspec` CLI。
  - 仓库历史已经接受过一种 fallback: 在 CLI 缺失时, 依照既有 OpenSpec 目录约定手工创建 change。

### 来源2: `recon/import_fastgs.py`

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/recon/import_fastgs.py`
- 要点:
  - 当前导入器对 `.pth` 的识别条件只有文件后缀, `load_fastgs_source(...)` 在 `.pth` 时统一走 `extract_fastgs_checkpoint_splats(...)`。
  - `extract_fastgs_checkpoint_splats(...)` 只要求 payload 是 `(model_args, iteration)` 且 `model_args` 至少有 `7` 个槽位。
  - `infer_step_from_path(...)` 除了 `ckpt_(\d+)` 外, 还会回退到任意数字片段, 所以 `chkpnt50000.pth` 也能推断出 `50000`。

### 来源3: `ours/run_fastgs_refine.py`

- 文件:
  - `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`
- 要点:
  - wrapper 只是编排现有 bridge/refine/export 三段, 不额外限制 checkpoint 文件名必须是 `ckpt_*.pth`。
  - 默认 bridge 输出名直接使用 `source_path.stem`, 因此 `chkpnt50000.pth` 会生成 `chkpnt50000_freefix.pt`。

### 来源4: 动态检查 `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth`

- 验证命令:
  - `/root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python` 读取 checkpoint 并打印外层结构
- 关键输出:
  - `tuple_len 2`
  - `idx 0 type tuple`
  - `nested_len 14`
  - `idx 1 type int`
- 深一层结构:
  - `CAPTURE_LEN 14`
  - 槽位 `1..6` 分别仍是 `means / sh0 / shN / scales / quats / opacities` 对应形状
  - 两个优化器状态仍在 `11`、`12` 号槽位
- 对照样本:
  - `/home/rais/FastGS/output/my7_nomask_v1/checkpoints/ckpt_35000.pth`
- 结论:
  - 用户给的 `fastdropgs` 样本在最关键的 checkpoint 容器形态上, 与现有 FastGS `.pth` 是同型的。

### 来源5: 动态 smoke

- 验证命令1:
  - `timeout 30s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m recon.import_fastgs --ckpt-path /home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth --colmap-path /root/autodl-tmp/home/rais/FreeFix/data/my4_fullcolmap --no-normalize --output /tmp/fastdropgs_bridge_probe.pt`
- 关键输出1:
  - `source_format: fastgs_checkpoint`
  - `step: 50000`
  - `output: /tmp/fastdropgs_bridge_probe.pt`
  - `gaussian_count: 26993`
- 验证命令2:
  - `timeout 20s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python ours/run_fastgs_refine.py --ckpt-path /home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth --colmap-path /root/autodl-tmp/home/rais/FreeFix/data/my4_fullcolmap --exp-cfg /root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum_v2.yaml --dry-run`
- 关键输出2:
  - wrapper 成功打印 bridge、`ours.refine_by_flux`、`recon.export_3dgs_ply` 三条命令
  - 默认 bridge 输出路径是 `outputs/fastgs_bridge/chkpnt50000_freefix.pt`

## 综合发现

### 现象

- 用户希望把 `fastdropgs` 的 checkpoint 纳入当前“转换后继续 refine”的工作流。
- 机器上没有 `openspec` CLI。
- 用户给的 checkpoint 文件真实存在, 且已经能被当前 bridge 脚本成功转换。

### 当前假设

- 这次需求的真实缺口, 更可能不是“完全不支持这种 checkpoint 结构”。
- 更像是:
  - 现有能力还没有被正式命名为 `fastdropgs` 支持
  - 缺少针对 `chkpnt*.pth` 命名与该来源语义的测试
  - wrapper / 文档 / source_format 口径还停留在 `FastGS`

### 已验证结论

- `fastdropgs` 样本与现有 FastGS checkpoint 在核心容器结构上同型。
- 当前 `recon.import_fastgs` 已能把这份样本转成 FreeFix checkpoint。
- 当前 `ours/run_fastgs_refine.py` 已能把这份样本串进 refine 流程的 dry-run。
- 因此新 change 更适合定义为“把 `fastdropgs checkpoint` 支持正式化、显式化并补齐验证”, 而不是“从零新增一套 bridge 主链”。

## [2026-03-29 17:03:25] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] 笔记: `fast-dropgs` 的真实命名与当前 wrapper 默认输出仍有语义缝隙

## 来源

### 来源1: `/home/rais/fast-dropgs/train.py` 与 `/home/rais/fast-dropgs/scene/gaussian_model.py`

- 关键代码:
  - `torch.save((gaussians.capture(), iteration), scene.model_path + "/chkpnt" + str(iteration) + ".pth")`
  - `GaussianModel.capture()` 返回长度为 `14` 的 tuple
- 要点:
  - `fast-dropgs` 官方训练脚本默认保存的不是 `ckpt_50000.pth`, 而是 `chkpnt50000.pth`
  - 它的 `capture()` 结构和当前 bridge 已适配的 FastGS 结构同型
- 结论:
  - “需要支持 `fastdropgs`”这件事, 至少有一半是“正式接住它的命名和来源语义”, 不只是张量结构兼容

### 来源2: `/root/autodl-tmp/home/rais/FreeFix/ours/run_fastgs_refine.py`

- 关键代码:
  - `choose_bridge_label(source_path)` 对非 `point_cloud` 默认直接返回 `source_path.stem`
  - dry-run 输出:
    - `outputs/fastgs_bridge/chkpnt50000_freefix.pt`
- 要点:
  - 对 `fast-dropgs` 这类普遍使用 `chkpnt{iter}.pth` 的来源来说, 只用 stem 作为 bridge 输出名过于通用
  - 不同 run 的 `chkpnt50000.pth` 很容易撞到同一个默认输出路径
- 当前假设:
  - 这可能是本次实现里值得顺手改良的一点
  - 最稳的方向是:
    - 为 `chkpnt*.pth` 这类通用命名补更明确的来源标签
    - 或把父目录名一并纳入默认 bridge 输出 label

## 综合发现

### 现象

- `fast-dropgs` 自己明确使用 `chkpnt{iter}.pth` 命名
- 当前 bridge/wrapper 语义和帮助文本还完全站在 `FastGS` 命名口径上
- 当前 wrapper 的默认输出名对这类来源不够稳

### 已验证结论

- `fastdropgs` 不是“结构不同的新 checkpoint 容器”, 但它确实是“命名与来源语义不同的一支”
- 因此 proposal / design 应该同时覆盖:
  - 来源识别与 metadata
  - CLI/help/README 里的用户口径
  - 默认 bridge 输出路径的可辨识性

## [2026-03-29 17:21:02] [Session ID: 019d3a83-dc80-73d3-928e-1ab2422bc1bf] 笔记: `add-fastdropgs-checkpoint-bridge` 实现后验证结果

## 来源

### 来源1: 定向验证命令

- `python3 -m py_compile recon/import_fastgs.py ours/run_fastgs_refine.py tests/test_import_fastgs.py tests/test_run_fastgs_refine.py`
- `timeout 120s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m unittest tests.test_import_fastgs tests.test_run_fastgs_refine`
- `timeout 15s python3 ours/run_fastgs_refine.py --help`
- `timeout 30s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python ours/run_fastgs_refine.py --ckpt-path /home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth --colmap-path /home/rais/FastGS/data/my8_colmap_fastgs --exp-cfg /root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum_v2.yaml --dry-run`
- `timeout 30s /root/autodl-tmp/home/rais/FreeFix/.pixi/envs/default/bin/python -m recon.import_fastgs --ckpt-path /home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth --colmap-path /home/rais/FastGS/data/my8_colmap_fastgs --no-normalize --output /tmp/fastdropgs_bridge_probe_apply.pt`

### 关键输出

- `py_compile`: 通过
- `unittest`: `Ran 23 tests in 0.123s` / `OK`
- `--help`: 描述和参数帮助已明确写成 `FastGS / fast-dropgs`
- dry-run:
  - bridge 输出路径变为 `outputs/fastgs_bridge/my8_input_50k_from45k_resetopt_chkpnt50000_freefix.pt`
- 真实 bridge smoke:
  - `source_format: fastdropgs_checkpoint`
  - `step: 50000`
  - `gaussian_count: 26993`
- 导出后的 bridge 文件复查:
  - `source_format == fastdropgs_checkpoint`
  - `step == 50000`
  - `normalized_for_freefix == False`

## 综合发现

### 已验证结论

- `recon.import_fastgs.py` 现在已经能把 `fast-dropgs` 明确标记为 `fastdropgs_checkpoint`
- `infer_step_from_path(...)` 的显式 `chkpnt` 规则已经生效
- `ours/run_fastgs_refine.py` 现在会为通用的 `chkpnt*.pth` 自动补父目录名, 减少默认输出撞名
- 当前 OpenSpec `tasks.md` 里定义的实现范围已经完成

### 当前边界

- 这轮没有做真实 `my8` full refine
- 这不是实现遗漏, 而是刻意和本次 change 的范围区分开:
  - 当前 change 聚焦“正式支持 fast-dropgs bridge + refine 入口语义”
  - 真实 full refine smoke 仍依赖匹配的 `exp_cfg`

## [2026-03-29 18:26:58] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] 笔记: `my8` 真实 refine smoke 的现象、假设与验证入口

## 来源

### 来源1: 已完成的 `my6 / my7` 真实流程

- 文件:
  - `task_plan__colmap_my6.md`
  - `task_plan__colmap_my7.md`
  - `WORKLOG__colmap_my6.md`
  - `WORKLOG__colmap_my7.md`
- 要点:
  - 两条已跑通分支都采用同一条套路:
    - 先补 `exp_cfg/<scene>/recon_*.yaml`
    - 再补 `exp_cfg/<scene>/flux_*.yaml`
    - 再落 `outputs/<base_dir>/cfg.json` 与 `ckpts/`
    - 最后跑 `ours.run_fastgs_refine` 和 `ours.evaluation`
  - `my6 / my7` 都使用:
    - `test_every: 8`
    - `refine_start_idx: 0`
    - `refine_end_idx: 41`
    - `train_end_idx: 283`

### 来源2: `my8` 的上游输入事实

- 文件:
  - `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/cfg_args`
  - `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth`
  - `/home/rais/FastGS/data/my8_colmap_fastgs`
- 要点:
  - `cfg_args` 指向的 source path 是 `.../data/my8_colmap_fastgs`
  - 上游 run 名是 `my8_input_50k_from45k_resetopt`
  - `my8` COLMAP 目录同时存在 `images/` 与 `input/`, 需要确认当前 FreeFix 真实消费的是哪一路

### 来源3: 动态反证

- 验证命令:
  - `timeout 120s ... python - <<'PY' ... Dataset(..., test_every=8) ... PY`
- 关键输出:
  - `TypeError: Dataset.__init__() got an unexpected keyword argument 'test_every'`
- 结论:
  - 旧分支里用过的动态 split 探测脚本, 不能不加核对地直接复用到当前代码
  - 后续必须改成读取当前仓库版本真实支持的 parser / dataset 接口

## 综合发现

### 现象

- 用户已经明确选择继续做 `my8` 的真实 refine smoke。
- `my8` 的上游 checkpoint 和数据目录都真实存在。
- 旧版 split probe 命令在当前仓库上已经不成立。

### 当前假设

- `my8` 大概率仍然能沿用 `my6 / my7` 的 `test_every: 8` 和 `41 / 283` 切分。
- 但在拿到当前版本代码路径的动态证据前, 这还只是候选假设, 不能直接写死成结论。

### 最小验证计划

- 先读取当前 `recon.datasets.colmap` / `recon.refiner` 相关入口, 找到真实的 split 构造方式。
- 再用该入口对 `my8` 算出:
  - 总图片数
  - train/test 数
  - 索引范围
- 最后再决定 `my8` 的 refine 配置是否可以直接平移 `my6 / my7`。

## [2026-03-29 18:26:58] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] 笔记: `my8` 应使用 pruned 277 视角场景, 而不是 324 视角全量场景

## 来源

### 来源1: 当前仓库真实的 COLMAP split 入口

- 文件:
  - `recon/datasets/colmap.py`
  - `recon/refiner.py`
- 要点:
  - `test_every` 现在属于 `Parser(...)`, 不是 `Dataset(...)`
  - `Dataset` 默认按 `indices % parser.test_every` 做 train/test 互斥划分

### 来源2: `my8` 的两个候选场景目录

- 验证命令1:
  - `Parser(data_dir='/home/rais/FastGS/data/my8_colmap_fastgs', test_every=8)`
- 关键输出1:
  - `324 images`
  - `train = 283`
  - `test = 41`
- 验证命令2:
  - `Parser(data_dir='/home/rais/FastGS/data/my8_colmap_fastgs_input_pruned_v1', test_every=8)`
- 关键输出2:
  - `277 images`
  - `train = 242`
  - `test = 35`

### 来源3: 上游 `fast-dropgs` 真实训练输出

- 文件:
  - `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/cfg_args`
  - `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/cameras.json`
  - `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/test/ours_50000/gt`
  - `/home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/train/ours_50000/gt`
- 关键输出:
  - `cfg_args` 写明 `images='input'`
  - `cameras.json` 数量是 `277`
  - `test gt = 35`
  - `train gt = 242`

### 来源4: `/home/rais/FastGS/data/my8_colmap_fastgs` 的目录差异

- 验证命令:
  - 比较 `images/` 和 `input/` 文件名集合
- 关键输出:
  - `images = 324`
  - `input = 277`
  - `only_in_images = 47`
  - `only_in_input = 0`
- 结论:
  - `input/` 是 `images/` 的真子集
  - 因此 `324` 视角场景并不等于上游 `fast-dropgs` 训练时实际使用的那套输入

## 综合发现

### 现象

- 同名 `my8` 场景其实有两套不同视角规模:
  - 全量 `324`
  - pruned `277`
- 上游 `fast-dropgs` 的 run 名虽然挂在 `my8_colmap_fastgs` 之下, 但真实消费的是 `input` 子集

### 当前主假设

- `my8` 的真实 bridge + refine smoke 应该对齐 `277` 视角的 pruned 场景。

### 最强备选解释

- 也可能上游 checkpoint 虽然由 `input` 训练得到, 但当前 bridge/refine 仍可以安全迁移到 `324` 视角全量场景上做再优化。

### 什么证据会推翻当前主假设

- 如果用 pruned 场景做 dry-run 或真实 refine 时出现 checkpoint / parser / render 级别不匹配
- 而改用 `324` 视角场景反而完整通过

### 已验证结论

- 当前更稳的第一选择不是 `my8_colmap_fastgs`
- 而是和上游 `cameras.json`、`train/test gt` 数量完全一致的:
  - `/home/rais/FastGS/data/my8_colmap_fastgs_input_pruned_v1`

## [2026-03-29 18:46:27] [Session ID: 88b3baf5-24a9-4d93-9df7-579a2af4213b] 笔记: `my8` 真实 refine 与评估的最终验证结果

## 来源

### 来源1: 真实 refine 主链命令

- 验证命令:
  - `timeout 3600s ... python ours/run_fastgs_refine.py --ckpt-path /home/rais/fast-dropgs/output/my8_input_50k_from45k_resetopt/chkpnt50000.pth --colmap-path /home/rais/FastGS/data/my8_colmap_fastgs_input_pruned_v1 --exp-cfg exp_cfg/my8/flux_shinkai_museum_v2_fastdropgs_my8_input_50k_from45k_resetopt_fixsh_rerun.yaml --bridge-output data/fastgs_bridge/my8_input_50k_from45k_resetopt/chkpnt50000_freefix.pt`
- 关键输出:
  - bridge:
    - `source_format: fastdropgs_checkpoint`
    - `step: 50000`
    - `normalize_enabled: True`
    - `gaussian_count: 26993`
  - export:
    - refined ckpt 已保存
    - final ply 已保存
    - `property_count: 62`

### 来源2: 产物核对

- 关键输出:
  - bridge ckpt 存在
  - refined ckpt 存在
  - final ply 存在
  - `before_refine = 35`
  - `refine/render = 35`
  - `refine/gen = 35`
  - `refine/depth = 35`
  - `after_refine = 35`
  - `refine/masks = 105`

### 来源3: 评估命令与 JSON

- 验证命令:
  - `timeout 1800s ... python -m ours.evaluation --exp_cfg ...my8... --colmap-path /home/rais/FastGS/data/my8_colmap_fastgs_input_pruned_v1 --ckpt-path data/fastgs_bridge/my8_input_50k_from45k_resetopt/chkpnt50000_freefix.pt --eval_test`
- 最终落盘:
  - `50000_test.json`
  - `50000_train.json`
  - `flux_shinkai_museum_v2_fastdropgs_my8_input_50k_from45k_resetopt_fixsh_rerun_test.json`
  - `flux_shinkai_museum_v2_fastdropgs_my8_input_50k_from45k_resetopt_fixsh_rerun_train.json`

### 来源4: 评估阶段暴露并修复的 bug

- 现象:
  - refined eval 首次报错:
    - `ValueError: invalid literal for int() with base 10: '<exp_name>'`
  - 第二次仍报:
    - `checkpoint 未记录有效 step, 且当前 load_step 也不是可转成整数的值`
- 静态证据:
  - `ours.evaluation` 通过字符串型 `exp_name` 选择 refined ckpt 文件名
  - `recon.refiner.Refiner` 会调用 `resolve_strategy_resume_step(...)`
  - 当前 refined ckpt 缺少 `step` 字段, 不能只靠 `payload_step`
- 修复:
  - `recon/refine_runtime.py` 支持 `fallback_load_step`
  - `recon/refiner.py` 新增 `resume_load_step`
  - `ours/evaluation.py` 在 refined eval 时显式传 `base_load_step` 作为恢复步数提示
- 验证:
  - `python3 -m py_compile recon/refiner.py ours/evaluation.py recon/refine_runtime.py`
  - `python -m unittest tests.test_refine_runtime tests.test_evaluation_cli`
  - 修复后 `ours.evaluation` 退出码 `0`

## 综合发现

### 已验证结论

- `my8` 当前最稳的真实闭环是:
  - fast-dropgs checkpoint
  - `my8_colmap_fastgs_input_pruned_v1`
  - FreeFix bridge
  - Flux refine
  - PLY export
  - base/refined 双评估
- 这一闭环现在已经全部跑通
- 本轮 `my8` refined 相比 bridge base 不是微调级别的小波动, 而是明显正向提升:
  - test:
    - `PSNR +6.8273`
    - `SSIM +0.1341`
    - `LPIPS -0.1192`
  - train:
    - `PSNR +7.0234`
    - `SSIM +0.1347`
    - `LPIPS -0.1215`
