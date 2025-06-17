import os
import json
import pickle
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.affinity import scale as scale_geom, translate as translate_geom
from dash import Dash, dcc, html, Input, Output, State, ctx
from matplotlib.colors import Normalize, LinearSegmentedColormap

# === Load data ===
data_path = os.path.join(os.path.dirname(__file__), "data")

with open(os.path.join(data_path, "CAreaGrid.json")) as f:
    carea_raw = json.load(f)

class CArea:
    def __init__(self, name, gridloc):
        self.name = name
        self.gridloc = tuple(gridloc)

CAreaGrid = [CArea(d['name'], d['gridloc']) for d in carea_raw]

grouped = pd.read_csv(os.path.join(data_path, "grouped.csv"))
bike_with_neigh = pd.read_csv(os.path.join(data_path, "bike_with_neigh.csv"))
crash_with_carea = pd.read_csv(os.path.join(data_path, "crash_with_carea.csv"))

with open(os.path.join(data_path, "name_to_bike_score.json")) as f:
    name_to_bike_score = json.load(f)
with open(os.path.join(data_path, "name_to_road_length.json")) as f:
    name_to_road_length = json.load(f)
with open(os.path.join(data_path, "community_pops.json")) as f:
    community_pops = json.load(f)

# === Load Chicago outline ===
places = gpd.read_file(os.path.join(data_path, "chicago_places.geojson"))
city_gdf = places[places['NAME'] == 'Chicago']
city_outline = city_gdf.unary_union

# === Cartogram transform ===
x_vals = [c.gridloc[0] for c in CAreaGrid]
y_vals = [c.gridloc[1] for c in CAreaGrid]
xmin, xmax = min(x_vals) - 1, max(x_vals) + 1
ymin, ymax = min(y_vals) - 1, max(y_vals) + 1
carto_w, carto_h = xmax - xmin, ymax - ymin

city_bounds = city_outline.bounds
outline_w, outline_h = city_bounds[2] - city_bounds[0], city_bounds[3] - city_bounds[1]
scale_factor = min(carto_w / outline_w, carto_h / outline_h) + 0.1

xfact = scale_factor * 0.85
yfact = -scale_factor * 1.15
scaled = scale_geom(city_outline, xfact=xfact, yfact=yfact, origin='center')
center_x, center_y = (xmin + xmax) / 2, (ymin + ymax) / 2
translated = translate_geom(
    scaled,
    xoff=center_x - (scaled.bounds[0] + scaled.bounds[2]) / 2 - 0.9,
    yoff=center_y - (scaled.bounds[1] + scaled.bounds[3]) / 2 + 0.2
)

# === Color settings ===
COLOR_GRADIENT_MAP = LinearSegmentedColormap.from_list("pink_to_blue", ['#FFC0CB', '#418CC0'])
COLOR_INJURY = 'darkred'
COLOR_EDGE = '#B3DDF2'
COLOR_TEXT = "#1A1A1A"
COLOR_INJURY_TEXT = "ivory"
COLOR_CITY = 'rgba(160, 160, 160, 0.3)'
norm = Normalize(vmin=0, vmax=5)

# === Utility functions ===
def rgba_to_plotly_color(rgba):
    r, g, b, a = rgba
    return f'rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {a:.2f})'

def name_to_abbrev(name):
    return ''.join(word[0] for word in name.split()).upper()

# === Derived data ===
bike_lane_summary = (
    bike_with_neigh.groupby(['CArea', 'DISPLAYROU_CLEAN'])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

causes_dict = (
    crash_with_carea[~crash_with_carea['PRIM_CONTRIBUTORY_CAUSE'].isin(['UNABLE TO DETERMINE', 'NOT APPLICABLE'])]
    .groupby(['CArea', 'PRIM_CONTRIBUTORY_CAUSE'])
    .size()
    .reset_index(name='count')
    .sort_values(['CArea', 'count'], ascending=[True, False])
    .groupby('CArea')['PRIM_CONTRIBUTORY_CAUSE']
    .apply(lambda x: x.head(5).tolist())
    .to_dict()
)

injuries_dict = (
    crash_with_carea.groupby(['CArea', 'MOST_SEVERE_INJURY'])
    .size()
    .unstack(fill_value=0)
    .to_dict(orient='index')
)

viz_data = []
for carea in CAreaGrid:
    name = carea.name
    row = grouped[grouped['CArea'] == name].iloc[0]
    total = row['total_crashes']
    serious = row['serious_crashes']
    share = row['crash_rate']
    rate = serious / total if total > 0 else 0
    bike_score = name_to_bike_score.get(name, 0)
    road_length = name_to_road_length.get(name, 0)
    population = community_pops[name]
    abbrev = name_to_abbrev(name).upper()
    x, y = carea.gridloc
    viz_data.append({
        'CArea': name, 'x': x, 'y': y,
        'total_crashes': total,
        'serious_crashes': serious,
        'serious_rate': rate,
        'bike_score': bike_score,
        'road_length': road_length,
        'population': population,
        'abbrev': abbrev,
        'crashes_share': share
    })

viz_df = pd.DataFrame(viz_data)
viz_df = viz_df.merge(bike_lane_summary, on='CArea', how='left').fillna(0)
