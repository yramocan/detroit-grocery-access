#!/usr/bin/env python3
"""Rebuild data/manual/qualifying_grocers.csv from OSM candidates + name screening.

This encodes the MVP manual-review rules in a reproducible script so the CSV
can be refreshed after re-downloading OSM candidates. Reviewers should still
edit the CSV for field verification.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ensure_dirs, load_config

EXCLUDE = re.compile(
    r"liquor|party\s*store|mini\s*mart|gas|pharmacy|dollar|cvs|walgreens|7[\-\s]?eleven|"
    r"family\s*dollar|dollar\s*general|smoke|cannabis|beer\s*depot|wine|"
    r"gordon\s*food\s*service|\bgfs\b|warehouse",
    re.I,
)


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    boundary = gpd.read_file(paths["processed"] / "detroit" / "boundary.geojson").to_crs(4326)
    candidates = gpd.read_file(paths["processed"] / "grocery" / "candidates_osm.geojson")
    candidates = gpd.sjoin(candidates, boundary[["geometry"]], predicate="intersects", how="inner")
    candidates = candidates.drop(
        columns=[c for c in candidates.columns if c.startswith("index_")]
    ).drop_duplicates(subset=["candidate_id"])

    base = candidates[candidates["osm_shop"].isin(["supermarket", "grocery"])].copy()
    rows = []
    for _, r in base.iterrows():
        raw = r["name"]
        name = str(raw).strip() if pd.notna(raw) else ""
        osm_id = r["osm_id"]
        if not name or name.lower() == "nan":
            name = f"Unnamed supermarket (OSM {osm_id})"
            qualifies = True
            notes = "OSM supermarket without name; included pending field verification."
            store_type = "supermarket_unnamed"
        elif EXCLUDE.search(name):
            qualifies = False
            notes = "Excluded by rubric keywords (liquor/convenience/warehouse/etc.)."
            store_type = "excluded"
        else:
            qualifies = True
            notes = "OSM supermarket/grocery tag; screened by name against MVP rubric."
            store_type = "supermarket" if r["osm_shop"] == "supermarket" else "grocery"

        rows.append(
            {
                "id": f"osm-{osm_id}" if pd.notna(osm_id) else f"osm-row-{_}",
                "name": name,
                "address": r["address"] if pd.notna(r.get("address")) else "",
                "latitude": round(float(r["latitude"]), 6),
                "longitude": round(float(r["longitude"]), 6),
                "source": "OpenStreetMap + manual review",
                "qualifies": qualifies,
                "store_type": store_type,
                "adequacy_tier": "assortment_only" if qualifies else "excluded",
                "price_concern": "unknown",
                "quality_concern": "unknown",
                "notes": notes,
                "reviewer_notes": (
                    "V1 assortment screen only. Quality and price not evaluated."
                    if qualifies
                    else notes
                ),
                "last_verified": cfg["project"]["retrieval_date"],
            }
        )

    rows.append(
        {
            "id": "ex-cvs",
            "name": "CVS Pharmacy (exclusion example)",
            "address": "Detroit, MI",
            "latitude": 42.3315,
            "longitude": -83.0465,
            "source": "Manual review",
            "qualifies": False,
            "store_type": "pharmacy",
            "adequacy_tier": "excluded",
            "price_concern": "unknown",
            "quality_concern": "unknown",
            "notes": "Excluded: pharmacy — not a grocery trip destination.",
            "reviewer_notes": "Excluded: pharmacy — not a grocery trip destination.",
            "last_verified": cfg["project"]["retrieval_date"],
        }
    )

    df = pd.DataFrame(rows)
    df["lat_r"] = df["latitude"].round(3)
    df["lon_r"] = df["longitude"].round(3)
    df = df.sort_values(["qualifies", "name"], ascending=[False, True])
    df = df.drop_duplicates(subset=["lat_r", "lon_r"], keep="first").drop(columns=["lat_r", "lon_r"])
    out = paths["manual"] / "qualifying_grocers.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out}: {int(df['qualifies'].sum())} qualifying / {len(df)} rows")


if __name__ == "__main__":
    main()
