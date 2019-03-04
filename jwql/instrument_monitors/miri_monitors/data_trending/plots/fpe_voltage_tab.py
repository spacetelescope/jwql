#! /usr/bin/env python
"""Prepares plots for FPE VOLTAGE tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1:
    IMIR_PDU_V_DIG_5V
    IMIR_PDU_I_DIG_5V

    Plot 2:
    IMIR_PDU_V_ANA_5V
    IMIR_PDU_I_ANA_5V

    Plot 3:
    IMIR_PDU_V_ANA_N5V
    IMIR_PDU_I_ANA_N5V

    Plot 4:
    IMIR_PDU_V_ANA_7V
    IMIR_PDU_I_ANA_7V

    Plot 5:
    IMIR_PDU_V_ANA_N7V
    IMIR_PDU_I_ANA_N7V

    Plot 6:
    IMIR_SPW_V_DIG_2R5V
    IMIR_PDU_V_REF_2R5V

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``dashborad.py``, e.g.:

    ::
        from .plots.fpe_voltage_tab import fpe_plots
        tab = fpe_plots(conn, start, end)

Dependencies
------------
    User must provide database "miri_database.db"

"""
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.models import LinearAxis, Range1d
from bokeh.plotting import figure
from bokeh.models.widgets import Panel, Tabs, Div
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.layouts import WidgetBox, gridplot, Column

import pandas as pd
import numpy as np

from astropy.time import Time


def dig5(conn, start, end):
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
                plot_width = 560,
                plot_height = 500,
                y_range = [4.9,5.1],
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Dig. 5V"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=2100, end=2500)}
    a = pf.add_to_plot(p, "FPE Dig. 5V", "IMIR_PDU_V_DIG_5V", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "FPE Dig. 5V Current", "IMIR_PDU_I_DIG_5V", start, end, conn, y_axis = "current", color = "blue")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def refdig(conn, start, end):
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
                y_range = [2.45,2.55],                              \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "2.5V Ref and FPE Dig."
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "FPE Dig. 2.5V", "IMIR_SPW_V_DIG_2R5V", start, end, conn, color = "orange")
    b = pf.add_to_plot(p, "FPE PDU 2.5V REF", "IMIR_PDU_V_REF_2R5V", start, end, conn, color = "red")

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana5(conn, start, end):
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
                y_range = [4.95,5.05],                              \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. 5V"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=100, end=250)}
    a = pf.add_to_plot(p, "FPE Ana. 5V", "IMIR_PDU_V_ANA_5V",start, end, conn, color = "red")
    b = pf.add_to_plot(p, "FPE Ana. 5V Current", "IMIR_PDU_I_ANA_5V",start, end, conn, y_axis = "current", color = "blue")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana5n(conn, start, end):
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
                y_range = [-5.1,-4.85],                             \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. N5V"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=100, end=300)}
    a = pf.add_to_plot(p, "FPE Ana. N5", "IMIR_PDU_V_ANA_N5V",start, end, conn, color = "red")
    b = pf.add_to_plot(p, "FPE Ana. N5 Current", "IMIR_PDU_I_ANA_N5V",start, end, conn, y_axis = "current", color = "blue")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana7(conn, start, end):
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
                y_range = [6.85, 7.1],                              \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. 7V"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=300, end=450)}
    a = pf.add_to_plot(p, "FPE Ana. 7V", "IMIR_PDU_V_ANA_7V",start, end, conn, color = "red")
    b = pf.add_to_plot(p, "FPE Ana. 7V Current", "IMIR_PDU_I_ANA_7V",start, end, conn, y_axis = "current", color = "blue")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana7n(conn, start, end):
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
                y_range = [-7.1, -6.9],                             \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. N7V"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=350, end=400)}
    a = pf.add_to_plot(p, "FPE Dig. N7V", "IMIR_PDU_V_ANA_N7V",start, end, conn, color = "red")
    b = pf.add_to_plot(p, "FPE Ana. N7V Current", "IMIR_PDU_I_ANA_N7V",start, end, conn, y_axis = "current", color = "blue")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def fpe_plots(conn, start, end):
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
        <td>2.5V Ref and FPE Digg</td>
        <td>IMIR_SPW_V_DIG_2R5V<br>
            IMIR_PDU_V_REF_2R5V<br> </td>
        <td>FPE 2.5V Digital and FPE 2.5V PDU Reference Voltage</td>
      </tr>
      <tr>
        <td>FPE Dig. 5V</td>
        <td>IMIR_PDU_V_DIG_5V<br>
            IMIR_PDU_I_DIG_5V</td>
        <td>FPE 5V Digital Voltage and Current</td>
      </tr>
      <tr>
        <td>FPE Ana. 5V</td>
        <td>IMIR_PDU_V_ANA_5V<br>
            IMIR_PDU_I_ANA_5V</td>
        <td>FPE +5V Analog Voltage and Current</td>
      </tr>
      <tr>
        <td>FPE Ana. N5V</td>
        <td>IMIR_PDU_V_ANA_N5V<br>
            IMIR_PDU_I_ANA_N5V</td>
        <td>FPE -5V Analog Voltage and Current</td>
      </tr>
      <tr>
        <td>FPE Ana. 7V</td>
        <td>IMIR_PDU_V_ANA_7V<br>
            IMIR_PDU_I_ANA_7V</td>
        <td>FPE +7V Analog Voltage and Current</td>
      </tr>
       <tr>
         <td>FPE Ana. N7V</td>
         <td>IMIR_PDU_V_ANA_N7V<br>
             IMIR_PDU_I_ANA_N7V</td>
         <td>FPE -7V Analog Voltage and Current</td>
       </tr>
    </table>
    </body>
    """, width=1100)

    plot1 = dig5(conn, start, end)
    plot2 = refdig(conn, start, end)
    plot3 = ana5(conn, start, end)
    plot4 = ana5n(conn, start, end)
    plot5 = ana7(conn, start, end)
    plot6 = ana7n(conn, start, end)

    l = gridplot([  [plot2, plot1],        \
                    [plot3, plot4],        \
                    [plot5, plot6]], merge_tools=False)

    layout = Column(descr, l)

    tab = Panel(child = layout, title = "FPE VOLTAGE/CURRENT")

    return tab
