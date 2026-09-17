"""Shared helpers for the Detroit grocery access pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or ROOT / "config.yaml"
    with cfg_path.open() as f:
        return yaml.safe_load(f)


def ensure_dirs(cfg: dict[str, Any] | None = None) -> dict[str, Path]:
    cfg = cfg or load_config()
    paths = {
        "root": ROOT,
        "raw": ROOT / cfg["paths"]["raw"],
        "processed": ROOT / cfg["paths"]["processed"],
        "manual": ROOT / cfg["paths"]["manual"],
        "outputs": ROOT / cfg["paths"]["outputs"],
        "scripts": ROOT / "scripts",
    }
    for key in ("raw", "processed", "manual", "outputs"):
        paths[key].mkdir(parents=True, exist_ok=True)
        for sub in ("detroit", "census", "grocery", "network"):
            if key in ("raw", "processed"):
                (paths[key] / sub).mkdir(parents=True, exist_ok=True)
    return paths


def walking_speed_meters_per_minute(cfg: dict[str, Any]) -> float:
    mph = float(cfg["walking"]["speed_mph"])
    # 1 mile = 1609.344 meters; minutes per hour = 60
    return (mph * 1609.344) / 60.0


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def retrieval_meta(cfg: dict[str, Any], source_key: str, extra: dict | None = None) -> dict:
    meta = {
        "retrieval_date": cfg["project"]["retrieval_date"],
        "source": cfg.get("data_sources", {}).get(source_key, {}),
    }
    if extra:
        meta.update(extra)
    return meta
