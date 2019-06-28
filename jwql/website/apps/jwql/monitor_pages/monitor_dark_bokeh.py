import os
from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamDarkQueryHistory, NIRCamDarkPixelStats, NIRCamDarkDarkCurrent
from jwql.database.database_interface import NIRISSDarkQueryHistory, NIRISSDarkPixelStats, NIRISSDarkDarkCurrent
from jwql.database.database_interface import MIRIDarkQueryHistory, MIRIDarkPixelStats, MIRIDarkDarkCurrent
from jwql.database.database_interface import NIRSpecDarkQueryHistory, NIRSpecDarkPixelStats, NIRSpecDarkDarkCurrent
from jwql.database.database_interface import FGSDarkQueryHistory, FGSDarkPixelStats, FGSDarkDarkCurrent
script_dir = os.path.dirname(os.path.abspath(__file__))

import numpy as np

from jwql.utils.utils import get_config
from jwql.bokeh_templating import BokehTemplate


class DarkMonitor(BokehTemplate):

    def pre_init(self, instrument, aperture):

        self._embed = True
        self.instrument = instrument
        self.aperture = aperture

        # App design
        self.format_string = None
        self.interface_file = os.path.join(script_dir, "yaml", "monitor_dark_interface.yml")

        self.settings = get_config()
        self.output_dir = self.settings['outputs']

        # Load data tables
        self.load_data()

        # Data for mean dark versus time plot
        self.timestamps = self.dark_table.gauss_peak
        self.dark_current = self.dark_table.obs_mid_time

        # Data for dark current histogram plot (full detector)
        self.full_dark_bin_center = self.dark_table.hist_dark_values
        self.full_dark_amplitude = self.dark_table.hist_amplitudes
        self.full_dark_bottom = np.zeros(len(self.full_dark_amplitude))
        self.full_dark_bin_width = self.full_dark_bin_center[1:] - self.full_dark_bin_center[0: -1]

    def post_init(self):

        self.refs['dark_current_yrange'].start = min(self.dark_current)
        self.refs['dark_current_yrange'].end = max(self.dark_current)

    def identify_tables(self):
        """Determine which dark current database tables as associated with
        a given instrument
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}DarkQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
        self.stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))

    def load_data(self, aperture=None):
        """Given a set of coordinates of bad pixels, determine which of
        these pixels have been previously identified and remove them
        from the list

        Parameters
        ----------
        badpix : tuple
            Tuple of lists containing x and y pixel coordinates. (Output
            of ``numpy.where`` call)

        pixel_type : str
            Type of bad pixel being examined. Options are ``hot``,
            ``dead``, and ``noisy``

        Returns
        -------
        new_pixels_x : list
            List of x coordinates of new bad pixels

        new_pixels_y : list
            List of y coordinates of new bad pixels
        """

        call this function "load_mean_dark" or something more specific than "load_data"

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        self.dark_table = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self.aperture) \
            .all()

        self.pix_table = session.query(self.pixel_table) \
            .filter(self.pixel_table.detector == self.detector) \
            .all()

DarkMonitor()