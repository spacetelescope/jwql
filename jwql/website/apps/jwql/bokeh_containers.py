"""Various functions to generate Bokeh objects to be used by the ``views`` of
the ``jwql`` app.

This module contains several functions that instantiate BokehTemplate objects
to be rendered in ``views.py`` for use by the ``jwql`` app.

Authors
-------

    - Gray Kanarek

Use
---

    The functions within this module are intended to be imported and
    used by ``views.py``, e.g.:

    ::
        from .data_containers import get_mast_monitor
"""

import glob
import os

from astropy.io import fits
from bokeh.embed import components
from bokeh.layouts import layout
from bokeh.models.widgets import Tabs, Panel
import numpy as np
import pysiaf

from . import monitor_pages
from jwql.utils.utils import get_config

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')
PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]

def dark_monitor_tabs(inst):
    """WRITE ME
    """
    # siaf_instrument = pysiaf.Siaf(inst)
    # full_apertures = [ap for ap in siaf_instrument.apernames if ap.endswith('FULL')]
    if inst == 'NIRCam':
        full_apertures = ['NRCA1_FULL', 'NRCA2_FULL', 'NRCA3_FULL', 'NRCA4_FULL',
                          'NRCA5_FULL', 'NRCB1_FULL', 'NRCB2_FULL', 'NRCB3_FULL',
                          'NRCB4_FULL', 'NRCB5_FULL']

    templates_all_apertures = {}
    for ap in full_apertures:
        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        monitor_template = monitor_pages.DarkMonitor()

        # Set instrument and monitor using DarkMonitor's setters
        monitor_template.aperture_info = (inst, ap)
        templates_all_apertures[ap] = monitor_template

    # Histogram tab
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    histograms_all_apertures = []
    for apername, template in templates_all_apertures.items():
        hist = template.refs["dark_full_histogram_figure"]
        #hist = template.get_bokeh_element("dark_full_histogram_figure")
        hist.sizing_mode = "scale_width"  # Make sure the sizing is adjustable

        histograms_all_apertures.append(hist)

    a1, a2, a3, a4, a5, b1, b2, b3, b4, b5 = histograms_all_apertures
    hist_layout = layout(
        [a2, a4, b3, b1],
        [a1, a3, b4, b2],
        [a5, b5]
    )
    hist_layout.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    hist_tab = Panel(child=hist_layout, title="Histogram")

    # Current v. time tab
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #line = monitor_template.get_bokeh_element("dark_current_time_figure")
    line = monitor_template.refs["dark_current_time_figure"]
    line.sizing_mode = "scale_width"  # Make sure the sizing is adjustable

    # Add a title
    line.title.text = "Dark Current v. Time"
    line.title.align = "center"
    line.title.text_font_size = "20px"

    # Make it shorter and thicker lines
    line.height = 250

    line_layout = layout(line)
    line_layout.sizing_mode = "scale_width"
    line_tab = Panel(child=line_layout, title="Trending")

    # Mean dark image tab
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #image = templates_all_apertures['NRCA3_FULL'].get_bokeh_element("mean_dark_image_figure")
    image = templates_all_apertures['NRCA3_FULL'].refs["mean_dark_image_figure"]
    image.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    image_layout = layout(image)

    # images_all_apertures = []
    # for apername, template in templates_all_apertures.items():
    #     if '5' not in apername:
    #         image = template.get_bokeh_element("mean_dark_image_figure")
    #         image.sizing_mode = "scale_width"  # Make sure the sizing is adjustable
    #
    #         images_all_apertures.append(image)
    #
    # a1, a2, a3, a4, b1, b2, b3, b4 = images_all_apertures
    # image_layout = layout(
    #     [a2, a4, b3, b1],
    #     [a1, a3, b4, b2]
    # )

    image.height = 250  # Not working

    image_layout.sizing_mode = "scale_width"
    image_tab = Panel(child=image_layout, title="Mean Dark Image")

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Build tabs
    tabs = Tabs(tabs=[hist_tab, line_tab, image_tab])

    # Return tab HTML and JavaScript to web app
    script, div = components(tabs)

    return div, script
