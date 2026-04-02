# 项目经验沉淀

## refine / Flux / ModelScope

- `ours.refine_by_flux` 与 `ours.refine_by_sdxl` 这条 refine 链路, 现在已经形成可恢复闭环。关键真相源是:
  - `refine_resume_state.json`
  - rolling resume checkpoint
  - `refine/generated_cams.jsonl`
  - `before_refine/` 与 `after_refine/` 的 jpg 序列
- fixed-view 导出提速时, 优先走 `render_fixed_rgb_batch(...)` 这一层的 batch rasterize, 不要把“多个视角一起生成”直接理解成 Python 线程并发。
- synthetic 主循环里, 单条 plan 的 `render -> Flux gen -> refiner.refine` 是严格前后依赖关系。
  - `Flux gen` 依赖当前 `render` 输出。
  - 下一条 plan 的 render 又依赖上一条 `refiner.refine(...)` 之后的新高斯状态。
  - 所以默认语义下, 不应直接把多条 jitter plan 并发起来跑。
- `black-forest-labs/FLUX.1-dev` 从 Hugging Face 直接取 `model_index.json` 时, 当前会命中 `GatedRepo`。
  - 现象上会表现成 rerun 在冷启动后提前退出。
  - 这时优先切到 ModelScope 官方 CLI/SDK 路线, 不要继续围绕 HF 失效地址硬补。
- 当前仓库一旦配置了失效的 `flux_model_path`, rerun 不会“慢慢等到成功”, 而是会在 `resolve_flux_model_source(cfg)` 处直接失败退出。
- 本机相关命令若继承到 `OMP_NUM_THREADS=0`, 容易出现 `libgomp: Invalid value for environment variable OMP_NUM_THREADS`。
  - 这类下载、单测、推理命令统一显式带 `OMP_NUM_THREADS=1` 更稳。
- 需要导出某个 refine 实验的 3DGS `ply` 时, 优先走项目现有链路:
  - 输入 checkpoint 选正式落盘的 `outputs/<base_dir>/ckpts/ckpt_<exp_name>.pt`
  - 导出入口用 `python -m recon.export_3dgs_ply --ckpt ... --output ...`
  - 不要先拿 `__resume_latest` 或中途恢复点做交付导出
- 当前代码里虽然预留了 `ip_adapter_image` 一类图像条件入口, 但本地 `FLUX.1-dev` 资产默认并没有 `image_encoder` / `feature_extractor`。
  - 这意味着“接口看起来能接双图”不等于“当前项目已经支持 reference-guided refine”
- 评估 `Kontext` 接入时, 要把它当成“新增可选 backend”而不是“现有 `flux/sdxl` 私有扩展的语义等价替代品”。
  - 现有 refine 依赖的 `mask_scheduler`、`warp_image`、`warp_mask` 等语义, 不能直接假设官方 Kontext pipeline 天然具备

## checkpoint / trajectory / dataset 契约

- refined checkpoint 的“文件名标签”和“恢复步数”必须显式解耦。
  - `exp_name` 这种字符串只适合定位文件
  - strategy resume / evaluation 需要的是数值型基础训练步数
  - 如果把两者混成一个参数, 很容易在 refined eval 或 resume 路径上把字符串误当整数解析
- `to_refine/refine_c2ws.npy` 不能直接当成 `after_refine.mp4` 的真实相机轨迹。
  - 前者更像 driving / render 轨迹
  - 后者如果要给 Unity 或别的下游消费, 应优先使用显式导出的 sidecar 轨迹 JSON
- 没有 `partition.json` 时, fallback split 也必须保持 train/test 互斥。
  - 不能让 `test_every` 只影响 test 抽样, 却让 train 继续吃全量数据
- 调试仓库脚本时, 一旦看到 `plyfile`、`imageio` 这类“明明项目里应该有”的缺包, 先怀疑是不是误用了系统 `python3`。
  - 这类验证应优先使用 `.pixi/envs/default/bin/python` 或 `direnv exec . pixi run ...`

## 上下文治理

- 判断一个 `__suffix` 支线是不是还活跃, 不能只看 `task_plan` 里有没有未勾选阶段。
  - 还要交叉核对同后缀 `WORKLOG` / `notes` 是否已经给出了完整交付, 以及最新时间戳是不是当天
  - `__fastgs_colmap_compare` 就出现过“task_plan 第4阶段未勾选, 但 worklog 已写完总结”的收尾漏勾情况
