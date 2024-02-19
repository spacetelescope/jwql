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
from bokeh.models import TabPanel, Tabs, DatetimeTickFormatter
from bokeh.plotting import figure, output_file
import numpy as np
import pysiaf

from jwql.website.apps.jwql import monitor_pages
from jwql.website.apps.jwql.monitor_pages.monitor_dark_bokeh import DarkMonitorPlots
from jwql.utils.constants import BAD_PIXEL_TYPES, FULL_FRAME_APERTURES
from jwql.utils.utils import get_config

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')
PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]
TEMPLATE_DIR = os.path.join(PACKAGE_DIR, 'website/apps/jwql/templates')


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
    histogram_tab = TabPanel(child=histogram_layout, title="Histogram")
    line_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    line_tab = TabPanel(child=line_layout, title="Trending")

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
    # This will query for the data and produce the plots
    plots = DarkMonitorPlots(instrument)

    # Define the layout for each plot type
    histogram_layout = standard_monitor_plot_layout(instrument, plots.hist_plots)
    trending_layout = standard_monitor_plot_layout(instrument, plots.trending_plots)
    image_layout = standard_monitor_plot_layout(instrument, plots.dark_image_data)

    # Create a tab for each type of plot
    histogram_tab = TabPanel(child=histogram_layout, title="Dark Rate Histogram")
    line_tab = TabPanel(child=trending_layout, title="Trending")
    image_tab = TabPanel(child=image_layout, title="Mean Dark Image")

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

    fig.xaxis.formatter = DatetimeTickFormatter(hours="%d %b %H:%M",
                                                days="%d %b %H:%M",
                                                months="%d %b %Y %H:%M",
                                                years="%d %b %Y"
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
        readnoise_tab = TabPanel(child=readnoise_layout, title=aperture)
        tabs.append(readnoise_tab)

    # Build tabs
    tabs = Tabs(tabs=tabs)

    # Return tab HTML and JavaScript to web app
    script, div = components(tabs)

    return div, script


def standard_monitor_plot_layout(instrument, plots):
    """Arrange a set of plots into a bokeh layout. The layout will
    show the plots for full frame apertures in an orientation that
    matches the relative detector locations within the instrument.
    Any subarray aperture plots will be arranged below the full frame
    plots, with 4 plots to a row, in an order matching that in pysiaf's
    aperture list. This function assumes that there are plots for all full
    frame apertures present.

    Parameters
    ----------
    instrument : str
        Name of the instrument that the plots are for

    plots : dict
        Dictionary containing a set of plots for an instrument.
        Keys are aperture names (e.g. NRCA1_FULL) and values are the
        plots (bokeh figures)

    Returns
    -------
    plot_layout : bokeh.layouts.layout
    """
    # Generate nested lists of the full frame apertures, which will be shown at the top
    # of the tab. Note that order below is intentional. It mimics the detectors' locations
    # relative to one another in the focal plane.
    if instrument.lower() == 'nircam':
        full_frame_lists = [
            [plots['NRCA2_FULL'], plots['NRCA4_FULL'], plots['NRCB3_FULL'], plots['NRCB1_FULL']],
            [plots['NRCA1_FULL'], plots['NRCA3_FULL'], plots['NRCB4_FULL'], plots['NRCB2_FULL']],
            [plots['NRCA5_FULL'], plots['NRCB5_FULL']]
        ]
    elif instrument.lower() == 'niriss':
        full_frame_lists = [
            [plots['NIS_CEN']]
            ]
    elif instrument.lower() == 'miri':
        full_frame_lists = [
            [plots['MIRIM_FULL']]
        ]
    elif instrument.lower() == 'nirspec':
        full_frame_lists = [
            [plots['NRS1_FULL'], plots['NRS2_FULL']]
        ]
    elif instrument.lower() == 'fgs':
        full_frame_lists = [
            [plots['FGS1_FULL'], plots['FGS2_FULL']]
        ]

    # Next create lists of subarrays. Keep the subarrays in the order in which
    # they exist in pyiaf, in order to make the page a little more readable.
    # The dark monitor also populates aperture names using pysiaf.
    subarrs = [p for p in plots.keys() if p not in FULL_FRAME_APERTURES[instrument.upper()]]
    siaf = pysiaf.Siaf(instrument.lower())
    all_apertures = np.array(list(siaf.apernames))

    indexes = []
    for key in subarrs:
        subarr_plot_idx = np.where(all_apertures == key)[0]
        if len(subarr_plot_idx) > 0:
            indexes.append(subarr_plot_idx[0])
    to_sort = np.argsort(indexes)
    sorted_keys = np.array(subarrs)[to_sort]

    # Place 4 subarray plots in each row. Generate a nested
    # list where each sublist contains the plots to place in
    # a given row
    subarr_plots_per_row = 4
    first_col = np.arange(0, len(sorted_keys), 4)

    subarr_lists = []
    for idx in first_col:
        row_keys = sorted_keys[idx: idx + subarr_plots_per_row]
        row_list = [plots[key] for key in row_keys]
        subarr_lists.append(row_list)

    # Combine full frame and subarray aperture lists
    full_list = full_frame_lists + subarr_lists

    # Now create a layout that holds the lists
    plot_layout = layout(full_list)

    return plot_layout
