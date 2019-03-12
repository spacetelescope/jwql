#! /usr/bin/env python
"""Prepares plots for Temperature tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - MCE Board 1 (AIC) Voltages and Currents
    INRSM_MCE_AIC_1R5_V
    INRSM_MCE_AIC_3R3_V
    INRSM_MCE_AIC_5_V
    INRSM_MCE_AIC_P12_V
    INRSM_MCE_AIC_N12_V
    INRSM_MCE_AIC_3R3_I
    INRSM_MCE_AIC_5_I
    INRSM_MCE_AIC_P12_I
    INRSM_MCE_AIC_N12_I

    Plot 2 - MCE Board 2 (MDAC) Voltages and Currents
    INRSM_MCE_MDAC_1R5_V
    INRSM_MCE_MDAC_3R3_V
    INRSM_MCE_MDAC_5_V
    INRSM_MCE_MDAC_P12_V
    INRSM_MCE_MDAC_N12_V
    INRSM_MCE_MDAC_3R3_I
    INRSM_MCE_MDAC_5_I
    INRSM_MCE_MDAC_P12_I
    INRSM_MCE_MDAC_N12_I

    Plot 3 - QUAD 1
    INRSM_MSA_Q1_365VDD
    INRSM_MSA_Q1_365VPP
    INRSM_MSA_Q1_171VPP
    IGDPM_MSA_Q1_365IDD
    IGDPM_MSA_Q1_365IPP
    IGDPM_MSA_Q1_171RTN

    Plot 4 - QUAD 2
    INRSM_MSA_Q2_365VDD
    INRSM_MSA_Q2_365VPP
    INRSM_MSA_Q2_171VPP
    IGDPM_MSA_Q2_365IDD
    IGDPM_MSA_Q2_365IPP
    IGDPM_MSA_Q2_171RTN

    Plot 5 - QUAD 3
    INRSM_MSA_Q3_365VDD
    INRSM_MSA_Q3_365VPP
    INRSM_MSA_Q3_171VPP
    IGDPM_MSA_Q3_365IDD
    IGDPM_MSA_Q3_365IPP
    IGDPM_MSA_Q3_171RTN

    Plot 6 - QUAD 4
    INRSM_MSA_Q4_365VDD
    INRSM_MSA_Q4_365VPP
    INRSM_MSA_Q4_171VPP
    IGDPM_MSA_Q4_365IDD
    IGDPM_MSA_Q4_365IPP
    IGDPM_MSA_Q4_171RTN

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
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.layouts import WidgetBox, gridplot, Column

import pandas as pd
import numpy as np

from astropy.time import Time


def aic_parameters(conn, start, end):
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
                plot_width = 1020,
                plot_height = 500,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "MCE Board 1 (AIC)"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=0, end=2500)}
    a = pf.add_to_plot(p, "1R5_V", "INRSM_MCE_AIC_1R5_V", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "3R3_V", "INRSM_MCE_AIC_3R3_V", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "5_V", "INRSM_MCE_AIC_5_V", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "P12_V", "INRSM_MCE_AIC_P12_V", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "N12_V", "INRSM_MCE_AIC_N12_V", start, end, conn, color = "darkmagenta")
    f = pf.add_to_plot(p, "3R3_I", "INRSM_MCE_AIC_3R3_I", start, end, conn, y_axis = "current", color = "blue")
    f = pf.add_to_plot(p, "5_I", "INRSM_MCE_AIC_3R3_I", start, end, conn, y_axis = "current", color = "cyan")
    g = pf.add_to_plot(p, "P12_I", "INRSM_MCE_AIC_P12_I", start, end, conn, y_axis = "current", color = "green")
    h = pf.add_to_plot(p, "N12_I", "INRSM_MCE_AIC_N12_I", start, end, conn, y_axis = "current", color = "darkgreen")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def mdac_parameters(conn, start, end):
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
                plot_width = 1020,
                plot_height = 500,
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "MCE Board 2 (MDAC)"
    pf.add_basic_layout(p)

    p.extra_y_ranges = {"current": Range1d(start=0, end=2500)}
    a = pf.add_to_plot(p, "1R5_V", "INRSM_MCE_MDAC_1R5_V", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "3R3_V", "INRSM_MCE_MDAC_3R3_V", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "5_V", "INRSM_MCE_MDAC_5_V", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "P12_V", "INRSM_MCE_MDAC_P12_V", start, end, conn, color = "burlywood")
    e = pf.add_to_plot(p, "N12_V", "INRSM_MCE_MDAC_N12_V", start, end, conn, color = "darkmagenta")
    f = pf.add_to_plot(p, "3R3_I", "INRSM_MCE_MDAC_3R3_I", start, end, conn, y_axis = "current", color = "blue")
    f = pf.add_to_plot(p, "5_I", "INRSM_MCE_MDAC_3R3_I", start, end, conn, y_axis = "current", color = "cyan")
    g = pf.add_to_plot(p, "P12_I", "INRSM_MCE_MDAC_P12_I", start, end, conn, y_axis = "current", color = "green")
    h = pf.add_to_plot(p, "N12_I", "INRSM_MCE_MDAC_N12_I", start, end, conn, y_axis = "current", color = "darkgreen")
    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h])

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

    plot1 = aic_parameters(conn, start, end)
    plot2 = mdac_parameters(conn, start, end)
    plot3 = quad1_volt(conn, start, end)
    plot4 = quad2_volt(conn, start, end)
    plot5 = quad3_volt(conn, start, end)
    plot6 = quad4_volt(conn, start, end)

    grid = gridplot([[plot3, plot4], [plot5, plot6]],merge_tools=False)
    layout = Column(descr, plot1, plot2, grid)

    tab = Panel(child = layout, title = "MSA/MCE")

    return tab
