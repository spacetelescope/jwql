#! /usr/bin/env python
"""Prepares plots for POWER tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - ICE Power Data
    GP_ZPSVOLT
    SE_ZINRSICEA / SE_ZINRSICEB
    INRSH_HK_P15V
    INRSH_HK_N15V
    INRSH_HK_VMOTOR
    INRSH_HK_P5V
    INRSH_HK_2P5V
    INRSH_HK_ADCTGAIN
    INRSH_HK_ADCTOFFSET
    INRSH_OA_VREFOFF
    INRSH_OA_VREF

    Plot 2 - MCE Power Data
    GP_ZPSVOLT
    SE_ZINRSMCEA / SE_ZINRSMCEB

    Plot 3 - FPE Power Data
    GP_ZPSVOLT
    SE_ZINRSFPEA / SE_ZINRSFPEB
    INRSD_ALG_ACC_P12C
    INRSD_ALG_ACC_N12C
    INRSD_ALG_ACC_3D3_1D5_C
    INRSD_ALG_CHASSIS

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``nirspec_dashboard.py``, e.g.:

    ::
        from .plots.power_tab import power_plots
        tab = power_plots(conn, start, end)

Dependencies
------------
    User must provide database "miri_database.db"

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


def ice_power(conn, start, end):
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
                plot_height = 700,
                x_axis_type = 'datetime',
                y_range = [-20, 20],
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "ICE Power Parameters"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start = 0, end=0.8)}
    #a = pf.add_to_plot(p, "In_VOlt", "GP_ZPSVOLT", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "ICE A current", "SE_ZINRSICEA", start, end, conn, color = "blue", y_axis="current")
    c = pf.add_to_plot(p, "P15V", "INRSH_HK_P15V", start, end, conn, color = "red")
    d = pf.add_to_plot(p, "N15V", "INRSH_HK_N15V", start, end, conn, color = "orange")
    e = pf.add_to_plot(p, "VMOTOR", "INRSH_HK_VMOTOR", start, end, conn, color = "burlywood")
    f = pf.add_to_plot(p, "P5V", "INRSH_HK_P5V", start, end, conn, color = "green")
    g = pf.add_to_plot(p, "2P5V", "INRSH_HK_2P5V", start, end, conn, color = "darkgreen")
    h = pf.add_to_plot(p, "ADCTGAIN", "INRSH_HK_ADCTGAIN", start, end, conn, color = "brown")
    i = pf.add_to_plot(p, "ADCOFFSET", "INRSH_HK_ADCTOFFSET", start, end, conn, color = "navy")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (A)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[b,c,d,e,g,f,h,i])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def mce_power(conn, start, end):
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
                plot_height = 400,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Current (A)')

    p.grid.visible = True
    p.title.text = "MCE Power Parameters"
    pf.add_basic_layout(p)

    b = pf.add_to_plot(p, "MCE A current", "SE_ZINRSMCEA", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def fpe_power(conn, start, end):
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
                plot_height = 700,
                y_range = [-30,280],
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Power Parameters"
    pf.add_basic_layout(p)


    p.extra_y_ranges = {"current": Range1d(start = 0, end=0.8)}
    #a = pf.add_to_plot(p, "In_VOlt", "GP_ZPSVOLT", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "FPE A current", "SE_ZINRSFPEA", start, end, conn, color = "blue", y_axis="current")
    c = pf.add_to_plot(p, "P12C", "INRSD_ALG_ACC_P12C", start, end, conn, color = "red")
    d = pf.add_to_plot(p, "N15V", "INRSH_HK_N15V", start, end, conn, color = "orange")
    e = pf.add_to_plot(p, "N12C", "INRSD_ALG_ACC_N12C", start, end, conn, color = "burlywood")
    f = pf.add_to_plot(p, "1D5", "INRSD_ALG_ACC_3D3_1D5_C", start, end, conn, color = "green")
    g = pf.add_to_plot(p, "Chassis", "INRSD_ALG_CHASSIS", start, end, conn, color = "purple")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (A)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[b,c,d,e,f,g])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p



def power_plots(conn, start, end):
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
        <td>ICE Power Parameters</td>
        <td>GP_ZPSVOLT (missing)<br>
            SE_ZINRSICEA<br>
            INRSH_HK_P15V<br>
            INRSH_HK_N15V<br>
            INRSH_HK_VMOTOR<br>
            INRSH_HK_P5V<br>
            INRSH_HK_2P5V<br>
            INRSH_HK_ADCTGAIN<br>
            INRSH_HK_ADCTOFFSET<br>
            INRSH_OA_VREFOFF<br>
            INRSH_OA_VREF<br>
        </td>
        <td>ICE Input Voltage<br>
            ICE Input Current (A side)<br>
            ICE +15V Voltage<br>
            ICE -15V Voltage<br>
            ICE Motor Voltage<br>
            ICE +5V FPGA Voltage<br>
            ICE +2V5 FPGA Voltage<br>
            ICE ADC TM Chain Gain for Calibration<br>
            ICE ADC TM Chain Offset for Calibration<br>
        </td>
      </tr>

      <tr>
        <td>MCE Power Parameters</td>
        <td>GP_ZPSVOLT (missing)<br>
            SE_ZINRSMCEA
        </td>
        <td>ICE Input Voltage<br>
            MCE Input Current (A side)<br>
        </td>
      </tr>

      <tr>
        <td>FPE Power Parameters</td>
        <td>GP_ZPSVOLT (missing)<br>
            SE_ZINRSFPEA<br>
            INRSD_ALG_ACC_P12C<br>
            INRSD_ALG_ACC_N12C<br>
            INRSD_ALG_ACC_3D3_1D5_C<br>
            INRSD_ALG_CHASSIS<br>
        </td>
        <td>ICE Input Voltage<br>
            MCE Input Current (A side)<br>
            ACC +12V Current<br>
            ACC -12V Current<br>
            ACC 3.3/1.5 Supply Current<br>
            Chassis Voltage<br>
        </td>
      </tr>

    </table>
    </body>
    """, width=1100)

    plot1 = ice_power(conn, start, end)
    plot2 = mce_power(conn, start, end)
    plot3 = fpe_power(conn, start, end)

    layout = Column(descr, plot1, plot2, plot3)

    tab = Panel(child = layout, title = "POWER")

    return tab
