#!/usr/bin/env python3
"""Build data/manual/qualifying_grocers.csv from Detroit Food Map full-line stores.

Primary source: Detroit Food Map Initiative master list (ground-truthed full-line
grocers). Adds placeholder columns for NEMS-S availability / price / quality
scores so later partnership data can be joined without schema churn.

OSM candidates remain available under data/processed/grocery/ for comparison,
but do not drive the headline qualifying set once DFM data is present.
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ensure_dirs, load_config


NEMS_PLACEHOLDER_NOTE = (
    "NEMS availability/price/quality placeholders pending Detroit Food Map / "
    "Great Grocer partnership data. Open DFM CSV confirms full-line status only."
)


def _clean_str(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _flag01(value) -> str:
    if pd.isna(value):
        return "unknown"
    try:
        return "yes" if float(value) == 1.0 else "no"
    except (TypeError, ValueError):
        text = str(value).strip().lower()
        if text in {"1", "y", "yes", "true"}:
            return "yes"
        if text in {"0", "n", "no", "false"}:
            return "no"
        return "unknown"


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    dfm_path = paths["processed"] / "grocery" / "dfm_full_line_grocers.csv"
    if not dfm_path.exists():
        # Allow raw download path as fallback
        raw = paths["raw"] / "grocery" / "dfm_stores_2024.csv"
        if not raw.exists():
            raise SystemExit("Missing DFM grocery list. Run download_dfm_grocers.py first.")
        dfm_path = raw

    boundary_path = paths["processed"] / "detroit" / "boundary.geojson"
    if not boundary_path.exists():
        raise SystemExit("Missing Detroit boundary. Run download_detroit_data.py first.")

    dfm = pd.read_csv(dfm_path)
    # Normalize expected columns across 2023/2024 schemas
    rename = {
        "Name": "name",
        "Address": "address",
        "City": "city",
        "Zipcode": "zipcode",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "DFM Type": "dfm_type",
        "Current Status": "current_status",
        "LICENSE": "license",
        "Community Score": "dfm_community_score",
        "SNAP": "snap",
        "WIC": "wic",
        "Green Grocer": "green_grocer",
        "GGP18": "ggp18",
        "GGP21": "ggp21",
        "Sq Ft by 1000": "sq_ft_thousands",
        "AKA": "aka",
        "NOTES": "dfm_notes",
        "Phone": "phone",
    }
    dfm = dfm.rename(columns={k: v for k, v in rename.items() if k in dfm.columns})

    required = {"name", "latitude", "longitude"}
    missing = required - set(dfm.columns)
    if missing:
        raise SystemExit(f"DFM file missing required columns: {missing}")

    # Keep open full-line stores; 2024 file is already OPEN/Grocery/DETROIT
    if "current_status" in dfm.columns:
        dfm = dfm[dfm["current_status"].astype(str).str.upper().eq("OPEN")].copy()
    if "city" in dfm.columns:
        dfm = dfm[dfm["city"].astype(str).str.upper().eq("DETROIT")].copy()

    dfm = dfm.dropna(subset=["latitude", "longitude"]).copy()
    gdf = gpd.GeoDataFrame(
        dfm,
        geometry=gpd.points_from_xy(dfm["longitude"], dfm["latitude"]),
        crs="EPSG:4326",
    )
    boundary = gpd.read_file(boundary_path).to_crs(4326)
    gdf = gpd.sjoin(gdf, boundary[["geometry"]], predicate="intersects", how="inner")
    gdf = gdf.drop(columns=[c for c in gdf.columns if c.startswith("index_")]).drop_duplicates(
        subset=["latitude", "longitude", "name"]
    )

    rows = []
    for i, row in gdf.iterrows():
        license_id = _clean_str(row.get("license"))
        store_id = f"dfm-{license_id}" if license_id else f"dfm-{i}"
        # Strip zero-width chars sometimes present in DFM license fields
        store_id = "".join(ch for ch in store_id if ch.isprintable())

        address = _clean_str(row.get("address"))
        city = _clean_str(row.get("city")) or "Detroit"
        zipcode = _clean_str(row.get("zipcode"))
        full_address = ", ".join(p for p in (address, city, "MI", zipcode) if p)

        community = row.get("dfm_community_score")
        community_txt = "" if pd.isna(community) else str(community)

        notes_parts = [
            "Detroit Food Map full-line grocery (ground-truthed).",
            NEMS_PLACEHOLDER_NOTE,
        ]
        if community_txt:
            notes_parts.append(f"DFM community score: {community_txt}.")
        aka = _clean_str(row.get("aka"))
        if aka:
            notes_parts.append(f"AKA: {aka}.")
        dfm_notes = _clean_str(row.get("dfm_notes"))
        if dfm_notes:
            notes_parts.append(dfm_notes)

        rows.append(
            {
                "id": store_id,
                "name": _clean_str(row.get("name")) or "Unnamed DFM grocery",
                "address": full_address,
                "latitude": round(float(row["latitude"]), 6),
                "longitude": round(float(row["longitude"]), 6),
                "source": "Detroit Food Map Initiative (DetroitData)",
                "qualifies": True,
                "store_type": "full_line_grocery",
                "adequacy_tier": "assortment_only",
                "price_concern": "unknown",
                "quality_concern": "unknown",
                # NEMS-S placeholders (to be filled from partnership / audit data)
                "nems_availability": "",
                "nems_price": "",
                "nems_quality": "",
                "nems_total": "",
                "nems_survey_year": "",
                "nems_status": "pending",
                # Useful open DFM attributes
                "dfm_community_score": community_txt,
                "snap": _flag01(row.get("snap")),
                "wic": _flag01(row.get("wic")),
                "green_grocer": _flag01(row.get("green_grocer")),
                "ggp18": _flag01(row.get("ggp18")),
                "ggp21": _flag01(row.get("ggp21")),
                "sq_ft_thousands": "" if pd.isna(row.get("sq_ft_thousands")) else str(row.get("sq_ft_thousands")),
                "notes": " ".join(notes_parts),
                "reviewer_notes": (
                    "Primary qualifying set from DFM full-line list. "
                    "Assortment confirmed by DFM methodology; quality/price not scored in open CSV."
                ),
                "last_verified": cfg["project"]["retrieval_date"],
            }
        )

    # Keep a documented exclusion example for rubric clarity
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
            "nems_availability": "",
            "nems_price": "",
            "nems_quality": "",
            "nems_total": "",
            "nems_survey_year": "",
            "nems_status": "not_applicable",
            "dfm_community_score": "",
            "snap": "unknown",
            "wic": "unknown",
            "green_grocer": "no",
            "ggp18": "no",
            "ggp21": "no",
            "sq_ft_thousands": "",
            "notes": "Excluded: pharmacy — not a grocery trip destination.",
            "reviewer_notes": "Excluded: pharmacy — not a grocery trip destination.",
            "last_verified": cfg["project"]["retrieval_date"],
        }
    )

    out = pd.DataFrame(rows)
    out_path = paths["manual"] / "qualifying_grocers.csv"
    out.to_csv(out_path, index=False)
    n_qual = int(out["qualifies"].astype(str).str.lower().isin(["true", "1", "yes"]).sum())
    print(f"Wrote {out_path}: {n_qual} qualifying DFM full-line stores (+ exclusion examples)")


if __name__ == "__main__":
    main()
