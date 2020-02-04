"""Prepares plots for FPE VOLTAGE/CURRENT tab on MIRI data trending
webpage

Module prepares plots for the mnemonics listed below. Combines plots
in a grid and returns tab object.

    Plot 1:
    IMIR_PDU_V_DIG_5V
    IMIR_PDU_I_DIG_5V

    Plot 2:
    IMIR_PDU_V_ANA_5V
    IMIR_PDU_I_ANA_5V

    Plot 3:
    IMIR_PDU_V_ANA_N5V
    IMIR_PDU_I_ANA_N5V

    Plot 4:
    IMIR_PDU_V_ANA_7V
    IMIR_PDU_I_ANA_7V

    Plot 5:
    IMIR_PDU_V_ANA_N7V
    IMIR_PDU_I_ANA_N7V

    Plot 6:
    IMIR_SPW_V_DIG_2R5V
    IMIR_PDU_V_REF_2R5V

Authors
-------

    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``dashborad.py``, e.g.:

    ::
        from .plots.fpe_voltage_tab import fpe_plots
        tab = fpe_plots(conn, start, end)

Dependencies
------------

    User must provide database ``miri_database.db``

    Other dependencies include:

    - ``bokeh``

"""

from bokeh.layouts import gridplot, Column
from bokeh.models import LinearAxis, Range1d
from bokeh.models.widgets import Panel, Div
from bokeh.plotting import figure

from jwql.instrument_monitors.miri_monitors.data_trending.plots import plot_functions


def ana5(conn, start, end):
    """Generates the 'FPE Ana. 5V' plot

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
        y_range=[4.95, 5.05],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'FPE Ana. 5V'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot.extra_y_ranges = {'current': Range1d(start=100, end=250)}
    fpe_ana_5v_line = plot_functions.add_to_plot(plot, 'FPE Ana. 5V', 'IMIR_PDU_V_ANA_5V', start, end, conn, color='red')
    fpe_ana_5v_current_line = plot_functions.add_to_plot(plot, 'FPE Ana. 5V Current', 'IMIR_PDU_I_ANA_5V', start, end, conn, y_axis='current', color='blue')
    plot.add_layout(LinearAxis(y_range_name='current', axis_label='Current (mA)', axis_label_text_color='blue'), 'right')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [fpe_ana_5v_line, fpe_ana_5v_current_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def ana5n(conn, start, end):
    """Generates the 'FPE Ana. N5V' plot

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
        y_range=[-5.1, -4.85],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'FPE Ana. N5V'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot.extra_y_ranges = {'current': Range1d(start=100, end=300)}
    fpe_ana_n5_line = plot_functions.add_to_plot(plot, 'FPE Ana. N5', 'IMIR_PDU_V_ANA_N5V', start, end, conn, color='red')
    fpe_ana_n5_current_line = plot_functions.add_to_plot(plot, 'FPE Ana. N5 Current', 'IMIR_PDU_I_ANA_N5V', start, end, conn, y_axis='current', color='blue')
    plot.add_layout(LinearAxis(y_range_name='current', axis_label='Current (mA)', axis_label_text_color='blue'), 'right')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [fpe_ana_n5_line, fpe_ana_n5_current_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def ana7(conn, start, end):
    """Generates the 'FPE Ana. 7V' plot

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
        y_range=[6.85, 7.1],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'FPE Ana. 7V'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot.extra_y_ranges = {'current': Range1d(start=300, end=450)}
    fpe_ana_7v_line = plot_functions.add_to_plot(plot, 'FPE Ana. 7V', 'IMIR_PDU_V_ANA_7V', start, end, conn, color='red')
    fpe_ana_7v_current_line = plot_functions.add_to_plot(plot, 'FPE Ana. 7V Current', 'IMIR_PDU_I_ANA_7V', start, end, conn, y_axis='current', color='blue')
    plot.add_layout(LinearAxis(y_range_name='current', axis_label='Current (mA)', axis_label_text_color='blue'), 'right')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [fpe_ana_7v_line, fpe_ana_7v_current_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def ana7n(conn, start, end):
    """Generates the 'FPE Ana. N7V' plot

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
        y_range=[-7.1, -6.9],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'FPE Ana. N7V'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot.extra_y_ranges = {'current': Range1d(start=350, end=400)}
    fpe_ana_n7v_line = plot_functions.add_to_plot(plot, 'FPE Dig. N7V', 'IMIR_PDU_V_ANA_N7V', start, end, conn, color='red')
    fpe_ana_n7v_current = plot_functions.add_to_plot(plot, 'FPE Ana. N7V Current', 'IMIR_PDU_I_ANA_N7V', start, end, conn, y_axis='current', color='blue')
    plot.add_layout(LinearAxis(y_range_name='current', axis_label='Current (mA)', axis_label_text_color='blue'), 'right')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [fpe_ana_n7v_line, fpe_ana_n7v_current])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def dig5(conn, start, end):
    """Generates the 'FPE Dig. 5v' plot

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
        y_range=[4.9, 5.1],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = 'FPE Dig. 5V'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    plot.extra_y_ranges = {'current': Range1d(start=2100, end=2500)}
    fpe_dig_5v_line = plot_functions.add_to_plot(plot, 'FPE Dig. 5V', 'IMIR_PDU_V_DIG_5V', start, end, conn, color='red')
    fpe_dig_5v_current_line = plot_functions.add_to_plot(plot, 'FPE Dig. 5V Current', 'IMIR_PDU_I_DIG_5V', start, end, conn, y_axis='current', color='blue')
    plot.add_layout(LinearAxis(y_range_name='current', axis_label='Current (mA)', axis_label_text_color='blue'), 'right')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [fpe_dig_5v_line, fpe_dig_5v_current_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot


def fpe_plots(conn, start, end):
    """Generates the 'FPE VOLTAGE/CURRENT' tab

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
                <td>2.5V Ref and FPE Digg</td>
                <td>IMIR_SPW_V_DIG_2R5V<br>
                    IMIR_PDU_V_REF_2R5V<br> </td>
                <td>FPE 2.5V Digital and FPE 2.5V PDU Reference Voltage</td>
              </tr>
              <tr>
                <td>FPE Dig. 5V</td>
                <td>IMIR_PDU_V_DIG_5V<br>
                    IMIR_PDU_I_DIG_5V</td>
                <td>FPE 5V Digital Voltage and Current</td>
              </tr>
              <tr>
                <td>FPE Ana. 5V</td>
                <td>IMIR_PDU_V_ANA_5V<br>
                    IMIR_PDU_I_ANA_5V</td>
                <td>FPE +5V Analog Voltage and Current</td>
              </tr>
              <tr>
                <td>FPE Ana. N5V</td>
                <td>IMIR_PDU_V_ANA_N5V<br>
                    IMIR_PDU_I_ANA_N5V</td>
                <td>FPE -5V Analog Voltage and Current</td>
              </tr>
              <tr>
                <td>FPE Ana. 7V</td>
                <td>IMIR_PDU_V_ANA_7V<br>
                    IMIR_PDU_I_ANA_7V</td>
                <td>FPE +7V Analog Voltage and Current</td>
              </tr>
               <tr>
                 <td>FPE Ana. N7V</td>
                 <td>IMIR_PDU_V_ANA_N7V<br>
                     IMIR_PDU_I_ANA_N7V</td>
                 <td>FPE -7V Analog Voltage and Current</td>
               </tr>
            </table>
            </body>""",
        width=1100)

    plot1 = dig5(conn, start, end)
    plot2 = refdig(conn, start, end)
    plot3 = ana5(conn, start, end)
    plot4 = ana5n(conn, start, end)
    plot5 = ana7(conn, start, end)
    plot6 = ana7n(conn, start, end)
    grid = gridplot([[plot2, plot1],
                     [plot3, plot4],
                     [plot5, plot6]], merge_tools=False)
    layout = Column(description_table, grid)
    tab = Panel(child=layout, title='FPE VOLTAGE/CURRENT')

    return tab


def refdig(conn, start, end):
    """Generates the '2.5V Reg and FPE Dig.' plot

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
        y_range=[2.45, 2.55],
        x_axis_type='datetime',
        output_backend='webgl',
        x_axis_label='Date',
        y_axis_label='Voltage (V)')
    plot.grid.visible = True
    plot.title.text = '2.5V Ref and FPE Dig.'
    plot_functions.add_basic_layout(plot)

    # Add a line renderer with legend and line thickness
    fpe_dig_25v_line = plot_functions.add_to_plot(plot, 'FPE Dig. 2.5V', 'IMIR_SPW_V_DIG_2R5V', start, end, conn, color='orange')
    fpe_pdu_25v_ref_line = plot_functions.add_to_plot(plot, 'FPE PDU 2.5V REF', 'IMIR_PDU_V_REF_2R5V', start, end, conn, color='red')

    # Configure hover tool
    plot_functions.add_hover_tool(plot, [fpe_dig_25v_line, fpe_pdu_25v_ref_line])

    # Configure legend
    plot.legend.location = 'bottom_right'
    plot.legend.click_policy = 'hide'

    return plot
