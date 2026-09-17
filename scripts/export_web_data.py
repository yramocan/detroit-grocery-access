#!/usr/bin/env python3
"""Copy analysis outputs into the web app public/data directory."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ROOT, ensure_dirs, load_config


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    dest = ROOT / "web" / "public" / "data"
    dest.mkdir(parents=True, exist_ok=True)
    files = [
        "accessibility.geojson",
        "grocers.geojson",
        "boundary.geojson",
        "summary.json",
        "scenario_base.json",
    ]
    for name in files:
        src = paths["outputs"] / name
        if not src.exists():
            raise SystemExit(f"Missing {src}. Run calculate_accessibility.py first.")
        shutil.copy2(src, dest / name)
        print(f"Copied {name} → web/public/data/")


if __name__ == "__main__":
    main()
