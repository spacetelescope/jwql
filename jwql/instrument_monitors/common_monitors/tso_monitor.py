
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
    - Jeff Valenti
Use
---
    This module can be used from the command line as such:
    ::
        python tso_monitor.py
"""

import datetime
import logging
import os

from astropy.time import Time
from datetime import datetime
from jwst import datamodels
import numpy as np
import pandas as pd
from requests import get as requests_get
from sqlalchemy import func

from jwql.database.database_interface import session
# from jwql.database.database_interface import NIRCamTsoMonitor, NIRSpecTsoMonitor, NIRISSTsoMonitor, MIRITsoMonitor
from jwql.jwql_monitors import monitor_mast
from jwql.utils.constants import JWST_DATAPRODUCTS, JWST_INSTRUMENT_NAMES, DETECTOR_PER_INSTRUMENT
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config


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

    Attributes
    ----------

    Raises
    ------

    """

    def __init__(self):
        """Initialize an instance of the ``tsoMonitor`` class."""

        self.token = get_config()['mast_token']
        self.baseurl = 'https://mast.stsci.edu/jwst/api/v0.1/' \
                        'Download/file?uri=mast:jwstedb'


    def compute_out_of_transit_flux(self):
        """Calculate the median out of transit flux.
        """
        # Extract very last times (corresponding to last segment):
        uncal_data = datamodels.open(self.uncal_file)
        times = uncal_data.int_times['int_mid_BJD_TDB'][-len(self.whtlt_flux):]

        # Convert to seconds since first integration on this last segment:
        times_seconds = (times - times[0]) * 24 * 3600.

        # self.median_out_of_transit_flux = np.median(ootf)


    def format_date(self, date):
        '''Convert datetime object or ISO 8501 string to EDB date format.'''
        if type(date) is str:
            dtobj = datetime.fromisoformat(date)
        elif type(date) is datetime:
            dtobj = date
        else:
            raise ValueError('date must be ISO 8501 string or datetime obj')

        return dtobj.strftime('%Y%m%dT%H%M%S')


    def get_jwstedb_data(self, mnemonic, start, end):
        '''Get engineering data for specified mnemonic and time interval.'''

        
        startdate = self.format_date(start)
        enddate = self.format_date(end)
        
        filename = f'{mnemonic}-{startdate}-{enddate}.csv'
        url = f'{self.baseurl}/{filename}'
        
        headers = {'Authorization': f'token {self.token}'}
        
        with requests_get(url, headers=headers, stream=True) as response:
            
            response.raise_for_status()
            
            lines = response.text.splitlines()
            time, time_mjd, value = self._parse(lines)
            
            return time, time_mjd, value


    def identify_tables(self):
        """Determine which database tables to use for a run of the dark
        monitor
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}TsoMonitor'.format(mixed_case_name))


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


    def _parse(self, lines):
        '''Parse lines of text returned by MAST EDB interface.'''

        from csv import reader as csv_reader
        from datetime import datetime

        # Define SQL-to-python datatype conversions. 
        # Taken from https://docs.microsoft.com/en-us/sql/machine-learning/python/python-libraries-and-data-types?view=sql-server-ver15
        cast = {'bigint': float, 
                'binary': bytes,
                'bit': bool,
                'char': str,
                'date': datetime,
                'datetime': datetime,
                'float': float, 
                'nchar': str,
                'nvarchar': str,
                'nvarchar(max)': str,
                'real': float,
                'smalldatetime': datetime,
                'smallint': int, 
                'tinyint': int,
                'uniqueidentifier': str,
                'varbinary': bytes,
                'varbinary(max)': bytes,
                'varchar': str, 
                'varchar(n)': str,
                'varchar(max)': str}
        
        # Set lists that will save the data:
        time = []
        time_mjd = []
        value = []

        for field in csv_reader(lines, delimiter=',', quotechar='"'):

            if field[0] == 'theTime':
                continue

            # Read in SQL data-type:
            sqltype = field[3]

            # Save time and value converted to python using the SQL data-type:
            time.append(datetime.fromisoformat(field[0]))
            time_mjd.append(float(field[1]))
            value.append(cast[sqltype](field[2]))

        return time, time_mjd, value


    def plot_acq_image(self):
        """Plot 2D acq image.
        """

        # use matplotlib
        print('plotting stuff here')


    def plot_spectrum_trace_and_jitter(self):
        """Plot the cross-correlation of the spectrum trace and jitter in the dispersion and x-dispersion directions.
        """
        #bokeh from database
        print('plotting stuff here')


    def plot_whitelight_curve(self):
        """Plot whitelight curve (band integrated light flux) vs wavelength and flux normalized to the median out-of-transit
        flux vs time.
        """
        # bokeh using database
        print('plotting stuff here')


    def plot_spectroscopic_lightcurves(self):
        """A surface plot of all spectral light curves: flux of each spectral light curve vs data point number
        with flux color bar.
        """
        # This will be plotted with matplotlib
        print('plotting stuff here')


    def plot_jitter(self):
        """Plot V1, V2, V3 jitter vs time.
        """
        # bokeh using database
        print('plotting stuff here')


    def process(self, fileset_dataframe):
        """Process and calculate statistics for database table.
        """
        # list file extensions
        file_exts = ['acq.fits', '.jit', 'whtlt.ecsv', 'x1d.fits']
        filenames = fileset_dataframe['files']
        for filename in filenames:
            # If file name in list of files doesn't contain extension we need, skip.
            if not any(filename.endswith(ext) for ext in file_exts):
                continue

            if filename.endswith('whtlt.ecsv'):
                self.process_whitelight_data(filename)
                self.plot_whitelight_curve(filename)
            
            if filename.endswith('acq.fits'):
                self.process_acq_image_centroids(filename)
                self.plot_acq_image(filename)

            if filename.endswith('jit.fits'):
                self.process_v2_v3_jitter(filename)
                self.plot_jitter(filename)
            
            if filename.endswith('x1d.fits'):
                self.process_spectrum_jitter(filename)
                self.plot_spectrum_trace_and_jitter(filename)
                self.plot_spectroscopic_lightcurves(filename)


    def process_acq_image_centroids(self, acq_file):
        """Find the centroid of the stars in acq image.

        acq_file : str
            full path to acq image
        """
        # hdu = fits.open(acq_file)
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

