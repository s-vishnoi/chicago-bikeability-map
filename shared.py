import os
import json
import pickle
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.affinity import scale as scale_geom, translate as translate_geom
from dash import Dash, dcc, html, Input, Output, State, ctx
from matplotlib.colors import Normalize, LinearSegmentedColormap
import plotly.graph_objects as go

# === path- DONT replace ===
data_path = os.path.join(os.path.dirname(__file__), "data")



# === Load Chicago outline ===
places = gpd.read_file(os.path.join(data_path, "chicago_places.geojson"))

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

with open(os.path.join(data_path, "name_to_road_length.json")) as f:
    name_to_road_length = json.load(f)
with open(os.path.join(data_path, "community_pops.json")) as f:
    community_pops = json.load(f)

with open(os.path.join(data_path, "name_to_infrastructure_score.json")) as f:
    name_to_infrastructure_score = json.load(f)
with open(os.path.join(data_path,"name_to_network_score.json")) as f:
    name_to_network_score = json.load(f)
with open(os.path.join(data_path, "name_to_bike_rank.json")) as f:
    name_to_bikeability_rank = json.load(f)

with open(os.path.join(data_path, "precomputed_network_plots.pkl"), "rb") as f:
    network_plots = pickle.load(f)
with open(os.path.join(data_path,"citywide_stats.pkl"), "rb") as f:
    citywide_stats = pickle.load(f)
#citywide network fig loaded directly 

with open(os.path.join(data_path, "injury_counts_city.json")) as f:
    injury_counts_city = json.load(f)
with open(os.path.join(data_path, "top_causes_city.json")) as f:
    top_causes_city = json.load(f)





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
COLOR_EDGE = 'rgba(160, 160, 160, 0.5)'#'#B3DDF2'
COLOR_TEXT = "#1A1A1A"
COLOR_TEXT_2 = 'darkgray'
COLOR_INJURY_TEXT = "ivory"


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
    severe = grouped.loc[grouped['CArea'] == name, 'severe_crashes'].values[0]
    share = grouped.loc[grouped['CArea'] == name, 'crash_rate'].values[0]
    rate = severe / total if total > 0 else 0

    infrastructure_score = name_to_infrastructure_score.get(name, 0)
    network_score = name_to_network_score.get(name, 0)
    bike_rank = name_to_bikeability_rank.get(name, 0)
    road_length = name_to_road_length.get(name, 0)
    population = community_pops[name]
    abbrev = name_to_abbrev(name).upper()
    x, y = carea.gridloc
    viz_data.append({
        'CArea': name, 'x': x, 'y': y,
        'total_crashes': total,
        'severe_crashes': severe,
        'severe_rate': rate,
        'infrastructure_score':infrastructure_score,
        'network_score':network_score,
        'bike_rank': bike_rank,
        'road_length':road_length,
        'population':population,
        'abbrev': abbrev,
        'crashes_share':share,

    })
viz_df = pd.DataFrame(viz_data)
viz_df = viz_df.merge(bike_lane_summary, on='CArea', how='left').fillna(0)

for k in ['PROTECTED','BUFFERED','BIKE','SHARED','NEIGHBORHOOD']:
    bike_with_neigh[k + '_MI'] = bike_with_neigh.apply(
        lambda row: row['length_miles'] if row['DISPLAYROU_CLEAN'] == k else 0,
        axis=1
    )


miles_by_type = bike_with_neigh.groupby('CArea')[[k + '_MI' for k in ['PROTECTED','BUFFERED','BIKE','SHARED','NEIGHBORHOOD']]].sum().reset_index()
viz_df = viz_df.merge(miles_by_type, on='CArea', how='left')


def get_bike_coverage_plotly(carea_name):
    return network_plots.get(carea_name, go.Figure())


#no bike areas 
missing = set(viz_df['CArea']) - set(miles_by_type['CArea'])
print("Names in viz_df but missing in miles_by_type:")
print(sorted(missing))
#fill nans foe those areas
lane_cols = [k + '_MI' for k in ['PROTECTED','BUFFERED','BIKE','SHARED','NEIGHBORHOOD']]
viz_df[lane_cols] = viz_df[lane_cols].fillna(0)


injury_order = ['FATAL', 'INCAPACITATING INJURY', 'NONINCAPACITATING INJURY', 'REPORTED, NOT EVIDENT', 'NO INDICATION OF INJURY']




network_mode_panel = html.Div([
    html.H3("Citywide Biking Network"),
    html.I("Do you live in a red desert?"),

    html.Hr(style={'margin': '12px 0'}),

    html.P("Roads:"),
    html.Ul([
        html.Li([
            html.Div(style={
                'display': 'inline-block', 'width': '30px', 'height': '8px',
                'borderTop': '2px solid #009E73', 'marginRight': '8px',
                'transform': 'translateY(+3.5px)'
            }),
            html.Span("Covered: ", style={'color': '#BBBBBB'}),
            f"{int(round(citywide_stats['covered'] * 100 / (citywide_stats['covered'] + citywide_stats['uncovered']),0))}%"
        ]),
        html.Li([
            html.Div(style={
                'display': 'inline-block', 'width': '30px', 'height': '8px',
                'borderTop': '2px solid #D55E00', 'marginRight': '8px',
                'transform': 'translateY(+3.5px)'
            }),
            html.Span("Uncovered: ", style={'color': '#BBBBBB'}),
            f"{int(round(citywide_stats['uncovered'] * 100 / (citywide_stats['covered'] + citywide_stats['uncovered']),0))}%"
        ])
    ], style={'listStyleType': 'none', 'paddingLeft': '0', 'marginLeft': '20px'}),

    html.P("A covered road offers a bike lane alternative (<= 600m) travelling along a similar direction (+-45 degrees)."),

    html.P("🚲 Bike Lanes:"),
    html.Ul([
        html.Li([
            html.Div(style={
                'display': 'inline-block', 'width': '30px', 'height': '8px',
                'borderTop': '2px solid #0072B2', 'marginRight': '8px',
                'transform': 'translateY(+3.5px)'
            }),
            html.Span("Protected: ", style={'color': '#BBBBBB'}),
            f"{round(citywide_stats['PROTECTED_MI'], 1)} mi"
        ]),
        html.Li([
            html.Div(style={
                'display': 'inline-block', 'width': '30px', 'height': '8px',
                'borderTop': '2px solid #0072B2',
                'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 6px, transparent 6px 8px, #0072B2 8px 10px, transparent 10px 12px) 100% 1',
                'marginRight': '8px', 'transform': 'translateY(+3.5px)'
            }),
            html.Span("Neighborhood: ", style={'color': '#BBBBBB'}),
            f"{round(citywide_stats['NEIGHBORHOOD_MI'], 1)} mi"
        ]),
        html.Li([
            html.Div(style={
                'display': 'inline-block', 'width': '30px', 'height': '8px',
                'borderTop': '2px solid #0072B2',
                'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 8px, transparent 8px 10px) 100% 1',
                'marginRight': '8px', 'transform': 'translateY(+3.5px)'
            }),
            html.Span("Buffered: ", style={'color': '#BBBBBB'}),
            f"{round(citywide_stats['BUFFERED_MI'], 1)} mi"
        ]),
        html.Li([
            html.Div(style={
                'display': 'inline-block', 'width': '30px', 'height': '8px',
                'borderTop': '2px solid #0072B2',
                'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 5px, transparent 5px 6px) 100% 1',
                'marginRight': '8px', 'transform': 'translateY(+3.5px)'
            }),
            html.Span("Bike: ", style={'color': '#BBBBBB'}),
            f"{round(citywide_stats['BIKE_MI'], 1)} mi"
        ]),
        html.Li([
            html.Div(style={
                'display': 'inline-block', 'width': '30px', 'height': '8px',
                'borderTop': '2px solid #0072B2',
                'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 2px, transparent 2px 5px) 100% 1',
                'marginRight': '8px', 'transform': 'translateY(+3.5px)'
            }),
            html.Span("Shared: ", style={'color': '#BBBBBB'}),
            f"{round(citywide_stats['SHARED_MI'], 1)} mi"
        ]),
    ], style={'listStyleType': 'none', 'paddingLeft': '0', 'marginLeft': '20px'}),

    html.P("Note: Excludes bike trails"),
    html.Hr(style={'margin': '12px 0'}),

    html.H3("Citywide Crash Summary"),

    html.P([
        html.Span("🤕 Reported Crashes (since 2018): ", style={'color': '#BBBBBB'}),
        f"{citywide_stats['crashes_total']}"
    ]),

    html.P("Top Causes:"),
    html.Ul([
        html.Li(c.title(), style={'color': '#BBBBBB'}) for c in top_causes_city
    ]),

    html.P("Injury Breakdown:"),
    html.Ul([
        html.Li([
            html.Span(
                f"{k.title()}" + (" (Severe):" if k.upper() in ['FATAL', 'INCAPACITATING INJURY'] else ":"),
                style={'color': '#BBBBBB'}
            ),
            f" {injury_counts_city.get(k, 0)}"
        ])
        for k in injury_order if k in injury_counts_city
    ]),

    html.Hr(style={'margin': '12px 0'}),

    html.P([
        html.A("Methodology", href='https://github.com/s-vishnoi/chicago-bikeability-map',
               style={'color': '#0072B2', 'textDecoration': 'none'})
    ], style={'margin': '0 0 4px 0px'}),

    html.P([
        html.A("Suggestions?", href='', style={'color': '#0072B2', 'textDecoration': 'none'})
    ], style={'margin': '0 0 0 0px'})
])
