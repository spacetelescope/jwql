#! /usr/bin/env python
"""Prepares plots for Temperature tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - MCE Board 1 (AIC) Voltages
    INRSM_MCE_AIC_1R5_V
    INRSM_MCE_AIC_3R3_V
    INRSM_MCE_AIC_5_V
    INRSM_MCE_AIC_P12_V
    INRSM_MCE_AIC_N12_V

    Plot 2 - MCE Board 1 (AIC) Currents
    INRSM_MCE_AIC_3R3_I
    INRSM_MCE_AIC_5_I
    INRSM_MCE_AIC_P12_I
    INRSM_MCE_AIC_N12_I

    Plot 3 - MCE Board 2 (MDAC) Voltages
    INRSM_MCE_MDAC_1R5_V
    INRSM_MCE_MDAC_3R3_V
    INRSM_MCE_MDAC_5_V
    INRSM_MCE_MDAC_P12_V
    INRSM_MCE_MDAC_N12_V

    Plot 4 - MCE Board 2 (MDAC) Currents
    INRSM_MCE_MDAC_3R3_I
    INRSM_MCE_MDAC_5_I
    INRSM_MCE_MDAC_P12_I
    INRSM_MCE_MDAC_N12_I

    Plot (5-8) - QUAD (1-4)
    INRSM_MSA_Q(1-4)_365VDD
    INRSM_MSA_Q(1-4)_365VPP
    INRSM_MSA_Q(1-4)_171VPP
    IGDPM_MSA_Q(1-4)_365IDD
    IGDPM_MSA_Q(1-4)_365IPP
    IGDPM_MSA_Q(1-4)_171RTN

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``nirspec_dashboard.py``, e.g.:

    ::
        from .plots.msa_mce_tab import msa_mce_plots
        tab = msa_mce_plots(conn, start, end)

Dependencies
------------
    User must provide database "nirspec_database.db"

"""
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.nirspec_monitors.data_trending.plots.plot_functions as pf
from bokeh.models import LinearAxis, Range1d
from bokeh.plotting import figure
from bokeh.models.widgets import Panel, Tabs, Div
from bokeh.models import ColumnDataSource, HoverTool, Title
from bokeh.layouts import WidgetBox, gridplot, Column

import pandas as pd
import numpy as np

from astropy.time import Time


def aic_voltage(conn, start, end):
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
                plot_height = 700,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "MCE Board 1 (AIC)"
    p.add_layout(Title(text="Voltages", text_font_style="italic", text_font_size="12pt"), 'above')
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "1R5_V", "INRSM_MCE_AIC_1R5_V", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "3R3_V", "INRSM_MCE_AIC_3R3_V", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "5_V", "INRSM_MCE_AIC_5_V", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "P12_V", "INRSM_MCE_AIC_P12_V", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "N12_V", "INRSM_MCE_AIC_N12_V", start, end, conn, color = "darkmagenta")

    pf.add_hover_tool(p,[a,b,c,d,e])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def aic_current(conn, start, end):
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
                plot_height = 700,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Current (A)')

    p.grid.visible = True
    p.title.text = "MCE Board 1 (AIC)"
    p.add_layout(Title(text="Currents", text_font_style="italic", text_font_size="12pt"), 'above')
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "3R3_I", "INRSM_MCE_AIC_3R3_I", start, end, conn, color = "blue")
    b = pf.add_to_plot(p, "5_I", "INRSM_MCE_AIC_5_I", start, end, conn, color = "red")
    c = pf.add_to_plot(p, "P12_I", "INRSM_MCE_AIC_P12_I", start, end, conn, color = "green")
    d = pf.add_to_plot(p, "N12_I", "INRSM_MCE_AIC_N12_I", start, end, conn, color = "orange")

    pf.add_hover_tool(p,[a,b,c,d])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def mdac_voltage(conn, start, end):
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
                plot_height = 700,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "MCE Board 2 (MDAC)"
    p.add_layout(Title(text="Voltages", text_font_style="italic", text_font_size="12pt"), 'above')
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "1R5_V", "INRSM_MCE_MDAC_1R5_V", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "3R3_V", "INRSM_MCE_MDAC_3R3_V", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "5_V", "INRSM_MCE_MDAC_5_V", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "P12_V", "INRSM_MCE_MDAC_P12_V", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "N12_V", "INRSM_MCE_MDAC_N12_V", start, end, conn, color = "darkmagenta")

    pf.add_hover_tool(p,[a,b,c,d,e])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def mdac_current(conn, start, end):
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
                plot_height = 700,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "MCE Board 2 (MDAC)"
    p.add_layout(Title(text="Currents", text_font_style="italic", text_font_size="12pt"), 'above')
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "3R3_I", "INRSM_MCE_MDAC_3R3_I", start, end, conn, color = "blue")
    b = pf.add_to_plot(p, "5_I", "INRSM_MCE_MDAC_5_I", start, end, conn, color = "red")
    c = pf.add_to_plot(p, "P12_I", "INRSM_MCE_MDAC_P12_I", start, end, conn, color = "green")
    d = pf.add_to_plot(p, "N12_I", "INRSM_MCE_MDAC_N12_I", start, end, conn, color = "orange")

    pf.add_hover_tool(p,[a,b,c,d])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def quad1_volt(conn, start, end):
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
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Quad 1"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "365VDD", "INRSM_MSA_Q1_365VDD", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "365VPP", "INRSM_MSA_Q1_365VPP", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "171VPP", "INRSM_MSA_Q1_171VPP", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "365IDD", "IGDPM_MSA_Q1_365IDD", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "365IPP", "IGDPM_MSA_Q1_365IPP", start, end, conn, color = "darkmagenta")
    f = pf.add_to_plot(p, "171RTN", "IGDPM_MSA_Q1_171RTN", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b,c,d,e,f])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def quad2_volt(conn, start, end):
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
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Quad 2"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "365VDD", "INRSM_MSA_Q2_365VDD", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "365VPP", "INRSM_MSA_Q2_365VPP", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "171VPP", "INRSM_MSA_Q2_171VPP", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "365IDD", "IGDPM_MSA_Q2_365IDD", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "365IPP", "IGDPM_MSA_Q2_365IPP", start, end, conn, color = "darkmagenta")
    f = pf.add_to_plot(p, "171RTN", "IGDPM_MSA_Q2_171RTN", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b,c,d,e,f])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def quad3_volt(conn, start, end):
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
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Quad 3"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "365VDD", "INRSM_MSA_Q3_365VDD", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "365VPP", "INRSM_MSA_Q3_365VPP", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "171VPP", "INRSM_MSA_Q3_171VPP", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "365IDD", "IGDPM_MSA_Q3_365IDD", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "365IPP", "IGDPM_MSA_Q3_365IPP", start, end, conn, color = "darkmagenta")
    f = pf.add_to_plot(p, "171RTN", "IGDPM_MSA_Q3_171RTN", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b,c,d,e,f])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def quad4_volt(conn, start, end):
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
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Quad 4"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "365VDD", "INRSM_MSA_Q4_365VDD", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "365VPP", "INRSM_MSA_Q4_365VPP", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "171VPP", "INRSM_MSA_Q4_171VPP", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "365IDD", "IGDPM_MSA_Q4_365IDD", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "365IPP", "IGDPM_MSA_Q4_365IPP", start, end, conn, color = "darkmagenta")
    f = pf.add_to_plot(p, "171RTN", "IGDPM_MSA_Q4_171RTN", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b,c,d,e,f])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def msa_mce_plots(conn, start, end):
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
        <td>MCE Board 1 (AIC) Voltages</td>
        <td>INRSM_MCE_AIC_1R5_V<br>
            INRSM_MCE_AIC_3R3_V<br>
            INRSM_MCE_AIC_5_V<br>
            INRSM_MCE_AIC_P12_V<br>
            INRSM_MCE_AIC_N12_V<br>
        </td>
        <td>MCE AIC +1.5V Voltage<br>
            MCE AIC +3.3V Voltage<br>
            MCE AIC +5V Voltage<br>
            MCE AIC +12V Voltage<br>
            MCE AIC -12V Voltage<br>
        </td>
      </tr>

      <tr>
        <td>MCE Board 1 (AIC) Currents</td>
        <td>INRSM_MCE_AIC_3R3_I<br>
            INRSM_MCE_AIC_5_I<br>
            INRSM_MCE_AIC_P12_I<br>
            INRSM_MCE_AIC_N12_I<br>
        </td>
        <td>MCE AIC Board +3.3V Current<br>
            MCE AIC Board +5V Current<br>
            MCE AIC Board +12V Current<br>
            MCE AIC Board -12V Current<br>
        </td>
      </tr>

      <tr>
        <td>MCE Board 2 (MDAC) Voltages</td>
        <td>INRSM_MCE_MDAC_1R5_V<br>
            INRSM_MCE_MDAC_3R3_V<br>
            INRSM_MCE_MDAC_5_V<br>
            INRSM_MCE_MDAC_P12_V<br>
            INRSM_MCE_MDAC_N12_V<br>
        </td>
        <td>MCE MDAC +1.5V Voltage<br>
            MCE MDAC +3.3V Voltage<br>
            MCE MDAC +5V Voltage<br>
            MCE MDAC +12V Voltage<br>
            MCE MDAC -12V Voltage<br>
        </td>
      </tr>

      <tr>
        <td>MCE Board 2 (MDAC) Currents</td>
        <td>INRSM_MCE_MDAC_3R3_I<br>
            INRSM_MCE_MDAC_5_I<br>
            INRSM_MCE_MDAC_P12_I<br>
            INRSM_MCE_MDAC_N12_I<br>
        </td>
        <td>MCE MDAC Board +3.3V Current<br>
            MCE MDAC Board +5V Current<br>
            MCE MDAC Board +12V Current<br>
            MCE MDAC Board -12V Current<br>
        </td>
      </tr>

      <tr>
        <td>QUAD (1-4)</td>
        <td>INRSM_MSA_Q(1-4)_365VDD<br>
            INRSM_MSA_Q(1-4)_365VPP<br>
            INRSM_MSA_Q(1-4)_171VPP<br>
            IGDPM_MSA_Q(1-4)_365IDD<br>
            IGDPM_MSA_Q(1-4)_365IPP<br>
            IGDPM_MSA_Q(1-4)_171RTN<br>
        </td>
        <td>MSA Quad (1-4) Vdd 365 Voltage<br>
            MSA Quad (1-4) Vpp 365 Voltage<br>
            MSA Quad (1-4) Vpp 171 Voltage<br>
            MSA Quad (1-4) Vdd 365 Current<br>
            MSA Quad (1-4) Vpp 365 Current<br>
            MSA Quad (1-4) Return 171 Current<br>
        </td>
      </tr>
    </table>
    </body>
    """, width=1100)

    plot1 = aic_voltage(conn, start, end)
    plot2 = aic_current(conn, start, end)
    plot3 = mdac_voltage(conn, start, end)
    plot4 = mdac_current(conn, start, end)
    plot5 = quad1_volt(conn, start, end)
    plot6 = quad2_volt(conn, start, end)
    plot7 = quad3_volt(conn, start, end)
    plot8 = quad4_volt(conn, start, end)

    grid = gridplot([[plot1, plot2],
                    [plot3, plot4],
                    [plot5, plot6],
                    [plot7, plot8]],merge_tools=False)
    layout = Column(descr, grid)

    tab = Panel(child = layout, title = "MSA/MCE")

    return tab
