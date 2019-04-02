#! /usr/bin/env python
"""Prepares plots for Temperature tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - IRSU monitored temps
    SI_GZCTS75A / SI_GZCTS75B
    SI_GZCTS68A / SI_GZCTS68B
    SI_GZCTS81A / SI_GZCTS81B
    SI_GZCTS80A / SI_GZCTS80B
    SI_GZCTS76A / SI_GZCTS76B
    SI_GZCTS79A / SI_GZCTS79B
    SI_GZCTS77A / SI_GZCTS77B
    SI_GZCTS78A / SI_GZCTS78B
    SI_GZCTS69A / SI_GZCTS69B

    Plot 2 - Box Temps
    IGDP_NRSD_ALG_TEMP
    INRSH_HK_TEMP1
    INRSH_HK_TEMP2

    Plot 3 - FPE Power Data
    IGDP_NRSI_C_CAM_TEMP
    IGDP_NRSI_C_COL_TEMP
    IGDP_NRSI_C_COM1_TEMP
    IGDP_NRSI_C_FOR_TEMP
    IGDP_NRSI_C_IFU_TEMP
    IGDP_NRSI_C_BP1_TEMP
    IGDP_NRSI_C_BP2_TEMP
    IGDP_NRSI_C_BP3_TEMP
    IGDP_NRSI_C_BP4_TEMP
    IGDP_NRSI_C_RMA_TEMP
    IGDP_NRSI_C_CAAL1_TEMP
    IGDP_NRSI_C_CAAL2_TEMP
    IGDP_NRSI_C_CAAL3_TEMP
    IGDP_NRSI_C_CAAL4_TEMP
    IGDP_NRSI_C_FWA_TEMP
    IGDP_NRSI_C_GWA_TEMP

    Plot 4 - MCE internal Temp
    INRSM_MCE_PCA_TMP1
    INRSM_MCE_PCA_TMP2
    INRSM_MCE_AIC_TMP_FPGA
    INRSM_MCE_AIC_TMP_ADC
    INRSM_MCE_AIC_TMP_VREG
    INRSM_MCE_MDAC_TMP_FPGA
    INRSM_MCE_MDAC_TMP_OSC
    INRSM_MCE_MDAC_TMP_BRD
    INRSM_MCE_MDAC_TMP_PHA
    INRSM_MCE_MDAC_TMP_PHB

    Plot 5 - MSA Temp
    INRSM_Q1_TMP_A
    INRSM_Q2_TMP_A
    INRSM_Q3_TMP_A
    INRSM_Q4_TMP_A
    INRSM_MECH_MTR_TMP_A
    INRSM_LL_MTR_TMP_A
    INRSM_MSA_TMP_A

    Plot 6 - FPA Temp
    IGDP_NRSD_ALG_FPA_TEMP
    IGDP_NRSD_ALG_A1_TEMP
    IGDP_NRSD_ALG_A2_TEMP

    Plot 7 - Heat Strap Temps (Trim heaters)
    SI_GZCTS74A / SI_GZCTS74B
    SI_GZCTS67A / SI_GZCTS67B

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``nirspec_dashboard.py``, e.g.:

    ::
        from .plots.temperature_tab import temperature_plots
        tab = temperature_plots(conn, start, end)

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


def irsu_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "IRSU monitored Temperatures"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "75A", "SI_GZCTS75A", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "68A", "SI_GZCTS68A", start, end, conn, color = "green")
    c = pf.add_to_plot(p, "81A", "SI_GZCTS81A", start, end, conn, color = "blue")
    d = pf.add_to_plot(p, "80A", "SI_GZCTS80A", start, end, conn, color = "orange")
    e = pf.add_to_plot(p, "76A", "SI_GZCTS76A", start, end, conn, color = "brown")
    f = pf.add_to_plot(p, "79A", "SI_GZCTS79A", start, end, conn, color = "cyan")
    g = pf.add_to_plot(p, "77A", "SI_GZCTS77A", start, end, conn, color = "darkmagenta")
    h = pf.add_to_plot(p, "78A", "SI_GZCTS78A ", start, end, conn, color = "burlywood")
    i = pf.add_to_plot(p, "69A", "SI_GZCTS69A ", start, end, conn, color = "chocolate")

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h,i])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def fpe_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "FPE Temperatures"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "CAM", "IGDP_NRSI_C_CAM_TEMP", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "COL", "IGDP_NRSI_C_COL_TEMP", start, end, conn, color = "green")
    c = pf.add_to_plot(p, "COM1", "IGDP_NRSI_C_COM1_TEMP", start, end, conn, color = "blue")
    d = pf.add_to_plot(p, "FOR", "IGDP_NRSI_C_FOR_TEMP", start, end, conn, color = "darkorange")
    e = pf.add_to_plot(p, "IFU", "IGDP_NRSI_C_IFU_TEMP", start, end, conn, color = "cyan")
    f = pf.add_to_plot(p, "BP1", "IGDP_NRSI_C_BP1_TEMP", start, end, conn, color = "darkmagenta")
    g = pf.add_to_plot(p, "BP2", "IGDP_NRSI_C_BP2_TEMP", start, end, conn, color = "burlywood")
    h = pf.add_to_plot(p, "BP3", "IGDP_NRSI_C_BP3_TEMP", start, end, conn, color = "brown")
    i = pf.add_to_plot(p, "BP4", "IGDP_NRSI_C_BP4_TEMP", start, end, conn, color = "chocolate")
    j = pf.add_to_plot(p, "RMA", "IGDP_NRSI_C_RMA_TEMP", start, end, conn, color = "darkgreen")

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h,i,j])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def caal_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "CAA Lamps / FWA, GWA"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "CAAL1", "IGDP_NRSI_C_CAAL1_TEMP", start, end, conn, color = "darkblue")
    b = pf.add_to_plot(p, "CAAL2", "IGDP_NRSI_C_CAAL2_TEMP", start, end, conn, color = "magenta")
    c = pf.add_to_plot(p, "CAAL3", "IGDP_NRSI_C_CAAL3_TEMP", start, end, conn, color = "mediumaquamarine")
    d = pf.add_to_plot(p, "CAAL4", "IGDP_NRSI_C_CAAL4_TEMP", start, end, conn, color = "goldenrod")
    e = pf.add_to_plot(p, "FWA", "IGDP_NRSI_C_FWA_TEMP", start, end, conn, color = "darkseagreen")
    f = pf.add_to_plot(p, "GWA", "IGDP_NRSI_C_GWA_TEMP", start, end, conn, color = "darkkhaki")

    pf.add_hover_tool(p,[a,b,c,d,e,f])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def box_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "Box Temperatures"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "ALG_TEMP", "IGDP_NRSD_ALG_TEMP", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "HK_TEMP1", "INRSH_HK_TEMP1", start, end, conn, color = "green")
    c = pf.add_to_plot(p, "HK_TEMP2", "INRSH_HK_TEMP2", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def mce_internal_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "MCE internal Temperatures"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "PCA_TMP1", "INRSM_MCE_PCA_TMP1", start, end, conn, color = "green")
    b = pf.add_to_plot(p, "PCA_TMP2", "INRSM_MCE_PCA_TMP2", start, end, conn, color = "blue")
    c = pf.add_to_plot(p, "FPGA_AIC", "INRSM_MCE_AIC_TMP_FPGA", start, end, conn, color = "brown")
    d = pf.add_to_plot(p, "ADC_AIC", "INRSM_MCE_AIC_TMP_ADC", start, end, conn, color = "red")
    e = pf.add_to_plot(p, "VREG_AIC", "INRSM_MCE_AIC_TMP_VREG", start, end, conn, color = "hotpink")
    f = pf.add_to_plot(p, "FPGA_MDAC", "INRSM_MCE_MDAC_TMP_FPGA", start, end, conn, color = "cadetblue")
    g = pf.add_to_plot(p, "OSC_MDAC", "INRSM_MCE_MDAC_TMP_OSC", start, end, conn, color = "navy")
    h = pf.add_to_plot(p, "BRD_MDAC", "INRSM_MCE_MDAC_TMP_BRD", start, end, conn, color = "darkgreen")
    i = pf.add_to_plot(p, "PHA_MDAC", "INRSM_MCE_MDAC_TMP_PHA", start, end, conn, color = "magenta")
    j = pf.add_to_plot(p, "PHB_MDAC", "INRSM_MCE_MDAC_TMP_PHB", start, end, conn, color = "orange")

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h,i,j])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def msa_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "MSA Temperatures"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "Q1_TEMP", "INRSM_Q1_TMP_A", start, end, conn, color = "green")
    b = pf.add_to_plot(p, "Q2_TEMP", "INRSM_Q2_TMP_A", start, end, conn, color = "red")
    c = pf.add_to_plot(p, "Q3_TEMP", "INRSM_Q3_TMP_A", start, end, conn, color = "blue")
    d = pf.add_to_plot(p, "Q4_TEMP", "INRSM_Q4_TMP_A", start, end, conn, color = "brown")
    e = pf.add_to_plot(p, "MECH_MTR", "INRSM_MECH_MTR_TMP_A", start, end, conn, color = "orange")
    f = pf.add_to_plot(p, "LL_MTR", "INRSM_LL_MTR_TMP_A", start, end, conn, color = "darkmagenta")
    g = pf.add_to_plot(p, "MSA", "INRSM_MSA_TMP_A", start, end, conn, color = "indigo")

    pf.add_hover_tool(p,[a,b,c,d,e,f,g])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def fpa_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "FPA Temperatures"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "ALG_FPA", "IGDP_NRSD_ALG_FPA_TEMP", start, end, conn, color = "green")
    b = pf.add_to_plot(p, "ALG_A1", "IGDP_NRSD_ALG_A1_TEMP", start, end, conn, color = "red")
    c = pf.add_to_plot(p, "ALG_A2", "IGDP_NRSD_ALG_A2_TEMP", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def heat_strap_temp(conn, start, end):
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
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label='Temperature (K)')

    p.grid.visible = True
    p.title.text = "Heat Strap Temperatures (Trim heaters)"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "74A", "SI_GZCTS74A", start, end, conn, color = "green")
    b = pf.add_to_plot(p, "67A", "SI_GZCTS67A", start, end, conn, color = "red")

    pf.add_hover_tool(p,[a,b])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def temperature_plots(conn, start, end):
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
        <td>IRSU monitored Temperatures</td>
        <td>SI_GZCTS75A<br>
            SI_GZCTS68A<br>
            SI_GZCTS81A<br>
            SI_GZCTS80A<br>
            SI_GZCTS76A<br>
            SI_GZCTS79A<br>
            SI_GZCTS77A<br>
            SI_GZCTS78A<br>
            SI_GZCTS69A</td>
        <td>CAA IRSU Temperature<br>
            CAM IRSU Temperature<br>
            COM1 Nominal IRSU Temperature<br>
            COM1 Redundant IRSU Temperature<br>
            FWA IRSU Temperature<br>
            GWA IRSU Temperature<br>
            Thermal Strap Nominal IRSU Temperature<br>
            Thermal Strap Redundant IRSU Temperature<br>
            MSA Nominal IRSU Temperature<br>
            MSA Redundant IRSU Temperature</td>
      </tr>

      <tr>
        <td>FPE Temperatures/td>
        <td>IGDP_NRSI_C_CAM_TEMP<br>
            IGDP_NRSI_C_COL_TEMP<br>
            IGDP_NRSI_C_COM1_TEMP<br>
            IGDP_NRSI_C_FOR_TEMP<br>
            IGDP_NRSI_C_IFU_TEMP<br>
            IGDP_NRSI_C_BP1_TEMP<br>
            IGDP_NRSI_C_BP2_TEMP<br>
            IGDP_NRSI_C_BP3_TEMP<br>
            IGDP_NRSI_C_BP4_TEMP<br>
            IGDP_NRSI_C_RMA_TEMP</td>
        <td>OA CAM Temperature<br>
            OA COL Temperature<br>
            OA COM1 Temperature<br>
            OA FOR Temperature<br>
            OA IFU Temperature<br>
            OA BP1 Temperature<br>
            OA BP2 Temperature<br>
            OA BP3 Temperature<br>
            OA BP4 Temperature<br>
            OA RMA Temperature</td>
      </tr>

      <tr>
        <td>Box Temperatures</td>
        <td>IGDP_NRSD_ALG_TEMP<br>
            INRSH_HK_TEMP1<br>
            INRSH_HK_TEMP2</td>
        <td>ICE Internal Temperature 1<br>
            ICE Internal Temperature 2</td>
      </tr>

      <tr>
        <td>MCE internal Temperatures</td>
        <td>INRSM_MCE_PCA_TMP1<br>
            INRSM_MCE_PCA_TMP2<br>
            INRSM_MCE_AIC_TMP_FPGA<br>
            INRSM_MCE_AIC_TMP_ADC<br>
            INRSM_MCE_AIC_TMP_VREG<br>
            INRSM_MCE_MDAC_TMP_FPGA<br>
            INRSM_MCE_MDAC_TMP_OSC<br>
            INRSM_MCE_MDAC_TMP_BRD<br>
            INRSM_MCE_MDAC_TMP_PHA<br>
            INRSM_MCE_MDAC_TMP_PHB</td>
        <td>MCE PCA Board Temperature 1<br>
            MCE PCA Board Temperature 2<br>
            MCE AIC Board FPGA Temperature<br>
            MCE AIC Board Analog/Digital Converter Temperature<br>
            MCE AIC Board Voltage Regulator Temperature<br>
            MCE MDAC Board FPGA Temperature<br>
            MCE MDAC Board Oscillator Temperature<br>
            MCE MDAC Board Temperature<br>
            MCE MDAC Board Phase A PA10 Temperature<br>
            MCE MDAC Board Phase B PA10 Temperature</td>
      </tr>

      <tr>
        <td>MSA Temperatures</td>
        <td>INRSM_Q1_TMP_A<br>
            INRSM_Q2_TMP_A<br>
            INRSM_Q3_TMP_A<br>
            INRSM_Q4_TMP_A<br>
            INRSM_MECH_MTR_TMP_A<br>
            INRSM_LL_MTR_TMP_A<br>
            INRSM_MSA_TMP_A</td>
        <td>MSA Quad 1 Temperature<br>
            MSA Quad 2 Temperature<br>
            MSA Quad 3 Temperature<br>
            MSA Quad 4 Temperature<br>
            MSA Magnetic Arm Motor Temperature<br>
            MSA Launch Lock Motor Temperature<br>
            MSA Frame Temperature</td>
      </tr>

      <tr>
        <td>FPA Temperatures</td>
        <td>IGDP_NRSD_ALG_FPA_TEMP<br>
            IGDP_NRSD_ALG_A1_TEMP<br>
            IGDP_NRSD_ALG_A2_TEMP</td>
        <td>FPE Temperature<br>
            FPA Temperature<br>
            ASIC 1 Temperature<br>
            ASIC 2 Temperature</td>
      </tr>

      <tr>
        <td>Heat Strap Temperatures (Trim Heaters)</td>
        <td>SI_GZCTS74A<br>
            SI_GZCTS67A</td>
        <td>FPA TH-Strap A Temperature from IRSU A<br>
            FPA TH-Strap B Temperature from IRSU A</td>
      </tr>

      <tr>
        <td>CAA Lamps / FWA,GWA</td>
        <td>IGDP_NRSI_C_CAAL1_TEMP<br>
            IGDP_NRSI_C_CAAL2_TEMP<br>
            IGDP_NRSI_C_CAAL3_TEMP<br>
            IGDP_NRSI_C_CAAL4_TEMP<br>
            IGDP_NRSI_C_FWA_TEMP<br>
            IGDP_NRSI_C_GWA_TEMP</td>
        <td>CAA Temperature LINE1<br>
            CAA Temperature LINE2<br>
            CAA Temperature LINE3<br>
            CAA Temperature LINE4<br>
            FWA Temperature Sensor Value<br>
            GWA Temperature Sensor Value</td>
      </tr>

    </table>
    </body>
    """, width=1100)

    plot1 = irsu_temp(conn, start, end)
    plot2 = fpe_temp(conn, start, end)
    plot3 = box_temp(conn, start, end)
    plot4 = mce_internal_temp(conn, start, end)
    plot5 = msa_temp(conn, start, end)
    plot6 = fpa_temp(conn, start, end)
    plot7 = heat_strap_temp(conn, start, end)
    plot8 = caal_temp(conn, start, end)

    layout = Column(descr, plot1, plot2, plot3, plot4, plot5, plot6, plot7, plot8)

    tab = Panel(child = layout, title = "TEMPERATURE")

    return tab
