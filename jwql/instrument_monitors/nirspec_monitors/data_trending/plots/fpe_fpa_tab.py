#! /usr/bin/env python
"""Prepares plots for Temperature tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - ASIC 1 Voltages
    IGDP_NRSD_ALG_A1_VDDA
    IGDP_NRSD_ALG_A1GND4VDA
    IGDP_NRSD_ALG_A1GND5VRF
    INRSD_ALG_A1_VDD3P3
    INRSD_ALG_A1_VDD
    INRSD_ALG_A1_REF
    INRSD_A1_DSUB_V
    INRSD_A1_VRESET_V
    INRSD_A1_CELLDRN_V
    INRSD_A1_DRAIN_V
    INRSD_A1_VBIASGATE_V
    INRSD_A1_VBIASPWR_V

    Plot 2 - ASIC 1 Currents
    IGDP_NRSD_ALG_A1_VDD_C
    IGDP_NRSD_ALG_A1VDAP12C
    IGDP_NRSD_ALG_A1VDAN12C
    INRSD_A1_VDDA_I

    Plot 3 - ASIC 2 Voltages
    IGDP_NRSD_ALG_A2_VDDA
    IGDP_NRSD_ALG_A2GND4VDA
    IGDP_NRSD_ALG_A2GND5VRF
    INRSD_ALG_A2_VDD3P3
    INRSD_ALG_A2_VDD
    INRSD_ALG_A2_REF
    INRSD_A2_DSUB_V
    INRSD_A2_VRESET_V
    INRSD_A2_CELLDRN_V
    INRSD_A2_DRAIN_V
    INRSD_A2_VBIASGATE_V
    INRSD_A2_VBIASPWR_V

    Plot 4 - ASIC 2 Currents
    IGDP_NRSD_ALG_A2_VDD_C
    IGDP_NRSD_ALG_A2VDAP12C
    IGDP_NRSD_ALG_A2VDAN12C
    INRSD_A2_VDDA_I

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``nirspec_dashboard.py``, e.g.:

    ::
        from .plots.fpa_fpe_tab import fpa_fpe_plots
        tab = fpa_fpe_plots(conn, start, end)

Dependencies
------------
    User must provide database "nirspec_database.db"

"""
import copy

from astropy.time import Time
from bokeh.layouts import Column, Row
from bokeh.models.widgets import Panel
from bokeh.plotting import figure

import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.tab_object as tabObjects
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.utils_f as utils


def asic_1_voltages(conn, start, end):
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
               plot_height=800,
               x_range=utils.time_delta(Time(end)),
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date', y_axis_label='Voltage (V)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "ASIC 1 Voltages"
    pf.add_basic_layout(p)
    a = pf.add_to_plot(p, "VDDA", "IGDP_NRSD_ALG_A1_VDDA", start, end, conn, color="burlywood")
    b = pf.add_to_plot(p, "A1GND4VDA", "IGDP_NRSD_ALG_A1GND4VDA", start, end, conn, color="cadetblue")
    c = pf.add_to_plot(p, "A1GND5VRF", "IGDP_NRSD_ALG_A1GND5VRF", start, end, conn, color="chartreuse")
    d = pf.add_to_plot(p, "A1VDD3P3", "INRSD_ALG_A1_VDD3P3", start, end, conn, color="chocolate")
    e = pf.add_to_plot(p, "VDD", "INRSD_ALG_A1_VDD", start, end, conn, color="coral")
    f = pf.add_to_plot(p, "REF", "INRSD_ALG_A1_REF", start, end, conn, color="darkorange")
    g = pf.add_to_plot(p, "DSUB_V", "INRSD_A1_DSUB_V", start, end, conn, color="crimson")
    h = pf.add_to_plot(p, "VRESET_V", "INRSD_A1_VRESET_V", start, end, conn, color="cyan")
    i = pf.add_to_plot(p, "CELLDRN_V", "INRSD_A1_CELLDRN_V", start, end, conn, color="darkblue")
    j = pf.add_to_plot(p, "DRAIN_V", "INRSD_A1_DRAIN_V", start, end, conn, color="darkgreen")
    k = pf.add_to_plot(p, "VBIASGATE_V", "INRSD_A1_VBIASGATE_V", start, end, conn, color="darkmagenta")
    l = pf.add_to_plot(p, "VBIASPWR_V", "INRSD_A1_VBIASPWR_V", start, end, conn, color="cornflowerblue")
    pf.add_hover_tool(p, [a, b, c, d, e, f, g, h, i, j, k, l])
    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def asic_2_voltages(conn, start, end):
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
               plot_height=800,
               x_range=utils.time_delta(Time(end)),
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date', y_axis_label='Voltage (V)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "ASIC 2 Voltages"
    pf.add_basic_layout(p)
    a = pf.add_to_plot(p, "VDDA", "IGDP_NRSD_ALG_A2_VDDA", start, end, conn, color="burlywood")
    b = pf.add_to_plot(p, "A2GND4VDA", "IGDP_NRSD_ALG_A2GND4VDA", start, end, conn, color="cadetblue")
    c = pf.add_to_plot(p, "A2GND5VRF", "IGDP_NRSD_ALG_A2GND5VRF", start, end, conn, color="chartreuse")
    d = pf.add_to_plot(p, "A2VDD3P3", "INRSD_ALG_A2_VDD3P3", start, end, conn, color="chocolate")
    e = pf.add_to_plot(p, "VDD", "INRSD_ALG_A2_VDD", start, end, conn, color="coral")
    f = pf.add_to_plot(p, "REF", "INRSD_ALG_A2_REF", start, end, conn, color="darkorange")
    g = pf.add_to_plot(p, "DSUB_V", "INRSD_A2_DSUB_V", start, end, conn, color="crimson")
    h = pf.add_to_plot(p, "VRESET_V", "INRSD_A2_VRESET_V", start, end, conn, color="cyan")
    i = pf.add_to_plot(p, "CELLDRN_V", "INRSD_A2_CELLDRN_V", start, end, conn, color="darkblue")
    j = pf.add_to_plot(p, "DRAIN_V", "INRSD_A2_DRAIN_V", start, end, conn, color="darkgreen")
    k = pf.add_to_plot(p, "VBIASGATE_V", "INRSD_A2_VBIASGATE_V", start, end, conn, color="darkmagenta")
    l = pf.add_to_plot(p, "VBIASPWR_V", "INRSD_A2_VBIASPWR_V", start, end, conn, color="cornflowerblue")
    pf.add_hover_tool(p, [a, b, c, d, e, f, g, h, i, j, k, l])
    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def asic_1_currents(conn, start, end):
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
               plot_width=560,
               plot_height=500,
               x_range=utils.time_delta(Time(end)),
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date', y_axis_label='Current (mA)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "ASIC 1 Currents"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "VDD_C", "IGDP_NRSD_ALG_A1_VDD_C", start, end, conn, color="burlywood")
    b = pf.add_to_plot(p, "A1VDAP12C", "IGDP_NRSD_ALG_A1VDAP12C", start, end, conn, color="cadetblue")
    c = pf.add_to_plot(p, "A1VDAN12C", "IGDP_NRSD_ALG_A1VDAN12C", start, end, conn, color="chartreuse")
    d = pf.add_to_plot(p, "VDDA_I", "INRSD_A1_VDDA_I", start, end, conn, color="chocolate")

    pf.add_hover_tool(p, [a, b, c, d])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p


def asic_2_currents(conn, start, end):
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
               plot_width=560,
               plot_height=500,
               x_range=utils.time_delta(Time(end)),
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date', y_axis_label='Current (mA)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "ASIC 2 Currents"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "VDD_C", "IGDP_NRSD_ALG_A2_VDD_C", start, end, conn, color="burlywood")
    b = pf.add_to_plot(p, "A2VDAP12C", "IGDP_NRSD_ALG_A2VDAP12C", start, end, conn, color="cadetblue")
    c = pf.add_to_plot(p, "A2VDAN12C", "IGDP_NRSD_ALG_A2VDAN12C", start, end, conn, color="chartreuse")
    d = pf.add_to_plot(p, "VDDA_I", "INRSD_A2_VDDA_I", start, end, conn, color="chocolate")

    pf.add_hover_tool(p, [a, b, c, d])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"
    return p


def fpe_fpa_plots(conn, start, end):
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

    descr = tabObjects.generate_tab_description(utils.description_fpe_fpa)


    plot1 = asic_1_voltages(conn, start, end)
    plot2 = asic_2_voltages(conn, start, end)
    plot3 = asic_1_currents(conn, start, end)
    plot4 = asic_2_currents(conn, start, end)
    data_table = tabObjects.anomaly_table(conn, utils.list_fpe_fpa)

    currents = Row(plot3, plot4)
    layout = Column(descr, plot1, plot2, currents, data_table)

    tab = Panel(child=layout, title="FPE/FPA")

    return tab
