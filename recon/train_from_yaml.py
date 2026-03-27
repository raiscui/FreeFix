from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf

from recon.trainer import Config, main


# =============================================================================
# YAML 训练入口
# -----------------------------------------------------------------------------
# `recon.trainer` 当前默认只接受 tyro 命令行参数。
# 这个脚本补一个轻量入口, 让我们可以把可复现训练参数放进 YAML,
# 同时保留少量命令行 override, 方便做 smoke test 或临时改输出目录。
# =============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 YAML 配置启动 recon.trainer。")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="YAML 配置路径, 例如 exp_cfg/my4/recon_my4.yaml",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        help="按 OmegaConf dotlist 方式覆盖配置, 例如 --set max_steps=1 --set result_dir=outputs/tmp",
    )
    return parser.parse_args()


def load_config(config_path: Path, overrides: list[str]) -> Config:
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    yaml_cfg = OmegaConf.load(config_path)
    if overrides:
        yaml_cfg = OmegaConf.merge(yaml_cfg, OmegaConf.from_dotlist(overrides))

    payload = OmegaConf.to_container(yaml_cfg, resolve=True)
    if not isinstance(payload, dict):
        raise TypeError(f"配置内容不是映射结构: {config_path}")

    # 只把 Config 真正支持的字段传进去, 避免未来 YAML 里混入注释型辅助键时直接报错。
    valid_fields = set(Config.__dataclass_fields__.keys())
    config_kwargs: dict[str, Any] = {key: value for key, value in payload.items() if key in valid_fields}
    unknown_keys = sorted(set(payload.keys()) - valid_fields)
    if unknown_keys:
        raise KeyError(f"配置里包含 trainer 不认识的字段: {unknown_keys}")

    return Config(**config_kwargs)


def run() -> None:
    args = parse_args()
    cfg = load_config(args.config, args.set)
    main(cfg)


if __name__ == "__main__":
    run()
