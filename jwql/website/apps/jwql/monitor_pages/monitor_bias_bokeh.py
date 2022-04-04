
"""This module contains code for the bias monitor Bokeh plots.

Author
------

    - Ben Sunnquist
    - Maria A. Pena-Guerrero

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.BiasMonitor()
        monitor_template.input_parameters = ('NIRCam', 'NRCA1_FULL')
"""

from datetime import datetime, timedelta
import os

from astropy.stats import sigma_clip
import numpy as np

from jwql.bokeh_templating import BokehTemplate
from jwql.database.database_interface import session, NIRCamBiasStats, NIRISSBiasStats, NIRSpecBiasStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class BiasMonitor(BokehTemplate):

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
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', 'monitor_bias_interface.yaml')

    def post_init(self):

        # Load the bias data
        self.load_data()

        # Update the mean bias over time figures
        self.update_mean_bias_figures()

        # Update the calibrated 0th group image
        self.update_calibrated_image()

        # Update the histogram of the calibrated 0th group image
        if self._instrument == 'NIRISS':
            self.update_calibrated_histogram()

        # Update the calibrated collapsed values figures
        if self._instrument != 'NIRISS':
            self.update_collapsed_vals_figures()

    def update_calibrated_histogram(self):
        """Updates the calibrated 0th group histogram"""

        if len(self.query_results) != 0:
            # Get the most recent data; the entries were sorted by time when
            # loading the database, so the last entry will always be the most recent.
            counts = np.array(self.query_results[-1].counts)
            bin_centers = np.array(self.query_results[-1].bin_centers)

            # Update the calibrated image histogram
            self.refs['cal_hist_source'].data = {'counts': counts,
                                                 'bin_centers': bin_centers}
            self.refs['cal_hist_xr'].start = bin_centers.min()
            self.refs['cal_hist_xr'].end = bin_centers.max()
            self.refs['cal_hist_yr'].start = counts.min()
            self.refs['cal_hist_yr'].end = counts.max() + counts.max() * 0.05

    def update_calibrated_image(self):
        """Updates the calibrated 0th group image"""

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
        self.refs['cal_image'].title.text_font_size = '22px'
        self.refs['cal_image'].title.align = 'center'

    def update_collapsed_vals_figures(self):
        """Updates the calibrated median-collapsed row and column figures"""

        if len(self.query_results) != 0:
            for direction in ['rows', 'columns']:
                # Get most recent data; the entries were sorted by time when
                # loading the database, so the last entry will always be the most recent.
                vals = np.array(self.query_results[-1].__dict__['collapsed_{}'.format(direction)])
                pixels = np.arange(len(vals))
                self.refs['collapsed_{}_source'.format(direction)].data = {'pixel': pixels,
                                                                           'signal': vals}

                # Update the pixel and signal limits
                self.refs['collapsed_{}_pixel_range'.format(direction)].start = pixels.min() - 10
                self.refs['collapsed_{}_pixel_range'.format(direction)].end = pixels.max() + 10
                self.refs['collapsed_{}_signal_range'.format(direction)].start = vals[4:2044].min() - 10  # excluding refpix
                self.refs['collapsed_{}_signal_range'.format(direction)].end = vals[4:2044].max() + 10

    def update_mean_bias_figures(self):
        """Updates the mean bias over time bokeh plots"""

        # Get the dark exposures and their starts times
        filenames = [os.path.basename(result.uncal_filename).replace('_uncal.fits', '') for result in self.query_results]
        expstarts_iso = np.array([result.expstart for result in self.query_results])
        expstarts = np.array([datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f') for date in expstarts_iso])

        # Update the mean bias figures for all amps and odd/even columns
        for amp in ['1', '2', '3', '4']:
            for kind in ['odd', 'even']:
                bias_vals = np.array([getattr(result, 'amp{}_{}_med'.format(amp, kind)) for result in self.query_results])
                self.refs['mean_bias_source_amp{}_{}'.format(amp, kind)].data = {'time': expstarts,
                                                                                 'time_iso': expstarts_iso,
                                                                                 'mean_bias': bias_vals,
                                                                                 'filename': filenames}
                self.refs['mean_bias_figure_amp{}_{}'.format(amp, kind)].title.text = 'Amp {} {}'.format(amp, kind.capitalize())
                self.refs['mean_bias_figure_amp{}_{}'.format(amp, kind)].hover.tooltips = [('file', '@filename'),
                                                                                           ('time', '@time_iso'),
                                                                                           ('bias level', '@mean_bias')]

                # Update plot limits if data exists
                if len(bias_vals) != 0:
                    self.refs['mean_bias_xr_amp{}_{}'.format(amp, kind)].start = expstarts.min() - timedelta(days=3)
                    self.refs['mean_bias_xr_amp{}_{}'.format(amp, kind)].end = expstarts.max() + timedelta(days=3)
                    self.refs['mean_bias_yr_amp{}_{}'.format(amp, kind)].start = min(x for x in bias_vals if x is not None) - 20
                    self.refs['mean_bias_yr_amp{}_{}'.format(amp, kind)].end = max(x for x in bias_vals if x is not None) + 20
