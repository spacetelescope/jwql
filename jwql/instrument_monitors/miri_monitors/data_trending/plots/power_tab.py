"""Prepares plots for POWER tab on MIRI data trending webpage

Module prepares plots for the mnemonics listed below. Combines plots
in a grid and returns tab object.

    Plot 1:
    SE_ZIMIRICEA * 30V

    Plot 2:
    SE_ZIMIRIFPEA * 30V

    Plot 3:
    SE_ZIMIRFPEA
    SE_ZIMIRCEA *I NPUT VOLTAGE

Authors
-------

    - Daniel Kühbacher

Use
---

    The functions within this module are intended to be imported and
    used by ``dashboard.py``, e.g.:

    ::
        from .plots.power_tab import power_plots
        tab = power_plots(conn, start, end)

Dependencies
------------

    User must provide database ``miri_database.db``

    Other dependencies include:

    - ``astropy``
    - ``bokeh``
    - ``pandas``

"""

from astropy.time import Time
from bokeh.layouts import column
from bokeh.models import BoxAnnotation, ColumnDataSource, HoverTool
from bokeh.models.widgets import Panel, Div
from bokeh.plotting import figure
import pandas as pd

from jwql.instrument_monitors.miri_monitors.data_trending.plots import plot_functions


def currents(conn, start, end):
    """Generates the 'FPE & ICE Currents' plot

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    # Create the plot
    plot = figure(
        tools='pan,wheel_zoom,box_zoom,reset,save',
        toolbar_location='above',
        plot_width=1120,
        plot_height=500,
        y_range=[0, 1.1],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Current (A)')
    plot.grid.visible = True
    plot.title.text = "FPE & ICE Currents"
    plot_functions.add_basic_layout(plot)

    # Plot the data
    ice_current_idle = plot_functions.add_to_plot(plot, 'ICE Current idle', 'SE_ZIMIRICEA_IDLE', start, end, conn, color='red')
    ice_current_hv_on = plot_functions.add_to_plot(plot, 'ICE Current HV on', 'SE_ZIMIRICEA_HV_ON', start, end, conn, color='orange')
    fpe_current = plot_functions.add_to_plot(plot, 'FPE Current', 'SE_ZIMIRFPEA', start, end, conn, color='brown')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [ice_current_idle, ice_current_hv_on, fpe_current])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'
    plot.legend.orientation = 'horizontal'

    return plot


def power_fpea(conn, start, end):
    """Generates the 'POWER FPE' plot

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    # Query data from database
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)
    command = "SELECT * FROM SE_ZIMIRFPEA \
               WHERE start_time BETWEEN {} AND {}\
               ORDER BY start_time".format(start_str, end_str)
    _fpea = pd.read_sql_query(command, conn)

    # Apply voltage factor
    voltage = 30
    _fpea['average'] *= voltage

    # Convert times to datetime objects
    _fpea['start_time'] = pd.to_datetime(Time(_fpea['start_time'], format='mjd').datetime)

    # Set column data source
    fpea = ColumnDataSource(_fpea)

    # Create the plot
    plot = figure(
        tools='pan,wheel_zoom,box_zoom,reset,save',
        toolbar_location='above',
        plot_width=1120,
        plot_height=500,
        y_range=[28.0, 28.5],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Power (W)')
    plot.grid.visible = True
    plot.title.text = 'POWER FPE'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    power_fpea_line = plot.scatter(x='start_time', y='average', color='orange', legend_label='Power FPEA', source=fpea)
    plot.line(x='start_time', y='average', color='orange', legend_label='Power FPEA', source=fpea)

    # Generate error bars
    err_xs, err_ys = [], []
    for index, item in _fpea.iterrows():
        err_xs.append((item['start_time'], item['start_time']))
        err_ys.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

    # plot the error bars
    plot.multi_line(err_xs, err_ys, color='orange', legend_label='Power FPEA')

    # Activate HoverTool for scatter plot
    hover_tool = HoverTool(
        tooltips=[('count', '@data_points'), ('mean', '@average'), ('deviation', '@deviation')],
        renderers=[power_fpea_line])
    plot.tools.append(hover_tool)

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def power_ice(conn, start, end):
    """Generates the 'POWER ICE' plot

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    # Query data from database
    start_str = str(Time(start).mjd)
    end_str = str(Time(end).mjd)
    command = 'SELECT * FROM SE_ZIMIRICEA_IDLE \
               WHERE start_time BETWEEN {} AND {} \
               ORDER BY start_time'.format(start_str, end_str)
    _idle = pd.read_sql_query(command, conn)
    command = 'SELECT * FROM SE_ZIMIRICEA_HV_ON \
               WHERE start_time BETWEEN {} AND {} \
               ORDER BY start_time'.format(start_str, end_str)
    _hv = pd.read_sql_query(command, conn)

    # Apply voltage factor
    voltage = 30
    _idle['average'] *= voltage
    _hv['average'] *= voltage

    # Convert times to datetime objects
    _idle['start_time'] = pd.to_datetime(Time(_idle['start_time'], format='mjd').datetime)
    _hv['start_time'] = pd.to_datetime(Time(_hv['start_time'], format='mjd').datetime)

    # Set column data source
    idle = ColumnDataSource(_idle)
    hv = ColumnDataSource(_hv)

    # Create the plot
    plot = figure(
        tools='pan,wheel_zoom,box_zoom,reset,save',
        toolbar_location='above',
        plot_width=1120,
        plot_height=500,
        y_range=[5, 14],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Power (W)')
    plot.grid.visible = True
    plot.title.text = 'POWER ICE'
    plot_functions.add_basic_layout(plot)
    plot.add_layout(BoxAnnotation(bottom=6, top=8, fill_alpha=0.1, fill_color='green'))

    # Add a line renderer with legend and line thickness
    power_idle_line = plot.scatter(x='start_time', y='average', color='orange', legend_label='Power idle', source=idle)
    power_hv_on_line = plot.scatter(x='start_time', y='average', color='red', legend_label='Power hv on', source=hv)
    plot.line(x='start_time', y='average', color='orange', legend_label='Power idle', source=idle)
    plot.line(x='start_time', y='average', color='red', legend_label='Power hv on', source=hv)

    # Generate error bars
    err_xs_hv, err_ys_hv, err_xs_idle, err_ys_idle = [], [], [], []
    for index, item in _hv.iterrows():
        err_xs_hv.append((item['start_time'], item['start_time']))
        err_ys_hv.append((item['average'] - item['deviation'], item['average'] + item['deviation']))
    for index, item in _idle.iterrows():
        err_xs_idle.append((item['start_time'], item['start_time']))
        err_ys_idle.append((item['average'] - item['deviation'], item['average'] + item['deviation']))

    # Plot the error bars
    plot.multi_line(err_xs_hv, err_ys_hv, color='red', legend_label='Power hv on')
    plot.multi_line(err_xs_idle, err_ys_idle, color='orange', legend_label='Power idle')

    # Activate HoverTool for scatter plot
    hover_tool = HoverTool(
        tooltips=[('count', '@data_points'), ('mean', '@average'), ('deviation', '@deviation')],
        mode='mouse',
        renderers=[power_idle_line, power_hv_on_line])
    plot.tools.append(hover_tool)

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def power_plots(conn, start, end):
    """Generates the 'POWER' tab

    Parameters
    ----------
    conn : obj
        Database connection object
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    plot : obj
        ``bokeh`` plot object
    """

    description_table = Div(
        text="""
            <style>
            table, th, td {
              border: 1px solid black;
              background-color: #efefef;
              border-collapse: collapse;
              padding: 5px
            }
            table {
              border-spacing: 15px;
            }
            </style>

            <body>
            <table style="width:100%">
              <tr>
                <th><h6>Plotname</h6></th>
                <th><h6>Mnemonic</h6></th>
                <th><h6>Description</h6></th>
              </tr>
              <tr>
                <td>POWER ICE</td>
                <td>SE_ZIMIRICEA * 30V (static)</td>
                <td>Primary power consumption ICE side A - HV on and IDLE</td>
              </tr>
              <tr>
                <td>POWER FPE</td>
                <td>SE_ZIMIRIFPEA * 30V (static)</td>
                <td>Primary power consumption FPE side A</td>
              </tr>
              <tr>
                <td>FPE & ICE Voltages/Currents</td>
                <td>SE_ZIMIRFPEA<br>
                    SE_ZIMIRCEA
                    *INPUT VOLTAGE* (missing)</td>
                <td>Supply voltage and current ICE/FPE</td>
              </tr>
            </table>
            </body>""",
        width=1100)

    plot1 = power_ice(conn, start, end)
    plot2 = power_fpea(conn, start, end)
    plot3 = currents(conn, start, end)
    layout = column(description_table, plot1, plot2, plot3)
    tab = Panel(child=layout, title='POWER')

    return tab
