#!/usr/bin/env python3
"""Run the full MVP data + analysis pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "download_detroit_data.py",
    "download_census_data.py",
    "download_dfm_grocers.py",
    "download_grocery_candidates.py",
    "build_qualifying_grocers.py",
    "build_walk_network.py",
    "calculate_accessibility.py",
]


def run(script: str) -> None:
    path = ROOT / "scripts" / script
    print(f"\n=== {script} ===")
    subprocess.run([sys.executable, str(path)], check=True, cwd=ROOT)


def main() -> None:
    only = sys.argv[1:] if len(sys.argv) > 1 else SCRIPTS
    for script in only:
        if not script.endswith(".py"):
            script = f"{script}.py"
        run(script)
    print("\nPipeline complete. Outputs in outputs/")


if __name__ == "__main__":
    main()
