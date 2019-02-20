import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource
from bokeh.layouts import column, row, WidgetBox

import pandas as pd

import numpy as np

from astropy.time import Time

def pol_regression(x, y, rank):
    z = np.polyfit(x, y, rank)
    f = np.poly1d(z)
    y_poly = f(x)
    return y_poly


def power_ice(conn):
    #query data from database
    _idle = pd.read_sql_query("SELECT * FROM SE_ZIMIRICEA_IDLE ORDER BY start_time", conn)
    _hv = pd.read_sql_query("SELECT * FROM SE_ZIMIRICEA_HV_ON ORDER BY start_time", conn)

    voltage = 30
    _idle['average'] *= voltage
    _hv['average'] *= voltage

    idle_reg = pd.DataFrame({'reg' : pol_regression(_idle['start_time'],_idle['average'],3)})
    hv_reg = pd.DataFrame({'reg' : pol_regression(_hv['start_time'],_hv['average'],3)})

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
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True
    p.title.text = "POWER ICE"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    # add a line renderer with legend and line thickness
    p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Power idle", source = idle)
    p.scatter(x = "start_time", y = "average", color = 'red', legend = "Power hv on", source = hv)
    p.line(x = "start_time", y = "reg", color = 'orange', legend = "Power idle", source = idle)
    p.line(x = "start_time", y = "reg", color = 'red', legend = "Power hv on", source = hv)

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def power_fpea(conn):
    #query data from database
    _fpea = pd.read_sql_query("SELECT * FROM SE_ZIMIRFPEA ORDER BY start_time", conn)

    voltage = 30
    _fpea['average'] *= voltage

    fpea_reg = pd.DataFrame({'reg' : pol_regression(_fpea['start_time'],_fpea['average'],3)})

    _fpea = pd.concat([_fpea, fpea_reg], axis=1)

    _fpea['start_time'] = pd.to_datetime( Time(_fpea['start_time'], format = "mjd").datetime )

    #set column data source
    fpea = ColumnDataSource(_fpea)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True
    p.title.text = "POWER FPEA"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    # add a line renderer with legend and line thickness
    p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Power FPEA", source = fpea)
    p.line(x = "start_time", y = "reg", color = 'orange', legend = "Power FPEA", source = fpea)

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def power_plots(conn):

    plot1 = power_ice(conn)
    plot2 = power_fpea(conn)

    layout = row(plot1, plot2)

    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "POWER")

    return tab
