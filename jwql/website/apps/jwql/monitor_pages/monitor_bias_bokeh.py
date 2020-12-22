"""This module contains code for the bias monitor Bokeh plots.

Author
------

    - Ben Sunnquist

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.BiasMonitor()
        monitor_template.input_parameters = ('NIRCam', 'NRCA1_FULL', '1', 'even')
"""

from datetime import datetime, timedelta
import os

import numpy as np

from jwql.bokeh_templating import BokehTemplate
from jwql.database.database_interface import session, NIRCamBiasStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class BiasMonitor(BokehTemplate):

    # Combine the input parameters into a single property because we
    # do not want to invoke the setter unless all are updated
    @property
    def input_parameters(self):
        return (self._instrument, self._aperture, self._amp, self._kind)

    @input_parameters.setter
    def input_parameters(self, info):
        self._instrument, self._aperture, self._amp, self._kind = info
        self.pre_init()
        self.post_init()

    def identify_tables(self):
        """Determine which database tables to use for the given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.stats_table = eval('{}BiasStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get all of the relevant bias data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in bias stats with a matching aperture,
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
            self._aperture = ''
            self._amp = ''
            self._kind = ''

        self._embed = True
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', 'monitor_bias_interface.yaml')

    def post_init(self):

        # Load the bias data
        self.load_data()

        # Get the relevant plotting data
        self.bias_vals = np.array([getattr(result, 'amp{}_{}_med'.format(self._amp, self._kind)) for result in self.query_results])
        self.expstarts_iso = np.array([result.expstart for result in self.query_results])
        self.expstarts = np.array([datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f') for date in self.expstarts_iso])
        self.filenames = [os.path.basename(result.uncal_filename).replace('_uncal.fits', '') for result in self.query_results]

        # Update the mean bias figure
        self.update_mean_bias_figure()

        # Update the calibrated 0th group image
        self.update_calibrated_image()

        # Update the calibrated collapsed values figures
        self.update_collapsed_rows_figure()
        self.update_collapsed_cols_figure()

    def update_mean_bias_figure(self):
        """Updates the mean bias bokeh plot"""

        # Update the mean bias vs time plot
        self.refs['mean_bias_source'].data = {'time': self.expstarts,
                                              'time_iso': self.expstarts_iso,
                                              'mean_bias': self.bias_vals,
                                              'filename': self.filenames}
        self.refs['mean_bias_figure'].title.text = 'Amp {} {}'.format(self._amp, self._kind.capitalize())
        self.refs['mean_bias_figure'].hover.tooltips = [('file', '@filename'),
                                                        ('time', '@time_iso'),
                                                        ('bias level', '@mean_bias')]

        # Update plot limits if data exists
        if len(self.query_results) != 0:
            self.refs['mean_bias_xr'].start = self.expstarts.min() - timedelta(days=3)
            self.refs['mean_bias_xr'].end = self.expstarts.max() + timedelta(days=3)
            self.refs['mean_bias_yr'].start = self.bias_vals.min() - 10
            self.refs['mean_bias_yr'].end = self.bias_vals.max() + 10

    def update_collapsed_cols_figure(self):
        """Updates the calibrated collapsed columns figure"""

        if len(self.query_results) != 0:
            # Get the most recent data; the entries were sorted by time when
            # loading the database, so the last entry will always be the most recent.
            collapsed_cols = np.array(self.query_results[-1].collapsed_columns)
            cols = np.arange(len(collapsed_cols))

            self.refs['collapsed_cols_source'].data = {'column': cols,
                                                       'signal': collapsed_cols}

            self.refs['collapsed_cols_xr'].start = cols.min()
            self.refs['collapsed_cols_xr'].end = cols.max()
            self.refs['collapsed_cols_yr'].start = collapsed_cols.min() - 10
            self.refs['collapsed_cols_yr'].end = collapsed_cols.max() + 10

    def update_collapsed_rows_figure(self):
        """Updates the calibrated collapsed rows figure"""

        if len(self.query_results) != 0:
            # Get the most recent data; the entries were sorted by time when
            # loading the database, so the last entry will always be the most recent.
            collapsed_rows = np.array(self.query_results[-1].collapsed_rows)
            rows = np.arange(len(collapsed_rows))

            self.refs['collapsed_rows_source'].data = {'row': rows,
                                                       'signal': collapsed_rows}

            self.refs['collapsed_rows_xr'].start = rows.min()
            self.refs['collapsed_rows_xr'].end = rows.max()
            self.refs['collapsed_rows_yr'].start = collapsed_rows.min() - 10
            self.refs['collapsed_rows_yr'].end = collapsed_rows.max() + 10

    def update_calibrated_image(self):
        """Updates the calibrated 0th group image"""

        # Update the calibrated 0th group image if data exists
        if len(self.query_results) != 0:
            # Get the most recent data; the entries were sorted by time when
            # loading the database, so the last entry will always be the most recent.
            cal_image_png = self.query_results[-1].cal_image
            cal_image_png = os.path.join('/static', '/'.join(cal_image_png.split('/')[-6:]))

            # Update the image source for the figure
            self.refs['cal_image'].image_url(url=[cal_image_png], x=0, y=0, w=2048, h=2048, anchor="bottom_left")

        # Update the calibrated image style
        self.refs['cal_image'].xaxis.visible = False
        self.refs['cal_image'].yaxis.visible = False
        self.refs['cal_image'].xgrid.grid_line_color = None
        self.refs['cal_image'].ygrid.grid_line_color = None
        self.refs['cal_image'].title.text_font_size = '30px'
