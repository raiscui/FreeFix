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
