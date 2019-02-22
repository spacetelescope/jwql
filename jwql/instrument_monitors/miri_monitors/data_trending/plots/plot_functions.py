import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource, HoverTool

import pandas as pd
import numpy as np

from astropy.time import Time


def pol_regression(x, y, rank):
    z = np.polyfit(x, y, rank)
    f = np.poly1d(z)
    y_poly = f(x)
    return y_poly


def add_to_plot(p, legend, mnemonic, start, end, conn, y_axis= "default", color="red"):

    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM "+mnemonic+" WHERE start_time BETWEEN "+start_str+" AND "+end_str+" ORDER BY start_time"
    temp = pd.read_sql_query(sql_c, conn)

    reg = pd.DataFrame({'reg' : pol_regression(temp['start_time'], temp['average'],3)})
    temp = pd.concat([temp, reg], axis=1)

    temp['start_time'] = pd.to_datetime( Time(temp['start_time'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    p.line(x = "start_time", y = "reg", color = color, y_range_name=y_axis, legend = legend, source = plot_data)
    p.scatter(x = "start_time", y = "average", color = color, y_range_name=y_axis, legend = legend, source = plot_data)

def add_basic_layout(p):
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    p.xaxis.axis_label_text_font_size = "14pt"
    p.xaxis.axis_label_text_color='#2D353C'
    p.yaxis.axis_label_text_font_size = "14pt"
    p.yaxis.axis_label_text_color='#2D353C'
