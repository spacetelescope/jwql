import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
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

    idle_reg = pd.DataFrame({'reg' : pf.pol_regression(_idle['start_time'],_idle['average'],3)})
    hv_reg = pd.DataFrame({'reg' : pf.pol_regression(_hv['start_time'],_hv['average'],3)})

    _idle = pd.concat([_idle, idle_reg], axis=1)
    _hv = pd.concat([_hv, hv_reg], axis=1)

    _idle['start_time'] = pd.to_datetime( Time(_idle['start_time'], format = "mjd").datetime )
    _hv['start_time'] = pd.to_datetime( Time(_hv['start_time'], format = "mjd").datetime )

    #set column data source
    idle = ColumnDataSource(_idle)
    hv = ColumnDataSource(_hv)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                y_range=[5,14],                                     \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True
    p.title.text = "POWER ICE"
    pf.add_basic_layout(p)

    # add a line renderer with legend and line thickness
    scat1=p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Power idle", source = idle)
    scat2=p.scatter(x = "start_time", y = "average", color = 'red', legend = "Power hv on", source = hv)
    p.line(x = "start_time", y = "reg", color = 'orange', legend = "Power idle", source = idle)
    p.line(x = "start_time", y = "reg", color = 'red', legend = "Power hv on", source = hv)

    #activate HoverTool for scatter plot
    hover_tool = HoverTool( tooltips =
    [
        ('count', '@data_points'),
        ('mean', '@average'),
        ('deviation', '@deviation'),

    ], renderers=[scat1,scat2])
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

    fpea_reg = pd.DataFrame({'reg' : pf.pol_regression(_fpea['start_time'],_fpea['average'],3)})
    _fpea = pd.concat([_fpea, fpea_reg], axis=1)

    _fpea['start_time'] = pd.to_datetime( Time(_fpea['start_time'], format = "mjd").datetime )

    #set column data source
    fpea = ColumnDataSource(_fpea)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                y_range=[28.0, 28.5],                               \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True
    p.title.text = "POWER FPE"
    pf.add_basic_layout(p)

    # add a line renderer with legend and line thickness
    scat1=p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Power FPEA", source = fpea)
    p.line(x = "start_time", y = "reg", color = 'orange', legend = "Power FPEA", source = fpea)

    #activate HoverTool for scatter plot
    hover_tool = HoverTool( tooltips =
    [
        ('count', '@data_points'),
        ('mean', '@average'),
        ('deviation', '@deviation'),

    ], renderers=[scat1])
    p.tools.append(hover_tool)

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def power_plots(conn, start, end):

    plot1 = power_ice(conn, start, end)
    plot2 = power_fpea(conn, start, end)

    layout = column(plot1, plot2)

    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "POWER")

    return tab
