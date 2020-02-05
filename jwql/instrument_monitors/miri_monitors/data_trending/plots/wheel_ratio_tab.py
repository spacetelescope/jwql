"""Prepares plots for WHEEL RATIO tab on MIRI data trending webpage

Module prepares plots for the mnemonics listed below. Combines plots
in a grid and returns tab object.

    Plot 1:
    IMIR_HK_FW_POS_RATIO_FND
    IMIR_HK_FW_POS_RATIO_OPAQUE
    IMIR_HK_FW_POS_RATIO_F1000W
    IMIR_HK_FW_POS_RATIO_F1130W
    IMIR_HK_FW_POS_RATIO_F1280W
    IMIR_HK_FW_POS_RATIO_P750L
    IMIR_HK_FW_POS_RATIO_F1500W
    IMIR_HK_FW_POS_RATIO_F1800W
    IMIR_HK_FW_POS_RATIO_F2100W
    IMIR_HK_FW_POS_RATIO_F560W
    IMIR_HK_FW_POS_RATIO_FLENS
    IMIR_HK_FW_POS_RATIO_F2300C
    IMIR_HK_FW_POS_RATIO_F770W
    IMIR_HK_FW_POS_RATIO_F1550C
    IMIR_HK_FW_POS_RATIO_F2550W
    IMIR_HK_FW_POS_RATIO_F1140C
    IMIR_HK_FW_POS_RATIO_F2550WR
    IMIR_HK_FW_POS_RATIO_F1065C

    Plot 2:
    IMIR_HK_GW14_POS_RATIO_SHORT
    IMIR_HK_GW14_POS_RATIO_MEDIUM
    IMIR_HK_GW14_POS_RATIO_LONG

    Plot 3:
    IMIR_HK_GW23_POS_RATIO_SHORT
    IMIR_HK_GW23_POS_RATIO_MEDIUM
    IMIR_HK_GW23_POS_RATIO_LONG

    Plot 4:
    IMIR_HK_CCC_POS_RATIO_LOCKED
    IMIR_HK_CCC_POS_RATIO_OPEN
    IMIR_HK_CCC_POS_RATIO_CLOSED

Authors
-------

    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``dashboard.py``, e.g.:

    ::
        from .plots.wheel_ratio_tab import wheel_plots
        tab = wheel_plots(conn, start, end)

Dependencies
------------

    User must provide database ``miri_database.db``

    Other dependencies include:

    - ``bokeh``
"""

from bokeh.layouts import column
from bokeh.models.widgets import Panel, Div
from bokeh.plotting import figure

from jwql.instrument_monitors.miri_monitors.data_trending.plots import plot_functions
from jwql.instrument_monitors.miri_monitors.data_trending.utils import mnemonics


def ccc(conn, start, end):
    """Generates the 'CCC Ratio' plot

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
        y_range=[-2, 2],
        x_axis_type='datetime',
        x_axis_label='Date',
        y_axis_label='ratio (normalized)')
    plot.grid.visible = True
    plot.title.text = 'CCC Ratio'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot_functions.add_to_wplot(plot, 'OPEN', 'IMIR_HK_CCC_POS_RATIO_OPEN', start, end, conn, mnemonics.ccc_nominals['OPEN'], color='red')
    plot_functions.add_to_wplot(plot, 'CLOSED', 'IMIR_HK_CCC_POS_RATIO_CLOSED', start, end, conn, mnemonics.ccc_nominals['CLOSED'], color='blue')

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def dga_a(conn, start, end):
    """Generates the 'DGA-A Ratio' plot

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
        y_range=[-2, 2],
        x_axis_type='datetime',
        x_axis_label='Date',
        y_axis_label='ratio (normalized)')
    plot.grid.visible = True
    plot.title.text = 'DGA-A Ratio'
    plot.title.align = 'left'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot_functions.add_to_wplot(plot, 'SHORT', 'IMIR_HK_GW14_POS_RATIO_SHORT', start, end, conn, mnemonics.gw14_nominals['SHORT'], color='green')
    plot_functions.add_to_wplot(plot, 'MEDIUM', 'IMIR_HK_GW14_POS_RATIO_MEDIUM', start, end, conn, mnemonics.gw14_nominals['MEDIUM'], color='red')
    plot_functions.add_to_wplot(plot, 'LONG', 'IMIR_HK_GW14_POS_RATIO_LONG', start, end, conn, mnemonics.gw14_nominals['LONG'], color='blue')

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def dga_b(conn, start, end):
    """Generates the 'DGA-B Ratio' plot

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
        y_range=[-2, 2],
        x_axis_type='datetime',
        x_axis_label='Date',
        y_axis_label='ratio (normalized)')
    plot.grid.visible = True
    plot.title.text = 'DGA-B Ratio'
    plot.title.align = 'left'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot_functions.add_to_wplot(plot, 'SHORT', 'IMIR_HK_GW23_POS_RATIO_SHORT', start, end, conn, mnemonics.gw23_nominals['SHORT'], color='green')
    plot_functions.add_to_wplot(plot, 'MEDIUM', 'IMIR_HK_GW23_POS_RATIO_MEDIUM', start, end, conn, mnemonics.gw23_nominals['MEDIUM'], color='red')
    plot_functions.add_to_wplot(plot, 'LONG', 'IMIR_HK_GW23_POS_RATIO_LONG', start, end, conn, mnemonics.gw23_nominals['LONG'], color='blue')

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def fw(conn, start, end):
    """Generates the 'Filterwheel Ratio' plot

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
        plot_height=800,
        y_range=[-6, 4],
        x_axis_type='datetime',
        x_axis_label='Date',
        y_axis_label='ratio (normalized)')
    plot.grid.visible = True
    plot.title.text = 'Filterwheel Ratio'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot_functions.add_to_wplot(plot, 'FND', 'IMIR_HK_FW_POS_RATIO_FND', start, end, conn, mnemonics.fw_nominals['FND'], color='green')
    plot_functions.add_to_wplot(plot, 'OPAQUE', 'IMIR_HK_FW_POS_RATIO_OPAQUE', start, end, conn, mnemonics.fw_nominals['OPAQUE'], color='red')
    plot_functions.add_to_wplot(plot, 'F1000W', 'IMIR_HK_FW_POS_RATIO_F1000W', start, end, conn, mnemonics.fw_nominals['F1000W'], color='blue')
    plot_functions.add_to_wplot(plot, 'F1130W', 'IMIR_HK_FW_POS_RATIO_F1130W', start, end, conn, mnemonics.fw_nominals['F1130W'], color='orange')
    plot_functions.add_to_wplot(plot, 'F1280W', 'IMIR_HK_FW_POS_RATIO_F1280W', start, end, conn, mnemonics.fw_nominals['F1280W'], color='firebrick')
    plot_functions.add_to_wplot(plot, 'P750L', 'IMIR_HK_FW_POS_RATIO_P750L', start, end, conn, mnemonics.fw_nominals['P750L'], color='cyan')
    plot_functions.add_to_wplot(plot, 'F1500W', 'IMIR_HK_FW_POS_RATIO_F1500W', start, end, conn, mnemonics.fw_nominals['F1500W'], color='magenta')
    plot_functions.add_to_wplot(plot, 'F1800W', 'IMIR_HK_FW_POS_RATIO_F1800W', start, end, conn, mnemonics.fw_nominals['F1800W'], color='burlywood')
    plot_functions.add_to_wplot(plot, 'F2100W', 'IMIR_HK_FW_POS_RATIO_F2100W', start, end, conn, mnemonics.fw_nominals['F2100W'], color='cadetblue')
    plot_functions.add_to_wplot(plot, 'F560W', 'IMIR_HK_FW_POS_RATIO_F560W', start, end, conn, mnemonics.fw_nominals['F560W'], color='chartreuse')
    plot_functions.add_to_wplot(plot, 'FLENS', 'IMIR_HK_FW_POS_RATIO_FLENS', start, end, conn, mnemonics.fw_nominals['FLENS'], color='brown')
    plot_functions.add_to_wplot(plot, 'F2300C', 'IMIR_HK_FW_POS_RATIO_F2300C', start, end, conn, mnemonics.fw_nominals['F2300C'], color='chocolate')
    plot_functions.add_to_wplot(plot, 'F770W', 'IMIR_HK_FW_POS_RATIO_F770W', start, end, conn, mnemonics.fw_nominals['F770W'], color='darkorange')
    plot_functions.add_to_wplot(plot, 'F1550C', 'IMIR_HK_FW_POS_RATIO_F1550C', start, end, conn, mnemonics.fw_nominals['F1550C'], color='darkgreen')
    plot_functions.add_to_wplot(plot, 'F2550W', 'IMIR_HK_FW_POS_RATIO_F2550W', start, end, conn, mnemonics.fw_nominals['F2550W'], color='darkcyan')
    plot_functions.add_to_wplot(plot, 'F1140C', 'IMIR_HK_FW_POS_RATIO_F1140C', start, end, conn, mnemonics.fw_nominals['F1140C'], color='darkmagenta')
    plot_functions.add_to_wplot(plot, 'F2550WR', 'IMIR_HK_FW_POS_RATIO_F2550WR', start, end, conn, mnemonics.fw_nominals['F2550WR'], color='crimson')
    plot_functions.add_to_wplot(plot, 'F1065C', 'IMIR_HK_FW_POS_RATIO_F1065C', start, end, conn, mnemonics.fw_nominals['F1065C'], color='cornflowerblue')

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def wheel_ratios(conn, start, end):
    """Generates the 'WHEEL RATIO' tab

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
            </style>

            <body>
            <table style='width:100%'>
              <tr>
                <th><h6>Plotname</h6></th>
                <th><h6>Mnemonic</h6></th>
                <th><h6>Description</h6></th>
              </tr>
              <tr>
                <td>Filterwheel Ratio</td>
                <td>IMIR_HK_FW_POS_RATIO<br>
                    IMIR_HK_FW_CUR_POS<br></td>
                <td>FW position sensor ratio (normalised) and commanded position</td>
              </tr>
              <tr>
                <td>DGA-A Ratio</td>
                <td>IMIR_HK_GW14_POS_RATIO<br>
                    IMIR_HK_GW14_CUR_POS<br></td>
                <td>DGA-A position sensor ratio (normalised) and commanded position</td>
              </tr>
              <tr>
                <td>DGA-B Ratio</td>
                <td>IMIR_HK_GW23_POS_RATIO<br>
                    IMIR_HK_GW23_CUR_POS<br></td>
                <td>DGA-B position sensor ratio (normalised) and commanded position</td>
              </tr>
              <tr>
                <td>CCC Ratio</td>
                <td>IMIR_HK_CCC_POS_RATIO<br>
                    IMIR_HK_CCC_CUR_POS<br></td>
                <td>Contamination Control Cover position sensor ratio (normalised) and commanded position</td>
              </tr>
            </table>
            </body>""",
        width=1100)

    plot1 = fw(conn, start, end)
    plot2 = dga_a(conn, start, end)
    plot3 = dga_b(conn,  start, end)
    plot4 = ccc(conn, start, end)
    layout = column(description_table, plot1, plot2, plot3, plot4)
    tab = Panel(child=layout, title='WHEEL RATIO')

    return tab
