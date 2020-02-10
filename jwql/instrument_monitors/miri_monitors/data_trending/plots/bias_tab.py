"""Prepares plots for BIAS tab on MIRI data trending webpage

Module prepares plots for the mnemonics listed below. Combines plots
in a grid and returns tab object.

    Plot 1:
    IGDP_MIR_IC_V_VDETCOM
    IGDP_MIR_SW_V_VDETCOM
    IGDP_MIR_LW_V_VDETCOM

    Plot 2:
    IGDP_MIR_IC_V_VSSOUT
    IGDP_MIR_SW_V_VSSOUT
    IGDP_MIR_LW_V_VSSOUT

    Plot 3:
    IGDP_MIR_IC_V_VRSTOFF
    IGDP_MIR_SW_V_VRSTOFF
    IGDP_MIR_LW_V_VRSTOFF

    Plot 4:
    IGDP_MIR_IC_V_VP
    IGDP_MIR_SW_V_VP
    IGDP_MIR_LW_V_VP

    Plot 5
    IGDP_MIR_IC_V_VDDUC
    IGDP_MIR_SW_V_VDDUC
    IGDP_MIR_LW_V_VDDUC

Authors
-------

    - Daniel Kühbacher

Use
---

    The functions within this module are intended to be imported and
    used by ``dashborad.py``, e.g.:

    ::
        from .plots.bias_tab import bias_plots
        tab = bias_plots(conn, start, end)

Dependencies
------------

    User must provide database ``miri_database.db``

    Other dependencies include:

    - ``bokeh``

"""

from bokeh.layouts import gridplot, Column
from bokeh.models.widgets import Panel, Div
from bokeh.plotting import figure

from jwql.instrument_monitors.miri_monitors.data_trending.plots import plot_functions


def _vdduc(conn, start, end):
    """Generates the 'VDDUC' plot

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
    plot.title.text = 'VDDUC'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    vdduc_ic_line = plot_functions.add_to_plot(plot, 'VDDUC IC', 'IGDP_MIR_IC_V_VDDUC', start, end, conn, color='red')
    vdduc_sw_line = plot_functions.add_to_plot(plot, 'VDDUC SW', 'IGDP_MIR_SW_V_VDDUC', start, end, conn, color='orange')
    vdduc_lw_line = plot_functions.add_to_plot(plot, 'VDDUC LW', 'IGDP_MIR_LW_V_VDDUC', start, end, conn, color='green')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [vdduc_ic_line, vdduc_sw_line, vdduc_lw_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'
    plot.legend.orientation = 'horizontal'

    return plot


def _vdetcom(conn, start, end):
    """Generates the 'VDETCOM' plot

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
    plot.title.text = 'VDETCOM'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    vdetcom_ic_line = plot_functions.add_to_plot(plot, 'VDETCOM IC', 'IGDP_MIR_IC_V_VDETCOM', start, end, conn, color='red')
    vdetcom_sw_line = plot_functions.add_to_plot(plot, 'VDETCOM SW', 'IGDP_MIR_SW_V_VDETCOM', start, end, conn, color='orange')
    vdetcom_lw_line = plot_functions.add_to_plot(plot, 'VDETCOM LW', 'IGDP_MIR_LW_V_VDETCOM', start, end, conn, color='green')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [vdetcom_ic_line, vdetcom_sw_line, vdetcom_lw_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'
    plot.legend.orientation = 'horizontal'

    return plot


def _vp(conn, start, end):
    """Generates the 'VP' plot

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
    plot.title.text = 'VP'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    vp_ic_line = plot_functions.add_to_plot(plot, 'VP IC', 'IGDP_MIR_IC_V_VP', start, end, conn, color='red')
    vp_sw_line = plot_functions.add_to_plot(plot, 'VP SW', 'IGDP_MIR_SW_V_VP', start, end, conn, color='orange')
    vp_lw_line = plot_functions.add_to_plot(plot, 'VP LW', 'IGDP_MIR_LW_V_VP', start, end, conn, color='green')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [vp_ic_line, vp_sw_line, vp_lw_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'
    plot.legend.orientation = 'horizontal'

    return plot


def _vrstoff(conn, start, end):
    """Generates the 'VRSTOFF' plot

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
    plot.title.text = 'VRSTOFF'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    vrstoff_ic_line = plot_functions.add_to_plot(plot, 'VRSTOFF IC', 'IGDP_MIR_IC_V_VRSTOFF', start, end, conn, color='red')
    vrstoff_sw_line = plot_functions.add_to_plot(plot, 'VRSTOFF SW', 'IGDP_MIR_SW_V_VRSTOFF', start, end, conn, color='orange')
    vrstoff_lw_line = plot_functions.add_to_plot(plot, 'VRSTOFF LW', 'IGDP_MIR_LW_V_VRSTOFF', start, end, conn, color='green')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [vrstoff_ic_line, vrstoff_sw_line, vrstoff_lw_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'
    plot.legend.orientation = 'horizontal'

    return plot


def _vssout(conn, start, end):
    """Generates the 'VSSOUT' plot

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
    plot.title.text = 'VSSOUT'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    vssout_ic_line = plot_functions.add_to_plot(plot, 'VSSOUT IC', 'IGDP_MIR_IC_V_VSSOUT', start, end, conn, color='red')
    vssout_sw_line = plot_functions.add_to_plot(plot, 'VSSOUT SW', 'IGDP_MIR_SW_V_VSSOUT', start, end, conn, color='orange')
    vssout_lw_line = plot_functions.add_to_plot(plot, 'VSSOUT LW', 'IGDP_MIR_LW_V_VSSOUT', start, end, conn, color='green')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [vssout_ic_line, vssout_sw_line, vssout_lw_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'
    plot.legend.orientation = 'horizontal'

    return plot


def bias_plots(conn, start, end):
    """Generates the 'BIAS' tab

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
            <table style='width:100%'>
              <tr>
                <th><h6>Plotname</h6></th>
                <th><h6>Mnemonic</h6></th>
                <th><h6>Description</h6></th>
              </tr>
              <tr>
                <td>VSSOUT</td>
                <td>IGDP_MIR_IC_V_VSSOUT<br>
                    IGDP_MIR_SW_V_VSSOUT<br>
                    IGDP_MIR_LW_V_VSSOUT<br> </td>
                <td>Detector Bias VSSOUT (IC,SW, & LW)</td>
              </tr>
              <tr>
                <td>VDETCOM</td>
                <td>IGDP_MIR_IC_V_VDETCOM<br>
                    IGDP_MIR_SW_V_VDETCOM<br>
                    IGDP_MIR_LW_V_VDETCOM<br> </td>
                <td>Detector Bias VDETCOM (IC,SW, & LW)</td>
              </tr>
              <tr>
                <td>VRSTOFF</td>
                <td>IGDP_MIR_IC_V_VRSTOFF<br>
                    IGDP_MIR_SW_V_VRSTOFF<br>
                    IGDP_MIR_LW_V_VRSTOFF<br> </td>
                <td>Detector Bias VRSTOFF (IC,SW, & LW)</td>
              </tr>
              <tr>
                <td>VP</td>
                <td>IGDP_MIR_IC_V_VP<br>
                    IGDP_MIR_SW_V_VP<br>
                    IGDP_MIR_LW_V_VP<br> </td>
                <td>Detector Bias VP (IC,SW, & LW)</td>
              </tr>
              <tr>
                <td>VDDUC</td>
                <td>IGDP_MIR_IC_V_VDDUC<br>
                    IGDP_MIR_SW_V_VDDUC<br>
                    IGDP_MIR_LW_V_VDDUC<br> </td>
                <td>Detector Bias VDDUC (IC,SW, & LW)</td>
              </tr>

            </table>
            </body>""",
        width=1100)

    plot1 = _vdetcom(conn, start, end)
    plot2 = _vssout(conn, start, end)
    plot3 = _vrstoff(conn, start, end)
    plot4 = _vp(conn, start, end)
    plot5 = _vdduc(conn, start, end)
    grid = gridplot([[plot2, plot1],
                     [plot3, plot4],
                     [plot5, None]], merge_tools=False)
    layout = Column(description_table, grid)
    tab = Panel(child=layout, title='BIAS')

    return tab
