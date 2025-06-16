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

with open(os.path.join(data_path, "CAreaGrid.pkl"), "rb") as f:
    CAreaGrid = pickle.load(f)

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
places = gpd.read_file("https://www2.census.gov/geo/tiger/TIGER2022/PLACE/tl_2022_17_place.zip")
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

# === Dash App init ===
app = Dash(__name__)

# === Import layout + fig ===
from layout import layout

app.layout = layout

# === Callbacks ===
@app.callback(
    Output('info-panel', 'children'),
    Input('cartogram', 'clickData'),
    Input('carea-dropdown', 'value')
)
def update_info(clickData, dropdown_value):
    triggered = ctx.triggered_id
    carea_name = None

    if triggered == 'cartogram' and clickData:
        carea_name = clickData['points'][0]['customdata']
    elif triggered == 'carea-dropdown' and dropdown_value:
        carea_name = dropdown_value

    if not carea_name:
        return "Click a community area or select from the dropdown."

    row = viz_df[viz_df['CArea'] == carea_name].iloc[0]
    causes = causes_dict.get(carea_name, [])
    injuries = injuries_dict.get(carea_name, {})

    return html.Div([
        html.H3(carea_name.title()),
        html.P(f"👥 Population: ~{int(round(row['population'], -3))}"),
        html.P(f"ꈨꈨ Road Length: {int(row['road_length'])} km"),
        html.P(f"💥 Total Crashes: {row['total_crashes']}"),
        html.P("📌 Top Causes:"),
        html.Ul([html.Li(c.title()) for c in causes]),
        html.P(f"🩸 Serious Injuries: {row['serious_crashes']} ({int(row['serious_rate'] * 100)}%)"),
        html.P("🩹 Injury Breakdown:"),
        html.Ul([html.Li(f"{k.title()}: {v}") for k, v in injuries.items()]),
        html.P("🛣️ Bike Lanes:"),
        html.Ul([html.Li(f"{k.title()}: {int(row[k])}") for k in ['PROTECTED', 'BUFFERED', 'BIKE', 'SHARED', 'NEIGHBORHOOD'] if k in row]),
        html.P(f"🚴 Bikeability Score: {row['bike_score']}/5"),
    ])

@app.callback(
    Output('carea-dropdown', 'value'),
    Input('cartogram', 'clickData'),
    State('carea-dropdown', 'value')
)
def autofill_dropdown(clickData, current_value):
    if clickData:
        return clickData['points'][0]['customdata']
    return current_value

# === Run ===
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
