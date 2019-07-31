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

import logging
import os

from astropy.io import fits
from astropy.time import Time
import numpy as np

from jwql.instrument_monitors.common_monitors.dark_monitor import mast_query_darks   
from jwql.utils.utils import filesystem_path, initialize_instrument_monitor, update_monitor_table

class Bias():
    """Class for executing the bias monitor.
    """

    def __init__(self):
        """Initialize an instance of the ``Bias`` class.
        """

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details.
        """

        logging.info('Begin logging for bias_monitor')

        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'bias_monitor')

        # query_start is a PLACEHOLDER. Use the current time as the end time for MAST query
        self.query_start, self.query_end = 57357.0, Time.now().mjd  # a.k.a. Dec 1, 2015 == CV3

        # Loop over all instruments
        for instrument in ['nircam']:
            self.instrument = instrument

            # PLACEHOLDER Make a list of all possible apertures
            possible_apertures = ['NRCA1_FULL','NRCA2_FULL','NRCA3_FULL','NRCA4_FULL','NRCA5_FULL',
                                  'NRCB1_FULL','NRCB2_FULL','NRCB3_FULL','NRCB4_FULL','NRCB5_FULL']

            for aperture in possible_apertures:

                logging.info('')
                logging.info('Working on aperture {} in {}'.format(aperture, instrument))

                # Query MAST for new data for this instrument/aperture
                logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))
                new_entries = mast_query_darks(instrument, aperture, self.query_start, self.query_end)
                logging.info('\tAperture: {}, new entries: {}'.format(self.aperture, len(new_entries)))

                # Get full paths to the files, some dont exist in JWQL filesystem
                new_filenames = []
                for file_entry in new_entries:
                    try:
                        new_filenames.append(filesystem_path(file_entry['filename']))
                    except FileNotFoundError:
                        logging.info('{} does not exist in JWQL filesystem'.format(file_entry['filename']))


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Bias()
    monitor.run()

    #update_monitor_table(module, start_time, log_file)
