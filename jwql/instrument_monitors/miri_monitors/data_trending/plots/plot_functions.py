"""Auxilary functions for building plots for the data trending webpage

Authors
-------

    - Daniel Kühbacher

Use
---

    The functions within this module are intended to be imported and
    used by various plotting modules, e.g.:

    ::
        from jwql.instrument_monitors.miri_monitors.data_trending.plots import plot_functions
        plot_functions.add_to_plot()


Dependencies
------------

    - ``astropy``
    - ``bokeh``
    - ``numpy``
    - ``pandas``
"""

from astropy.time import Time
from bokeh.models import ColumnDataSource, HoverTool
import numpy as np
import pandas as pd


def add_basic_layout(plot):
    """Add basic layout to given plot
    Parameters
    ----------
    plot : bokeh object
        ``bokeh`` plot object
    """

    plot.title.align = 'left'
    plot.title.text_color = '#c85108'
    plot.title.text_font_size = '25px'
    plot.background_fill_color = '#efefef'
    plot.xaxis.axis_label_text_font_size = '14pt'
    plot.xaxis.axis_label_text_color = '#2D353C'
    plot.yaxis.axis_label_text_font_size = '14pt'
    plot.yaxis.axis_label_text_color = '#2D353C'
    plot.xaxis.major_tick_line_color = 'firebrick'
    plot.xaxis.major_tick_line_width = 2
    plot.xaxis.minor_tick_line_color = '#c85108'


def add_hover_tool(plot, renderer):
    """Append hover tool to plot

    parameters
    ----------
    plot : obj
        ``bokeh`` plot object to append hover tool to
    renderer : list
        List of renderer to append hover tool
    """

    # Activate HoverTool for scatter plot
    hover_tool = HoverTool(
        tooltips=[('Name', '$name'), ('Count', '@data_points'), ('Mean', '@average'), ('Deviation', '@deviation')],
        renderers=renderer)

    # Append hover tool
    plot.tools.append(hover_tool)


def add_to_plot(plot, legend, mnemonic, start, end, conn, y_axis='default', color='red', err='n'):
    """Add scatter and line to given plot and activates hover tool

    Parameters
    ----------
    plot : obj
        ``bokeh`` plot object to add the line and scatter to
    legend : str
        Will be showed in legend of plot
    mnemonic : str
        Defines mnemonic to be plotted
    start : obj
        ``datetime`` object that defines start time for data query
    end : obj
        ``datetime`` object that defines end time for data query
    conn : obj
        Connection object to database
    y_axis : str
        Used if secon y axis is provided
    color : str
        Defines color for scatter and line plot

    Returns
    -------
    scatter_plot : plot scatter object
        Used for applying hovertools o plots
    """

    # Convert given start and end time to astropy time
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    # Prepare and execute sql query
    command = 'SELECT * FROM {} \
               WHERE start_time BETWEEN {} AND {} \
               ORDER BY start_time'.format(mnemonic, start_str, end_str)
    query_results = pd.read_sql_query(command, conn)

    # Put data into Dataframe and define ColumnDataSource for each plot
    reg = pd.DataFrame({'reg': pol_regression(query_results['start_time'], query_results['average'], 3)})
    query_results = pd.concat([query_results, reg], axis=1)
    query_results['start_time'] = pd.to_datetime(Time(query_results['start_time'], format='mjd').datetime)
    plot_data = ColumnDataSource(query_results)

    # Plot data
    plot.line(x='start_time', y='average', color=color, y_range_name=y_axis, legend_label=legend, source=plot_data)
    scatter_plot = plot.scatter(x='start_time', y='average', color=color, name=mnemonic, y_range_name=y_axis, legend_label=legend, source=plot_data)

    # Generate error lines if necessary
    if err != 'n':
        err_xs, err_ys = [], []
        for index, item in query_results.iterrows():
            err_xs.append((item['start_time'], item['start_time']))
            err_ys.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

        # Plot the error bars
        plot.multi_line(err_xs, err_ys, color=color, legend_label=legend)

    return scatter_plot


def add_to_wplot(plot, legend, mnemonic, start, end, conn, normalization_factor, color='red'):
    """Add line plot to figure (for wheel positions)

    Parameters
    ----------
    plot : obj
        ``bokeh`` plot object to add the line and scatter to
    legend : str
        Will be showed in legend of plot
    mnemonic : str
        Defines mnemonic to be plotted
    start : obj
        ``datetime`` object that defines start time for data query
    end : obj
        ``datetime`` object that defines end time for data query
    conn : obj
        Connection object to database
    normalization_factor : float
        Value to normalize by
    color : str (default='dred')
        defines color for scatter and line plot
    """

    # Convert given start and end time to astropy time
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)

    # Prepare and execute sql query
    command = 'SELECT * FROM {} \
               WHERE timestamp BETWEEN {} AND {} \
               ORDER BY timestamp'.format(mnemonic, start_str, end_str)
    query_results = pd.read_sql_query(command, conn)

    # Normalize values
    query_results['value'] -= normalization_factor

    # Put data into Dataframe and define ColumnDataSource for each plot
    query_results['timestamp'] = pd.to_datetime(Time(query_results['timestamp'], format='mjd').datetime)
    plot_data = ColumnDataSource(query_results)

    # Plot data
    plot.line(x='timestamp', y='value', color=color, legend_label=legend, source=plot_data)
    plot.scatter(x='timestamp', y='value', color=color, legend_label=legend, source=plot_data)


def pol_regression(x, y, rank):
    """Calculate polynominal regression of certain rank

    Parameters
    ----------
    x : list
        x parameters for regression
    y : list
        y parameters for regression
    rank : int
        rank of regression

    Returns
    -------
    y_poly : list
        regression y parameters
    """

    z = np.polyfit(x, y, rank)
    f = np.poly1d(z)
    y_poly = f(x)

    return y_poly
