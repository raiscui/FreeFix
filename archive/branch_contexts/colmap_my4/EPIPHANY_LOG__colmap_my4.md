## [2026-03-27 00:48:18] [Session ID: 78200] 主题: pixi 的 CUDA toolkit 不能默认等同于环境根目录

### 发现来源
- 在排查 `my4` 训练时 `gsplat` CUDA 扩展加载失败的过程中发现
- 先后通过:
  - `cuda_runtime_api.h` 缺失日志
  - `cicc: not found` 日志
  - 最终 JIT 成功验证
  把路径关系逐层钉实

### 核心问题
- 这个项目当前的 pixi CUDA 布局不是很多人直觉里的:
  - `.pixi/envs/default/bin`
  - `.pixi/envs/default/include`
  - `.pixi/envs/default/lib`
- 真正有效的路径被拆成了:
  - toolkit 根: `.pixi/envs/default/targets/x86_64-linux`
  - NVVM 编译器: `.pixi/envs/default/nvvm/bin`

### 为什么重要
- 只要某个包使用 `torch.utils.cpp_extension`、`setup.py`、自定义 `nvcc` JIT, 就可能再次踩中这件事
- 这不是 `gsplat` 特例, 而是当前环境组织方式带来的系统性风险

### 未来风险
- 如果后续再接 `pytorch3d`、自定义 CUDA op、别的 3DGS 扩展, 很容易再次出现:
  - “No CUDA toolkit found”
  - `cuda_runtime_api.h` 缺失
  - `cicc: not found`
- 如果只修表层 warning, 不核对真实 toolkit 根, 就会陷入反复试错

### 当前结论
- 当前已知事实:
  - `CUDA_HOME` 应指向 `.pixi/envs/default/targets/x86_64-linux`
  - `PATH` 应包含 `.pixi/envs/default/nvvm/bin`
  - 入口脚本内部自动引导和 `.envrc` 都已经同步修正
- 仍未确认的部分:
  - 未来如果 pixi 改变目录布局, 这套探测逻辑是否还需要继续扩展

### 后续讨论入口
- 下次再遇到任何本地 CUDA 扩展编译失败, 先看:
  - [runtime_env.py](/root/autodl-tmp/home/rais/FreeFix/recon/runtime_env.py)
  - [.envrc](/root/autodl-tmp/home/rais/FreeFix/.envrc)
  - `/tmp/gsplat_jit_fixed.log`

## [2026-03-27 01:27:18] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 主题: 共享渲染路径依赖“不同 Dataset 返回统一样本字段”这个隐含契约

### 发现来源
- 在从 `ckpt_29999.pt` 导出轨迹视频时发现
- `render_traj` 对 `colmap.Dataset` 取样后直接读取:
  - `image_path`
  - `image_name`
  - `image_size`

### 核心问题
- 这个契约之前没有被明确写出来
- `hugsim` / `seva` 已经返回这些字段, 但 `colmap` 没有
- 结果是共享上层逻辑表面上“支持多数据集”, 实际上会因为某一个数据集样本字段偏少而在运行时炸掉

### 为什么重要
- 这不是“只影响一次导视频”的小问题
- 只要后面还有别的共享路径复用 Dataset 样本字典, 就可能再次踩中同类错误

### 未来风险
- 如果以后又新增一个 Dataset 类型, 但没有对齐这套样本字段, 上层渲染/评估/导出逻辑仍可能晚一点才爆
- 这种问题静态上不显眼, 但一旦触发就会直接在长流程中断掉

### 当前结论
- 当前已知事实:
  - `colmap.Dataset` 已补齐缺失字段
  - 已新增最小单测锁住这层契约
- 仍未确认的部分:
  - 代码库里是否还有别的共享路径依赖更多“未文档化字段”

### 后续讨论入口
- 下次如果继续整理数据集抽象层, 建议先看:
  - [colmap.py](/home/rais/FreeFix/recon/datasets/colmap.py)
  - [hugsim.py](/home/rais/FreeFix/recon/datasets/hugsim.py)
  - [test_colmap_dataset_contract.py](/home/rais/FreeFix/tests/test_colmap_dataset_contract.py)

## [2026-03-27 03:20:26] [Session ID: 20260327T032026Z-main] 主题: 多模型 COLMAP 输出里, `sparse/0` 不是“最佳模型”的同义词

### 发现来源
- 在修复 `data/my4_fullcolmap` 的 full COLMAP 后处理时发现
- `mapper` 已成功产出:
  - `distorted/sparse/0`
  - `distorted/sparse/1`
- 但只有对每个模型做真实计数后, 才看到:
  - `0`: `2` 图 / `296` 点
  - `1`: `264` 图 / `27521` 点

### 核心问题
- 很多脚本会直接把 `distorted/sparse/0` 当成默认输入
- 这其实把“目录编号”误当成了“质量排序”
- 一旦 `mapper` 输出多个模型, 这种假设就会把后处理稳定带到错误分支

### 为什么重要
- 这不是 `my4` 特例
- 任何存在弱连通分量、坏图剔除、或者多初始种子扩张的 COLMAP 重建, 都可能输出多个 model
- 如果后处理脚本继续固定拿 `0`, 就会出现:
  - `mapper` 看起来成功
  - 但 `image_undistorter` / 后续训练资产却只剩一个很小的子模型

### 未来风险
- 以后如果继续批量导入别的场景, 只看 `mapper exit code = 0` 还不够
- 必须额外核对:
  - 最终选中的 model 注册图数量
  - 最终 `images/` 数量
  - 根级 `sparse/0` 是否真的对应主模型

### 当前结论
- 当前已知事实:
  - `recon/convert.py` 已改成自动选择注册图数最多的 sparse model
  - `my4_fullcolmap` 已用这套逻辑成功修复
- 仍未确认的部分:
  - 未来是否需要把“最佳模型选择规则”继续扩展为更多指标, 例如平均 track 长度或 BA 质量

### 后续讨论入口
- 下次再看到“mapper 成功, 但 images 太少”的现象时, 先看:
  - [convert.py](/root/autodl-tmp/home/rais/FreeFix/recon/convert.py)
  - [notes__colmap_my4.md](/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md)
  - [ERRORFIX__colmap_my4.md](/root/autodl-tmp/home/rais/FreeFix/ERRORFIX__colmap_my4.md)

## [2026-03-27 04:55:05] [Session ID: 20260327T045120Z-main] 主题: `my4_fullcolmap_quality` 这条训练线里, 更长训练与更多 GS 没有自动换来更好的 test 指标

### 发现来源
- 在同一配置、同一 test split 下连续补完三档手动评测后发现:
  - `9999`
  - `29999`
  - `49999`

### 核心问题
- 这条线如果默认取“最终步”, 当前会稳定选到一个比中前期更差的 checkpoint。
- 从动态证据看:
  - `9999`: `PSNR 23.1868 / SSIM 0.8350 / LPIPS 0.2547 / GS 300253`
  - `29999`: `PSNR 22.7931 / SSIM 0.8258 / LPIPS 0.2675 / GS 373083`
  - `49999`: `PSNR 22.8325 / SSIM 0.8253 / LPIPS 0.2585 / GS 373083`

### 为什么重要
- 这不是“某一次看图的主观偏好”。
- 现在已经有三档真实评测证据说明:
  - checkpoint 选择本身就是一等策略问题
  - 不能再把“最终步”当默认最优

### 未来风险
- 如果后续别的场景也沿用“只看最后 checkpoint”的习惯, 很可能会静默交付次优结果。
- 如果继续只加训练步数、不改保存和筛选策略, 还会重复浪费算力和时间。

### 当前结论
- 当前已知事实:
  - 在这条训练线上, `9999` 是当前最佳 test checkpoint
  - `29999` 与 `49999` 都没有反超它
- 仍未确认的部分:
  - 最优点是否恰好在 `9999`, 还是落在它附近更细的某个中前期 checkpoint

### 后续讨论入口
- 下次继续优化这条线时, 先看:
  - [summary_compare_3way_web.jpg](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_quality_eval_compare/summary_compare_3way_web.jpg)
  - [notes__colmap_my4.md](/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md)
  - [LATER_PLANS__colmap_my4.md](/root/autodl-tmp/home/rais/FreeFix/LATER_PLANS__colmap_my4.md)

## [2026-03-27 14:21:07] [Session ID: 20260327T141244Z-main] 主题: 在 `my4_fullcolmap` 这条线上, “更稳的短训组合”已经明确优于旧 `quality` 长训线

### 发现来源
- 在本轮按计划完成以下动作后得到:
  - `quality 9999` 视频导出
  - `stable_12k` 配置落盘
  - `stable_12k` 真实训练
  - `stable_12k 11999` 手动评测

### 核心问题
- 过去的口径更接近:
  - “先把窗口拉长”
  - “把 `pose/app/depth` 都打开”
- 但这轮新的动态证据显示:
  - 对 `my4_fullcolmap`, 这不一定是最优方向
- 同一数据、同一 test split 下:
  - `stable_12k 11999`: `PSNR 25.9493 / SSIM 0.8618 / LPIPS 0.2220 / GS 268776`
  - `quality 9999`: `PSNR 23.1868 / SSIM 0.8350 / LPIPS 0.2547 / GS 300253`

### 为什么重要
- 这不是“主观上好像更顺眼”。
- 现在已经有新的硬证据说明:
  - 当前更好的方向是“更稳的训练窗口 + 更受控的补偿”
  - 不是默认把更多补偿和更长训练一起打开

### 未来风险
- 如果后续又回到“训练越久越好, 补偿越多越稳”的习惯, 很容易把当前更优方向重新冲掉。
- 但反过来, 如果没有做单因素消融, 也会误把“组合收益”说成“单一模块根因”。

### 当前结论
- 当前已知事实:
  - `stable_12k` 组合策略已经显著优于旧 `quality` 线
  - 当前主交付候选应该切到 `stable_12k 11999`
- 仍未确认的部分:
  - 这次收益到底有多少来自:
    - `app_opt=false`
    - 更短 `max_steps`
    - 更早 `refine_stop_iter`

### 后续讨论入口
- 下次继续推进前先看:
  - [recon_my4_fullcolmap_stable_12k.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_stable_12k.yaml)
  - [val_step11999.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_eval_11999/stats/val_step11999.json)
  - [render_ckpt_11999.mp4](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k/to_refine/render_ckpt_11999.mp4)

## [2026-03-27 09:31:56] [Session ID: 20260327T091216Z-main] 主题: CLIP 上限紧的 refine prompt, 先做最小动态证伪比整轮盲跑更值钱

### 发现来源
- 在 `my4_fullcolmap_v2 best` 的第二次 Flux refine 观感验证中发现
- 第一轮 prompt 看起来已经“压缩过”, 但只有真实运行日志才能确认它是否真的进了编码器

### 核心问题
- 对 `CLIP 77 tokens` 这类硬上限来说, 肉眼看着“不长”的中英混合 prompt, 实际上仍可能严重超长
- 如果不先看首段日志, 很容易整轮跑完才发现:
  - 最想保住的词根本没进编码器

### 为什么重要
- 这不是 `my4` 或 `Flux` 私有的小问题
- 只要流程底层还是 `CLIP` 类文本编码器, 类似风险都会重复出现
- 特别是:
  - 中文长串
  - 中英混合风格词
  - 多个并列光效词

### 未来风险
- 如果以后继续盲目整轮跑 refine:
  - 会浪费显存和时间
  - 还会得到“看起来跑通, 其实语义没打准”的假结果

### 当前结论
- 当前已知事实:
  - 第一轮中英混合 prompt 真实触发了 `126 > 77`
  - 被截掉的正好是 `god rays / 光束 / 镜头光晕 / high detail`
  - 第二轮改成更短英文主锚点后, 截断 warning 消失
- 仍未确认的部分:
  - 哪一种英文锚点组合对这个场景的最终观感最优

### 后续讨论入口
- 下次再做任何 `Flux refine` prompt 调整前, 先看:
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`
  - `/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/flux_shinkai_museum_v2.yaml`
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/flux_shinkai_museum_v2_run.log`

## [2026-03-27 14:33:22] [Session ID: 20260327T142526Z-main] 主题: 在 `my4_fullcolmap` 这条线上, `app_opt=true` 本身就足以把结果从最优解拉回去

### 发现来源
- 在上一轮 `stable_12k app_opt=false` 完成后
- 紧接着做了单因素消融:
  - 只恢复 `app_opt=true`
  - 其余训练窗口和几何相关设置保持不变

### 核心问题
- 之前还存在一个关键不确定点:
  - 到底是“短窗口”更重要
  - 还是“关闭 `app_opt`”更重要
- 当前这轮新证据已经把这件事钉得很实:
  - `app_opt=false`: `PSNR 25.9493 / SSIM 0.8618 / LPIPS 0.2220`
  - `app_opt=true`: `PSNR 23.2633 / SSIM 0.8354 / LPIPS 0.2486`

### 为什么重要
- 这不再是组合实验里的模糊判断。
- 现在已经有:
  - 静态证据: 两轮配置只差 `app_opt`
  - 动态证据: 指标大幅回落
- 所以这条线后续的默认训练口径, 应该明确把 `app_opt` 当成高风险开关。

### 未来风险
- 如果后续忘了这条结论, 又默认把 `app_opt` 打开, 很可能会稳定重现“结构发虚、重影感上来、指标回落”的问题。
- 如果以后别的场景也直接套这条经验, 又可能会过度泛化, 因为当前证据还只覆盖 `my4_fullcolmap`。

### 当前结论
- 当前已知事实:
  - 在 `my4_fullcolmap` 这条线上, `app_opt=true` 本身就是主要退化来源
  - `app_opt=false` 应该成为这条线的默认口径
- 仍未确认的部分:
  - 这个规律在其他场景是否同样成立

### 后续讨论入口
- 下次继续前先看:
  - [recon_my4_fullcolmap_stable_12k_app.yaml](/root/autodl-tmp/home/rais/FreeFix/exp_cfg/my4/recon_my4_fullcolmap_stable_12k_app.yaml)
  - [val_step11999.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_app_eval_11999/stats/val_step11999.json)
  - [val_step11999.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_eval_11999/stats/val_step11999.json)

## [2026-03-27 06:55:58] [Session ID: 019d2b2b-d919-70a2-8f1e-1deda75211ab] 主题: `app_opt=false` 的 `stable_12k` 线在 `9000-12000` 区间内没有出现提前回落

### 发现来源
- 在 dense-scan 训练完成后, 连续做了四档真实评测:
  - `8999`
  - `9999`
  - `10999`
  - `11999`

### 核心问题
- 旧 `quality` 线曾经明确出现:
  - 中前期 checkpoint 优于最终步
- 但这轮新的 `app_opt=false` 短训线, 动态证据显示并不是那个走势

### 为什么重要
- 这会直接改变下一步优化策略
- 如果继续拿旧线的直觉来指导新线, 很容易误把“应该往后延一点”做成“应该更早停”

### 未来风险
- 如果后续只因为旧经验就把默认 checkpoint 提前到 `9999` 或 `10999`, 会把当前这条线已经拿到的后段收益主动丢掉
- 但反过来, 目前也还不能直接把“12000 之后一定继续涨”说成已验证结论

### 当前结论
- 当前已知事实:
  - `8999`: `PSNR 25.6098 / SSIM 0.8570 / LPIPS 0.2351`
  - `9999`: `PSNR 25.7586 / SSIM 0.8599 / LPIPS 0.2283`
  - `10999`: `PSNR 25.8514 / SSIM 0.8608 / LPIPS 0.2241`
  - `11999`: `PSNR 25.9338 / SSIM 0.8617 / LPIPS 0.2216`
  - 在当前扫描窗口里, 三项指标都持续朝更好方向移动
- 仍未确认的部分:
  - `12000` 之后是否继续改善
  - 还是会在更后一点进入平台期

### 后续讨论入口
- 下次继续推进前先看:
  - `/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_stable_12k_dense_eval_compare/summary_4way.json`
  - `/root/autodl-tmp/home/rais/FreeFix/LATER_PLANS__colmap_my4.md`
  - `/root/autodl-tmp/home/rais/FreeFix/notes__colmap_my4.md`

## [2026-03-27 08:30:49] [Session ID: 20260327T074108Z-main] 主题: `my4_fullcolmap` 上的 train-only blur 清洗, 会稳定推高 PSNR, 但不会自动带来更好的 LPIPS

### 发现来源
- 在 `my4_fullcolmap` 上先做了第一版保守删图
- 生成 `my4_fullcolmap_v2`
- 然后用同一条 `stable_12k_dense` 线重新完成训练与四档真实评测

### 核心问题
- 之前我们只知道“数据清洗可能值得做”。
- 现在新证据把这件事拆得更细了:
  - `PSNR` 确实持续上涨
  - 但 `LPIPS` 并没有一起变好
- 以 `11999` 为例:
  - 原线: `25.9338 / 0.8617 / 0.2216`
  - `v2`: `26.0887 / 0.8617 / 0.2257`

### 为什么重要
- 这会直接改变后续优化口径。
- 如果目标是“先冲 PSNR”, 这条路已经被动态证据证明有效。
- 但如果目标是“整体观感一起变好”, 就不能把“PSNR 涨了”直接等价成“画质全变好”。

### 未来风险
- 如果后续只沿着“继续删 blur 帧”一路推进, 很可能会继续得到:
  - 更高 PSNR
  - 但不一定更好的 LPIPS
- 反过来, 如果因为 LPIPS 没同步改善就立刻放弃清洗路线, 也会错过它在几何和像素误差上的真实收益。

### 当前结论
- 当前已知事实:
  - train-only blur 清洗在这条线里, 会稳定把四档 checkpoint 的 PSNR 一起抬高
  - 最佳点仍然落在 `11999`
- 仍未确认的部分:
  - 更激进清洗是否还能继续推高 PSNR
  - 以及是否能找到同时挽回 LPIPS 的第二个调节抓手

### 后续讨论入口
- 下次继续前先看:
  - [summary_4way.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense_eval_compare/summary_4way.json)
  - [val_step11999.json](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense_eval_11999/stats/val_step11999.json)
  - [BEST_RESULT.md](/root/autodl-tmp/home/rais/FreeFix/outputs/my4_fullcolmap_v2_stable_12k_dense/BEST_RESULT.md)
