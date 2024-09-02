import os
import numpy as np
import pandas as pd
from posydon.grids.psygrid import PSyGrid
from posydon.visualization.combine_TF import combine_TF12
from posydon.visualization.plot_defaults import (
    DEFAULT_MARKERS_COLORS_LEGENDS, add_flag_to_MARKERS_COLORS_LEGENDS,
    PLOT_PROPERTIES, DEFAULT_LABELS)
from collections import Counter
import dash_daq as daq

from dash import Dash, html, dcc, callback, Output, Input, State, ctx
import pandas as pd
import plotly.express as px
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go
from plotly_posydon import dash_plot2D, HRD_on_click, get_IF_values
from ssh_io import download_data_to_df

# some globals
q_range = np.arange(0.05, 1.05, 0.05)
gpath = "/mnt/d/Research/POSYDON_GRIDS_v2/HMS-HMS/1e+00_Zsun/LITE/grid_low_res_combined_rerun6b_LBV_wind+dedt_energy_eqn.h5"
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
        self.s1_df, self.s2_df, self.bdf, self.tf1 = download_data_to_df(mesa_dir)
        self.s1_compare_df, self.s2_compare_df, self.compare_bdf, self.alt_tf1 = download_data_to_df(mesa_dir, self.compare_dir)


mesa_model = MESA_model(compare_dir)

# build dash app
app = Dash()

# App layout
app.layout = html.Div([
                        # 1st row, grid slice and HRD
                        html.Div([
                                            # slice slider
                                  html.Div([html.Div(dcc.Slider(
                                                       q_range.min(), 
                                                       q_range.max(), 
                                                       step=None, 
                                                       marks={ round(q,2) : "" for q in q_range}, #str(round(q, 2))
                                                       value=q_range[0], 
                                                       id='grid-slice-slider',
                                                       tooltip={"placement": "top", 
                                                                "always_visible": True,
                                                                "template": "q = {value}",
                                                                "style": {"color": "LightSteelBlue", "fontSize": "20px"}}), 
                                                       style={'width': '50%', 'padding-left':'15%', 'padding-right':'25%', 'padding-top':'5%'}),
                                                    html.Div([dcc.Input(id='input-comp-dir', type='text', 
                                                              value='/projects/b1119/ssg9761/POSYDON_hydro_debug/1e+00_Zsun/LBV_wind+dedt_energy_eqn/lgTeff_test_5'),
                                                              daq.ToggleSwitch( id='comparison-toggle', value=False, size=30)], 
                                                              style={"display":"flex", 'padding-left':'80%'}),
                                                    # slice plot                     
                                                    dcc.Loading(
                                                      id = "slice-loading", type = 'cube',
                                                      children=[html.Div(dcc.Graph(id='grid-slice-graph', figure={"layout":{"height":800, "width":1200}}) )]
                                                      )
                                            ]),
                                    # HRD plot
                                    html.Div([dcc.Loading(
                                                id = "evo-loading", type = 'cube', 
                                                children=[html.Div(dcc.Graph(id='hrd-graph', figure={"layout":{"height":800, "width":1200}}))]
                                                )
                                          ])
                                 ], 
                                 style={"display":"flex", "gap":"5px", "align-items":"flex-end"}),
                        # 2nd row of time series plots
                        html.Div([html.Div(children=[html.Label(['Star 1 Data:'], style={'font-weight': 'bold', "text-align": "center"}), 
                                           dcc.Dropdown(id='star1-dropdown', style={'width': '50%'}),
                                           dcc.RadioItems(['log Age', 'Model Number'], 'log Age', id='star1-xaxis-type', inline=True),
                                           dcc.Graph(id='star1-timeseries', figure={"layout":{"height":400, "width":800}}),
                                           html.Label(['Star 2 Data:'], style={'font-weight': 'bold', "text-align": "center"}), 
                                           dcc.Dropdown(id='star2-dropdown', style={'width': '50%'}),
                                           dcc.RadioItems(['log Age', 'Model Number'], 'log Age', id='star2-xaxis-type', inline=True),
                                           dcc.Graph(id='star2-timeseries', figure={"layout":{"height":400, "width":800}})]),
                                  html.Div(children=[html.Label(['Binary y-Data:'], style={'font-weight': 'bold', "text-align": "center"}), 
                                           dcc.Dropdown(id='binary-y-dropdown', style={'width': '50%'}),
                                           html.Label(['Binary x-Data:'], style={'font-weight': 'bold', "text-align": "center"}),
                                           dcc.Dropdown(id='binary-x-dropdown', style={'width': '50%'}),
                                           dcc.Checklist(['log-x', 'log-y', 'star 2'], id='binary-checklist', inline=True),
                                           dcc.Graph(id='binary-plot', figure={"layout":{"height":800, "width":1200}})
                                    ])
                                ], style={"display":"flex", "gap":"400px", "align-items":"flex-end"})
                        
                      ])

# Callbacks
# Grid slice plot update on slider value
@callback(
    Output('grid-slice-graph', 'figure'),
    Input('grid-slice-slider', 'value'),
    Input('comparison-toggle', 'value')
)
def update_slice_graph(q, toggle_value):

    # plot grid plot for selected q
    f = dash_plot2D(q, iv, fv, mesa_model.compare_dir, highlight_comparisons=toggle_value)
    return f

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
                                              marker=dict(color='LightSkyBlue', symbol='square-open', size=20, 
                                                          line=dict(color='MediumPurple',width=6)), 
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
    f = HRD_on_click(mesa_model)
        
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
        if mesa_model.s1_compare_df is not None:
            f.add_trace(px.line(mesa_model.s1_compare_df, x=star1_x, y=star1_y, custom_data=['star_age', 'star_mass']).update_traces(name='Star 1 (alt.)', line =dict(color='magenta', width=1),
                            hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
            
        f.update_layout(template='simple_white',
                            xaxis_type=xaxis_type,
                            height=400, width=800)

        return f
        
    else:
        raise PreventUpdate

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
        if mesa_model.s2_compare_df is not None:
             f.add_trace(px.line(mesa_model.s2_compare_df, x=star2_x, y=star2_y, custom_data=['star_age', 'star_mass']).update_traces(name='Star 2 (alt.)', line =dict(color='orangered', width=1),
                         hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
        
        f.update_layout(template='simple_white',
                        xaxis_type=xaxis_type,
                        height=400, width=800)

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
        if mesa_model.compare_bdf is not None:
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
                        height=800, width=1200)

        return f
        
    else:
        raise PreventUpdate

# plot comparison highlights 
@callback(
    Output('grid-slice-graph', 'figure', allow_duplicate=True),
    Input('grid-slice-slider', 'value'),
    Input('comparison-toggle', 'value'),
    prevent_initial_call=True
    
)
def highlight_comparisons(q, value):

    if not mesa_model.compare_dir:
        raise PreventUpdate
    else:
        f = dash_plot2D(q, iv, fv, mesa_model.compare_dir, highlight_comparisons=value)
        return f

# set compare dir and initialize comparison toggle to False for it
@callback(
    Output('comparison-toggle', 'value'),
    Input('input-comp-dir', 'value'),
    prevent_initial_call=True
    
)
def set_compare_dir(value):

    mesa_model.compare_dir = value
    
    return False


if __name__ == "__main__":
    # Run the app
    app.run(port=8080, debug=True)