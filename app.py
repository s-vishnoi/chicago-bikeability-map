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
from layout import layout, fig, bin_vals

app.layout = layout
# === Callbacks ===
selected_bin = None  # Change to an int 0–4 to simulate click behavior


@app.callback(
    Output('carea-dropdown', 'value'),
    Input('cartogram', 'clickData'),
    State('carea-dropdown', 'value')
)
def autofill_dropdown(clickData, current_value):
    if clickData:
        return clickData['points'][0]['customdata']
    return current_value
@app.callback(
    Output('info-panel', 'children'),
    Input('cartogram', 'clickData'),
    Input('carea-dropdown', 'value')
)
def update_info(clickData, dropdown_value):
    triggered = ctx.triggered_id
    carea_name = None
    selected_bin = None

    if triggered == 'cartogram' and clickData:
        cd = clickData['points'][0]['customdata']
        if cd.startswith('bin_'):
            selected_bin = int(cd.split('_')[1])
        else:
            carea_name = cd
    elif triggered == 'carea-dropdown' and dropdown_value:
        carea_name = dropdown_value

    if not carea_name:
        return html.Div([
            html.P("Click a community area or select from the dropdown."),
        ], style={'paddingBottom': '200px'})

    row = viz_df[viz_df['CArea'] == carea_name].iloc[0]

    if selected_bin is not None:
        bin_min = bin_vals[::-1][selected_bin]
        bin_max = 1.0 if selected_bin == 0 else bin_vals[::-1][selected_bin - 1]
        in_bin = bin_min <= row['bike_score'] < bin_max


    

     

    causes = causes_dict.get(carea_name, [])
    injuries = injuries_dict.get(carea_name, {})

    return html.Div([
        html.H3(carea_name.title()),  
        html.P(f"👥 Population: ~{int(round(row['population'], -3))}"),
        html.P(f"ꈨꈨ Roads: ~{int(row['road_length'])} mi"),
        html.P(f"💥 Reported Crashes: {row['total_crashes']}"),
        html.P("📌 Top Causes:",style={'marginLeft': '15px'}),
        html.Ul([html.Li(c.title()) for c in causes]),
        html.P(f"🩸 Serious Injuries: {row['serious_crashes']} ({int(row['serious_rate'] * 100)}%)",style={'marginLeft': '15px'}),
        html.P("🩹 Injury Breakdown:",style={'marginLeft': '15px'}),
        html.Ul([
            html.Li(f"{k.title()}" + ("(Serious):" if k.upper() in ['FATAL', 'INCAPACITATING INJURY'] else ":") + f" {v}")
            for k, v in injuries.items()
        ]),

        html.P("🛣️ Bike Lanes (mi):"),
        html.Ul([
            html.Li(f"{k.title()}: {round(row[k + '_MI'], 1)} mi") 
            for k in ['PROTECTED','BUFFERED','NEIGHBORHOOD','BIKE', 'SHARED']
            if f"{k}_MI" in row
        ]),
        html.P(f"🚴 Bikeability: {row['bike_score']}/5",style={'marginLeft': '24px'}),   
    ])

from dash import Output, Input
from copy import deepcopy

@app.callback(
    Output('cartogram', 'figure'),
    Input('cartogram', 'clickData')
)
def update_figure(clickData):
    if not clickData or not str(clickData['points'][0]['customdata']).startswith('bin_'):
        return fig

    selected_bin = int(clickData['points'][0]['customdata'].split('_')[1])

    updated_fig = deepcopy(fig)

    # Each community has 3 shapes: background, injury bar, badge
    n_areas = len(viz_df)

    for i, (_, row) in enumerate(viz_df.iterrows()):
        is_match = int(row['bike_score']) == selected_bin
        opacity_val = 1.0 if is_match else 0.3

        # Each community contributes 3 shapes, starting at i*3
        base_idx = i * 3

        for j in range(3):  # apply to all 3 shapes
            updated_fig['layout']['shapes'][base_idx + j]['opacity'] = opacity_val

    return updated_fig




# === Run ===
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)



