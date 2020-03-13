"""temperature_tab.py

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
    - [AIRBUS] Daniel Kübacher
    - [AIRBUS] Leo Stumpf

Use
---
    The functions within this module are intended to be imported and
    used by ``dashborad.py``, e.g.:

    ::
        from .plots.bias_tab import bias_plots
        tab = bias_plots(conn, start, end)

Dependencies
------------
    The file miri_database.db in the directory jwql/jwql/database/ must be populated.

References
----------
    The code was developed in reference to the information provided in:
    ‘MIRI trend requestsDRAFT1900301.docx’

Notes
-----
    For further information please contact Brian O'Sullivan
"""

from bokeh.layouts import column
from bokeh.models.widgets import Panel

import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.miri_monitors.data_trending.plots.tab_object as tabObjects
import jwql.instrument_monitors.miri_monitors.data_trending.utils.utils_f as utils


def cryo(conn, start, end):
    """Create specific plot and return plot object
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
    """

    # create a new plot with a title and axis labels
    p = utils.get_figure(end, "Cryo Temperature", "Temperature (K)", 1120, 700, [0, 10])

    a = pf.add_to_plot(p, "T1P", "IGDP_MIR_ICE_T1P_CRYO", start, end, conn, color="brown")
    b = pf.add_to_plot(p, "T2R", "IGDP_MIR_ICE_T2R_CRYO", start, end, conn, color="burlywood")
    c = pf.add_to_plot(p, "T3LW", "IGDP_MIR_ICE_T3LW_CRYO", start, end, conn, color="cadetblue")
    d = pf.add_to_plot(p, "T4SW", "IGDP_MIR_ICE_T4SW_CRYO", start, end, conn, color="chartreuse")
    e = pf.add_to_plot(p, "T5IMG", "IGDP_MIR_ICE_T5IMG_CRYO", start, end, conn, color="chocolate")
    f = pf.add_to_plot(p, "T6DECK", "IGDP_MIR_ICE_T6DECKCRYO", start, end, conn, color="coral")
    g = pf.add_to_plot(p, "T7IOC", "IGDP_MIR_ICE_T7IOC_CRYO", start, end, conn, color="darkorange")
    h = pf.add_to_plot(p, "FW", "IGDP_MIR_ICE_FW_CRYO", start, end, conn, color="crimson")
    i = pf.add_to_plot(p, "CCC", "IGDP_MIR_ICE_CCC_CRYO", start, end, conn, color="cyan")
    j = pf.add_to_plot(p, "GW14", "IGDP_MIR_ICE_GW14_CRYO", start, end, conn, color="darkblue")
    k = pf.add_to_plot(p, "GW23", "IGDP_MIR_ICE_GW23_CRYO", start, end, conn, color="darkgreen")
    l = pf.add_to_plot(p, "POMP", "IGDP_MIR_ICE_POMP_CRYO", start, end, conn, color="darkmagenta")
    m = pf.add_to_plot(p, "POMR", "IGDP_MIR_ICE_POMR_CRYO", start, end, conn, color="darkcyan")
    n = pf.add_to_plot(p, "IFU", "IGDP_MIR_ICE_IFU_CRYO", start, end, conn, color="cornflowerblue")
    o = pf.add_to_plot(p, "IMG", "IGDP_MIR_ICE_IMG_CRYO", start, end, conn, color="orange")

    pf.add_hover_tool(p, [a, b, c, d, e, f, g, h, i, j, k, l, m, n, o])

    p.legend.click_policy = "hide"

    return p


def temp(conn, start, end):
    """Create specific plot and return plot object
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
    """

    # create a new plot with a title and axis labels
    p = utils.get_figure(end, "IEC Temperature", "Temperature (K)", 1120, 700, [250, 350])

    a = pf.add_to_plot(p, "ICE IEC A", "ST_ZTC1MIRIA", start, end, conn, color="burlywood")
    b = pf.add_to_plot(p, "FPE IEC A", "ST_ZTC2MIRIA", start, end, conn, color="cadetblue")
    j = pf.add_to_plot(p, "ICE IEC B", "ST_ZTC1MIRIB", start, end, conn, color="blue")
    k = pf.add_to_plot(p, "FPE IEC B.", "ST_ZTC2MIRIB", start, end, conn, color="brown")
    c = pf.add_to_plot(p, "FPE PDU", "IMIR_PDU_TEMP", start, end, conn, color="chartreuse")
    d = pf.add_to_plot(p, "ANA IC", "IMIR_IC_SCE_ANA_TEMP1", start, end, conn, color="chocolate")
    e = pf.add_to_plot(p, "ANA SW", "IMIR_SW_SCE_ANA_TEMP1", start, end, conn, color="coral")
    f = pf.add_to_plot(p, "ANA LW", "IMIR_LW_SCE_ANA_TEMP1", start, end, conn, color="darkorange")
    g = pf.add_to_plot(p, "DIG IC", "IMIR_IC_SCE_DIG_TEMP", start, end, conn, color="crimson")
    h = pf.add_to_plot(p, "DIG SW", "IMIR_SW_SCE_DIG_TEMP", start, end, conn, color="cyan")
    i = pf.add_to_plot(p, "DIG LW", "IMIR_LW_SCE_DIG_TEMP", start, end, conn, color="darkblue")
    l = pf.add_to_plot(p, "ICE Internal", "IGDP_MIR_ICE_INTER_TEMP", start, end, conn, color="brown")
    l.data_source.data['average'] += 273.15  # I do not know why

    pf.add_hover_tool(p, [a, b, c, d, e, f, g, h, i, j, k, l])

    p.legend.click_policy = "hide"

    return p


def det(conn, start, end):
    """Create specific plot and return plot object
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
    """

    # create a new plot with a title and axis labels
    p = utils.get_figure(end, "Detector Temperature", "Temperature (K)", 1120, 700, [0, 20])

    a = pf.add_to_plot(p, "Det. Temp. IC", "IGDP_MIR_IC_DET_TEMP", start, end, conn, color="red")
    b = pf.add_to_plot(p, "Det. Temp. LW", "IGDP_MIR_LW_DET_TEMP", start, end, conn, color="green")
    c = pf.add_to_plot(p, "Det. Temp. SW", "IGDP_MIR_SW_DET_TEMP", start, end, conn, color="blue")

    pf.add_hover_tool(p, [a, b, c])

    p.legend.click_policy = "hide"

    return p


def temperature_plots(conn, start, end):
    """Combines plots to a tab
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
    """

    descr = tabObjects.generate_tab_description(utils.description_Temperature)

    plot1 = cryo(conn, start, end)
    plot2 = temp(conn, start, end)
    plot3 = det(conn, start, end)
    data_table = tabObjects.anomaly_table(conn, utils.list_mn_temperature)

    layout = column(descr, plot1, plot2, plot3, data_table)
    tab = Panel(child=layout, title="TEMPERATURE")

    return tab
