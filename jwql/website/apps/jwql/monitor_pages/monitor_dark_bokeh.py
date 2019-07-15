#! /usr/bin/env python

"""This module contains code for the dark current monitor Bokeh plots.


Author
------

    - Bryan Hilbert
    - Gray Kanarek
    - Lauren Chambers

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.DarkMonitor('NIRCam', 'NRCA3_FULL')
        script, div = monitor_template.embed("dark_current_time_figure")
"""

import os

from astropy.time import Time
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamDarkQueryHistory, NIRCamDarkPixelStats, NIRCamDarkDarkCurrent
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config
from jwql.bokeh_templating import BokehTemplate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class DarkMonitor(BokehTemplate):

    def pre_init(self, instrument, aperture):

        self._embed = True
        self.instrument = instrument
        self.aperture = aperture
        self.detector = aperture.split('_')[0]

        # App design
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, "yaml", "monitor_dark_interface.yaml")

        self.settings = get_config()
        self.output_dir = self.settings['outputs']

        # Load data tables
        self.load_data()

        # Data for mean dark versus time plot
        # TODO: how to get the time of the data, not the database entry?
        datetime_stamps = [row.entry_date for row in self.dark_table]
        # Convert to MJD
        times = Time(datetime_stamps, format='datetime', scale='utc')
        self.timestamps = times.mjd
        self.dark_current = [row.mean for row in self.dark_table]

        # Data for dark current histogram plot (full detector)
        # TODO: how to show multiple histograms? here just showing last.
        last_hist_index = -1
        self.full_dark_bin_center = np.array([row.hist_dark_values for row in self.dark_table])[last_hist_index]
        self.full_dark_amplitude = [row.hist_amplitudes for row in self.dark_table][last_hist_index]
        self.full_dark_bottom = np.zeros(len(self.full_dark_amplitude))
        self.full_dark_bin_width = self.full_dark_bin_center[1:] - self.full_dark_bin_center[0: -1]

    def post_init(self):

        # Define y range of dark current v. time plot
        self.refs['dark_current_yrange'].start = min(self.dark_current)
        self.refs['dark_current_yrange'].end = max(self.dark_current)

        # Define x range of dark current v. time plot
        self.refs['dark_current_xrange'].start = min(self.timestamps)
        self.refs['dark_current_xrange'].end = max(self.timestamps)

        # Define y range of dark current histogram
        self.refs['dark_histogram_yrange'].start = min(self.full_dark_bottom)
        self.refs['dark_histogram_yrange'].end = max(self.full_dark_amplitude)

        # Define x range of dark current histogram
        self.refs['dark_histogram_xrange'].start = min(self.full_dark_bin_center)
        self.refs['dark_histogram_xrange'].end = max(self.full_dark_bin_center)


    def identify_tables(self):
        """Determine which dark current database tables as associated with
        a given instrument
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.query_table = eval('{}DarkQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
        self.stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))

    def load_data(self, aperture=None):
        """Given a set of coordinates of bad pixels, determine which of
        these pixels have been previously identified and remove them
        from the list

        Parameters
        ----------
        badpix : tuple
            Tuple of lists containing x and y pixel coordinates. (Output
            of ``numpy.where`` call)

        pixel_type : str
            Type of bad pixel being examined. Options are ``hot``,
            ``dead``, and ``noisy``

        Returns
        -------
        new_pixels_x : list
            List of x coordinates of new bad pixels

        new_pixels_y : list
            List of y coordinates of new bad pixels
        """

        # call this function "load_mean_dark" or something more specific than "load_data"

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in NIRCamDarkDarkCurrent with a matching aperture
        self.dark_table = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self.aperture) \
            .all()

        # self.pix_table = session.query(self.pixel_table) \
        #     .filter(self.pixel_table.detector == self.detector) \
        #     .all()

# DarkMonitor()
