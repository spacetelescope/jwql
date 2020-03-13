"""bias_tab.py

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1:
    IGDP_MIR_IC_V_VDETCOM
    IGDP_MIR_SW_V_VDETCOM
    IGDP_MIR_LW_V_VDETCOM

    Plot 2:
    IGDP_MIR_IC_V_VSSOUT
    IGDP_MIR_SW_V_VSSOUT
    IGDP_MIR_LW_V_VSSOUT

    Plot 3:
    IGDP_MIR_IC_V_VRSTOFF
    IGDP_MIR_SW_V_VRSTOFF
    IGDP_MIR_LW_V_VRSTOFF

    Plot 4:
    IGDP_MIR_IC_V_VP
    IGDP_MIR_SW_V_VP
    IGDP_MIR_LW_V_VP

    Plot 5
    IGDP_MIR_IC_V_VDDUC
    IGDP_MIR_SW_V_VDDUC
    IGDP_MIR_LW_V_VDDUC

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
from bokeh.layouts import gridplot, Column
from bokeh.models.widgets import Panel

import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.miri_monitors.data_trending.plots.tab_object as tabObjects
import jwql.instrument_monitors.miri_monitors.data_trending.utils.utils_f as utils


def vdetcom(conn, start, end):
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

    p = utils.get_figure(end, "VDETCOM", "Voltage (V)", 560, 500, [-5, -1])

    a = pf.add_to_plot(p, "VDETCOM IC", "IGDP_MIR_IC_V_VDETCOM", start, end, conn, color="red")
    b = pf.add_to_plot(p, "VDETCOM SW", "IGDP_MIR_SW_V_VDETCOM", start, end, conn, color="orange")
    c = pf.add_to_plot(p, "VDETCOM LW", "IGDP_MIR_LW_V_VDETCOM", start, end, conn, color="green")

    pf.add_hover_tool(p, [a, b, c])
    p.legend.click_policy = "hide"
    return p


def vssout(conn, start, end):
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

    p = utils.get_figure(end, "VSSOUT", "Voltage (V)", 560, 500, [1.5, 5])

    a = pf.add_to_plot(p, "VSSOUT IC", "IGDP_MIR_IC_V_VSSOUT", start, end, conn, color="red")
    b = pf.add_to_plot(p, "VSSOUT SW", "IGDP_MIR_SW_V_VSSOUT", start, end, conn, color="orange")
    c = pf.add_to_plot(p, "VSSOUT LW", "IGDP_MIR_LW_V_VSSOUT", start, end, conn, color="green")

    pf.add_hover_tool(p, [a, b, c])
    p.legend.click_policy = "hide"
    return p


def vrstoff(conn, start, end):
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

    p = utils.get_figure(end, "VRSTOFF", "Voltage (V)", 560, 500, [-3, 3])

    a = pf.add_to_plot(p, "VRSTOFF IC", "IGDP_MIR_IC_V_VRSTOFF", start, end, conn, color="red")
    b = pf.add_to_plot(p, "VRSTOFF SW", "IGDP_MIR_SW_V_VRSTOFF", start, end, conn, color="orange")
    c = pf.add_to_plot(p, "VRSTOFF LW", "IGDP_MIR_LW_V_VRSTOFF", start, end, conn, color="green")

    pf.add_hover_tool(p, [a, b, c])
    p.legend.click_policy = "hide"
    return p


def vp(conn, start, end):
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

    p = utils.get_figure(end, "VP", "Voltage (V)", 560, 500, [-3, 3])

    a = pf.add_to_plot(p, "VP IC", "IGDP_MIR_IC_V_VP", start, end, conn, color="red")
    b = pf.add_to_plot(p, "VP SW", "IGDP_MIR_SW_V_VP", start, end, conn, color="orange")
    c = pf.add_to_plot(p, "VP LW", "IGDP_MIR_LW_V_VP", start, end, conn, color="green")

    pf.add_hover_tool(p, [a, b, c])
    p.legend.click_policy = "hide"
    return p


def vdduc(conn, start, end):
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

    p = utils.get_figure(end, "VDDUC", "Voltage (V)", 560, 500, [-3, 3])

    a = pf.add_to_plot(p, "VDDUC IC", "IGDP_MIR_IC_V_VDDUC", start, end, conn, color="red")
    b = pf.add_to_plot(p, "VDDUC SW", "IGDP_MIR_SW_V_VDDUC", start, end, conn, color="orange")
    c = pf.add_to_plot(p, "VDDUC LW", "IGDP_MIR_LW_V_VDDUC", start, end, conn, color="green")

    pf.add_hover_tool(p, [a, b, c])
    p.legend.click_policy = "hide"
    return p


def bias_plots(conn, start, end):
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

    descr = tabObjects.generate_tab_description(utils.description_bias)

    plot1 = vdetcom(conn, start, end)
    plot2 = vssout(conn, start, end)
    plot3 = vrstoff(conn, start, end)
    plot4 = vp(conn, start, end)
    plot5 = vdduc(conn, start, end)
    data_table = tabObjects.anomaly_table(conn, utils.list_ms_bias)

    l = gridplot([[plot2, plot1],
                  [plot3, plot4],
                  [plot5, None]], merge_tools=False)

    layout = Column(descr, l, data_table)

    tab = Panel(child=layout, title="BIAS")

    return tab
