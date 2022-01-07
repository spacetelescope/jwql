
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
from jwst import datamodels
import numpy as np
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


    def compute_out_of_transit_flux(self):
        """Calculate the median out of transit flux.
        """
        # Extract very last times (corresponding to last segment):
        uncal_data = datamodels.open(self.uncal_file)
        times = uncal_data.int_times['int_mid_BJD_TDB'][-len(self.whtlt_flux):]

        # Convert to seconds since first integration on this last segment:
        times_seconds = (times - times[0]) * 24 * 3600.


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


    def trace_spectrum(self, image, dqflags, xstart, ystart, profile_radius=20, nsigma = 100, gauss_filter_width=10, xend=None, y_tolerance = 5, verbose = False):
        """
        Function that non-parametrically traces NIRISS/SOSS spectra. First, to get the centroid at xstart and 
        ystart, it convolves the spatial profile with a gaussian filter, finding its peak through usual flux-weighted 
        centroiding. Next, this centroid is used as a starting point to find the centroid of the left column through 
        the same algorithm. 
        
        Parameters
        ----------

        image: numpy.array
            The image that wants to be traced.
        dqflags: ndarray
            The data quality flags for each pixel in the image. Only pixels with DQ flags of zero will be used 
            in the centroiding.
        xstart: float
            The x-position (column) on which the tracing algorithm will be started
        ystart: float
            The estimated y-position (row) of the center of the trace. An estimate within 10-20 pixels is enough.
        profile_radius: float
            Expected radius of the profile measured from its center. Only this region will be used to estimate 
            the centroids of the spectrum.
        nsigma : float
            Median filters are applied to each column in search of outliers. This number defines how many n-sigma above the noise level 
            the residuals of the median filter and the image should be considered outliers.
        gauss_filter_width: float
            Width of the gaussian filter used to perform the centroiding of the first column
        xend: int
            x-position at which tracing ends. If none, trace all the columns left to xstart.
        y_tolerance: float
            When tracing, if the difference between the two difference centroids at two contiguous columns is larger than this, 
            then assume tracing failed (e.g., cosmic ray).
        verbose: boolean
            If True, print error messages.

        Returns
        -------

        x : numpy.array
            Columns at which the centroid is calculated.
        y : numpy.array
            Calculated centroids.
        """
        def get_mad_sigma(x):

            x_median = np.nanmedian(x)

            return 1.4826 * np.nanmedian( np.abs(x - x_median) )

        # Define x-axis:
        if xend is not None:
            x = np.arange(xend, xstart + 1)
        else:
            x = np.arange(0, xstart + 1)
            
        # Define y-axis:
        y = np.arange(image.shape[0])
        
        # Define status of good/bad for each centroid:
        status = np.full(len(x), True, dtype=bool)
        
        # Define array that will save centroids at each x:
        ycentroids = np.zeros(len(x))
        
        for i in range(len(x))[::-1]:
            xcurrent = x[i]

            # Perform median filter to identify nasty (i.e., cosmic rays) outliers in the column:
            mf = median_filter(image[:,xcurrent], size = 5)
            residuals = mf - image[:,xcurrent]
            mad_sigma = get_mad_sigma(residuals)
            column_nsigma = np.abs(residuals) / mad_sigma
            
            # Extract data-quality flags for current column; index good pixels --- mask nans as well:
            idx_good = np.where((dqflags[:, xcurrent] == 0) & (~np.isnan(image[:, xcurrent]) & (column_nsigma < nsigma)))[0]        
            idx_bad = np.where(~(dqflags[:, xcurrent] == 0) & (~np.isnan(image[:, xcurrent]) & (column_nsigma < nsigma)))[0]
            
            if len(idx_good) > 0:

                # Replace bad values with the ones in the median filter:
                column_data = np.copy(image[:, xcurrent])
                column_data[idx_bad] = mf[idx_bad]

                # Convolve column with a gaussian filter; remove median before convolving:
                filtered_column = gaussian_filter1d(column_data - \
                                                    np.median(column_data), gauss_filter_width)
        
                # Find centroid within profile_radius pixels of the initial guess:
                idx = np.where(np.abs(y - ystart) < profile_radius)[0]
                ycentroids[i] = np.sum(y[idx] * filtered_column[idx]) / np.sum(filtered_column[idx])

                # Get the difference of the current centroid with the previous one (if any):
                if xcurrent != x[-1]:

                    previous_centroid = ycentroids[i + 1]
                    difference = np.abs(previous_centroid - ycentroids[i])

                    if (difference > y_tolerance):

                        if verbose:
                            print('Tracing failed at column',xcurrent,'; estimated centroid:',ycentroids[i],', previous one:',previous_centroid,'> than tolerance: ',y_tolerance,\
                                '. Replacing with closest good trace position.')

                        ycentroids[i] = previous_centroid
                        

                ystart = ycentroids[i]
            else:
                print(xcurrent,'is a bad column. Setting to previous centroid:')
                ycentroids[i] = previous_centroid
                status[i] = True
        
        # Return only good centroids:
        idx_output = np.where(status)[0]
        return x[idx_output], ycentroids[idx_output]


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

            self.query_start =  session.query(self.query_table).filter(func.max(self.query_table.end_time_mjd),
                                                self.query_table.instrument == self.instrument)

            new_entries = self.query_tso_observations(instrument, self.query_start, self.query_end)

            rootnames = list(set([row['fileSetName'] for row in new_entries]))

            monitor_file_suffix = ('photom.fits', 'acq.fits', 'jit.fits', 'whtlt.ecsv')


            # Update the query history
            new_entry = {'instrument': instrument,
                         'aperture': self.aperture,
                         'filter': self.filter,
                         'detector': self.detector,
                         'obslabel': self.obslabel,
                         'start_time_mjd': self.query_start,
                         'end_time_mjd': self.query_end,
                         'photom_file': self.photom_file,
                         'acq_file': self.acq_file,
                         'jit_file': self.jit_file,
                         'whtlt_file': self.whtlt_file,
                         'whtlt_mjd': self.whtlt_mjd,
                         'whtlt_flux':self.whtlt_flux,
                         'out_of_transit_median_flux': self.out_of_transit_median_flux,
                         'entry_date': datetime.datetime.now()}

            self.query_table.__table__.insert().execute(new_entry)
            logging.info('\tUpdated the tso monitor table')

        logging.info('TSO Monitor completed successfully.')


    def query_tso_observations(self, instrument, query_start, query_end):
        """Obtain all tso observations based on instrument and time.
        """

        parameters = {"date_obs_mjd": {"min": query_start, "max": query_end},
                      "tsovisit": "t"}

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                    add_filters=parameters, return_data=True, caom=False)
        self.data = query['data']