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
        monitor_template.input_parameters = ('NIRCam', 'NRCA1_FULL')
"""

from datetime import datetime, timedelta
import os

import numpy as np

from jwql.bokeh_templating import BokehTemplate
from jwql.database.database_interface import session
from jwql.database.database_interface import FGSReadnoiseStats, MIRIReadnoiseStats, NIRCamReadnoiseStats, NIRISSReadnoiseStats, NIRSpecReadnoiseStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class ReadnoiseMonitor(BokehTemplate):

    # Combine the input parameters into a single property because we
    # do not want to invoke the setter unless all are updated
    @property
    def input_parameters(self):
        return (self._instrument, self._aperture)

    @input_parameters.setter
    def input_parameters(self, info):
        self._instrument, self._aperture = info
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

        session.close()

    def pre_init(self):

        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        try:
            dummy_instrument = self._instrument
            dummy_aperture = self._aperture
        except AttributeError:
            self._instrument = 'NIRCam'
            self._aperture = ''

        self._embed = True
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', 'monitor_readnoise_interface.yaml')

    def post_init(self):

        # Load the readnoise data
        self.load_data()

        # Update the mean readnoise figures
        self.update_mean_readnoise_figures()

        # Update the readnoise difference image and histogram
        self.update_readnoise_diff_plots()

    def update_mean_readnoise_figures(self):
        """Updates the mean readnoise bokeh plots"""

        # Get the dark exposures info
        filenames = [os.path.basename(result.uncal_filename).replace('_uncal.fits', '') for result in self.query_results]
        expstarts_iso = np.array([result.expstart for result in self.query_results])
        expstarts = np.array([datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f') for date in expstarts_iso])
        nints = [result.nints for result in self.query_results]
        ngroups = [result.ngroups for result in self.query_results]

        # Update the mean readnoise figures for all amps
        for amp in ['1', '2', '3', '4']:
            readnoise_vals = np.array([getattr(result, 'amp{}_mean'.format(amp)) for result in self.query_results])
            self.refs['mean_readnoise_source_amp{}'.format(amp)].data = {'time': expstarts,
                                                                         'time_iso': expstarts_iso,
                                                                         'mean_rn': readnoise_vals,
                                                                         'filename': filenames,
                                                                         'nints': nints,
                                                                         'ngroups': ngroups}
            self.refs['mean_readnoise_figure_amp{}'.format(amp)].title.text = 'Amp {}'.format(amp)
            self.refs['mean_readnoise_figure_amp{}'.format(amp)].hover.tooltips = [('file', '@filename'),
                                                                                   ('time', '@time_iso'),
                                                                                   ('nints', '@nints'),
                                                                                   ('ngroups', '@ngroups'),
                                                                                   ('readnoise', '@mean_rn')]

            # Update plot limits if data exists
            if len(readnoise_vals) != 0:
                self.refs['mean_readnoise_xr_amp{}'.format(amp)].start = expstarts.min() - timedelta(days=3)
                self.refs['mean_readnoise_xr_amp{}'.format(amp)].end = expstarts.max() + timedelta(days=3)
                min_val, max_val = min(x for x in readnoise_vals if x is not None), max(x for x in readnoise_vals if x is not None)
                if min_val == max_val:
                    self.refs['mean_readnoise_yr_amp{}'.format(amp)].start = min_val - 1
                    self.refs['mean_readnoise_yr_amp{}'.format(amp)].end = max_val + 1
                else:
                    offset = (max_val - min_val) * .1
                    self.refs['mean_readnoise_yr_amp{}'.format(amp)].start = min_val - offset
                    self.refs['mean_readnoise_yr_amp{}'.format(amp)].end = max_val + offset

    def update_readnoise_diff_plots(self):
        """Updates the readnoise difference image and histogram"""

        # Update the readnoise difference image and histogram, if data exists
        if len(self.query_results) != 0:
            # Get the most recent data; the entries were sorted by time when
            # loading the database, so the last entry will always be the most recent.
            diff_image_png = self.query_results[-1].readnoise_diff_image
            diff_image_png = os.path.join('/static', '/'.join(diff_image_png.split('/')[-6:]))
            diff_image_n = np.array(self.query_results[-1].diff_image_n)
            diff_image_bin_centers = np.array(self.query_results[-1].diff_image_bin_centers)

            # Update the readnoise difference image and histogram
            self.refs['readnoise_diff_image'].image_url(url=[diff_image_png], x=0, y=0, w=2048, h=2048, anchor="bottom_left")
            self.refs['diff_hist_source'].data = {'n': diff_image_n,
                                                  'bin_centers': diff_image_bin_centers}
            self.refs['diff_hist_xr'].start = diff_image_bin_centers.min()
            self.refs['diff_hist_xr'].end = diff_image_bin_centers.max()
            self.refs['diff_hist_yr'].start = diff_image_n.min()
            self.refs['diff_hist_yr'].end = diff_image_n.max() + diff_image_n.max() * 0.05

        # Update the readnoise difference image style
        self.refs['readnoise_diff_image'].xaxis.visible = False
        self.refs['readnoise_diff_image'].yaxis.visible = False
        self.refs['readnoise_diff_image'].xgrid.grid_line_color = None
        self.refs['readnoise_diff_image'].ygrid.grid_line_color = None
        self.refs['readnoise_diff_image'].title.text_font_size = '22px'
        self.refs['readnoise_diff_image'].title.align = 'center'
