#! /usr/bin/env python
"""Prepares plots for Ref. Voltage/Currents tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - Ref Voltages OA (Voltages)
    INRSH_OA_VREFOFF
    INRSH_OA_VREF

    Plot 2 - CAA (Voltages and Currents)
    INRSH_CAA_VREFOFF
    INRSH_CAA_VREF
    INRSI_C_CAA_CURRENT
    INRSI_C_CAA_VOLTAGE

    Plot 3 - FWA (Voltages)
    INRSH_FWA_ADCMGAIN
    INRSH_FWA_ADCMOFFSET
    INRSH_FWA_MOTOR_VREF

    Plot 4 - GWA (Voltages)
    INRSH_GWA_ADCMGAIN
    INRSH_GWA_ADCMOFFSET
    INRSH_GWA_MOTOR_VREF

    Plot 5 - RMA (Voltages)
    INRSH_RMA_ADCMGAIN
    INRSH_RMA_ADCMOFFSET

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


def ref_volt(conn, start, end):
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
                plot_height = 500,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Ref Voltages OA (Voltages)"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "OA_VREFOFF", "INRSH_OA_VREFOFF", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "OA_VREF", "INRSH_OA_VREF", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

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

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",
                toolbar_location = "above",
                plot_width = 1120,
                plot_height = 500,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "CAA Voltages and Currents"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=0, end=2500)}
    a = pf.add_to_plot(p, "CAA_VREFOFF", "INRSH_CAA_VREFOFF", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "CAA_VREF", "INRSH_CAA_VREF", start, end, conn, color = "green")
    c = pf.add_to_plot(p, "C_CAA_VOLTAGE", "INRSI_C_CAA_CURRENT", start, end, conn, color = "orange")
    d = pf.add_to_plot(p, "CAA_VREFOFF", "", start, end, conn, color = "red")
    e = pf.add_to_plot(p, "C_CAA_CURRENT", "INRSI_C_CAA_CURRENT", start, end, conn, y_axis = "current", color = "blue")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b,c,d,e])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def fwa_volt(conn, start, end):
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
                plot_height = 500,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FWA"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "ADCMGAIN", "INRSH_FWA_ADCMGAIN", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "ADCMOFFSET", "INRSH_FWA_ADCMOFFSET", start, end, conn, color = "blue")
    c = pf.add_to_plot(p, "MOTOR_VREF", "INRSH_FWA_MOTOR_VREF", start, end, conn, color = "green")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def gwa_volt(conn, start, end):
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
                plot_height = 500,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "GWA"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "ADCMGAIN", "INRSH_GWA_ADCMGAIN", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "ADCMOFFSET", "INRSH_GWA_ADCMOFFSET", start, end, conn, color = "blue")
    c = pf.add_to_plot(p, "MOTOR_VREF", "INRSH_GWA_MOTOR_VREF", start, end, conn, color = "green")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def rma_volt(conn, start, end):
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
                plot_height = 500,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "RMA"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "ADCMGAIN", "INRSH_RMA_ADCMGAIN", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "ADCMOFFSET", "INRSH_RMA_ADCMOFFSET", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt_plots(conn, start, end):
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
        <td>DEFAULT</td>
        <td>DEFAULT</td>
        <td>DEAULT</td>
      </tr>
    </table>
    </body>
    """, width=1100)

    #plot1 = ref_volt(conn, start, end)
    #plot2 = caa_volt(conn, start, end)
    #plot3 = fwa_volt(conn, start, end)
    #plot4 = gwa_volt(conn, start, end)
    plot5 = rma_volt(conn, start, end)

    layout = Column(descr, plot1, plot5)

    tab = Panel(child = layout, title = "Ref. VOLTAGES and CURRENTS")

    return tab
