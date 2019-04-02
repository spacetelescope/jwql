#! /usr/bin/env python
"""Prepares plots for CAA tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - Lamp Voltages and Currents (Distincted)
    INRSH_LAMP_SEL
    INRSI_C_CAA_CURRENT
    INRSI_C_CAA_VOLTAGE

    Plot 2 - CAA (Voltages and Currents)
    INRSH_CAA_VREFOFF
    INRSH_CAA_VREF

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``nirspec_dashboard.py``, e.g.:

    ::
        from .plots.voltage_tab import voltage_plots
        tab = voltage_plots(conn, start, end)

Dependencies
------------
    User must provide database "nirpsec_database.db"

"""
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.plot_functions as pf
from bokeh.models import LinearAxis, Range1d
from bokeh.plotting import figure
from bokeh.models.widgets import Panel, Tabs, Div
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.layouts import WidgetBox, gridplot, Column

import pandas as pd
import numpy as np

from astropy.time import Time


def lamp_volt(conn, start, end):
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
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",
                toolbar_location = "above",
                plot_width = 1120,
                plot_height = 800,
                y_range = [1.2,2.3],
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "CAA Lamp Voltages"
    pf.add_basic_layout(p)

    l = pf.add_to_plot(p, "FLAT1", "LAMP_FLAT1_VOLT", start, end, conn, color = "red")
    m = pf.add_to_plot(p, "FLAT2", "LAMP_FLAT2_VOLT", start, end, conn, color = "green")
    n = pf.add_to_plot(p, "FLAT3", "LAMP_FLAT3_VOLT", start, end, conn, color = "blue")
    o = pf.add_to_plot(p, "FLAT4", "LAMP_FLAT4_VOLT", start, end, conn, color = "brown")
    x = pf.add_to_plot(p, "FLAT5", "LAMP_FLAT5_VOLT", start, end, conn, color = "orange")
    q = pf.add_to_plot(p, "LINE1", "LAMP_LINE1_VOLT", start, end, conn, color = "cyan")
    r = pf.add_to_plot(p, "LINE2", "LAMP_LINE2_VOLT", start, end, conn, color = "darkmagenta")
    s = pf.add_to_plot(p, "LINE3", "LAMP_LINE3_VOLT", start, end, conn, color = "burlywood")
    t = pf.add_to_plot(p, "LINE4", "LAMP_LINE4_VOLT", start, end, conn, color = "darkkhaki")
    u = pf.add_to_plot(p, "REF", "LAMP_REF_VOLT", start, end, conn, color = "darkblue")
    v = pf.add_to_plot(p, "TEST", "LAMP_TEST_VOLT", start, end, conn, color = "goldenrod")

    pf.add_hover_tool(p,[l,m,n,o,x,q,r,s,t,u,v])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def lamp_current(conn, start, end):
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
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",
                toolbar_location = "above",
                plot_width = 1120,
                plot_height = 600,
                y_range = [10.5,14.5],
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Current (mA)')

    p.grid.visible = True
    p.title.text = "CAA Lamp currents"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "FLAT1", "LAMP_FLAT1_CURR", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "FLAT2", "LAMP_FLAT2_CURR", start, end, conn, color = "green")
    c = pf.add_to_plot(p, "FLAT3", "LAMP_FLAT3_CURR", start, end, conn, color = "blue")
    d = pf.add_to_plot(p, "FLAT4", "LAMP_FLAT4_CURR", start, end, conn, color = "brown")
    e = pf.add_to_plot(p, "FLAT5", "LAMP_FLAT5_CURR", start, end, conn, color = "orange")
    f = pf.add_to_plot(p, "LINE1", "LAMP_LINE1_CURR", start, end, conn, color = "cyan")
    g = pf.add_to_plot(p, "LINE2", "LAMP_LINE2_CURR", start, end, conn, color = "darkmagenta")
    h = pf.add_to_plot(p, "LINE3", "LAMP_LINE3_CURR", start, end, conn, color = "burlywood")
    i = pf.add_to_plot(p, "LINE4", "LAMP_LINE4_CURR", start, end, conn, color = "darkkhaki")
    j = pf.add_to_plot(p, "REF", "LAMP_REF_CURR", start, end, conn, color = "darkblue")
    k = pf.add_to_plot(p, "TEST", "LAMP_TEST_CURR", start, end, conn, color = "goldenrod")

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h,i,j,k])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def caa_volt(conn, start, end):
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

    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",
                toolbar_location = "above",
                plot_width = 1120,
                plot_height = 600,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    a = pf.add_to_plot(p, "CAA_VREFOFF", "INRSH_CAA_VREFOFF", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "CAA_VREF", "INRSH_CAA_VREF", start, end, conn, color = "green")

    #pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def caa_plots(conn, start, end):
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
        <td>CAA Lamp Voltages</td>
        <td>INRSH_LAMP_SEL<br>
            INRSI_C_CAA_VOLTAGE</td>
        <td>Lamp Voltage for each CAA Lamp</td>
      </tr>

      <tr>
        <td>CAA Lamp Currents</td>
        <td>INRSH_LAMP_SEL<br>
            INRSI_C_CAA_CURRENT</td>
        <td>Lamp Currents for each CAA Lamp</td>
      </tr>

    </table>
    </body>
    """, width=1100)

    plot1 = lamp_volt(conn, start, end)
    plot2 = lamp_current(conn, start, end)
    #plot3 = caa_plots(conn, start, end)

    layout = Column(descr, plot1, plot2)

    tab = Panel(child = layout, title = "CAA/LAMPS")

    return tab
