
#! /usr/bin/env python

"""This module contains code for the dark current monitor, which
performs some basic analysis to check whether the dark current behavior
for the most recent set of input files is consistent with that from
past files.
If enough new files for a given instrument/aperture combination
(currently the files must be identified as dark current files in the
``exp_type`` header keyword) are present in the filesystem at the time
the ``dark_monitor`` is called, the files are first run through the the
appropriate pipeline steps to produce slope images.
A mean slope image as well as a standard deviation slope image is
created by sigma-clipping on a pixel by pixel basis. The mean and
standard deviation images are saved to a fits file, the name of which
is entered into the ``<Instrument>DarkCurrent`` database table.
The mean slope image is then normalized by an existing baseline slope
image. New hot pixels are identified as those with normalized signal
rates above a ``hot_threshold`` value. Similarly, pixels with
normalized signal rates below a ``dead_threshold`` are flagged as new
dead pixels.
The standard deviation slope image is normalized by a baseline
(historical) standard deviation image. Pixels with normalized values
above a noise threshold are flagged as newly noisy pixels.
New hot, dead, and noisy pixels are saved to the ``DarkPixelStats``
database table.
Next, the dark current in the mean slope image is examined. A histogram
of the slope values is created for the pixels in each amplifier, as
well as for all pixels on the detector. In all cases, a Gaussian is fit
to the histogram. Currently for NIRCam and NIRISS, a double Gaussian is
also fit to the histogram from the entire detector.
The histogram itself as well as the best-fit Gaussian and double
Gaussian parameters are saved to the DarkDarkCurrent database table.
Author
------
    - Mees Fix
Use
---
    This module can be used from the command line as such:
    ::
        python tso_monitor.py
"""

from copy import copy, deepcopy
import datetime
import logging
import os

from astropy.io import ascii, fits
from astropy.modeling import models
from astropy.time import Time
import numpy as np
from pysiaf import Siaf
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamTsoMonitor, NIRSpecTsoMonitor, NIRISSTsoMonitor, MIRITsoMonitor
from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils import calculations, instrument_properties, monitor_utils

from jwql.utils.constants import JWST_DATAPRODUCTS, JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE

from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path


class tsoMonitor():
    """Class for executing the time series observaiton monitor.
    This class will search for new (since the previous instance of the
    class) *photom.fits, *whtlt.ecsv, and *jit.fits files. Monitor will create plots depicting normalized 
    flux vs time, surface plot depicting flux (using colors) as functions of integration number 
    and wavelength, two plots depicting x and y positions vs time, plot of drift/jitter 
    estimates vs Median absolute deviation (MAD) of 1D flux, and 2D image of target. Results 
    are all saved to database tables.

    Parameters
    ----------
    testing : bool
        For pytest. If ``True``, an instance of ``Dark`` is created, but
        no other code is executed.
    Attributes
    ----------

    Raises
    ------
    ValueError
        If encountering an unrecognized bad pixel type
    ValueError
        If the most recent query search returns more than one entry
    """

    def __init__(self):
        """Initialize an instance of the ``tsoMonitor`` class."""


    def identify_tables(self):
        """Determine which database tables to use for a run of the dark
        monitor
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}TsoMonitor'.format(mixed_case_name))


    def most_recent_search(self):
        """Query the query history database and return the information
        on the most recent query for the given ``aperture_name`` where
        the dark monitor was executed.
        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the dark monitor was run.
        """
        query = session.query(self.query_table).filter(self.query_table.run_monitor == True,
                                                       self.query_table.instrument == self.instrument)

        dates = np.zeros(0)
        for instance in query:
            dates = np.append(dates, instance.end_time_mjd)

        query_count = len(dates)
        if query_count == 0:
            query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history for {} with {}. Beginning search date will be set to {}.'
                         .format(self.aperture, self.readpatt, query_result)))
        else:
            query_result = np.max(dates)

        return query_result


    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further
        details.
        """

        logging.info('Begin logging for tso_monitor')

        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'tso_monitor')

        self.query_end = Time.now().mjd

        # Loop over all instruments
        for instrument in JWST_INSTRUMENT_NAMES:
            self.instrument = instrument

            # Identify which database tables to use
            self.identify_tables()

            self.query_start = self.most_recent_search()

            new_files = self.query_tso_observations(instrument, self.query_start, self.query_end)

            # Update the query history
            new_entry = {'instrument': instrument,
                        'start_time_mjd': self.query_start,
                        'end_time_mjd': self.query_end,
                        'files_found': len(new_entries),
                        'run_monitor': monitor_run,
                        'entry_date': datetime.datetime.now()}
            self.query_table.__table__.insert().execute(new_entry)
            logging.info('\tUpdated the query history table')

        logging.info('Dark Monitor completed successfully.')


    def query_tso_observations(self, instrument, query_start, query_end):
        """Obtain all tso observations based on instrument and time.
        """

        parameters = {"date_obs_mjd": {"min": query_start, "max": query_end},
                      "tsovisit": "t"}

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                    add_filters=parameters, return_data=True, caom=False)
        self.data = query['data']