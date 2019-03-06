#! /usr/bin/env python
"""Prepares plots for FPE VOLTAGE tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1:
    IMIR_HK_FW_POS_RATIO_FND
    IMIR_HK_FW_POS_RATIO_OPAQUE
    IMIR_HK_FW_POS_RATIO_F1000W
    IMIR_HK_FW_POS_RATIO_F1130W
    IMIR_HK_FW_POS_RATIO_F1280W
    IMIR_HK_FW_POS_RATIO_P750L
    IMIR_HK_FW_POS_RATIO_F1500W
    IMIR_HK_FW_POS_RATIO_F1800W
    IMIR_HK_FW_POS_RATIO_F2100W
    IMIR_HK_FW_POS_RATIO_F560W
    IMIR_HK_FW_POS_RATIO_FLENS
    IMIR_HK_FW_POS_RATIO_F2300C
    IMIR_HK_FW_POS_RATIO_F770W
    IMIR_HK_FW_POS_RATIO_F1550C
    IMIR_HK_FW_POS_RATIO_F2550W
    IMIR_HK_FW_POS_RATIO_F1140C
    IMIR_HK_FW_POS_RATIO_F2550WR
    IMIR_HK_FW_POS_RATIO_F1065C

    Plot 2:
    IMIR_HK_GW14_POS_RATIO_SHORT
    IMIR_HK_GW14_POS_RATIO_MEDIUM
    IMIR_HK_GW14_POS_RATIO_LONG

    Plot 3:
    IMIR_HK_GW23_POS_RATIO_SHORT
    IMIR_HK_GW23_POS_RATIO_MEDIUM
    IMIR_HK_GW23_POS_RATIO_LONG

    Plot 4:
    IMIR_HK_CCC_POS_RATIO_LOCKED
    IMIR_HK_CCC_POS_RATIO_OPEN
    IMIR_HK_CCC_POS_RATIO_CLOSED

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``dashboard.py``, e.g.:

    ::
        from .plots.wheel_ratio_tab import wheel_plots
        tab = wheel_plots(conn, start, end)

Dependencies
------------
    User must provide database "miri_database.db"

"""

import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs, Div
from bokeh.models import ColumnDataSource
from bokeh.layouts import column, row, WidgetBox

import pandas as pd
import numpy as np

from astropy.time import Time


def gw14(conn, start, end):
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
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                y_range = [-2,2],                                   \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'ratio (normalized)')

    p.grid.visible = True
    p.title.text = "DGA-A Ratio"
    p.title.align = "left"
    pf.add_basic_layout(p)

    pf.add_to_wplot(p, "SHORT", "IMIR_HK_GW14_POS_RATIO_SHORT", start, end, conn, mn.gw14_nominals['SHORT'], color = "green")
    pf.add_to_wplot(p, "MEDIUM", "IMIR_HK_GW14_POS_RATIO_MEDIUM", start, end, conn, mn.gw14_nominals['MEDIUM'], color = "red")
    pf.add_to_wplot(p, "LONG", "IMIR_HK_GW14_POS_RATIO_LONG", start, end, conn, mn.gw14_nominals['LONG'], color = "blue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def gw23(conn, start, end):
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
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                y_range = [-2,2],                                   \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'ratio (normalized)')

    p.grid.visible = True
    p.title.text = "DGA-B Ratio"
    p.title.align = "left"
    pf.add_basic_layout(p)

    pf.add_to_wplot(p, "SHORT", "IMIR_HK_GW23_POS_RATIO_SHORT", start, end, conn, mn.gw23_nominals['SHORT'], color = "green")
    pf.add_to_wplot(p, "MEDIUM", "IMIR_HK_GW23_POS_RATIO_MEDIUM", start, end, conn, mn.gw23_nominals['MEDIUM'], color = "red")
    pf.add_to_wplot(p, "LONG", "IMIR_HK_GW23_POS_RATIO_LONG", start, end, conn, mn.gw23_nominals['LONG'], color = "blue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def ccc(conn, start, end):
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
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                y_range = [-2,2],                                   \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'ratio (normalized)')

    p.grid.visible = True
    p.title.text = "CCC Ratio"
    pf.add_basic_layout(p)

    #add_to_wplot(p, "LOCKED", "IMIR_HK_CCC_POS_RATIO_LOCKED", start, end, conn, mn.ccc_nominals['LOCKED'], color = "green")
    pf.add_to_wplot(p, "OPEN", "IMIR_HK_CCC_POS_RATIO_OPEN", start, end, conn, mn.ccc_nominals['OPEN'], color = "red")
    pf.add_to_wplot(p, "CLOSED", "IMIR_HK_CCC_POS_RATIO_CLOSED", start, end, conn, mn.ccc_nominals['CLOSED'], color = "blue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def fw(conn, start, end):
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
                plot_width = 1120,                                   \
                plot_height = 800,                                  \
                y_range = [-6,4],                                   \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='ratio (normalized)')

    p.grid.visible = True
    p.title.text = "Filterwheel Ratio"
    pf.add_basic_layout(p)

    pf.add_to_wplot(p, "FND", "IMIR_HK_FW_POS_RATIO_FND", start, end, conn, mn.fw_nominals['FND'], color = "green")
    pf.add_to_wplot(p, "OPAQUE", "IMIR_HK_FW_POS_RATIO_OPAQUE", start, end, conn, mn.fw_nominals['OPAQUE'], color = "red")
    pf.add_to_wplot(p, "F1000W", "IMIR_HK_FW_POS_RATIO_F1000W", start, end, conn, mn.fw_nominals['F1000W'], color = "blue")
    pf.add_to_wplot(p, "F1130W", "IMIR_HK_FW_POS_RATIO_F1130W", start, end, conn, mn.fw_nominals['F1130W'], color = "orange")
    pf.add_to_wplot(p, "F1280W", "IMIR_HK_FW_POS_RATIO_F1280W", start, end, conn, mn.fw_nominals['F1280W'], color = "firebrick")
    pf.add_to_wplot(p, "P750L", "IMIR_HK_FW_POS_RATIO_P750L", start, end, conn, mn.fw_nominals['P750L'], color = "cyan")
    pf.add_to_wplot(p, "F1500W", "IMIR_HK_FW_POS_RATIO_F1500W", start, end, conn, mn.fw_nominals['F1500W'], color = "magenta")
    pf.add_to_wplot(p, "F1800W", "IMIR_HK_FW_POS_RATIO_F1800W", start, end, conn, mn.fw_nominals['F1800W'], color = "burlywood")
    pf.add_to_wplot(p, "F2100W", "IMIR_HK_FW_POS_RATIO_F2100W", start, end, conn, mn.fw_nominals['F2100W'], color = "cadetblue")
    pf.add_to_wplot(p, "F560W", "IMIR_HK_FW_POS_RATIO_F560W", start, end, conn, mn.fw_nominals['F560W'], color = "chartreuse")
    pf.add_to_wplot(p, "FLENS", "IMIR_HK_FW_POS_RATIO_FLENS", start, end, conn, mn.fw_nominals['FLENS'], color = "brown")
    pf.add_to_wplot(p, "F2300C", "IMIR_HK_FW_POS_RATIO_F2300C", start, end, conn, mn.fw_nominals['F2300C'], color = "chocolate")
    pf.add_to_wplot(p, "F770W", "IMIR_HK_FW_POS_RATIO_F770W", start, end, conn, mn.fw_nominals['F770W'], color = "darkorange")
    pf.add_to_wplot(p, "F1550C", "IMIR_HK_FW_POS_RATIO_F1550C", start, end, conn, mn.fw_nominals['F1550C'], color = "darkgreen")
    pf.add_to_wplot(p, "F2550W", "IMIR_HK_FW_POS_RATIO_F2550W", start, end, conn, mn.fw_nominals['F2550W'], color = "darkcyan")
    pf.add_to_wplot(p, "F1140C", "IMIR_HK_FW_POS_RATIO_F1140C", start, end, conn, mn.fw_nominals['F1140C'], color = "darkmagenta")
    pf.add_to_wplot(p, "F2550WR", "IMIR_HK_FW_POS_RATIO_F2550WR", start, end, conn, mn.fw_nominals['F2550WR'], color = "crimson")
    pf.add_to_wplot(p, "F1065C", "IMIR_HK_FW_POS_RATIO_F1065C", start, end, conn, mn.fw_nominals['F1065C'], color = "cornflowerblue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def wheel_ratios(conn, start, end):
    '''Combine plots to a tab
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
    </style>

    <body>
    <table style="width:100%">
      <tr>
        <th><h6>Plotname</h6></th>
        <th><h6>Mnemonic</h6></th>
        <th><h6>Description</h6></th>
      </tr>
      <tr>
        <td>Filterwheel Ratio</td>
        <td>IMIR_HK_FW_POS_RATIO<br>
            IMIR_HK_FW_CUR_POS<br></td>
        <td>FW position sensor ratio (normalised) and commanded position</td>
      </tr>
      <tr>
        <td>DGA-A Ratio</td>
        <td>IMIR_HK_GW14_POS_RATIO<br>
            IMIR_HK_GW14_CUR_POS<br></td>
        <td>DGA-A position sensor ratio (normalised) and commanded position</td>
      </tr>
      <tr>
        <td>DGA-B Ratio</td>
        <td>IMIR_HK_GW23_POS_RATIO<br>
            IMIR_HK_GW23_CUR_POS<br></td>
        <td>DGA-B position sensor ratio (normalised) and commanded position</td>
      </tr>
      <tr>
        <td>CCC Ratio</td>
        <td>IMIR_HK_CCC_POS_RATIO<br>
            IMIR_HK_CCC_CUR_POS<br></td>
        <td>Contamination Control Cover position sensor ratio (normalised) and commanded position</td>
      </tr>
    </table>
    </body>
    """, width=1100)

    plot1 = fw(conn, start, end)
    plot2 = gw14(conn, start, end)
    plot3 = gw23(conn,  start, end)
    plot4 = ccc(conn, start, end)

    layout = column(descr, plot1, plot2, plot3, plot4)
    tab = Panel(child = layout, title = "WHEEL RATIO")

    return tab
