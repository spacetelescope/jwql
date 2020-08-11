"""This module contains code for the bad pixel monitor Bokeh plots.

Author
------

    - Bryan Hilbert

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.BadPixelMonitor('NIRCam', 'NRCA3_FULL')
        script, div = monitor_template.embed("bad_pixel_time_figure")
"""

import os

from astropy.io import fits
from astropy.time import Time
from bokeh.models.tickers import LogTicker
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamBadPixelQueryHistory, NIRCamBadPixelStats
from jwql.database.database_interface import NIRISSBadPixelQueryHistory, NIRISSBadPixelStats
from jwql.database.database_interface import MIRIBadPixelQueryHistory, MIRIBadPixelStats
from jwql.database.database_interface import NIRSpecBadPixelQueryHistory, NIRSpecBadPixelStats
from jwql.database.database_interface import FGSBadPixelQueryHistory, FGSBadPixelStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config
from jwql.bokeh_templating import BokehTemplate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class BadPixelMonitor(BokehTemplate):

    # Combine instrument and aperture into a single property because we
    # do not want to invoke the setter unless both are updated
    @property
    def aperture_info(self):
        return (self._instrument, self._aperture)

    @aperture_info.setter
    def aperture_info(self, info):
        self._instrument, self._aperture = info
        self.pre_init()
        self.post_init()

    def _dark_mean_image(self):
        """Update bokeh objects with mean dark image data."""

        # Open the mean dark current file and get the data
        mean_dark_image_file = self.pixel_table[-1].mean_dark_image_file
        mean_slope_dir = os.path.join(get_config()['outputs'], 'dark_monitor', 'mean_slope_images')
        mean_dark_image_path = os.path.join(mean_slope_dir, mean_dark_image_file)
        with fits.open(mean_dark_image_path) as hdulist:
            data = hdulist[1].data

        # Update the plot with the data and boundaries
        y_size, x_size = np.shape(data)
        self.refs["mean_dark_source"].data['image'] = [data]
        self.refs["stamp_xr"].end = x_size
        self.refs["stamp_yr"].end = y_size
        self.refs["mean_dark_source"].data['dw'] = [x_size]
        self.refs["mean_dark_source"].data['dh'] = [x_size]

        # Set the image color scale
        self.refs["log_mapper"].high = 0
        self.refs["log_mapper"].low = -.2

        # This should add ticks to the colorbar, but it doesn't
        self.refs["mean_dark_cbar"].ticker = LogTicker()

        # Add a title
        self.refs['mean_dark_image_figure'].title.text = self._aperture
        self.refs['mean_dark_image_figure'].title.align = "center"
        self.refs['mean_dark_image_figure'].title.text_font_size = "20px"

    def pre_init(self):
        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        try:
            dummy_instrument = self._instrument
            dummy_aperture = self._aperture
        except AttributeError:
            self._instrument = 'NIRCam'
            self._aperture = 'NRCA1_FULL'

        self._embed = True

        # Fix aperture/detector name discrepency
        if self._aperture in ['NRCA5_FULL', 'NRCB5_FULL']:
            self.detector = '{}LONG'.format(self._aperture[0:4])
        else:
            self.detector = self._aperture.split('_')[0]

        # App design
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, "yaml", "badpixel_monitor_interface.yaml")

        # Load data tables
        self.load_data()

        # Data for mean dark versus time plot
        datetime_stamps = [row.obs_mid_time for row in self.badpixel_table]
        times = Time(datetime_stamps, format='datetime', scale='utc')  # Convert to MJD
        self.timestamps = times.mjd


        replace the line below with a new function? We need the number of bad pixels for
        each flavor of bad pixel versus time
        self.dark_current = [row.mean for row in self.badpixel_table]

        something like this, where self.bad_pixels is a dictionary with keys equal
        to aperture names (e.g. NRCA1_FULL)
        self.bad_pixels = XXXX.bad_pixel_trends()

        We also want to retrieve the information for just the most recent entry for each
        bad pixel type. We will print the coordinates of the most-recently found bad pixels
        in a table, and show an image (or maybe just a blank 2048x2048 grid) with dots at
        the locations of the new bad pixels.

        So for each type of bad pixel, that's three panels.
        1) bad pixel count vs time
        2) plot of latest locations
        3) table of latest bad pix - API view, so users can download

        for badpix_type in BAD_PIXEL_TYPES:
            entries = [row for row in self.badpixel_table if row.type == badpix_type]
            time_stamps = [row.obs_mid_time for row in entries]
            latest_timestamp = time_stamps[-1].isoformat()
            latest_xcoord = entries[-1].x_coord
            latest_ycoord = entries[-1].y_coord




        # Data for dark current histogram plot (full detector)
        # Just show the last histogram, which is the one most recently
        # added to the database
        last_hist_index = -1
        self.last_timestamp = datetime_stamps[last_hist_index].isoformat()
        self.full_dark_bin_center = np.array([row.hist_dark_values for
                                              row in self.dark_table])[last_hist_index]
        self.full_dark_amplitude = [row.hist_amplitudes for
                                    row in self.dark_table][last_hist_index]
        self.full_dark_bottom = np.zeros(len(self.full_dark_amplitude))
        deltas = self.full_dark_bin_center[1:] - self.full_dark_bin_center[0: -1]
        self.full_dark_bin_width = np.append(deltas[0], deltas)

    def post_init(self):

        self._update_dark_v_time()
        self._update_hist()
        self._dark_mean_image()

    def identify_tables(self):
        """Determine which dark current database tables as associated with
        a given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.query_table = eval('{}BadPixelQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}BadPixelStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data with a matching aperture
        self.badpixel_table = session.query(self.pixel_table) \
            .filter(self.pixel_table.detector == self.detector) \
            .all()

    def _update_dark_v_time(self):

        # Define y range of dark current v. time plot
        buffer_size = 0.05 * (max(self.dark_current) - min(self.dark_current))
        self.refs['dark_current_yrange'].start = min(self.dark_current) - buffer_size
        self.refs['dark_current_yrange'].end = max(self.dark_current) + buffer_size

        # Define x range of dark current v. time plot
        horizontal_half_buffer = (max(self.timestamps) - min(self.timestamps)) * 0.05
        if horizontal_half_buffer == 0:
            horizontal_half_buffer = 1.  # day
        self.refs['dark_current_xrange'].start = min(self.timestamps) - horizontal_half_buffer
        self.refs['dark_current_xrange'].end = max(self.timestamps) + horizontal_half_buffer

        # Add a title
        self.refs['dark_current_time_figure'].title.text = self._aperture
        self.refs['dark_current_time_figure'].title.align = "center"
        self.refs['dark_current_time_figure'].title.text_font_size = "20px"

    def _update_hist(self):

        # Define y range of dark current histogram
        buffer_size = 0.05 * (max(self.full_dark_amplitude) - min(self.full_dark_bottom))
        self.refs['dark_histogram_yrange'].start = min(self.full_dark_bottom)
        self.refs['dark_histogram_yrange'].end = max(self.full_dark_amplitude) + buffer_size

        # Define x range of dark current histogram
        self.refs['dark_histogram_xrange'].start = min(self.full_dark_bin_center)
        self.refs['dark_histogram_xrange'].end = max(self.full_dark_bin_center)

        # Add a title
        self.refs['dark_full_histogram_figure'].title.text = self._aperture
        self.refs['dark_full_histogram_figure'].title.align = "center"
        self.refs['dark_full_histogram_figure'].title.text_font_size = "20px"
