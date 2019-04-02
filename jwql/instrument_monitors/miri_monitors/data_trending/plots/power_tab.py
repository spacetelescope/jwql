import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs, Div
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.layouts import column, row, WidgetBox

import pandas as pd
import numpy as np

from astropy.time import Time


def power_ice(conn, start, end):
    #query data from database
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM SE_ZIMIRICEA_IDLE WHERE start_time BETWEEN "+start_str+" AND "+end_str+" ORDER BY start_time"
    _idle = pd.read_sql_query(sql_c, conn)
    sql_c = "SELECT * FROM SE_ZIMIRICEA_HV_ON WHERE start_time BETWEEN "+start_str+" AND "+end_str+" ORDER BY start_time"
    _hv = pd.read_sql_query(sql_c, conn)

    voltage = 30
    _idle['average'] *= voltage
    _hv['average'] *= voltage

    _idle['start_time'] = pd.to_datetime( Time(_idle['start_time'], format = "mjd").datetime )
    _hv['start_time'] = pd.to_datetime( Time(_hv['start_time'], format = "mjd").datetime )

    #set column data source
    idle = ColumnDataSource(_idle)
    hv = ColumnDataSource(_hv)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                  \
                plot_height = 500,                                  \
                y_range = [5,14],                                   \
                x_axis_type = 'datetime',                           \
                output_backend = "webgl",                           \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True
    p.title.text = "POWER ICE"
    pf.add_basic_layout(p)
    pf.add_limit_box(p, 6, 8, alpha = 0.1, color = "green")


    # add a line renderer with legend and line thickness
    scat1=p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Power idle", source = idle)
    scat2=p.scatter(x = "start_time", y = "average", color = 'red', legend = "Power hv on", source = hv)
    p.line(x = "start_time", y = "average", color = 'orange', legend = "Power idle", source = idle)
    p.line(x = "start_time", y = "average", color = 'red', legend = "Power hv on", source = hv)

    #generate error bars
    err_xs_hv = []
    err_ys_hv = []
    err_xs_idle = []
    err_ys_idle = []

    for index, item in _hv.iterrows():
        err_xs_hv.append((item['start_time'],item['start_time']))
        err_ys_hv.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

    for index, item in _idle.iterrows():
        err_xs_idle.append((item['start_time'],item['start_time']))
        err_ys_idle.append((item['average'] - item['deviation'], item['average'] + item['deviation']))
    # plot them
    p.multi_line(err_xs_hv, err_ys_hv, color='red', legend='Power hv on')
    p.multi_line(err_xs_idle, err_ys_idle, color='orange', legend='Power idle')

    #activate HoverTool for scatter plot
    hover_tool = HoverTool( tooltips =
    [
        ('count', '@data_points'),
        ('mean', '@average'),
        ('deviation', '@deviation'),

    ], mode='mouse', renderers=[scat1,scat2])

    p.tools.append(hover_tool)

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def power_fpea(conn, start, end):

    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM SE_ZIMIRFPEA WHERE start_time BETWEEN "+start_str+" AND "+end_str+" ORDER BY start_time"
    _fpea = pd.read_sql_query(sql_c, conn)

    voltage = 30
    _fpea['average'] *= voltage

    _fpea['start_time'] = pd.to_datetime( Time(_fpea['start_time'], format = "mjd").datetime )

    #set column data source
    fpea = ColumnDataSource(_fpea)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                y_range = [28.0, 28.5],                               \
                x_axis_type = 'datetime',                           \
                output_backend = "webgl",                             \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True
    p.title.text = "POWER FPE"
    pf.add_basic_layout(p)

    # add a line renderer with legend and line thickness
    scat1 = p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Power FPEA", source = fpea)
    p.line(x = "start_time", y = "average", color = 'orange', legend = "Power FPEA", source = fpea)

    err_xs = []
    err_ys = []

    for index, item in _fpea.iterrows():
        err_xs.append((item['start_time'], item['start_time']))
        err_ys.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

    # plot them
    p.multi_line(err_xs, err_ys, color='orange', legend='Power FPEA')

    #activate HoverTool for scatter plot
    hover_tool = HoverTool( tooltips =
    [
        ('count', '@data_points'),
        ('mean', '@average'),
        ('deviation', '@deviation'),

    ], renderers = [scat1])
    p.tools.append(hover_tool)

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def currents(conn, start, end):
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
                plot_height = 500,
                y_range = [0,1.1],
                x_axis_type = 'datetime',
                output_backend = "webgl",
                x_axis_label = 'Date', y_axis_label = 'Current (A)')

    p.grid.visible = True
    p.title.text = "FPE & ICE Currents"
    pf.add_basic_layout(p)

    a = pf.add_to_plot(p, "ICE Current idle", "SE_ZIMIRICEA_IDLE", start, end, conn, color = "red")
    b = pf.add_to_plot(p, "ICE Current HV on", "SE_ZIMIRICEA_HV_ON", start, end, conn, color = "orange")
    c = pf.add_to_plot(p, "FPE Current", "SE_ZIMIRFPEA", start, end, conn, color = "brown")

    pf.add_hover_tool(p,[a,b,c])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p


def power_plots(conn, start, end):


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
        <td>POWER ICE</td>
        <td>SE_ZIMIRICEA * 30V (static)</td>
        <td>Primary power consumption ICE side A - HV on and IDLE</td>
      </tr>
      <tr>
        <td>POWER FPE</td>
        <td>SE_ZIMIRIFPEA * 30V (static)</td>
        <td>Primary power consumption FPE side A</td>
      </tr>
      <tr>
        <td>FPE & ICE Voltages/Currents</td>
        <td>SE_ZIMIRFPEA<br>
            SE_ZIMIRCEA
            *INPUT VOLTAGE* (missing)</td>
        <td>Supply voltage and current ICE/FPE</td>
      </tr>
    </table>
    </body>
    """, width=1100)

    plot1 = power_ice(conn, start, end)
    plot2 = power_fpea(conn, start, end)
    plot3 = currents(conn, start, end)

    layout = column(descr, plot1, plot2, plot3)

    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "POWER")

    return tab
