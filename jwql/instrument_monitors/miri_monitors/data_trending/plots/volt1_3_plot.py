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
    volt1 = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT1', columns)
    volt2 = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT2', columns)
    volt3 = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT3', columns)

    #append data from query to numpy arrays
    volt1_time, volt1_val, volt1_dev = pf.split_data(volt1)
    volt2_time, volt2_val, volt2_dev = pf.split_data(volt2)
    volt3_time, volt3_val, volt3_dev = pf.split_data(volt3)

    #polynomial regression
    volt1_reg = pf.pol_regression(volt1_time, volt1_val, 3)
    volt2_reg = pf.pol_regression(volt2_time, volt2_val, 3)
    volt3_reg = pf.pol_regression(volt3_time, volt3_val, 3)

    #convert time mjd format to a more readable format
    volt1_time = Time(volt1_time, format="mjd").datetime
    volt2_time = Time(volt2_time, format="mjd").datetime
    volt3_time = Time(volt3_time, format="mjd").datetime

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range = [30,50],                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Voltage (V)')

    p.grid.visible = True

    # configure visual properties on a plotś title attribute
    p.title.text = "ICE_SEC_VOLT1-3"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"
    #p.xgrid.grid_line_color = '#efefef'

    p.extra_y_ranges = {"volt2": Range1d(start=70, end=82)}

    # add a line renderer with legend and line thickness
    p.scatter(volt1_time, volt1_val, color = 'orange', legend = "Volt1")
    p.scatter(volt2_time, volt2_val, color = 'firebrick', legend = "Volt2", y_range_name = 'volt2')
    p.scatter(volt3_time, volt3_val, color = 'red', legend = "Volt3")


    p.line(volt1_time, volt1_reg , color = 'green')
    p.line(volt2_time, volt2_reg , color = 'blue', y_range_name = 'volt2')
    p.line(volt3_time, volt3_reg , color = 'navy')

    p.add_layout(LinearAxis(y_range_name = "volt2"), 'right')


    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p
