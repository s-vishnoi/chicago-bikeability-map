import json
import urllib.parse
import urllib.request
from pathlib import Path


OUT = Path(__file__).resolve().parent / "data" / "osm_chicago_roads.json"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Covers Chicago with a little buffer so edge communities have complete roads.
SOUTH, WEST, NORTH, EAST = 41.60, -87.96, 42.04, -87.48

QUERY = f"""
[out:json][timeout:180];
(
  way["highway"]["highway"!~"^(footway|cycleway|path|steps|pedestrian|track|service|construction|bridleway)$"]({SOUTH},{WEST},{NORTH},{EAST});
);
out body;
>;
out skel qt;
"""

ROAD_CLASSES = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "living_street",
    "motorway_link",
    "trunk_link",
    "primary_link",
    "secondary_link",
    "tertiary_link",
}


def main():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    request = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={
            "User-Agent": "chicago-bikeability-map/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        payload = json.loads(response.read().decode())

    nodes = {}
    ways = []
    for element in payload.get("elements", []):
        if element.get("type") == "node":
            nodes[element["id"]] = [float(element["lon"]), float(element["lat"])]
        elif element.get("type") == "way":
            highway = element.get("tags", {}).get("highway")
            if highway in ROAD_CLASSES:
                ways.append(element)

    roads = []
    for way in ways:
        coords = [nodes[node_id] for node_id in way.get("nodes", []) if node_id in nodes]
        if len(coords) < 2:
            continue
        tags = way.get("tags", {})
        roads.append(
            {
                "id": way.get("id"),
                "name": tags.get("name") or "",
                "highway": tags.get("highway") or "road",
                "coords": coords,
            }
        )

    OUT.write_text(
        json.dumps(
            {
                "source": "OpenStreetMap via Overpass API",
                "bbox": [WEST, SOUTH, EAST, NORTH],
                "roadCount": len(roads),
                "roads": roads,
            },
            separators=(",", ":"),
        )
    )
    print(f"Wrote {OUT} with {len(roads)} roads")


if __name__ == "__main__":
    main()
