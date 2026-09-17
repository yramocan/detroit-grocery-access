#!/usr/bin/env python3
"""Build and cache the OpenStreetMap pedestrian network for Detroit."""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import osmnx as ox

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ensure_dirs, load_config, retrieval_meta, write_json


def main() -> None:
    cfg = load_config()
    paths = ensure_dirs(cfg)
    boundary_path = paths["processed"] / "detroit" / "boundary.geojson"
    if not boundary_path.exists():
        raise SystemExit("Missing Detroit boundary. Run download_detroit_data.py first.")

    boundary = gpd.read_file(boundary_path).to_crs(4326)
    buffer_m = float(cfg["network"]["download_buffer_meters"])
    poly = boundary.to_crs(3857).buffer(buffer_m).to_crs(4326).union_all()

    print("Downloading OSM walk network (this may take several minutes)…")
    ox.settings.use_cache = True
    ox.settings.log_console = True
    G = ox.graph_from_polygon(poly, network_type=cfg["network"]["network_type"], simplify=True)
    G = ox.project_graph(G)  # project for accurate lengths

    graphml = paths["processed"] / "network" / "detroit_walk.graphml"
    ox.save_graphml(G, graphml)

    # Optional debug export (large): set EXPORT_WALK_EDGES=1
    import os

    if os.environ.get("EXPORT_WALK_EDGES") == "1":
        edges = ox.graph_to_gdfs(G, nodes=False).to_crs(4326)
        edges_out = paths["processed"] / "network" / "walk_edges.geojson"
        keep = [c for c in ("osmid", "name", "highway", "length", "geometry") if c in edges.columns]
        edges[keep].to_file(edges_out, driver="GeoJSON")
        print(f"Wrote debug edges → {edges_out}")

    write_json(
        paths["raw"] / "network" / "meta.json",
        retrieval_meta(
            cfg,
            "osm",
            {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "crs": str(G.graph.get("crs")),
                "network_type": cfg["network"]["network_type"],
                "buffer_meters": buffer_m,
            },
        ),
    )
    print(f"Saved network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges → {graphml}")


if __name__ == "__main__":
    main()
