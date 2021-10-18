
"""This module contains code for the grating wheel monitor Bokeh plots.
This code was adapted from monitor_bias_bokeh.py.

Author
------

    - Teagan King

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.GratingMonitor()
"""

from datetime import datetime, timedelta
import os

from astropy.stats import sigma_clip
import numpy as np

from jwql.bokeh_templating import BokehTemplate
from jwql.database.database_interface import session, NIRSpecGratingStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.constants import GRATING_TELEMETRY

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class GratingMonitor(BokehTemplate):

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
        self.stats_table = eval('{}GratingStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get all of the relevant grating wheel data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in grating wheel stats with a matching aperture,
        # and sort the data by exposure start time.
        # FAILING HERE: (psycopg2.errors.UndefinedTable) relation "nirspec_grating_stats" does not exist
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
        except AttributeError:
            self._instrument = 'NIRSpec'
            self._aperture = ''

        self._embed = True
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', 'monitor_grating_interface.yaml')

    def post_init(self):

        # Load the grating wheel data
        self.load_data()

        # Update the mean grating wheel over time figures
        self.update_mean_grating_figures()

    def update_mean_grating_figures(self):
        """Updates the mean bias over time bokeh plots"""

        # POSSIBLY REPLACE DARK EXPOSURES WITH SOMETHING ELSE
        # Get the dark exposures and their starts times
        filenames = [os.path.basename(result.uncal_filename).replace('_uncal.fits', '') for result in self.query_results]
        expstarts_iso = np.array([result.expstart for result in self.query_results])
        expstarts = np.array([datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f') for date in expstarts_iso])

        # Update the figures for all GWA telemetry values
        for telemetry in GRATING_TELEMETRY:
            gwa_vals = np.array([getattr(result, '{}'.format(telemetry)) for result in self.query_results])
            self.refs['source_{}'.format(telemetry)].data = {'time': expstarts,
                                                             'time_iso': expstarts_iso,
                                                             'gwa_vals': gwa_vals,
                                                             'filename': filenames}
            self.refs['figure_{}'.format(telemetry)].title.text = '{}'.format(telemetry)
            self.refs['figure_{}'.format(telemetry)].hover.tooltips = [('file', '@filename'),
                                                                       ('time', '@time_iso'),
                                                                       ('gwa val', '@gwa_vals')]

            # Update plot limits if data exists
            if len(gwa_vals) != 0:
                self.refs['gwa_x_{}'.format(telemetry)].start = expstarts.min() - timedelta(days=3)
                self.refs['gwa_x_{}'.format(telemetry)].end = expstarts.max() + timedelta(days=3)
                self.refs['gwa_y_{}'.format(telemetry)].start = gwa_vals.min() - 20
                self.refs['gwa_y_{}'.format(telemetry)].end = gwa_vals.max() + 20
