#! /usr/bin/env python
"""Prepares plots for WHEEL tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - Filterwheel
    INRSI_FWA_MECH_POS
    INRSI_C_FWA_POSITION

    Plot 2 - Gratingwheel X
    INRSI_GWA_MECH_POS
    INRSI_C_GWA_X_POSITION

    Plot 3 - Gratingwheel Y
    INRSI_GWA_MECH_POS
    INRSI_C_GWA_Y_POSITION

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
    User must provide database "nirspec_database.db"

"""

import copy

from astropy.time import Time
from bokeh.layouts import column
from bokeh.models.widgets import Panel
from bokeh.plotting import figure

import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.tab_object as tabObjects
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.utils_f as utils


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
    p = figure(tools="pan,wheel_zoom,box_zoom,reset,save", \
               toolbar_location="above", \
               plot_width=1120, \
               plot_height=500, \
               x_range=utils.time_delta(Time(end)),\
               y_range=[-3, 3], \
               x_axis_type='datetime', \
               x_axis_label='Date', y_axis_label='mV (normalized)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "Filterwheel"
    p.title.align = "left"
    pf.add_basic_layout(p)

    a=pf.add_to_plot_normalized(p, "F110W", "INRSI_C_FWA_POSITION_F110W", start, end, conn, mn.fw_nominals['F110W'],
                              color="green")
    b=pf.add_to_plot_normalized(p, "F100LP", "INRSI_C_FWA_POSITION_F100LP", start, end, conn, mn.fw_nominals['F100LP'],
                              color="red")
    c=pf.add_to_plot_normalized(p, "F140X", "INRSI_C_FWA_POSITION_F140X", start, end, conn, mn.fw_nominals['F140X'],
                              color="blue")
    d=pf.add_to_plot_normalized(p, "OPAQUE", "INRSI_C_FWA_POSITION_OPAQUE", start, end, conn, mn.fw_nominals['OPAQUE'],
                              color="orange")
    e=pf.add_to_plot_normalized(p, "F290LP", "INRSI_C_FWA_POSITION_F290LP", start, end, conn, mn.fw_nominals['F290LP'],
                              color="purple")
    f=pf.add_to_plot_normalized(p, "F170LP", "INRSI_C_FWA_POSITION_F170LP", start, end, conn, mn.fw_nominals['F170LP'],
                              color="brown")
    g=pf.add_to_plot_normalized(p, "CLEAR", "INRSI_C_FWA_POSITION_CLEAR", start, end, conn, mn.fw_nominals['CLEAR'],
                              color="chocolate")
    h=pf.add_to_plot_normalized(p, "F070LP", "INRSI_C_FWA_POSITION_F070LP", start, end, conn, mn.fw_nominals['F070LP'],
                              color="darkmagenta")

    pf.add_hover_tool_weel(p, [a,b,c,d,e,f,g,h])


    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = 'horizontal'
    return p


def gwx(conn, start, end):
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
    p = figure(tools="pan,wheel_zoom,box_zoom,reset,save", \
               toolbar_location="above", \
               plot_width=1120, \
               plot_height=500, \
               x_range=utils.time_delta(Time(end)),\
               y_range=[-4, 4], \
               x_axis_type='datetime', \
               x_axis_label='Date', y_axis_label='mV (normalized)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "Gratingwheel X"
    p.title.align = "left"
    pf.add_basic_layout(p)

    a=pf.add_to_plot_normalized(p, "PRISM", "INRSI_C_GWA_X_POSITION_PRISM", start, end, conn, mn.gwx_nominals['PRISM'],
                              color="green")
    b=pf.add_to_plot_normalized(p, "MIRROR", "INRSI_C_GWA_X_POSITION_MIRROR", start, end, conn, mn.gwx_nominals['MIRROR'],
                              color="blue")
    c=pf.add_to_plot_normalized(p, "G140H", "INRSI_C_GWA_X_POSITION_G140H", start, end, conn, mn.gwx_nominals['G140H'],
                              color="red")
    d=pf.add_to_plot_normalized(p, "G235H", "INRSI_C_GWA_X_POSITION_G235H", start, end, conn, mn.gwx_nominals['G235H'],
                              color="purple")
    e=pf.add_to_plot_normalized(p, "G395H", "INRSI_C_GWA_X_POSITION_G395H", start, end, conn, mn.gwx_nominals['G395H'],
                              color="orange")
    f=pf.add_to_plot_normalized(p, "G140M", "INRSI_C_GWA_X_POSITION_G140M", start, end, conn, mn.gwx_nominals['G140M'],
                              color="brown")
    g=pf.add_to_plot_normalized(p, "G235M", "INRSI_C_GWA_X_POSITION_G235M", start, end, conn, mn.gwx_nominals['G235M'],
                              color="darkmagenta")
    h=pf.add_to_plot_normalized(p, "G395M", "INRSI_C_GWA_X_POSITION_G395M", start, end, conn, mn.gwx_nominals['G395M'],
                              color="darkcyan")

    pf.add_hover_tool_weel(p, [a,b,c,d,e,f,g,h])


    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = 'horizontal'

    return p


def gwy(conn, start, end):
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
    p = figure(tools="pan,wheel_zoom,box_zoom,reset,save", \
               toolbar_location="above", \
               plot_width=1120, \
               plot_height=500, \
               x_range=utils.time_delta(Time(end)),\
               y_range=[-3, 3], \
               x_axis_type='datetime', \
               x_axis_label='Date', y_axis_label='mV (normalized)')

    p.xaxis.formatter = copy.copy(utils.plot_x_axis_format)

    p.grid.visible = True
    p.title.text = "Gratingwheel Y"
    p.title.align = "left"
    pf.add_basic_layout(p)

    a=pf.add_to_plot_normalized(p, "PRISM", "INRSI_C_GWA_Y_POSITION_PRISM", start, end, conn, mn.gwy_nominals['PRISM'],
                              color="green")
    b=pf.add_to_plot_normalized(p, "MIRROR", "INRSI_C_GWA_Y_POSITION_MIRROR", start, end, conn, mn.gwy_nominals['MIRROR'],
                              color="blue")
    c=pf.add_to_plot_normalized(p, "G140H", "INRSI_C_GWA_Y_POSITION_G140H", start, end, conn, mn.gwy_nominals['G140H'],
                              color="red")
    d=pf.add_to_plot_normalized(p, "G235H", "INRSI_C_GWA_Y_POSITION_G235H", start, end, conn, mn.gwy_nominals['G235H'],
                              color="purple")
    e=pf.add_to_plot_normalized(p, "G395H", "INRSI_C_GWA_Y_POSITION_G395H", start, end, conn, mn.gwy_nominals['G395H'],
                              color="orange")
    f=pf.add_to_plot_normalized(p, "G140M", "INRSI_C_GWA_Y_POSITION_G140M", start, end, conn, mn.gwy_nominals['G140M'],
                              color="brown")
    g=pf.add_to_plot_normalized(p, "G235M", "INRSI_C_GWA_Y_POSITION_G235M", start, end, conn, mn.gwy_nominals['G235M'],
                              color="darkmagenta")
    h=pf.add_to_plot_normalized(p, "G395M", "INRSI_C_GWA_Y_POSITION_G395M", start, end, conn, mn.gwy_nominals['G395M'],
                              color="darkcyan")

    pf.add_hover_tool_weel(p, [a,b,c,d,e,f,g,h])


    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = 'horizontal'
    return p


def wheel_pos(conn, start, end):
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

    descr = tabObjects.generate_tab_description(utils.description_wheel)


    plot1 = fw(conn, start, end)
    plot2 = gwx(conn, start, end)
    plot3 = gwy(conn, start, end)
    data_table = tabObjects.anomaly_table(conn, utils.list_wheel)

    layout = column(descr, plot1, plot2, plot3, data_table)
    tab = Panel(child=layout, title="FILTER/GRATINGWHEEL")

    return tab
