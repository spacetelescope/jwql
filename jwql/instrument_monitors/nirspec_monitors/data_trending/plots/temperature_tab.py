#! /usr/bin/env python
"""Prepares plots for Temperature tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1 - IRSU monitored temps
    SI_GZCTS75A / SI_GZCTS75B
    SI_GZCTS68A / SI_GZCTS68B
    SI_GZCTS81A / SI_GZCTS81B
    SI_GZCTS80A / SI_GZCTS80B
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

    plot1 = ice_power(conn, start, end)
    plot2 = mce_power(conn, start, end)
    plot3 = fpe_power(conn, start, end)

    layout = Column(descr, plot1, plot2, plot3)

    tab = Panel(child = layout, title = "POWER")

    return tab
