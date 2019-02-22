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


def dig5(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [4.9,5.1],                                \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Dig. 5V"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"
    p.yaxis.axis_label_text_color = "red"

    p.extra_y_ranges = {"current": Range1d(start=2100, end=2500)}
    # add a line renderer with legend and line thickness

    pf.add_to_plot(p, "FPE Dig. 5V", "IMIR_PDU_V_DIG_5V", start, end, conn, color = "red")
    pf.add_to_plot(p, "FPE Dig. 5V Current", "IMIR_PDU_I_DIG_5V", start, end, conn, y_axis = "current", color = "blue")

    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def refdig(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [2.45,2.55],                              \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "2.5V Ref and FPE Dig."
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    pf.add_to_plot(p, "FPE Dig. 2.5V", "IMIR_SPW_V_DIG_2R5V", start, end, conn, color = "orange")
    pf.add_to_plot(p, "FPE PDU 2.5V REF", "IMIR_PDU_V_REF_2R5V", start, end, conn, color = "red")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana5(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [4.95,5.05],                              \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. 5V"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"
    p.yaxis.axis_label_text_color = "red"

    p.extra_y_ranges = {"current": Range1d(start=100, end=300)}
    # add a line renderer with legend and line thickness

    pf.add_to_plot(p, "FPE Ana. 5V", "IMIR_PDU_V_ANA_5V",start, end, conn, color = "red")
    pf.add_to_plot(p, "FPE Ana. 5V Current", "IMIR_PDU_I_ANA_5V",start, end, conn, y_axis = "current", color = "blue")

    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana5n(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [-4.85,-5.1],                             \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. N5V"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"
    p.yaxis.axis_label_text_color = "red"

    p.extra_y_ranges = {"current": Range1d(start=100, end=300)}
    # add a line renderer with legend and line thickness

    pf.add_to_plot(p, "FPE Ana. N5", "IMIR_PDU_V_ANA_N5V",start, end, conn, color = "red")
    pf.add_to_plot(p, "FPE Ana. N5 Current", "IMIR_PDU_I_ANA_N5V",start, end, conn, y_axis = "current", color = "blue")

    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana7(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [6.85, 7.1],                              \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. 7V"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"
    p.yaxis.axis_label_text_color = "red"

    p.extra_y_ranges = {"current": Range1d(start=300, end=500)}
    # add a line renderer with legend and line thickness

    pf.add_to_plot(p, "FPE Ana. 7V", "IMIR_PDU_V_ANA_7V",start, end, conn, color = "red")
    pf.add_to_plot(p, "FPE Ana. 7V Current", "IMIR_PDU_I_ANA_7V",start, end, conn, y_axis = "current", color = "blue")

    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def ana7n(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [-7.05, -6.85],                           \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "FPE Ana. N7V"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"
    p.yaxis.axis_label_text_color = "red"

    p.extra_y_ranges = {"current": Range1d(start=350, end=400)}
    # add a line renderer with legend and line thickness

    pf.add_to_plot(p, "FPE Dig. N7V", "IMIR_PDU_V_ANA_N7V",start, end, conn, color = "red")
    pf.add_to_plot(p, "FPE Ana. N7V Current", "IMIR_PDU_I_ANA_N7V",start, end, conn, y_axis = "current", color = "blue")

    p.add_layout(LinearAxis(y_range_name = "current", axis_label = "Current (mA)", axis_label_text_color = "blue"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p


def fpe_plots(conn, start, end):

    plot1 = dig5(conn, start, end)
    plot2 = refdig(conn, start, end)
    plot3 = ana5(conn, start, end)
    plot4 = ana5n(conn, start, end)
    plot5 = ana7(conn, start, end)
    plot6 = ana7n(conn, start, end)

    layout = gridplot([ [plot2, plot1],         \
                        [plot3, plot4],        \
                        [plot5, plot6]], merge_tools=False)

    tab = Panel(child = layout, title = "FPE VOLTAGE")

    return tab
