#!/usr/bin/env python3
"""Calculate pedestrian-network walking access from population points to grocers."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    ensure_dirs,
    load_config,
    walking_speed_meters_per_minute,
    write_json,
)


def load_qualifying_grocers(paths: dict[str, Path]) -> gpd.GeoDataFrame:
    manual = paths["manual"] / "qualifying_grocers.csv"
    if not manual.exists():
        raise SystemExit(f"Missing {manual}. Create the manually reviewed grocer dataset first.")
    df = pd.read_csv(manual)
    required = {"id", "name", "latitude", "longitude", "qualifies"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"qualifying_grocers.csv missing columns: {missing}")
    df = df[df["qualifies"].astype(str).str.lower().isin(["true", "1", "yes", "y"])].copy()
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["longitude"], df["latitude"])],
        crs="EPSG:4326",
    )
    return gdf


def bin_minutes(minutes: float, thresholds: list[int]) -> str:
    if minutes is None or (isinstance(minutes, float) and math.isnan(minutes)):
        return "unreachable"
    for t in thresholds:
        if minutes <= t:
            return f"<= {t} min"
    return f"> {thresholds[-1]} min"


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    speed_mpm = walking_speed_meters_per_minute(cfg)
    thresholds = list(cfg["walking"]["thresholds_minutes"])
    headline = int(cfg["walking"]["headline_threshold_minutes"])
    snap_max = float(cfg["network"]["snap_max_distance_meters"])

    graphml = paths["processed"] / "network" / "detroit_walk.graphml"
    pop_path = paths["processed"] / "census" / "population_points.geojson"
    bg_path = paths["processed"] / "census" / "block_groups_inhabited.geojson"
    boundary_path = paths["processed"] / "detroit" / "boundary.geojson"

    for p in (graphml, pop_path, bg_path, boundary_path):
        if not p.exists():
            raise SystemExit(f"Missing {p}. Run prior pipeline steps first.")

    print("Loading walk network…")
    G = ox.load_graphml(graphml)
    # Ensure edge lengths exist
    if not any("length" in d for _, _, d in G.edges(data=True)):
        G = ox.distance.add_edge_lengths(G)

    pop = gpd.read_file(pop_path).to_crs(4326)
    bgs = gpd.read_file(bg_path).to_crs(4326)
    grocers = load_qualifying_grocers(paths)
    print(f"Qualifying grocers: {len(grocers)}; population points: {len(pop)}")

    # Project for nearest-node search in meters
    crs = G.graph.get("crs")
    pop_p = pop.to_crs(crs)
    grocers_p = grocers.to_crs(crs)

    print("Snapping grocery stores to network…")
    store_nodes = []
    store_meta = []
    for _, row in grocers_p.iterrows():
        try:
            node = ox.distance.nearest_nodes(G, row.geometry.x, row.geometry.y)
            # Check snap distance
            node_pt = Point(G.nodes[node]["x"], G.nodes[node]["y"])
            dist = row.geometry.distance(node_pt)
            if dist > snap_max:
                print(f"  skip {row.get('name')}: snap distance {dist:.0f}m > {snap_max}m")
                continue
            store_nodes.append(node)
            store_meta.append(row)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip store snap error: {exc}")

    if not store_nodes:
        raise SystemExit("No grocery stores could be snapped to the walk network.")

    # Multi-source Dijkstra from all store nodes
    print("Computing multi-source shortest paths from grocery stores…")
    dist_m = nx.multi_source_dijkstra_path_length(G, set(store_nodes), weight="length")

    print("Measuring access for each population point…")
    minutes_list = []
    nearest_node_dist = []
    origin_nodes = []
    for _, row in pop_p.iterrows():
        try:
            node = ox.distance.nearest_nodes(G, row.geometry.x, row.geometry.y)
            node_pt = Point(G.nodes[node]["x"], G.nodes[node]["y"])
            snap_d = row.geometry.distance(node_pt)
            origin_nodes.append(node)
            nearest_node_dist.append(snap_d)
            if snap_d > snap_max or node not in dist_m:
                minutes_list.append(np.nan)
            else:
                # Include snap distance on both ends approximately via origin snap only;
                # store snap already absorbed into network path from store node.
                path_m = dist_m[node] + snap_d
                minutes_list.append(path_m / speed_mpm)
        except Exception:
            origin_nodes.append(None)
            nearest_node_dist.append(np.nan)
            minutes_list.append(np.nan)

    pop = pop.copy()
    pop["walk_minutes"] = minutes_list
    pop["access_bin"] = [bin_minutes(m, thresholds) for m in minutes_list]
    pop["within_15"] = pop["walk_minutes"] <= headline
    pop["origin_node"] = origin_nodes
    pop["snap_distance_m"] = nearest_node_dist

    # Join minutes back to block group polygons
    bg_access = bgs.merge(
        pop[["GEOID", "walk_minutes", "access_bin", "within_15"]],
        on="GEOID",
        how="left",
    )

    total_pop = int(bg_access["population"].sum())
    within_pop = int(bg_access.loc[bg_access["within_15"] == True, "population"].sum())  # noqa: E712
    outside_pop = total_pop - within_pop
    pct = (100.0 * within_pop / total_pop) if total_pop else 0.0

    # Population-weighted median walking time
    reachable = bg_access[bg_access["walk_minutes"].notna() & (bg_access["population"] > 0)]
    if len(reachable):
        ordered = reachable.sort_values("walk_minutes")
        cum = ordered["population"].cumsum()
        cutoff = ordered["population"].sum() / 2.0
        median_minutes = float(ordered.loc[cum >= cutoff, "walk_minutes"].iloc[0])
    else:
        median_minutes = None

    # Neighborhood accessibility if a neighborhood name field exists later;
    # for MVP, compute by census tract (first 11 chars of GEOID)
    bg_access["tract"] = bg_access["GEOID"].astype(str).str[:11]
    tract_stats = (
        bg_access.groupby("tract")
        .apply(
            lambda g: pd.Series(
                {
                    "population": g["population"].sum(),
                    "pct_within_15": 100.0
                    * g.loc[g["within_15"] == True, "population"].sum()  # noqa: E712
                    / g["population"].sum()
                    if g["population"].sum()
                    else 0.0,
                    "median_walk_minutes": float(
                        g.sort_values("walk_minutes")
                        .assign(c=lambda x: x["population"].cumsum())
                        .loc[lambda x: x["c"] >= x["population"].sum() / 2, "walk_minutes"]
                        .iloc[0]
                    )
                    if g["walk_minutes"].notna().any() and g["population"].sum() > 0
                    else None,
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    inhabited_tracts = tract_stats[tract_stats["population"] >= 200].copy()
    if len(inhabited_tracts):
        lowest = inhabited_tracts.sort_values("pct_within_15").iloc[0]
        highest = inhabited_tracts.sort_values("pct_within_15", ascending=False).iloc[0]
        lowest_tract = {
            "tract": lowest["tract"],
            "pct_within_15": round(float(lowest["pct_within_15"]), 1),
            "population": int(lowest["population"]),
        }
        highest_tract = {
            "tract": highest["tract"],
            "pct_within_15": round(float(highest["pct_within_15"]), 1),
            "population": int(highest["population"]),
        }
    else:
        lowest_tract = highest_tract = None

    bin_summary = []
    for label in [f"<= {t} min" for t in thresholds] + [f"> {thresholds[-1]} min", "unreachable"]:
        sub = bg_access[bg_access["access_bin"] == label]
        bin_summary.append(
            {
                "bin": label,
                "population": int(sub["population"].sum()),
                "block_groups": int(len(sub)),
            }
        )

    summary = {
        "retrieval_date": cfg["project"]["retrieval_date"],
        "walking_speed_mph": cfg["walking"]["speed_mph"],
        "headline_threshold_minutes": headline,
        "total_population": total_pop,
        "residents_within_15": within_pop,
        "residents_outside_15": outside_pop,
        "pct_within_15": round(pct, 1),
        "qualifying_grocery_stores": len(store_meta),
        "median_walk_minutes_pop_weighted": round(median_minutes, 1) if median_minutes is not None else None,
        "lowest_access_tract": lowest_tract,
        "highest_access_tract": highest_tract,
        "bins": bin_summary,
        "assumptions": {
            "network": "OpenStreetMap pedestrian network via OSMnx",
            "routing": "Multi-source Dijkstra on walk graph, length-weighted",
            "population": "ACS 5-year total population at block-group centroids (representative points)",
            "scope": "City of Detroit municipal boundary",
        },
        "limitations": [
            "Does not measure grocery prices, inventory quality, cultural appropriateness, or store hours reliability.",
            "Does not include transit, driving, delivery, sidewalk quality, personal safety, weather, or disability-specific travel times.",
            "Measures geographic pedestrian accessibility, not total food security.",
        ],
    }

    # Outputs
    out_access = paths["outputs"] / "accessibility.geojson"
    bg_out = bg_access.copy()
    bg_out["within_15"] = bg_out["within_15"].fillna(False).astype(bool)
    bg_out.to_file(out_access, driver="GeoJSON")

    grocers_out = gpd.GeoDataFrame(store_meta, crs=grocers_p.crs).to_crs(4326)
    # Ensure expected properties for the map
    for col in ("id", "name", "address", "source", "store_type", "notes", "last_verified"):
        if col not in grocers_out.columns:
            grocers_out[col] = None
    grocers_path = paths["outputs"] / "grocers.geojson"
    grocers_out.to_file(grocers_path, driver="GeoJSON")

    boundary = gpd.read_file(boundary_path)
    boundary.to_file(paths["outputs"] / "boundary.geojson", driver="GeoJSON")

    write_json(paths["outputs"] / "summary.json", summary)
    tract_stats.to_csv(paths["outputs"] / "tract_accessibility.csv", index=False)

    # Precompute light matrix for place-a-store stretch: BG node ids + coords
    scenario = pop[["GEOID", "population", "walk_minutes", "within_15", "origin_node"]].copy()
    scenario["lat"] = pop.geometry.y.values
    scenario["lon"] = pop.geometry.x.values
    write_json(
        paths["outputs"] / "scenario_base.json",
        {
            "speed_mpm": speed_mpm,
            "headline_minutes": headline,
            "total_population": total_pop,
            "residents_within_15": within_pop,
            "pct_within_15": round(pct, 1),
            "points": scenario.replace({np.nan: None}).to_dict(orient="records"),
        },
    )

    print(
        f"Within {headline} min: {pct:.1f}% "
        f"({within_pop:,} / {total_pop:,}); stores={len(store_meta)}"
    )


if __name__ == "__main__":
    main()
