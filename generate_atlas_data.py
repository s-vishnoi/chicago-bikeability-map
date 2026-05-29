import csv
import base64
import json
import math
import pickle
import sys
import types
import re
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    from shapely.affinity import scale as scale_geom, translate as translate_geom
    from shapely.geometry import shape
    from shapely.ops import unary_union
except ImportError:  # pragma: no cover - optional for local builds without shapely
    scale_geom = translate_geom = shape = unary_union = None


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA
SCHEMA_VERSION = 2
REQUIRED_SOURCE_FILES = [
    "grouped.csv",
    "CAreaGrid.json",
    "name_to_bike_rank.json",
    "name_to_infrastructure_score.json",
    "name_to_network_score.json",
    "name_to_road_length.json",
    "community_pops.json",
    "citywide_stats.pkl",
    "precomputed_network_plots.pkl",
    "crash_with_carea.csv",
    "bike_with_neigh.csv",
]

OSM_ROADS_FILE = DATA / "osm_chicago_roads.json"


def read_json(path):
    with open(path) as f:
        return json.load(f)


def read_csv_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def require_source_files():
    missing = [name for name in REQUIRED_SOURCE_FILES if not (DATA / name).exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Missing required data source(s) in {DATA}: {joined}")


def number(value, default=0.0):
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def lonlat_to_utm16(lon, lat):
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lon_origin_rad = math.radians(-87)
    semi_major = 6378137.0
    eccentricity_sq = 0.00669438
    scale_factor = 0.9996
    eccentricity_prime_sq = eccentricity_sq / (1 - eccentricity_sq)

    n = semi_major / math.sqrt(1 - eccentricity_sq * math.sin(lat_rad) ** 2)
    t = math.tan(lat_rad) ** 2
    c = eccentricity_prime_sq * math.cos(lat_rad) ** 2
    a = math.cos(lat_rad) * (lon_rad - lon_origin_rad)
    meridian = semi_major * (
        (1 - eccentricity_sq / 4 - 3 * eccentricity_sq ** 2 / 64 - 5 * eccentricity_sq ** 3 / 256) * lat_rad
        - (3 * eccentricity_sq / 8 + 3 * eccentricity_sq ** 2 / 32 + 45 * eccentricity_sq ** 3 / 1024) * math.sin(2 * lat_rad)
        + (15 * eccentricity_sq ** 2 / 256 + 45 * eccentricity_sq ** 3 / 1024) * math.sin(4 * lat_rad)
        - (35 * eccentricity_sq ** 3 / 3072) * math.sin(6 * lat_rad)
    )

    easting = scale_factor * n * (
        a
        + (1 - t + c) * a ** 3 / 6
        + (5 - 18 * t + t ** 2 + 72 * c - 58 * eccentricity_prime_sq) * a ** 5 / 120
    ) + 500000
    northing = scale_factor * (
        meridian
        + n * math.tan(lat_rad) * (
            a ** 2 / 2
            + (5 - t + 9 * c + 4 * c ** 2) * a ** 4 / 24
            + (61 - 58 * t + t ** 2 + 600 * c - 330 * eccentricity_prime_sq) * a ** 6 / 720
        )
    )
    return easting, northing


def abbrev(name):
    replacements = {
        "North": "N",
        "South": "S",
        "East": "E",
        "West": "W",
        "Park": "Pk",
        "Heights": "Ht",
        "Square": "Sq",
        "Crossing": "Cross.",
        "Boulevard": "Blvd",
        "Mount": "Mt.",
    }
    return " ".join(replacements.get(part, part) for part in name.split()).upper()


def escape_xml(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def percentile_rank(values, value):
    if not values:
        return 0
    below = sum(1 for item in values if item < value)
    return round((below / max(len(values) - 1, 1)) * 100)


def decode_typed_arrays(obj):
    if isinstance(obj, dict):
        if set(obj.keys()) == {"dtype", "bdata"}:
            raw = base64.b64decode(obj["bdata"])
            dtype = np.dtype(obj["dtype"])
            count = len(raw) // dtype.itemsize
            return np.frombuffer(raw, dtype=dtype, count=count)
        return {k: decode_typed_arrays(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decode_typed_arrays(v) for v in obj]
    return obj


def parse_wkt_segments(wkt_text):
    if not wkt_text:
        return []

    segments = []
    for segment_text in re.findall(r"\(([^()]+)\)", wkt_text):
        coords = []
        for pair in segment_text.split(","):
            parts = pair.strip().split()
            if len(parts) < 2:
                continue
            try:
                coords.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
        if len(coords) >= 2:
            segments.append(coords)
    return segments


def point_to_segment_distance_sq(px, py, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return (px - ax) ** 2 + (py - ay) ** 2

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return (px - proj_x) ** 2 + (py - proj_y) ** 2


def polyline_distance_sq(px, py, coords):
    best = float("inf")
    for idx in range(len(coords) - 1):
        ax, ay = coords[idx]
        bx, by = coords[idx + 1]
        best = min(best, point_to_segment_distance_sq(px, py, ax, ay, bx, by))
    return best


def normalize_street_label(row, fallback="Street unavailable"):
    street = (row.get("STREET") or row.get("ST_NAME") or "").strip()
    if street:
        return street

    from_street = (row.get("F_STREET") or "").strip()
    to_street = (row.get("T_STREET") or "").strip()
    if from_street or to_street:
        parts = [part for part in [from_street, to_street] if part]
        return " to ".join(parts)

    return (row.get("DISPLAYROU") or row.get("DISPLAYROU_CLEAN") or fallback).strip() or fallback


def build_road_segments(bike_rows):
    road_segments = defaultdict(list)
    for row in bike_rows:
        area = row.get("CArea")
        if not area:
            continue
        label = normalize_street_label(row)
        for segment in parse_wkt_segments(row.get("the_geom") or ""):
            road_segments[area].append((segment, label))
    return road_segments


def nearest_street_label(lon, lat, road_segments):
    best_label = None
    best_distance = float("inf")

    for coords, label in road_segments:
        distance = polyline_distance_sq(lon, lat, coords)
        if distance < best_distance:
            best_distance = distance
            best_label = label

    return best_label or "Street unavailable"


def build_osm_street_index(osm_roads, cell_size=360):
    index = defaultdict(list)
    for road in osm_roads:
        label = str(road.get("name") or "").strip()
        if not label:
            continue
        coords = road.get("projected") or []
        for idx in range(len(coords) - 1):
            ax, ay = coords[idx]
            bx, by = coords[idx + 1]
            min_cx = math.floor(min(ax, bx) / cell_size)
            max_cx = math.floor(max(ax, bx) / cell_size)
            min_cy = math.floor(min(ay, by) / cell_size)
            max_cy = math.floor(max(ay, by) / cell_size)
            segment = (ax, ay, bx, by, label, road.get("highway") or "")
            for cx in range(min_cx, max_cx + 1):
                for cy in range(min_cy, max_cy + 1):
                    index[(cx, cy)].append(segment)
    return {"cells": index, "cell_size": cell_size}


def nearest_osm_street_label(x, y, osm_index, max_ring=4):
    if not osm_index:
        return None

    cells = osm_index.get("cells") or {}
    cell_size = osm_index.get("cell_size") or 360
    center_cx = math.floor(x / cell_size)
    center_cy = math.floor(y / cell_size)
    best_label = None
    best_distance = float("inf")
    seen = set()

    for ring in range(max_ring + 1):
        for cx in range(center_cx - ring, center_cx + ring + 1):
            for cy in range(center_cy - ring, center_cy + ring + 1):
                if ring and abs(cx - center_cx) < ring and abs(cy - center_cy) < ring:
                    continue
                for segment in cells.get((cx, cy), []):
                    key = tuple(segment[:4]) + (segment[4],)
                    if key in seen:
                        continue
                    seen.add(key)
                    ax, ay, bx, by, label, _highway = segment
                    distance = point_to_segment_distance_sq(x, y, ax, ay, bx, by)
                    if distance < best_distance:
                        best_distance = distance
                        best_label = label
        if best_label and best_distance <= (cell_size * max(1, ring + 0.5)) ** 2:
            break

    return best_label


def build_crash_lookup(crash_rows):
    lookup = defaultdict(lambda: defaultdict(deque))
    for row in crash_rows:
        area = row.get("CArea")
        if not area:
            continue
        date = (row.get("CRASH_DATE") or "").strip()
        cause = (row.get("PRIM_CONTRIBUTORY_CAUSE") or "UNKNOWN").strip().upper()
        lookup[area][(date, cause)].append(row)
    return lookup


def build_severe_crash_lookup(crash_rows):
    lookup = defaultdict(deque)
    severe_values = {"FATAL", "INCAPACITATING INJURY"}
    for row in crash_rows:
        area = row.get("CArea")
        if not area:
            continue
        severity = (row.get("MOST_SEVERE_INJURY") or "").strip().upper()
        if severity in severe_values:
            lookup[area].append(row)
    return lookup


def normalize_severity_key(severity):
    value = str(severity or "").strip().upper()
    if value == "FATAL":
        return "fatal"
    if value == "INCAPACITATING INJURY":
        return "severe"
    if value == "NONINCAPACITATING INJURY":
        return "moderate"
    if value == "REPORTED, NOT EVIDENT":
        return "reported"
    if value == "NO INDICATION OF INJURY":
        return "none"
    return "unknown"


def severity_marker_style(severity):
    key = normalize_severity_key(severity)
    styles = {
        "fatal": {
            "shape": "circle",
            "fill": "#b32020",
            "stroke": "#6f0f0f",
            "stroke_width": 1.2,
            "opacity": 0.96,
            "size_scale": 1.15,
        },
        "severe": {
            "shape": "circle",
            "fill": "#f0c94f",
            "stroke": "#a67d08",
            "stroke_width": 1.0,
            "opacity": 0.95,
            "size_scale": 1.0,
        },
        "moderate": {
            "shape": "ring",
            "fill": "none",
            "stroke": "#f0c94f",
            "stroke_width": 1.0,
            "opacity": 0.88,
            "size_scale": 0.92,
        },
        "reported": {
            "shape": "ring",
            "fill": "none",
            "stroke": "#9ba5a6",
            "stroke_width": 1.0,
            "opacity": 0.86,
            "size_scale": 0.84,
        },
        "none": {
            "shape": "ring",
            "fill": "none",
            "stroke": "#9ba5a6",
            "stroke_width": 0.9,
            "opacity": 0.76,
            "size_scale": 0.68,
        },
        "unknown": {
            "shape": "cross",
            "stroke": "#cc0000",
            "stroke_width": 1.0,
            "opacity": 0.7,
            "size_scale": 1.0,
        },
    }
    return key, styles.get(key, styles["unknown"])


def network_line_style(trace):
    name = str(trace.get("name") or "").strip().lower()
    line = trace.get("line", {})
    width = float(line.get("width") or 0)

    if width <= 0:
        return None

    if name in {"covered", "uncovered"}:
        return {
            "layer": 0,
            "color": "#8b9ba3",
            "width": 0.85 if width <= 0.8 else 1.25,
            "opacity": 0.65,
            "dash": "",
        }

    facility_styles = {
        "protected": ("#ffc0cb", 2.65, 1.0, ""),
        "buffered": ("#ffc0cb", 2.3, 0.98, "8 4"),
        "bike": ("#ffc0cb", 2.1, 0.96, ""),
        "neighborhood": ("#ffc0cb", 1.9, 0.94, "5 4"),
        "shared": ("#ffc0cb", 1.55, 0.9, "2 4"),
    }
    if name in facility_styles:
        color, styled_width, opacity, dash = facility_styles[name]
        return {
            "layer": 1,
            "color": color,
            "width": styled_width,
            "opacity": opacity,
            "dash": dash,
        }

    return {
        "layer": 1,
        "color": str(line.get("color") or "#d8dee0"),
        "width": width,
        "opacity": 0.85,
        "dash": "",
    }


def bike_facility_key(row):
    return str(row.get("DISPLAYROU_CLEAN") or row.get("DISPLAYROU") or "OTHER").strip().upper()


def bike_facility_style(facility):
    styles = {
        "PROTECTED": {"layer": 2, "color": "#ffc0cb", "width": 2.75, "opacity": 1.0, "dash": ""},
        "NEIGHBORHOOD": {"layer": 2, "color": "#ffc0cb", "width": 1.95, "opacity": 0.96, "dash": "5 4"},
        "LOCAL": {"layer": 2, "color": "#ffc0cb", "width": 1.95, "opacity": 0.96, "dash": "5 4"},
        "BUFFERED": {"layer": 3, "color": "#ffc0cb", "width": 2.45, "opacity": 1.0, "dash": "8 4"},
        "BIKE": {"layer": 2, "color": "#ffc0cb", "width": 2.05, "opacity": 0.98, "dash": "5 2"},
        "SHARED": {"layer": 2, "color": "#ffc0cb", "width": 1.55, "opacity": 0.92, "dash": "2 4"},
    }
    return styles.get(str(facility or "").upper())


def osm_road_style(highway):
    key = str(highway or "").strip().lower()
    if key in {"motorway", "trunk"}:
        return {"layer": -3, "color": "#cfd9db", "width": 1.9, "opacity": 0.72, "dash": ""}
    if key in {"primary", "motorway_link", "trunk_link", "primary_link"}:
        return {"layer": -2, "color": "#dbe3e4", "width": 1.55, "opacity": 0.7, "dash": ""}
    if key in {"secondary", "secondary_link"}:
        return {"layer": -2, "color": "#e4e9e8", "width": 1.2, "opacity": 0.62, "dash": ""}
    if key in {"tertiary", "tertiary_link", "unclassified"}:
        return {"layer": -1, "color": "#edf0ec", "width": 0.92, "opacity": 0.52, "dash": ""}
    return {"layer": -1, "color": "#f4f4ef", "width": 0.58, "opacity": 0.34, "dash": ""}


def load_osm_roads():
    if not OSM_ROADS_FILE.exists():
        return []
    payload = read_json(OSM_ROADS_FILE)
    roads = []
    for road in payload.get("roads", []):
        projected = []
        for lon, lat in road.get("coords", []):
            projected.append(lonlat_to_utm16(float(lon), float(lat)))
        if len(projected) >= 2:
            roads.append(
                {
                    "name": road.get("name") or "",
                    "highway": road.get("highway") or "road",
                    "projected": projected,
                }
            )
    return roads


INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8


def outcode(x, y, min_x, min_y, max_x, max_y):
    code = INSIDE
    if x < min_x:
        code |= LEFT
    elif x > max_x:
        code |= RIGHT
    if y < min_y:
        code |= BOTTOM
    elif y > max_y:
        code |= TOP
    return code


def clip_segment(ax, ay, bx, by, min_x, min_y, max_x, max_y):
    code_a = outcode(ax, ay, min_x, min_y, max_x, max_y)
    code_b = outcode(bx, by, min_x, min_y, max_x, max_y)

    while True:
        if not (code_a | code_b):
            return (ax, ay), (bx, by)
        if code_a & code_b:
            return None

        code_out = code_a or code_b
        if code_out & TOP:
            x = ax + (bx - ax) * (max_y - ay) / (by - ay)
            y = max_y
        elif code_out & BOTTOM:
            x = ax + (bx - ax) * (min_y - ay) / (by - ay)
            y = min_y
        elif code_out & RIGHT:
            y = ay + (by - ay) * (max_x - ax) / (bx - ax)
            x = max_x
        else:
            y = ay + (by - ay) * (min_x - ax) / (bx - ax)
            x = min_x

        if code_out == code_a:
            ax, ay = x, y
            code_a = outcode(ax, ay, min_x, min_y, max_x, max_y)
        else:
            bx, by = x, y
            code_b = outcode(bx, by, min_x, min_y, max_x, max_y)


def clipped_projected_segments(points, min_x, min_y, max_x, max_y):
    clipped = []
    current = []
    for idx in range(len(points) - 1):
        clipped_segment = clip_segment(*points[idx], *points[idx + 1], min_x, min_y, max_x, max_y)
        if clipped_segment is None:
            if len(current) >= 2:
                clipped.append(current)
            current = []
            continue
        start, end = clipped_segment
        if not current or current[-1] != start:
            if len(current) >= 2:
                clipped.append(current)
            current = [start]
        current.append(end)
    if len(current) >= 2:
        clipped.append(current)
    return clipped


def projected_bbox(points):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_network_plot_figures():
    figure_module = types.ModuleType("plotly.graph_objs._figure")

    class Figure(dict):
        pass

    figure_module.Figure = Figure
    sys.modules.setdefault("plotly", types.ModuleType("plotly"))
    sys.modules.setdefault("plotly.graph_objs", types.ModuleType("plotly.graph_objs"))
    sys.modules["plotly.graph_objs._figure"] = figure_module

    with open(DATA / "precomputed_network_plots.pkl", "rb") as f:
        raw = pickle.load(f)

    return {name: decode_typed_arrays(fig) for name, fig in raw.items()}


def crash_marker_from_row(row, project, road_segments, osm_street_index, size):
    lat = number(row.get("LATITUDE"), None)
    lon = number(row.get("LONGITUDE"), None)
    if lat is None or lon is None:
        return None

    x, y = lonlat_to_utm16(lon, lat)
    px, py = project(x, y)
    if px < 0 or px > size or py < 0 or py > size:
        return None

    severity = row.get("MOST_SEVERE_INJURY", "UNKNOWN")
    severity_key, _style = severity_marker_style(severity)
    cause = (row.get("PRIM_CONTRIBUTORY_CAUSE") or "UNKNOWN").strip()
    street = nearest_osm_street_label(x, y, osm_street_index) or nearest_street_label(lon, lat, road_segments)
    return {
        "xPct": round(px / size, 6),
        "yPct": round(py / size, 6),
        "date": (row.get("CRASH_DATE") or "").strip(),
        "cause": cause.title() if cause else "Unknown",
        "severity": severity.title() if severity else "Unknown",
        "severityKey": severity_key,
        "street": street,
    }


def figure_to_network_plot(
    fig,
    area_name,
    crash_rows_by_area,
    road_segments,
    bike_rows_by_area,
    osm_roads=None,
    osm_street_index=None,
    size=300,
):
    traces = fig.get("data", [])
    points_x = []
    points_y = []
    for trace in traces:
        xs = trace.get("x")
        ys = trace.get("y")
        if xs is None or ys is None:
            continue
        for x, y in zip(xs, ys):
            if x is None or y is None:
                continue
            points_x.append(float(x))
            points_y.append(float(y))
    for row in crash_rows_by_area.get(area_name, []):
        lat = number(row.get("LATITUDE"), None)
        lon = number(row.get("LONGITUDE"), None)
        if lat is None or lon is None:
            continue
        crash_x, crash_y = lonlat_to_utm16(lon, lat)
        points_x.append(crash_x)
        points_y.append(crash_y)
    for row in bike_rows_by_area.get(area_name, []):
        for segment in parse_wkt_segments(row.get("geometry") or row.get("the_geom") or ""):
            for x, y in segment:
                points_x.append(float(x))
                points_y.append(float(y))

    if not points_x or not points_y:
        return {
            "svg": f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg"></svg>',
            "crashMarkers": [],
        }

    min_x, max_x = min(points_x), max(points_x)
    min_y, max_y = min(points_y), max(points_y)
    padding = 12
    plot_width = max(max_x - min_x, 1e-9)
    plot_height = max(max_y - min_y, 1e-9)
    drawable_size = size - padding * 2
    scale = min(drawable_size / plot_width, drawable_size / plot_height)
    offset_x = (size - plot_width * scale) / 2
    offset_y = (size - plot_height * scale) / 2

    def project(x, y):
        px = round(offset_x + (float(x) - min_x) * scale)
        py = round(size - offset_y - (float(y) - min_y) * scale)
        return px, py

    grouped = defaultdict(list)
    label_candidates = []
    crash_markers = []

    if osm_roads:
        clip_padding = 28 / scale
        clip_min_x = min_x - clip_padding
        clip_max_x = max_x + clip_padding
        clip_min_y = min_y - clip_padding
        clip_max_y = max_y + clip_padding
        for road in osm_roads:
            road_min_x, road_min_y, road_max_x, road_max_y = projected_bbox(road["projected"])
            if (
                road_max_x < clip_min_x
                or road_min_x > clip_max_x
                or road_max_y < clip_min_y
                or road_min_y > clip_max_y
            ):
                continue

            style = osm_road_style(road.get("highway"))
            clipped_segments = clipped_projected_segments(
                road["projected"],
                clip_min_x,
                clip_min_y,
                clip_max_x,
                clip_max_y,
            )
            for segment in clipped_segments:
                pts = []
                previous = None
                for x, y in segment:
                    projected_point = project(x, y)
                    if projected_point == previous:
                        continue
                    pts.append(f"{projected_point[0]},{projected_point[1]}")
                    previous = projected_point
                if len(pts) < 2:
                    continue
                grouped[(
                    style["layer"],
                    style["color"],
                    round(style["width"], 2),
                    style["opacity"],
                    style["dash"],
                )].append(
                    f'<polyline points="{" ".join(pts)}" fill="none" />'
                )

                if road.get("name") and road.get("highway") in {"primary", "secondary", "tertiary"}:
                    mid = segment[len(segment) // 2]
                    label_x, label_y = project(*mid)
                    label_candidates.append((len(segment), road["name"], label_x, label_y))

    for trace in traces:
        xs = trace.get("x")
        ys = trace.get("y")
        if xs is None or ys is None:
            continue
        mode = str(trace.get("mode") or "")
        if "markers" in mode:
            continue
        trace_name = str(trace.get("name") or "").strip().lower()
        if trace_name not in {"covered", "uncovered"}:
            continue

        style = network_line_style(trace)
        if style is None:
            continue
        pts = []
        for x, y in zip(xs, ys):
            if x is None or y is None:
                continue
            px, py = project(x, y)
            pts.append(f"{px},{py}")
        if len(pts) < 2:
            continue
        grouped[(
            style["layer"],
            style["color"],
            round(style["width"], 2),
            style["opacity"],
            style["dash"],
        )].append(
            f'<polyline points="{" ".join(pts)}" fill="none" />'
        )

    rendered_lane_miles = defaultdict(float)
    for row in bike_rows_by_area.get(area_name, []):
        facility = bike_facility_key(row)
        style = bike_facility_style(facility)
        if style is None:
            continue
        rendered_any_segment = False
        for segment in parse_wkt_segments(row.get("geometry") or row.get("the_geom") or ""):
            pts = []
            previous = None
            for x, y in segment:
                projected_point = project(x, y)
                if projected_point == previous:
                    continue
                pts.append(f"{projected_point[0]},{projected_point[1]}")
                previous = projected_point
            if len(pts) < 2:
                continue
            grouped[(
                style["layer"],
                style["color"],
                round(style["width"], 2),
                style["opacity"],
                style["dash"],
            )].append(
                f'<polyline points="{" ".join(pts)}" fill="none" />'
            )
            rendered_any_segment = True
        if rendered_any_segment:
            rendered_lane_miles[facility] += number(row.get("length_miles"))

    svg_parts = [f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">']
    for (layer, color, width, opacity, dash), shapes in sorted(grouped.items(), key=lambda item: item[0]):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        svg_parts.append(
            f'<g stroke="{color}" stroke-width="{width}" opacity="{opacity}"{dash_attr} '
            f'stroke-linecap="round" stroke-linejoin="round">'
            + "".join(shapes)
            + "</g>"
        )
    used_labels = set()
    label_shapes = []
    for _length, label, label_x, label_y in sorted(label_candidates, reverse=True):
        normalized = re.sub(r"\s+", " ", label.strip())
        if not normalized or normalized in used_labels:
            continue
        used_labels.add(normalized)
        short_label = normalized[:20]
        label_shapes.append(
            f'<text x="{label_x}" y="{label_y}" fill="#f4f4f2" opacity="0.34" '
            f'font-size="8" font-weight="700" text-anchor="middle" '
            f'paint-order="stroke" stroke="#111820" stroke-width="2" stroke-opacity="0.42">'
            f'{escape_xml(short_label)}</text>'
        )
        if len(label_shapes) >= 4:
            break
    if label_shapes:
        svg_parts.append('<g class="osm-road-labels">' + "".join(label_shapes) + "</g>")
    svg_parts.append("</svg>")
    for row in crash_rows_by_area.get(area_name, []):
        marker = crash_marker_from_row(row, project, road_segments.get(area_name, []), osm_street_index, size)
        if marker is not None:
            crash_markers.append(marker)
    return {
        "svg": "".join(svg_parts),
        "crashMarkers": crash_markers,
        "laneMiles": {
            "Protected": rendered_lane_miles.get("PROTECTED", 0),
            "Local": rendered_lane_miles.get("NEIGHBORHOOD", 0) + rendered_lane_miles.get("LOCAL", 0),
            "Buffered": rendered_lane_miles.get("BUFFERED", 0),
            "Painted": rendered_lane_miles.get("BIKE", 0),
            "Shared": rendered_lane_miles.get("SHARED", 0),
        },
    }


def build_city_outline(grid):
    if scale_geom is None or translate_geom is None or shape is None or unary_union is None:
        existing = OUT / "atlas-data.json"
        if existing.exists():
            try:
                return read_json(existing).get("cityOutline", [])
            except Exception:
                return []
        return []

    places = read_json(DATA / "chicago_places.geojson")["features"]
    city_geoms = [
        shape(feature["geometry"])
        for feature in places
        if feature.get("properties", {}).get("NAME") == "Chicago"
    ]
    city_outline = unary_union(city_geoms)

    x_vals = [item["gridloc"][0] for item in grid]
    y_vals = [item["gridloc"][1] for item in grid]
    xmin, xmax = min(x_vals) - 1, max(x_vals) + 1
    ymin, ymax = min(y_vals) - 1, max(y_vals) + 1
    carto_w = xmax - xmin
    carto_h = ymax - ymin

    city_bounds = city_outline.bounds
    outline_w = city_bounds[2] - city_bounds[0]
    outline_h = city_bounds[3] - city_bounds[1]
    scale_factor = min(carto_w / outline_w, carto_h / outline_h) + 0.1

    scaled = scale_geom(
        city_outline,
        xfact=scale_factor * 0.85,
        yfact=-scale_factor * 1.15,
        origin="center",
    )

    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2
    translated = translate_geom(
        scaled,
        xoff=center_x - (scaled.bounds[0] + scaled.bounds[2]) / 2 - 0.9,
        yoff=center_y - (scaled.bounds[1] + scaled.bounds[3]) / 2 + 0.2,
    )

    polygons = [translated] if translated.geom_type == "Polygon" else list(translated.geoms)
    rings = []
    for polygon in polygons:
        rings.append([[round(x, 4), round(y, 4)] for x, y in polygon.exterior.coords])
    return rings


def validate_output(output, grid, crash_rows, citywide_stats):
    errors = []
    areas = output.get("areas", [])
    network_plots = output.get("networkPlots", {})
    area_names = [area.get("name") for area in areas]
    grid_names = [item.get("name") for item in grid]

    if len(areas) != len(grid):
        errors.append(f"Expected {len(grid)} areas from grid, generated {len(areas)}")

    missing_from_output = sorted(set(grid_names) - set(area_names))
    extra_in_output = sorted(set(area_names) - set(grid_names))
    if missing_from_output:
        errors.append(f"Missing generated area(s): {', '.join(missing_from_output)}")
    if extra_in_output:
        errors.append(f"Unexpected generated area(s): {', '.join(extra_in_output)}")

    missing_plots = sorted(set(area_names) - set(network_plots))
    if missing_plots:
        errors.append(f"Missing network plot(s): {', '.join(missing_plots)}")

    total_crashes = sum(int(area.get("totalCrashes") or 0) for area in areas)
    source_crashes = int(citywide_stats["crashes_total"])
    if total_crashes != source_crashes:
        errors.append(f"Community crash total {total_crashes} != citywide source total {source_crashes}")

    severe_crashes = sum(int(area.get("severeCrashes") or 0) for area in areas)
    source_severe = int(citywide_stats["crashes_severe"])
    if severe_crashes != source_severe:
        errors.append(f"Community severe total {severe_crashes} != citywide source total {source_severe}")

    crash_rows_with_area = sum(1 for row in crash_rows if row.get("CArea"))
    if total_crashes != crash_rows_with_area:
        errors.append(f"Community crash total {total_crashes} != source rows with community area {crash_rows_with_area}")

    crash_marker_count = int(output.get("meta", {}).get("crashMarkerCount") or 0)
    if crash_marker_count != total_crashes:
        errors.append(f"Network crash marker total {crash_marker_count} != community crash total {total_crashes}")

    for area in areas:
        name = area.get("name", "Unknown")
        injury_total = sum(int(count or 0) for count in area.get("injuries", {}).values())
        if injury_total != int(area.get("totalCrashes") or 0):
            errors.append(f"{name}: injury total {injury_total} != total crashes {area.get('totalCrashes')}")
        plot_lane_miles = network_plots.get(name, {}).get("laneMiles", {})
        for lane_label, miles in area.get("laneMiles", {}).items():
            plotted_miles = number(plot_lane_miles.get(lane_label))
            if abs(number(miles) - plotted_miles) > 0.01:
                errors.append(
                    f"{name}: plotted {lane_label} miles {plotted_miles:.2f} != legend/chart miles {number(miles):.2f}"
                )
        if number(area.get("roadMiles")) <= 0:
            errors.append(f"{name}: roadMiles must be positive")
        if not 0 <= int(area.get("bikeRank", -1)) <= 4:
            errors.append(f"{name}: bikeRank must be between 0 and 4")

    if errors:
        message = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Atlas data validation failed:\n{message}")


def main():
    OUT.mkdir(exist_ok=True)
    require_source_files()

    grouped = {row["CArea"]: row for row in read_csv_rows(DATA / "grouped.csv")}
    grid = read_json(DATA / "CAreaGrid.json")
    bike_rank = read_json(DATA / "name_to_bike_rank.json")
    infrastructure = read_json(DATA / "name_to_infrastructure_score.json")
    connectivity = read_json(DATA / "name_to_network_score.json")
    road_length = read_json(DATA / "name_to_road_length.json")
    population = read_json(DATA / "community_pops.json")

    with open(DATA / "citywide_stats.pkl", "rb") as f:
        citywide_stats = pickle.load(f)

    network_figures = load_network_plot_figures()
    osm_roads = load_osm_roads()
    osm_street_index = build_osm_street_index(osm_roads)

    crash_rows = read_csv_rows(DATA / "crash_with_carea.csv")
    bike_rows = read_csv_rows(DATA / "bike_with_neigh.csv")
    road_segments = build_road_segments(bike_rows)
    crash_rows_by_area = defaultdict(list)
    for row in crash_rows:
        if row.get("CArea"):
            crash_rows_by_area[row["CArea"]].append(row)
    bike_rows_by_area = defaultdict(list)
    for row in bike_rows:
        if row.get("CArea"):
            bike_rows_by_area[row["CArea"]].append(row)

    causes = defaultdict(Counter)
    injuries = defaultdict(Counter)
    for row in crash_rows:
        area = row.get("CArea")
        if not area:
            continue
        causes[area][row.get("PRIM_CONTRIBUTORY_CAUSE", "UNKNOWN").upper()] += 1
        injuries[area][row.get("MOST_SEVERE_INJURY", "UNKNOWN").upper()] += 1

    lane_miles = defaultdict(lambda: defaultdict(float))
    for row in bike_rows:
        area = row.get("CArea")
        lane_type = row.get("DISPLAYROU_CLEAN") or row.get("DISPLAYROU") or "OTHER"
        lane_miles[area][lane_type.upper()] += number(row.get("length_miles"))

    base = []
    for item in grid:
        name = item["name"]
        stats = grouped.get(name, {})
        road = number(road_length.get(name))
        lanes = lane_miles[name]
        lane_total = sum(lanes.values())
        coverage = lane_total / road if road else 0
        severe_rate = number(stats.get("severe_rate"))
        base.append(
            {
                "name": name,
                "abbrev": abbrev(name),
                "gridX": item["gridloc"][0],
                "gridY": item["gridloc"][1],
                "population": int(number(population.get(name), 0)),
                "totalCrashes": int(number(stats.get("total_crashes"))),
                "bikeCrashes": int(number(stats.get("total_crashes"))),
                "severeCrashes": int(number(stats.get("severe_crashes"))),
                "severeRate": severe_rate,
                "bikeRank": int(number(bike_rank.get(name))),
                "infrastructure": number(infrastructure.get(name)),
                "connectivity": number(connectivity.get(name)),
                "roadMiles": road,
                "laneMiles": {
                    "Protected": lanes.get("PROTECTED", 0),
                    "Local": lanes.get("NEIGHBORHOOD", 0),
                    "Buffered": lanes.get("BUFFERED", 0),
                    "Painted": lanes.get("BIKE", 0),
                    "Shared": lanes.get("SHARED", 0),
                },
                "laneTotal": lane_total,
                "coverage": coverage,
                "topCauses": [
                    {"name": label.title(), "count": count}
                    for label, count in causes[name].most_common(5)
                ],
                "injuries": dict(injuries[name]),
            }
        )

    severe_values = [area["severeRate"] for area in base]
    coverage_values = [area["coverage"] for area in base]
    max_severe = max(severe_values) or 1
    max_coverage = max(coverage_values) or 1

    for area in base:
        risk_norm = area["severeRate"] / max_severe
        coverage_norm = area["coverage"] / max_coverage
        area["coveragePercentile"] = percentile_rank(coverage_values, area["coverage"])
        area["riskPercentile"] = percentile_rank(severe_values, area["severeRate"])
        area["mismatch"] = round((risk_norm * (1 - coverage_norm)) * 100, 1)

    for field, rank_name, reverse in [
        ("mismatch", "mismatchRank", True),
        ("coverage", "coverageRank", True),
        ("severeRate", "riskRank", True),
        ("bikeRank", "bikeabilityRank", True),
    ]:
        for idx, area in enumerate(sorted(base, key=lambda a: a[field], reverse=reverse), start=1):
            area[rank_name] = idx

    network_plots = {
        name: figure_to_network_plot(
            fig,
            name,
            crash_rows_by_area,
            road_segments,
            bike_rows_by_area,
            osm_roads,
            osm_street_index,
        )
        for name, fig in network_figures.items()
    }
    crash_marker_count = sum(len(plot.get("crashMarkers", [])) for plot in network_plots.values())
    severe_marker_count = sum(
        1
        for plot in network_plots.values()
        for marker in plot.get("crashMarkers", [])
        if marker.get("severityKey") in {"fatal", "severe"}
    )

    citywide_causes_counter = Counter()
    for v in causes.values():
        citywide_causes_counter.update(v)
        
    citywide_injuries = defaultdict(int)
    for area in base:
        for k, v in area["injuries"].items():
            citywide_injuries[k] += v
            
    city_total = sum(area["totalCrashes"] for area in base)
    city_severe = sum(area["severeCrashes"] for area in base)

    output = {
        "generatedFrom": "bikeability_dash_app",
        "schemaVersion": SCHEMA_VERSION,
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sourceDirectory": str(DATA),
            "sourceFiles": REQUIRED_SOURCE_FILES,
            "communityCount": len(base),
            "crashRowsWithCommunityArea": sum(1 for row in crash_rows if row.get("CArea")),
            "bikeFacilityRowsWithCommunityArea": sum(1 for row in bike_rows if row.get("CArea")),
            "networkPlotCount": len(network_plots),
            "osmRoadCount": len(osm_roads),
            "crashMarkerCount": crash_marker_count,
            "severeCrashMarkerCount": severe_marker_count,
            "notes": [
                "Network plot roads use an optional static OpenStreetMap centerline basemap under the bike-lane overlay when data/osm_chicago_roads.json is present.",
                "Network plot crash hotspots include all reported injury severities from crash_with_carea.csv.",
                "City outline is reused from the existing atlas-data.json when Shapely is unavailable.",
            ],
        },
        "citywide": {
            "crashes": int(citywide_stats["crashes_total"]),
            "bikeCrashes": int(citywide_stats["crashes_total"]),
            "severe": int(citywide_stats["crashes_severe"]),
            "roads": round(float(citywide_stats["roads_total"]), 1),
            "population": sum(area["population"] for area in base),
            "totalCrashes": city_total,
            "severeRate": city_severe / city_total if city_total else 0,
            "topCauses": [
                {"name": label.title(), "count": count}
                for label, count in citywide_causes_counter.most_common(5)
            ],
            "injuries": dict(citywide_injuries),
        },
        "cityOutline": build_city_outline(grid),
        "areas": base,
        "networkPlots": network_plots,
    }
    validate_output(output, grid, crash_rows, citywide_stats)
    with open(OUT / "atlas-data.json", "w") as f:
        json.dump(output, f, separators=(",", ":"))
    print(f"Wrote {OUT / 'atlas-data.json'} with {len(base)} community areas")
    print(f"Validated {output['citywide']['crashes']} crashes and {len(network_plots)} network plots")


if __name__ == "__main__":
    main()
