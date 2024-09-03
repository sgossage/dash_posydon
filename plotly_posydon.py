import pandas as pd
from posydon.grids.psygrid import PSyGrid
from posydon.visualization.combine_TF import combine_TF12
from posydon.visualization.plot_defaults import (
    DEFAULT_MARKERS_COLORS_LEGENDS, add_flag_to_MARKERS_COLORS_LEGENDS,
    PLOT_PROPERTIES, DEFAULT_LABELS)

import plotly.express as px
import plotly.graph_objects as go
from ssh_io import available_comparison

marker_settings = DEFAULT_MARKERS_COLORS_LEGENDS['combined_TF12']
symbol_map = {'D': 'diamond', 's': 'square', '.': 'circle', 'x': 'x'}

def color_convert(c):
    if c == "tab:olive":
        return "olive"
    if c == [(31/255, 119/255, 180/255)]:
        return "royalblue"
    if c == [(255/255, 127/255, 14/255)]:
        return 'darkorange'

    return c

def get_IF_values(grid_path):
    grid = PSyGrid()
    grid.load(grid_path)

    iv = pd.DataFrame(grid.initial_values)
    fv = pd.DataFrame(grid.final_values)
    iv = iv.assign(mesa_dir=[ mdir.decode("utf-8") for mdir in grid.MESA_dirs])
    iv = iv.assign(grid_index=[ mdir.decode("utf-8").split("index_")[-1] for mdir in grid.MESA_dirs])
    iv = iv.assign(termination_flag_1=[ tf1 for tf1 in fv['termination_flag_1'].values])

    return iv, fv

def dash_plot2D(q, iv, fv, compare_dir=None, highlight_comparisons=True, fig_width=1200, fig_height=800):
    
    TF12 = combine_TF12(fv['interpolation_class'], fv['termination_flag_2'])
    cut = (iv['star_2_mass']/iv['star_1_mass'] < q+0.025) & (iv['star_2_mass']/iv['star_1_mass'] > q-0.025)
    
    # plotly version of plot2D
    f = px.scatter(iv[cut], x="star_1_mass", y="period_days", color=TF12[cut], custom_data=['star_2_mass', 'mesa_dir', 'grid_index', 'termination_flag_1'],
                   log_x=True, log_y=True, hover_name="grid_index")
    
    f.update_traces(hovertemplate='M<sub>1</sub>: %{x:.2f} M<sub>&#8857;</sub> <br>' +\
                                  'M<sub>2</sub>: %{customdata[0]:.2f} M<sub>&#8857;</sub> <br>' +\
                                  'P<sub>orb,i</sub>: %{y:.2f} d')
    
    f.for_each_trace(lambda t: t.update(name = marker_settings[t.name][3], 
                                        marker = dict(size = 6, symbol=symbol_map[marker_settings[t.name][0]],
                                                      color=color_convert(marker_settings[t.name][2]), 
                                                      line=dict(color='black', width=0.1)), 
                                        legendgroup= marker_settings[t.name][3]) )
    
    f.update_layout(template='simple_white',
                    xaxis_title="log<sub>10</sub> M<sub>1</sub>/M<sub>&#8857;</sub>", 
                    yaxis_title="log<sub>10</sub> P<sub>orb</sub>/days", legend_title="Termination Flags",
                    height=fig_height, width=fig_width,
                    margin={'t':0,'l':0,'b':0,'r':0})
    
    # prevent duplicate labels in legend
    names = set()
    f.for_each_trace(
        lambda trace:
            trace.update(showlegend=False)
            if (trace.name in names) else names.add(trace.name))
    
    if highlight_comparisons:
        availability_list, success_list = available_comparison(iv[cut]['mesa_dir'], compare_dir)

        for i, available in enumerate(availability_list):
            if available:
                if success_list[i]:
                    marker_color = 'green'
                else:
                    marker_color = 'red'       
                # highlight selected point on grid plot
                f.add_trace(px.scatter(x=[iv[cut]['star_1_mass'].iloc[i]], y=[iv[cut]['period_days'].iloc[i]]).update_traces(
                        marker=dict(color=marker_color, symbol='square-open', size=10, 
                        line=dict(color=marker_color,width=3)
                        ), hoverinfo='skip', hovertemplate=None).data[0])

    return f


def HRD_on_click(mesa_model, fig_width=1200, fig_height=800):
        
        if mesa_model.s1_df.empty:
            # when no data (history) files are found...
            f = go.Figure()
            f.add_annotation(text='Data missing in {:s} <br>'.format("/".join(mesa_model.mesa_dir.split("/")[:-1])) +\
                                  'for run {:s}'.format(mesa_model.mesa_dir.split("/")[-1]), 
                        align='left',
                        showarrow=False,
                        xref='paper',
                        yref='paper',
                        x=0.01,
                        y=0.5,
                        bordercolor='black',
                        borderwidth=0)
            f.update_layout(template='simple_white',
                        height=fig_height, width=fig_width)
            return f

        porbi = mesa_model.porbi 
        mdi = mesa_model.mdi 
        mai = mesa_model.mai 

        # star 1
        f = px.line(mesa_model.s1_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 1', line =dict(color='royalblue', width=3),
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>')
        
        # plot comparison tracks if provided
        if not mesa_model.s2_compare_df.empty:
             f.add_trace(px.line(mesa_model.s1_compare_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 1 (alt.)', line =dict(color='magenta', width=1),
                         hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
             
        # ZAMS marker
        f.add_trace(px.scatter(mesa_model.s1_df.iloc[[0]], x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(
                    name="ZAMS",
                    marker=dict(color='LightSkyBlue', 
                    line=dict(color='MediumPurple',width=2)),
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])

        # star 2
        f.add_trace(px.line(mesa_model.s2_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 2', line_color='darkorange',
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
        
        if not mesa_model.s2_compare_df.empty:
             f.add_trace(px.line(mesa_model.s2_compare_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 2 (alt.)', line_color='orangered',
                         hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])

        # ZAMS marker
        f.add_trace(px.scatter(mesa_model.s2_df.iloc[[0]], x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(
                    name="ZAMS",
                    marker=dict(color='moccasin', 
                    line=dict(color='MediumPurple',width=2)),
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])

        # don't show ZAMS markers in the legend
        f.for_each_trace(lambda trace: trace.update(showlegend=False) if (trace.name == "ZAMS") else trace.update(showlegend=True))

        # Add some text annotating the initial orbital config
        f.add_annotation(text='P<sub>orb,i</sub> = {:.2f} d <br>'.format(porbi) +\
                              'M<sub>1</sub> = {:.2f} M<sub>&#8857;</sub> <br>'.format(mdi)+\
                              'M<sub>2</sub> = {:.2f} M<sub>&#8857;</sub> <br>'.format(mai)+\
                              'TF1: {:s} <br>'.format(mesa_model.tf1)+\
                              'TF1 (alt.): {:s}'.format(mesa_model.alt_tf1), 
                        align='left',
                        showarrow=False,
                        xref='paper',
                        yref='paper',
                        x=0.05,
                        y=0.05,
                        bordercolor='black',
                        borderwidth=0)
        
        # set aesthetics
        f.update_layout(template='simple_white',
                        xaxis_title="log<sub>10</sub> T<sub>eff</sub>", 
                        yaxis_title="log<sub>10</sub> L/L<sub>&#8857;</sub>", legend_title="",
                        height=fig_height, width=fig_width,
                        xaxis = dict(autorange="reversed"))
    
        return f