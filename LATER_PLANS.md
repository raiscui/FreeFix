## [2026-03-26 07:20:13] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 主题: 若 pytorch3d 后续仍报新错, 优先复核官方支持矩阵

### 待后续处理事项
- 当前项目使用的是 Python 3.11.10 与 `torch 2.5.1+cu118`
- `pytorch3d v0.7.7` 官方 `INSTALL.md` 列出的支持矩阵只到 Python 3.10 和 PyTorch 2.3.1
- 如果在 CUDA mismatch 修复之后仍出现新的编译、头文件或 ABI 错误, 下一步优先评估:
  - 升级 `pytorch3d`
  - 调整 Torch 版本
  - 或确认项目里是否真的需要保留 `pytorch3d`

## [2026-03-26 08:45:50] [Session ID: 24cc3783-4a2b-4794-84b7-d2d4b7e7c6b6] 主题: 若要在本机 Blackwell GPU 上真正运行, 单独立项做版本栈迁移

### 待后续处理事项
- 目标不再是“修好安装”, 而是“让 `sm_120` GPU 上的最小 CUDA 运算跑通”
- 优先评估的升级方向:
  - `torch/torchvision` 切到官方支持 Blackwell 的 `2.7+cu128` 或更高
  - `xformers` 从 `v0.0.28.post3` 迁移到与新 Torch 对齐的版本, 或改为 source build
  - `pytorch3d` 评估 `v0.7.9` 以上是否仍需自维护补丁, 或寻找替代方案
  - `unidepth` 内部与 `pytorch3d` 耦合的 KNN / cutils 路径要跟着一起复查
- 执行方式建议:
  - 先在临时环境做完整探针
  - 通过后再落回项目 `pixi.toml`
  - 不要直接在主项目环境里盲改

## [2026-03-26 09:40:05] [Session ID: 019d28a9-9701-7013-a2b7-6683f4e4f3fe] 主题: Blackwell 迁移前, 先评估 pytorch3d 是否值得继续保留

### 待后续处理事项
- 当前主仓库几乎没有直接 `import pytorch3d`
- `UniDepth` 对它的直接耦合只剩一个很薄的本地 `pytorch3d_cutils.h`
- 因此在真正启动 `torch 2.7+/cu128` 迁移之前, 可以优先做一轮更聚焦的判断:
  - 是否能完全移除 `pixi.toml` 里的 `pytorch3d` 依赖
  - 是否只保留 `UniDepth` 自己的 `ops/knn`
  - 如果不能移除, 再决定是升到 `v0.7.9` 还是改走 `main/补丁版`

## [2026-03-27 21:44:58] [Session ID: 019d2f6a-705e-7ca1-97af-342c1bf4e24d] 主题: 补齐 GitHub 认证后继续推送到 `raiscui/FreeFix`

### 待后续处理事项
- 当前本地已新增远端:
  - `raiscui -> https://github.com/raiscui/FreeFix.git`
- 当前待推送提交仍是:
  - `3fb6b57b6007c36c5b0ea39e9832094727e2db52`
- 继续前需要先补齐一种可用认证:
  - GitHub PAT
  - 或安装并登录 `gh`
  - 或配置可用 SSH key / agent
- 认证补齐后, 直接执行:
  - `git push raiscui main:main`

## [2026-03-27 22:13:32] [Session ID: 019d2f6a-705e-7ca1-97af-342c1bf4e24d] 主题: `raiscui/FreeFix` 推送待办已落地

### 待后续处理事项
- 上一条“补齐认证后继续推送到 `raiscui/FreeFix`”已完成
- 当前无需继续跟进这条待办
