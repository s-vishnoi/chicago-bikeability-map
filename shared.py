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


#paste below 



# Filter to Chicago
city_gdf = places[places['NAME'] == 'Chicago']
city_outline = city_gdf.unary_union

from shapely.affinity import scale as scale_geom, translate as translate_geom
from shapely.geometry import box

# Compute cartogram bounding box
x_vals = [carea.gridloc[0] for carea in CAreaGrid]
y_vals = [carea.gridloc[1] for carea in CAreaGrid]
xmin, xmax = min(x_vals) - 1, max(x_vals) + 1
ymin, ymax = min(y_vals) - 1, max(y_vals) + 1
carto_w = xmax - xmin
carto_h = ymax - ymin

# Get bounds of city
city_bounds = city_outline.bounds
outline_w = city_bounds[2] - city_bounds[0]
outline_h = city_bounds[3] - city_bounds[1]

# Compute scale factors
scale_x = carto_w / outline_w
scale_y = carto_h / outline_h
scale_factor = min(scale_x, scale_y)+0.1

# Apply transformation
xfact = scale_factor * 0.85  # tweak x compression
yfact = -scale_factor * 1.15  # flip y
scaled = scale_geom(city_outline, xfact=xfact, yfact=yfact, origin='center')

center_x = (xmin + xmax) / 2
center_y = (ymin + ymax) / 2

translated = translate_geom(
    scaled,
    xoff=center_x - (scaled.bounds[0] + scaled.bounds[2]) / 2 - 0.9,
    yoff=center_y - (scaled.bounds[1] + scaled.bounds[3]) / 2 +0.2
)
def name_to_abbrev(n):
    # simple abbreviator for capitalized names

    abrv = ""
    words = n.split()
    for word in words:
        if word in ['North','South','East','West']:
            abrv += " "+word[0][0]
        elif word  == 'Mount':
            abrv += "Mt."
        elif word  == 'Park':
            abrv += " "+"Pk"
        elif word == 'Greater':
            abrv += ""
        elif word == "O'Hare":
            abrv = "ORD"
        elif word == "Heights":
            abrv += " "+"Ht"
        elif word == "Boulevard":
            abrv += " "+"Blvd"
        elif word == "Crossing":
            abrv += " "+"Cross."
        elif word == "Square":
            abrv += " "+"Sq"
        elif word == "Auburn":
            abrv += " "+"Aub."
        elif word == "Washington":
            abrv += " "+"Washingt."
        elif word == "Cragin":
            abrv += " "+"cra."
        elif word == "Ridge":
            abrv += " "+"Rdg"
        elif word == "Greenwood":
            abrv += " "+"Greenwd"
        else:
            abrv += " "+word
        """elif len(abrv) > 2:
            abrv += word[0]
        else:
            cons = [x for x in word.lower()[1:] if x not in "aeiou"]
            abrv += word[0][0] + cons[0]"""
    return abrv

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LinearSegmentedColormap
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, ctx


# Define colors
COLOR_GRADIENT_MAP = LinearSegmentedColormap.from_list("pink_to_blue", ['#FFC0CB', '#418CC0'])
COLOR_INJURY = 'darkred'
COLOR_EDGE = '#B3DDF2'
COLOR_TEXT = "#1A1A1A"
COLOR_INJURY_TEXT = "ivory"
COLOR_CITY = 'rgba(160, 160, 160, 0.5)'

def rgba_to_plotly_color(rgba):
    r, g, b, a = rgba
    return f'rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {a:.2f})'

norm = Normalize(vmin=0, vmax=5)

# Group bike lane types
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





# Build viz data
viz_data = []
for carea in CAreaGrid:
    name = carea.name
    total = grouped.loc[grouped['CArea'] == name, 'total_crashes'].values[0]
    serious = grouped.loc[grouped['CArea'] == name, 'serious_crashes'].values[0]
    share = grouped.loc[grouped['CArea'] == name, 'crash_rate'].values[0]
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
        'road_length':road_length,
        'population':population,
        'abbrev': abbrev,
        'crashes_share':share,

    })
viz_df = pd.DataFrame(viz_data)
viz_df = viz_df.merge(bike_lane_summary, on='CArea', how='left').fillna(0)




miles_by_type = bike_with_neigh.groupby('CArea')[[k + '_MI' for k in ['PROTECTED','BUFFERED','BIKE','SHARED','NEIGHBORHOOD']]].sum().reset_index()
viz_df = viz_df.merge(miles_by_type, on='CArea', how='left')
#no bike areas 
missing = set(viz_df['CArea']) - set(miles_by_type['CArea'])
print("Names in viz_df but missing in miles_by_type:")
print(sorted(missing))
#fill nans foe those areas
lane_cols = [k + '_MI' for k in ['PROTECTED','BUFFERED','BIKE','SHARED','NEIGHBORHOOD']]
viz_df[lane_cols] = viz_df[lane_cols].fillna(0)

