import os
import json
import pickle
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.affinity import scale as scale_geom, translate as translate_geom
from dash import Dash, dcc, html, Input, Output, State, ctx
from matplotlib.colors import Normalize, LinearSegmentedColormap

# === Import from shared and layout whatever ===
from shared import viz_df,causes_dict, injuries_dict, get_bike_coverage_plotly, translated, COLOR_GRADIENT_MAP, COLOR_INJURY, COLOR_EDGE, COLOR_TEXT, COLOR_INJURY_TEXT, COLOR_CITY, norm, rgba_to_plotly_color
from layout import layout, fig, empty_plot


# === Dash App init ===
app = Dash(__name__)
server = app.server
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

    if selected_bin is not None and not carea_name:
        return html.Div([
            html.P(f"Highlighting Bikeability Bin {selected_bin + 1}. Click a community to explore."),
        ], style={'paddingBottom': '200px'})

    if not carea_name:
        return html.Div([
            html.P("Click a community area or select from the dropdown."),
        ], style={'paddingBottom': '200px'})


    

     

    causes = causes_dict.get(carea_name, [])
    injuries = injuries_dict.get(carea_name, {})
    '''   # --- Bike lane styles ---
    lane_styles = {
        'PROTECTED':    {'color': 'navy', 'dash': 'solid'},
        'BUFFERED':     {'color': 'navy', 'dash': '8px 2px'},
        'NEIGHBORHOOD': {'color': 'navy', 'dash': 'dashdot'},
        'BIKE':         {'color': 'navy', 'dash': '5px 2px'},
        'SHARED':       {'color': 'navy', 'dash': '2px 5px'}
    }'''


    return html.Div([
    html.H3(carea_name.title()),

    html.P(f"👥 Population: ~{int(round(row['population'], -3))}"),
    html.P(f"ꈨꈨ Roads: ~{int(row['road_length'])} mi"),
    html.P(f"💥 Reported Crashes: {row['total_crashes']}"),

    html.P("📌 Top Causes:", style={'marginLeft': '15px'}),
    html.Ul([
    html.Li(c.title(), style={'color': '#666'}) for c in causes
    ]),

    html.P(f"🩸 Severe Injuries: {row['severe_crashes']} ({int(row['severe_rate'] * 100)}%)", style={'marginLeft': '15px'}),
    html.P("🩹 Injury Breakdown:", style={'marginLeft': '15px'}),
    html.Ul([
        html.Li([
            html.Span(
                f"{k.title()}" + (" (Severe):" if k.upper() in ['FATAL', 'INCAPACITATING INJURY'] else ":"),
                style={'color': '#666'}
            ),
            f" {v}"
        ])
        for k, v in injuries.items()
    ]),

    html.Hr(style={'margin': '12px 0'}),

    html.P(f"🚴 Bikeability Rank: {row['bike_rank']}/5", style={'marginLeft': '10px'}),
    html.P("🛠️ Infrastructure (Bike Lanes):", style={'marginLeft': '15px'}),
    
    html.Ul([
    # PROTECTED — solid
    html.Li([
        html.Div(style={
            'display': 'inline-block',
            'width': '30px',
            'height': '8px',
            'borderTop': '2px solid navy',
            'marginRight': '8px',
            'transform': 'translateY(+3.5px)'
        }),
        html.Span("Protected:", style={'color': '#666'}),
        f" {round(row['PROTECTED_MI'], 1)} mi"
    ]) if 'PROTECTED_MI' in row else None,

    # BUFFERED — longdash
    html.Li([
        html.Div(style={
            'display': 'inline-block',
            'width': '30px',
            'height': '8px',
            'borderTop': '2px solid navy',
            'borderImage': 'repeating-linear-gradient(to right, navy 0 8px, transparent 8px 10px) 100% 1',
            'marginRight': '8px',
            'transform': 'translateY(+3.5px)'
        }),
        html.Span("Buffered:", style={'color': '#666'}),
        f" {round(row['BUFFERED_MI'], 1)} mi"
    ]) if 'BUFFERED_MI' in row else None,

    # NEIGHBORHOOD — dashdot
    html.Li([
        html.Div(style={
            'display': 'inline-block',
            'width': '30px',
            'height': '8px',
            'borderTop': '2px solid navy',
            'borderImage': 'repeating-linear-gradient(to right, navy 0 6px, transparent 6px 8px, navy 8px 10px, transparent 10px 12px) 100% 1',
            'marginRight': '8px',
            'transform': 'translateY(+3.5px)'
        }),
        html.Span("Neighborhood:", style={'color': '#666'}),
        f" {round(row['NEIGHBORHOOD_MI'], 1)} mi"
    ]) if 'NEIGHBORHOOD_MI' in row else None,

    # BIKE — dashed
    html.Li([
        html.Div(style={
            'display': 'inline-block',
            'width': '30px',
            'height': '8px',
            'borderTop': '2px solid navy',
            'borderImage': 'repeating-linear-gradient(to right, navy 0 5px, transparent 5px 6px) 100% 1',
            'marginRight': '8px',
            'transform': 'translateY(+3.5px)'
        }),#666
        html.Span("Bike:", style={'color': '#666'}),
        f" {round(row['BIKE_MI'], 1)} mi"
    ]) if 'BIKE_MI' in row else None,

    # SHARED — sparse pattern
    html.Li([
        html.Div(style={
            'display': 'inline-block',
            'width': '30px',
            'height': '8px',
            'borderTop': '2px solid navy',
            'borderImage': 'repeating-linear-gradient(to right, navy 0 2px, transparent 2px 5px) 100% 1',
            'marginRight': '8px',
            'transform': 'translateY(+3.5px)'
        }),
        html.Span("Shared:", style={'color': '#666'}),
        f" {round(row['SHARED_MI'], 1)} mi"
    ]) if 'SHARED_MI' in row else None,
    ], style={
        'listStyleType': 'none',
        'paddingLeft': '0',
        'marginLeft': '20px'
    }),

    

    html.P(f"🌐 Network Score: {round(row['network_score'], 2)}", style={'marginLeft': '15px'}),
    ])


from dash import Output, Input
from copy import deepcopy


@app.callback(
    Output('network-coverage', 'figure'),
    Input('carea-dropdown', 'value')
)
def update_network_plot(carea_name):
    if not carea_name or str(carea_name).startswith('bin_'):
        return empty_plot()  #return clean blank

    return get_bike_coverage_plotly(carea_name)

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
        is_match = int(row['bike_rank']) == selected_bin
        opacity_val = 1.0 if is_match else 0.3

        # Each community contributes 3 shapes, starting at i*3
        base_idx = i * 3

        for j in range(3):  # apply to all 3 shapes
            updated_fig['layout']['shapes'][base_idx + j]['opacity'] = opacity_val

    return updated_fig



#app.py finish 
fig.update_layout(
    plot_bgcolor='rgba(0,0,0,0)'    # Remove plot area background
)
import warnings
warnings.filterwarnings("ignore")


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5002)
