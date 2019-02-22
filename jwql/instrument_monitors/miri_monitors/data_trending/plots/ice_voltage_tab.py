#! /usr/bin/env python
"""Prepares plots for FPE VOLTAGE tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.


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
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource
from bokeh.layouts import gridplot

import pandas as pd
import numpy as np

from astropy.time import Time

def volt4(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [4.2,5],                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "ICE_SEC_VOLT4"
    pf.add_basic_layout(p)

    # add a line renderer with legend and line thickness

    pf.add_to_plot(p, "Volt4 Idle", "IMIR_HK_ICE_SEC_VOLT4_IDLE", start, end, conn, color = "orange")
    pf.add_to_plot(p, "Volt4 Hv on", "IMIR_HK_ICE_SEC_VOLT4_HV_ON" ,start, end, conn, color = "red")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt1_3(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [30,50],                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "ICE_SEC_VOLT1/3"
    pf.add_basic_layout(p)

    # add a line renderer with legend and line thickness
    pf.add_to_plot(p, "Volt1", "IMIR_HK_ICE_SEC_VOLT1" ,start, end, conn, color = "red")
    pf.add_to_plot(p, "Volt3", "IMIR_HK_ICE_SEC_VOLT3" ,start, end, conn, color = "purple")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt2(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "ICE_SEC_VOLT2"
    pf.add_basic_layout(p)

    # add a line renderer with legend and line thickness
    pf.add_to_plot(p, "Volt2", "IMIR_HK_ICE_SEC_VOLT2", start, end, conn, color = "red")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def pos_volt(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [280,300],                                \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (mV)')

    p.grid.visible = True
    p.title.text = "Wheel Sensor Voltage"
    pf.add_basic_layout(p)

    pf.add_to_plot(p, "FW", "IMIR_HK_FW_POS_VOLT" ,start, end, conn, color = "red")
    pf.add_to_plot(p, "GW14", "IMIR_HK_GW14_POS_VOLT" ,start, end, conn, color = "purple")
    pf.add_to_plot(p, "GW23", "IMIR_HK_GW23_POS_VOLT" ,start, end, conn, color = "orange")
    pf.add_to_plot(p, "CCC", "IMIR_HK_CCC_POS_VOLT" ,start, end, conn, color = "firebrick")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt_plots(conn, start, end):

    plot1 = volt1_3(conn, start, end)
    plot2 = volt2(conn, start, end)
    plot3 = volt4(conn, start, end)
    plot4 = pos_volt(conn, start, end)

    layout = gridplot([[plot1, plot2], [plot3, plot4]], merge_tools = False)

    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "ICE/WHEEL VOLTAGE")

    return tab
