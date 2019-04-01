#! /usr/bin/env python
"""Prepares plots for BIAS tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1:
    IGDP_MIR_IC_V_VDETCOM
    IGDP_MIR_SW_V_VDETCOM
    IGDP_MIR_LW_V_VDETCOM

    Plot 2:
    IGDP_MIR_IC_V_VSSOUT
    IGDP_MIR_SW_V_VSSOUT
    IGDP_MIR_LW_V_VSSOUT

    Plot 3:
    IGDP_MIR_IC_V_VRSTOFF
    IGDP_MIR_SW_V_VRSTOFF
    IGDP_MIR_LW_V_VRSTOFF

    Plot 4:
    IGDP_MIR_IC_V_VP
    IGDP_MIR_SW_V_VP
    IGDP_MIR_LW_V_VP

    Plot 5
    IGDP_MIR_IC_V_VDDUC
    IGDP_MIR_SW_V_VDDUC
    IGDP_MIR_LW_V_VDDUC

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``dashborad.py``, e.g.:

    ::
        from .plots.bias_tab import bias_plots
        tab = bias_plots(conn, start, end)

Dependencies
------------
    User must provide database "miri_database.db"

"""

import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure
from bokeh.models.widgets import Panel, Tabs, Div
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.layouts import gridplot, Column

import pandas as pd
import numpy as np

from astropy.time import Time


def vdetcom(conn, start, end):
    '''Create specific plot and return plot object
    Parameters
    ----------
    conn : DBobject
        Connection object that represents database
    start : time
        Startlimit for x-axis and query (typ. datetime.now()- 4Months)
    end : time
        Endlimit for x-axis and query (typ. datetime.now())
    Return
    ------
    p : Plot object
        Bokeh plot
    '''

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "VDETCOM"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "VDETCOM IC", "IGDP_MIR_IC_V_VDETCOM", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "VDETCOM SW", "IGDP_MIR_SW_V_VDETCOM", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "VDETCOM LW", "IGDP_MIR_LW_V_VDETCOM", start, end, conn, color = "green")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vssout(conn, start, end):
    '''Create specific plot and return plot object
    Parameters
    ----------
    conn : DBobject
        Connection object that represents database
    start : time
        Startlimit for x-axis and query (typ. datetime.now()- 4Months)
    end : time
        Endlimit for x-axis and query (typ. datetime.now())
    Return
    ------
    p : Plot object
        Bokeh plot
    '''

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "VSSOUT"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "VSSOUT IC", "IGDP_MIR_IC_V_VSSOUT", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "VSSOUT SW", "IGDP_MIR_SW_V_VSSOUT", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "VSSOUT LW", "IGDP_MIR_LW_V_VSSOUT", start, end, conn, color = "green")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vrstoff(conn, start, end):
    '''Create specific plot and return plot object
    Parameters
    ----------
    conn : DBobject
        Connection object that represents database
    start : time
        Startlimit for x-axis and query (typ. datetime.now()- 4Months)
    end : time
        Endlimit for x-axis and query (typ. datetime.now())
    Return
    ------
    p : Plot object
        Bokeh plot
    '''

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "VRSTOFF"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "VRSTOFF IC", "IGDP_MIR_IC_V_VRSTOFF", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "VRSTOFF SW", "IGDP_MIR_SW_V_VRSTOFF", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "VRSTOFF LW", "IGDP_MIR_LW_V_VRSTOFF", start, end, conn, color = "green")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vp(conn, start, end):
    '''Create specific plot and return plot object
    Parameters
    ----------
    conn : DBobject
        Connection object that represents database
    start : time
        Startlimit for x-axis and query (typ. datetime.now()- 4Months)
    end : time
        Endlimit for x-axis and query (typ. datetime.now())
    Return
    ------
    p : Plot object
        Bokeh plot
    '''

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "VP"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "VP IC", "IGDP_MIR_IC_V_VP", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "VP SW", "IGDP_MIR_SW_V_VP", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "VP LW", "IGDP_MIR_LW_V_VP", start, end, conn, color = "green")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vdduc(conn, start, end):
    '''Create specific plot and return plot object
    Parameters
    ----------
    conn : DBobject
        Connection object that represents database
    start : time
        Startlimit for x-axis and query (typ. datetime.now()- 4Months)
    end : time
        Endlimit for x-axis and query (typ. datetime.now())
    Return
    ------
    p : Plot object
        Bokeh plot
    '''

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "VDDUC"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "VDDUC IC", "IGDP_MIR_IC_V_VDDUC", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "VDDUC SW", "IGDP_MIR_SW_V_VDDUC", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "VDDUC LW", "IGDP_MIR_LW_V_VDDUC", start, end, conn, color = "green")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def bias_plots(conn, start, end):
    '''Combines plots to a tab
    Parameters
    ----------
    conn : DBobject
        Connection object that represents database
    start : time
        Startlimit for x-axis and query (typ. datetime.now()- 4Months)
    end : time
        Endlimit for x-axis and query (typ. datetime.now())
    Return
    ------
    p : tab object
        used by dashboard.py to set up dashboard
    '''

    descr = Div(text=
    """
    <style>
    table, th, td {
      border: 1px solid black;
      background-color: #efefef;
      border-collapse: collapse;
      padding: 5px
    }
    table {
      border-spacing: 15px;
    }
    </style>

    <body>
    <table style="width:100%">
      <tr>
        <th><h6>Plotname</h6></th>
        <th><h6>Mnemonic</h6></th>
        <th><h6>Description</h6></th>
      </tr>
      <tr>
        <td>VSSOUT</td>
        <td>IGDP_MIR_IC_V_VSSOUT<br>
            IGDP_MIR_SW_V_VSSOUT<br>
            IGDP_MIR_LW_V_VSSOUT<br> </td>
        <td>Detector Bias VSSOUT (IC,SW, & LW)</td>
      </tr>
      <tr>
        <td>VDETCOM</td>
        <td>IGDP_MIR_IC_V_VDETCOM<br>
            IGDP_MIR_SW_V_VDETCOM<br>
            IGDP_MIR_LW_V_VDETCOM<br> </td>
        <td>Detector Bias VDETCOM (IC,SW, & LW)</td>
      </tr>
      <tr>
        <td>VRSTOFF</td>
        <td>IGDP_MIR_IC_V_VRSTOFF<br>
            IGDP_MIR_SW_V_VRSTOFF<br>
            IGDP_MIR_LW_V_VRSTOFF<br> </td>
        <td>Detector Bias VRSTOFF (IC,SW, & LW)</td>
      </tr>
      <tr>
        <td>VP</td>
        <td>IGDP_MIR_IC_V_VP<br>
            IGDP_MIR_SW_V_VP<br>
            IGDP_MIR_LW_V_VP<br> </td>
        <td>Detector Bias VP (IC,SW, & LW)</td>
      </tr>
      <tr>
        <td>VDDUC</td>
        <td>IGDP_MIR_IC_V_VDDUC<br>
            IGDP_MIR_SW_V_VDDUC<br>
            IGDP_MIR_LW_V_VDDUC<br> </td>
        <td>Detector Bias VDDUC (IC,SW, & LW)</td>
      </tr>

    </table>
    </body>
    """, width=1100)

    plot1 = vdetcom(conn, start, end)
    plot2 = vssout(conn, start, end)
    plot3 = vrstoff(conn, start, end)
    plot4 = vp(conn, start, end)
    plot5 = vdduc(conn, start, end)

    l = gridplot([ [plot2, plot1],              \
                        [plot3, plot4],         \
                        [plot5, None]], merge_tools=False)

    layout = Column(descr, l)

    tab = Panel(child = layout, title = "BIAS")

    return tab
