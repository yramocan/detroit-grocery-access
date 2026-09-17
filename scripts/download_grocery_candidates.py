#!/usr/bin/env python3
"""Download grocery/supermarket candidate locations from OpenStreetMap."""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ensure_dirs, load_config, retrieval_meta, write_json


TAGS = {
    "shop": ["supermarket", "grocery", "greengrocer", "convenience", "butcher", "bakery"],
}


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    boundary_path = paths["processed"] / "detroit" / "boundary.geojson"
    if not boundary_path.exists():
        raise SystemExit("Missing Detroit boundary. Run download_detroit_data.py first.")

    boundary = gpd.read_file(boundary_path).to_crs(4326)
    # Buffer slightly so near-boundary stores are candidates for future inclusion
    buffer_m = float(cfg["geography"]["outside_store_buffer_meters"])
    poly = boundary.to_crs(3857).buffer(buffer_m).to_crs(4326).union_all()

    print("Querying OpenStreetMap for grocery-related shops…")
    ox.settings.use_cache = True
    ox.settings.log_console = False
    gdf = ox.features_from_polygon(poly, TAGS)
    if gdf.empty:
        raise RuntimeError("No OSM grocery features returned.")

    gdf = gdf.reset_index()
    # Prefer points; convert polygons to centroids
    geoms = []
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            geoms.append(None)
        elif geom.geom_type == "Point":
            geoms.append(geom)
        else:
            geoms.append(geom.representative_point())
    gdf = gdf.copy()
    gdf["geometry"] = geoms
    gdf = gdf[gdf.geometry.notna()].set_crs(4326)

    name_col = "name" if "name" in gdf.columns else None
    shop_col = "shop" if "shop" in gdf.columns else None
    addr_parts = [c for c in ("addr:housenumber", "addr:street", "addr:city") if c in gdf.columns]

    rows = []
    for i, row in gdf.iterrows():
        address = ""
        if addr_parts:
            address = " ".join(str(row.get(c) or "") for c in addr_parts).strip()
        rows.append(
            {
                "candidate_id": f"osm-{row.get('osmid', i)}",
                "name": (row.get(name_col) if name_col else None) or "Unnamed",
                "address": address or None,
                "latitude": float(row.geometry.y),
                "longitude": float(row.geometry.x),
                "source": "OpenStreetMap",
                "osm_shop": row.get(shop_col) if shop_col else None,
                "osm_id": row.get("osmid"),
                "geometry": row.geometry,
            }
        )

    out = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    # Deduplicate near-identical coordinates
    out["lat_r"] = out.geometry.y.round(4)
    out["lon_r"] = out.geometry.x.round(4)
    out = out.drop_duplicates(subset=["name", "lat_r", "lon_r"]).drop(columns=["lat_r", "lon_r"])

    candidate_path = paths["processed"] / "grocery" / "candidates_osm.geojson"
    out.to_file(candidate_path, driver="GeoJSON")

    # Also write a CSV seed for manual review
    csv_path = paths["processed"] / "grocery" / "candidates_osm.csv"
    pd.DataFrame(
        {
            "candidate_id": out["candidate_id"],
            "name": out["name"],
            "address": out["address"],
            "latitude": out["latitude"],
            "longitude": out["longitude"],
            "source": out["source"],
            "osm_shop": out["osm_shop"],
            "qualifies": "",
            "store_type": "",
            "notes": "",
        }
    ).to_csv(csv_path, index=False)

    write_json(
        paths["raw"] / "grocery" / "osm_meta.json",
        retrieval_meta(cfg, "osm", {"candidate_count": len(out), "tags": TAGS}),
    )
    print(f"Wrote {len(out)} OSM grocery candidates → {candidate_path}")


if __name__ == "__main__":
    main()
