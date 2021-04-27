"""Various functions to generate Bokeh objects to be used by the
``views`` of the ``jwql`` app.

This module contains several functions that instantiate
``BokehTemplate`` objects to be rendered in ``views.py``.

Authors
-------

    - Gray Kanarek

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

from . import monitor_pages
from jwql.utils.constants import BAD_PIXEL_TYPES, FULL_FRAME_APERTURES
from jwql.utils.utils import get_config

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')
PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]


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

    full_apertures = FULL_FRAME_APERTURES[instrument.upper()]

    templates_all_apertures = {}
    for aperture in full_apertures:

        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        monitor_template = monitor_pages.DarkMonitor()

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

    elif instrument == 'NIRSpec':
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

    elif instrument == 'NIRSpec':
        d1, d2 = lines_all_apertures
        line_layout = layout(
            [d1, d2]
        )

    line_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    line_tab = Panel(child=line_layout, title="Trending")

    # Mean dark image tab

    # The three lines below work for displaying a single image
    image = templates_all_apertures['NRCA3_FULL'].refs["mean_dark_image_figure"]
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
