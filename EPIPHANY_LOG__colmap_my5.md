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
