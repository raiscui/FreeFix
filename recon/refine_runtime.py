import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional, Sequence


def resolve_strategy_resume_step(
    *,
    payload_step: Optional[int],
    load_step: int | str,
    fallback_load_step: Optional[int | str] = None,
) -> int:
    """解析 refine 恢复时应该沿用的训练步数基线。"""
    if payload_step is not None:
        normalized_payload_step = int(payload_step)
        if normalized_payload_step >= 0:
            return normalized_payload_step

    conversion_errors: list[str] = []
    for candidate_name, candidate_value in (
        ("load_step", load_step),
        ("fallback_load_step", fallback_load_step),
    ):
        if candidate_value is None:
            continue
        try:
            return max(0, int(candidate_value))
        except (TypeError, ValueError):
            conversion_errors.append(f"{candidate_name}={candidate_value!r}")

    detail = ", ".join(conversion_errors) if conversion_errors else "没有可用的数值型步数候选"
    raise ValueError(f"checkpoint 未记录有效 step, 且无法解析恢复步数: {detail}")


def resolve_strategy_step(
    *,
    strategy_resume_step: int,
    local_step: int,
) -> int:
    """把 refine 局部步数映射回原训练时间轴上的真实步数。"""
    return max(0, int(strategy_resume_step)) + max(0, int(local_step))


def chunk_items(items: Sequence[Any], chunk_size: int) -> Iterator[Sequence[Any]]:
    """把序列按固定大小切块, 供批量渲染等场景复用。"""
    normalized_chunk_size = int(chunk_size)
    if normalized_chunk_size < 1:
        raise ValueError(f"chunk_size 必须 >= 1, 当前得到: {chunk_size}")

    for start in range(0, len(items), normalized_chunk_size):
        yield items[start : start + normalized_chunk_size]


def build_refine_resume_state_path(output_dir: str | Path) -> Path:
    """返回 refine 断点恢复状态文件路径。"""
    return Path(output_dir) / "refine_resume_state.json"


def build_refine_resume_checkpoint_path(base_dir: str | Path, exp_name: str) -> Path:
    """返回滚动覆盖的 refine 恢复 checkpoint 路径。"""
    return Path(base_dir) / "ckpts" / f"ckpt_{exp_name}__resume_latest.pt"


def build_generated_camera_log_path(output_dir: str | Path) -> Path:
    """返回 synthetic 相机记录 jsonl 路径。"""
    return Path(output_dir) / "refine" / "generated_cams.jsonl"


def build_refine_resume_state(
    *,
    exp_name: str,
    plan_total: int,
    next_plan_index: int,
    before_refine_complete: bool,
    synthetic_complete: bool,
    after_refine_complete: bool,
    resume_ckpt_path: str | None,
    final_ckpt_path: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """构造一份可落盘的 refine 恢复状态。"""
    normalized_plan_total = max(0, int(plan_total))
    normalized_next_plan_index = max(0, int(next_plan_index))
    if normalized_next_plan_index > normalized_plan_total:
        raise ValueError(
            "next_plan_index 不能超过 plan_total: "
            f"{normalized_next_plan_index} > {normalized_plan_total}"
        )

    if status is None:
        if final_ckpt_path is not None and after_refine_complete and synthetic_complete:
            status = "complete"
        elif after_refine_complete:
            status = "after_refine_complete"
        elif synthetic_complete:
            status = "synthetic_complete"
        elif before_refine_complete:
            status = "synthetic_in_progress"
        else:
            status = "before_refine_pending"

    return {
        "version": 1,
        "exp_name": exp_name,
        "status": status,
        "plan_total": normalized_plan_total,
        "next_plan_index": normalized_next_plan_index,
        "latest_completed_plan_index": normalized_next_plan_index - 1,
        "before_refine_complete": bool(before_refine_complete),
        "synthetic_complete": bool(synthetic_complete),
        "after_refine_complete": bool(after_refine_complete),
        "resume_ckpt_path": resume_ckpt_path,
        "final_ckpt_path": final_ckpt_path,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def load_refine_resume_state(path: str | Path) -> Optional[dict[str, Any]]:
    """读取 refine 恢复状态; 文件不存在时返回 `None`。"""
    state_path = Path(path)
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def save_refine_resume_state(path: str | Path, state: dict[str, Any]) -> None:
    """原子写入 refine 恢复状态, 避免中断时留下半截 json。"""
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_path.with_suffix(f"{state_path.suffix}.tmp")
    tmp_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(tmp_path, state_path)


def resolve_resume_checkpoint_path(
    *,
    resume_state: Optional[dict[str, Any]],
    initial_load_ckpt_path: str | None,
) -> str | None:
    """优先选择恢复状态里记录的 checkpoint, 否则回退到初始输入 ckpt。"""
    if resume_state is not None:
        recorded_path = resume_state.get("resume_ckpt_path")
        if isinstance(recorded_path, str) and recorded_path:
            candidate = Path(recorded_path).expanduser()
            if candidate.exists():
                return str(candidate.resolve())
    return initial_load_ckpt_path


_FRAME_INDEX_RE = re.compile(r"^(?P<prefix>.*?)(?P<index>\d+)$")


def _extract_frame_index(stem: str, *, expected_prefix: str = "") -> Optional[int]:
    if expected_prefix and not stem.startswith(expected_prefix):
        return None
    numeric_stem = stem[len(expected_prefix) :] if expected_prefix else stem
    match = _FRAME_INDEX_RE.match(numeric_stem)
    if match is None:
        return None
    index_text = match.group("index")
    if not index_text.isdigit():
        return None
    return int(index_text)


def remove_numbered_frames(
    frame_dir: str | Path,
    *,
    start_index: int,
    stem_prefix: str = "",
) -> None:
    """删除编号大于等于 `start_index` 的帧文件。"""
    normalized_start_index = max(0, int(start_index))
    target_dir = Path(frame_dir)
    if not target_dir.exists():
        return

    for frame_path in target_dir.glob("*.jpg"):
        frame_index = _extract_frame_index(frame_path.stem, expected_prefix=stem_prefix)
        if frame_index is None:
            continue
        if frame_index >= normalized_start_index:
            frame_path.unlink()


def truncate_jsonl_by_plan_index(
    jsonl_path: str | Path,
    *,
    keep_before_plan_index: int,
) -> None:
    """把 jsonl 截断到指定 plan 边界之前。"""
    target_path = Path(jsonl_path)
    if not target_path.exists():
        return

    threshold = max(0, int(keep_before_plan_index))
    kept_lines: list[str] = []
    for raw_line in target_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        record_plan_index = int(record.get("plan_index", record.get("frame_index", -1)))
        if record_plan_index < threshold:
            kept_lines.append(json.dumps(record, ensure_ascii=False))

    suffix = "\n" if kept_lines else ""
    target_path.write_text("\n".join(kept_lines) + suffix, encoding="utf-8")


def cleanup_stale_resume_artifacts(
    output_dir: str | Path,
    *,
    next_plan_index: int,
    c_exp_index: Sequence[object],
) -> None:
    """清理与恢复 checkpoint 不一致的中间 synthetic 产物。"""
    target_output_dir = Path(output_dir)
    normalized_next_plan_index = max(0, int(next_plan_index))

    remove_numbered_frames(
        target_output_dir / "refine" / "render",
        start_index=normalized_next_plan_index,
    )
    remove_numbered_frames(
        target_output_dir / "refine" / "depth",
        start_index=normalized_next_plan_index,
    )
    remove_numbered_frames(
        target_output_dir / "refine" / "gen",
        start_index=normalized_next_plan_index,
        stem_prefix="image_",
    )
    for exp_index in c_exp_index:
        remove_numbered_frames(
            target_output_dir / "refine" / "masks" / str(exp_index),
            start_index=normalized_next_plan_index,
        )

    gen_video_path = target_output_dir / "refine" / "gen.mp4"
    if gen_video_path.exists():
        gen_video_path.unlink()

    truncate_jsonl_by_plan_index(
        target_output_dir / "refine" / "pose_jitter_log.jsonl",
        keep_before_plan_index=normalized_next_plan_index,
    )
    truncate_jsonl_by_plan_index(
        build_generated_camera_log_path(target_output_dir),
        keep_before_plan_index=normalized_next_plan_index,
    )


def clear_after_refine_outputs(output_dir: str | Path) -> None:
    """清理未完成 run 的 after 对比产物, 防止恢复后混入旧文件。"""
    target_output_dir = Path(output_dir)
    after_dir = target_output_dir / "after_refine"
    if after_dir.exists():
        for image_path in after_dir.glob("*.jpg"):
            image_path.unlink()

    after_video_path = target_output_dir / "after_refine.mp4"
    if after_video_path.exists():
        after_video_path.unlink()


def _tensor_like_to_nested_list(value: Any) -> Any:
    """把 tensor / ndarray 风格对象转成可 json 序列化的嵌套列表。"""
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def append_generated_camera_record(
    log_path: str | Path,
    *,
    plan_index: int,
    cam_param: dict[str, Any],
) -> None:
    """记录每个 synthetic 视角的相机参数, 供断点恢复重建 train pool。"""
    target_path = Path(log_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "plan_index": int(plan_index),
        "image_id": cam_param.get("image_id"),
        "camera_mode": cam_param.get("camera_mode"),
        "source_split": cam_param.get("source_split"),
        "source_index": cam_param.get("source_index"),
        "source_repeat_index": cam_param.get("source_repeat_index"),
        "source_image_name": cam_param.get("source_image_name"),
        "K": _tensor_like_to_nested_list(cam_param.get("K")),
        "c2w": _tensor_like_to_nested_list(cam_param.get("c2w")),
    }
    with target_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_generated_camera_records(
    log_path: str | Path,
    *,
    keep_before_plan_index: int,
) -> list[dict[str, Any]]:
    """按 plan 边界读取已经稳定持久化的 synthetic 相机记录。"""
    target_path = Path(log_path)
    if not target_path.exists():
        return []

    threshold = max(0, int(keep_before_plan_index))
    records: list[dict[str, Any]] = []
    for raw_line in target_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        record_plan_index = int(record.get("plan_index", -1))
        if record_plan_index < threshold:
            records.append(record)
    return records


def restore_completed_generated_cams(
    log_path: str | Path,
    gen_dir: str | Path,
    *,
    keep_before_plan_index: int,
) -> list[dict[str, Any]]:
    """从已保存的 synthetic 图像与相机日志重建 train pool 里的生成样本。"""
    import numpy as np
    import torch
    from PIL import Image

    restored_cams: list[dict[str, Any]] = []
    for record in load_generated_camera_records(
        log_path,
        keep_before_plan_index=keep_before_plan_index,
    ):
        plan_index = int(record["plan_index"])
        image_path = Path(gen_dir) / f"image_{plan_index:03d}.jpg"
        if not image_path.exists():
            raise FileNotFoundError(
                "恢复 synthetic train pool 失败, 缺少生成图像: "
                f"{image_path}"
            )

        restored_cams.append(
            {
                "image": torch.from_numpy(np.array(Image.open(image_path).convert("RGB"))),
                "camtoworld": torch.tensor(record["c2w"], dtype=torch.float32),
                "K": torch.tensor(record["K"], dtype=torch.float32),
                "Gen": True,
                "image_id": record["image_id"],
            }
        )
    return restored_cams


def rebuild_video_from_frame_dir(
    frame_dir: str | Path,
    output_path: str | Path,
    *,
    fps: int,
) -> bool:
    """根据目录里的 jpg 帧重建视频。

    恢复模式下我们把 jpg 序列视为真相源。
    mp4 只是衍生产物, 丢了可以重建。
    """
    import imageio.v2 as imageio

    source_dir = Path(frame_dir)
    frame_paths = sorted(source_dir.glob("*.jpg"))
    if not frame_paths:
        return False

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(target_path, fps=int(fps))
    try:
        for frame_path in frame_paths:
            writer.append_data(imageio.imread(frame_path))
    finally:
        writer.close()
    return True
