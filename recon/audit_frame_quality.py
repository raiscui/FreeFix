from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


# =============================================================================
# 图像质量审计工具
# -----------------------------------------------------------------------------
# 这个脚本的目标不是“直接删图”, 而是先把坏帧候选从 264 张图里筛出来。
# 先把证据变成报告, 后面再基于报告决定真正要删哪些图。
# =============================================================================


@dataclass
class FrameMetrics:
    image_name: str
    blur_score: float
    brightness_mean: float
    brightness_std: float
    dark_ratio: float
    bright_ratio: float
    prev_duplicate_distance: int | None
    next_duplicate_distance: int | None
    prev_similarity: float | None
    next_similarity: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="审计一组输入图像的模糊、曝光和近重复情况。")
    parser.add_argument(
        "--scene-dir",
        type=Path,
        required=True,
        help="场景目录, 例如 data/my4_fullcolmap",
    )
    parser.add_argument(
        "--input-subdir",
        type=str,
        default="input",
        help="要审计的图片子目录, 默认是 input",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="frame_audit",
        help="输出文件名前缀, 默认是 frame_audit",
    )
    parser.add_argument(
        "--blur-quantile",
        type=float,
        default=0.12,
        help="按模糊分数从低到高选候选的分位数, 默认 0.12",
    )
    parser.add_argument(
        "--exposure-quantile",
        type=float,
        default=0.10,
        help="按亮度异常程度选候选的分位数, 默认 0.10",
    )
    parser.add_argument(
        "--duplicate-distance-threshold",
        type=int,
        default=1,
        help="dHash 汉明距离阈值, 小于等于该值视为近重复候选",
    )
    parser.add_argument(
        "--duplicate-similarity-threshold",
        type=float,
        default=0.999,
        help="缩略图余弦相似度阈值, 大于等于该值视为近重复候选",
    )
    return parser.parse_args()


def list_images(image_dir: Path) -> list[Path]:
    images = sorted(path for path in image_dir.iterdir() if path.is_file())
    if not images:
        raise FileNotFoundError(f"没有在 {image_dir} 下找到可审计图片。")
    return images


def load_gray_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"无法读取图片: {path}")
    return image


def compute_blur_score(gray: np.ndarray) -> float:
    # 用经典的 Laplacian variance 做一阶模糊评分。
    # 分数越低, 边缘能量越弱, 越像模糊帧。
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def compute_exposure_metrics(gray: np.ndarray) -> tuple[float, float, float, float]:
    gray_f32 = gray.astype(np.float32)
    brightness_mean = float(gray_f32.mean())
    brightness_std = float(gray_f32.std())
    dark_ratio = float((gray <= 12).mean())
    bright_ratio = float((gray >= 243).mean())
    return brightness_mean, brightness_std, dark_ratio, bright_ratio


def compute_dhash(gray: np.ndarray) -> int:
    # 这里不依赖额外库, 直接实现一个 64-bit dHash。
    # 对于相邻几乎重复的帧, 这个指标很稳。
    thumb = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = thumb[:, 1:] > thumb[:, :-1]
    bits = "".join("1" if value else "0" for value in diff.flatten())
    return int(bits, 2)


def hamming_distance(lhs: int, rhs: int) -> int:
    return int((lhs ^ rhs).bit_count())


def compute_similarity_embedding(gray: np.ndarray) -> np.ndarray:
    # 用一个小灰度缩略图当作近重复特征。
    # 相比只看 hash, 这里还能补到“视觉上很像但 hash 稍有差异”的情况。
    thumb = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    vector = thumb.reshape(-1)
    vector -= vector.mean()
    norm = np.linalg.norm(vector)
    if norm <= 1e-8:
        return np.zeros_like(vector)
    return vector / norm


def cosine_similarity(lhs: np.ndarray, rhs: np.ndarray) -> float:
    return float(np.clip(np.dot(lhs, rhs), -1.0, 1.0))


def quantile_threshold(values: list[float], q: float, lower_tail: bool) -> float:
    array = np.asarray(values, dtype=np.float64)
    if lower_tail:
        return float(np.quantile(array, q))
    return float(np.quantile(array, 1.0 - q))


def build_markdown_report(
    scene_dir: Path,
    image_dir: Path,
    metrics: list[FrameMetrics],
    blur_candidates: list[str],
    dark_candidates: list[str],
    bright_candidates: list[str],
    duplicate_candidates: list[str],
    summary: dict,
) -> str:
    lines: list[str] = []
    lines.append(f"# Frame Audit Report: {scene_dir.name}")
    lines.append("")
    lines.append("## 范围")
    lines.append("")
    lines.append(f"- scene_dir: `{scene_dir}`")
    lines.append(f"- image_dir: `{image_dir}`")
    lines.append(f"- image_count: `{len(metrics)}`")
    lines.append("")
    lines.append("## 阈值")
    lines.append("")
    lines.append(f"- blur_threshold: `{summary['thresholds']['blur_score_lte']:.6f}`")
    lines.append(f"- dark_mean_threshold: `{summary['thresholds']['brightness_mean_lte']:.6f}`")
    lines.append(f"- bright_mean_threshold: `{summary['thresholds']['brightness_mean_gte']:.6f}`")
    lines.append(f"- duplicate_distance_threshold: `{summary['thresholds']['duplicate_distance_lte']}`")
    lines.append(
        f"- duplicate_similarity_threshold: `{summary['thresholds']['duplicate_similarity_gte']:.6f}`"
    )
    lines.append("")
    lines.append("## 候选统计")
    lines.append("")
    lines.append(f"- blur_candidates: `{len(blur_candidates)}`")
    lines.append(f"- dark_candidates: `{len(dark_candidates)}`")
    lines.append(f"- bright_candidates: `{len(bright_candidates)}`")
    lines.append(f"- duplicate_candidates: `{len(duplicate_candidates)}`")
    lines.append("")
    lines.append("## 候选名单")
    lines.append("")

    for title, names in [
        ("模糊候选", blur_candidates),
        ("偏暗候选", dark_candidates),
        ("偏亮候选", bright_candidates),
        ("近重复候选", duplicate_candidates),
    ]:
        lines.append(f"### {title}")
        lines.append("")
        if not names:
            lines.append("- 无")
        else:
            for name in names:
                lines.append(f"- `{name}`")
        lines.append("")

    lines.append("## 最低 blur_score 前 20")
    lines.append("")
    lines.append("| image | blur | mean | dark_ratio | bright_ratio | prev_dup | next_dup |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for item in sorted(metrics, key=lambda entry: entry.blur_score)[:20]:
        lines.append(
            f"| `{item.image_name}` | {item.blur_score:.3f} | {item.brightness_mean:.2f} | "
            f"{item.dark_ratio:.4f} | {item.bright_ratio:.4f} | "
            f"{item.prev_duplicate_distance if item.prev_duplicate_distance is not None else '-'} | "
            f"{item.next_duplicate_distance if item.next_duplicate_distance is not None else '-'} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_priority_review_list(
    metrics: list[FrameMetrics],
    blur_candidates: list[str],
    dark_candidates: list[str],
    bright_candidates: list[str],
    duplicate_candidates: list[str],
) -> list[dict[str, object]]:
    metrics_map = {item.image_name: item for item in metrics}
    candidate_map = {
        "blur": set(blur_candidates),
        "dark": set(dark_candidates),
        "bright": set(bright_candidates),
        "duplicate": set(duplicate_candidates),
    }
    names = sorted(set().union(*candidate_map.values()))
    rows: list[dict[str, object]] = []
    for name in names:
        tags = [key for key, values in candidate_map.items() if name in values]
        item = metrics_map[name]
        rows.append(
            {
                "image_name": name,
                "tags": tags,
                "tag_count": len(tags),
                "blur_score": item.blur_score,
                "brightness_mean": item.brightness_mean,
                "dark_ratio": item.dark_ratio,
                "bright_ratio": item.bright_ratio,
                "prev_duplicate_distance": item.prev_duplicate_distance,
                "prev_similarity": item.prev_similarity,
            }
        )
    rows.sort(key=lambda row: (-int(row["tag_count"]), float(row["blur_score"]), str(row["image_name"])))
    return rows


def save_priority_contact_sheet(
    image_dir: Path,
    review_rows: list[dict[str, object]],
    output_path: Path,
    limit: int = 24,
) -> None:
    selected = review_rows[:limit]
    if not selected:
        return

    thumbs: list[Image.Image] = []
    for row in selected:
        image_name = str(row["image_name"])
        image = Image.open(image_dir / image_name).convert("RGB")
        image.thumbnail((300, 180))

        card = Image.new("RGB", (320, 240), color=(20, 22, 27))
        x = (320 - image.width) // 2
        y = 8
        card.paste(image, (x, y))

        draw = ImageDraw.Draw(card)
        draw.text((8, 192), image_name, fill=(255, 255, 255))
        draw.text((8, 210), f"tags={','.join(row['tags'])}", fill=(197, 215, 255))
        draw.text((8, 226), f"blur={float(row['blur_score']):.1f}", fill=(255, 215, 160))
        thumbs.append(card)

    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * 320, rows * 240), color=(10, 12, 16))
    for index, thumb in enumerate(thumbs):
        canvas.paste(thumb, ((index % cols) * 320, (index // cols) * 240))
    canvas.save(output_path, quality=90)


def main() -> None:
    args = parse_args()
    scene_dir = args.scene_dir.expanduser().resolve()
    image_dir = scene_dir / args.input_subdir
    meta_dir = scene_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    image_paths = list_images(image_dir)

    metrics: list[FrameMetrics] = []
    hashes: list[int] = []
    embeddings: list[np.ndarray] = []

    for image_path in image_paths:
        gray = load_gray_image(image_path)
        blur_score = compute_blur_score(gray)
        brightness_mean, brightness_std, dark_ratio, bright_ratio = compute_exposure_metrics(gray)
        hashes.append(compute_dhash(gray))
        embeddings.append(compute_similarity_embedding(gray))
        metrics.append(
            FrameMetrics(
                image_name=image_path.name,
                blur_score=blur_score,
                brightness_mean=brightness_mean,
                brightness_std=brightness_std,
                dark_ratio=dark_ratio,
                bright_ratio=bright_ratio,
                prev_duplicate_distance=None,
                next_duplicate_distance=None,
                prev_similarity=None,
                next_similarity=None,
            )
        )

    for index, item in enumerate(metrics):
        if index > 0:
            item.prev_duplicate_distance = hamming_distance(hashes[index], hashes[index - 1])
            item.prev_similarity = cosine_similarity(embeddings[index], embeddings[index - 1])
        if index + 1 < len(metrics):
            item.next_duplicate_distance = hamming_distance(hashes[index], hashes[index + 1])
            item.next_similarity = cosine_similarity(embeddings[index], embeddings[index + 1])

    blur_threshold = quantile_threshold(
        [item.blur_score for item in metrics],
        q=args.blur_quantile,
        lower_tail=True,
    )
    dark_mean_threshold = quantile_threshold(
        [item.brightness_mean for item in metrics],
        q=args.exposure_quantile,
        lower_tail=True,
    )
    bright_mean_threshold = quantile_threshold(
        [item.brightness_mean for item in metrics],
        q=args.exposure_quantile,
        lower_tail=False,
    )

    blur_candidates = [
        item.image_name
        for item in metrics
        if item.blur_score <= blur_threshold
    ]
    dark_candidates = [
        item.image_name
        for item in metrics
        if item.brightness_mean <= dark_mean_threshold or item.dark_ratio >= 0.08
    ]
    bright_candidates = [
        item.image_name
        for item in metrics
        if item.brightness_mean >= bright_mean_threshold or item.bright_ratio >= 0.08
    ]

    duplicate_candidates: list[str] = []
    for item in metrics:
        # 这里只把“当前帧与上一帧几乎同帧”的情况记成候选。
        # 不同时看 prev/next, 避免把一整段正常平滑运动都误打成重复。
        is_prev_duplicate = (
            item.prev_duplicate_distance is not None
            and item.prev_similarity is not None
            and item.prev_duplicate_distance <= args.duplicate_distance_threshold
            and item.prev_similarity >= args.duplicate_similarity_threshold
        )
        if is_prev_duplicate:
            duplicate_candidates.append(item.image_name)

    summary = {
        "scene_dir": str(scene_dir),
        "image_dir": str(image_dir),
        "image_count": len(metrics),
        "thresholds": {
            "blur_score_lte": blur_threshold,
            "brightness_mean_lte": dark_mean_threshold,
            "brightness_mean_gte": bright_mean_threshold,
            "duplicate_distance_lte": args.duplicate_distance_threshold,
            "duplicate_similarity_gte": args.duplicate_similarity_threshold,
        },
        "candidate_counts": {
            "blur": len(blur_candidates),
            "dark": len(dark_candidates),
            "bright": len(bright_candidates),
            "duplicate": len(duplicate_candidates),
        },
        "candidates": {
            "blur": blur_candidates,
            "dark": dark_candidates,
            "bright": bright_candidates,
            "duplicate": duplicate_candidates,
        },
        "metrics": [asdict(item) for item in metrics],
    }

    priority_review = build_priority_review_list(
        metrics=metrics,
        blur_candidates=blur_candidates,
        dark_candidates=dark_candidates,
        bright_candidates=bright_candidates,
        duplicate_candidates=duplicate_candidates,
    )
    summary["priority_review"] = priority_review

    json_path = meta_dir / f"{args.output_prefix}_report.json"
    md_path = meta_dir / f"{args.output_prefix}_report.md"
    candidate_path = meta_dir / f"{args.output_prefix}_union_candidates.txt"
    review_path = meta_dir / f"{args.output_prefix}_priority_review.txt"
    contact_sheet_path = meta_dir / f"{args.output_prefix}_priority_review.jpg"

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(
        build_markdown_report(
            scene_dir=scene_dir,
            image_dir=image_dir,
            metrics=metrics,
            blur_candidates=blur_candidates,
            dark_candidates=dark_candidates,
            bright_candidates=bright_candidates,
            duplicate_candidates=duplicate_candidates,
            summary=summary,
        ),
        encoding="utf-8",
    )

    union_candidates = sorted(
        set(blur_candidates) | set(dark_candidates) | set(bright_candidates) | set(duplicate_candidates)
    )
    candidate_path.write_text(
        "\n".join(union_candidates) + ("\n" if union_candidates else ""),
        encoding="utf-8",
    )
    review_path.write_text(
        "\n".join(
            f"{row['image_name']}\ttags={','.join(row['tags'])}\tblur={float(row['blur_score']):.3f}\tmean={float(row['brightness_mean']):.3f}"
            for row in priority_review
        )
        + ("\n" if priority_review else ""),
        encoding="utf-8",
    )
    save_priority_contact_sheet(
        image_dir=image_dir,
        review_rows=priority_review,
        output_path=contact_sheet_path,
    )

    print(
        json.dumps(
            {
                "json_report": str(json_path),
                "markdown_report": str(md_path),
                "union_candidates": str(candidate_path),
                "priority_review": str(review_path),
                "priority_contact_sheet": str(contact_sheet_path),
                "candidate_counts": summary["candidate_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
