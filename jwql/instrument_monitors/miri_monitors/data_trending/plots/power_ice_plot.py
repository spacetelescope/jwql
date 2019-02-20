import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation
from bokeh.embed import components
from bokeh.layouts import column, row, WidgetBox
from bokeh.models import Panel
from bokeh.models.widgets import Tabs

import numpy as np

from astropy.time import Time

def power_ice(conn):

    #query data from database
    columns = ('start_time, average, deviation')
    curr_idle = sql.query_data(conn, 'SE_ZIMIRICEA_IDLE', columns)
    curr_hv = sql.query_data(conn, 'SE_ZIMIRICEA_HV_ON', columns)

    #set static voltage (MIRI VOLT not supplied)
    voltage = 30

    #append data from query to numpy arrays
    curr_idle_time, curr_idle_val, curr_idle_dev = pf.split_data(curr_idle)
    power_idle = curr_idle_val * voltage

    curr_hv_time, curr_hv_val , curr_hv_dev = pf.split_data(curr_hv)
    power_hv = curr_hv_val * voltage

    #prepare ploynom regression
    power_hv_reg = pf.pol_regression(curr_hv_time, power_hv, 3)
    power_idle_reg = pf.pol_regression(curr_idle_time, power_idle, 3)

    idle_time = Time(curr_idle_time, format = "mjd").datetime
    hv_time = Time(curr_hv_time, format = "mjd").datetime

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True

    # configure visual properties on a plotś title attribute
    p.title.text="POWER ICE"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"

    p.background_fill_color = "#efefef"
    #p.xgrid.grid_line_color = '#efefef'

    # add a line renderer with legend and line thickness
    p.scatter(idle_time, power_idle, color = 'red', legend = "Power idle")
    p.scatter(hv_time, power_hv, color = 'orange', legend = "Power HV on")

    p.line(hv_time, power_hv_reg , color = 'green', legend = "HV regression")
    p.line(idle_time, power_idle_reg, color = 'blue', legend = "Idle regression")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p
