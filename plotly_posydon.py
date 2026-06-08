import pandas as pd
import numpy as np
from posydon.grids.psygrid import PSyGrid
from posydon.visualization.combine_TF import combine_TF12
from posydon.visualization.plot_defaults import (
    DEFAULT_MARKERS_COLORS_LEGENDS, add_flag_to_MARKERS_COLORS_LEGENDS,
    PLOT_PROPERTIES, DEFAULT_LABELS)

import plotly.express as px
import plotly.graph_objects as go
from ssh_io import available_comparison
import textwrap

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

    iv = grid.initial_values
    fv = grid.final_values
    iv = grid.initial_values.to_df()
    fv = grid.final_values.to_df()
    iv = iv.assign(mesa_dir=[ mdir.decode("utf-8") for mdir in grid.MESA_dirs])
    iv = iv.assign(grid_index=[ mdir.decode("utf-8").split("index_")[-1] for mdir in grid.MESA_dirs])
    iv = iv.assign(termination_flag_1=[ tf1 for tf1 in fv['termination_flag_1'].values])

    return iv, fv

def dash_plot2D(q, iv, fv, compare_dir=None, highlight_comparisons=True, fig_width=1200, fig_height=800):
    
    TF12 = combine_TF12(fv['interpolation_class'], fv['termination_flag_2'])
    cut = (iv['star_2_mass']/iv['star_1_mass'] < q+0.025) & (iv['star_2_mass']/iv['star_1_mass'] > q-0.025)
    
    # plotly version of plot2D
    f = px.scatter(iv[cut], x="star_1_mass", y="period_days", color=TF12[cut], 
                   custom_data=['star_2_mass', 'mesa_dir', 'grid_index', 'termination_flag_1'],
                   hover_name="grid_index", log_x=True, log_y=True)
    
    f.update_traces(hovertemplate='M<sub>1</sub>: %{x:.2f} M<sub>&#8857;</sub> <br>' +\
                                  'M<sub>2</sub>: %{customdata[0]:.2f} M<sub>&#8857;</sub> <br>' +\
                                  'P<sub>orb,i</sub>: %{y:.2f} d')
    
    f.for_each_trace(lambda t: t.update(name = marker_settings[t.name][3], 
                                        marker = dict(size = 6, symbol=symbol_map[marker_settings[t.name][0]],
                                                      color=color_convert(marker_settings[t.name][2]), 
                                                      line=dict(color='black', width=0.1)), 
                                        legendgroup= marker_settings[t.name][3]) )
    
    f.update_layout(template='simple_white',
                    xaxis_title="log<sub>10</sub>(M<sub>1</sub>) [M<sub>&#8857;</sub>]", 
                    yaxis_title="log<sub>10</sub>(P<sub>orb</sub>) [days]", 
                    legend_title="Termination Flags",
                    height=fig_height, width=fig_width,
                    margin={'t':0,'l':0,'b':0,'r':0}, 
                    #font=dict(size=18),
                    legend=dict(font=dict(size=14))
                   )
    
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
                
    x_tickvals = np.logspace(np.log10(iv[cut]['star_1_mass'].min()), 
                             np.log10(iv[cut]['star_1_mass'].max()), 5)
    x_tickstrs = [f"{np.log10(tick):.1f}" for tick in x_tickvals]
    y_tickvals = np.logspace(np.log10(iv[cut]['period_days'].min()), 
                             np.log10(iv[cut]['period_days'].max()), 5)
    y_tickstrs = [f"{np.log10(tick):.1f}" for tick in y_tickvals]

    f.update_layout(xaxis = dict(
                                 tickmode='array',
                                 tickvals=x_tickvals,
                                 nticks=len(x_tickvals),
                                 ticktext=x_tickstrs,
                                 ticks='inside',
                                 tickfont=dict(size=16),
                                 title_font=dict(size=18)
                                ),
                    yaxis = dict(
                                 tickmode='array',
                                 tickvals=y_tickvals,
                                 nticks=len(y_tickvals),
                                 ticktext=y_tickstrs,
                                 ticks='inside',
                                 tickfont=dict(size=16),
                                 title_font=dict(size=18)
                                )
                    )

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
            #f.update_layout(template='simple_white',
            #            height=fig_height, width=fig_width)
            return f

        porbi = mesa_model.porbi 
        mdi = mesa_model.mdi 
        mai = mesa_model.mai 

        # star 1
        f = px.line(mesa_model.s1_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 1', line =dict(color='royalblue', width=3),
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>')
        
        # plot comparison tracks if provided
        if not mesa_model.s1_compare_df.empty:
            f.add_trace(px.line(mesa_model.s1_compare_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 1 (alt.)', line =dict(color='magenta', width=1),
                        hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
             
        # ZAMS marker
        f.add_trace(px.scatter(mesa_model.s1_df.iloc[[0]], x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(
                    name="ZAMS",
                    marker=dict(color='LightSkyBlue', 
                    line=dict(color='MediumPurple',width=2)),
                    hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])

        # star 2
        if not mesa_model.s2_df.empty:
            f.add_trace(px.line(mesa_model.s2_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 2', line_color='darkorange',
                        hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
        
        if not mesa_model.s2_compare_df.empty:
            f.add_trace(px.line(mesa_model.s2_compare_df, x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(name='Star 2 (alt.)', line_color='orangered',
                        hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])

        # ZAMS marker
        if not mesa_model.s2_df.empty:
            f.add_trace(px.scatter(mesa_model.s2_df.iloc[[0]], x="log_Teff", y="log_L", custom_data=['star_age', 'star_mass']).update_traces(
                        name="ZAMS",
                        marker=dict(color='moccasin', 
                        line=dict(color='MediumPurple',width=2)),
                        hovertemplate='Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])

        # don't show ZAMS markers in the legend
        f.for_each_trace(lambda trace: trace.update(showlegend=False) if (trace.name == "ZAMS") else trace.update(showlegend=True))

        tf1_wrapped = "<br>".join(textwrap.wrap(mesa_model.tf1, width=40))
        # Add some text annotating the initial orbital config
        f.add_annotation(text='P<sub>orb,i</sub> = {:.2f} d <br>'.format(porbi) +\
                              'M<sub>1</sub> = {:.2f} M<sub>&#8857;</sub> <br>'.format(mdi)+\
                              'M<sub>2</sub> = {:.2f} M<sub>&#8857;</sub> <br>'.format(mai)+\
                              'TF1: {:s} <br>'.format(tf1_wrapped),#+\
                              #'TF1 (alt.): {:s}'.format(mesa_model.alt_tf1), 
                        align='left',
                        showarrow=False,
                        xref='paper',
                        yref='paper',
                        x=0.05,
                        y=0.05,
                        bordercolor='black',
                        borderwidth=0,
                        font=dict(size=14))
        
        # set aesthetics
        f.update_layout(template='simple_white',
                        xaxis_title="log<sub>10</sub>(T<sub>eff</sub>) [K]", 
                        yaxis_title="log<sub>10</sub>(L) [L<sub>&#8857;</sub>]", legend_title="",
                        #height=fig_height, width=fig_width,
                        margin={'t':0,'l':0,'b':0,'r':0},
                        xaxis = dict(autorange="reversed"),
                        #legend=dict(x=0.05,
                        #            y=0.17,
                        #            xanchor="left",
                        #            yanchor="bottom",
                        #            font=dict(size=14)))
                        legend=dict(x=0.98,
                                    y=0.98,
                                    xanchor="right",
                                    yanchor="top",
                                    font=dict(size=14)))
        
        f.update_layout(xaxis = dict(
                                    ticks='inside',
                                    tickfont=dict(size=16),
                                    title_font=dict(size=18)
                                    ),
                        yaxis = dict(
                                    ticks='inside',
                                    tickfont=dict(size=16),
                                    title_font=dict(size=18)
                                    )
                        )
    
        return f

def layers_on_click(star_df, fig_width=1200, fig_height=800):

    star_df["h_layer_mass"] = star_df["star_mass"] - star_df["he_core_mass"]
    star_df["he_layer_mass"] = star_df["he_core_mass"] - star_df["c_core_mass"]
    star_df["c_layer_mass"] = star_df["c_core_mass"] - star_df["o_core_mass"]
    star_df["o_layer_mass"] = star_df["o_core_mass"]

    star_df["h_layer_bot"] = star_df["o_layer_mass"] + star_df["c_layer_mass"] + star_df["he_layer_mass"]
    star_df["h_layer_top"] = star_df["o_layer_mass"] + star_df["c_layer_mass"] + star_df["he_layer_mass"] + star_df["h_layer_mass"]
    star_df["he_layer_bot"] = star_df["o_layer_mass"] + star_df["c_layer_mass"]
    star_df["he_layer_top"] = star_df["o_layer_mass"] + star_df["c_layer_mass"] + star_df["he_layer_mass"]
    star_df["c_layer_bot"] = star_df["o_layer_mass"]
    star_df["c_layer_top"] = star_df["o_layer_mass"] + star_df["c_layer_mass"]
    star_df["o_layer_bot"] = 0.0
    star_df["o_layer_top"] = star_df["o_layer_mass"]


    f = go.Figure()

    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["h_layer_bot"],
        mode="lines",
        line=dict(color="orange", width=3),
        showlegend=False
    ))

    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["h_layer_top"],
        mode="lines",
        name="H layer",
        line=dict(color="orange", width=3),
        fill="tonexty",
        fillcolor="rgba(255,165,0,0.2)",  # semi-transparent orange
        customdata=star_df[["star_age", "h_layer_mass"]],
        hovertemplate="Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.3f} M<sub>&#8857;</sub>"
    ))

    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["he_layer_bot"],
        mode="lines",
        line=dict(color="royalblue", width=3),
        showlegend=False
    ))
    
    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["he_layer_top"],
        mode="lines",
        name="He layer",
        line=dict(color="royalblue", width=3),
        fill="tonexty",
        fillcolor="rgba(65,105,225,0.2)",  # semi-transparent royalblue
        customdata=star_df[["star_age", "he_layer_mass"]],
        hovertemplate="Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.3f} M<sub>&#8857;</sub>"
    ))

    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["c_layer_bot"],
        mode="lines",
        line=dict(color="goldenrod", width=3),
        showlegend=False
    ))
    
    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["c_layer_top"],
        mode="lines",
        name="C layer",
        line=dict(color="goldenrod", width=3),
        fill="tonexty",
        fillcolor="rgba(255,215,0,0.2)",  # semi-transparent gold
        customdata=star_df[["star_age", "c_layer_mass"]],
        hovertemplate="Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.3f} M<sub>&#8857;</sub>"
    ))

    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["o_layer_bot"],
        mode="lines",
        line=dict(color="cyan", width=3),
        showlegend=False
    ))
    
    f.add_trace(go.Scatter(
        x=star_df["star_age"],
        y=star_df["o_layer_top"],
        mode="lines",
        name="O layer",
        line=dict(color="cyan", width=3),
        fill="tonexty",
        fillcolor="rgba(255,215,0,0.2)",  # semi-transparent gold
        customdata=star_df[["star_age", "o_layer_mass"]],
        hovertemplate="Age: %{customdata[0]:.3e} yrs <br> Mass: %{customdata[1]:.3f} M<sub>&#8857;</sub>"
    ))

    f.update_layout(template='simple_white',
                        xaxis_title="age [yr]", 
                        yaxis_title="Mass of layer [M<sub>&#8857;</sub>]")

    return f

def radii_on_click(mesa_model, id = 1, fig_width=1200, fig_height=800):

    if id == 1:
        line_color = 'royalblue'
    else:
        line_color = 'darkorange'

    q = mesa_model.bdf["star_2_mass"] / mesa_model.bdf["star_1_mass"]
    mesa_model.bdf[f"star_{id}_rL2"] = mesa_model.bdf[f"rl_{id}"] * (0.784 * q**1.05 * np.exp(-0.188 * q) + 1.004)

    f = px.line(mesa_model.bdf, x="age", y=f"star_{id}_radius", 
                custom_data=['age', f'star_{id}_radius']).update_traces(name='R', line =dict(color=line_color, width=3),
                hovertemplate='Age: %{customdata[0]:.3e} yrs <br> R: %{customdata[1]:.2f} M<sub>&#8857;</sub>')

    f.add_trace(px.line(mesa_model.bdf, x="age", y=f"rl_{id}", 
                custom_data=['age', f'rl_{id}']).update_traces(name='R<sub>L1</sub>', line_color='peru',
                hovertemplate='Age: %{customdata[0]:.3e} yrs <br> R<sub>L1</sub>: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])

    f.add_trace(px.line(mesa_model.bdf, x="age", y=f"star_{id}_rL2", 
                custom_data=['age', f"star_{id}_rL2"]).update_traces(name='R<sub>L2</sub>', line_color='sienna',
                hovertemplate='Age: %{customdata[0]:.3e} yrs <br> R<sub>L2</sub>: %{customdata[1]:.2f} M<sub>&#8857;</sub>').data[0])
    f.update_traces(showlegend=True)
    #f.update_layout(template='simple_white',
    #                legend_title="",
    #                legend=dict(x=0.98,
    #                            y=0.98,
    #                            xanchor="right",
    #                            yanchor="top",
    #                            font=dict(size=14)))

    return f

"""
    # roche lobe plots
        ax = axa[2]
        q = bd['star_2_mass'] / bd['star_1_mass']
        r_l2 = bd['rl_1'] * (0.784 * q**1.05 * np.exp(-0.188 * q) + 1.004)
        d_l2 = bd['rl_1'] * (3.334 * q**0.514 * np.exp(-0.052 * q) + 1.308)
        label = r'$\rm R_{L2,1}\ (Devina)$' if i == 0 else ''
        ax.plot(x_bh, r_l2, lw = lw, c = s1color, ls='-.', label=label)
        label = r'$\rm D_{L2,1}\ (Devina)$' if i == 0 else ''
        ax.plot(x_bh, d_l2, lw = lw, c = s1color, ls='--', label=label)
        ax.plot(x_bh, bd['star_1_radius'], lw = lw, c = s1color)
        ax.scatter(x_bh[lbv_index_bh], bd['star_1_radius'][lbv_index_bh], edgecolor='k', 
                   facecolor = 'pink', lw=2, marker = 'o', s = 100, zorder=2)
        ax.plot(x_bh, bd['star_2_radius'], lw = lw, c = s2color)
        label = r"$\rm R_{RL,1}$" if i == 0 else ''
        ax.plot(x_bh, bd['rl_1'], lw = lw, c = s1color, ls = ':', label = label)
        label = r"$\rm R_{RL,2}$" if i == 0 else ''
        ax.plot(x_bh, bd['rl_2'], lw = lw, c = s2color, ls = ':', label = label)
        label = r"$\rm a_{sep}$" if i == 0 else ''
        sep_color = 'firebrick' if i == 0 else 'coral'
        ax.plot(x_bh, bd['binary_separation'], c=sep_color, lw = lw, label=label)
        r_lbv1 = np.array([np.inf if L <= 6e5 else 1e5/np.sqrt(L) for L in 10**d['log_L']])
        r_lbv2 = np.array([np.inf if L <= 6e5 else 1e5/np.sqrt(L) for L in 10**d2['log_L']])
        label = r'$\rm R_{LBV,1}$' if i == 0 else ''
        ax.plot(x_h1, r_lbv1, lw = lw, c = s1color_alt, label=label)
        label = r'$\rm R_{LBV,2}$' if i == 0 else ''
        ax.plot(x_h2, r_lbv2, lw = lw, c = s2color_alt, label=label)
"""

"""
    # envelope mass plot
        ax = axa[3]
        h_layer_mass = d['star_mass'] - d['he_core_mass']
        he_layer_mass = d['he_core_mass'] - d['c_core_mass']
        c_layer_mass = d['c_core_mass'] - d['o_core_mass']
        o_layer_mass = d['o_core_mass']
        ax.plot(x_h1, d['star_mass'], lw = lw, ls = '-', c=s1color, label = '')
        #ax.plot(x_h1, h_layer_mass, lw = lw, ls = '--', c=s1color, label = 'H layer', alpha=alpha)
        #ax.plot(x_h1, he_layer_mass, lw = lw, ls = '-.', c=s1color, label= 'He layer', alpha=alpha)
        #ax.plot(x_h1, c_layer_mass, lw = lw, ls = ':', c=s1color, label= 'C layer', alpha=alpha)
        #ax.plot(x_bh, transferred - accreted, lw = 3, label ='diff')
        if i == 0:
            ax.set_ylabel(r'$\rm \bf Envelope\ Mass\ [M_{\odot}]$', fontsize=ylabel_size, fontweight='bold')
            ax.set_xlabel(xlabel, fontsize=xlabel_size, fontweight='bold')
            #ax.fill_between(x_h1, d['star_mass']*0, d['star_mass'], ls = '-', lw=2,
            #                facecolor='aquamarine', edgecolor=s1color, alpha=0.4, label="Star mass")
            ax.fill_between(x_h1, o_layer_mass + c_layer_mass + he_layer_mass, 
                            o_layer_mass + c_layer_mass + he_layer_mass + h_layer_mass, 
                        edgecolor='none', facecolor='tab:orange',
                        lw = lw, ls='-', alpha=0.4, label = 'H layer')
            ax.fill_between(x_h1, o_layer_mass + c_layer_mass, o_layer_mass + c_layer_mass + he_layer_mass, 
                            edgecolor=s1color, facecolor='none',
                        lw = lw, ls='-', alpha=0.4, label = 'He layer', hatch='o')
            ax.fill_between(x_h1, o_layer_mass, o_layer_mass + c_layer_mass, 
                            edgecolor=s1color, facecolor='aquamarine',
                        lw = lw, ls='-', alpha=0.4, label = 'C layer')
            ax.fill_between(x_h1, o_layer_mass*0, o_layer_mass, edgecolor=s1color, facecolor='gold',
                        lw = lw, ls='-', alpha=0.4, label = 'O layer')
            ax.tick_params(axis='both', which='major', labelsize=major_tick_size)
            ax.tick_params(axis='both', which='minor', labelsize=minor_tick_size)
            ax.legend(loc='best', prop=dict(size=20), frameon=False)
            ax.set_xlim(xlims_bh)
            ax.set_xscale(xscale)
            #ax.set_yscale('log')
"""