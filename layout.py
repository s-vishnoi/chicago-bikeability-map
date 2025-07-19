
import numpy as np
import plotly.graph_objects as go
from dash import dcc, html
from shared import viz_df, translated, COLOR_GRADIENT_MAP, COLOR_INJURY, COLOR_EDGE, COLOR_TEXT, COLOR_TEXT_2, COLOR_INJURY_TEXT, COLOR_CITY, norm, rgba_to_plotly_color


# Build figure
fig = go.Figure()
scale = 1

fig.update_layout(
    hoverlabel=dict(
        bgcolor="white", 
        font_color ='black',       # background
        font_size=11,
        font_family="Segoe UI, sans-serif"
    )
)



for _, row in viz_df.iterrows():
    x, y = row['x'], row['y']
    total, rate = row['total_crashes'], row['severe_rate']
    bike_rank = row['bike_rank']
    fill = rgba_to_plotly_color(COLOR_GRADIENT_MAP(norm(bike_rank)))

    w, h = scale-0.1, scale-0.1
    minx, maxx = x - 0.5 * w, x + 0.5 * w
    miny, maxy = y - 0.5 * h, y + 0.5 * h
    red_h = h * rate
    red_y0 = maxy - red_h

    fig.add_shape(type="rect", x0=minx, x1=maxx, y0=miny, y1=maxy,
                  fillcolor=fill, line=dict(color=COLOR_EDGE, width=0.5))
    stroke = 0.01  # half of 2px in coordinate space
    fig.add_shape(type="rect", x0=minx, x1=maxx , y0=red_y0, y1=maxy,
              fillcolor=COLOR_INJURY, line=dict(color=COLOR_TEXT, width=1.5))


    fig.add_annotation(x=x, y=y, text=str(total), showarrow=False,
                       font=dict(size=8, color=COLOR_TEXT))
    fig.add_annotation(x=x, y=maxy - 0.1, text=f"{int(rate * 100)}%",
                       showarrow=False, font=dict(size=8, color=COLOR_INJURY_TEXT))
    
    
    
    


    badge_text = row["abbrev"]
    badge_y = miny + 0.16
    badge_w = w * 1.1
    badge_h = h * 0.25
    fig.add_shape(type="rect", x0=x - badge_w / 2, x1=x + badge_w / 2,
                  y0=badge_y - badge_h / 2, y1=badge_y + badge_h / 2,
                  fillcolor=fill, line=dict(color=COLOR_EDGE, width=0.3))
    fig.add_annotation(x=x, y=badge_y, text=badge_text, showarrow=False,
                       font=dict(size=7.2, color=COLOR_TEXT), yanchor="middle")

    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode='markers',
        marker=dict(size=30, opacity=0),
        customdata=[row['CArea']],
        name=row['CArea'],
        hovertemplate=f"{row['CArea'].title()}<extra></extra>",
        showlegend=False, 
    ))

# Reference square
ref_x, ref_y = 3.2, 7
ref_scale, ref_rate = 1.42, 0.3
w, h = scale * ref_scale, scale * ref_scale
minx, maxx = ref_x - 0.5 * w, ref_x + 0.5 * w
miny, maxy = ref_y - 0.5 * h, ref_y + 0.5 * h
ref_red_h = h * ref_rate
ref_red_y0 = maxy - ref_red_h


fig.add_shape(type="rect", x0=minx, x1=maxx, y0=miny, y1=maxy,
              fillcolor='white', line=dict(color=COLOR_EDGE, width=0.5))
fig.add_shape(type="rect", x0=minx, x1=maxx, y0=ref_red_y0, y1=maxy,
              fillcolor=COLOR_INJURY, line=dict(color = COLOR_TEXT, width=1.8))

badge_y = miny + 0.25
badge_w = w * 1.2
badge_h = h * 0.25
fig.add_shape(type="rect", x0=ref_x - badge_w / 2, x1=ref_x + badge_w / 2,
              y0=badge_y - badge_h / 2, y1=badge_y + badge_h / 2,
              fillcolor='white', line=dict(color=COLOR_EDGE, width=0.3))
fig.add_annotation(x=ref_x, y=badge_y, text="COMMUNITY AREA",
                   showarrow=False, font=dict(size=8, color=COLOR_TEXT),
                   yanchor="middle")
fig.add_annotation(x=ref_x, y=ref_y - 0.10, text="# Bike Crashes",
                   showarrow=False, font=dict(size=9, color=COLOR_TEXT)),
fig.add_annotation(x=ref_x, y=ref_y + 0.10, text="Reported since 2018",
                   showarrow=False, font=dict(size=8, color=COLOR_TEXT_2)),
fig.add_annotation(x=ref_x , y=ref_y + 0.45, text="% Severe",
                   showarrow=False, font=dict(size=9, color=COLOR_INJURY_TEXT))



# Manual bikability legend using colored rectangles (like matplotlib)
legend_x = 13.5
legend_y_start = 5.5
legend_h = 4.0
legend_w = 0.2
n_bins = 5
bin_vals = np.linspace(0, 1, n_bins)
bin_colors = [rgba_to_plotly_color(COLOR_GRADIENT_MAP(v)) for v in bin_vals]
bin_h = legend_h / n_bins

for i, (val, color) in enumerate(zip(bin_vals[::-1], bin_colors[::-1])):
    y0 = legend_y_start + i * bin_h
    y1 = y0 + bin_h
    fig.add_shape(
        type="rect",
        x0=legend_x, x1=legend_x + legend_w,
        y0=y0, y1=y1,
        line=dict(width=0),
        fillcolor=color,
        layer="above"
    )



# Add vertical label "Bikability"
fig.add_annotation(
    x=legend_x + 0.35,
    y=legend_y_start + legend_h / 2,
    text="Bikeability",
    textangle=90,
    font=dict(size=11, color=COLOR_TEXT),
    showarrow=False
)
fig.add_annotation(
    x=legend_x + 0.1,
    y=legend_y_start + 0.9*legend_h,
    text="Lowest",
    textangle=90,
    font=dict(size=9, color=COLOR_TEXT),
    showarrow=False
)
fig.add_annotation(
    x=legend_x + 0.1,
    y=legend_y_start + 0.1*legend_h,
    text="Highest",
    textangle=90,
    font=dict(size=9, color=COLOR_TEXT),
    showarrow=False
)
for i, (val, color) in enumerate(zip(bin_vals[::-1], bin_colors[::-1])):
    flipped_bin = n_bins - 1 - i  # bin_4 (bluest) at top, bin_0 (reddest) at bottom
    y0 = legend_y_start + i * bin_h
    y1 = y0 + bin_h
    fig.add_trace(go.Scatter(
        x=[legend_x + legend_w / 2],
        y=[y0 + bin_h / 2],
        mode='markers',
        marker=dict(size=30, opacity=0),
        customdata=[f'bin_{flipped_bin}'],  # Now matches bike_rank logic
        name=f'bin_{flipped_bin}',
        hovertemplate=f"Bikeability {flipped_bin + 1}<extra></extra>",
        showlegend=False
    ))





fig.update_layout(
    clickmode='event+select',
    height=1100,
    width=900,
    #title=f"Chicago Bike Crashes, 2018-Present",
    #title_font=dict(size=16),
    xaxis=dict(visible=False),
    yaxis=dict(visible=False, autorange="reversed"),
    margin=dict(l=20, r=20, t=60, b=20),
    plot_bgcolor="white"
)



import plotly.graph_objects as go

# Add city outline (behind rects) using transparent line
if translated.geom_type == 'Polygon':
    x, y = list(translated.exterior.xy[0]), list(translated.exterior.xy[1])
    fig.add_trace(go.Scatter(
        x=x, y=y, mode='lines',
        line=dict(color='ivory', width=1.5),
        fill='toself',
        fillcolor = '#7CCDEF',
        hoverinfo='skip',
        hovertemplate = 'none',
        showlegend=False
    ))




# Arrow pointing to reference square
fig.add_annotation(
    x=ref_x + 0.75, y=ref_y +0.7,  # Arrow head
    ax=ref_x + 2.4, ay=ref_y - 2.0,  # Tail of the arrow (shift to right)
    xref='x', yref='y',
    axref='x', ayref='y',
   
    showarrow=True,
    arrowhead=1,
    arrowsize=1,
    arrowwidth=1,
    arrowcolor='lightgray',
)

# Arrow pointing to reference square
fig.add_annotation(
    x=ref_x + 0.75, y=ref_y -0.7,  # Arrow head
    ax=ref_x + 2.4, ay=ref_y - 2.0,  # Tail of the arrow (shift to right)
    xref='x', yref='y',
    axref='x', ayref='y',
   
    showarrow=True,
    arrowhead=1,
    arrowsize=1,
    arrowwidth=1,
    arrowcolor='lightgray',
)


#Informational annotations
fig.add_annotation(
    x=ref_x,
    y=ref_y + 0.9,
    text="Click a community area to explore",
    textangle=0,
    font=dict(size=10, color=COLOR_TEXT_2),
    showarrow=False
)

fig.add_annotation(
    x=legend_x - 0.15,
    y=legend_y_start + legend_h / 2,
    text="Click to filter",
    textangle=90,
    font=dict(size=9, color=COLOR_TEXT_2),
    showarrow=False
)
fig.add_annotation(
    x=ref_x - 0.3,
    y=ref_y + 10.7 -1.2,
    text="Severe = Incapacitating/Fatal",
    textangle=0,
    font=dict(size=10.5, color=COLOR_TEXT_2),
    showarrow=False
)

fig.add_annotation(
    x=ref_x + 1.75 ,
    y=ref_y + 11 -1.2,
    text="Bikeability = Custom ranking using Bike Infrasturcture + Network Coverage ",
    textangle=0,
    font=dict(size=10.5, color=COLOR_TEXT_2),
    showarrow=False
)

fig.add_annotation(
    x=ref_x + 10.75 ,
    y=ref_y + 11 -1.2,
    text="Data: City of Chicago",
    textangle=0,
    font=dict(size=11.5, color=COLOR_TEXT_2),
    showarrow=False
)
def empty_plot():
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=0, r=0, t=0, b=0)
    )
    return fig


layout = html.Div([
    dcc.Store(id='bin-shape-map', storage_type='memory'),
    dcc.Store(id='view-mode', data='community'),

    html.Div([
        # 🌐 Top-left Button
        html.Div([
            html.Button('🌐', id='show-network-btn', title='Show Network', n_clicks=0, style={})
        ], style={
            'position': 'absolute',
            'top': '20px',
            'left': '20px',
            'zIndex': 9999
        }),

        # 🛠️ Top-right Button
        html.Div([
            html.Button('🚲', id='exit-network-btn', title='Community View', n_clicks=0, style={
                'display': 'none'
            })
        ], style={
            'position': 'absolute',
            'top': '20px',
            'left': '80px',
            'zIndex': 9999
        }),

        # Main cartogram container
        html.Div(id='cartogram-container', children=[
            dcc.Graph(
                id='cartogram',
                figure=fig,
                config={'displayModeBar': False},
                style={'width': '100%', 'height': '100%', 'display': 'block'}
            ),
            html.Iframe(
                id='network-iframe',
                src='/assets/citywide_network.html',
                style={
                    'width': '900px',
                    'height': '1100px',
                    'border': 'none',
                    'backgroundColor': 'white',
                    'borderRadius': '8px',
                    'boxShadow': '0 2px 6px rgba(0,0,0,0.1)',
                    'display': 'none'
                }
            )
        ])
    ], style={
        'flex': '3',
        'margin': '10px',
        'padding': '15px',
        'backgroundColor': '#ffffff',
        'borderRadius': '16px',
        'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'boxSizing': 'border-box',
        'display': 'flex',
        'alignItems': 'stretch',
        'position': 'relative'
    }),

    # Info panel with dropdown
    html.Div([
        html.Div([
            dcc.Dropdown(
                id='carea-dropdown',
                options=[{'label': name.title(), 'value': name} for name in sorted(viz_df['CArea'].unique())],
                placeholder="Choose an area...",
                style={
                    'fontSize': '14px',
                    'backgroundColor': '#ffffff',
                    'border': '1px solid #d0d0d0',
                    'borderRadius': '8px',
                    'padding': '2px',
                    'boxShadow': '0 1px 3px rgba(0,0,0,0.05)'
                }
            ),
            html.Div(id='info-panel', style={
                'fontFamily': 'Segoe UI, sans-serif',
                'fontSize': '14px',
                'color': '#333',
                'lineHeight': '1.6',
                'padding': '4px 2px'
            })
        ], style={
            'flex': '1',
            'overflowY': 'auto',
            'boxSizing': 'border-box'
        })
    ], className='info-panel-container', style={
        'flex': '1',
        'margin': '10px 10px 10px 0',
        'padding': '15px',
        'backgroundColor': '#ffffff',
        'borderRadius': '16px',
        'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'display': 'flex',
        'flexDirection': 'column',
        'alignSelf': 'stretch',
        'boxSizing': 'border-box'
    })
], className="app-container", style={
    'display': 'flex',
    'flexDirection': 'row',
    'height': '100%',
    'margin': '0',
    'padding': '0',
    'boxSizing': 'border-box',
    'fontFamily': 'Segoe UI, sans-serif',
    'backgroundColor': '#eef2f5'
})



layout = html.Div([
    dcc.Store(id='bin-shape-map', storage_type='memory'),
    dcc.Store(id='view-mode', data='community'),

    # 📊 Main cartogram & network panel
    html.Div([
        html.Div([
            html.Button('🌐', id='show-network-btn', title='Show Network', n_clicks=0, style={})
        ], style={
            'position': 'absolute',
            'top': '20px',
            'left': '20px',
            'zIndex': 9999
        }),

        html.Div([
            html.Button('🚲', id='exit-network-btn', title='Community View', n_clicks=0, style={
                'display': 'none'
            })
        ], style={
            'position': 'absolute',
            'top': '20px',
            'left': '80px',
            'zIndex': 9999
        }),

        html.Div(id='cartogram-container', children=[
            dcc.Graph(
                id='cartogram',
                figure=fig,
                config={'displayModeBar': False},
                style={'width': '100%', 'height': '100%', 'display': 'block'}
            ),
            html.Iframe(
                id='network-iframe',
                src='/assets/citywide_network.html',
                style={
                    'width': '900px',
                    'height': '1100px',
                    'border': 'none',
                    'backgroundColor': 'white',
                    'borderRadius': '8px',
                    'boxShadow': '0 2px 6px rgba(0,0,0,0.1)',
                    'display': 'none'
                }
            )
        ])
    ], style={
        'flex': '3',
        'margin': '10px',
        'padding': '15px',
        'backgroundColor': 'rgba(30,30,30,0.42)',
        'borderRadius': '16px',
        'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.2)',
        'boxSizing': 'border-box',
        'display': 'flex',
        'alignItems': 'stretch',
        'position': 'relative'
    }),

    # ℹ️ Info panel & dropdown
    html.Div([
        html.Div([
            dcc.Dropdown(
                id='carea-dropdown',
                options=[{'label': name.title(), 'value': name} for name in sorted(viz_df['CArea'].unique())],
                placeholder="Choose an area...",
                style={
                    'fontSize': '14px',
                    'backgroundColor': 'rgba(30,30,30,0.42)',
                    'color': '#f0f0f0',
                    'border': '1px solid #444',
                    'borderRadius': '8px',
                    'padding': '2px',
                    'boxShadow': '0 1px 3px rgba(0,0,0,0.05)'
                }
            ),
            html.Div(id='info-panel', style={
                'fontFamily': 'Segoe UI, sans-serif',
                'fontSize': '14px',
                'color': '#f0f0f0',
                'lineHeight': '1.6',
                'padding': '4px 2px'
            })
        ], style={
            'flex': '1',
            'overflowY': 'auto',
            'boxSizing': 'border-box'
        })
    ], className='info-panel-container', style={
        'flex': '1',
        'margin': '10px 10px 10px 0',
        'padding': '15px',
        'backgroundColor': 'rgba(30,30,30,0.42)',
        'borderRadius': '16px',
        'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.2)',
        'display': 'flex',
        'flexDirection': 'column',
        'alignSelf': 'stretch',
        'boxSizing': 'border-box'
    })
], className="app-container", style={
    'display': 'flex',
    'flexDirection': 'row',
    'height': '100%',
    'margin': '0',
    'padding': '0',
    'boxSizing': 'border-box',
    'fontFamily': 'Segoe UI, sans-serif',
    'backgroundColor': 'rgba(30,30,30,0.42)'
})
