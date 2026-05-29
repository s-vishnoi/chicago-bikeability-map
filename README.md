# Chicago Bikeability Atlas

This folder is a self-contained static snapshot of the atlas surface.

`generate_atlas_data.py` reads the local `data/` snapshot and writes `data/atlas-data.json` for the browser app.

Run locally:

```bash
python3 generate_atlas_data.py
python3 -m http.server 8090
```

Then open:

```text
http://127.0.0.1:8090/
```

Build a single-file shareable export:

```bash
python3 build_shareable_html.py
```

This writes `chicago-bikeability-atlas.html`, which can be opened directly in a browser or sent as one file.

## Updates / Live Rebuild Flow

Use this flow when the crash data should be refreshed from the City of Chicago source instead of using the checked-in snapshot.

```bash
python3 refresh_live_crashes.py
python3 refresh_population.py
python3 generate_atlas_data.py
python3 build_shareable_html.py
```

What each step does:

- `refresh_live_crashes.py` pulls current pedalcyclist crash records from the City of Chicago Socrata Traffic Crashes API, pulls official community-area boundaries, assigns each crash point to an atlas community, rewrites `data/crash_with_carea.csv` and `data/grouped.csv`, and updates crash totals in `data/citywide_stats.pkl`.
- `refresh_population.py` pulls CMAP's 2025 Community Data Snapshot table for Chicago community areas and rewrites `data/community_pops.json`.
- `generate_atlas_data.py` rebuilds `data/atlas-data.json`, including crash markers, injury counts, causes, severe-injury drops, OSM-matched street hover labels, and network plots.
- `build_shareable_html.py` embeds the refreshed JSON/CSS/JS/assets into `chicago-bikeability-atlas.html`.

Optional road basemap refresh:

```bash
python3 fetch_osm_roads.py
python3 generate_atlas_data.py
python3 build_shareable_html.py
```

`fetch_osm_roads.py` pulls OpenStreetMap Chicago road centerlines from Overpass into `data/osm_chicago_roads.json`. When that file exists, `generate_atlas_data.py` renders a static Google-ish road basemap underneath the bike-lane overlay and uses those OSM street centerlines for more robust crash-marker hover street names.

Notes:

- These refresh commands need internet access.
- The app itself remains static and shareable after rebuilding.
- The refresh scripts normalize a few source names to the atlas cartogram names, including `East/West Garfield Park -> Garfield Park`, `Greater Grand Crossing -> Grand Crossing`, `West Englewood -> Englewood`, `The Loop -> Loop`, and `Ohare -> O'Hare`.
- Last verified live refresh in this workspace produced `15,683` community-assigned pedalcyclist crashes from `2018-01-03` through `2026-05-28`.
- Last verified CMAP population refresh produced a citywide atlas population total of `2,707,252`.
