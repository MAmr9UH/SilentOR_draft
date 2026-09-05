"""Named experiment configuration loader."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_DIR = HERE / "configs"


def load_config(name: str) -> dict:
    path = CONFIG_DIR / f"{name}.json"
    if not path.is_file():
        raise ValueError(f"unknown configuration {name!r}; available: track_b")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("name") != name:
        raise ValueError(f"configuration name mismatch in {path}")
    return cfg
