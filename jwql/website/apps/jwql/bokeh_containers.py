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
from jwql.utils.constants import FULL_FRAME_APERTURES
from jwql.utils.utils import get_config

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')
PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]


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
