"""Various functions to generate Bokeh objects to be used by the
``views`` of the ``jwql`` app.

This module contains several functions that instantiate
``BokehTemplate`` objects to be rendered in ``views.py``.

Authors
-------

    - Gray Kanarek
    - Bryan Hilbert

Use
---

    The functions within this module are intended to be imported and
    used by ``views.py``, e.g.:

    ::
        from .bokeh_containers import dark_monitor_tabs
"""

import os

from bokeh.embed import components
from bokeh.layouts import layout
from bokeh.models.widgets import Tabs, Panel
from bokeh.plotting import figure, output_file
import numpy as np

from . import monitor_pages
from jwql.utils.constants import BAD_PIXEL_TYPES, FULL_FRAME_APERTURES
from jwql.utils.utils import get_config

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')
PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]


def add_limit_boxes(fig, yellow=None, red=None):
    """Add gree/yellow/red background colors

    Parameters
    ----------
    fig : bokeh.plotting.figure
        Bokeh figure of the telemetry values

    yellow : tup
        2-Tuple of (low, high) values. If provided, the areas of the plot less than <low>
        and greater than <high> will be given a yellow background, to indicate an area
        of concern.

    red : tup
        2-Tuple of (low, high) values. If provided, the areas of the plot less than <low>
        and greater than <high> will be given a red background, to indicate values that
        may indicate an error. It is assumed that the low value of red is less
        than the low value of yellow, and that the high value of red is
        greater than the high value of yellow.
    """
    if yellow is not None:
        green = BoxAnnotation(bottom=yellow_limits[0], top=yellow_limits[1], fill_color='chartreuse', fill_alpha=0.2)
        fig.add_layout(green)
        if red is not None:
            yellow_high = BoxAnnotation(bottom=yellow_limits[1], top=red_limits[1], fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_high)
            yellow_low = BoxAnnotation(bottom=red_limits[0], top=yellow_limits[0], fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_low)
            red_high = BoxAnnotation(bottom=red_limits[1], top=red_limits[1] + 100, fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_high)
            red_low = BoxAnnotation(bottom=red_limits[0] - 100, top=red_limits[0], fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_low)
        else:
            yellow_high = BoxAnnotation(bottom=yellow_limits[1], top=yellow_limits[1] + 100, fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_high)
            yellow_low = BoxAnnotation(bottom=yellow_limits[0] - 100, top=yellow_limits[0], fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_low)
    else:
        if red is not None:
            green = BoxAnnotation(bottom=red_limits[0], top=red_limits[1], fill_color='chartreuse', fill_alpha=0.2)
            fig.add_layout(green)
            red_high = BoxAnnotation(bottom=red_limits[1], top=red_limits[1] + 100, fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_high)
            red_low = BoxAnnotation(bottom=red_limits[0] - 100, top=red_limits[0], fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_low)
    return fig


def bad_pixel_monitor_tabs(instrument):
    """Creates the various tabs of the bad pixel monitor results page.

    Parameters
    ----------
    instrument : str
        The JWST instrument of interest (e.g. ``nircam``).

    Returns
    -------
    div : str
        The HTML div to render bad pixel monitor plots
    script : str
        The JS script to render bad pixel monitor plots
    """
    full_apertures = FULL_FRAME_APERTURES[instrument.upper()]

    templates_all_apertures = {}
    for aperture in full_apertures:

        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        monitor_template = monitor_pages.BadPixelMonitor()

        # Set instrument and monitor using DarkMonitor's setters
        monitor_template.aperture_info = (instrument, aperture)
        templates_all_apertures[aperture] = monitor_template

    # for reference - here are the bad pixel types
    # badpix_types_from_flats = ['DEAD', 'LOW_QE', 'OPEN', 'ADJ_OPEN']
    # badpix_types_from_darks = ['HOT', 'RC', 'OTHER_BAD_PIXEL', 'TELEGRAPH']

    # We loop over detectors here, and create one tab per detector, rather
    # than one tab for each plot type, as is done with the dark monitor
    all_tabs = []
    for aperture_name, template in templates_all_apertures.items():

        tab_plots = []
        # Add the image of bad pixels found in darks
        dark_image = template.refs["dark_position_figure"]
        dark_image.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
        tab_plots.append(dark_image)

        # Add the image of bad pixels found in flats
        flat_image = template.refs["flat_position_figure"]
        flat_image.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
        tab_plots.append(flat_image)

        # Add history plots
        for badpix_type in BAD_PIXEL_TYPES:
            history = template.refs["{}_history_figure".format(badpix_type.lower())]
            history.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
            tab_plots.append(history)

        # Let's put two plots per line
        badpix_layout = layout(
            tab_plots[0:2],
            tab_plots[2:4],
            tab_plots[4:6],
            tab_plots[6:8],
            tab_plots[8:10]
        )

        badpix_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
        badpix_tab = Panel(child=badpix_layout, title=aperture_name)
        all_tabs.append(badpix_tab)

    # Build tabs
    tabs = Tabs(tabs=all_tabs)

    # Return tab HTML and JavaScript to web app
    script, div = components(tabs)

    return div, script


def bias_monitor_tabs(instrument):
    """Creates the various tabs of the bias monitor results page.

    Parameters
    ----------
    instrument : str
        The JWST instrument of interest (e.g. ``nircam``).

    Returns
    -------
    div : str
        The HTML div to render bias monitor plots
    script : str
        The JS script to render bias monitor plots
    """

    # Make a separate tab for each aperture
    tabs = []
    for aperture in FULL_FRAME_APERTURES[instrument.upper()]:
        monitor_template = monitor_pages.BiasMonitor()
        monitor_template.input_parameters = (instrument, aperture)

        # Add the mean bias vs time plots for each amp and odd/even columns
        plots = []
        for amp in ['1', '2', '3', '4']:
            for kind in ['even', 'odd']:
                bias_plot = monitor_template.refs['mean_bias_figure_amp{}_{}'.format(amp, kind)]
                bias_plot.sizing_mode = 'scale_width'  # Make sure the sizing is adjustable
                plots.append(bias_plot)

        # Add the calibrated 0th group image
        calibrated_image = monitor_template.refs['cal_image']
        calibrated_image.sizing_mode = 'scale_width'
        calibrated_image.margin = (0, 100, 0, 100)  # Add space around sides of figure
        plots.append(calibrated_image)

        # Add the calibrated 0th group histogram
        if instrument == 'NIRISS':
            calibrated_hist = monitor_template.refs['cal_hist']
            calibrated_hist.sizing_mode = 'scale_width'
            calibrated_hist.margin = (0, 190, 0, 190)
            plots.append(calibrated_hist)

        # Add the collapsed row/column plots
        if instrument != 'NIRISS':
            for direction in ['rows', 'columns']:
                collapsed_plot = monitor_template.refs['collapsed_{}_figure'.format(direction)]
                collapsed_plot.sizing_mode = 'scale_width'
                plots.append(collapsed_plot)

        # Put the mean bias plots on the top 2 rows, the calibrated image on the
        # third row, and the remaining plots on the bottom row.
        bias_layout = layout(
            plots[0:8][::2],
            plots[0:8][1::2],
            plots[8:9],
            plots[9:]
        )
        bias_layout.sizing_mode = 'scale_width'
        bias_tab = Panel(child=bias_layout, title=aperture)
        tabs.append(bias_tab)

    # Build tabs
    tabs = Tabs(tabs=tabs)

    # Return tab HTML and JavaScript to web app
    script, div = components(tabs)

    return div, script


def cosmic_ray_monitor_tabs(instrument):
    """Creates the various tabs of the cosmic monitor results page.

    Parameters
    ----------
    instrument : str
        The JWST instrument of interest (e.g. ``nircam``).

    Returns
    -------
    div : str
        The HTML div to render cosmic ray monitor plots
    script : str
        The JS script to render cosmic ray monitor plots
    """

    full_apertures = FULL_FRAME_APERTURES[instrument.upper()]

    histograms_all_apertures = []
    history_all_apertures = []
    for aperture in full_apertures:

        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        monitor_template = monitor_pages.CosmicRayMonitor(instrument.lower(), aperture)

        # Set instrument and monitor using CosmicRayMonitor's setters
        # monitor_template.aperture_info = (instrument, aperture)
        # templates_all_apertures[aperture] = monitor_template
        histograms_all_apertures.append(monitor_template.histogram_figure)
        history_all_apertures.append(monitor_template.history_figure)

    if instrument.lower() == 'nircam':
        # Histogram tab
        a1, a2, a3, a4, a5, b1, b2, b3, b4, b5 = histograms_all_apertures
        histogram_layout = layout(
            [a2, a4, b3, b1],
            [a1, a3, b4, b2],
            [a5, b5]
        )

        # CR Rate History tab
        a1_line, a2_line, a3_line, a4_line, a5_line, b1_line, b2_line, b3_line, b4_line, b5_line = history_all_apertures
        line_layout = layout(
            [a2_line, a4_line, b3_line, b1_line],
            [a1_line, a3_line, b4_line, b2_line],
            [a5_line, b5_line]
        )

    elif instrument.lower() in ['miri', 'niriss', 'nirspec']:
        # Histogram tab
        single_aperture = histograms_all_apertures[0]
        histogram_layout = layout(
            [single_aperture]
        )

        # CR Rate History tab
        single_aperture_line = history_all_apertures[0]
        line_layout = layout(
            [single_aperture_line]
        )

    elif instrument.lower() == 'fgs':
        # Histogram tab
        g1, g2 = histograms_all_apertures
        histogram_layout = layout([g1, g2])

        # CR Rate History tab
        g1_line, g2_line = history_all_apertures
        line_layout = layout([g1_line, g2_line])

    # Allow figure sizes to scale with window
    histogram_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    histogram_tab = Panel(child=histogram_layout, title="Histogram")
    line_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    line_tab = Panel(child=line_layout, title="Trending")

    # Build tabs
    tabs = Tabs(tabs=[histogram_tab, line_tab])

    # Return tab HTML and JavaScript to web app
    script, div = components(tabs)

    return div, script


def dark_monitor_tabs(instrument):
    """Creates the various tabs of the dark monitor results page.

    Parameters
    ----------
    instrument : str
        The JWST instrument of interest (e.g. ``nircam``).

    Returns
    -------
    div : str
        The HTML div to render dark monitor plots
    script : str
        The JS script to render dark monitor plots
    """
    get all dark data here. then loop over the apertures and call
    the monitor_dark_bokeh.DarkMonitor for each.
    # Apertures that do not correspond to single subarrays on a detector
    apertures_to_skip = ['NRCALL_FULL', 'NRCAS_FULL', 'NRCBS_FULL']

    # This will query for the data and produce the plots
    plot_list, or_something = DarkMonitorPlots(instrument)

    # Now we need to organize the plots into Panels, etc.



    full_apertures = FULL_FRAME_APERTURES[instrument.upper()]

    templates_all_apertures = {}
    for aperture in full_apertures:

        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        monitor_template = monitor_pages.DarkMonitor(instrument, aperture)

        # Set instrument and monitor using DarkMonitor's setters
        monitor_template.aperture_info = (instrument, aperture)
        templates_all_apertures[aperture] = monitor_template

    # Histogram tab
    histograms_all_apertures = []
    for aperture_name, template in templates_all_apertures.items():
        histogram = template.refs["dark_full_histogram_figure"]
        histogram.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
        histograms_all_apertures.append(histogram)

    if instrument == 'NIRCam':
        a1, a2, a3, a4, a5, b1, b2, b3, b4, b5 = histograms_all_apertures
        histogram_layout = layout(
            [a2, a4, b3, b1],
            [a1, a3, b4, b2],
            [a5, b5]
        )

    elif instrument in ['NIRISS', 'MIRI']:
        single_aperture = histograms_all_apertures[0]
        histogram_layout = layout(
            [single_aperture]
        )

    elif instrument in ['NIRSpec', 'FGS']:
        d1, d2 = histograms_all_apertures
        histogram_layout = layout(
            [d1, d2]
        )

    histogram_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    histogram_tab = Panel(child=histogram_layout, title="Histogram")

    # Current v. time tab
    lines_all_apertures = []
    for aperture_name, template in templates_all_apertures.items():
        line = template.refs["dark_current_time_figure"]
        line.title.align = "center"
        line.title.text_font_size = "20px"
        line.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
        lines_all_apertures.append(line)

    if instrument == 'NIRCam':
        a1, a2, a3, a4, a5, b1, b2, b3, b4, b5 = lines_all_apertures
        line_layout = layout(
            [a2, a4, b3, b1],
            [a1, a3, b4, b2],
            [a5, b5]
        )

    elif instrument in ['NIRISS', 'MIRI']:
        single_aperture = lines_all_apertures[0]
        line_layout = layout(
            [single_aperture]
        )

    elif instrument in ['NIRSpec', 'FGS']:
        d1, d2 = lines_all_apertures
        line_layout = layout(
            [d1, d2]
        )

    line_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    line_tab = Panel(child=line_layout, title="Trending")

    # Mean dark image tab

    # The three lines below work for displaying a single image
    image = templates_all_apertures[full_apertures[0]].refs["mean_dark_image_figure"]
    image.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    image_layout = layout(image)
    image.height = 250  # Not working
    image_layout.sizing_mode = "scale_width"
    image_tab = Panel(child=image_layout, title="Mean Dark Image")

    # Build tabs
    tabs = Tabs(tabs=[histogram_tab, line_tab, image_tab])

    # Return tab HTML and JavaScript to web app
    script, div = components(tabs)

    return div, script


def edb_monitor_tabs(instrument):
    """Creates the various tabs of the dark monitor results page.

    Parameters
    ----------
    instrument : str
        The JWST instrument of interest (e.g. ``nircam``).

    Returns
    -------
    div : str
        The HTML div to render dark monitor plots
    script : str
        The JS script to render dark monitor plots
    """
    html_file_list = file_list[instrument]
    print('read in html files')


def generic_telemetry_plot(times, values, name, nominal_value=None, yellow_limits=None,
                           red_limits=None, save=True):
    """Create a value versus time plot of a single telemetry mnemonic. Optionally
    add background colors corresponding to good (green), warning (yellow), and red
    (error) values.

    Parameters
    ----------
    times : list
        List of datetime instances

    values : list
        Telemetry values

    name : str
        Name of the telemetry mnemonic (e.g. 'SE_ZINRCICE1')

    nominal_value : float
        Optional expected value for the mnemonic. If provided, a horizontal dashed line
        at this value will be added to the plot.

    yellow_limits : tup
        Tuple of (low, high) values. If provided, the areas of the plot less than <low>
        and greater than <high> will be given a yellow background, to indicate an area
        of concern.

    red_limits : tup
        Tuple of (low, high) values. If provided, the areas of the plot less than <low>
        and greater than <high> will be given a red background, to indicate values that
        may indicate an error. It is assumed that the low value of red_limits is less
        than the low value of yellow_limits, and that the high value of red_limits is
        greater than the high value of yellow_limits.

    save : bool
        If True, save the plot to an html file.

    Returns
    -------
    fig : bokeh.plotting.figure
        Telemetry plot object
    """
    if save:
        output_file(f"telem_plot_{name}.html")

    fig = figure(width=400, height=400, x_axis_label='Date', y_axis_label='Voltage',
                 x_axis_type='datetime')
    fig.circle(times, values, size=4, color='navy', alpha=0.5)

    if nominal_value is not None:
        fig.line(times, np.repeat(nominal_value, len(times)), line_dash='dashed')

    fig.xaxis.formatter = DatetimeTickFormatter(hours=["%d %b %H:%M"],
                                                days=["%d %b %H:%M"],
                                                months=["%d %b %Y %H:%M"],
                                                years=["%d %b %Y"],
                                                )
    fig.xaxis.major_label_orientation = np.pi / 4

    fig = add_limit_boxes(fig, yellow=yellow_limits, red=red_limits)

    return fig


def identify_dark_monitor_tables(instrument):
    """Determine which dark current database tables as associated with
    a given instrument"""

    mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]
    query_table = eval('{}DarkQueryHistory'.format(mixed_case_name))
    pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
    stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))
    return query_table, pixel_table, stats_table


def readnoise_monitor_tabs(instrument):
    """Creates the various tabs of the readnoise monitor results page.

    Parameters
    ----------
    instrument : str
        The JWST instrument of interest (e.g. ``nircam``).

    Returns
    -------
    div : str
        The HTML div to render readnoise monitor plots
    script : str
        The JS script to render readnoise monitor plots
    """

    # Make a separate tab for each aperture
    tabs = []
    for aperture in FULL_FRAME_APERTURES[instrument.upper()]:
        monitor_template = monitor_pages.ReadnoiseMonitor()
        monitor_template.input_parameters = (instrument, aperture)

        # Add the mean readnoise vs time plots for each amp
        plots = []
        for amp in ['1', '2', '3', '4']:
            readnoise_plot = monitor_template.refs['mean_readnoise_figure_amp{}'.format(amp)]
            readnoise_plot.sizing_mode = 'scale_width'  # Make sure the sizing is adjustable
            plots.append(readnoise_plot)

        # Add the readnoise difference image
        readnoise_diff_image = monitor_template.refs['readnoise_diff_image']
        readnoise_diff_image.sizing_mode = 'scale_width'
        readnoise_diff_image.margin = (0, 100, 0, 100)  # Add space around sides of figure
        plots.append(readnoise_diff_image)

        # Add the readnoise difference histogram
        readnoise_diff_hist = monitor_template.refs['readnoise_diff_hist']
        readnoise_diff_hist.sizing_mode = 'scale_width'
        readnoise_diff_hist.margin = (0, 190, 0, 190)
        plots.append(readnoise_diff_hist)

        # Put mean readnoise plots on the top row, difference image on the
        # second row, and difference histogram on the bottom row.
        readnoise_layout = layout(
            plots[0:4],
            plots[4:5],
            plots[5:6]
        )
        readnoise_layout.sizing_mode = 'scale_width'
        readnoise_tab = Panel(child=readnoise_layout, title=aperture)
        tabs.append(readnoise_tab)

    # Build tabs
    tabs = Tabs(tabs=tabs)

    # Return tab HTML and JavaScript to web app
    script, div = components(tabs)

    return div, script
