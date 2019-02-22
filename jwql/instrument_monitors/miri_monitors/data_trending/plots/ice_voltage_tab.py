import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource
from bokeh.layouts import WidgetBox, gridplot

import pandas as pd

import numpy as np

from astropy.time import Time


def volt4(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [4.2,5],                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "ICE_SEC_VOLT4"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    # add a line renderer with legend and line thickness

    pf.add_to_plot(p, "Volt4 Idle", "IMIR_HK_ICE_SEC_VOLT4_IDLE", start, end, conn, color = "orange")
    pf.add_to_plot(p, "Volt4 Hv on", "IMIR_HK_ICE_SEC_VOLT4_HV_ON" ,start, end, conn, color = "red")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt1_3(conn, start, end):
    #query data from database
    _volt2 = pd.read_sql_query("SELECT * FROM IMIR_HK_ICE_SEC_VOLT2 ORDER BY start_time", conn)
    volt2_reg = pd.DataFrame({'reg' : pf.pol_regression(_volt2['start_time'],_volt2['average'],3)})
    _volt2 = pd.concat([_volt2, volt2_reg], axis=1)

    _volt2['start_time'] = pd.to_datetime( Time(_volt2['start_time'], format = "mjd").datetime )

    #set column data source
    volt2 = ColumnDataSource(_volt2)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [30,50],                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "ICE_SEC_VOLT1-3"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    # add a line renderer with legend and line thickness
    pf.add_to_plot(p, "Volt1", "IMIR_HK_ICE_SEC_VOLT1" ,start, end, conn, color = "red")
    pf.add_to_plot(p, "Volt3", "IMIR_HK_ICE_SEC_VOLT3" ,start, end, conn, color = "purple")

    p.extra_y_ranges = {"volt2": Range1d(start=70, end=82)}
    p.scatter(x = "start_time", y = "average", color = 'blue', y_range_name = 'volt2', legend = "Volt 2", source = volt2)
    p.line(x = "start_time", y = "reg", color = 'blue', y_range_name = 'volt2',  legend = "Volt 2", source = volt2)
    p.add_layout(LinearAxis(y_range_name = "volt2", axis_label = "Voltage (V) -Volt2", axis_label_text_color = "blue"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def pos_volt(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [280,300],                                \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (mV)')

    p.grid.visible = True
    p.title.text = "Wheel Sensor Voltage"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    pf.add_to_plot(p, "FW", "IMIR_HK_FW_POS_VOLT" ,start, end, conn, color = "red")
    pf.add_to_plot(p, "GW14", "IMIR_HK_GW14_POS_VOLT" ,start, end, conn, color = "purple")
    pf.add_to_plot(p, "GW23", "IMIR_HK_GW23_POS_VOLT" ,start, end, conn, color = "orange")
    pf.add_to_plot(p, "CCC", "IMIR_HK_CCC_POS_VOLT" ,start, end, conn, color = "firebrick")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt_plots(conn, start, end):

    plot1 = volt1_3(conn, start, end)
    plot2 = volt4(conn, start, end)
    plot3 = pos_volt(conn, start, end)

    layout = gridplot([[plot2, plot1], [plot3, None]], merge_tools = False)


    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "ICE/WHEEL VOLTAGE")

    return tab
