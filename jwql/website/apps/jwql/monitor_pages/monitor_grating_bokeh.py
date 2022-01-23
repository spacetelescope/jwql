
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
        monitor_template.input_parameters = ('NIRSpec', 'NRS1_FULL')
"""

from datetime import datetime, timedelta
from astropy.time import Time
import os

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
        return (self._instrument)

    @input_parameters.setter
    def input_parameters(self, info):
        self._instrument = info
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

        # Query database for all data in grating wheel stats,
        # and sort the data by exposure start time.
        # If monitor fails here because relation does not exist, need to reset database
        self.query_results = session.query(self.stats_table) \
            .order_by(self.stats_table.time) \
            .all()

    def pre_init(self):

        # Start with default values for instrument because
        # BokehTemplate's __init__ method does not allow input arguments
        try:
            dummy_instrument = self._instrument
        except AttributeError:
            self._instrument = 'NIRSpec'

        self._embed = True
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', 'monitor_grating_interface.yaml')

    def post_init(self):

        # Load the grating wheel data
        self.load_data()

        # Update the mean grating wheel over time figures
        self.update_grating_figures()

    def update_grating_figures(self):
        """Updates the grating telemetry over time bokeh plots"""

        # Update the figures for all GWA telemetry values
        for telemetry in GRATING_TELEMETRY.keys():
            gwa_vals = np.array([getattr(result, '{}'.format(telemetry.lower())) for result in self.query_results])

            if len(gwa_vals) != 0:  # SHOULD UPDATE WITHOUT IF STATEMENT
                dates_iso = np.array([str(Time(Time(result.time, format='mjd'), format='iso')) for result in self.query_results])
                dates = np.array([datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f') for date in dates_iso])

                fake_filenames = []
                for length in range(len(gwa_vals)):
                    fake_filenames.append("file{}".format(length))
                self.refs['source_{}'.format(telemetry)].data = {'time': dates,
                                                                 'time_iso': dates_iso,
                                                                 'grating': gwa_vals,
                                                                 'filename': fake_filenames}

                self.refs['figure_{}'.format(telemetry)].title.text = '{}'.format(telemetry)
                self.refs['figure_{}'.format(telemetry)].hover.tooltips = [('time', '@time_iso'),
                                                                           ('gwa val', '@grating')]

            # Update plot limits if data exists
            gwa_vals_cut = gwa_vals[np.where(gwa_vals != None)]  # USE ABOVE AS WELL?
            if len(gwa_vals_cut) != 0:
                self.refs['gwa_x_{}'.format(telemetry)].start = datetime.now() - timedelta(days=3)
                self.refs['gwa_x_{}'.format(telemetry)].end = datetime.now()
                if telemetry in ['INRSH_GWA_ADCMGAIN', 'INRSH_GWA_ADCMOFFSET', 'INRSH_GWA_MOTOR_VREF']:
                    self.refs['gwa_y_{}'.format(telemetry)].start = gwa_vals_cut.min() - 0.5
                    self.refs['gwa_y_{}'.format(telemetry)].end = gwa_vals_cut.max() + 0.5
                else:
                    # Use wider y-range to see full green/yellow/red areas for x/y position telemetry
                    self.refs['gwa_y_{}'.format(telemetry)].start = -400
                    self.refs['gwa_y_{}'.format(telemetry)].end = 400