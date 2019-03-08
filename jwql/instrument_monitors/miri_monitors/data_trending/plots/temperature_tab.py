#! /usr/bin/env python
"""Prepares plots for TEMPERATURE tab

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1:
    IGDP_MIR_ICE_T1P_CRYO
    IGDP_MIR_ICE_T2R_CRYO
    IGDP_MIR_ICE_T3LW_CRYO
    IGDP_MIR_ICE_T4SW_CRYO
    IGDP_MIR_ICE_T5IMG_CRYO
    IGDP_MIR_ICE_T6DECKCRYO
    IGDP_MIR_ICE_T7IOC_CRYO
    IGDP_MIR_ICE_FW_CRYO
    IGDP_MIR_ICE_CCC_CRYO
    IGDP_MIR_ICE_GW14_CRYO
    IGDP_MIR_ICE_GW23_CRYO
    IGDP_MIR_ICE_POMP_CRYO
    IGDP_MIR_ICE_POMR_CRYO
    IGDP_MIR_ICE_IFU_CRYO
    IGDP_MIR_ICE_IMG_CRYO

    Plot 2:
    ST_ZTC1MIRIA
    ST_ZTC2MIRIA
    IMIR_PDU_TEMP
    IMIR_IC_SCE_ANA_TEMP1
    IMIR_SW_SCE_ANA_TEMP1
    IMIR_LW_SCE_ANA_TEMP1
    IMIR_IC_SCE_DIG_TEMP
    IMIR_SW_SCE_DIG_TEMP
    IMIR_LW_SCE_DIG_TEMP

    Plot 3:
    IGDP_MIR_IC_DET_TEMP
    IGDP_MIR_LW_DET_TEMP
    IGDP_MIR_SW_DET_TEMP

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``dashborad.py``, e.g.:

    ::
        from .plots.temperature_tab import temperature_plots
        tab = temperature_plots(conn, start, end)

Dependencies
------------
    User must provide database "miri_database.db"

"""
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs, Div
from bokeh.models import ColumnDataSource
from bokeh.layouts import column

import pandas as pd
import numpy as np

from astropy.time import Time


def cryo(conn, start, end):
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
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 700,                                  \
                y_range = [5.8,6.4],                                \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label = 'Temperature (K)')

    p.grid.visible = True
    p.title.text = "Cryo Temperatures"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "T1P", "IGDP_MIR_ICE_T1P_CRYO", start, end, conn, color = "brown")
    b = pf.add_to_plot(p, "T2R", "IGDP_MIR_ICE_T2R_CRYO", start, end, conn, color = "burlywood")
    c = pf.add_to_plot(p, "T3LW", "IGDP_MIR_ICE_T3LW_CRYO", start, end, conn, color = "cadetblue")
    d = pf.add_to_plot(p, "T4SW", "IGDP_MIR_ICE_T4SW_CRYO", start, end, conn, color = "chartreuse")
    e = pf.add_to_plot(p, "T5IMG", "IGDP_MIR_ICE_T5IMG_CRYO", start, end, conn, color = "chocolate")
    f = pf.add_to_plot(p, "T6DECK", "IGDP_MIR_ICE_T6DECKCRYO", start, end, conn, color = "coral")
    g = pf.add_to_plot(p, "T7IOC", "IGDP_MIR_ICE_T7IOC_CRYO", start, end, conn, color = "darkorange")
    h = pf.add_to_plot(p, "FW", "IGDP_MIR_ICE_FW_CRYO", start, end, conn, color = "crimson")
    i = pf.add_to_plot(p, "CCC", "IGDP_MIR_ICE_CCC_CRYO", start, end, conn, color = "cyan")
    j = pf.add_to_plot(p, "GW14", "IGDP_MIR_ICE_GW14_CRYO", start, end, conn, color = "darkblue")
    k = pf.add_to_plot(p, "GW23", "IGDP_MIR_ICE_GW23_CRYO", start, end, conn, color = "darkgreen")
    l = pf.add_to_plot(p, "POMP", "IGDP_MIR_ICE_POMP_CRYO", start, end, conn, color = "darkmagenta")
    m = pf.add_to_plot(p, "POMR", "IGDP_MIR_ICE_POMR_CRYO", start, end, conn, color = "darkcyan")
    n = pf.add_to_plot(p, "IFU", "IGDP_MIR_ICE_IFU_CRYO", start, end, conn, color = "cornflowerblue")
    o = pf.add_to_plot(p, "IMG", "IGDP_MIR_ICE_IMG_CRYO", start, end, conn, color = "orange")

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h,i,j,k,l,m,n,o])

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def temp(conn, start, end):
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

    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM IGDP_MIR_ICE_INTER_TEMP WHERE start_time BETWEEN "+start_str+" AND "+end_str+" ORDER BY start_time"
    temp = pd.read_sql_query(sql_c, conn)

    temp['average']+= 273.15
    reg = pd.DataFrame({'reg' : pf.pol_regression(temp['start_time'], temp['average'],3)})
    temp = pd.concat([temp, reg], axis=1)

    temp['start_time'] = pd.to_datetime( Time(temp['start_time'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 700,                                  \
                y_range = [275,295],                             \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label = 'Temperature (K)')

    p.grid.visible = True
    p.title.text = "IEC Temperatures"
    pf.add_basic_layout(p)

    p.line(x = "start_time", y = "average", color = "brown", legend = "ICE Internal", source = plot_data)
    p.scatter(x = "start_time", y = "average", color = "brown", legend = "ICE Internal", source = plot_data)

    a = pf.add_to_plot(p, "ICE IEC A", "ST_ZTC1MIRIA", start, end, conn, color = "burlywood")
    b = pf.add_to_plot(p, "FPE IEC A", "ST_ZTC2MIRIA", start, end, conn, color = "cadetblue")
    j = pf.add_to_plot(p, "ICE IEC B", "ST_ZTC1MIRIB", start, end, conn, color = "blue")
    k = pf.add_to_plot(p, "FPE IEC B.", "ST_ZTC2MIRIB", start, end, conn, color = "brown")
    c = pf.add_to_plot(p, "FPE PDU", "IMIR_PDU_TEMP", start, end, conn, color = "chartreuse")
    d = pf.add_to_plot(p, "ANA IC", "IMIR_IC_SCE_ANA_TEMP1", start, end, conn, color = "chocolate")
    e = pf.add_to_plot(p, "ANA SW", "IMIR_SW_SCE_ANA_TEMP1", start, end, conn, color = "coral")
    f = pf.add_to_plot(p, "ANA LW", "IMIR_LW_SCE_ANA_TEMP1", start, end, conn, color = "darkorange")
    g = pf.add_to_plot(p, "DIG IC", "IMIR_IC_SCE_DIG_TEMP", start, end, conn, color = "crimson")
    h = pf.add_to_plot(p, "DIG SW", "IMIR_SW_SCE_DIG_TEMP", start, end, conn, color = "cyan")
    i = pf.add_to_plot(p, "DIG LW", "IMIR_LW_SCE_DIG_TEMP", start, end, conn, color = "darkblue")

    pf.add_hover_tool(p,[a,b,c,d,e,f,g,h,i,j,k])

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def det(conn, start, end):
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
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 400,                                  \
                y_range = [6.395,6.41],                             \
                x_axis_type = 'datetime',                           \
                output_backend="webgl",                             \
                x_axis_label = 'Date', y_axis_label = 'Temperature (K)')

    p.grid.visible = True
    p.title.text = "Detector Temperature"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "Det. Temp. IC", "IGDP_MIR_IC_DET_TEMP", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "Det. Temp. LW", "IGDP_MIR_LW_DET_TEMP", start, end, conn, color = "green")
    c = pf.add_to_plot(p, "Det. Temp. SW", "IGDP_MIR_SW_DET_TEMP", start, end, conn, color = "blue")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
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
    </style>

    <body>
    <table style="width:100%">
      <tr>
        <th><h6>Plotname</h6></th>
        <th><h6>Mnemonic</h6></th>
        <th><h6>Description</h6></th>
      </tr>
      <tr>
        <td>CRYO Temperatures</td>
        <td>IGDP_MIR_ICE_T1P_CRYO<br>
            IGDP_MIR_ICE_T2R_CRYO<br>
            IGDP_MIR_ICE_T3LW_CRYO<br>
            IGDP_MIR_ICE_T4SW_CRYO<br>
            IGDP_MIR_ICE_T5IMG_CRYO<br>
            IGDP_MIR_ICE_T6DECKCRYO<br>
            IGDP_MIR_ICE_T7IOC_CRYO<br>
            IGDP_MIR_ICE_FW_CRYO<br>
            IGDP_MIR_ICE_CCC_CRYO<br>
            IGDP_MIR_ICE_GW14_CRYO<br>
            IGDP_MIR_ICE_GW23_CRYO<br>
            IGDP_MIR_ICE_POMP_CRYO<br>
            IGDP_MIR_ICE_POMR_CRYO<br>
            IGDP_MIR_ICE_IFU_CRYO<br>
            IGDP_MIR_ICE_IMG_CRYO<br></td>
        <td>Deck Nominal Temperature (T1)<br>
            Deck Redundant Temperature (T2)<br>
            LW FPM I/F Temperature (T3)<br>
            SW FPM I/F Temperature (T4)<br>
            IM FPM I/F Temperature (T5)<br>
            A-B Strut Apex Temperature (T6)<br>
            IOC Temperature (T7)<br>
            FWA Temperature<br>
            CCC Temperature<br>
            DGA-A (GW14) Temperature<br>
            DGA-B (GW23) Temperature<br>
            POMH Nominal Temperature<br>
            POMH Redundant Temperature<br>
            MRS (CF) Cal. Source Temperature<br>
            Imager (CI) Cal. Source Temperature<br></td>
      </tr>
      <tr>
        <td>IEC Temperatures</td>
        <td>ST_ZTC1MIRIA<br>
            ST_ZTC2MIRIA<br>
            ST_ZTC1MIRIB<br>
            ST_ZTC2MIRIB<br>
            IGDP_MIR_ICE_INTER_TEMP<br>
            IMIR_PDU_TEMP<br>
            IMIR_IC_SCE_ANA_TEMP1<br>
            IMIR_SW_SCE_ANA_TEMP1<br>
            IMIR_LW_SCE_ANA_TEMP1<br>
            IMIR_IC_SCE_DIG_TEMP<br>
            IMIR_SW_SCE_DIG_TEMP<br>
            IMIR_LW_SCE_DIG_TEMP<br></td>
        <td>ICE IEC Panel Temp A<br>
            FPE IEC Panel Temp A<br>
            ICE IEC Panel Temp B<br>
            FPE IEC Panel Temp B<br>
            ICE internal Temperature<br>
            FPE PDU Temperature<br>
            FPE SCE Analogue board Temperature IC<br>
            FPE SCE Analogue board Temperature SW<br>
            FPE SCE Analogue board Temperature LW<br>
            FPE SCE Digital board Temperature IC<br>
            FPE SCE Digital board Temperature SW<br>
            FPE SCE Digital board Temperature LW<br></td>
      </tr>
       <tr>
         <td>Detector Temperatures</td>
         <td>IGDP_MIR_IC_DET_TEMP<br>
            IGDP_MIR_lW_DET_TEMP<br>
            IGDP_MIR_SW_DET_TEMP<br></td>
         <td>Detector Temperature (IC,SW&LW)<br></td>
       </tr>
    </table>
    </body>
    """, width=1100)


    plot1 = cryo(conn, start, end)
    plot2 = temp(conn, start, end)
    plot3 = det(conn, start, end)

    layout = column(descr, plot1, plot2, plot3)
    tab = Panel(child = layout, title = "TEMPERATURE")

    return tab
