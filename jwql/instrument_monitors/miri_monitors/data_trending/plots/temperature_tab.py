"""Prepares plots for TEMPERATURE tab on MIRI data trending webpage

Module prepares plots for the mnemonics listed below. Combines plots
in a grid and returns tab object.

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

    User must provide database ``miri_database.db``

    Other dependencies include:

    - ``astropy``
    - ``bokeh``
    - ``pandas``
"""

from astropy.time import Time
from bokeh.layouts import column
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Panel, Div
from bokeh.plotting import figure
import pandas as pd

import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as plot_functions


def cryo(conn, start, end):
    """Generates the 'Cryo Temperatures' plot

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    # Create the plot
    plot = figure(
        tools='pan,wheel_zoom,box_zoom,reset,save',
        toolbar_location='above',
        plot_width=1120,
        plot_height=700,
        y_range=[5.8, 6.4],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Temperature (K)')
    plot.grid.visible = True
    plot.title.text = 'Cryo Temperatures'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    t1p_line = plot_functions.add_to_plot(plot, 'T1P', 'IGDP_MIR_ICE_T1P_CRYO', start, end, conn, color='brown')
    t2r_line = plot_functions.add_to_plot(plot, 'T2R', 'IGDP_MIR_ICE_T2R_CRYO', start, end, conn, color='burlywood')
    t3lw_line = plot_functions.add_to_plot(plot, 'T3LW', 'IGDP_MIR_ICE_T3LW_CRYO', start, end, conn, color='cadetblue')
    t4sw_line = plot_functions.add_to_plot(plot, 'T4SW', 'IGDP_MIR_ICE_T4SW_CRYO', start, end, conn, color='chartreuse')
    t5img_line = plot_functions.add_to_plot(plot, 'T5IMG', 'IGDP_MIR_ICE_T5IMG_CRYO', start, end, conn, color='chocolate')
    t6deck_line = plot_functions.add_to_plot(plot, 'T6DECK', 'IGDP_MIR_ICE_T6DECKCRYO', start, end, conn, color='coral')
    t7ioc_line = plot_functions.add_to_plot(plot, 'T7IOC', 'IGDP_MIR_ICE_T7IOC_CRYO', start, end, conn, color='darkorange')
    fw_line = plot_functions.add_to_plot(plot, 'FW', 'IGDP_MIR_ICE_FW_CRYO', start, end, conn, color='crimson')
    ccc_line = plot_functions.add_to_plot(plot, 'CCC', 'IGDP_MIR_ICE_CCC_CRYO', start, end, conn, color='cyan')
    gw14_line = plot_functions.add_to_plot(plot, 'GW14', 'IGDP_MIR_ICE_GW14_CRYO', start, end, conn, color='darkblue')
    gw23_line = plot_functions.add_to_plot(plot, 'GW23', 'IGDP_MIR_ICE_GW23_CRYO', start, end, conn, color='darkgreen')
    pomp_line = plot_functions.add_to_plot(plot, 'POMP', 'IGDP_MIR_ICE_POMP_CRYO', start, end, conn, color='darkmagenta')
    pomr_line = plot_functions.add_to_plot(plot, 'POMR', 'IGDP_MIR_ICE_POMR_CRYO', start, end, conn, color='darkcyan')
    ifu_line = plot_functions.add_to_plot(plot, 'IFU', 'IGDP_MIR_ICE_IFU_CRYO', start, end, conn, color='cornflowerblue')
    img_line = plot_functions.add_to_plot(plot, 'IMG', 'IGDP_MIR_ICE_IMG_CRYO', start, end, conn, color='orange')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [t1p_line, t2r_line, t3lw_line, t4sw_line, t5img_line, t6deck_line, t7ioc_line,
                                         fw_line, ccc_line, gw14_line, gw23_line, pomp_line, pomr_line, ifu_line, img_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.orientation = 'horizontal'
    plot.legend.click_policy = 'hide'

    return plot


def detector(conn, start, end):
    """Generates the 'Detector Temperatures' plot

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    # Create the plot
    plot = figure(
        tools='pan,wheel_zoom,box_zoom,reset,save',
        toolbar_location='above',
        plot_width=1120,
        plot_height=400,
        y_range=[6.395, 6.41],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Temperature (K)')
    plot.grid.visible = True
    plot.title.text = 'Detector Temperature'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    ic_line = plot_functions.add_to_plot(plot, 'Det. Templot. IC', 'IGDP_MIR_IC_DET_TEMP', start, end, conn, color='red')
    lw_line = plot_functions.add_to_plot(plot, 'Det. Templot. LW', 'IGDP_MIR_LW_DET_TEMP', start, end, conn, color='green')
    sw_line = plot_functions.add_to_plot(plot, 'Det. Templot. SW', 'IGDP_MIR_SW_DET_TEMP', start, end, conn, color='blue')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [ic_line, lw_line, sw_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.orientation = 'horizontal'
    plot.legend.click_policy = 'hide'

    return plot


def iec_temp(conn, start, end):
    """Generates the 'IEC Temperatures' plot

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    # Query data from database
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)
    command = 'SELECT * FROM IGDP_MIR_ICE_INTER_TEMP \
               WHERE start_time BETWEEN {} AND {} \
               ORDER BY start_time'.format(start_str, end_str)
    temp = pd.read_sql_query(command, conn)

    # Apply temperature factor
    temp['average'] += 273.15
    reg = pd.DataFrame({'reg': plot_functions.pol_regression(temp['start_time'], temp['average'], 3)})
    temp = pd.concat([temp, reg], axis=1)

    # Set column data source
    temp['start_time'] = pd.to_datetime(Time(temp['start_time'], format='mjd').datetime)
    plot_data = ColumnDataSource(temp)

    # Create the plot
    plot = figure(
        tools='pan,wheel_zoom,box_zoom,reset,save',
        toolbar_location='above',
        plot_width=1120,
        plot_height=700,
        y_range=[275, 295],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Temperature (K)')
    plot.grid.visible = True
    plot.title.text = 'IEC Temperatures'
    plot_functions.add_basic_layout(plot)
    plot.line(x='start_time', y='average', color='brown', legend='ICE Internal', source=plot_data)
    plot.scatter(x='start_time', y='average', color='brown', legend='ICE Internal', source=plot_data)

    # Add a line renderer with legend and line thickness
    ice_iec_a_line = plot_functions.add_to_plot(plot, 'ICE IEC A', 'ST_ZTC1MIRIA', start, end, conn, color='burlywood')
    fpe_iec_a_line = plot_functions.add_to_plot(plot, 'FPE IEC A', 'ST_ZTC2MIRIA', start, end, conn, color='cadetblue')
    fpe_pdu_line = plot_functions.add_to_plot(plot, 'FPE PDU', 'IMIR_PDU_TEMP', start, end, conn, color='chartreuse')
    ana_ic_line = plot_functions.add_to_plot(plot, 'ANA IC', 'IMIR_IC_SCE_ANA_TEMP1', start, end, conn, color='chocolate')
    ana_sw_line = plot_functions.add_to_plot(plot, 'ANA SW', 'IMIR_SW_SCE_ANA_TEMP1', start, end, conn, color='coral')
    ana_lw_line = plot_functions.add_to_plot(plot, 'ANA LW', 'IMIR_LW_SCE_ANA_TEMP1', start, end, conn, color='darkorange')
    dig_ic_line = plot_functions.add_to_plot(plot, 'DIG IC', 'IMIR_IC_SCE_DIG_TEMP', start, end, conn, color='crimson')
    dig_sw_line = plot_functions.add_to_plot(plot, 'DIG SW', 'IMIR_SW_SCE_DIG_TEMP', start, end, conn, color='cyan')
    dig_lw_line = plot_functions.add_to_plot(plot, 'DIG LW', 'IMIR_LW_SCE_DIG_TEMP', start, end, conn, color='darkblue')
    ice_iec_b_line = plot_functions.add_to_plot(plot, 'ICE IEC B', 'ST_ZTC1MIRIB', start, end, conn, color='blue')
    fpe_iec_b_line = plot_functions.add_to_plot(plot, 'FPE IEC B.', 'ST_ZTC2MIRIB', start, end, conn, color='brown')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [ice_iec_a_line, fpe_iec_a_line, fpe_pdu_line, ana_ic_line, ana_sw_line, ana_lw_line,
                                         dig_ic_line, dig_sw_line, dig_lw_line, ice_iec_b_line, fpe_iec_b_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.orientation = 'horizontal'
    plot.legend.click_policy = 'hide'

    return plot


def temperature_plots(conn, start, end):
    """Generates the 'TEMPERATURE' tab

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    description_table = Div(
        text="""
            <style>
            table, th, td {
              border: 1px solid black;
              background-color: #efefef;
              border-collapse: collapse;
              padding: 5px
            }
            </style>

            <body>
            <table style='width:100%'>
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
            </body>""",
        width=1100)

    plot1 = cryo(conn, start, end)
    plot2 = iec_temp(conn, start, end)
    plot3 = detector(conn, start, end)
    layout = column(description_table, plot1, plot2, plot3)
    tab = Panel(child=layout, title='TEMPERATURE')

    return tab
