import os
import numpy as np
import pandas as pd
from posydon.grids.psygrid import PSyGrid
from posydon.visualization.combine_TF import combine_TF12
from posydon.visualization.plot_defaults import (
    DEFAULT_MARKERS_COLORS_LEGENDS, add_flag_to_MARKERS_COLORS_LEGENDS,
    PLOT_PROPERTIES, DEFAULT_LABELS)
from posydon.config import PATH_TO_POSYDON_DATA
from collections import Counter
import dash_daq as daq

from dash import Dash, html, dcc, callback, Output, Input, State, ctx
import pandas as pd
import plotly.express as px
from dash.exceptions import PreventUpdate
import sys

import plotly.graph_objects as go
from plotly_posydon import dash_plot2D, HRD_on_click, get_IF_values, layers_on_click
from ssh_io import download_data_to_df

fac = 1.0
fig_width = fac*1200
fig_height = fac*900

# some globals
q_range = np.arange(0.05, 1.05, 0.05)
#gpath = "/mnt/d/Research/POSYDON_GRIDS_v2/HMS-HMS/1e+00_Zsun/LITE/grid_low_res_combined_rerun6b_LBV_wind+dedt_energy_eqn.h5"
#gpath = "/mnt/d/Research/POSYDON_GRIDS_v2/HMS-HMS/1e-04_Zsun/LITE/grid_random_combined_rerun7b_LBV_wind+dedt_hepulse_NOCSTOP.h5"
#gpath = "/home/sethg/Research/POSYDON_GRIDS_v3/sparse_test/CO-HMS/1e+00_Zsun.h5"
#gpath = "/home/sethg/Research/POSYDON_GRIDS_v3/sparse_test/CO-HeMS_vflag_rerun/grid_low_res_combined_vflag_rerun.h5"
gpath = "/home/sethg/Research/Downloads/POSYDON_grids/grid_vlm_exp_combined.h5"
#gpath = "/home/sethg/Research/Downloads/POSYDON_grids/rerun/grid_vlm_exp_rerun_fdm_limit_combined_processed.h5"
#gpath = os.path.join(PATH_TO_POSYDON_DATA, "HMS-HMS/1e-04_Zsun.h5")
compare_dir = ""
iv, fv = get_IF_values(gpath)

class MESA_model:
    def __init__(self, compare_dir=None):
        self.mesa_dir = ""
        self.compare_dir = compare_dir

    def set_mesa_dir(self, clickData):

        self.mesa_dir = clickData["points"][0]["customdata"][1]
        self.porbi = clickData["points"][0]["y"]
        self.mdi = clickData["points"][0]["x"]
        self.mai = clickData["points"][0]["customdata"][0]


    def load_data(self):
        mesa_dir = self.mesa_dir
        print(mesa_dir)
        self.s1_df, self.s2_df, self.bdf, self.tf1 = download_data_to_df(mesa_dir)
        self.s1_compare_df, self.s2_compare_df, self.compare_bdf, self.alt_tf1 = download_data_to_df(mesa_dir, self.compare_dir)


mesa_model = MESA_model(compare_dir)

# build dash app
app = Dash()

# App layout
app.layout = html.Div([

    html.Div([

        # ---------------- LEFT: Slice plot ----------------
        html.Div([
            html.Div(
                dcc.Slider(
                    q_range.min(), 
                    q_range.max(), 
                    step=None, 
                    marks={round(q,2): "" for q in q_range},
                    value=q_range[0], 
                    id='grid-slice-slider',
                    tooltip={
                        "placement": "top", 
                        "always_visible": True,
                        "template": "q\u00A0=\u00A0{value}",
                        "style": {"color": "Black", "fontSize": "20px"}
                    }
                ), style={
                    "width": "60%",
                    "margin": "10px 50% 5px 100px",
                    "height": "40px"
                    #"border": "2px solid red"
                }),

                dcc.Loading(
                id="slice-loading",
                type='cube',
                children=[
                    html.Div(
                        dcc.Graph(
                            id='grid-slice-graph',
                            style={"height": "100%", "width": "100%"}
                        ),
                        style={
                            "flex": "1",
                            "minWidth": 0,
                            "overflow": "hidden"
                        }
                    )
                ]
            )

        ],
        style={
            "margin": "0 auto",
            #"paddingTop": "20px",
            "display": "flex",
            "flexDirection": "column",
            "flex": "3",
            "height": "90vh",
            #"border": "2px solid red",
            "justifyContent": "center"
        }),

        # ---------------- MIDDLE: CONTROL CARD ----------------
        html.Div(
            [

                html.Div("Controls", style={
                    "textAlign": "center",
                    "fontWeight": "bold",
                    "marginBottom": "6px"
                }),

                html.Div([
                    html.Div("Star 1 Data:", style={"fontWeight": "bold", "marginBottom": "2px"}),
                    dcc.Dropdown(id='star1-dropdown', style={"marginBottom": "4px"}),
                    dcc.RadioItems(
                        ['log Age', 'Model Number'],
                        'log Age',
                        id='star1-xaxis-type',
                        style={"marginBottom": "8px"}
                    ),
                ]),

                html.Div([
                    html.Div("Star 2 Data:", style={"fontWeight": "bold", "marginBottom": "2px"}),
                    dcc.Dropdown(id='star2-dropdown', style={"marginBottom": "4px"}),
                    dcc.RadioItems(
                        ['log Age', 'Model Number'],
                        'log Age',
                        id='star2-xaxis-type',
                        style={"marginBottom": "8px"}
                    ),
                ]),

                html.Div([
                    html.Div("Binary Y:", style={"fontWeight": "bold", "marginBottom": "2px"}),
                    dcc.Dropdown(id='binary-y-dropdown', style={"marginBottom": "6px"}),

                    html.Div("Binary X:", style={"fontWeight": "bold", "marginBottom": "2px"}),
                    dcc.Dropdown(id='binary-x-dropdown', style={"marginBottom": "6px"}),

                    dcc.Checklist(
                        ['log-x', 'log-y', 'star 2'],
                        id='binary-checklist',
                        style={"marginTop": "4px"}
                    ),
                ])

            ],
            style={
                "padding": "8px 10px",
                "border": "1px solid #ddd",
                "borderRadius": "10px",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
                "backgroundColor": "white",
                "width": "100%",
                "maxWidth": "280px",
                "height": "auto",
                "alignSelf": "center"
            }
        ),

        # ---------------- RIGHT: 4 PANEL GRID ----------------
        html.Div([

            dcc.Loading(
                id="evo-loading-1",
                type='cube',
                children=[
                    dcc.Graph(id='hrd-graph', style={"height":"100%", "width":"100%"})
                ]
            ),

            dcc.Loading(
                id="evo-loading-2",
                type='cube',
                children=[
                    dcc.Graph(id='star1-timeseries', style={"height":"100%", "width":"100%"})
                ]
            ),

            dcc.Loading(
                id="evo-loading-3",
                type='cube',
                children=[
                    dcc.Graph(id='star2-timeseries', style={"height":"100%", "width":"100%"})
                ]
            ),

            dcc.Loading(
                id="evo-loading-4",
                type='cube',
                children=[
                    dcc.Graph(id='binary-plot', style={"height":"100%", "width":"100%"})
                ]
            )

        ],
        style={
            "flex": "3",
            "display": "grid",
            "gridTemplateColumns": "1fr 1fr",
            "gridTemplateRows": "1fr 1fr",
            "gap": "8px",
            "height": "90vh",
            "padding": "8px",
            "minWidth": 0#,
            #"border": "2px solid red"
        }),

    ],
    style={
        "display": "flex",
        "height": "100vh",
        "gap": "20px",
        "padding": "10px"
    })

])

# Callbacks
@callback(
    Output("grid-slice-graph", "figure", allow_duplicate=True),
    Input("grid-slice-graph", "relayoutData"),
    State("grid-slice-slider", "value"),
    State("grid-slice-graph", "figure"),
    prevent_initial_call=True
)
def update_ticks(relayout_data, q, fig):

    if not relayout_data:
        return fig
    
    cut = (iv['star_2_mass']/iv['star_1_mass'] < q+0.025) & (iv['star_2_mass']/iv['star_1_mass'] > q-0.025)
    # ---- X axis ----
    if "xaxis.autorange" in relayout_data:
        # recompute from FULL dataset
        x0 = np.log10(iv[cut]['star_1_mass'].min())
        x1 = np.log10(iv[cut]['star_1_mass'].max())

        x_tickvals = np.logspace(x0, x1, 5)
        x_ticktext = [f"{np.log10(t):.1f}" for t in x_tickvals]

        fig["layout"]["xaxis"]["tickvals"] = x_tickvals.tolist()
        fig["layout"]["xaxis"]["ticktext"] = x_ticktext

    elif "xaxis.range[0]" in relayout_data:
        x0 = relayout_data["xaxis.range[0]"]
        x1 = relayout_data["xaxis.range[1]"]

        x_tickvals = np.logspace(x0, x1, 5)
        x_ticktext = [f"{np.log10(t):.1f}" for t in x_tickvals]

        fig["layout"]["xaxis"]["tickvals"] = x_tickvals.tolist()
        fig["layout"]["xaxis"]["ticktext"] = x_ticktext

    # ---- Y axis ----
    if "yaxis.autorange" in relayout_data:
        # recompute from FULL dataset
        y0 = np.log10(iv[cut]['period_days'].min())
        y1 = np.log10(iv[cut]['period_days'].max())

        y_tickvals = np.logspace(y0, y1, 5)
        y_ticktext = [f"{np.log10(t):.1f}" for t in y_tickvals]

        fig["layout"]["yaxis"]["tickvals"] = y_tickvals.tolist()
        fig["layout"]["yaxis"]["ticktext"] = y_ticktext

    elif "yaxis.range[0]" in relayout_data:
        y0 = relayout_data["yaxis.range[0]"]
        y1 = relayout_data["yaxis.range[1]"]

        y_tickvals = np.logspace(y0, y1, 5)
        y_ticktext = [f"{np.log10(t):.1f}" for t in y_tickvals]

        fig["layout"]["yaxis"]["tickvals"] = y_tickvals.tolist()
        fig["layout"]["yaxis"]["ticktext"] = y_ticktext

    return fig

# Grid slice plot update on slider value
@callback(
    Output('grid-slice-graph', 'figure'),
    Input('grid-slice-slider', 'value'),
    #Input('comparison-toggle', 'value')
)
def update_slice_graph(q):

    # plot grid plot for selected q
    f = dash_plot2D(q, iv, fv, mesa_model.compare_dir, highlight_comparisons=False, fig_width=fig_width, fig_height=fig_height)
    return f
#def update_slice_graph(q, toggle_value):

    # plot grid plot for selected q
#    f = dash_plot2D(q, iv, fv, mesa_model.compare_dir, highlight_comparisons=toggle_value, fig_width=fig_width, fig_height=fig_height)
#    return f

# Highlight model clicked on in grid slice plot
# Triggers on clicking grid-slice-plot, uses current state of grid-slice plot to clean old traces
@callback(
    Output('grid-slice-graph', 'figure', allow_duplicate=True),
    Output('grid-slice-graph', 'clickData'),
    Input('grid-slice-graph', 'clickData'),
    State('grid-slice-graph', 'figure'),
    prevent_initial_call=True
)
#def highlight_on_click(q, clickData, toggle_value, current_fig):
def highlight_on_click(clickData, current_fig):

    if clickData:

        mesa_model.set_mesa_dir(clickData)

        # if a trace for selected data already exists, delete it
        for i, trace in enumerate(current_fig['data']):
            if 'name' in trace and trace['name'] == 'selected':
                current_fig['data'][i].clear()

        porbi = mesa_model.porbi
        mdi = mesa_model.mdi
        
        # add a new trace to highlight selected point on grid plot
        current_fig['data'].append(px.scatter(x=[float(mdi)], y=[float(porbi)]).update_traces(
                                              marker=dict(color='LightSkyBlue', symbol='square-open', size=15, 
                                                          line=dict(color='MediumPurple',width=4)), 
                                              hoverinfo='skip', hovertemplate=None, name='selected').data[0])
        
        return current_fig, None
    else:
        raise PreventUpdate

# Model HRD plot update on clicking model in slice plot
# Also update dropdown menu with available data columns
@callback(
    Output('hrd-graph', 'figure'),
    Output('star1-dropdown', 'options'),
    Output('star2-dropdown', 'options'),
    Output('binary-x-dropdown', 'options'),
    Output('binary-y-dropdown', 'options'),
    Input('grid-slice-graph', 'clickData'),
    prevent_initial_call = True
)
def load_and_plot_HRD(clickData):
        
    mesa_model.load_data()

    # plot HRD for selected model
    f = HRD_on_click(mesa_model, fig_width=fig_width/2, fig_height=fig_height/2)
        
    return f, mesa_model.s1_df.columns, mesa_model.s2_df.columns, mesa_model.bdf.columns, mesa_model.bdf.columns


# update star 1 time evo
@callback(
    Output('star1-timeseries', 'figure'),
    Input('star1-dropdown', 'value'),
    Input('star1-xaxis-type', 'value'),
    Input('star1-dropdown', 'options'),
    prevent_initial_call = True
)
def load_and_plot_click_data_pri(star1_y, star1_x, options):
    
    """
    if star1_x == "log Age":
        star1_x = "star_age"
        xaxis_type = "log"
    else:
        star1_x = "model_number"
        xaxis_type = "linear"

    if star1_y:

        f = px.line(mesa_model.s1_df, x=star1_x, y=star1_y, custom_data=['star_age', 'star_mass']).update_traces(name='Star 1', line_color='royalblue',
                        hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>')
            
        # plot comparison tracks if provided
        if not mesa_model.s1_compare_df.empty:
            f.add_trace(px.line(mesa_model.s1_compare_df, x=star1_x, y=star1_y, custom_data=['star_age', 'star_mass']).update_traces(name='Star 1 (alt.)', line =dict(color='magenta', width=1),
                            hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
            
        f.update_layout(template='simple_white',
                            xaxis_type=xaxis_type,
                            height=fig_height*0.5, width=fig_width*0.5)

        return f
        
    else:
        raise PreventUpdate
    """

    f = layers_on_click(mesa_model, fig_width=fig_width/2, fig_height=fig_height/2)

    return f
        
# update star 2 time evo
@callback(
    Output('star2-timeseries', 'figure'),
    Input('star2-dropdown', 'value'),
    Input('star2-xaxis-type', 'value'),
    Input('star2-dropdown', 'options'),
    prevent_initial_call = True
)
def load_and_plot_click_data_sec(star2_y, star2_x, options):
    
    if star2_x == "log Age":
        star2_x = "star_age"
        xaxis_type = "log"
    else:
        star2_x = "model_number"
        xaxis_type = "linear"

    if star2_y:

        f = px.line(mesa_model.s2_df, x=star2_x, y=star2_y, custom_data=['star_age', 'star_mass']).update_traces(name='Star 2', line_color='darkorange',
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>')
        
        # plot comparison tracks if provided
        if not mesa_model.s2_compare_df.empty:
             f.add_trace(px.line(mesa_model.s2_compare_df, x=star2_x, y=star2_y, custom_data=['star_age', 'star_mass']).update_traces(name='Star 2 (alt.)', line =dict(color='orangered', width=1),
                         hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
        
        f.update_layout(template='simple_white',
                        xaxis_type=xaxis_type,
                        height=fig_height*0.5, width=fig_width*0.5)

        return f
        
    else:
        raise PreventUpdate

# update binary time evo
@callback(
    Output('binary-plot', 'figure'),
    Input('binary-x-dropdown', 'value'),
    Input('binary-y-dropdown', 'value'),
    Input('binary-checklist', 'value'),
    Input('binary-x-dropdown', 'options'),
    prevent_initial_call = True
)
def load_and_plot_click_data_bin(bin_x, bin_y, log_options, options):

    if log_options:
        xaxis_type = 'log' if 'log-x' in log_options else 'linear'
        yaxis_type = 'log' if 'log-y' in log_options else 'linear'
    else:
        xaxis_type = 'linear'
        yaxis_type = 'linear'

    if bin_x and bin_y:

        f = px.line(mesa_model.bdf, x=bin_x, y=bin_y, custom_data=['age', 'star_1_mass', 'star_2_mass']).update_traces(line_color='royalblue',
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>')
        
        if log_options:
            if "star 2" in log_options and "1" in bin_y:
                bin_y2 = bin_y.replace("1", "2")
                f.add_trace(px.line(mesa_model.bdf, x=bin_x, y=bin_y2, custom_data=['age', 'star_1_mass', 'star_2_mass']).update_traces(line =dict(color='darkorange', width=1),
                            hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
        
        # plot comparison tracks if provided
        if not mesa_model.compare_bdf.empty:
            f.add_trace(px.line(mesa_model.compare_bdf, x=bin_x, y=bin_y, custom_data=['age', 'star_1_mass', 'star_2_mass']).update_traces(line =dict(color='magenta', width=1),
                         hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
             
            if log_options:
                if "star 2" in log_options and "1" in bin_y:
                    bin_y2 = bin_y.replace("1", "2")
                    f.add_trace(px.line(mesa_model.compare_bdf, x=bin_x, y=bin_y2, custom_data=['age', 'star_1_mass', 'star_2_mass']).update_traces(line =dict(color='orangered', width=1),
                                hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
        
        f.update_layout(template='simple_white',
                        xaxis_type=xaxis_type,
                        yaxis_type=yaxis_type,
                        height=fig_height/2, width=fig_width/2)

        return f
        
    else:
        raise PreventUpdate

# plot comparison highlights 
#@callback(
#    Output('grid-slice-graph', 'figure', allow_duplicate=True),
#    Input('grid-slice-slider', 'value'),
#    Input('comparison-toggle', 'value'),
#    prevent_initial_call=True   
#)
def highlight_comparisons(q, value):

    if not mesa_model.compare_dir:
        raise PreventUpdate
    else:
        f = dash_plot2D(q, iv, fv, mesa_model.compare_dir, highlight_comparisons=value)
        return f

# set compare dir and initialize comparison toggle to False for it
#@callback(
#    Output('comparison-toggle', 'value'),
#    Input('input-comp-dir', 'value'),
#    prevent_initial_call=True   
#)
def set_compare_dir(value):

    mesa_model.compare_dir = value
    
    return False


if __name__ == "__main__":
    # Run the app
    app.run(port=sys.argv[1], debug=True)