
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
from astropy.timeseries import LombScargle
from glob import glob
from jwst import datamodels
import numpy as np
import pandas as pd
from pysiaf import Siaf
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d
from scipy.ndimage import median_filter
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamTsoMonitor, NIRSpecTsoMonitor, NIRISSTsoMonitor, MIRITsoMonitor
from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils import calculations, instrument_properties, monitor_utils

from jwql.utils.constants import JWST_DATAPRODUCTS, JWST_INSTRUMENT_NAMES, DETECTOR_PER_INSTRUMENT

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


    def compute_out_of_transit_flux(self):
        """Calculate the median out of transit flux.
        """
        # Extract very last times (corresponding to last segment):
        uncal_data = datamodels.open(self.uncal_file)
        times = uncal_data.int_times['int_mid_BJD_TDB'][-len(self.whtlt_flux):]

        # Convert to seconds since first integration on this last segment:
        times_seconds = (times - times[0]) * 24 * 3600.

        # self.median_out_of_transit_flux = np.median(ootf)


    def identify_tables(self):
        """Determine which database tables to use for a run of the dark
        monitor
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}TsoMonitor'.format(mixed_case_name))


    def plot_acq_image(self):
        """Plot 2D acq image.
        """
        print('plotting stuff here')


    def plot_spectrum_trace_and_jitter(self):
        """Plot the cross-correlation of the spectrum trace and jitter in the dispersion and x-dispersion directions.
        """
        print('plotting stuff here')


    def plot_whitelight_curve(self):
        """Plot whitelight curve (band integrated light flux) vs wavelength and flux normalized to the median out-of-transit
        flux vs time.
        """
        print('plotting stuff here')


    def plot_spectroscopic_lightcurves(self):
        """A surface plot of all spectral light curves: flux of each spectral light curve vs data point number
        with flux color bar.
        """
        print('plotting stuff here')


    def plot_jitter(self):
        """Plot V1, V2, V3 jitter vs time.
        """
        print('plotting stuff here')


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
            
            for detector in DETECTOR_PER_INSTRUMENT[self.instrument]:
                self.detector = detector
                self.query_start =  session.query(self.query_table).filter(func.max(self.query_table.end_time_mjd),
                                                    self.query_table.instrument == self.instrument,
                                                    self.query_table.detector == self.detector)

                new_entries = self.query_tso_observations(self.instrument, self.detector, self.query_start, self.query_end)

                if len(new_entries) is None:
                    continue

                # Putting these results into pandas dataframe for convenience.
                query_result_df = pd.DataFrame(new_entries)

                # Make tso_monitor output dir
                self.output_dir = os.path.join(get_config()['outputs'], 'tso_monitor')

                if not os.path.isdir(self.output_dir):
                    os.mkdir(self.output_dir)

                for fileSetName in query_result_df.fileSetName.unique():
                    sorted_df = query_result_df[query_result_df['filename'].str.contains(fileSetName)]

                    self.data_dir = os.path.join(self.output_dir,
                            'data/{}/{}'.format(self.instrument.lower(),
                                                fileSetName.lower()))
                    ensure_dir_exists(self.data_dir)

                    # Copy files from filesystem
                    new_filenames = sorted_df['filenames']
                    tso_files, not_copied = copy_files(new_filenames, self.data_dir)
                    
                    new_entry = {'instrument': self.instrument,
                                'aperture': sorted_df['apername'].unique()[0],
                                'filter': sorted_df['filter'].unique()[0],
                                'detector': sorted_df['detector'].unique()[0],
                                'obslabel': sorted_df['obslabel'].unique()[0],
                                'filesetname': fileSetName,
                                'start_time_mjd': self.query_start,
                                'end_time_mjd': self.query_end,
                                'files': tso_files,
                                'entry_date': datetime.datetime.now()}

                    self.query_table.insert().execute(new_entries)
                    logging.info('\tUpdated {} with {}'.format(self.query_table.__name__, new_entry))

                    logging.info('\tBeginning Preprocessing for {}'.format(new_entry))
                    self.process(sorted_df)


        logging.info('TSO Monitor completed successfully.')


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
        query = session.query(self.query_table).filter(self.query_table.instrument == self.instrument,
                                                       self.query_table.detector == self.detector). \
                              filter(self.query_table.run_monitor == True)

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


    def process(self, fileset_dataframe):
        """Process and calculate statistics for database table.
        """
        files = glob.glob('{}/*'.format(self.data_dir))
        # calculate out of transit median flux
        # obtain frame numbers and x, y jitter
        # centroids of targets in acq images brightest to faintest


    def process_acq_image_centroids(self, acq_image):
        """Find the centroid of the stars in acq image.

        acq_file : str
            full path to acq image
        """
        hdu = fits.open(acq_image)
        # im_size = hdu[1].data.shape
        # obtain centroids

        # store acq image location of centroid x, y as well as brightness
        # organize positions in x,y with brightness from highest to lowest.


    def process_spectrum_jitter(self, x1d_file):
        """Cross correlate a spectral trace with
        """


    def process_v2_v3_jitter(self, jit_file):
        """Obtain time and v2/v3 jitter for marginally successful and failed observations.
        """
        # jit_data = open(jit_file)
        # store time, v2, v3
        print('v2, v3 jit')
        return


    def process_whitelight_data(self, whitelight_file):
        """Process data from whitelight files if available.
        """

        # whtlt_data = open(whitelight_file)
        # calculate out of transit flux
        # normalize flux to out of transit flux
        # store time, flux, out of transit flux
        print('whitelight processing')


    def query_tso_observations(self, instrument, detector, query_start, query_end):
        """Obtain all tso observations based on instrument and time.
        """

        parameters = {"date_obs_mjd": {"min": query_start, "max": query_end},
                      "tsovisit": "t", "detector": detector}

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                    add_filters=parameters, return_data=True, caom=False)
        return query['data']


    def webapp_plotting(self, filesetname):
        """Given a single filesetname, create monitoring plots for the webapp.
        """

        self.plot_acq_image(filesetname)

        self.plot_spectrum_trace_and_jitter(filesetname)

        self.plot_whitelight_curve(filesetname)

        self.plot_spectroscopic_lightcurves(filesetname)

        self.plot_jitter(filesetname)
