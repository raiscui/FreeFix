from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


# =============================================================================
# refine backend 共用轻量 helper
# -----------------------------------------------------------------------------
# 这里故意只放:
# - CLI 参数
# - 路径覆盖
# - 日志
# - 本地模型来源解析
#
# 这些能力在 `flux / sdxl / kontext` 三条入口里都是同一套语义。
# 提前抽出来, 能避免第三条 backend 继续复制粘贴同一批基础逻辑。
# =============================================================================


def build_stage_logger(prefix: str):
    """返回带 backend 前缀的阶段日志函数。"""

    def log(message: str) -> None:
        print(f"[{prefix}] {message}", flush=True)

    return log


def build_refine_arg_parser(*, description: str) -> argparse.ArgumentParser:
    """构造 refine backend 通用 CLI。

    三条 backend 的 CLI 契约保持一致, 这样 wrapper 才能稳定分流。
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--exp_cfg", type=str, required=True, help="exp cfg path")
    parser.add_argument("--base_cfg", type=str, default="exp_cfg/base.yaml", help="base cfg path")
    parser.add_argument(
        "--colmap-path",
        type=str,
        default=None,
        help="运行时覆盖数据集路径, 直接指向 COLMAP 场景目录",
    )
    parser.add_argument(
        "--ckpt-path",
        type=str,
        default=None,
        help="运行时覆盖初始高斯 checkpoint 路径",
    )
    return parser


def append_pose_jitter_log(log_path: Path, *, frame_index: int, cam_param: dict) -> None:
    """把每轮 synthetic 相机采样结果追加到 jsonl。"""
    sample_log = cam_param.get("sample_log")
    if not isinstance(sample_log, dict):
        return

    record = {
        "frame_index": int(frame_index),
        "plan_index": cam_param.get("plan_index"),
        "camera_mode": cam_param.get("camera_mode"),
        "source_split": cam_param.get("source_split"),
        "source_index": cam_param.get("source_index"),
        "source_repeat_index": cam_param.get("source_repeat_index"),
        "source_image_name": cam_param.get("source_image_name"),
        "image_id": cam_param.get("image_id"),
        "sample_log": sample_log,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def resolve_optional_checkpoint_path(cfg) -> str | None:
    """解析运行时覆盖的初始 checkpoint 路径。"""
    raw_path = getattr(cfg, "load_ckpt_path", None)
    if raw_path is None:
        return None

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return str(candidate)

    # 先尊重用户从仓库根目录运行时写的相对路径。
    if candidate.exists():
        return str(candidate.resolve())

    # 仓库相对路径不存在时, 再回退成相对 `base_dir` 的路径。
    return str((Path(cfg.base_dir) / candidate).resolve())


def apply_runtime_path_overrides(cfg, config) -> str | None:
    """把 wrapper 或 CLI 传入的路径覆盖回底层 GS 配置。"""
    colmap_path = getattr(cfg, "colmap_path", None)
    if colmap_path is not None:
        scene_dir = Path(colmap_path).expanduser().resolve()
        config.data_dir = str(scene_dir)

        # 如果目标场景目录里已经有 partition, 优先直接跟过去。
        # 这样用户只传一个 `--colmap-path`, 不必再手工同步旧配置里的分片路径。
        partition_path = scene_dir / "partition.json"
        if partition_path.exists():
            config.partition = str(partition_path)

    return resolve_optional_checkpoint_path(cfg)


def resolve_local_model_source(
    cfg,
    *,
    config_attr: str,
    default_repo_id: str,
    default_local_paths: Sequence[Path],
    label: str,
) -> tuple[str, bool]:
    """解析模型来源, 优先使用显式配置或本地快照。"""
    configured_path = getattr(cfg, config_attr, None)
    if configured_path not in (None, ""):
        candidate = Path(str(configured_path)).expanduser()
        if not candidate.exists():
            raise FileNotFoundError(f"配置里的 {config_attr} 不存在: {candidate}")
        if not (candidate / "model_index.json").exists():
            raise FileNotFoundError(f"本地 {label} 目录缺少 model_index.json: {candidate}")
        return str(candidate), True

    for candidate in default_local_paths:
        if candidate.exists() and (candidate / "model_index.json").exists():
            return str(candidate), True

    return default_repo_id, False
