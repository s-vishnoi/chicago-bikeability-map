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
from copy import deepcopy


# === Import from shared and layout whatever ===
from shared import viz_df,causes_dict, injuries_dict, get_bike_coverage_plotly, translated, COLOR_GRADIENT_MAP, COLOR_INJURY, COLOR_EDGE, COLOR_TEXT, COLOR_INJURY_TEXT, COLOR_CITY, norm, rgba_to_plotly_color
from layout import layout, fig, empty_plot


# === Dash App init ===
app = Dash(__name__)
server = app.server
app.layout = layout
# === Callbacks ===
selected_bin = None  # Change to an int 0–4 to simulate click behavior


# === App paste below ===
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
    causes = causes_dict.get(carea_name, [])
    injuries = injuries_dict.get(carea_name, {})
    panel_html = html.Div([
                html.H3(carea_name.title()),

                html.P(f"👥 Population: ~{int(round(row['population'], -3))}"),
                html.P(f"💥 Reported Crashes: {row['total_crashes']}"),

                html.P("Common Causes:", style={'marginLeft': '20px'}),
                html.Ul([
                html.Li(c.title(), style={'color': '#666'}) for c in causes[:3]
                ]),

                html.P("Injury Breakdown:", style={'marginLeft': '20px'}),
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
                html.P(f"🩸 Severe Injuries: {row['severe_crashes']} ({int(row['severe_rate'] * 100)}%)"),


                html.Hr(style={'margin': '12px 0'}),

                html.P(f"🚴‍♂️ Bikeability: {row['bike_rank']}/5"),
                html.P(f"ꈨꈨ Roads: ~{int(row['road_length'])} mi"),
                html.P("🛣️ Bike Lanes:"),
                
                html.Ul([
                # PROTECTED — solid
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid #0072B2',
                        'marginRight': '8px',
                        'marginTop': '0px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Protected:", style={'color': '#666'}),
                    f" {round(row['PROTECTED_MI'], 1)} mi"
                ]) if 'PROTECTED_MI' in row else None,

                # NEIGHBORHOOD — dashdot
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid #0072B2',
                        'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 6px, transparent 6px 8px, navy 8px 10px, transparent 10px 12px) 100% 1',
                        'marginRight': '8px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Neighborhood:", style={'color': '#666'}),
                    f" {round(row['NEIGHBORHOOD_MI'], 1)} mi"
                ]) if 'NEIGHBORHOOD_MI' in row else None,

                # BUFFERED — longdash
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid #0072B2',
                        'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 8px, transparent 8px 10px) 100% 1',
                        'marginRight': '8px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Buffered:", style={'color': '#666'}),
                    f" {round(row['BUFFERED_MI'], 1)} mi"
                ]) if 'BUFFERED_MI' in row else None,

                

                # BIKE — dashed
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid #0072B2',
                        'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 5px, transparent 5px 6px) 100% 1',
                        'marginRight': '8px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Bike:", style={'color': '#666'}),
                    f" {round(row['BIKE_MI'], 1)} mi"
                ]) if 'BIKE_MI' in row else None,

                # SHARED — sparse pattern
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid #0072B2',
                        'borderImage': 'repeating-linear-gradient(to right, #0072B2 0 2px, transparent 2px 5px) 100% 1',
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

                html.P(f"🛠️ Infrastructure Score: {round(row['infrastructure_score'], 2)}", style={'marginLeft': '15px'}),


                html.P(f"🌐 Network Score: {round(row['network_score'], 2)}", style={'marginLeft': '15px'}),
                html.Div([
                    html.Br(),
                    html.Br(),
                    html.Br(),
                    html.P([
                        html.A(
                            "Methodology",
                            href='https://github.com/s-vishnoi/chicago-bikeability-map',
                            style={'color': '#0072B2', 'textDecoration': 'none'}
                        )
                    ], style={'margin': '0 0 4px 15px'}),  # bottom margin only, aligned left

                    html.P([
                        html.A(
                            "Suggestions?",
                            href='https://docs.google.com/forms/d/e/1FAIpQLSeFxMoI1pig3d9YPGAEFEN-uDXyC7-F7AdTir7p3XG_DYAhrg/viewform?usp=dialog',
                            style={'color': '#0072B2', 'textDecoration': 'none'}
                        )
                    ], style={'margin': '0 0 0 15px'})  # aligned left, no top margin
                ]),
                ])                
                
    
    return panel_html 
@app.callback(
    Output('cartogram', 'figure'),
    [Input('cartogram', 'clickData'),
     Input('carea-dropdown', 'value')]
)
def update_figure(clickData, dropdown_value):
    updated_fig = deepcopy(fig)

    triggered_id = ctx.triggered_id
    if triggered_id == 'cartogram' and clickData:
        custom_data = clickData['points'][0]['customdata']
    elif triggered_id == 'carea-dropdown' and dropdown_value:
        custom_data = dropdown_value
    else:
        return updated_fig

    if str(custom_data).startswith('bin_'):
        selected_bin = int(custom_data.split('_')[1])
        
        for i, (_, row) in enumerate(viz_df.iterrows()):
            is_match = int(row['bike_rank']) == selected_bin
            opacity_val = 1.0 if is_match else 0.3
            base_idx = i * 3
            for j in range(3):
                updated_fig['layout']['shapes'][base_idx + j]['opacity'] = opacity_val

        # Dim bikeability legend rectangles
        total_shapes = len(updated_fig['layout']['shapes'])
        for i in range(5):
            shape_idx = total_shapes - 5 + i
            is_match = (4 - i) == selected_bin  # Reverse order
            updated_fig['layout']['shapes'][shape_idx]['opacity'] = 1.0 if is_match else 0.25


        return updated_fig


    
    carea_name = custom_data
    network_fig = get_bike_coverage_plotly(carea_name)

    updated_fig.update_layout(
        xaxis2=dict(domain=[0.73, 0.96], anchor='y2', visible=False),
        yaxis2=dict(domain=[0.73, 0.96], anchor='x2', visible=False)
    )

    updated_fig.add_shape(
        type="path",
        path=(
            "M 0.72 0.745 "
            "Q 0.72 0.72 0.745 0.72 "
            "L 0.945 0.72 "
            "Q 0.97 0.72 0.97 0.745 "
            "L 0.97 0.945 "
            "Q 0.97 0.97 0.945 0.97 "
            "L 0.745 0.97 "
            "Q 0.72 0.97 0.72 0.945 Z"
        ),
        fillcolor='white',
        line=dict(color='lightgray', width=1),
        layer='below',
        xref='paper',
        yref='paper'
    )

    for trace in network_fig['data']:
        trace['xaxis'] = 'x2'
        trace['yaxis'] = 'y2'
        trace['showlegend'] = False  # Remove legend
        updated_fig.add_trace(trace)

    return updated_fig


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5005)
