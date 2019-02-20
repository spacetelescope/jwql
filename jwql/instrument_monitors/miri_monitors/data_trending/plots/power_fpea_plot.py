import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs

import numpy as np

from astropy.time import Time


def power_fpea(conn):
    #query data from database
    columns = ('start_time, average, deviation')
    curr = sql.query_data(conn, 'SE_ZIMIRFPEA', columns)

    voltage = 30

    #append data from query to numpy arrays
    curr_time, curr_val, curr_dev = pf.split_data(curr)
    power = curr_val * voltage

    #polynomial regression
    power_reg = pf.pol_regression(curr_time, power, 3)

    #convert time mjd format to a more readable format
    time = Time(curr_time, format="mjd").datetime

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,wheel_zoom,box_zoom,reset,save",       \
                toolbar_location = "above",                         \
                plot_width = 560,                                   \
                plot_height = 500,                                  \
                y_range =[28, 28.7],                              \
                x_axis_type = 'datetime',                           \
                x_axis_label = 'Date', y_axis_label='Power (W)')

    p.grid.visible = True

    # configure visual properties on a plotś title attribute
    p.title.text="POWER FPEA"
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"

    p.background_fill_color = "#efefef"
    #p.xgrid.grid_line_color = '#efefef'

    # add a line renderer with legend and line thickness
    p.scatter(time, power, color = 'orange', legend = "Power FPEA")

    p.line(time, power_reg , color = 'green', legend = "Power FPEA regression")

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    return p
