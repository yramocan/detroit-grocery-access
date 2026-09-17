# Detroit 15-Minute Grocery Access

Interactive MVP dashboard answering one question:

**Who in Detroit can walk to good groceries within 15 minutes—and who cannot?**

![License](https://img.shields.io/badge/license-MIT-blue)

## What this is

A civic-tech proof of concept that:

1. Maps manually reviewed **qualifying grocery stores** in Detroit
2. Measures **walking-network** travel time (not straight-line circles)
3. Weights results by **Census block-group population**
4. Reports the share of residents inside vs. outside a **15-minute** walk
5. Documents methodology and limitations for policy audiences

This is the skateboard, not the car. It is designed to be credible enough to
share with city, Green Grocer, DEGC, community, or research partners—while
staying intentionally narrow.

## Quick start

```bash
# Python analysis environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download data, build walk network, compute accessibility
make analyze

# Web dashboard
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

You can also run:

```bash
python scripts/build_all.py
python scripts/export_web_data.py
```

## Repository layout

```
/
  README.md
  config.yaml                 # walking speed, thresholds, paths
  Makefile
  requirements.txt
  data/
    raw/                      # download metadata (large raw files gitignored)
    processed/
    manual/
      classification_rubric.md
      qualifying_grocers.csv  # human-reviewed store list
  scripts/
    download_detroit_data.py
    download_census_data.py
    download_grocery_candidates.py
    build_walk_network.py
    calculate_accessibility.py
    export_web_data.py
    build_all.py
  analysis/
    methodology.md
  web/                        # Next.js + MapLibre dashboard
  outputs/
    accessibility.geojson
    grocers.geojson
    boundary.geojson
    summary.json
```

## Current MVP estimate

From the committed analysis outputs (`web/public/data/summary.json`):

- **48.3%** of Detroit residents within a 15-minute walk
- **308,758** residents within / **329,877** outside
- **84** qualifying grocery stores analyzed
- Population-weighted median walk time: **15.1 minutes**

Re-run `make analyze` to refresh after revising stores or assumptions.

## Qualifying grocery definition

See `data/manual/classification_rubric.md`. Classification is **manual** in V1.

## Methodology

See [`analysis/methodology.md`](analysis/methodology.md) or the in-app
`/methodology` page.

Default walking speed: **3 mph / 4.8 km/h** (configurable in `config.yaml`).

## Important limitations

This MVP does not measure prices, inventory quality, cultural fit, transit,
disability-specific travel, sidewalk quality, safety, weather, delivery, store
capacity, or reliable hours.

**It measures geographic pedestrian accessibility—not total food security.**

## License

MIT. Data from U.S. Census, OpenStreetMap, and Detroit Open Data remain under
their respective terms. OSM data © OpenStreetMap contributors.
