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


def volt4(conn):
    #query data from database
    _idle = pd.read_sql_query("SELECT * FROM IMIR_HK_ICE_SEC_VOLT4_IDLE ORDER BY start_time", conn)
    _hv = pd.read_sql_query("SELECT * FROM IMIR_HK_ICE_SEC_VOLT4_HV_ON ORDER BY start_time", conn)

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
    p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Volt4 idle", source = idle)
    p.scatter(x = "start_time", y = "average", color = 'red', legend = "Volt4 hv on", source = hv)
    p.line(x = "start_time", y = "reg", color = 'orange', legend = "Volt4 idle", source = idle)
    p.line(x = "start_time", y = "reg", color = 'red', legend = "Volt4 hv on", source = hv)

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt1_3(conn):
    #query data from database
    _volt1 = pd.read_sql_query("SELECT * FROM IMIR_HK_ICE_SEC_VOLT1 ORDER BY start_time", conn)
    _volt2 = pd.read_sql_query("SELECT * FROM IMIR_HK_ICE_SEC_VOLT2 ORDER BY start_time", conn)
    _volt3 = pd.read_sql_query("SELECT * FROM IMIR_HK_ICE_SEC_VOLT3 ORDER BY start_time", conn)

    volt1_reg = pd.DataFrame({'reg' : pol_regression(_volt1['start_time'],_volt1['average'],3)})
    volt2_reg = pd.DataFrame({'reg' : pol_regression(_volt2['start_time'],_volt2['average'],3)})
    volt3_reg = pd.DataFrame({'reg' : pol_regression(_volt3['start_time'],_volt3['average'],3)})

    _volt1 = pd.concat([_volt1, volt1_reg], axis=1)
    _volt2 = pd.concat([_volt2, volt2_reg], axis=1)
    _volt3 = pd.concat([_volt3, volt3_reg], axis=1)

    _volt1['start_time'] = pd.to_datetime( Time(_volt1['start_time'], format = "mjd").datetime )
    _volt2['start_time'] = pd.to_datetime( Time(_volt2['start_time'], format = "mjd").datetime )
    _volt3['start_time'] = pd.to_datetime( Time(_volt3['start_time'], format = "mjd").datetime )

    #set column data source
    volt1 = ColumnDataSource(_volt1)
    volt2 = ColumnDataSource(_volt2)
    volt3 = ColumnDataSource(_volt3)

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
    p.scatter(x = "start_time", y = "average", color = 'red', legend = "Volt 1", source = volt1)
    p.line(x = "start_time", y = "reg", color = 'red', legend = "Volt 1", source = volt1)

    p.scatter(x = "start_time", y = "average", color = 'orange', legend = "Volt 3", source = volt3)
    p.line(x = "start_time", y = "reg", color = 'orange', legend = "Volt 3", source = volt3)

    p.extra_y_ranges = {"volt2": Range1d(start=70, end=82)}
    p.scatter(x = "start_time", y = "average", color = 'purple', y_range_name = 'volt2', legend = "Volt 2", source = volt2)
    p.line(x = "start_time", y = "reg", color = 'purple', y_range_name = 'volt2',  legend = "Volt 2", source = volt2)
    p.add_layout(LinearAxis(y_range_name = "volt2"), 'right')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def pos_volt(conn):
    #query data from database
    _fw = pd.read_sql_query("SELECT * FROM IMIR_HK_FW_POS_VOLT ORDER BY start_time", conn)
    _gw14 = pd.read_sql_query("SELECT * FROM IMIR_HK_GW14_POS_VOLT ORDER BY start_time", conn)
    _gw23 = pd.read_sql_query("SELECT * FROM IMIR_HK_GW23_POS_VOLT ORDER BY start_time", conn)
    _ccc = pd.read_sql_query("SELECT * FROM IMIR_HK_CCC_POS_VOLT ORDER BY start_time", conn)

    fw_reg = pd.DataFrame({'reg' : pol_regression(_fw['start_time'],_fw['average'],3)})
    gw14_reg = pd.DataFrame({'reg' : pol_regression(_gw14['start_time'],_gw14['average'],3)})
    gw23_reg = pd.DataFrame({'reg' : pol_regression(_gw23['start_time'],_gw23['average'],3)})
    ccc_reg = pd.DataFrame({'reg' : pol_regression(_ccc['start_time'],_ccc['average'],3)})

    _fw = pd.concat([_fw, fw_reg], axis=1)
    _gw14 = pd.concat([_gw14, gw14_reg], axis=1)
    _gw23 = pd.concat([_gw23, gw23_reg], axis=1)
    _ccc = pd.concat([_gw23, gw23_reg], axis=1)

    _fw['start_time'] = pd.to_datetime( Time(_fw['start_time'], format = "mjd").datetime )
    _gw14['start_time'] = pd.to_datetime( Time(_gw14['start_time'], format = "mjd").datetime )
    _gw23['start_time'] = pd.to_datetime( Time(_gw23['start_time'], format = "mjd").datetime )
    _ccc['start_time'] = pd.to_datetime( Time(_ccc['start_time'], format = "mjd").datetime )

    #set column data source
    fw = ColumnDataSource(_fw)
    gw14 = ColumnDataSource(_gw14)
    gw23 = ColumnDataSource(_gw23)
    ccc = ColumnDataSource(_ccc)

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

    # add a line renderer with legend and line thickness
    p.scatter(x = "start_time", y = "average", color = 'red', legend = "FW", source = fw)
    p.line(x = "start_time", y = "reg", color = 'red', legend = "FW", source = fw)

    p.scatter(x = "start_time", y = "average", color = 'orange', legend = "GW14", source = gw14)
    p.line(x = "start_time", y = "reg", color = 'orange', legend = "GW14", source = gw14)

    p.scatter(x = "start_time", y = "average", color = 'purple', legend = "GW23", source = gw23)
    p.line(x = "start_time", y = "reg", color = 'purple', legend = "GW23", source = gw23)

    p.scatter(x = "start_time", y = "average", color = 'firebrick', legend = "CCC", source = ccc)
    p.line(x = "start_time", y = "reg", color = 'firebrick', legend = "CCC", source = ccc)

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p

def volt_plots(conn):

    plot1 = volt1_3(conn)
    plot2 = volt4(conn)
    plot3 = pos_volt(conn)

    layout = gridplot([[plot2, plot1], [plot3, None]], merge_tools = False)


    #layout_volt = row(volt4, volt1_3)
    tab = Panel(child = layout, title = "VOLTAGE")

    return tab
