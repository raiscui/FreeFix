## [2026-03-27 15:36:37] [Session ID: 20260327T153637Z-main] 主题: 更强的基础模型并不意味着同参 refine 会更好

### 发现来源
- `my5` 的 `12k` 与 `30k` 对照实验
- 同一组 Flux refine 参数分别作用在:
  - `ckpt_11999.pt`
  - `ckpt_29999.pt`

### 核心问题
- `30k base` 已经明显优于 `12k base`
- 但把 `12k` 上跑过的那组 refine 参数原样套到 `30k` 上, 反而会把结果拉差

### 为什么重要
- 这说明 refine 不是“基础模型越强, 同一套参数越稳”的单调过程
- 如果后面继续按旧参数盲跑更长训练线, 很容易把已经更好的基础结果又修坏

### 未来风险
- 未来如果直接把 `12k` 上的 refine 参数平移到:
  - 更长训练
  - 更高质量基础模型
  - 更稠密的 GS 状态
  这类场景, 很可能继续出现“基础更好, refine 反而过度”的现象

### 当前结论
- 当前最优 test 结果停在:
  - `30k base`
- 当前 `30k refine vs 30k base` 的 test 增量:
  - `PSNR -0.2261`
  - `SSIM -0.00008`
  - `LPIPS +0.0372`
- 因此当前参数组合应被视为:
  - 对 `30k` 基础模型过强

### 后续讨论入口
- 如果以后继续做 refine 调参, 建议先看:
  - `notes__colmap_my5.md`
  - `LATER_PLANS__colmap_my5.md`
- 第一优先不是继续加训练步数, 而是先把 refine 强度调轻

## [2026-03-27 18:09:34] [Session ID: 20260327T175741Z-main] 主题: 对比 `test_every` 这类 split 规则时, 默认 test 分数不是天然同一 benchmark

### 发现来源
- `35k base` vs `35k te7` 对照实验
- 两条线都完整跑到了 `34999`, 也都完成了基础评估

### 核心问题
- 一旦 `test_every` 改了:
  - 训练集会变
  - 测试集也会一起变
- 所以“各自默认 test JSON”的差异, 并不等于“同一批样本上的纯模型差异”

### 为什么重要
- 如果忽略这一点, 很容易把:
  - benchmark 难度变化
  - 误读成模型本身变好或变差
- 这会直接污染 split / partition 类实验的结论

### 未来风险
- 后面如果继续比较:
  - `test_every`
  - 自定义 partition
  - 训练步数
  - refine 前后的 base fidelity
  这类变量, 只看默认 test 分数就可能再次得出不严谨结论

### 当前结论
- 这轮通过补“双方共同未见的 6 张 holdout”后, 证据已经足够说明:
  - `35k te7` 不是更好
- 但更重要的长期规律是:
  - 以后做 split 研究时, 应优先固定独立 benchmark

### 后续讨论入口
- 继续看:
  - `notes__colmap_my5.md`
  - `LATER_PLANS__colmap_my5.md`
- 如果下一轮还做 split / partition 研究, 先准备固定 `partition.json`

## [2026-03-27 18:54:03] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 主题: 长 densify 对 base 有增益, 但已经进入明显的边际收益区

### 发现来源
- `35k base` vs `50k + 长 densify` 的真实训练与基础评估
- 两条线都使用:
  - `test_every: 8`
  - 同一份 `my5` 数据

### 核心问题
- 把训练从 `35k` 拉到 `50k`, 并把 densify 窗口从 `9000` 拉到 `30000` 后:
  - 指标确实继续变好了一点
  - 但提升幅度已经很小

### 为什么重要
- 这说明当前 base 质量的上限, 可能不再主要受“训练时间不够”限制。
- 如果继续只靠加步数堆, 很容易多花不少算力, 只换来很窄的提升。

### 未来风险
- 后面如果继续把主路线推到:
  - `60k`
  - `80k`
  - 更长 densify
  但不重新审视数据和 densify 策略, 可能会进入低性价比区间。

### 当前结论
- `50k + 长 densify` 相对 `35k base`:
  - `test PSNR +0.02845`
  - `test LPIPS -0.00315`
  - `test SSIM -0.00072`
- 因此它是“有收益但不大”的有效路线, 不是新的量级跃迁。

### 后续讨论入口
- 如果继续追 base 质量, 下一轮优先看:
  - `notes__colmap_my5.md`
  - `WORKLOG__colmap_my5.md`
- 更推荐的下一步是:
  - 精细化 densify 窗口搜索
  - 数据 / COLMAP 清洗

## [2026-03-27 19:23:40] [Session ID: 019d2fa3-847c-73e0-bd2b-4c29a070ef49] 主题: 外部 FastGS checkpoint 已被真实验证可桥接进 FreeFix refine

### 发现来源
- `my5_nomask_v1` 的真实 FastGS checkpoint:
  - `/home/rais/FastGS/output/my5_nomask_v1/checkpoints/ckpt_35000.pth`
- 本轮真实 bridge + refine

### 核心问题
- 之前这条链路虽然已经有脚本和单测, 但还缺一轮真实 `my5` 级别的外部 run 验证。
- 这次已经补上了。

### 为什么重要
- 这说明后面如果又有 FastGS 侧更强、或不同风格的 base checkpoint, 不需要先完整迁回 FreeFix 重新训练, 就能直接接 refine 做视觉修补。

### 未来风险
- 当前 bridge refine 能跑通, 不代表评估链路也完全同样支持外部 ckpt。
- 如果后续要系统比较 bridge base / refined 的量化指标, 还需要补 evaluation 的 `--ckpt-path` 能力。

### 当前结论
- 这次真实 `my5` bridge refine 的初始高斯数是:
  - `49200`
- refined checkpoint 的高斯数增长到了:
  - `154614`
- 因此这条链路已经从“格式兼容”升级成“可真实继续优化”的生产级路径。

### 后续讨论入口
- 继续看:
  - `WORKLOG__colmap_my5.md`
  - `ERRORFIX__colmap_my5.md`
- 如果后续要补定量评估, 先看:
  - `LATER_PLANS__colmap_my5.md`

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 主题: 外部 bridge checkpoint 在 FreeFix 中“可 refine”不等于“可无损复现 FastGS base benchmark”

### 发现来源
- `my5_nomask_v1` 的真实 bridge 评估与 refined 评估
- FastGS 原始结果文件:
  - `/home/rais/FastGS/output/my5_nomask_v1/results.json`

### 核心问题
- 当前已经同时观察到两件事:
  - 外部 FastGS checkpoint 成功桥接进 FreeFix, 并且可以真实 refine
  - 但 bridge base 的量化结果明显低于 FastGS 原始记录
- 这说明“链路可跑通”和“benchmark 完全等价”不能混为一谈

### 为什么重要
- 如果忽略这个区别, 很容易把:
  - refine 后指标大幅回升
  误读成:
  - FreeFix 已经 1:1 复现了 FastGS base
- 这会污染后续对:
  - import fidelity
  - refine 真正收益
  - 跨框架 checkpoint 兼容性
  的判断

### 未来风险
- 后面如果直接把 bridge base 和原始 FastGS 结果当成同一 benchmark 横比, 结论可能会被:
  - split 差异
  - 相机顺序差异
  - 渲染契约差异
  - 导入归一化差异
  一起污染

### 当前结论
- 已验证事实:
  - bridge base `test`:
    - `PSNR 23.9542`
    - `SSIM 0.8489`
    - `LPIPS 0.2550`
  - refined `test`:
    - `PSNR 26.6134`
    - `SSIM 0.8804`
    - `LPIPS 0.2211`
  - FastGS 原始记录:
    - `PSNR 27.2039`
    - `SSIM 0.8910`
    - `LPIPS 0.2026`
- 当前仍未确认:
  - bridge fidelity 损失的具体根因
- 当前更稳妥的口径是:
  - bridge refine 这条链路已被真实验证有效
  - 但 bridge base 还不能直接视为 FastGS 原始 benchmark 的无损镜像

### 后续讨论入口
- 继续看:
  - `LATER_PLANS__colmap_my5.md`
  - `notes__colmap_my5.md`
  - `WORKLOG__colmap_my5.md`
- 如果下一轮继续查根因, 先做:
  - `--no-normalize` 导入对照
  - split / 相机顺序一致性核对
  - 单帧指标复算

## [2026-03-27 19:43:14] [Session ID: 20260327T194314Z-main] 主题: FastGS -> FreeFix bridge 的主损失不在几何, 而在高阶 SH 颜色旋转缺失

### 发现来源
- `my5_nomask_v1` 的 bridge 掉分根因调查
- raw / normalized / DC-only 三组真实对照实验

### 核心问题
- 一开始看起来像是“整个 bridge fidelity 都不对”
- 但更细地拆开后发现:
  - raw checkpoint + raw cameras 在 FreeFix renderer 中几乎能复现 FastGS
  - 只有经过 FreeFix normalization transform 后才明显掉分

### 为什么重要
- 这意味着 bridge 方案本身不是坏的。
- 真正需要修的是一条很具体的契约:
  - 当场景坐标发生大角度全局旋转时
  - 方向相关的高阶 SH 颜色也必须一起旋转

### 未来风险
- 如果后面继续拿别的 FastGS checkpoint 直接 bridge:
  - 只要目标 FreeFix transform 含有明显旋转
  - 又没补 SH rotation
  就还会重复出现“base 掉分, refine 拉回”的模式

### 当前结论
- 已验证事实:
  - raw + raw cameras:
    - `PSNR 27.1882`
    - `SSIM 0.8907`
    - `LPIPS 0.2037`
  - normalized + normalized cameras:
    - `PSNR 23.9542`
    - `SSIM 0.8489`
    - `LPIPS 0.2550`
  - 只保留 DC (`shN=0`) 后, raw 与 normalized 两边重新完全对齐
  - 当前全局旋转角约:
    - `86.79` 度
- 已验证结论:
  - 几何变换没有根本问题
  - 主损失来自高阶 SH 在全局旋转后没有做 SH basis rotation

### 后续讨论入口
- 如果下一轮直接修:
  - 先看 `recon.import_fastgs.py`
  - 再看 `notes__colmap_my5.md`
  - 最后按 `LATER_PLANS__colmap_my5.md` 补回归测试

## [2026-03-27 21:19:24] [Session ID: 20260327T194314Z-main] 主题: 3DGS / FastGS 跨坐标系桥接时, “旋转几何但不旋转高阶 SH” 会制造一种很像 renderer bug 的假象

### 发现来源
- `my5_nomask_v1` 的 FastGS -> FreeFix bridge 修复
- 修复前后真实评估对比

### 核心问题
- 如果只看现象:
  - bridge base 掉很多
  - refine 又能拉回很多
- 很容易误以为:
  - renderer 不兼容
  - 相机契约不一致
  - benchmark 对不上
- 但这次真正的问题只是:
  - 高阶 SH 没有跟着全局坐标旋转

### 为什么重要
- 这类 bug 非常迷惑, 因为:
  - 几何通常看起来还是“差不多对”
  - GT 和 split 也可能全都对
  - 最后却在 view-dependent 外观上整体掉分
- 如果没有把 `DC-only` 和 full SH 分开做实验, 很容易一直在错误层面上排查

### 未来风险
- 以后只要继续做:
  - FastGS / 3DGS / FreeFix 之间的 checkpoint bridge
  - 并且目标坐标系含有明显全局旋转
- 如果忘了同步旋转高阶 SH, 就会重复出现同类掉分

### 当前结论
- 这次 `my5_nomask_v1` 已经证明:
  - 修复 SH rotation 后, bridge base 从 `23.95` 回到 `27.19`
  - 已经基本追平 FastGS 原始 `27.20`
- 因此这条经验可以上升成长期规律:
  - 方向相关外观参数必须被视为“坐标系相关状态”, 不能只桥接几何不桥接它

### 后续讨论入口
- 下次再做 checkpoint bridge, 先看:
  - `ERRORFIX__colmap_my5.md`
  - `notes__colmap_my5.md`
  - `recon/import_fastgs.py`

## [2026-03-27 21:37:03] [Session ID: 20260327T212417Z-main] 主题: 修复 bridge bug 后, 当前这组 refine 参数的真实角色更清楚了

### 发现来源
- 基于修复后 canonical bridge checkpoint 的 refine rerun
- 同口径的 base + refined 真实评估

### 核心问题
- 在旧 bridge bug 还存在时, refine 看起来像是在“明显救回质量”。
- 但 bug 修掉以后再看, 同一组参数其实仍然会把 GT 指标拉差。

### 为什么重要
- 这说明过去对 refine 收益的感知里, 混进了两层不同的东西:
  - 补旧 bridge bug 造成的失真
  - 真正的主观修补 / 风格修正
- 如果不把这两层拆开, 后面很容易高估这组 refine 参数的泛化价值。

### 未来风险
- 如果以后继续把这组参数直接套到:
  - 更干净的 bridge
  - 更强的 base
  - 其它外部 checkpoint
 可能还会重复出现:
  - 主观瑕疵少一点
  - 但 GT fidelity 更差

### 当前结论
- 已验证事实:
  - 修复后 base `test`:
    - `PSNR 27.1882`
    - `SSIM 0.8907`
    - `LPIPS 0.2037`
  - 修复后 refined `test`:
    - `PSNR 26.7527`
    - `SSIM 0.8826`
    - `LPIPS 0.2231`
- 已验证结论:
  - 当前这组 refine 参数不再适合作为默认量化主线
  - 它更像一组“主观修补参数”, 而不是“提高 GT fidelity 的参数”

### 后续讨论入口
- 如果以后继续做 refine:
  - 先看 `notes__colmap_my5.md`
  - 再看 `LATER_PLANS__colmap_my5.md`
- 下一轮更值得做的是:
  - 轻量参数搜索
  - 而不是默认重用这组偏强配置

## [2026-03-28 18:08:00] [Session ID: 945d570e-8f9a-4112-9004-6a0f244a9a65] 主题: `to_refine/refine_c2ws.npy` 不能被默认视为 `after_refine.mp4` 的真实镜头轨迹

### 发现来源
- `after_refine.mp4` 镜头轨迹导出工具开发
- 对 `Refiner.test_dataset` 真实轨迹与 `to_refine/ckpt_34999/refine_c2ws.npy` 的逐帧矩阵对比

### 核心问题
- 这两条轨迹看起来都来自同一批验证视角, 帧数也都是 `41`
- 但它们不是同一条位移轨迹

### 为什么重要
- 如果后面有人把 `to_refine/refine_c2ws.npy` 直接拿去解释 `after_refine.mp4`
- 就会把训练期为 driving/render 引入的那个人工平移, 错当成 refine 视频本身的真实镜头路径

### 未来风险
- 这类误读会污染:
  - 动画数据导出
  - 相机轨迹可视化
  - 外部 DCC/动画工具链对接
  - “为什么视频镜头和测试相机位置对不上”的后续排查

### 当前结论
- 已验证事实:
  - 两者旋转矩阵逐帧一致:
    - `rotation_matrix_diff_max = 0.0`
  - 但平移逐帧恒差约 `2.5`
- 因此更稳的规则是:
  - refine 视频轨迹应以 `Refiner.test_dataset` 为准
  - `to_refine/refine_c2ws.npy` 只能当训练期 sidecar 或对照证据

### 后续讨论入口
- 先看:
  - `ours/export_refine_video_trajectory.py`
  - `notes__colmap_my5.md`
- 如果以后还要导出别的 refine 视频轨迹, 继续沿用 `refiner_test_dataset` 这条口径
