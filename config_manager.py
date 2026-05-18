from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from filters import FilterConfig, default_filter_config


def load_filter_config(config_path: Path) -> FilterConfig:
    if not config_path.exists():
        cfg = default_filter_config()
        save_filter_config(config_path, cfg)
        return cfg

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return FilterConfig(**data)


def save_filter_config(config_path: Path, cfg: FilterConfig) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
