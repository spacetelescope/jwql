import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource
from bokeh.layouts import column, row, WidgetBox

import pandas as pd
import numpy as np

from astropy.time import Time


def add_to_wplot(p, legend, mnemonic, start, end, conn, nominal, color = "red"):

    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM "+mnemonic+" WHERE timestamp BETWEEN "+start_str+" AND "+end_str+" ORDER BY timestamp"
    temp = pd.read_sql_query(sql_c, conn)

    #normalize values
    temp['value'] /= nominal
    temp['value'] -= 1

    temp['timestamp'] = pd.to_datetime( Time(temp['timestamp'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    p.line(x = "timestamp", y = "value", color = color, legend = legend, source = plot_data)

def gw14(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'ratio (normalized)')

    p.grid.visible = True
    p.title.text = "GW14 Ratio"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    add_to_wplot(p, "SHORT", "IMIR_HK_GW14_POS_RATIO_SHORT", start, end, conn, mn.gw14_nominals['SHORT'], color = "green")
    add_to_wplot(p, "MEDIUM", "IMIR_HK_GW14_POS_RATIO_MEDIUM", start, end, conn, mn.gw14_nominals['MEDIUM'], color = "red")
    add_to_wplot(p, "LONG", "IMIR_HK_GW14_POS_RATIO_LONG", start, end, conn, mn.gw14_nominals['LONG'], color = "blue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    #p.legend.orientation = "horizontal"

    return p

def gw23(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'ratio (normalized)')

    p.grid.visible = True
    p.title.text = "GW23 Ratio"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    add_to_wplot(p, "SHORT", "IMIR_HK_GW23_POS_RATIO_SHORT", start, end, conn, mn.gw23_nominals['SHORT'], color = "green")
    add_to_wplot(p, "MEDIUM", "IMIR_HK_GW23_POS_RATIO_MEDIUM", start, end, conn, mn.gw23_nominals['MEDIUM'], color = "red")
    add_to_wplot(p, "LONG", "IMIR_HK_GW23_POS_RATIO_LONG", start, end, conn, mn.gw23_nominals['LONG'], color = "blue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    #p.legend.orientation = "horizontal"

    return p

def ccc(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'ratio (normalized)')

    p.grid.visible = True
    p.title.text = "CCC Ratio"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    #add_to_wplot(p, "LOCKED", "IMIR_HK_CCC_POS_RATIO_LOCKED", start, end, conn, mn.ccc_nominals['LOCKED'], color = "green")
    add_to_wplot(p, "OPEN", "IMIR_HK_CCC_POS_RATIO_OPEN", start, end, conn, mn.ccc_nominals['OPEN'], color = "red")
    add_to_wplot(p, "CLOSED", "IMIR_HK_CCC_POS_RATIO_CLOSED", start, end, conn, mn.ccc_nominals['CLOSED'], color = "blue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    #p.legend.orientation = "horizontal"

    return p

def fw(conn, start, end):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 1000,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True
    p.title.text = "Filterwheel Ratio"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    add_to_wplot(p, "FND", "IMIR_HK_FW_POS_RATIO_FND", start, end, conn, mn.fw_nominals['FND'], color = "green")
    add_to_wplot(p, "OPAQUE", "IMIR_HK_FW_POS_RATIO_OPAQUE", start, end, conn, mn.fw_nominals['OPAQUE'], color = "red")
    add_to_wplot(p, "F1000W", "IMIR_HK_FW_POS_RATIO_F1000W", start, end, conn, mn.fw_nominals['F1000W'], color = "blue")
    add_to_wplot(p, "F1130W", "IMIR_HK_FW_POS_RATIO_F1130W", start, end, conn, mn.fw_nominals['F1130W'], color = "orange")
    add_to_wplot(p, "F1280W", "IMIR_HK_FW_POS_RATIO_F1280W", start, end, conn, mn.fw_nominals['F1280W'], color = "firebrick")
    add_to_wplot(p, "P750L", "IMIR_HK_FW_POS_RATIO_P750L", start, end, conn, mn.fw_nominals['P750L'], color = "cyan")
    add_to_wplot(p, "F1500W", "IMIR_HK_FW_POS_RATIO_F1500W", start, end, conn, mn.fw_nominals['F1500W'], color = "magenta")
    add_to_wplot(p, "F1800W", "IMIR_HK_FW_POS_RATIO_F1800W", start, end, conn, mn.fw_nominals['F1800W'], color = "burlywood")
    add_to_wplot(p, "F2100W", "IMIR_HK_FW_POS_RATIO_F2100W", start, end, conn, mn.fw_nominals['F2100W'], color = "cadetblue")
    add_to_wplot(p, "F560W", "IMIR_HK_FW_POS_RATIO_F560W", start, end, conn, mn.fw_nominals['F560W'], color = "chartreuse")
    add_to_wplot(p, "FLENS", "IMIR_HK_FW_POS_RATIO_FLENS", start, end, conn, mn.fw_nominals['FLENS'], color = "brown")
    add_to_wplot(p, "F2300C", "IMIR_HK_FW_POS_RATIO_F2300C", start, end, conn, mn.fw_nominals['F2300C'], color = "chocolate")
    add_to_wplot(p, "F770W", "IMIR_HK_FW_POS_RATIO_F770W", start, end, conn, mn.fw_nominals['F770W'], color = "darkorange")
    add_to_wplot(p, "F1550C", "IMIR_HK_FW_POS_RATIO_F1550C", start, end, conn, mn.fw_nominals['F1550C'], color = "darkgreen")
    add_to_wplot(p, "F2550W", "IMIR_HK_FW_POS_RATIO_F2550W", start, end, conn, mn.fw_nominals['F2550W'], color = "darkcyan")
    add_to_wplot(p, "F1140C", "IMIR_HK_FW_POS_RATIO_F1140C", start, end, conn, mn.fw_nominals['F1140C'], color = "darkmagenta")
    add_to_wplot(p, "F2550WR", "IMIR_HK_FW_POS_RATIO_F2550WR", start, end, conn, mn.fw_nominals['F2550WR'], color = "crimson")
    add_to_wplot(p, "F1065C", "IMIR_HK_FW_POS_RATIO_F1065C", start, end, conn, mn.fw_nominals['F1065C'], color = "cornflowerblue")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    #p.legend.orientation = "horizontal"

    return p


def wheel_ratios(conn, start, end):

    plot1 = fw(conn, start, end)
    plot2 = gw14(conn, start, end)
    plot3 = gw23(conn,  start, end)
    plot4 = ccc(conn, start, end)

    layout = column(plot1,plot2,plot3, plot4)

    tab = Panel(child = layout, title = "WHEEL RATIO")

    return tab
