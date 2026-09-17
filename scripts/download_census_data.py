#!/usr/bin/env python3
"""Download Census TIGER block groups and ACS population for Detroit.

Population source preference:
1. Census Reporter API (no key required) for ACS B01003 within Detroit place
2. Official Census API if CENSUS_API_KEY is set
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ensure_dirs, load_config, retrieval_meta, write_json


def download_tiger_block_groups(state_fips: str, year: int, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    years_to_try = [year, year + 1, year - 1, 2024, 2023, 2022]
    last_err: Exception | None = None
    for y in years_to_try:
        url = f"https://www2.census.gov/geo/tiger/TIGER{y}/BG/tl_{y}_{state_fips}_bg.zip"
        zip_path = dest_dir / f"tl_{y}_{state_fips}_bg.zip"
        if zip_path.exists() and zip_path.stat().st_size > 1_000_000:
            print(f"Using cached {zip_path.name}")
            return zip_path
        try:
            print(f"Downloading {url}")
            r = requests.get(url, timeout=300)
            r.raise_for_status()
            zip_path.write_bytes(r.content)
            return zip_path
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"  failed: {exc}")
    raise RuntimeError(f"Could not download TIGER block groups: {last_err}")


def fetch_acs_population_census_reporter(acs_year: int) -> pd.DataFrame:
    """ACS total population for block groups inside Detroit place via Census Reporter."""
    # latest release for place Detroit; still records release metadata
    url = (
        "https://api.censusreporter.org/1.0/data/show/latest"
        "?table_ids=B01003&geo_ids=150|16000US2622000"
    )
    print(f"Fetching ACS population via Census Reporter (target year ~{acs_year})…")
    r = requests.get(url, timeout=180, headers={"User-Agent": "DetroitGroceryAccessMVP/0.1"})
    r.raise_for_status()
    payload = r.json()
    release = payload.get("release", {})
    rows = []
    for geoid_full, tables in payload.get("data", {}).items():
        # geoid_full like 15000US261635001001 → GEOID 261635001001
        geoid = geoid_full.replace("15000US", "")
        est = tables.get("B01003", {}).get("estimate", {}).get("B01003001")
        if est is None:
            continue
        rows.append(
            {
                "GEOID": geoid,
                "NAME": geoid_full,
                "population": int(est),
                "acs_year": release.get("years", acs_year),
                "acs_release": release.get("id") or release.get("name"),
            }
        )
    if not rows:
        raise RuntimeError("Census Reporter returned no block-group population rows")
    return pd.DataFrame(rows)


def fetch_acs_population_census_api(
    state_fips: str, county_fips: str, year: int, variable: str, api_key: str
) -> pd.DataFrame:
    years_to_try = [year, year - 1, year - 2, 2023, 2022, 2021]
    last_err: Exception | None = None
    for y in years_to_try:
        url = (
            f"https://api.census.gov/data/{y}/acs/acs5"
            f"?get=NAME,{variable}&for=block%20group:*"
            f"&in=state:{state_fips}%20county:{county_fips}&key={api_key}"
        )
        try:
            print(f"Fetching ACS {y} via Census API…")
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            rows = r.json()
            header, *body = rows
            df = pd.DataFrame(body, columns=header)
            df["GEOID"] = df["state"] + df["county"] + df["tract"] + df["block group"]
            df["population"] = pd.to_numeric(df[variable], errors="coerce").fillna(0).astype(int)
            df["acs_year"] = y
            return df[["GEOID", "NAME", "population", "acs_year"]]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"  failed: {exc}")
    raise RuntimeError(f"Could not fetch ACS population: {last_err}")


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    pop_cfg = cfg["population"]
    state = pop_cfg["state_fips"]
    county = pop_cfg["county_fips"]
    year = int(pop_cfg["acs_year"])
    variable = pop_cfg["population_variable"]

    boundary_path = paths["processed"] / "detroit" / "boundary.geojson"
    if not boundary_path.exists():
        raise SystemExit("Missing Detroit boundary. Run download_detroit_data.py first.")
    boundary = gpd.read_file(boundary_path).to_crs(4326)

    zip_path = download_tiger_block_groups(state, year, paths["raw"] / "census")
    print("Reading block groups…")
    bg = gpd.read_file(f"zip://{zip_path}").to_crs(4326)
    print("Clipping to Detroit boundary…")
    detroit_bg = gpd.sjoin(bg, boundary[["geometry"]], predicate="intersects", how="inner")
    detroit_bg = detroit_bg.drop(columns=[c for c in detroit_bg.columns if c.startswith("index_")])
    detroit_bg = detroit_bg.drop_duplicates(subset=["GEOID"]).copy()

    api_key = os.environ.get("CENSUS_API_KEY", "").strip()
    pop_source = "census_reporter"
    try:
        pop = fetch_acs_population_census_reporter(year)
    except Exception as exc:  # noqa: BLE001
        print(f"Census Reporter failed ({exc}); trying Census API…")
        if not api_key:
            raise SystemExit(
                "Population download failed. Set CENSUS_API_KEY or fix Census Reporter access."
            ) from exc
        pop = fetch_acs_population_census_api(state, county, year, variable, api_key)
        pop_source = "census_api"

    merged = detroit_bg.merge(pop, on="GEOID", how="left")
    merged["population"] = merged["population"].fillna(0).astype(int)

    out_all = paths["processed"] / "census" / "block_groups.geojson"
    keep_cols = ["GEOID", "NAME", "population", "acs_year", "ALAND", "AWATER", "geometry"]
    keep_cols = [c for c in keep_cols if c in merged.columns]
    result = merged[keep_cols].copy()
    result.to_file(out_all, driver="GeoJSON")

    inhabited = result[result["population"] > 0].copy()
    inhabited_path = paths["processed"] / "census" / "block_groups_inhabited.geojson"
    inhabited.to_file(inhabited_path, driver="GeoJSON")

    pts = inhabited.copy()
    pts["geometry"] = pts.geometry.representative_point()
    pts_path = paths["processed"] / "census" / "population_points.geojson"
    pts.to_file(pts_path, driver="GeoJSON")

    write_json(
        paths["raw"] / "census" / "meta.json",
        retrieval_meta(
            cfg,
            "census_acs",
            {
                "tiger_zip": zip_path.name,
                "population_source": pop_source,
                "block_groups_in_detroit": int(len(result)),
                "inhabited_block_groups": int(len(inhabited)),
                "total_population": int(result["population"].sum()),
                "acs_year_used": str(result["acs_year"].dropna().iloc[0])
                if result["acs_year"].notna().any()
                else None,
            },
        ),
    )
    print(
        f"Wrote {len(result)} block groups "
        f"({len(inhabited)} inhabited, pop={int(result['population'].sum()):,})"
    )


if __name__ == "__main__":
    main()
