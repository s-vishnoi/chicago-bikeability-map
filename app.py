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
from shared import viz_df,causes_dict, injuries_dict, get_bike_coverage_plotly,network_mode_panel, translated, COLOR_GRADIENT_MAP, COLOR_INJURY, COLOR_EDGE, COLOR_TEXT,COLOR_TEXT_2, COLOR_INJURY_TEXT, norm, rgba_to_plotly_color
from layout import layout, fig, empty_plot


# === Dash App init ===
from dash import Dash, html, dcc, Output, Input, State, ctx
import plotly.graph_objects as go
from copy import deepcopy
import numpy as np


# === Preview ===
app = Dash(
    __name__,
    assets_folder='assets',
    meta_tags=[
        {"property": "og:image", "content": "/assets/preview.png"},
        {"property": "og:title", "content": "Chicago Bike Crash Dashboard"},
        {"property": "og:description", "content": "Explore bike crash patterns and infrastructure equity in Chicago."},
        {"property": "og:type", "content": "website"},
        {"property": "og:image", "content": "https://chicago-bike-dashboard.onrender.com/assets/preview.png"},
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ]
)

server = app.server
app.config.suppress_callback_exceptions = True




app.title = "Chicago Bikeability Map"

# === Layout ===
app.layout = layout



# === APP.py ===

@app.callback(
    Output('cartogram', 'style'),
    Output('network-iframe', 'style'),
    Output('exit-network-btn', 'style'),
    Output('view-mode', 'data'),
    Input('show-network-btn', 'n_clicks'),
    Input('exit-network-btn', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_network_view(show_clicks, exit_clicks):
    triggered_id = ctx.triggered_id

    if triggered_id == 'show-network-btn':
        return (
            {'display': 'none'},  # hide Graph
            {'display': 'block',
             'width': '880px',
             'height': '1030px',
             'overflow': 'hidden', 
             'border': 'none',
             'backgroundColor': '#4A4A4A',
             'borderRadius': '8px',
             'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'},  # show iframe
            {'display': 'inline-block'},
            'network'
        )

    # on exit
    return (
        {'display': 'block',
        'width': '100%',
        'height': '100%',
        'border': 'none',
        'backgroundColor': '#4A4A4A',
        'borderRadius': '8px',
        'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'},  # show Graph
        {'display': 'none'},  # hide iframe
        {'display': 'none'},
        'community'
    )

from dash.exceptions import PreventUpdate

@app.callback(
    Output('carea-dropdown', 'value'),
    Input('cartogram', 'clickData'),
    Input('view-mode', 'data'),
    State('carea-dropdown', 'value')
)
def handle_dropdown(clickData, mode, current_value):
    triggered_id = ctx.triggered_id

    # Option 1: Clear dropdown if switching to network mode
    if triggered_id == 'view-mode' and mode == 'network':
        return None

    # Option 2: Autofill from map clicks in community mode
    if triggered_id == 'cartogram' and mode == 'community' and clickData:
        return clickData['points'][0]['customdata']

    raise PreventUpdate



@app.callback(
    Output('info-panel', 'children'),
    Input('cartogram', 'clickData'),
    Input('carea-dropdown', 'value'),
    Input('view-mode', 'data')
)
def update_info(clickData, dropdown_value, mode):
    if mode == 'network':
        return network_mode_panel
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
    injury_order = ['FATAL', 'INCAPACITATING INJURY', 'NONINCAPACITATING INJURY', 'REPORTED, NOT EVIDENT', 'NO INDICATION OF INJURY']
    panel_html = html.Div([
                html.H3(carea_name.title()),

                html.P(f"Population: ~{int(round(row['population'], -3))}"),
                html.P(f"🤕 Reported Crashes: {row['total_crashes']}"),

                html.P("Top Causes:", style={'marginLeft': '0px'}),
                html.Ul([
                html.Li(c.title(), style={'color': '#BBBBBB'}) for c in causes[:3]
                ]),

                html.P("Injury Breakdown:", style={'marginLeft': '0px'}),
                html.Ul([
                    html.Li([
                        html.Span(
                            f"{k.title()}" + (" (Severe):" if k.upper() in ['FATAL', 'INCAPACITATING INJURY'] else ":"),
                            style={'color': '#BBBBBB'}
                        ),
                        f" {injuries.get(k, 0)}"
                    ])
                    for k in injury_order if k in injuries
                ]),
                html.P(f"🩸 Severe Injuries: {row['severe_crashes']} ({int(row['severe_rate'] * 100)}%)"),


                html.Hr(style={'margin': '12px 0'}),

                html.P(f"🚲 Bikeability: {row['bike_rank']+1}/5"),
                html.P(f"Roads: ~{int(row['road_length'])} mi"),
                html.P("Bike Lanes:", style={'marginLeft': '0px'}),
                
                html.Ul([
                # PROTECTED — solid
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid lightgray',
                        'marginRight': '8px',
                        'marginTop': '0px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Protected:", style={'color': '#BBBBBB'}),
                    f" {round(row['PROTECTED_MI'], 1)} mi"
                ]) if 'PROTECTED_MI' in row else None,

                # NEIGHBORHOOD — dashdot
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid lightgray',
                        'borderImage': 'repeating-linear-gradient(to right, lightgray 0 6px, transparent 6px 8px, lightgray 8px 10px, transparent 10px 12px) 100% 1',
                        'marginRight': '8px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Neighborhood:", style={'color': '#BBBBBB'}),
                    f" {round(row['NEIGHBORHOOD_MI'], 1)} mi"
                ]) if 'NEIGHBORHOOD_MI' in row else None,

                # BUFFERED — longdash
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid lightgray',
                        'borderImage': 'repeating-linear-gradient(to right, lightgray 0 8px, transparent 8px 10px) 100% 1',
                        'marginRight': '8px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Buffered:", style={'color': '#BBBBBB'}),
                    f" {round(row['BUFFERED_MI'], 1)} mi"
                ]) if 'BUFFERED_MI' in row else None,

                

                # BIKE — dashed
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid lightgray',
                        'borderImage': 'repeating-linear-gradient(to right, lightgray 0 5px, transparent 5px 6px) 100% 1',
                        'marginRight': '8px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Bike:", style={'color': '#BBBBBB'}),
                    f" {round(row['BIKE_MI'], 1)} mi"
                ]) if 'BIKE_MI' in row else None,

                # SHARED — sparse pattern
                html.Li([
                    html.Div(style={
                        'display': 'inline-block',
                        'width': '30px',
                        'height': '8px',
                        'borderTop': '2px solid lightgray',
                        'borderImage': 'repeating-linear-gradient(to right, lightgray 0 2px, transparent 2px 5px) 100% 1',
                        'marginRight': '8px',
                        'transform': 'translateY(+3.5px)'
                    }),
                    html.Span("Shared:", style={'color': '#BBBBBB'}),
                    f" {round(row['SHARED_MI'], 1)} mi"
                ]) if 'SHARED_MI' in row else None,
                ], style={
                    'listStyleType': 'none',
                    'paddingLeft': '0',
                    'marginLeft': '20px'
                }),

                html.P(f"🛠️ Infrastructure Score: {round(row['infrastructure_score'], 2)}", style={'marginLeft': '0px'}),


                html.P(f"🌐 Network Score: {round(row['network_score'], 2)}", style={'marginLeft': '0px'}),
                html.Hr(style={'margin': '12px 0'}),
                html.Div([

                    html.P([
                        html.A(
                            "Methodology",
                            href='https://github.com/s-vishnoi/chicago-bikeability-map',
                            style={'color': 'lightgray', 'textDecoration': 'none'}
                        )
                    ], style={'margin': '0 0 4px 0px'}),  # bottom margin only, aligned left

                    html.P([
                        html.A(
                            "Suggestions?",
                            href='https://docs.google.com/forms/d/e/1FAIpQLSeFxMoI1pig3d9YPGAEFEN-uDXyC7-F7AdTir7p3XG_DYAhrg/viewform?usp=sharing&ouid=111142553725252767700',
                            style={'color': 'lightgray', 'textDecoration': 'none'}
                        )
                    ], style={'margin': '0 0 0 0px'})  # aligned left, no top margin
                ]),
                ])                
                
    
    return panel_html 
@app.callback(
    Output('cartogram', 'figure'),
    [Input('cartogram', 'clickData'),
     Input('carea-dropdown', 'value')],
     State('view-mode', 'data')
)
def update_figure(clickData, dropdown_value, mode):
    if mode != 'community':
        return fig

    triggered_id = ctx.triggered_id
    custom_data = None

    if triggered_id == 'cartogram' and clickData:
        custom_data = clickData['points'][0]['customdata']
    elif triggered_id == 'carea-dropdown' and dropdown_value:
        custom_data = dropdown_value
    else:
        return fig

    updated_fig = deepcopy(fig)

    if str(custom_data).startswith('bin_'):
        selected_bin = int(custom_data.split('_')[1])
        for i, (_, row) in enumerate(viz_df.iterrows()):
            is_match = int(row['bike_rank']) == selected_bin
            opacity_val = 1.0 if is_match else 0.3
            base_idx = i * 3
            for j in range(3):
                updated_fig['layout']['shapes'][base_idx + j]['opacity'] = opacity_val

        total_shapes = len(updated_fig['layout']['shapes'])
        for i in range(5):
            shape_idx = total_shapes - 5 + i
            is_match = (4 - i) == selected_bin
            updated_fig['layout']['shapes'][shape_idx]['opacity'] = 1.0 if is_match else 0.25

        return updated_fig

    # Add inset network plot for carea
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
        fillcolor='#606060',
        line=dict(color='lightgray', width=1),
        layer='below',
        xref='paper',
        yref='paper'
    )

    updated_fig.add_annotation(
        x=0.9,  # Center of your custom box horizontally
        y=0.715,  # Slightly below the hover box
        xref="paper",
        yref="paper",
        text="Hover to see cause",
        showarrow=False,
        font=dict(size=9, color= COLOR_TEXT_2),
        align="center",
    )
    

    for trace in network_fig['data']:
        trace['xaxis'] = 'x2'
        trace['yaxis'] = 'y2'
        trace['showlegend'] = False
        updated_fig.add_trace(trace)

    return updated_fig






