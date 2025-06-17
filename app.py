import os
import json
import pickle
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.affinity import scale as scale_geom, translate as translate_geom
from dash import Dash, dcc, html, Input, Output, State, ctx
from matplotlib.colors import Normalize, LinearSegmentedColormap
from shared import viz_df,causes_dict, injuries_dict, translated, COLOR_GRADIENT_MAP, COLOR_INJURY, COLOR_EDGE, COLOR_TEXT, COLOR_INJURY_TEXT, COLOR_CITY, norm, rgba_to_plotly_color

# === Dash App init ===
app = Dash(__name__)
server = app.server
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
    from dash import ctx
    triggered = ctx.triggered_id
    carea_name = None

    if triggered == 'cartogram' and clickData:
        carea_name = clickData['points'][0]['customdata']
    elif triggered == 'carea-dropdown' and dropdown_value:
        carea_name = dropdown_value

    if not carea_name:
        return html.Div([
        html.P("Click a community area or select from the dropdown."),
        ], style={'paddingBottom': '200px'}) 

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
        html.Ul([html.Li(f"{k.title()}: {int(row[k])}") for k in ['PROTECTED','BUFFERED', 'BIKE', 'SHARED','NEIGHBORHOOD'] if k in row]), 
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



