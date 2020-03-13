#! /usr/bin/env python
"""Prepares plots for Ref. Voltage/Currents tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - Ref Voltages
    INRSH_FWA_MOTOR_VREF
    INRSH_GWA_MOTOR_VREF
    INRSH_OA_VREF

    Plot 2 - ADCMGAIN (Voltages)
    INRSH_FWA_ADCMGAIN
    INRSH_GWA_ADCMGAIN
    INRSH_RMA_ADCMGAIN

    Plot 3 - OFFSET (Voltages)
    INRSH_GWA_ADCMOFFSET
    INRSH_FWA_ADCMOFFSET
    INRSH_OA_VREFOFF
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
import copy

from astropy.time import Time
from bokeh.layouts import Column
from bokeh.models.widgets import Panel
from bokeh.plotting import figure

import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.tab_object as tabObjects
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.utils_f as utils


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
    p = figure(tools="pan,wheel_zoom,box_zoom,reset,save",
               toolbar_location="above",
               plot_width=1120,
               plot_height=500,
               x_range=utils.time_delta(Time(end)),
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date', y_axis_label='Voltage (V)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "Ref Voltages"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "FWA_MOTOR_VREF", "INRSH_FWA_MOTOR_VREF", start, end, conn, color="green")
    b = pf.add_to_plot(p, "GWA_MOTOR_VREF", "INRSH_GWA_MOTOR_VREF", start, end, conn, color="blue")
    c = pf.add_to_plot(p, "OA_VREF", "INRSH_OA_VREF", start, end, conn, color="red")

    pf.add_hover_tool(p, [a, b, c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"
    return p


def gain_volt(conn, start, end):
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
    p = figure(tools="pan,wheel_zoom,box_zoom,reset,save",
               toolbar_location="above",
               plot_width=1120,
               plot_height=500,
               x_range=utils.time_delta(Time(end)),
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date', y_axis_label='Voltage (V)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "ADCMAIN"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "FWA_ADCMGAIN", "INRSH_FWA_ADCMGAIN", start, end, conn, color="green")
    b = pf.add_to_plot(p, "GWA_ADCMGAIN", "INRSH_GWA_ADCMGAIN", start, end, conn, color="blue")
    c = pf.add_to_plot(p, "RMA_ADCMGAIN", "INRSH_RMA_ADCMGAIN", start, end, conn, color="red")

    # pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"
    return p


def offset_volt(conn, start, end):
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
    p = figure(tools="pan,wheel_zoom,box_zoom,reset,save",
               toolbar_location="above",
               plot_width=1120,
               plot_height=500,
               x_range=utils.time_delta(Time(end)),
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date', y_axis_label='Voltage (V)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "OFFSET"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "GWA_ADCMOFFSET", "INRSH_GWA_ADCMOFFSET", start, end, conn, color="blue")
    b = pf.add_to_plot(p, "FWA_ADCMOFFSET", "INRSH_FWA_ADCMOFFSET", start, end, conn, color="green")
    c = pf.add_to_plot(p, "OA_VREFOFF", "INRSH_OA_VREFOFF", start, end, conn, color="orange")
    d = pf.add_to_plot(p, "RMA_ADCMOFFSET", "INRSH_RMA_ADCMOFFSET", start, end, conn, color="red")

    pf.add_hover_tool(p, [a, b, c, d])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

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

    descr = tabObjects.generate_tab_description(utils.description_volt)


    plot1 = ref_volt(conn, start, end)
    plot2 = gain_volt(conn, start, end)
    plot3 = offset_volt(conn, start, end)
    data_table = tabObjects.anomaly_table(conn, utils.list_voltage)

    layout = Column(descr, plot1, plot2, plot3, data_table)

    tab = Panel(child=layout, title="REF VOLTAGES")

    return tab
