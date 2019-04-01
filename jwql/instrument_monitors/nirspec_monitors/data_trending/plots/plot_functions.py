#! /usr/bin/env python
"""Auxilary functions for plots

    Module holds functions that are used for several plots.


Authors
-------
    - Daniel Kühbacher

Use
---


Dependencies
------------

"""
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.sql_interface as sql
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource, HoverTool, DatetimeTickFormatter, DatetimeTicker, SingleIntervalTicker
from bokeh.models.formatters import TickFormatter
from bokeh.models.tools import PanTool, SaveTool

import pandas as pd
import numpy as np

from astropy.time import Time


def pol_regression(x, y, rank):
    ''' Calculate polynominal regression of certain rank
    Parameters
    ----------
    x : list
        x parameters for regression
    y : list
        y parameters for regression
    rank : int
        rank of regression
    Return
    ------
    y_poly : list
        regression y parameters
    '''
    z = np.polyfit(x, y, rank)
    f = np.poly1d(z)
    y_poly = f(x)
    return y_poly

def add_hover_tool(p, rend):
    ''' Append hover tool to plot
    parameters
    ----------
    p : bokeh figure
        declares where to append hover tool
    rend : list
        list of renderer to append hover tool
    '''

    from bokeh.models import HoverTool

    #activate HoverTool for scatter plot
    hover_tool = HoverTool( tooltips =
    [
        ('Name', '$name'),
        ('Count', '@data_points'),
        ('Mean', '@average'),
        ('Deviation', '@deviation'),
    ], renderers = rend)
    #append hover tool
    p.tools.append(hover_tool)

def add_limit_box(p, lower, upper, alpha = 0.1, color="green"):
    ''' Adds box to plot
    Parameters
    ----------
    p : bokeh figure
        declares where to append hover tool
    lower : float
        lower limit of box
    upper : float
        upper limit of box
    alpha : float
        transperency of box
    color : str
        filling color
    '''
    box = BoxAnnotation(bottom = lower, top = upper, fill_alpha = alpha, fill_color = color)
    p.add_layout(box)

def add_to_plot(p, legend, mnemonic, start, end, conn, y_axis= "default", color="red", err='y'):
    '''Add scatter and line to certain plot and activates hoover tool
    Parameters
    ----------
    p : bokeh object
        defines plot where line and scatter should be added
    legend : str
        will be showed in legend of plot
    mnemonic : str
        defines mnemonic to be plotted
    start : datetime
        sets start time for data query
    end : datetime
        sets end time for data query
    conn : DBobject
        connection object to database
    y_axis : str (default='default')
        used if secon y axis is provided
    color : str (default='dred')
        defines color for scatter and line plot
    Return
    ------
    scat : plot scatter object
        used for applying hovertools o plots
    '''

    #convert given start and end time to astropy time
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    #prepare and execute sql query
    sql_c = "SELECT * FROM "+mnemonic+" WHERE start_time BETWEEN "+start_str+" AND "+end_str+" ORDER BY start_time"
    temp = pd.read_sql_query(sql_c, conn)

    #put data into Dataframe and define ColumnDataSource for each plot
    #reg = pd.DataFrame({'reg' : pol_regression(temp['start_time'], temp['average'],3)})
    #temp = pd.concat([temp, reg], axis = 1)
    temp['start_time'] = pd.to_datetime( Time(temp['start_time'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    #plot data
    p.line(x = "start_time", y = "average", color = color, y_range_name=y_axis, legend = legend, source = plot_data)
    scat = p.scatter(x = "start_time", y = "average", name = mnemonic, color = color, y_range_name=y_axis, legend = legend, source = plot_data)

    #generate error lines if wished
    if err != 'n':
        #generate error bars
        err_xs = []
        err_ys = []

        for index, item in temp.iterrows():
            err_xs.append((item['start_time'], item['start_time']))
            err_ys.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

        # plot them
        p.multi_line(err_xs, err_ys, color = color, legend = legend)

    return scat

def add_to_plot_normalized(p, legend, mnemonic, start, end, conn, nominal, color = "red"):
    '''Add line plot to figure (for wheelpositions)
    Parameters
    ----------
    p : bokeh object
        defines figure where line schould be plotted
    legend : str
        will be showed in legend of plot
    mnemonic : str
        defines mnemonic to be plotted
    start : datetime
        sets start time for data query
    end : datetime
        sets end time for data query
    conn : DBobject
        connection object to database
    color : str (default='dred')
        defines color for scatter and line plot
    '''

    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    sql_c = "SELECT * FROM "+mnemonic+" WHERE timestamp BETWEEN "+start_str+" AND "+end_str+" ORDER BY timestamp"
    temp = pd.read_sql_query(sql_c, conn)

    #normalize values
    temp['value'] -= nominal
    #temp['value'] -= 1

    temp['timestamp'] = pd.to_datetime( Time(temp['timestamp'], format = "mjd").datetime )
    plot_data = ColumnDataSource(temp)

    p.line(x = "timestamp", y = "value", color = color, legend = legend, source = plot_data)
    p.scatter(x = "timestamp", y = "value", color = color, legend = legend, source = plot_data)

def add_basic_layout(p):
    '''Add basic layout to certain plot
    Parameters
    ----------
    p : bokeh object
        defines plot where line and scatter should be added
    '''
    p.title.align = "left"
    p.title.text_color = "#c85108"
    p.title.text_font_size = "25px"
    p.background_fill_color = "#efefef"

    p.xaxis.axis_label_text_font_size = "14pt"
    p.xaxis.axis_label_text_color ='#2D353C'
    p.yaxis.axis_label_text_font_size = "14pt"
    p.yaxis.axis_label_text_color = '#2D353C'

    p.xaxis.major_tick_line_color = "firebrick"
    p.xaxis.major_tick_line_width = 2
    p.xaxis.minor_tick_line_color = "#c85108"
