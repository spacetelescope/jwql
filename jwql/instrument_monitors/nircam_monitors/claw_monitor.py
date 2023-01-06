#! /usr/bin/env python

"""This module contains code for the claw monitor.

Author
------
    - Ben Sunnquist

Use
---
    This module can be used from the command line as such:

    ::

        python claw_monitor.py
"""

import logging
import os

from astropy.io import fits
from astropy.time import Time
from astropy.visualization import ZScaleInterval
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from jwql.utils import monitor_utils
from jwql.utils.logging_functions import log_info, log_fail


class ClawMonitor():
    """Class for executing the claw monitor.
    """

    def __init__(self):
        """Initialize an instance of the ``ClawMonitor`` class.
        """

    def process(self, file_list):
        """The main method for processing.  See module docstrings for further details.
        """

    #@log_fail  # ben uncomment
    #@log_info  # ben uncomment
    def run(self):
        """The main method.  See module docstrings for further details."""

        logging.info('Begin logging for claw_monitor')


        logging.info('Claw Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    #start_time, log_file = monitor_utils.initialize_instrument_monitor(module)   # ben uncomment

    monitor = ClawMonitor()
    monitor.run()

    #monitor_utils.update_monitor_table(module, start_time, log_file)   # ben uncomment
