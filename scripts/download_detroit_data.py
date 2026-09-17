#!/usr/bin/env python3
"""Download City of Detroit municipal boundary.

Primary source: U.S. Census Bureau cartographic boundary file for Michigan
places (Detroit place GEOID 2622000). This is reproducible and stable.

Optional ArcGIS / Detroit Open Data endpoints are tried as secondary sources
when available.
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ensure_dirs, load_config, retrieval_meta, write_json

DETROIT_PLACE_GEOID = "2622000"

CENSUS_PLACE_URLS = [
    "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_26_place_500k.zip",
    "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_26_place_500k.zip",
    "https://www2.census.gov/geo/tiger/GENZ2021/shp/cb_2021_26_place_500k.zip",
]

ARCGIS_CANDIDATES = [
    "https://services2.arcgis.com/qvkbeam7Wirqt0Vp/arcgis/rest/services/City_of_Detroit_Boundary/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson",
    "https://gis.detroitmi.gov/arcgis/rest/services/OpenData/Boundaries/MapServer/0/query?where=1%3D1&outFields=*&f=geojson",
]


def fetch_from_census_places(dest_dir: Path) -> gpd.GeoDataFrame:
    dest_dir.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for url in CENSUS_PLACE_URLS:
        try:
            print(f"Downloading Census places: {url}")
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            zip_path = dest_dir / Path(url).name
            zip_path.write_bytes(r.content)
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                zf.extractall(dest_dir / zip_path.stem)
            gdf = gpd.read_file(dest_dir / zip_path.stem).to_crs(4326)
            det = gdf[gdf["GEOID"].astype(str) == DETROIT_PLACE_GEOID].copy()
            if det.empty:
                det = gdf[(gdf["NAME"] == "Detroit") & (gdf["NAMELSAD"].str.contains("city", case=False, na=False))].copy()
            if det.empty:
                raise ValueError("Detroit place not found in Census file")
            det = det.head(1)
            out = gpd.GeoDataFrame(
                {
                    "name": ["City of Detroit"],
                    "geoid": [str(det.iloc[0]["GEOID"])],
                    "source_url": [url],
                    "geometry": [det.iloc[0].geometry],
                },
                crs="EPSG:4326",
            )
            return out
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"  failed: {exc}")
    raise RuntimeError(f"Census place download failed: {last_err}")


def fetch_from_arcgis() -> gpd.GeoDataFrame | None:
    for url in ARCGIS_CANDIDATES:
        try:
            print(f"Trying ArcGIS boundary: {url}")
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            gdf = gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")
            if gdf.empty:
                continue
            if len(gdf) > 1:
                gdf["area_tmp"] = gdf.to_crs(3857).area
                gdf = gdf.sort_values("area_tmp", ascending=False).head(1).drop(columns=["area_tmp"])
            return gpd.GeoDataFrame(
                {
                    "name": ["City of Detroit"],
                    "geoid": [DETROIT_PLACE_GEOID],
                    "source_url": [url],
                    "geometry": [gdf.iloc[0].geometry],
                },
                crs="EPSG:4326",
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  failed: {exc}")
    return None


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    print("Downloading Detroit municipal boundary…")
    boundary = fetch_from_census_places(paths["raw"] / "detroit")
    # Prefer Census for reproducibility; ArcGIS only logged as optional check
    _ = fetch_from_arcgis()

    out = paths["processed"] / "detroit" / "boundary.geojson"
    boundary.to_file(out, driver="GeoJSON")
    write_json(
        paths["raw"] / "detroit" / "boundary_meta.json",
        retrieval_meta(
            cfg,
            "detroit_boundary",
            {
                "feature_count": len(boundary),
                "source_url": boundary.iloc[0]["source_url"],
                "geoid": boundary.iloc[0]["geoid"],
                "note": "Census place boundary for Detroit city (GEOID 2622000).",
            },
        ),
    )
    # Update config note in printed output
    print(f"Wrote {out}")
    print(f"Bounds: {boundary.total_bounds}")


if __name__ == "__main__":
    main()
