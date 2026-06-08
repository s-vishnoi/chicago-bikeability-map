import csv
import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

CRASH_DATASET = "85ca-t3if"
COMMUNITY_AREAS_DATASET = "igwz-8jzy"
SOCRATA = "https://data.cityofchicago.org/resource"

CRASH_OUT = DATA / "crash_with_carea.csv"
GROUPED_OUT = DATA / "grouped.csv"
CITYWIDE_OUT = DATA / "citywide_stats.json"
BOUNDARIES_OUT = DATA / "community_areas_live.geojson"

START_DATE = "2018-01-01T00:00:00"
SEVERE_LABELS = {"FATAL", "INCAPACITATING INJURY"}

COMMUNITY_ALIASES = {
    "East Garfield Park": "Garfield Park",
    "West Garfield Park": "Garfield Park",
    "West Englewood": "Englewood",
    "Greater Grand Crossing": "Grand Crossing",
    "Ohare": "O'Hare",
    "O Hare": "O'Hare",
}

CRASH_FIELDS = [
    "crash_record_id",
    "posted_speed_limit",
    "traffic_control_device",
    "device_condition",
    "weather_condition",
    "lighting_condition",
    "first_crash_type",
    "trafficway_type",
    "alignment",
    "roadway_surface_cond",
    "road_defect",
    "intersection_related_i",
    "prim_contributory_cause",
    "sec_contributory_cause",
    "dooring_i",
    "most_severe_injury",
    "crash_hour",
    "crash_month",
    "latitude",
    "longitude",
    "crash_date",
    "street_no",
    "street_direction",
    "street_name",
]

OUTPUT_FIELDS = [
    "Unnamed: 0",
    "POSTED_SPEED_LIMIT",
    "TRAFFIC_CONTROL_DEVICE",
    "DEVICE_CONDITION",
    "WEATHER_CONDITION",
    "LIGHTING_CONDITION",
    "FIRST_CRASH_TYPE",
    "TRAFFICWAY_TYPE",
    "ALIGNMENT",
    "ROADWAY_SURFACE_COND",
    "ROAD_DEFECT",
    "INTERSECTION_RELATED_I",
    "PRIM_CONTRIBUTORY_CAUSE",
    "SEC_CONTRIBUTORY_CAUSE",
    "DOORING_I",
    "MOST_SEVERE_INJURY",
    "CRASH_HOUR",
    "CRASH_MONTH",
    "LATITUDE",
    "LONGITUDE",
    "CRASH_YEAR",
    "SPEED_LIMIT",
    "geometry",
    "DISPLAYROU",
    "the_geom",
    "DIST",
    "LANE_TYPE",
    "CRASH_DATE",
    "is_severe",
    "index_right",
    "CArea",
]


def socrata_json(dataset, params):
    query = urllib.parse.urlencode(params, safe=",()' >=:")
    url = f"{SOCRATA}/{dataset}.json?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "chicago-bikeability-atlas/1.0"})
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode())


def socrata_geojson(dataset, params):
    query = urllib.parse.urlencode(params, safe=",()' >=:")
    url = f"{SOCRATA}/{dataset}.geojson?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "chicago-bikeability-atlas/1.0"})
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode())


def fetch_crashes():
    rows = []
    offset = 0
    limit = 50000
    where = (
        "first_crash_type='PEDALCYCLIST' "
        f"AND crash_date >= '{START_DATE}' "
        "AND latitude IS NOT NULL AND longitude IS NOT NULL"
    )
    while True:
        batch = socrata_json(
            CRASH_DATASET,
            {
                "$select": ",".join(CRASH_FIELDS),
                "$where": where,
                "$order": "crash_date",
                "$limit": limit,
                "$offset": offset,
            },
        )
        rows.extend(batch)
        print(f"Fetched {len(rows)} crash rows")
        if len(batch) < limit:
            return rows
        offset += limit


def community_name(props):
    for key in ("community", "community_area_name", "name", "area_name", "pri_neigh"):
        value = props.get(key)
        if value:
            name = str(value).strip().title()
            return COMMUNITY_ALIASES.get(name, name)
    return ""


def fetch_community_boundaries():
    geojson = socrata_geojson(COMMUNITY_AREAS_DATASET, {"$limit": 5000})
    BOUNDARIES_OUT.write_text(json.dumps(geojson, separators=(",", ":")))
    features = []
    for idx, feature in enumerate(geojson.get("features", [])):
        name = community_name(feature.get("properties", {}))
        geometry = feature.get("geometry") or {}
        if name and geometry:
            features.append({"name": name, "geometry": geometry, "index": idx})
    if len(features) < 75:
        raise ValueError(f"Expected community boundaries, got only {len(features)} features")
    print(f"Fetched {len(features)} community boundaries")
    return features


def point_on_segment(px, py, ax, ay, bx, by, eps=1e-12):
    cross = (py - ay) * (bx - ax) - (px - ax) * (by - ay)
    if abs(cross) > eps:
        return False
    dot = (px - ax) * (bx - ax) + (py - ay) * (by - ay)
    if dot < -eps:
        return False
    length_sq = (bx - ax) ** 2 + (by - ay) ** 2
    return dot <= length_sq + eps


def point_in_ring(lon, lat, ring):
    inside = False
    if not ring:
        return False
    prev_lon, prev_lat = ring[-1][:2]
    for point in ring:
        curr_lon, curr_lat = point[:2]
        if point_on_segment(lon, lat, prev_lon, prev_lat, curr_lon, curr_lat):
            return True
        crosses = (curr_lat > lat) != (prev_lat > lat)
        if crosses:
            at_lon = (prev_lon - curr_lon) * (lat - curr_lat) / (prev_lat - curr_lat) + curr_lon
            if lon < at_lon:
                inside = not inside
        prev_lon, prev_lat = curr_lon, curr_lat
    return inside


def point_in_polygon(lon, lat, polygon):
    if not polygon or not point_in_ring(lon, lat, polygon[0]):
        return False
    return not any(point_in_ring(lon, lat, hole) for hole in polygon[1:])


def geometry_polygons(geometry):
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return coords
    if kind == "MultiPolygon":
        return [polygon for polygon in coords]
    return []


def polygon_bbox(polygon):
    xs = []
    ys = []
    for ring in polygon:
        for lon, lat, *_rest in ring:
            xs.append(lon)
            ys.append(lat)
    return min(xs), min(ys), max(xs), max(ys)


def build_boundary_index(features, cell_size=0.012):
    cells = {}
    polygons = []
    for feature in features:
        for polygon in geometry_polygons(feature["geometry"]):
            bbox = polygon_bbox(polygon)
            entry = {"name": feature["name"], "polygon": polygon, "bbox": bbox, "index": feature["index"]}
            poly_index = len(polygons)
            polygons.append(entry)
            min_lon, min_lat, max_lon, max_lat = bbox
            min_cx = math.floor(min_lon / cell_size)
            max_cx = math.floor(max_lon / cell_size)
            min_cy = math.floor(min_lat / cell_size)
            max_cy = math.floor(max_lat / cell_size)
            for cx in range(min_cx, max_cx + 1):
                for cy in range(min_cy, max_cy + 1):
                    cells.setdefault((cx, cy), []).append(poly_index)
    return {"cells": cells, "polygons": polygons, "cell_size": cell_size}


def assign_community(lon, lat, index):
    cell_size = index["cell_size"]
    cx = math.floor(lon / cell_size)
    cy = math.floor(lat / cell_size)
    candidates = index["cells"].get((cx, cy), [])
    for poly_index in candidates:
        entry = index["polygons"][poly_index]
        min_lon, min_lat, max_lon, max_lat = entry["bbox"]
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            if point_in_polygon(lon, lat, entry["polygon"]):
                return entry["name"], entry["index"]
    return "", ""


def parse_year(value):
    text = str(value or "")
    if len(text) >= 4 and text[:4].isdigit():
        return text[:4]
    return ""


def normalize_date(value):
    text = str(value or "").strip()
    if not text:
        return ""
    # Socrata usually returns ISO strings; keep date precision for hover labels.
    return text[:10]


def output_row(row, idx, area, area_index):
    lat = str(row.get("latitude") or "")
    lon = str(row.get("longitude") or "")
    severity = str(row.get("most_severe_injury") or "UNKNOWN").upper()
    crash_date = normalize_date(row.get("crash_date"))
    speed = row.get("posted_speed_limit") or ""
    return {
        "Unnamed: 0": idx,
        "POSTED_SPEED_LIMIT": speed,
        "TRAFFIC_CONTROL_DEVICE": str(row.get("traffic_control_device") or "").upper(),
        "DEVICE_CONDITION": str(row.get("device_condition") or "").upper(),
        "WEATHER_CONDITION": str(row.get("weather_condition") or "").upper(),
        "LIGHTING_CONDITION": str(row.get("lighting_condition") or "").upper(),
        "FIRST_CRASH_TYPE": str(row.get("first_crash_type") or "PEDALCYCLIST").upper(),
        "TRAFFICWAY_TYPE": str(row.get("trafficway_type") or "").upper(),
        "ALIGNMENT": str(row.get("alignment") or "").upper(),
        "ROADWAY_SURFACE_COND": str(row.get("roadway_surface_cond") or "").upper(),
        "ROAD_DEFECT": str(row.get("road_defect") or "").upper(),
        "INTERSECTION_RELATED_I": str(row.get("intersection_related_i") or "").upper(),
        "PRIM_CONTRIBUTORY_CAUSE": str(row.get("prim_contributory_cause") or "UNKNOWN").upper(),
        "SEC_CONTRIBUTORY_CAUSE": str(row.get("sec_contributory_cause") or "").upper(),
        "DOORING_I": str(row.get("dooring_i") or "").upper(),
        "MOST_SEVERE_INJURY": severity,
        "CRASH_HOUR": row.get("crash_hour") or "",
        "CRASH_MONTH": row.get("crash_month") or "",
        "LATITUDE": lat,
        "LONGITUDE": lon,
        "CRASH_YEAR": parse_year(row.get("crash_date")),
        "SPEED_LIMIT": speed,
        "geometry": f"POINT ({lon} {lat})",
        "DISPLAYROU": "",
        "the_geom": "",
        "DIST": "",
        "LANE_TYPE": "",
        "CRASH_DATE": crash_date,
        "is_severe": str(severity in SEVERE_LABELS),
        "index_right": area_index,
        "CArea": area,
    }


def write_crash_outputs(crashes, boundary_features):
    grid_names = [item["name"] for item in json.loads((DATA / "CAreaGrid.json").read_text())]
    boundary_index = build_boundary_index(boundary_features)
    output_rows = []
    skipped = 0
    for idx, row in enumerate(crashes):
        try:
            lat = float(row.get("latitude"))
            lon = float(row.get("longitude"))
        except (TypeError, ValueError):
            skipped += 1
            continue
        area, area_index = assign_community(lon, lat, boundary_index)
        if not area:
            skipped += 1
            continue
        output_rows.append(output_row(row, idx, area, area_index))

    with CRASH_OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    grouped_rows = []
    by_area = Counter(row["CArea"] for row in output_rows)
    severe_by_area = Counter(row["CArea"] for row in output_rows if row["MOST_SEVERE_INJURY"] in SEVERE_LABELS)
    for name in grid_names:
        total = by_area[name]
        severe = severe_by_area[name]
        grouped_rows.append(
            {
                "CArea": name,
                "total_crashes": total,
                "severe_crashes": severe,
                "severe_rate": severe / total if total else 0,
                "crash_rate": total / sum(by_area.values()) if by_area else 0,
            }
        )
    with GROUPED_OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["CArea", "total_crashes", "severe_crashes", "severe_rate", "crash_rate"])
        writer.writeheader()
        writer.writerows(grouped_rows)

    total = len(output_rows)
    severe = sum(1 for row in output_rows if row["MOST_SEVERE_INJURY"] in SEVERE_LABELS)
    existing = {}
    if CITYWIDE_OUT.exists():
        with CITYWIDE_OUT.open() as f:
            existing = json.load(f)
    existing.update(
        {
            "crashes_total": total,
            "crashes_severe": severe,
            "severe_rate": severe / total if total else 0,
        }
    )
    with CITYWIDE_OUT.open("w") as f:
        json.dump(existing, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {CRASH_OUT} with {total} community-assigned crashes")
    print(f"Wrote {GROUPED_OUT} and updated {CITYWIDE_OUT}")
    if skipped:
        print(f"Skipped {skipped} rows outside community areas or without coordinates")


def main():
    DATA.mkdir(exist_ok=True)
    boundaries = fetch_community_boundaries()
    crashes = fetch_crashes()
    write_crash_outputs(crashes, boundaries)


if __name__ == "__main__":
    main()
