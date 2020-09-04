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
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamBadPixelQueryHistory, NIRCamBadPixelStats
from jwql.database.database_interface import NIRISSBadPixelQueryHistory, NIRISSBadPixelStats
from jwql.database.database_interface import MIRIBadPixelQueryHistory, MIRIBadPixelStats
from jwql.database.database_interface import NIRSpecBadPixelQueryHistory, NIRSpecBadPixelStats
from jwql.database.database_interface import FGSBadPixelQueryHistory, FGSBadPixelStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config, filesystem_path
from jwql.bokeh_templating import BokehTemplate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


BAD_PIXEL_TYPES = ['DEAD', 'HOT', 'LOW_QE', 'OPEN', 'ADJ_OPEN', 'RC', 'OTHER_BAD_PIXEL', 'TELEGRAPH']

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

    def bad_pixel_history(self, bad_type):
        """Use the database to construct information on the total number
        of a given type of bad pixels over time

        Parameters
        ----------
        bad_type : str
            The flavor of bad pixel (e.g. 'hot')

        Returns
        -------
        num_bad : numpy.ndarray
            1D array of the number of bad pixels

        dates : datetime.datetime
            1D array of dates/times corresponding to num_bad
        """
        # Find all the rows corresponding to the requested type of bad pixel
        rows = [row for row in self.badpixel_table if row.type == bad_type]

        # Extract the dates and number of bad pixels from each entry
        dates = [row.obs_mid_time for row in rows]
        num = [len(row.coordinates[0]) for row in rows]

        # If there are no valid entres in the database, return None
        if len(dates) == 0:
            return None, None

        # Sort by date to make sure everything is in chronological order
        chrono = np.argsort(dates)
        dates = dates[chrono]
        num = num[chrono]

        # Sum the number of bad pixels found from the earliest entry up to
        # each new entry
        num_bad = [np.sum(num[0:i]) for i in range(1, len(num)+1)]

        return num_bad, dates

    def _badpix_image(self):
        """Update bokeh objects with sample image data.
        """
        # Open the mean dark current file and get the data
        with fits.open(self.image_file) as hdulist:
            data = hdulist[1].data

        # Grab only one frame
        ndims = len(data.shape)
        if ndims == 4:
            data = data[0, -1, :, :]
        elif ndims == 3:
            data = data[-1, :, :]
        elif ndims == 2:
            pass
        else:
            raise ValueError('Unrecognized number of dimensions in data file: {}'.format(ndims))

        # Update the plot with the data and boundaries
        y_size, x_size = data.shape
        self.refs["bkgd_image"].data['image'] = [data]
        self.refs["stamp_xr"].end = x_size
        self.refs["stamp_yr"].end = y_size
        self.refs["bkgd_source"].data['dw'] = [x_size]
        self.refs["bkgd_source"].data['dh'] = [y_size]

        # Set the image color scale
        self.refs["log_mapper"].high = 0
        self.refs["log_mapper"].low = -.2

        # Add a title
        self.refs['badpix_map_figure'].title.text = '{}: New Bad Pixels'.format(self._aperture)
        self.refs['badpix_map_figure'].title.align = "center"
        self.refs['badpix_map_figure'].title.text_font_size = "20px"


    def most_recent_coords(self, bad_type):
        """Return the coordinates of the bad pixels in the most recent
        database entry for the given bad pixel type

        Parameters
        ----------
        bad_type : str
            The flavor of bad pixel (e.g. 'hot')

        Returns
        -------
        coords : tup
            Tuple containing a list of x coordinates and a list of y
            coordinates
        """
        # Find all the rows corresponding to the requested type of bad pixel
        rows = [row for row in self.badpixel_table if row.type == bad_type]

        # Extract the dates, number of bad pixels, and files used from each entry
        dates = [row.obs_mid_time for row in rows]
        coords = [row.coordinates for row in rows]
        files = [row.source_files[0] for row in rows]

        # If there are no valid entres in the database, return None
        if len(dates) == 0:
            return None, None

        # Sort by date to make sure everything is in chronological order
        chrono = np.argsort(dates)
        dates = dates[chrono]
        coords = coords[chrono]
        files = files[chrono]

        # Keep track of the latest timestamp
        self.last_timestamp = dates[-1].isoformat()

        # Grab the name of one of the files used when these bad pixels
        # were identified. We'll use this as an image on top of which
        # the bad pixels will be noted. Note that these should be
        # slope files
        self.image_file = filesystem_path(files[-1])

        # Return the list of coordinates for the most recent entry
        return coords[-1]


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

        # comment out for now since the database is empty
        #self.load_data()
        import datetime

        # Populate a dictionary with the number of bad pixels vs time for
        # each type of bad pixel. We can't get the full list of bad pixel
        # types from the database itself, because if there is a type of bad
        # pixel with no found instances, then it won't appear in the database
        # Also populate a dictionary containing the locations of all of the
        # bad pixels found in the most recent search
        self.bad_history = {}
        self.bad_latest = {}
        for badtype in BAD_PIXEL_TYPES:

            # Comment out while waiting for populated database tables
            #num, times = self.bad_pixel_history(badtype)

            # Placeholders while we wait for a populated database
            days = np.arange(1, 11)
            times = np.array([datetime.datetime(2020, 8, day, 12, 0, 0) for day in days])
            num = np.arange(10)

            self.bad_history[badtype] = (times, num)
            #self.bad_latest[badtype] = self.most_recent_coords(badtype)

            self.bad_latest[badtype] = ([0, 1, 2], [4, 4, 4])


            print(badtype, self.bad_latest[badtype], times, num)




        #We also want to retrieve the information for just the most recent entry for each
        #bad pixel type. We will print the coordinates of the most-recently found bad pixels
        #in a table, and show an image (or maybe just a blank 2048x2048 grid) with dots at
        #the locations of the new bad pixels.

        #for each type of bad pixel, there are three items to show:
        #1) bad pixel count vs time
        #2) plot of latest locations (overlain on an image?)
        #3) table of latest bad pix - API view, so users can download


    def post_init(self):
        self._update_badpix_v_time()
        self._update_badpix_loc_plot()
        self._badpix_image()

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

        # Define y range of bad pixel v. time plot
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

    def _update_badpix_loc_plot(self):
        """Update the plot properties for the plot showing the locations
        of new bad pixels"""
        self.refs['bad_pixel_map_xrange'].start = 0
        self.refs['bad_pixel_map_xrange'].end = 2047
        self.refs['bad_pixel_map_yrange'].start = 0
        self.refs['bad_pixel_map_yrange'].end = 2047

        self.refs['bad_pixel_map'].title.text = '{}: New Bad Pixel Locations'.format(self._aperture)
        self.refs['bad_pixel_map'].title.align = "center"
        self.refs['bad_pixel_map'].title.text_font_size = "20px"

    def _update_badpix_v_time(self):
        """Update the plot properties for the plots of the number of bad
        pixels versus time
        """
        for bad_type in BAD_PIXEL_TYPES:
            bad_type_lc = bad_type.lower()

            # Define y ranges of bad pixel v. time plot
            buffer_size = 0.05 * (max(self.bad_history[bad_type][1]) - min(self.bad_history[bad_type][1]))
            self.refs['{}_history_yrange'.format(bad_type_lc)].start = min(self.bad_history[bad_type][1]) - buffer_size
            self.refs['{}_history_yrange'.format(bad_type_lc)].end = max(self.bad_history[bad_type][1]) + buffer_size

            # Define x range of bad_pixel v. time plot
            horizontal_half_buffer = (max(self.bad_history[bad_type][0]) - min(self.bad_history[bad_type][0])) * 0.05
            if horizontal_half_buffer == 0:
                horizontal_half_buffer = 1.  # day
            self.refs['{}_history_xrange'.format(bad_type_lc)].start = min(self.bad_history[bad_type][0]) - horizontal_half_buffer
            self.refs['{}_history_xrange'.format(bad_type_lc)].end = max(self.bad_history[bad_type][0]) + horizontal_half_buffer

            # Add a title
            self.refs['{}_history_figure'].title.text = '{}: {} pixels'.format(self._aperture, bad_type)
            self.refs['{}_history_figure'].title.align = "center"
            self.refs['{}_history_figure'].title.text_font_size = "20px"

BadPixelMonitor()
