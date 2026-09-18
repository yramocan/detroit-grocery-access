#!/usr/bin/env python3
"""Download Detroit Food Map full-line grocery store master lists.

Source: DetroitData / Detroit Food Map Initiative (CC BY)
https://detroitdata.org/dataset/full-line-grocery-stores
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ensure_dirs, load_config, retrieval_meta, write_json

DFM_PACKAGE = "https://detroitdata.org/api/3/action/package_show?id=full-line-grocery-stores"
FALLBACK_URLS = {
    "2024": (
        "https://detroitdata.org/dataset/5a9fca49-7f45-4f36-a141-b4a8eb1d4f1b/"
        "resource/daa5088a-950d-417e-b40d-819c49130941/download/"
        "dfm-stores-master-dfm_grocery_062424.csv"
    ),
    "2023": (
        "https://detroitdata.org/dataset/5a9fca49-7f45-4f36-a141-b4a8eb1d4f1b/"
        "resource/ae1982ac-682f-4587-9014-e7d995a3f32a/download/"
        "dfm-stores-master-dfm072523.csv"
    ),
}


def resolve_resources() -> list[dict]:
    try:
        r = requests.get(DFM_PACKAGE, timeout=60)
        r.raise_for_status()
        payload = r.json()
        resources = payload["result"]["resources"]
        out = []
        for res in resources:
            if str(res.get("format", "")).upper() != "CSV":
                continue
            out.append(
                {
                    "name": res.get("name"),
                    "url": res.get("url"),
                    "id": res.get("id"),
                    "last_modified": res.get("last_modified"),
                    "size": res.get("size"),
                }
            )
        if out:
            return out
    except Exception as exc:  # noqa: BLE001
        print(f"CKAN package lookup failed ({exc}); using fallback URLs")
    return [
        {"name": f"DFM STORES MASTER LIST {year}", "url": url, "id": None, "last_modified": None, "size": None}
        for year, url in FALLBACK_URLS.items()
    ]


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    dest = paths["raw"] / "grocery"
    dest.mkdir(parents=True, exist_ok=True)

    resources = resolve_resources()
    saved = []
    for res in resources:
        url = res["url"]
        label = (res.get("name") or "dfm").lower().replace(" ", "_")
        year = "2024" if "2024" in label or "062424" in url else "2023" if "2023" in label or "072523" in url else "unknown"
        out_path = dest / f"dfm_stores_{year}.csv"
        print(f"Downloading {res.get('name')} → {out_path.name}")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        out_path.write_bytes(r.content)
        df = pd.read_csv(out_path)
        saved.append(
            {
                "file": out_path.name,
                "rows": int(len(df)),
                "columns": list(df.columns),
                "source_name": res.get("name"),
                "source_url": url,
                "last_modified": res.get("last_modified"),
            }
        )
        print(f"  {len(df)} rows, {len(df.columns)} columns")

    # Prefer newest year for processed copy
    preferred = dest / "dfm_stores_2024.csv"
    if not preferred.exists():
        preferred = next(dest.glob("dfm_stores_*.csv"))
    processed = paths["processed"] / "grocery" / "dfm_full_line_grocers.csv"
    df = pd.read_csv(preferred)
    df.to_csv(processed, index=False)

    write_json(
        dest / "dfm_meta.json",
        retrieval_meta(
            cfg,
            "detroit_food_map",
            {
                "package": "full-line-grocery-stores",
                "license": "CC BY",
                "files": saved,
                "processed_copy": str(processed.relative_to(paths["root"])),
                "notes": (
                    "Ground-truthed full-line grocery stores from Detroit Food Map Initiative. "
                    "NEMS availability/price/quality scores are collected by DFM/Great Grocer "
                    "but are not fully published in this open CSV; placeholders are added downstream."
                ),
            },
        ),
    )
    print(f"Wrote processed copy → {processed}")


if __name__ == "__main__":
    main()
