"""This module contains code for the bias monitor Bokeh plots.

Authors
------

    - Maria Pena-Guerrero

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.BiasMonitor('NIRCam', 'NRCA3_FULL')
        script, div = monitor_template.embed("bias_time_figure")
"""

import os

from astropy.io import fits
from astropy.time import Time
from bokeh.models.tickers import LogTicker
import numpy as np
import datetime

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRSpecBiasQueryHistory, NIRSpecBiasStats
from jwql.database.database_interface import NIRCamBiasQueryHistory, NIRCamBiasStats
from jwql.database.database_interface import NIRISSBiasQueryHistory, NIRISSBiasStats
# not implemented yet for MIRI and FGS
#from jwql.database.database_interface import MIRIBiasQueryHistory, MIRIBiasStats
#from jwql.database.database_interface import FGSBiasQueryHistory, FGSBiasStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config
from jwql.bokeh_templating import BokehTemplate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class BiasMonitor(BokehTemplate):

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

    def _bias_mean_image(self):
        """Update bokeh objects with mean bias image data."""

        # Open the mean bias file and get the data
        mean_bias_image_file = self.pixel_table[-1].mean_bias_image_file
        mean_slope_dir = os.path.join(get_config()['outputs'], 'bias_monitor', 'mean_slope_images')
        mean_bias_image_path = os.path.join(mean_slope_dir, mean_bias_image_file)
        with fits.open(mean_bias_image_path) as hdulist:
            data = hdulist[1].data

        # Update the plot with the data and boundaries
        y_size, x_size = np.shape(data)
        self.refs["mean_bias_source"].data['image'] = [data]
        self.refs["stamp_xr"].end = x_size
        self.refs["stamp_yr"].end = y_size
        self.refs["mean_bias_source"].data['dw'] = [x_size]
        self.refs["mean_bias_source"].data['dh'] = [x_size]

        # Set the image color scale
        self.refs["log_mapper"].high = 0
        self.refs["log_mapper"].low = -.2

        # This should add ticks to the colorbar, but it doesn't
        self.refs["mean_bias_cbar"].ticker = LogTicker()

        # Add a title
        self.refs['mean_bias_image_figure'].title.text = self._aperture
        self.refs['mean_bias_image_figure'].title.align = "center"
        self.refs['mean_bias_image_figure'].title.text_font_size = "20px"

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
        self.interface_file = os.path.join(SCRIPT_DIR, "yaml", "bias_monitor_interface.yaml")

        # Load data tables
        self.load_data()

        # Data for mean bias versus time plot
        datetime_stamps = [row.expstart for row in self.bias_table]
        times = np.array([])
        for dt_s in datetime_stamps:
            t = datetime.datetime.strptime(dt_s, '%Y-%m-%dT%H:%M:%S.%f')  # Convert to MJD
            times = np.append(times, t)
        self.timestamps = times
        self.bias = [row.mean for row in self.bias_table]

        # Data for bias plot (values vs time)
        # Just show the last histogram, which is the one most recently
        # added to the database
        last_hist_index = -1
        self.last_timestamp = times[last_hist_index].isoformat()
        self.full_bias_bin_center = np.array([row.hist_bias_values for
                                              row in self.bias_table])[last_hist_index]
        self.full_bias_amplitude = [row.hist_amplitudes for
                                    row in self.bias_table][last_hist_index]
        self.full_bias_bottom = np.zeros(len(self.full_bias_amplitude))
        deltas = self.full_bias_bin_center[1:] - self.full_bias_bin_center[0: -1]
        self.full_bias_bin_width = np.append(deltas[0], deltas)

    def post_init(self):

        self._update_bias_v_time()
        self._update_hist()
        self._bias_mean_image()

    def identify_tables(self):
        """Determine which bias database tables as associated with
        a given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.query_table = eval('{}BiasQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}BiasStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in InstrumentBias with a matching aperture
        self.bias_table = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self._aperture) \
            .all()

    def _update_bias_v_time(self):

        # Define y range of bias v. time plot
        buffer_size = 0.05 * (max(self.bias) - min(self.bias))
        self.refs['bias_yrange'].start = min(self.bias) - buffer_size
        self.refs['bias_yrange'].end = max(self.bias) + buffer_size

        # Define x range of bias v. time plot
        horizontal_half_buffer = (max(self.timestamps) - min(self.timestamps)) * 0.05
        if horizontal_half_buffer == 0:
            horizontal_half_buffer = 1.  # day
        self.refs['bias_xrange'].start = min(self.timestamps) - horizontal_half_buffer
        self.refs['bias_xrange'].end = max(self.timestamps) + horizontal_half_buffer

        # Add a title
        self.refs['bias_time_figure'].title.text = self._aperture
        self.refs['bias_time_figure'].title.align = "center"
        self.refs['bias_time_figure'].title.text_font_size = "20px"

    def _update_hist(self):

        # Define y range of bias histogram
        buffer_size = 0.05 * (max(self.full_bias_amplitude) - min(self.full_bias_bottom))
        self.refs['bias_histogram_yrange'].start = min(self.full_bias_bottom)
        self.refs['bias_histogram_yrange'].end = max(self.full_bias_amplitude) + buffer_size

        # Define x range of bias histogram
        self.refs['bias_histogram_xrange'].start = min(self.full_bias_bin_center)
        self.refs['bias_histogram_xrange'].end = max(self.full_bias_bin_center)

        # Add a title
        self.refs['bias_full_histogram_figure'].title.text = self._aperture
        self.refs['bias_full_histogram_figure'].title.align = "center"
        self.refs['bias_full_histogram_figure'].title.text_font_size = "20px"
