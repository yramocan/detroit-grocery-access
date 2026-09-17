# Methodology

This document explains how the Detroit 15-Minute Grocery Access MVP estimates
who can walk to a qualifying grocery store within 15 minutes.

It is also published in the web app at `/methodology`.

## Core question

What percentage of Detroit residents can reach a qualifying grocery store
within 15 minutes on foot, and where are the largest access gaps?

## Geographic scope

- Primary statistics use **City of Detroit municipal boundaries only**.
- The broader metro area is not included in headline metrics.
- The data model allows grocery stores immediately outside the city to be
  added later if Detroit residents can walk to them
  (`include_outside_city_stores` in `config.yaml`).

## Qualifying grocery stores

Stores are **manually reviewed** against
`data/manual/classification_rubric.md`.

In short, a qualifying store should support a normal grocery trip with
meaningful access to produce, protein, dairy/substitutes, grains/staples,
frozen foods, and basic household grocery needs.

Excluded formats include liquor stores, gas stations, convenience stores,
pharmacies, limited-assortment dollar stores, and specialty shops that cannot
reasonably support a full grocery trip.

V1 does **not** use automated AI classification.

Dataset: `data/manual/qualifying_grocers.csv`

## Population

- Source: U.S. Census Bureau American Community Survey (ACS) 5-year estimates
  via Census Reporter (B01003), with optional direct Census API if
  `CENSUS_API_KEY` is set
- Variable: Total population (`B01003_001E` / B01003001)
- Geography: Census **block groups** intersecting Detroit
- Uninhabited block groups (population 0) are excluded from accessibility
  weighting
- Origins use each inhabited block group’s representative point so empty land
  is not treated as equally populated

Retrieval metadata is written under `data/raw/census/`.

## Walking network and routing

- Pedestrian network: OpenStreetMap via **OSMnx** (`network_type=walk`)
- Routing: **NetworkX** multi-source Dijkstra from all qualifying grocery
  store nodes, weighted by edge length
- Travel time = network distance ÷ walking speed
- Default walking speed: **3.0 mph (4.8 km/h)**, configurable in `config.yaml`
- Straight-line radius buffers are **not** used as the primary measure

## Access thresholds

Reported bins:

- ≤ 5 minutes
- ≤ 10 minutes
- ≤ 15 minutes
- ≤ 20 minutes
- > 20 minutes
- unreachable (could not snap to network or no path)

Headline metric: share of Detroit residents with ≤ **15** minutes walking
access to the nearest qualifying grocery store.

## Dashboard metrics

Computed in `scripts/calculate_accessibility.py` and written to
`outputs/summary.json`:

- Percent of residents within 15 minutes
- Residents within / outside 15 minutes
- Count of qualifying grocery stores analyzed
- Population-weighted median walking time (when paths exist)
- Lowest / highest access census tracts (among tracts with sufficient
  population)

## Data dates

See `config.yaml` → `project.retrieval_date` and JSON metadata files under
`data/raw/`. Re-run `make analyze` to refresh.

## Known limitations

This MVP does **not** measure:

- grocery prices
- inventory quality in real time
- cultural appropriateness of inventory
- transit accessibility
- disability-specific travel times
- sidewalk quality or curb ramps
- personal safety
- snow / weather impacts
- grocery delivery
- store capacity
- reliable store hours beyond basic metadata

**The MVP measures geographic pedestrian accessibility, not total food security.**

## Stretch: place a grocery store

If enabled in the web app, the scenario tool estimates how many additional
residents would fall within 15 minutes if a store existed at a clicked
location. The MVP scenario uses a documented approximation on top of the
precomputed block-group network baselines; it is a planning sketch, not an
engineered siting study.

## Reproducibility

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make analyze
cd web && npm install && npm run dev
```

Or: `python scripts/build_all.py`
