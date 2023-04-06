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


class ReadnoiseMonitorData():
    """Class to hold bias data to be plotted
    
    Parameters
    ----------
    
    instrument : str
        Instrument name (e.g. nircam)
    
    Attributes
    ----------
    
    instrument : str
        Instrument name (e.g. nircam)
    aperture : str
        Aperture name (e.g. apername)
    
    """

    def __init__(self, instrument, aperture):
        self.instrument = instrument
        self.aperture = aperture
        self.load_data()


    def identify_tables(self):
        """Determine which database tables to use for the given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.stats_table = eval('{}ReadnoiseStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get all of the relevant readnoise data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in readnoise stats with a matching aperture,
        # and sort the data by exposure start time.
        self.query_results = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self.aperture) \
            .order_by(self.stats_table.expstart) \
            .all()

        session.close()

class ReadNoisePlots():
    """Class to make readnoise plots.
    """
    def __init__(self, instrument, aperture):
        self.instrument = instrument
        self.aperture = aperture

        self.db = ReadnoiseMonitorData(self.instrument, self.aperture)


    def read_noise_amp_plots(self):
        """Make read noise monitor trending plots per amplifier
        """
        print('make plot here')
        # for amp in ['1', '2', '3', '4']:
        #     expstarts_iso = np.array([result.expstart for result in self.db])
        #     readnoise_vals = np.array([getattr(result, 'amp{}_mean'.format(amp)) for result in self.query_results])
            




