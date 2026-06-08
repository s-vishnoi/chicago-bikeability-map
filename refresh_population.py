import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "community_pops.json"

CMAP_CCA_2025_TABLE = (
    "https://services5.arcgis.com/LcMXE3TFhi1BSaCY/arcgis/rest/services/"
    "CommunityDataSnapshots_2015_2025_gdb/FeatureServer/22/query"
)

COMMUNITY_ALIASES = {
    "East Garfield Park": "Garfield Park",
    "West Garfield Park": "Garfield Park",
    "West Englewood": "Englewood",
    "Greater Grand Crossing": "Grand Crossing",
    "The Loop": "Loop",
    "Ohare": "O'Hare",
    "O Hare": "O'Hare",
}


def normalize_name(value):
    name = str(value or "").strip().title()
    return COMMUNITY_ALIASES.get(name, name)


def fetch_cmap_population_rows():
    params = urllib.parse.urlencode(
        {
            "f": "json",
            "where": "1=1",
            "outFields": "GEOG,TOT_POP",
            "returnGeometry": "false",
            "resultRecordCount": 500,
        }
    )
    request = urllib.request.Request(
        f"{CMAP_CCA_2025_TABLE}?{params}",
        headers={"User-Agent": "chicago-bikeability-map/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode())
    rows = [feature.get("attributes", {}) for feature in payload.get("features", [])]
    if len(rows) < 77:
        raise ValueError(f"Expected at least 77 CMAP CCA rows, got {len(rows)}")
    return rows


def main():
    grid_names = [item["name"] for item in json.loads((DATA / "CAreaGrid.json").read_text())]
    allowed = set(grid_names)
    population = defaultdict(int)

    for row in fetch_cmap_population_rows():
        name = normalize_name(row.get("GEOG"))
        if name not in allowed:
            continue
        population[name] += round(float(row.get("TOT_POP") or 0))

    missing = [name for name in grid_names if name not in population]
    if missing:
        raise ValueError(f"Missing population rows for atlas communities: {', '.join(missing)}")

    ordered = {name: int(population[name]) for name in grid_names}
    OUT.write_text(json.dumps(ordered, indent=2) + "\n")
    print(f"Wrote {OUT} with {len(ordered)} communities")
    print(f"Total population: {sum(ordered.values()):,}")


if __name__ == "__main__":
    main()
