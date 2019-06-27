#! /usr/bin/env python

"""This module contains code for the bias monitor.

Author
------
    - Ben Sunnquist

Use
---
    This module can be used from the command line as such:

    ::

        python bias_monitor.py
"""

from astropy.io import fits
import numpy as np

from jwql.instrument_monitors.common_monitors.dark_monitor import mast_query_darks   
from jwql.utils.utils import initialize_instrument_monitor, update_monitor_table

class Bias():
    """Class for executing the bias monitor.
    """

    def __init__(self):
        """Initialize an instance of the ``Bias`` class."""

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further
        details.
        """

        logging.info('Begin logging for bias_monitor')

        # Loop over all instruments
        for instrument in ['nircam']:
            self.instrument = instrument
            aperture = 'nrca1_full'
            query_start, query_end = 0, 99999999

            # Query MAST for new data for this instrument
            new_entries = mast_query_darks(instrument, aperture, query_start, query_end)

if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Bias()
    monitor.run()

    #update_monitor_table(module, start_time, log_file)
