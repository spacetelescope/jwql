"""This module contains code for the readnoise monitor Bokeh plots.

Author
------

    - Ben Sunnquist

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.ReadnoiseMonitor()
        monitor_template.input_parameters = ('NIRCam', 'NRCA1_FULL', '1')
"""

from datetime import datetime, timedelta
import os

import numpy as np

from jwql.bokeh_templating import BokehTemplate
from jwql.database.database_interface import session, NIRCamReadnoiseStats, NIRISSReadnoiseStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class ReadnoiseMonitor(BokehTemplate):

    # Combine the input parameters into a single property because we
    # do not want to invoke the setter unless all are updated
    @property
    def input_parameters(self):
        return (self._instrument, self._aperture, self._amp)

    @input_parameters.setter
    def input_parameters(self, info):
        self._instrument, self._aperture, self._amp = info
        self.pre_init()
        self.post_init()

    def identify_tables(self):
        """Determine which database tables to use for the given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.stats_table = eval('{}ReadnoiseStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get all of the relevant readnoise data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in readnoise stats with a matching aperture,
        # and sort the data by exposure start time.
        self.query_results = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self._aperture) \
            .order_by(self.stats_table.expstart) \
            .all()

    def pre_init(self):

        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        try:
            dummy_instrument = self._instrument
            dummy_aperture = self._aperture
            dummy_amp = self._amp
        except AttributeError:
            self._instrument = 'NIRCam'
            self._aperture = 'NRCA1_FULL'
            self._amp = '1'

        self._embed = True
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', 'monitor_readnoise_interface.yaml')

    def post_init(self):

        # Load the readnoise data
        self.load_data()

        # Get the relevant plotting data
        self.readnoise_vals = np.array([getattr(result, 'amp{}_mean'.format(self._amp)) for result in self.query_results])
        self.expstarts_iso = np.array([result.expstart for result in self.query_results])
        self.expstarts = np.array([datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f') for date in self.expstarts_iso])
        self.filenames = [os.path.basename(result.uncal_filename).replace('_uncal.fits', '') for result in self.query_results]
        self.nints = [result.nints for result in self.query_results]
        self.ngroups = [result.ngroups for result in self.query_results]

        # Update the mean readnoise figure
        self.update_mean_readnoise_figure()

        # Update the readnoise difference image and histogram
        self.update_readnoise_diff_plots()

    def update_mean_readnoise_figure(self):
        """Updates the mean readnoise bokeh plot"""

        # Update the mean readnoise vs time plot
        self.refs['mean_readnoise_source'].data = {'time': self.expstarts,
                                                   'time_iso': self.expstarts_iso,
                                                   'mean_rn': self.readnoise_vals,
                                                   'filename': self.filenames,
                                                   'nints': self.nints,
                                                   'ngroups': self.ngroups}
        self.refs['mean_readnoise_xr'].start = self.expstarts.min() - timedelta(days=3)
        self.refs['mean_readnoise_xr'].end = self.expstarts.max() + timedelta(days=3)
        self.refs['mean_readnoise_yr'].start = self.readnoise_vals.min() - 1
        self.refs['mean_readnoise_yr'].end = self.readnoise_vals.max() + 1
        self.refs['mean_readnoise_figure'].title.text = 'Amp {}'.format(self._amp)
        self.refs['mean_readnoise_figure'].hover.tooltips = [('file', '@filename'),
                                                             ('time', '@time_iso'),
                                                             ('nints', '@nints'),
                                                             ('ngroups', '@ngroups'),
                                                             ('readnoise', '@mean_rn')
                                                             ]

    def update_readnoise_diff_plots(self):
        """Updates the readnoise difference image and histogram"""

        # Get the most recent data; the entries were sorted by time when
        # loading the database, so the last entry will always be the most recent.
        diff_image_png = self.query_results[-1].readnoise_diff_image
        diff_image_n = np.array(self.query_results[-1].diff_image_n)
        diff_image_bin_centers = np.array(self.query_results[-1].diff_image_bin_centers)

        # Update the readnoise difference image
        self.refs['readnoise_diff_image'].image_url(url=[diff_image_png], x=0, y=0, w=2048, h=2048, anchor="bottom_left")
        self.refs['readnoise_diff_image'].xaxis.visible = False
        self.refs['readnoise_diff_image'].yaxis.visible = False
        self.refs['readnoise_diff_image'].xgrid.grid_line_color = None
        self.refs['readnoise_diff_image'].ygrid.grid_line_color = None
        self.refs['readnoise_diff_image'].title.text_font_size = '30px'

        # Update the readnoise difference histogram
        self.refs['diff_hist_source'].data = {'n': diff_image_n,
                                              'bin_centers': diff_image_bin_centers}
        self.refs['diff_hist_xr'].start = diff_image_bin_centers.min()
        self.refs['diff_hist_xr'].end = diff_image_bin_centers.max()
        self.refs['diff_hist_yr'].start = diff_image_n.min()
        self.refs['diff_hist_yr'].end = diff_image_n.max() + diff_image_n.max() * 0.05


ReadnoiseMonitor()
