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


def add_to_plot(p, legend, mnemonic, conn, y_axis='default', color="red"):

    sql_command = "SELECT * FROM "+mnemonic+" ORDER BY start_time"
    temp = pd.read_sql_query(sql_command, conn)

    reg = pd.DataFrame({'reg' : pol_regression(temp['start_time'], temp['average'],3)})
    temp = pd.concat([temp, reg], axis=1)

    temp['start_time'] = pd.to_datetime( Time(temp['start_time'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    p.line(x = "start_time", y = "reg", y_range_name = y_axis, color = color, legend = legend, source = plot_data)
    p.scatter(x = "start_time", y = "average", y_range_name = y_axis, color = color, legend = legend, source = plot_data)


def vdetcom(conn):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VDETCOM"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"


    add_to_plot(p, "VDETCOM IC", "IGDP_MIR_IC_V_VDETCOM", conn, color = "red")
    add_to_plot(p, "VDETCOM SW", "IGDP_MIR_SW_V_VDETCOM", conn, color = "orange")
    add_to_plot(p, "VDETCOM LW", "IGDP_MIR_LW_V_VDETCOM", conn, color = "green")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vssout(conn):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VSSOUT"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"


    add_to_plot(p, "VSSOUT IC", "IGDP_MIR_IC_V_VSSOUT", conn, color = "red")
    add_to_plot(p, "VSSOUT SW", "IGDP_MIR_SW_V_VSSOUT", conn, color = "orange")
    add_to_plot(p, "VSSOUT LW", "IGDP_MIR_LW_V_VSSOUT", conn, color = "green")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vrstoff(conn):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VRSTOFF"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"


    add_to_plot(p, "VRSTOFF IC", "IGDP_MIR_IC_V_VRSTOFF", conn, color = "red")
    add_to_plot(p, "VRSTOFF SW", "IGDP_MIR_SW_V_VRSTOFF", conn, color = "orange")
    add_to_plot(p, "VRSTOFF LW", "IGDP_MIR_LW_V_VRSTOFF", conn, color = "green")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vp(conn):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VP"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    add_to_plot(p, "VP IC", "IGDP_MIR_IC_V_VP", conn, color = "red")
    add_to_plot(p, "VP SW", "IGDP_MIR_SW_V_VP", conn, color = "orange")
    add_to_plot(p, "VP LW", "IGDP_MIR_LW_V_VP", conn, color = "green")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def vdduc(conn):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Det.Bias VDDUC"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    add_to_plot(p, "VDDUC IC", "IGDP_MIR_IC_V_VDDUC", conn, color = "red")
    add_to_plot(p, "VDDUC SW", "IGDP_MIR_SW_V_VDDUC", conn, color = "orange")
    add_to_plot(p, "VDDUC LW", "IGDP_MIR_LW_V_VDDUC", conn, color = "green")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.orientation = "horizontal"

    return p

def bias_plots(conn):

    plot1 = vdetcom(conn)
    plot2 = vssout(conn)
    plot3 = vrstoff(conn)
    plot4 = vp(conn)
    plot5 = vdduc(conn)

    layout = gridplot([ [plot2, plot1],         \
                        [plot3, plot4],         \
                        [plot5, None]], merge_tools=False)

    tab = Panel(child = layout, title = "BIAS")

    return tab
