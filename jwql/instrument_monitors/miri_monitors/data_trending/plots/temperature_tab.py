import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
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


def add_to_plot(p, legend, mnemonic, conn, color="red"):

    sql_command = "SELECT * FROM "+mnemonic+" ORDER BY start_time"
    temp = pd.read_sql_query(sql_command, conn)

    reg = pd.DataFrame({'reg' : pol_regression(temp['start_time'], temp['average'],3)})
    temp = pd.concat([temp, reg], axis=1)

    temp['start_time'] = pd.to_datetime( Time(temp['start_time'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    p.line(x = "start_time", y = "reg", color = color, legend = legend, source = plot_data)
    p.scatter(x = "start_time", y = "average", color = color, legend = legend, source = plot_data)


def cryo(conn):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 700,                                  \
                y_range = [5.8,6.4],
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'Temperature (K)')

    p.grid.visible = True
    p.title.text = "Cryo Temperatures"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    add_to_plot(p, "T1P", "IGDP_MIR_ICE_T1P_CRYO", conn, color = "brown")
    add_to_plot(p, "T2R", "IGDP_MIR_ICE_T2R_CRYO", conn, color = "burlywood")
    add_to_plot(p, "T3LW", "IGDP_MIR_ICE_T3LW_CRYO", conn, color = "cadetblue")
    add_to_plot(p, "T4SW", "IGDP_MIR_ICE_T4SW_CRYO", conn, color = "chartreuse")
    add_to_plot(p, "T5IMG", "IGDP_MIR_ICE_T5IMG_CRYO", conn, color = "chocolate")
    add_to_plot(p, "T6DECK", "IGDP_MIR_ICE_T6DECKCRYO", conn, color = "coral")
    add_to_plot(p, "T7IOC", "IGDP_MIR_ICE_T7IOC_CRYO", conn, color = "darkorange")
    add_to_plot(p, "FW", "IGDP_MIR_ICE_FW_CRYO", conn, color = "crimson")
    add_to_plot(p, "CCC", "IGDP_MIR_ICE_CCC_CRYO", conn, color = "cyan")
    add_to_plot(p, "GW14", "IGDP_MIR_ICE_GW14_CRYO", conn, color = "darkblue")
    add_to_plot(p, "GW23", "IGDP_MIR_ICE_GW23_CRYO", conn, color = "darkgreen")
    add_to_plot(p, "POMP", "IGDP_MIR_ICE_POMP_CRYO", conn, color = "darkmagenta")
    add_to_plot(p, "POMR", "IGDP_MIR_ICE_POMR_CRYO", conn, color = "darkcyan")
    add_to_plot(p, "IFU", "IGDP_MIR_ICE_IFU_CRYO", conn, color = "cornflowerblue")
    add_to_plot(p, "IMG", "IGDP_MIR_ICE_IMG_CRYO", conn, color = "orange")

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def temp(conn):

    temp = pd.read_sql_query("SELECT * FROM IGDP_MIR_ICE_INTER_TEMP ORDER BY start_time", conn)
    temp['average']+= 273
    reg = pd.DataFrame({'reg' : pol_regression(temp['start_time'], temp['average'],3)})
    temp = pd.concat([temp, reg], axis=1)

    temp['start_time'] = pd.to_datetime( Time(temp['start_time'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 700,                                  \
                y_range = [275,295],                             \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'Temperature')

    p.grid.visible = True
    p.title.text = "TEMP"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    p.line(x = "start_time", y = "reg", color = "brown", legend = "Internal Temp.", source = plot_data)
    p.scatter(x = "start_time", y = "average", color = "brown", legend = "Internal Temp.", source = plot_data)

    add_to_plot(p, "ICE IEC", "ST_ZTC1MIRIA", conn, color = "burlywood")
    add_to_plot(p, "FPE IEC", "ST_ZTC2MIRIA", conn, color = "cadetblue")
    add_to_plot(p, "FPE PDU", "IMIR_PDU_TEMP", conn, color = "chartreuse")
    add_to_plot(p, "Analog IC", "IMIR_IC_SCE_ANA_TEMP1", conn, color = "chocolate")
    add_to_plot(p, "Analog SW", "IMIR_SW_SCE_ANA_TEMP1", conn, color = "coral")
    add_to_plot(p, "Analog LW", "IMIR_LW_SCE_ANA_TEMP1", conn, color = "darkorange")
    add_to_plot(p, "Digital IC", "IMIR_IC_SCE_DIG_TEMP", conn, color = "crimson")
    add_to_plot(p, "Digital SW", "IMIR_SW_SCE_DIG_TEMP", conn, color = "cyan")
    add_to_plot(p, "Digital LW", "IMIR_LW_SCE_DIG_TEMP", conn, color = "darkblue")

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def det(conn):

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 1120,                                   \
                plot_height = 400,                                  \
                y_range = [6.395,6.41],                             \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label = 'Temperature (K)')

    p.grid.visible = True
    p.title.text = "Detector Temperature"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    add_to_plot(p, "Det. Temp. IC", "IGDP_MIR_IC_DET_TEMP", conn, color = "red")
    add_to_plot(p, "Det. Temp. LW", "IGDP_MIR_LW_DET_TEMP", conn, color = "green")
    add_to_plot(p, "Det. Temp. SW", "IGDP_MIR_SW_DET_TEMP", conn, color = "blue")

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def temperature_plots(conn):

    plot1 = cryo(conn)
    plot2 = temp(conn)
    plot3 = det(conn)


    layout = column(plot1, plot2, plot3)

    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "TEMPERATURE")

    return tab
