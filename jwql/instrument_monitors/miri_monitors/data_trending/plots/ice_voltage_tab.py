"""Prepares plots for ICE VOLTAGE tab on MIRI data trending webpage

Module prepares plots for the mnemonics listed below. Combines plots
in a grid and returns tab object.

    Plot 1:
    IMIR_HK_ICE_SEC_VOLT1
    IMIR_HK_ICE_SEC_VOLT3

    Plot 2:
    IMIR_HK_ICE_SEC_VOLT2

    Plot 3:
    IMIR_HK_ICE_SEC_VOLT4 : IDLE and HV_ON

    Plot 4:
    IMIR_HK_FW_POS_VOLT
    IMIR_HK_GW14_POS_VOLT
    IMIR_HK_GW23_POS_VOLT
    IMIR_HK_CCC_POS_VOLT

Authors
-------

    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``dashborad.py``, e.g.:

    ::
        from .plots.ice_voltage_tab import ice_plots
        tab = ice_plots(conn, start, end)

Dependencies
------------

    User must provide database ``miri_database.db``

    Other dependencies include:

    - ``bokeh``
"""

from bokeh.layouts import gridplot, Column
from bokeh.models.widgets import Panel, Div
from bokeh.plotting import figure

from jwql.instrument_monitors.miri_monitors.data_trending.plots import plot_functions as plot_functions


def volt1_3(conn, start, end):
    """Generates the 'ICE_SEC_VOLT1/3' plot

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
        tools="pan,wheel_zoom,box_zoom,reset,save",
        toolbar_location='above',
        plot_width=560,
        plot_height=500,
        y_range=[30, 50],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'ICE_SEC_VOLT1/3'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    volt_1_line = plot_functions.add_to_plot(plot, 'Volt1', 'IMIR_HK_ICE_SEC_VOLT1', start, end, conn, color='red')
    volt_3_line = plot_functions.add_to_plot(plot, 'Volt3', 'IMIR_HK_ICE_SEC_VOLT3', start, end, conn, color='purple')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [volt_1_line, volt_3_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def volt2(conn, start, end):
    """Generates the 'ICE_SEC_VOLT2' plot

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
        plot_width=560,
        plot_height=500,
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'ICE_SEC_VOLT2'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    volt_2_line = plot_functions.add_to_plot(plot, 'Volt2', 'IMIR_HK_ICE_SEC_VOLT2', start, end, conn, color='red')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [volt_2_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def volt4(conn, start, end):
    """Generates the 'ICE_SEC_VOLT4' plot

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
        plot_width=560,
        plot_height=500,
        y_range=[4.2, 5],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'ICE_SEC_VOLT4'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    volt_4_idle_line = plot_functions.add_to_plot(plot, 'Volt4 Idle', 'IMIR_HK_ICE_SEC_VOLT4_IDLE', start, end, conn, color='orange')
    volt_4_hv_on_line = plot_functions.add_to_plot(plot, 'Volt4 Hv on', 'IMIR_HK_ICE_SEC_VOLT4_HV_ON', start, end, conn, color='red')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [volt_4_idle_line, volt_4_hv_on_line])

    # Configure legend
    plot.legend.location = "bottom_right"
    plot.legend.click_policy = "hide"

    return plot


def volt_plots(conn, start, end):
    """Generates the 'ICE VOLTAGE' tab

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
                <td>ICE_SEC_VOLT1/3</td>
                <td>IMIR_HK_ICE_SEC_VOLT1 <br>
                    IMIR_HK_ICE_SEC_VOLT3 <br> </td>
                <td>ICE Secondary Voltage (HV) V1 and V3</td>
              </tr>
              <tr>
                <td>ICE_SEC_VOLT2</td>
                <td>IMIR_HK_SEC_VOLT2</td>
                <td>ICE secondary voltage (HV) V2</td>
              </tr>
              <tr>
                <td>ICE_SEC_VOLT4</td>
                <td>IMIR_HK_SEC_VOLT2</td>
                <td>ICE secondary voltage (HV) V4 - HV on and IDLE</td>
              </tr>
              <tr>
                <td>Wheel Sensor Supply</td>
                <td>IMIR_HK_FW_POS_VOLT<br>
                    IMIR_HK_GW14_POS_VOLT<br>
                    IMIR_HK_GW23_POS_VOLT<br>
                    IMIR_HK_CCC_POS_VOLT</td>
                <td>Wheel Sensor supply voltages </td>
              </tr>
            </table>
            </body>
            """,
        width=1100)

    plot1 = volt1_3(conn, start, end)
    plot2 = volt2(conn, start, end)
    plot3 = volt4(conn, start, end)
    plot4 = wheel_sensor_supply(conn, start, end)
    grid = gridplot([[plot1, plot2], [plot3, plot4]], merge_tools=False)
    layout = Column(description_table, grid)
    tab = Panel(child=layout, title='ICE VOLTAGE')

    return tab


def wheel_sensor_supply(conn, start, end):
    """Generates the 'Wheel Sensor Supply' plot

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
        plot_width=560,
        plot_height=500,
        y_range=[280, 300],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (mV)')
    plot.grid.visible = True
    plot.title.text = 'Wheel Sensor Supply'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    fw_line = plot_functions.add_to_plot(plot, 'FW', 'IMIR_HK_FW_POS_VOLT', start, end, conn, color='red')
    gw14_line = plot_functions.add_to_plot(plot, 'GW14', 'IMIR_HK_GW14_POS_VOLT', start, end, conn, color='purple')
    gw23_line = plot_functions.add_to_plot(plot, 'GW23', 'IMIR_HK_GW23_POS_VOLT', start, end, conn, color='orange')
    ccc_line = plot_functions.add_to_plot(plot, 'CCC', 'IMIR_HK_CCC_POS_VOLT', start, end, conn, color='firebrick')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [fw_line, gw14_line, gw23_line, ccc_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot
