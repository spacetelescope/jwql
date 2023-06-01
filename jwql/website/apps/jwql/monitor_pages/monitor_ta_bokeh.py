"""This module contains code for the TA monitor Bokeh plots.
Author
------
    - Mike Engesser
Use
---
    This module can be used from the command line as such:
    ::
"""

import os

from astropy.io import fits
from astropy.time import Time
import datetime
import numpy as np
import matplotlib.pyplot as plt

from jwql.database.database_interface import session
from jwql.database.database_interface import MIRITAQueryHistory, MIRITAStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config, filesystem_path
from jwql.bokeh_templating import BokehTemplate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class TAMonitor(BokehTemplate):

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

    def pre_init(self):
        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        try:
            dummy_instrument = self._instrument
            dummy_aperture = self._aperture
        except AttributeError:
            self._instrument = 'MIRI'
            self._aperture = 'MIRIM_FULL'

        self._embed = True

        # App design
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, "yaml", "ta_monitor_interface.yaml")

        # Load data tables
        self.load_data()
        self.get_history_data()

        # Get dates and coordinates of the most recent entries
        # self.most_recent_data()
        self.get_histogram_data()

    def post_init(self):
        # self._update_cosmic_ray_v_time()
         self._update_ta_histogram()

    def get_histogram_data(self):
        """Get data required to create TA histogram from the
        database query.
        """

        last_hist_index = -1
        hist = plt.hist(self.offs[last_hist_index])

        self.bin_left = np.array( [bar.get_x() for bar in hist[2]] )
        self.amplitude = [bar.get_height() for bar in hist[2]]
        self.bottom = [bar.get_y() for bar in hist[2]]
        deltas = self.bin_left[1:] - self.bin_left[0: -1]
        self.bin_width = np.append(deltas[0], deltas)

    def get_history_data(self):
        """Extract data on the history of TA from the
        database query result
        """
        self.TA_history = {}

        self.times = [row.obs_end_time for row in self.ta_table]
        self.offs = [row.offset for row in self.ta_table]

        hover_values = np.array([datetime.datetime.strftime(t, "%d-%b-%Y") for t in self.times])
        self.ta_history['Offsets'] = (self.times, self.num, hover_values)

    def identify_tables(self):
        """Determine which database tables as associated with
        a given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.query_table = eval('{}TAQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}TAStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data with a matching aperture
        self.ta_table = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self._aperture) \
            .all()

    def most_recent_data(self):
        """Get the cosmic ray magnitudes associated with the most
        recent run of the monitor.
        """

        ta_times = [row.obs_end_time for row in self.ta_table]

        if len(ta_times) > 0:
            self.most_recent_obs = max(ta_times)
        else:
            self.most_recent_obs = datetime.datetime(1999, 10, 31)


    def _update_ta_histogram():

        offs = [row.offset for row in self.ta_table]

        self.refs['hist_x_range'].start = 0
        self.refs['hist_x_range'].end = max(offs)

        self.refs['hist_y_range'].start = 0
        self.refs['hist_y_range'].end = len(offs)

        self.refs['ta_histogram'].title.text = '{} TA Offsets'.format(self.aperture)
        self.refs['ta_histogram'].title.align = "center"
        self.refs['ta_histogram'].title.text_font_size = "20px"

# Uncomment the line below when testing via the command line:
# bokeh serve --show monitor_ta_bokeh.py
TAMonitor()
