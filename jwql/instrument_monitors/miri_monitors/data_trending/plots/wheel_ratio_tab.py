"""wheel_ratio_tab.py

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1:
    IMIR_HK_FW_POS_RATIO_FND
    IMIR_HK_FW_POS_RATIO_OPAQUE
    IMIR_HK_FW_POS_RATIO_F1000W
    IMIR_HK_FW_POS_RATIO_F1130W
    IMIR_HK_FW_POS_RATIO_F1280W
    IMIR_HK_FW_POS_RATIO_P750L
    IMIR_HK_FW_POS_RATIO_F1500W
    IMIR_HK_FW_POS_RATIO_F1800W
    IMIR_HK_FW_POS_RATIO_F2100W
    IMIR_HK_FW_POS_RATIO_F560W
    IMIR_HK_FW_POS_RATIO_FLENS
    IMIR_HK_FW_POS_RATIO_F2300C
    IMIR_HK_FW_POS_RATIO_F770W
    IMIR_HK_FW_POS_RATIO_F1550C
    IMIR_HK_FW_POS_RATIO_F2550W
    IMIR_HK_FW_POS_RATIO_F1140C
    IMIR_HK_FW_POS_RATIO_F2550WR
    IMIR_HK_FW_POS_RATIO_F1065C

    Plot 2:
    IMIR_HK_GW14_POS_RATIO_SHORT
    IMIR_HK_GW14_POS_RATIO_MEDIUM
    IMIR_HK_GW14_POS_RATIO_LONG

    Plot 3:
    IMIR_HK_GW23_POS_RATIO_SHORT
    IMIR_HK_GW23_POS_RATIO_MEDIUM
    IMIR_HK_GW23_POS_RATIO_LONG

    Plot 4:
    IMIR_HK_CCC_POS_RATIO_LOCKED
    IMIR_HK_CCC_POS_RATIO_OPEN
    IMIR_HK_CCC_POS_RATIO_CLOSED

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
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.utils_f as utils


def gw14(conn, start, end):
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
    p = utils.get_figure(end, "DGA-A Ratio", "ratio (normalized)", 1120, 500, [-20, 20])

    a = pf.add_to_wplot(p, "SHORT", "IMIR_HK_GW14_POS_RATIO_SHORT", start, end, conn, mn.gw14_nominals['SHORT'],
                        color="green")
    b = pf.add_to_wplot(p, "MEDIUM", "IMIR_HK_GW14_POS_RATIO_MEDIUM", start, end, conn, mn.gw14_nominals['MEDIUM'],
                        color="red")
    c = pf.add_to_wplot(p, "LONG", "IMIR_HK_GW14_POS_RATIO_LONG", start, end, conn, mn.gw14_nominals['LONG'],
                        color="blue")

    pf.add_hover_tool_weel(p, [a, b, c])

    p.legend.click_policy = "hide"

    return p


def gw23(conn, start, end):
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

    p = utils.get_figure(end, "DGA-B Ratio", "ratio (normalized)", 1120, 500, [-30, 30])

    a = pf.add_to_wplot(p, "SHORT", "IMIR_HK_GW23_POS_RATIO_SHORT", start, end, conn, mn.gw23_nominals['SHORT'],
                        color="green")
    b = pf.add_to_wplot(p, "MEDIUM", "IMIR_HK_GW23_POS_RATIO_MEDIUM", start, end, conn, mn.gw23_nominals['MEDIUM'],
                        color="red")
    c = pf.add_to_wplot(p, "LONG", "IMIR_HK_GW23_POS_RATIO_LONG", start, end, conn, mn.gw23_nominals['LONG'],
                        color="blue")

    pf.add_hover_tool_weel(p, [a, b, c])
    p.legend.click_policy = "hide"

    return p


def ccc(conn, start, end):
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

    p = utils.get_figure(end, "CCC Ratio", "ratio (normalized)", 1120, 500, [-30, 30])

    # add_to_wplot(p, "LOCKED", "IMIR_HK_CCC_POS_RATIO_LOCKED", start, end, conn, mn.ccc_nominals['LOCKED'], color = "green")
    a = pf.add_to_wplot(p, "OPEN", "IMIR_HK_CCC_POS_RATIO_OPEN", start, end, conn, mn.ccc_nominals['OPEN'], color="red")
    b = pf.add_to_wplot(p, "CLOSED", "IMIR_HK_CCC_POS_RATIO_CLOSED", start, end, conn, mn.ccc_nominals['CLOSED'],
                        color="blue")

    pf.add_hover_tool_weel(p, [a, b])
    p.legend.click_policy = "hide"

    return p


def fw(conn, start, end):
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

    p = utils.get_figure(end, "Filterwheel Ratio", "ratio (normalized)", 1120, 800, [-20, 20])

    a = pf.add_to_wplot(p, "FND", "IMIR_HK_FW_POS_RATIO_FND", start, end, conn, mn.fw_nominals['FND'], color="green")
    b = pf.add_to_wplot(p, "OPAQUE", "IMIR_HK_FW_POS_RATIO_OPAQUE", start, end, conn, mn.fw_nominals['OPAQUE'],
                        color="red")
    c = pf.add_to_wplot(p, "F1000W", "IMIR_HK_FW_POS_RATIO_F1000W", start, end, conn, mn.fw_nominals['F1000W'],
                        color="blue")
    d = pf.add_to_wplot(p, "F1130W", "IMIR_HK_FW_POS_RATIO_F1130W", start, end, conn, mn.fw_nominals['F1130W'],
                        color="orange")
    e = pf.add_to_wplot(p, "F1280W", "IMIR_HK_FW_POS_RATIO_F1280W", start, end, conn, mn.fw_nominals['F1280W'],
                        color="firebrick")
    f = pf.add_to_wplot(p, "P750L", "IMIR_HK_FW_POS_RATIO_P750L", start, end, conn, mn.fw_nominals['P750L'],
                        color="cyan")
    g = pf.add_to_wplot(p, "F1500W", "IMIR_HK_FW_POS_RATIO_F1500W", start, end, conn, mn.fw_nominals['F1500W'],
                        color="magenta")
    h = pf.add_to_wplot(p, "F1800W", "IMIR_HK_FW_POS_RATIO_F1800W", start, end, conn, mn.fw_nominals['F1800W'],
                        color="burlywood")
    i = pf.add_to_wplot(p, "F2100W", "IMIR_HK_FW_POS_RATIO_F2100W", start, end, conn, mn.fw_nominals['F2100W'],
                        color="cadetblue")
    j = pf.add_to_wplot(p, "F560W", "IMIR_HK_FW_POS_RATIO_F560W", start, end, conn, mn.fw_nominals['F560W'],
                        color="chartreuse")
    k = pf.add_to_wplot(p, "FLENS", "IMIR_HK_FW_POS_RATIO_FLENS", start, end, conn, mn.fw_nominals['FLENS'],
                        color="brown")
    l = pf.add_to_wplot(p, "F2300C", "IMIR_HK_FW_POS_RATIO_F2300C", start, end, conn, mn.fw_nominals['F2300C'],
                        color="chocolate")
    m = pf.add_to_wplot(p, "F770W", "IMIR_HK_FW_POS_RATIO_F770W", start, end, conn, mn.fw_nominals['F770W'],
                        color="darkorange")
    n = pf.add_to_wplot(p, "F1550C", "IMIR_HK_FW_POS_RATIO_F1550C", start, end, conn, mn.fw_nominals['F1550C'],
                        color="darkgreen")
    o = pf.add_to_wplot(p, "F2550W", "IMIR_HK_FW_POS_RATIO_F2550W", start, end, conn, mn.fw_nominals['F2550W'],
                        color="darkcyan")
    q = pf.add_to_wplot(p, "F1140C", "IMIR_HK_FW_POS_RATIO_F1140C", start, end, conn, mn.fw_nominals['F1140C'],
                        color="darkmagenta")
    r = pf.add_to_wplot(p, "F2550WR", "IMIR_HK_FW_POS_RATIO_F2550WR", start, end, conn, mn.fw_nominals['F2550WR'],
                        color="crimson")
    s = pf.add_to_wplot(p, "F1065C", "IMIR_HK_FW_POS_RATIO_F1065C", start, end, conn, mn.fw_nominals['F1065C'],
                        color="cornflowerblue")

    pf.add_hover_tool_weel(p, [a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, q, r, s])
    p.legend.click_policy = "hide"

    return p


def wheel_ratios(conn, start, end):
    """Combine plots to a tab
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

    descr = tabObjects.generate_tab_description(utils.description_weehl)

    plot1 = fw(conn, start, end)
    plot2 = gw14(conn, start, end)
    plot3 = gw23(conn, start, end)
    plot4 = ccc(conn, start, end)
    data_table = tabObjects.anomaly_table(conn, utils.list_mn_weelRatio)

    layout = column(descr, plot1, plot2, plot3, plot4, data_table)
    tab = Panel(child=layout, title="WHEEL RATIO")

    return tab
