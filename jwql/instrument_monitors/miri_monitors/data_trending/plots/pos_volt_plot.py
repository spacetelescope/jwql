import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs

import numpy as np

from astropy.time import Time


def volt1_3(conn):
    #query data from database
    columns = ('start_time, average, deviation')
    fw_volt = sql.query_data(conn, 'IMIR_HK_FW_POS_VOLT', columns)
    gw14_volt = sql.query_data(conn, 'IMIR_HK_GW14_POS_VOLT', columns)
    gw23_volt = sql.query_data(conn, 'IMIR_HK_GW23_POS_VOLT', columns)
    ccc_volt = sql.query_data(conn, 'IMIR_HK_CCC_POS_VOLT', columns)

    #append data from query to numpy arrays
    fw_time, fw_val, fw_dev = pf.split_data(fw_volt)
    gw14_time, gw14_val, gw14_dev = pf.split_data(gw14_volt)
    gw23_time, gw23_val, gw23_dev = pf.split_data(gw23_volt)
    ccc_time, ccc_val, ccc_dev = pf.split_data(ccc_volt)


    #polynomial regression
    fw_reg = pf.pol_regression(fw_time, fw_val, 3)
    gw14_reg = pf.pol_regression(gw14_time, gw14_val, 3)
    gw23_reg = pf.pol_regression(gw23_time, gw23_val, 3)
    ccc_reg = pf.pol_regression(ccc_time, ccc_val, 3)


    #convert time mjd format to a more readable format
    fw_time = Time(fw_time, format="mjd").datetime
    gw14_time = Time(gw14_time, format="mjd").datetime
    gw23_time = Time(gw23_time, format="mjd").datetime
    ccc_time = Time(ccc_time, format="mjd").datetime

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 600,                                   \
                plot_height = 600,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True

    # configure visual properties on a plotś title attribute
    p.title.text = "Wheel Voltages"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"
    #p.xgrid.grid_line_color = '#efefef'


    # add a line renderer with legend and line thickness
    p.scatter(fw_time, fw_val, color = 'orange', legend = "FW Volt")
    p.scatter(gw14_time, gw14_val, color = 'red', legend = "FW Volt")
    p.scatter(gw23_time, gw23_val, color = 'firebrick', legend = "FW Volt")
    p.scatter(ccc_time, ccc_val, color = 'yellow', legend = "FW Volt")

    p.scatter(volt2_time, volt2_val, color = 'firebrick', legend = "Volt2", y_range_name = 'volt2')
    p.scatter(volt3_time, volt3_val, color = 'red', legend = "Volt3")


    p.line(volt1_time, volt1_reg , color = 'green')
    p.line(volt2_time, volt2_reg , color = 'blue', y_range_name = 'volt2')
    p.line(volt3_time, volt3_reg , color = 'navy')

    p.add_layout(LinearAxis(y_range_name = "volt2"), 'right')


    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    script, div = components(p)
    plot_data = [div, script]

    return plot_data
