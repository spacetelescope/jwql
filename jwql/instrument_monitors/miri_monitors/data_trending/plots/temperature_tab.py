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


def cryo(conn, start, end):

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
    pf.add_basic_layout(p)

    pf.add_to_plot(p, "T1P", "IGDP_MIR_ICE_T1P_CRYO", start, end, conn, color = "brown")
    pf.add_to_plot(p, "T2R", "IGDP_MIR_ICE_T2R_CRYO", start, end, conn, color = "burlywood")
    pf.add_to_plot(p, "T3LW", "IGDP_MIR_ICE_T3LW_CRYO", start, end, conn, color = "cadetblue")
    pf.add_to_plot(p, "T4SW", "IGDP_MIR_ICE_T4SW_CRYO", start, end, conn, color = "chartreuse")
    pf.add_to_plot(p, "T5IMG", "IGDP_MIR_ICE_T5IMG_CRYO", start, end, conn, color = "chocolate")
    pf.add_to_plot(p, "T6DECK", "IGDP_MIR_ICE_T6DECKCRYO", start, end, conn, color = "coral")
    pf.add_to_plot(p, "T7IOC", "IGDP_MIR_ICE_T7IOC_CRYO", start, end, conn, color = "darkorange")
    pf.add_to_plot(p, "FW", "IGDP_MIR_ICE_FW_CRYO", start, end, conn, color = "crimson")
    pf.add_to_plot(p, "CCC", "IGDP_MIR_ICE_CCC_CRYO", start, end, conn, color = "cyan")
    pf.add_to_plot(p, "GW14", "IGDP_MIR_ICE_GW14_CRYO", start, end, conn, color = "darkblue")
    pf.add_to_plot(p, "GW23", "IGDP_MIR_ICE_GW23_CRYO", start, end, conn, color = "darkgreen")
    pf.add_to_plot(p, "POMP", "IGDP_MIR_ICE_POMP_CRYO", start, end, conn, color = "darkmagenta")
    pf.add_to_plot(p, "POMR", "IGDP_MIR_ICE_POMR_CRYO", start, end, conn, color = "darkcyan")
    pf.add_to_plot(p, "IFU", "IGDP_MIR_ICE_IFU_CRYO", start, end, conn, color = "cornflowerblue")
    pf.add_to_plot(p, "IMG", "IGDP_MIR_ICE_IMG_CRYO", start, end, conn, color = "orange")

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def temp(conn, start, end):

    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM IGDP_MIR_ICE_INTER_TEMP WHERE start_time BETWEEN "+start_str+" AND "+end_str+" ORDER BY start_time"
    temp = pd.read_sql_query(sql_c, conn)

    temp['average']+= 273.15
    reg = pd.DataFrame({'reg' : pf.pol_regression(temp['start_time'], temp['average'],3)})
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
                x_axis_label = 'Date', y_axis_label = 'Temperature (K)')

    p.grid.visible = True
    p.title.text = "TEMP"
    pf.add_basic_layout(p)

    p.line(x = "start_time", y = "reg", color = "brown", legend = "Internal Temp.", source = plot_data)
    p.scatter(x = "start_time", y = "average", color = "brown", legend = "Internal Temp.", source = plot_data)

    pf.add_to_plot(p, "ICE IEC", "ST_ZTC1MIRIA", start, end, conn, color = "burlywood")
    pf.add_to_plot(p, "FPE IEC", "ST_ZTC2MIRIA", start, end, conn, color = "cadetblue")
    pf.add_to_plot(p, "FPE PDU", "IMIR_PDU_TEMP", start, end, conn, color = "chartreuse")
    pf.add_to_plot(p, "Analog IC", "IMIR_IC_SCE_ANA_TEMP1", start, end, conn, color = "chocolate")
    pf.add_to_plot(p, "Analog SW", "IMIR_SW_SCE_ANA_TEMP1", start, end, conn, color = "coral")
    pf.add_to_plot(p, "Analog LW", "IMIR_LW_SCE_ANA_TEMP1", start, end, conn, color = "darkorange")
    pf.add_to_plot(p, "Digital IC", "IMIR_IC_SCE_DIG_TEMP", start, end, conn, color = "crimson")
    pf.add_to_plot(p, "Digital SW", "IMIR_SW_SCE_DIG_TEMP", start, end, conn, color = "cyan")
    pf.add_to_plot(p, "Digital LW", "IMIR_LW_SCE_DIG_TEMP", start, end, conn, color = "darkblue")

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def det(conn, start, end):

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
    pf.add_basic_layout(p)

    pf.add_to_plot(p, "Det. Temp. IC", "IGDP_MIR_IC_DET_TEMP", start, end, conn, color = "red")
    pf.add_to_plot(p, "Det. Temp. LW", "IGDP_MIR_LW_DET_TEMP", start, end, conn, color = "green")
    pf.add_to_plot(p, "Det. Temp. SW", "IGDP_MIR_SW_DET_TEMP", start, end, conn, color = "blue")

    p.legend.location = "bottom_right"
    p.legend.orientation = "horizontal"
    p.legend.click_policy = "hide"

    return p

def temperature_plots(conn, start, end):

    plot1 = cryo(conn, start, end)
    plot2 = temp(conn, start, end)
    plot3 = det(conn, start, end)


    layout = column(plot1, plot2, plot3)

    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "TEMPERATURE")

    return tab
