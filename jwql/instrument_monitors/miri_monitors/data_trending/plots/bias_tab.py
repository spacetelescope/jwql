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
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource
from bokeh.layouts import gridplot

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
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VDETCOM"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    pf.add_to_plot(p, "VDETCOM IC", "IGDP_MIR_IC_V_VDETCOM", start, end, conn, color = "red")
    pf.add_to_plot(p, "VDETCOM SW", "IGDP_MIR_SW_V_VDETCOM", start, end, conn, color = "orange")
    pf.add_to_plot(p, "VDETCOM LW", "IGDP_MIR_LW_V_VDETCOM", start, end, conn, color = "green")

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
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VSSOUT"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    pf.add_to_plot(p, "VSSOUT IC", "IGDP_MIR_IC_V_VSSOUT", start, end, conn, color = "red")
    pf.add_to_plot(p, "VSSOUT SW", "IGDP_MIR_SW_V_VSSOUT", start, end, conn, color = "orange")
    pf.add_to_plot(p, "VSSOUT LW", "IGDP_MIR_LW_V_VSSOUT", start, end, conn, color = "green")

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
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VRSTOFF"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    pf.add_to_plot(p, "VRSTOFF IC", "IGDP_MIR_IC_V_VRSTOFF", start, end, conn, color = "red")
    pf.add_to_plot(p, "VRSTOFF SW", "IGDP_MIR_SW_V_VRSTOFF", start, end, conn, color = "orange")
    pf.add_to_plot(p, "VRSTOFF LW", "IGDP_MIR_LW_V_VRSTOFF", start, end, conn, color = "green")

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
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VP"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    pf.add_to_plot(p, "VP IC", "IGDP_MIR_IC_V_VP", start, end, conn, color = "red")
    pf.add_to_plot(p, "VP SW", "IGDP_MIR_SW_V_VP", start, end, conn, color = "orange")
    pf.add_to_plot(p, "VP LW", "IGDP_MIR_LW_V_VP", start, end, conn, color = "green")

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
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VDDUC"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    pf.add_to_plot(p, "VDDUC IC", "IGDP_MIR_IC_V_VDDUC", start, end, conn, color = "red")
    pf.add_to_plot(p, "VDDUC SW", "IGDP_MIR_SW_V_VDDUC", start, end, conn, color = "orange")
    pf.add_to_plot(p, "VDDUC LW", "IGDP_MIR_LW_V_VDDUC", start, end, conn, color = "green")

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

    plot1 = vdetcom(conn, start, end)
    plot2 = vssout(conn, start, end)
    plot3 = vrstoff(conn, start, end)
    plot4 = vp(conn, start, end)
    plot5 = vdduc(conn, start, end)

    layout = gridplot([ [plot2, plot1],         \
                        [plot3, plot4],         \
                        [plot5, None]], merge_tools=False)

    tab = Panel(child = layout, title = "BIAS")

    return tab
