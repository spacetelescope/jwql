import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource
from bokeh.layouts import WidgetBox, gridplot

import pandas as pd

import numpy as np

from astropy.time import Time

#small function for a polynomal regression
def pol_regression(x, y, rank):
    z = np.polyfit(x, y, rank)
    f = np.poly1d(z)
    y_poly = f(x)
    return y_poly


def add_to_plot(p, legend, mnemonic, conn, color="red"):

    sql_command = "SELECT * FROM "+mnemonic+" ORDER BY start_time"
    temp = pd.read_sql_query(sql_command, conn)

    reg = pd.DataFrame({'reg' : pol_regression(temp['start_time'], temp['average'],3)})
    temp = pd.concat([temp, reg], axis=1)

    temp['start_time'] = pd.to_datetime( Time(temp['start_time'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    p.line(x = "start_time", y = "reg", color = color, legend = legend, source = plot_data)
    p.scatter(x = "start_time", y = "average", color = color, legend = legend, source = plot_data)




def volt4(conn):

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

    add_to_plot(p, "Volt4 Idle", "IMIR_HK_ICE_SEC_VOLT4_IDLE", conn, color = "orange")
    add_to_plot(p, "Volt4 Hv on", "IMIR_HK_ICE_SEC_VOLT4_HV_ON" , conn, color = "red")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt1_3(conn):
    #query data from database
    _volt2 = pd.read_sql_query("SELECT * FROM IMIR_HK_ICE_SEC_VOLT2 ORDER BY start_time", conn)
    volt2_reg = pd.DataFrame({'reg' : pol_regression(_volt2['start_time'],_volt2['average'],3)})
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
    add_to_plot(p, "Volt1", "IMIR_HK_ICE_SEC_VOLT1" , conn, color = "red")
    add_to_plot(p, "Volt3", "IMIR_HK_ICE_SEC_VOLT3" , conn, color = "purple")

    p.extra_y_ranges = {"volt2": Range1d(start=70, end=82)}
    p.scatter(x = "start_time", y = "average", color = 'purple', y_range_name = 'volt2', legend = "Volt 2", source = volt2)
    p.line(x = "start_time", y = "reg", color = 'purple', y_range_name = 'volt2',  legend = "Volt 2", source = volt2)
    p.add_layout(LinearAxis(y_range_name = "volt2"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def pos_volt(conn):

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

    add_to_plot(p, "FW", "IMIR_HK_FW_POS_VOLT" , conn, color = "red")
    add_to_plot(p, "GW14", "IMIR_HK_GW14_POS_VOLT" , conn, color = "purple")
    add_to_plot(p, "GW23", "IMIR_HK_GW23_POS_VOLT" , conn, color = "orange")
    add_to_plot(p, "CCC", "IMIR_HK_CCC_POS_VOLT" , conn, color = "firebrick")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt_plots(conn):

    plot1 = volt1_3(conn)
    plot2 = volt4(conn)
    plot3 = pos_volt(conn)

    layout = gridplot([[plot2, plot1], [plot3, None]], merge_tools = False)


    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "ICE/WHEEL VOLTAGE")

    return tab
