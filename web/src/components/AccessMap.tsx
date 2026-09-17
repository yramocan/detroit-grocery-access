"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, Map, Popup, MapMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  ScenarioBase,
  Summary,
  estimateWalkMinutes,
  formatNumber,
} from "@/lib/types";

type Props = {
  summary: Summary;
  scenario: ScenarioBase;
};

type ScenarioResult = {
  lng: number;
  lat: number;
  newlyServed: number;
  newWithin: number;
  newPct: number;
};

const ACCESS_COLORS: Record<string, string> = {
  "<= 5 min": "#147a4e",
  "<= 10 min": "#2f9e6e",
  "<= 15 min": "#6fbf8f",
  "<= 20 min": "#e2b07a",
  "> 20 min": "#c56a3a",
  unreachable: "#8a8f96",
};

export default function AccessMap({ summary, scenario }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const [ready, setReady] = useState(false);
  const [placeMode, setPlaceMode] = useState(false);
  const [thresholdFilter, setThresholdFilter] = useState<"all" | "15">("15");
  const [scenarioResult, setScenarioResult] = useState<ScenarioResult | null>(
    null
  );

  const headline = useMemo(
    () => ({
      pct: summary.pct_within_15,
      within: summary.residents_within_15,
      outside: summary.residents_outside_15,
      stores: summary.qualifying_grocery_stores,
      median: summary.median_walk_minutes_pop_weighted,
    }),
    [summary]
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          carto: {
            type: "raster",
            tiles: [
              "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
              "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
            ],
            tileSize: 256,
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
          },
        },
        layers: [
          {
            id: "carto",
            type: "raster",
            source: "carto",
          },
        ],
      },
      center: [-83.05, 42.35],
      zoom: 10.4,
      attributionControl: { compact: true },
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    popupRef.current = new maplibregl.Popup({
      closeButton: true,
      maxWidth: "280px",
    });

    map.on("load", async () => {
      const [boundary, access, grocers] = await Promise.all([
        fetch("/data/boundary.geojson").then((r) => r.json()),
        fetch("/data/accessibility.geojson").then((r) => r.json()),
        fetch("/data/grocers.geojson").then((r) => r.json()),
      ]);

      map.addSource("boundary", { type: "geojson", data: boundary });
      map.addSource("access", { type: "geojson", data: access });
      map.addSource("grocers", { type: "geojson", data: grocers });
      map.addSource("scenario", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.addLayer({
        id: "access-fill",
        type: "fill",
        source: "access",
        paint: {
          "fill-color": [
            "match",
            ["get", "access_bin"],
            "<= 5 min",
            ACCESS_COLORS["<= 5 min"],
            "<= 10 min",
            ACCESS_COLORS["<= 10 min"],
            "<= 15 min",
            ACCESS_COLORS["<= 15 min"],
            "<= 20 min",
            ACCESS_COLORS["<= 20 min"],
            "> 20 min",
            ACCESS_COLORS["> 20 min"],
            ACCESS_COLORS.unreachable,
          ],
          "fill-opacity": 0.58,
        },
      });

      map.addLayer({
        id: "access-outline",
        type: "line",
        source: "access",
        paint: {
          "line-color": "#12202b",
          "line-opacity": 0.12,
          "line-width": 0.5,
        },
      });

      map.addLayer({
        id: "boundary-line",
        type: "line",
        source: "boundary",
        paint: {
          "line-color": "#12202b",
          "line-width": 2.2,
          "line-opacity": 0.75,
        },
      });

      map.addLayer({
        id: "grocers-halo",
        type: "circle",
        source: "grocers",
        paint: {
          "circle-radius": 10,
          "circle-color": "#1f6b4f",
          "circle-opacity": 0.18,
        },
      });

      map.addLayer({
        id: "grocers-circle",
        type: "circle",
        source: "grocers",
        paint: {
          "circle-radius": 5.5,
          "circle-color": "#0f3f2f",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
        },
      });

      map.addLayer({
        id: "scenario-point",
        type: "circle",
        source: "scenario",
        paint: {
          "circle-radius": 8,
          "circle-color": "#e8c468",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#12202b",
        },
      });

      map.on("click", "grocers-circle", (e) => {
        const f = e.features?.[0];
        if (!f || !popupRef.current) return;
        const p = f.properties || {};
        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font-size:13px;line-height:1.45">
              <strong style="font-size:15px">${p.name || "Grocery store"}</strong><br/>
              ${p.address ? `${p.address}<br/>` : ""}
              <span style="color:#456">Type:</span> ${p.store_type || "—"}<br/>
              <span style="color:#456">Source:</span> ${p.source || "—"}<br/>
              <span style="color:#456">Verified:</span> ${p.last_verified || "—"}
              ${p.notes ? `<div style="margin-top:6px;color:#456">${p.notes}</div>` : ""}
            </div>`
          )
          .addTo(map);
      });

      map.on("mouseenter", "grocers-circle", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "grocers-circle", () => {
        map.getCanvas().style.cursor = placeMode ? "crosshair" : "";
      });

      map.on("click", "access-fill", (e) => {
        if (placeMode) return;
        const f = e.features?.[0];
        if (!f || !popupRef.current) return;
        const p = f.properties || {};
        const mins =
          p.walk_minutes != null ? `${Number(p.walk_minutes).toFixed(1)} min` : "n/a";
        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font-size:13px;line-height:1.45">
              <strong>Block group ${p.GEOID || ""}</strong><br/>
              Population: ${formatNumber(Number(p.population || 0))}<br/>
              Walk to nearest qualifying grocer: <strong>${mins}</strong><br/>
              Access bin: ${p.access_bin || "—"}
            </div>`
          )
          .addTo(map);
      });

      setReady(true);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !map.getLayer("access-fill")) return;
    if (thresholdFilter === "15") {
      map.setPaintProperty("access-fill", "fill-color", [
        "case",
        ["==", ["get", "within_15"], true],
        "#2f9e6e",
        "#c56a3a",
      ]);
    } else {
      map.setPaintProperty("access-fill", "fill-color", [
        "match",
        ["get", "access_bin"],
        "<= 5 min",
        ACCESS_COLORS["<= 5 min"],
        "<= 10 min",
        ACCESS_COLORS["<= 10 min"],
        "<= 15 min",
        ACCESS_COLORS["<= 15 min"],
        "<= 20 min",
        ACCESS_COLORS["<= 20 min"],
        "> 20 min",
        ACCESS_COLORS["> 20 min"],
        ACCESS_COLORS.unreachable,
      ]);
    }
  }, [thresholdFilter, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.getCanvas().style.cursor = placeMode ? "crosshair" : "";

    const onClick = (e: MapMouseEvent) => {
      if (!placeMode) return;
      const { lng, lat } = e.lngLat;
      let newly = 0;
      let newWithin = 0;
      for (const pt of scenario.points) {
        const existing =
          pt.walk_minutes == null || Number.isNaN(pt.walk_minutes)
            ? Infinity
            : pt.walk_minutes;
        const est = estimateWalkMinutes(lat, lng, pt.lat, pt.lon, scenario.speed_mpm);
        const best = Math.min(existing, est);
        const wasIn = existing <= scenario.headline_minutes;
        const nowIn = best <= scenario.headline_minutes;
        if (nowIn) newWithin += pt.population;
        if (!wasIn && nowIn) newly += pt.population;
      }
      const newPct = (100 * newWithin) / scenario.total_population;
      setScenarioResult({
        lng,
        lat,
        newlyServed: newly,
        newWithin,
        newPct,
      });
      const src = map.getSource("scenario") as GeoJSONSource;
      src.setData({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: {},
            geometry: { type: "Point", coordinates: [lng, lat] },
          },
        ],
      });
    };

    map.on("click", onClick);
    return () => {
      map.off("click", onClick);
    };
  }, [placeMode, scenario]);

  return (
    <div className="mx-auto grid max-w-[1400px] gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[340px_1fr]">
      <aside className="animate-rise space-y-4">
        <section className="rounded-2xl bg-white/80 p-5 shadow-panel backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-lake">
            Citywide headline
          </p>
          <h1 className="mt-2 font-display text-4xl font-semibold leading-none tracking-tight text-ink">
            {headline.pct.toFixed(1)}%
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-ink/70">
            of Detroit residents can reach a qualifying grocery store within a{" "}
            <strong className="font-semibold text-ink">15-minute walk</strong> on
            the pedestrian network.
          </p>
          <dl className="mt-5 grid grid-cols-1 gap-3 text-sm">
            <div className="flex items-baseline justify-between border-t border-ink/10 pt-3">
              <dt className="text-ink/60">Within 15 minutes</dt>
              <dd className="font-semibold text-canopy">
                {formatNumber(headline.within)}
              </dd>
            </div>
            <div className="flex items-baseline justify-between border-t border-ink/10 pt-3">
              <dt className="text-ink/60">Outside 15 minutes</dt>
              <dd className="font-semibold text-gap">
                {formatNumber(headline.outside)}
              </dd>
            </div>
            <div className="flex items-baseline justify-between border-t border-ink/10 pt-3">
              <dt className="text-ink/60">Qualifying stores</dt>
              <dd className="font-semibold">{headline.stores}</dd>
            </div>
            {headline.median != null && (
              <div className="flex items-baseline justify-between border-t border-ink/10 pt-3">
                <dt className="text-ink/60">Median walk time</dt>
                <dd className="font-semibold">{headline.median.toFixed(1)} min</dd>
              </div>
            )}
          </dl>
        </section>

        <section className="animate-rise-delay rounded-2xl bg-white/80 p-5 shadow-panel backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-lake">
            Map layers
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => setThresholdFilter("15")}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                thresholdFilter === "15"
                  ? "bg-ink text-white"
                  : "bg-mist/70 text-ink hover:bg-mist"
              }`}
            >
              15-minute view
            </button>
            <button
              type="button"
              onClick={() => setThresholdFilter("all")}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                thresholdFilter === "all"
                  ? "bg-ink text-white"
                  : "bg-mist/70 text-ink hover:bg-mist"
              }`}
            >
              All bins
            </button>
          </div>
          <ul className="mt-4 space-y-2 text-sm">
            {thresholdFilter === "15" ? (
              <>
                <li className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm bg-[#2f9e6e]" /> Within 15 min
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm bg-[#c56a3a]" /> Outside 15 min
                </li>
              </>
            ) : (
              Object.entries(ACCESS_COLORS)
                .filter(([k]) => k !== "unreachable")
                .map(([label, color]) => (
                  <li key={label} className="flex items-center gap-2">
                    <span
                      className="h-3 w-3 rounded-sm"
                      style={{ background: color }}
                    />
                    {label}
                  </li>
                ))
            )}
            <li className="flex items-center gap-2 pt-1">
              <span className="h-3 w-3 rounded-full bg-[#0f3f2f] ring-2 ring-white" />
              Qualifying grocery store
            </li>
          </ul>
        </section>

        <section className="rounded-2xl bg-white/80 p-5 shadow-panel backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-lake">
            Place a grocery store
          </p>
          <p className="mt-2 text-sm text-ink/70">
            Click the map to estimate how a new store would change 15-minute
            access. Uses an approximate network distance factor—planning sketch,
            not a siting study.
          </p>
          <button
            type="button"
            onClick={() => {
              setPlaceMode((v) => !v);
              if (placeMode) {
                setScenarioResult(null);
                const map = mapRef.current;
                const src = map?.getSource("scenario") as GeoJSONSource | undefined;
                src?.setData({ type: "FeatureCollection", features: [] });
              }
            }}
            className={`mt-4 w-full rounded-lg px-3 py-2.5 text-sm font-semibold transition ${
              placeMode
                ? "bg-highlight text-ink"
                : "bg-lake text-white hover:bg-lake/90"
            }`}
          >
            {placeMode ? "Placing… click map (click to cancel)" : "Start placement"}
          </button>
          {scenarioResult && (
            <div className="relative mt-4 rounded-xl bg-canopySoft/60 p-3 text-sm">
              <div className="scenario-pulse absolute right-3 top-3 h-2 w-2 rounded-full bg-highlight" />
              <p>
                <strong>+{formatNumber(scenarioResult.newlyServed)}</strong> residents
                newly within 15 minutes
              </p>
              <p className="mt-1 text-ink/70">
                New citywide access:{" "}
                <strong className="text-ink">
                  {scenarioResult.newPct.toFixed(1)}%
                </strong>{" "}
                ({formatNumber(scenarioResult.newWithin)} people)
              </p>
            </div>
          )}
        </section>

        {(summary.lowest_access_tract || summary.highest_access_tract) && (
          <section className="rounded-2xl bg-white/80 p-5 text-sm shadow-panel backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-lake">
              Tract contrast
            </p>
            {summary.highest_access_tract && (
              <p className="mt-3">
                Highest access tract{" "}
                <span className="font-mono text-xs">
                  {summary.highest_access_tract.tract}
                </span>
                : {summary.highest_access_tract.pct_within_15.toFixed(0)}% within 15
                min
              </p>
            )}
            {summary.lowest_access_tract && (
              <p className="mt-2">
                Lowest access tract{" "}
                <span className="font-mono text-xs">
                  {summary.lowest_access_tract.tract}
                </span>
                : {summary.lowest_access_tract.pct_within_15.toFixed(0)}% within 15
                min
              </p>
            )}
          </section>
        )}
      </aside>

      <section className="animate-rise-delay overflow-hidden rounded-2xl border border-ink/10 bg-white/50 shadow-panel">
        <div className="border-b border-ink/10 px-4 py-3 sm:px-5">
          <h2 className="font-display text-xl font-semibold text-ink">
            Walking access across Detroit
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-ink/65">
            Green areas can reach a reviewed grocery store within 15 minutes on
            foot. Copper areas cannot. Click a store or block group for details.
          </p>
        </div>
        <div ref={containerRef} className="h-[68vh] min-h-[420px] w-full" />
      </section>
    </div>
  );
}
