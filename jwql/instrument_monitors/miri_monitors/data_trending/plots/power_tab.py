"""power_tab.py

    Module prepares plots for mnemonics below. Combines plots in a grid and
    returns tab object.

    Plot 1:
    SE_ZIMIRICEA

    Plot 2:
    SE_ZIMIRIFPEA

    Plot 3:
    SE_ZIMIRFPEA
    SE_ZIMIRCEA

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
import pandas as pd
from astropy.time import Time
from bokeh.layouts import column
from bokeh.models import (ColumnDataSource,
                          DataTable, TableColumn, )
from bokeh.models import Div
from bokeh.models.widgets import Panel

import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.miri_monitors.data_trending.plots.tab_object as tabObjects
import jwql.instrument_monitors.miri_monitors.data_trending.utils.utils_f as utils


def power_ice(conn, start, end):
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM SE_ZIMIRICEA_IDLE WHERE start_time BETWEEN " + start_str + " AND " + end_str + " ORDER BY start_time"
    _idle = pd.read_sql_query(sql_c, conn)
    sql_c = "SELECT * FROM SE_ZIMIRICEA_HV_ON WHERE start_time BETWEEN " + start_str + " AND " + end_str + " ORDER BY start_time"
    _hv = pd.read_sql_query(sql_c, conn)

    voltage = 30
    _idle['average'] *= voltage
    _hv['average'] *= voltage

    _idle['start_time'] = pd.to_datetime(Time(_idle['start_time'], format="mjd").datetime)
    _hv['start_time'] = pd.to_datetime(Time(_hv['start_time'], format="mjd").datetime)

    # set column data source

    timeDeltaEnd = Time(end).datetime

    p = utils.get_figure(end, "POWER ICE", "Power (W)", 1120, 500, [5, 14])
    pf.add_limit_box(p, 6, 8, alpha=0.1, color="green")

    voltage = 30
    a = pf.add_to_plot(p, "Power idle", "SE_ZIMIRICEA_IDLE", start, end, conn, color="orange")
    b = pf.add_to_plot(p, "Power hv on", "SE_ZIMIRICEA_HV_ON", start, end, conn, color="red")
    a.data_source.data['average'] *= voltage
    b.data_source.data['average'] *= voltage

    # generate error bars
    err_xs_hv = []
    err_ys_hv = []
    err_xs_idle = []
    err_ys_idle = []

    for index, item in _hv.iterrows():
        err_xs_hv.append((item['start_time'], item['start_time']))
        err_ys_hv.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

    for index, item in _idle.iterrows():
        err_xs_idle.append((item['start_time'], item['start_time']))
        err_ys_idle.append((item['average'] - item['deviation'], item['average'] + item['deviation']))
    # plot them
    p.multi_line(err_xs_hv, err_ys_hv, color='red', legend='Power hv on')
    p.multi_line(err_xs_idle, err_ys_idle, color='orange', legend='Power idle')

    pf.add_hover_tool(p, [a, b])
    # activate HoverTool for scatter plot

    p.legend.click_policy = "hide"

    return p


def power_fpea(conn, start, end):
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM SE_ZIMIRFPEA WHERE start_time BETWEEN " + start_str + " AND " + end_str + " ORDER BY start_time"
    _fpea = pd.read_sql_query(sql_c, conn)

    voltage = 30
    _fpea['average'] *= voltage

    _fpea['start_time'] = pd.to_datetime(Time(_fpea['start_time'], format="mjd").datetime)

    # set column data source
    fpea = ColumnDataSource(_fpea)

    # create a new plot with a title and axis labels
    p = utils.get_figure(end, "POWER FPE", "Power (W)", 1120, 500, [28.0, 28.5])

    # add a line renderer with legend and line thickness
    scat1 = p.scatter(x="start_time", y="average", color='orange', legend="Power FPEA", source=fpea)
    scat1.data_source.data['average'] *= voltage

    err_xs = []
    err_ys = []

    for index, item in _fpea.iterrows():
        err_xs.append((item['start_time'], item['start_time']))
        err_ys.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

    # plot them
    p.multi_line(err_xs, err_ys, color='orange', legend='Power FPEA')

    # activate HoverTool for scatter plot
    pf.add_hover_tool(p, [scat1])
    p.legend.click_policy = "hide"

    return p


def currents(conn, start, end):
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
    p = utils.get_figure(end, "FPE & ICE Currents", "Current (A)", 1120, 500, [0, 1.1])

    a = pf.add_to_plot(p, "ICE Current idle", "SE_ZIMIRICEA_IDLE", start, end, conn, color="red")
    b = pf.add_to_plot(p, "ICE Current HV on", "SE_ZIMIRICEA_HV_ON", start, end, conn, color="orange")
    c = pf.add_to_plot(p, "FPE Current", "SE_ZIMIRFPEA", start, end, conn, color="brown")

    pf.add_hover_tool(p, [a, b, c])
    p.legend.click_policy = "hide"

    return p


def anomaly_table(conn, mnemonic):
    get_str = '('
    for element in mnemonic:
        get_str = get_str + "'" + str(element) + "',"
    get_str = get_str[:-1] + ')'

    sql_c = "SELECT * FROM miriAnomaly WHERE plot in " + get_str + " ORDER BY start_time"
    anomaly_orange = pd.read_sql_query(sql_c, conn)

    div = Div(text="<font size='5'> Reported anomalys: </font>")

    try:
        # convert mjd to iso time
        anomaly_orange['start_time'] = Time(anomaly_orange['start_time'], format='mjd').iso
        anomaly_orange['end_time'] = Time(anomaly_orange['end_time'], format='mjd').iso

        # neu
        source = ColumnDataSource(anomaly_orange)

        columns = [
            TableColumn(field="id", title="ID", width=20),
            TableColumn(field="plot", title="Mnemonic", width=100),
            TableColumn(field="autor", title="Autor", width=100),
            TableColumn(field="start_time", title="Start Time", width=200),
            TableColumn(field="end_time", title="End Time", width=200),
            TableColumn(field="comment", title="Comment", width=600),
        ]

        data_table = DataTable(source=source, columns=columns, editable=False, width=1120, fit_columns=True,
                               index_position=None, selectable=True)
    except:
        data_table = Div(text='There are currently no anomalies reported')

    return column(div, data_table)


def power_plots(conn, start, end):
    descr = tabObjects.generate_tab_description(utils.description_power)

    plot1 = power_ice(conn, start, end)
    plot2 = power_fpea(conn, start, end)
    plot3 = currents(conn, start, end)
    data_table = tabObjects.anomaly_table(conn, utils.list_mn_power)

    layout = column(descr, plot1, plot2, plot3, data_table)

    # layout_volt = row(volt4, volt1_3)
    tab = Panel(child=layout, title="POWER")

    return tab
