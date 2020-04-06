#! /usr/bin/env python

"""This module contains code for the bad/dead pixel monitor, XXX
XXXXXXXXXXXXXX THIS DOCSTRING NEEDS TO BE UPDATED

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

    - Bryan Hilbert

Use
---

    This module can be used from the command line as such:

    ::

        python bad_pixel_monitor.py



Development notes:

This can't be used with NIRCam since NIRCam has no internal lamp and therefore
will not be taking any more internal flat field images. Could perhaps be used with
a series of external undithered observations...

Dead pixel algorithem was designed to use flats for all instruments except MIRI, which uses
darks. (Would anything useful result if using darks for NIRCam?)

Templates to use: FGS_INTFLAT, NIS_LAMP, NRS_LAMP, MIR_DARK











"""

from copy import copy, deepcopy
import datetime
import logging
import os

from astropy.io import ascii, fits
from astropy.modeling import models
from astropy.time import Time
from jwst.datamodels import dqflags
from jwst_reffiles.bad_pixel_mask.bad_pixel_mask import find_bad_pix as deadpix_search
from jwst_reffiles.dark_current.badpix_from_darks import find_bad_pix as noisypix_search
import numpy as np
from pysiaf import Siaf
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamDarkQueryHistory, NIRCamDarkPixelStats, NIRCamDarkDarkCurrent
from jwql.database.database_interface import NIRISSDarkQueryHistory, NIRISSDarkPixelStats, NIRISSDarkDarkCurrent
from jwql.database.database_interface import MIRIDarkQueryHistory, MIRIDarkPixelStats, MIRIDarkDarkCurrent
from jwql.database.database_interface import NIRSpecDarkQueryHistory, NIRSpecDarkPixelStats, NIRSpecDarkDarkCurrent
from jwql.database.database_interface import FGSDarkQueryHistory, FGSDarkPixelStats, FGSDarkDarkCurrent
from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils import calculations, instrument_properties
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_DATAPRODUCTS, \
                                 FLAT_EXP_TYPES, DARK_EXP_TYPES
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.mast_utils import mast_query
from jwql.utils.monitor_utils import initialize_instrument_monitor, update_monitor_table
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path

THRESHOLDS_FILE = os.path.join(os.path.split(__file__)[0], 'bad_pixel_file_thresholds.txt')

def bad_map_to_list(badpix_image, mnemonic):
    """Given an DQ image and a bad pixel mnemonic, create a list of (x,y)
    locations of this type of bad pixel in ```badpix_image```

    Parameters
    ----------
    badpix_image : numpy.ndarray
        2D image of bad pixels (i.e. a DQ array)

    mnemonic : str
        The type of bad pixel to map. The mnemonic must be one of those
        in the JWST calibration pipeline's list of possible mnemonics

    Returns
    -------
    x_loc : list
        List of x locations within ```badpix_image``` containing
        ```mnemonic``` pixels.

    y_loc : list
        List of x locations within ```badpix_image``` containing
        ```mnemonic``` pixels.
    """
    mnemonic = mnemonic.upper()
    possible_mnemonics = dqflags.pixel.keys()
    if mnemonic not in possible_mnemonics:
        raise ValueError("ERROR: Unrecognized bad pixel mnemonic: {}".format(mnemonic))

    # Find locations of this type of bad pixel
    y_loc, x_loc = np.where(badpix_image & dqflags.pixel[mnemonic] > 0)
    return x_loc, y_loc


def exclude_crds_mask_pix(bad_pix, existing_bad_pix):
    """Find differences between a set of newly-identified bad pixels
    and an existing set. Return a list of newly-discovered bad pixels
    that are not present in the existing set.

    Parameters
    ----------
    bad_pix : numpy.ndarray
        2D array of bad pixel flags. Flags must correspond to the
        defintiions used by the JWST calibration pipeline


    existing_bad_pix : numpy.ndarray
        2D array of bad pixel flags. Flags must correspond to the
        definitions used by the JWST calibration pipeline

    Returns
    -------
    new_bad_pix : numpy.ndarray
        2D array of bad pixel flags contained in ```bad_pix```
        but not ```existing_bad_pix```
    """
    return bad_pix - (bad_pix & existing_bad_pix)


def locate_rate_files(uncal_files):
        """Given a list of uncal (raw) files, generate a list of corresponding
        rate files. For each uncal file, if the rate file is present in the
        filesystem, add the name of the rate file (if a rateints file exists,
        use that) to the list of files. If no rate file is present, add None to
        the list.

        Parameters
        ----------
        uncal_files : list
            List of uncal files to use as the basis of the search

        Returns
        -------
        rate_files : list
            List of rate files. This list corresponds 1-to-1 with ``uncal_files``.
            Any missing rate files are listed as None.

        rate_files_to_copy : list
            Same as ``rate_files`` but without the None entries. This is a list
            of only the rate files that exist in the filesystem
        """
        rate_files = []
        rate_files_to_copy = []
        for uncal in uncal_files:
            base = uncal.split('_uncal.fits')[0]
            constructed_ratefile = '{}_rateints.fits'.format(base)
            try:
                rate_files.append(filesystem_path(constructed_ratefile))
                rate_files_to_copy.append(filesystem_path(constructed_ratefile))
            except FileNotFoundError:
                constructed_ratefile = '{}_rate.fits'.format(base)
                try:
                    rate_files.append(filesystem_path(constructed_ratefile))
                    rate_files_to_copy.append(filesystem_path(constructed_ratefile))
                except FileNotFoundError:
                    rate_files.append('None')
        return rate_files, rate_files_to_copy


def locate_uncal_files(query_result):
        """Given a MAST query result, locate the raw version (uncal.fits) of
        the listed files in the filesystem.

        Parameters
        ----------
        query_result : list
            MAST query results. List of dictionaries

        Returns
        -------
        uncal_files : list
            List of raw file locations within the filesystem
        """
        uncal_files = []
        for entry in query_result:
            filename = entry['filename']
            suffix = filename.split('_')[-1].strip('.fits')
            uncal_file = filename.replace(suffix, 'uncal')

            # Look for uncal file
            try:
                uncal_files.append(filesystem_path(uncal_file))
            except FileNotFoundError:
                logging.warning('\t\tUnable to locate {} in filesystem. Not including in processing.'
                                .format(uncal_file))
        return uncal_files


class BadPixels():
    """Class for executing the bad pixel monitor.


    XXXXX NEED TO UPATE DOCSTRING  XXXXXX

    This class will search for new (since the previous instance of the
    class) dark current files in the file system. It will loop over
    instrument/aperture combinations and find the number of new dark
    current files available. If there are enough, it will copy the files
    over to a working directory and run the monitor. This will create a
    mean dark current rate image, create a histogram of the dark current
    values, and fit several functions to the histogram. It will also
    compare the dark current image to a historical image in order to
    search for new hot or dead pixels. Results are all saved to
    database tables.

    Parameters
    ----------
    testing : bool
        For pytest. If ``True``, an instance of ``Dark`` is created, but
        no other code is executed.

    Attributes
    ----------
    output_dir : str
        Path into which outputs will be placed

    data_dir : str
        Path into which new dark files will be copied to be worked on

    query_start : float
        MJD start date to use for querying MAST

    query_end : float
        MJD end date to use for querying MAST

    instrument : str
        Name of instrument used to collect the dark current data

    aperture : str
        Name of the aperture used for the dark current (e.g.
        ``NRCA1_FULL``)

    query_table : sqlalchemy table
        Table containing the history of dark current queries to MAST
        for each instrument/aperture combination

    pixel_table : sqlalchemy table
        Table containing lists of bad pixels found for each
        instrument/detector

    Raises
    ------
    ValueError
        If encountering an unrecognized bad pixel type

    ValueError
        If the most recent query search returns more than one entry
    """

    def __init__(self):
        """Initialize an instance of the ``Dark`` class."""

    def add_bad_pix(self, coordinates, pixel_type, files, observation_start_time,
                    observation_mid_time, observation_end_time, baseline_file):
        """Add a set of bad pixels to the bad pixel database table

        Parameters
        ----------
        coordinates : tuple
            Tuple of two lists, containing x,y coordinates of bad
            pixels (Output of ``np.where`` call)

        pixel_type : str
            Type of bad pixel. e.g. ``dead``, ``hot``, and ``noisy``

        files : list
            List of fits files which were used to identify the bad
            pixels

        observation_start_time : datetime.datetime
            Observation time of the earliest file in ``files``

        observation_mid_time : datetime.datetime
            Average of the observation times in ``files``

        observation_end_time : datetime.datetime
            Observation time of the latest file in ``files``

        baseline_file : str
            Name of baseline bad pixel file against which the new bad
            pixel population was compared
        """

        logging.info('Adding {} {} pixels to database.'.format(len(coordinates[0]), pixel_type))

        source_files = [os.path.basename(item) for item in files]
        entry = {'detector': self.detector,
                 'x_coord': coordinates[0],
                 'y_coord': coordinates[1],
                 'type': pixel_type,
                 'source_files': source_files,
                 'obs_start_time': observation_start_time,
                 'obs_mid_time': observation_mid_time,
                 'obs_end_time': observation_end_time,
                 'baseline_file': baseline_file,
                 'entry_date': datetime.datetime.now()}
        self.pixel_table.__table__.insert().execute(entry)

    def get_metadata(self, filename):
        """Collect basic metadata from a fits file

        Parameters
        ----------
        filename : str
            Name of fits file to examine
        """

        header = fits.getheader(filename)

        try:
            self.detector = header['DETECTOR']
            self.x0 = header['SUBSTRT1']
            self.y0 = header['SUBSTRT2']
            self.xsize = header['SUBSIZE1']
            self.ysize = header['SUBSIZE2']
            self.nints = header['NINTS']
            self.sample_time = header['TSAMPLE']
            self.frame_time = header['TFRAME']
            self.read_pattern = header['READPATT']
            self.exp_type = header['EXP_TYPE']

        except KeyError as e:
            logging.error(e)

    def exclude_existing_badpix(self, badpix, pixel_type):
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

        if pixel_type not in ['hot', 'dead', 'noisy']:
            raise ValueError('Unrecognized bad pixel type: {}'.format(pixel_type))

        db_entries = session.query(self.pixel_table) \
            .filter(self.pixel_table.type == pixel_type) \
            .filter(self.pixel_table.detector == self.detector) \
            .all()

        already_found = []
        if len(db_entries) != 0:
            for _row in db_entries:
                x_coords = _row.x_coord
                y_coords = _row.y_coord
                for x, y in zip(x_coords, y_coords):
                    already_found.append((x, y))

        # Check to see if each pixel already appears in the database for
        # the given bad pixel type
        new_pixels_x = []
        new_pixels_y = []
        for x, y in zip(badpix[0], badpix[1]):
            pixel = (x, y)
            if pixel not in already_found:
                new_pixels_x.append(x)
                new_pixels_y.append(y)

        return (new_pixels_x, new_pixels_y)

    def identify_tables(self):
        """Determine which database tables to use for a run of the bad pixel
        monitor
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}BadPixelQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}BadPixelStats'.format(mixed_case_name))

    def map_uncal_and_rate_file_lists(self, uncal_files, rate_files, rate_files_to_copy, obs_type):
        """Copy uncal and rate files from the filesystem to the working
        directory. Any requested files that are not in the filesystem are
        noted and skipped. Return the file lists with skipped files removed.

        Parameters
        ----------
        uncal_files : list
            List of raw files to be copied

        rate_files : list
            List of rate (slope) images to be copied. This list should
            correspond 1-to-1 with ``uncal_files``. Any rate files that
            were not found in the MAST query should be set to None.

        rate_files_to_copy : list
            Similar to ``rate_files`` but with the None entries omitted.

        obs_type : str
            Observation type ("dark" or "flat"). Used only for logging

        Returns
        -------
        uncal_files : list
            List of the input raw files with any that failed to copy removed

        rate_files : list
            List of the input rate files with any that failed to copy removed
            (if the uncal also failed) or set to None (if only the rate file
            failed)
        """
        # Copy files from filesystem
        uncal_copied_files, uncal_not_copied = copy_files(uncal_files, self.data_dir)
        rate_copied_files, rate_not_copied = copy_files(rate_files_to_copy, self.data_dir)

        # Set any rate files that failed to copy to None so
        # that we can regenerate them
        if len(rate_not_copied) > 0:
            for badfile in rate_not_copied:
                rate_files[rate_files.index(badfile)] = 'None'

        # Any uncal files that failed to copy must be removed
        # entirely from the uncal and rate lists
        if len(uncal_not_copied) > 0:
            for badfile in uncal_not_copied:
                bad_index = uncal_files.index[badfile]
                del uncal_files[bad_index]
                del rate_files[bad_index]

        logging.info('\tNew {} observations: '.format(obs_type))
        logging.info('\tData dir: {}'.format(self.data_dir))
        logging.info('\tCopied to data dir: {}'.format(uncal_copied_files))
        logging.info('\tNot copied (failed, or missing from filesystem): {}'.format(uncal_not_copied))

        # After all this, the lists should be the same length
        # and have a 1-to-1 correspondence
        if len(uncal_files) != len(rate_files):
            print('Lists of {} uncal and rate files have different lengths!!'.format(obs_type))
            raise ValueError

        return uncal_files, rate_files

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
        sub_query = session.query(self.query_table.aperture,
                                  func.max(self.query_table.end_time_mjd).label('maxdate')
                                  ).group_by(self.query_table.aperture).subquery('t2')

        # Note that "self.query_table.run_monitor == True" below is
        # intentional. Switching = to "is" results in an error in the query.
        query = session.query(self.query_table).join(
            sub_query,
            and_(
                self.query_table.aperture == self.aperture,
                self.query_table.end_time_mjd == sub_query.c.maxdate,
                self.query_table.run_monitor == True
            )
        ).all()

        query_count = len(query)
        if query_count == 0:
            query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'
                         .format(self.aperture, query_result)))
        elif query_count > 1:
            raise ValueError('More than one "most recent" query?')
        else:
            query_result = query[0].end_time_mjd

        return query_result

    def make_crds_parameter_dict(self):
        """Construct a paramter dictionary to be used for querying CRDS

        Returns
        -------
        parameters : dict
            Dictionary of parameters, in the format expected by CRDS
        """
        parameters = {}
        parameters['INSTRUME'] = self.instrument.upper()
        parameters['SUBARRAY'] = 'FULL'
        parameters['DATE-OBS'] = datetime.date.today().isoformat()
        current_date = datetime.datetime.now()
        parameters['TIME-OBS'] = current_date.time().isoformat()
        parameters['DETECTOR'] = self.detector.upper()
        if instrument == 'NIRCAM':
            if parameters['DETECTOR'] in ['NRCALONG', 'NRCBLONG']:
                parameters['CHANNEL'] = 'LONG'
            else:
                parameters['CHANNEL'] = 'SHORT'
        return parameters

    def process(self, illuminated_raw_files, illuminated_slope_files, dark_raw_files, dark_slope_files):
        """The main method for processing darks.  See module docstrings
        for further details.

        Parameters
        ----------
        illuminated_raw_files : list
            List of filenames (including full paths) of raw (uncal) flat
            field files. These should all be for the same detector and
            aperture.

        illuminated_slope_files : list
            List of filenames (including full paths) of flat field slope
            files. These should all be for the same detector and aperture
            and correspond one-to-one with ``illuminated_raw_files``. For
            cases where a raw file exists but no slope file, the slope
            file should be None

        dark_raw_files : list
            List of filenames (including full paths) of raw (uncal) dark
            files. These should all be for the same detector and
            aperture.

        dark_slope_files : list
            List of filenames (including full paths) of dark current slope
            files. These should all be for the same detector and aperture
            and correspond one-to-one with ``dark_raw_files``. For
            cases where a raw file exists but no slope file, the slope
            file should be None
        """
        # Illuminated files - run entirety of calwebb_detector1 for uncal
        # files where corresponding rate file is 'None'
        badpix_types = []
        illuminated_obstimes = []
        if len(illuminated_raw_files) > 0:
            index = 0
            badpix_types.extend(['DEAD', 'LOW_QE', 'OPEN', 'ADJ_OPEN'])
            for uncal_file, rate_file in zip(illuminated_raw_files, illuminated_slope_files):
                if rate_file == 'None':
                    self.get_metadata(uncal_file)
                    jump_output, rate_output, junk = pipeline_tools.calwebb_detector1_save_jump(uncal_file, out_dir,
                                                                                          ramp_fit=True, save_fitopt=False)
                    if self.nints > 1:
                        illuminated_slope_files[index] = rate_output.replace('rate', 'rateints')
                    else:
                        illuminated_slope_files[index] = copy.deepcopy(rate_output)
                    index += 1

                # Get observation time for all files
                illuminated_obstimes.append(instrument_properties.get_obstime(uncal_file))

            min_illum_time = min(illuminated_obstimes)
            max_illum_time = max(illuminated_obstimes)
            mid_illum_time = instrument_properties.mean_time(illuminated_obstimes)

        # Dark files - Run calwebb_detector1 on all uncal files, saving the
        # Jump step output. If corresponding rate file is 'None', then also
        # run the ramp-fit step and save the output
        dark_jump_files = []
        dark_fitopts_files = []
        dark_obstimes = []
        if len(dark_raw_files) > 0:
            badpix_types.extend(['HOT', 'RC', 'OTHER_BAD_PIXEL', 'TELEGRAPH'])
            # In this case we need to run the pipeline on all input files,
            # even if the rate file is present, because we also need the jump
            # and fitops files, which are not saved by default
            for uncal_file, rate_file in zip(dark_raw_files, dark_slope_files):
                jump_output, rate_output, fitopt_output = pipeline_tools.calwebb_detector1_save_jump(uncal_file, out_dir,
                                                                                                     ramp_fit=save_rate, save_fitopt=True)
                self.get_metadata(uncal_file)
                dark_jump_files.append(jump_output)
                dark_fitopts_files.append(fitopt_output)
                if self.nints > 1:
                    dark_rates.append(rate_output.replace('rate', 'rateints'))
                else:
                    dark_rates.append(rate_output)
                dark_obstimes.append(instrument_properties.get_obstime(uncal_file))

            min_dark_time = min(dark_obstimes)
            max_dark_time = max(dark_obstimes)
            mid_dark_time = instrument_properties.mean_time(dark_obstimes)

        # Instrument-specific preferences from jwst_reffiles meetings
        if self.instrument in ['nircam', 'niriss', 'fgs']:
            dead_search_type = 'sigma_rate'
        elif self.instrument in ['miri', 'nirspec']:
            dead_search_type = 'absolute_rate'
            flat_mean_normalization_method = 'smoothed'

        # Call the bad pixel search module from jwst_reffiles. Lots of
        # other possible parameters. Only specify the non-default params
        # in order to make things easier to read.
        output_file = '{}_{}_{}_{}_bpm.fits'.format(self.instrument, self.aperture, self.query_start, self.query_end)
        output_file = os.path.join(self.output_dir, output_file)
        bad_pixel_mask.bad_pixels(flat_slope_files=illuminated_slope_files, dead_search_type=dead_search_type,
                                  flat_mean_normalization_method=flat_mean_normalization_method,
                                  run_dead_flux_check=True, dead_flux_check_files=illuminated_raw_files, flux_check=35000,
                                  dark_slope_files=dark_slope_files, dark_uncal_files=dark_raw_files,
                                  dark_jump_files=dark_jump_files, dark_fitopt_files=dark_fitopt_files, plot=False,
                                  output_file=output_file, author='jwst_reffiles', description='A bad pix mask',
                                  pedigree='GROUND', useafter='2222-04-01 00:00:00',
                                  history='This file was created by JWQL', quality_check=False)

        # Read in the newly-created bad pixel file
        badpix_map = fits.getdata(output_file)

        # Locate and read in the current bad pixel mask
        parameters = self.make_crds_parameter_dict()
        mask_dictionary = crds_tools.get_reffiles(parameters, ['mask'], download=True)
        baseline_file = mask_dictionary['mask']

        if 'NOT FOUND' in baseline_file:
            logging.warning(('\tNo baseline bad pixel file for {} {}. Any bad '
                             'pixels found as part of this search will be considered new'.format(self.instrument, self.aperture)))
            baseline_file = new_badpix_file
            with fits.open(illum_rates[0]) as hdulist:
                xd = hdulist[0].header[]
                yd = hdulist[0].header[] fix me
            baseline_badpix_mask = np.zeros((yd, xd), type=np.int)
        else:
            logging.info('\tBaseline bad pixel file is {}'.format(baseline_file))
            baseline_badpix_mask = fits.getdata(baseline_file)

        # Exclude hot and dead pixels in the current bad pixel mask
        #new_hot_pix = self.exclude_existing_badpix(new_hot_pix, 'hot')
        new_since_reffile = exclude_crds_mask_pix(badpix_map, baseline_badpix_mask)

        # Create a list of the new instances of each type of bad pixel
        bad_lists = {}
        for bad_type in badpix_types:
            bad_location_list = self.bad_map_to_list(new_since_reffile, bad_type)

            # Add new hot and dead pixels to the database
            logging.info('\tFound {} new {} pixels'.format(len(bad_location_list[0]), bad_type))
            self.add_bad_pix(bad_location_list, bad_type, file_list, min_time, mid_time, max_time, baseline_file)

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further
        details.

        There are 2 parts to the bad pixel monitor:
        1. Bad pixels from illuminated data
        2. Bad pixels from dark data

        For each, we will query MAST, copy new files from the filesystem
        and pass the list of copied files into the process() method.
        """
        logging.info('Begin logging for bad_pixel_monitor')

        apertures_to_skip = ['NRCALL_FULL', 'NRCAS_FULL', 'NRCBS_FULL']

        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'badpix_monitor')

        # Read in config file that defines the thresholds for the number
        # of dark files that must be present in order for the monitor to run
        limits = ascii.read(THRESHOLDS_FILE)

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd

        # Loop over all instruments
        for instrument in JWST_INSTRUMENT_NAMES:
            self.instrument = instrument

            # Identify which database tables to use
            self.identify_tables()

            # Get a list of all possible apertures from pysiaf
            if self.instrument == 'nircam':
                possible_apertures = []
                for i in range(1, 6):
                    possible_apertures.append('NRCA{}_FULL'.format(i))
                    possible_apertures.append('NRCB{}_FULL'.format(i))
            if self.instrument == 'niriss':
                possible_apertures = ['NIS_CEN']
            if self.instrument == 'miri':
                possible_apertures = ['MIRIM_FULL']
            if self.instrument == 'fgs':
                possible_apertures = ['FGS1_FULL', 'FGS2_FULL']
            if self.instrument == 'nirspec':
                possible_apertures = ['NRS1_FULL', 'NRS2_FULL']

            for aperture in possible_apertures:
                logging.info('')
                logging.info('Working on aperture {} in {}'.format(aperture, instrument))

                # Find the appropriate threshold for the number of new files needed
                match = aperture == limits['Aperture']
                flat_file_count_threshold = limits['FlatThreshold'][match]
                dark_file_count_threshold = limits['DarkThreshold'][match]

                # Locate the record of the most recent MAST search
                self.aperture = aperture
                self.query_start = self.most_recent_search()
                logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

                # Query MAST using the aperture and the time of the
                # most recent previous search as the starting time
                flat_templates = FLAT_EXP_TYPES[instrument]
                new_flat_entries = mast_query(instrument, aperture, flat_templates, self.query_start, self.query_end)

                dark_templates = DARK_EXP_TYPES[instrument]
                new_dark_entries = mast_query(instrument, aperture, dark_templates, self.query_start, self.query_end)

                # NIRISS - results can include rate, rateints, trapsfilled
                # MIRI - Jane says they now use illuminated data!!
                # NIRSpec - can be cal, x1d, rate, rateints can have both cal and x1d so filter repeats
                # FGS - rate, rateints, trapsfilled
                # NIRCam - no int flats

                # The query results can contain multiple entries for files
                # in different calibration states (or for different output
                # products), so we need to filter the list for duplicate
                # entries and for the calibration state we are interested
                # in before we know how many new entries there really are.

                # In the end, we need rate files as well as uncal files
                # because we're going to need to create jump files.
                rate_files = []
                uncal_files = []

                flat_uncal_files = locate_uncal_files(new_flat_entries)
                dark_uncal_files = locate_uncal_files(new_dark_entries)

                # Remove duplicates and check if there are enough new flat
                # field files
                if len(flat_uncal_files) > 0:
                    flat_uncal_files = list(set(flat_uncal_files))

                if len(flat_uncal_files) < flat_file_count_threshold:
                    logging.info(('\tBad pixels from flats skipped. {} new flat files for {}, {}. {} new files are '
                                  'required to run bad pixels from flats portion of monitor.').format(
                        len(new_flat_entries), instrument, aperture, flat_file_count_threshold[0]))
                    flat_uncal_files = []
                    run_flats = False

                else:
                    logging.info('\tSufficient new files found for {}, {} to run the bad pixel from flats portion of the monitor.'
                                 .format(self.instrument, self.aperture))
                    logging.info('\tNew entries: {}'.format(len(flat_uncal_files)))
                    run_flats = True

                # Remove duplicates and check if there are enough new dark
                # files
                if len(dark_uncal_files) > 0:
                    dark_uncal_files = list(set(dark_uncal_files))

                if len(dark_uncal_files) < dark_file_count_threshold:
                    logging.info(('\tBad pixels from darks skipped. {} new dark files for {}, {}. {} new files are '
                                  'required to run bad pixels from darks portion of monitor.').format(
                        len(new_dark_entries), instrument, aperture, dark_file_count_threshold[0]))
                    dark_uncal_files = []
                    run_darks = False

                else:
                    logging.info('\tSufficient new files found for {}, {} to run the bad pixel from darks portion of the monitor.'
                                 .format(self.instrument, self.aperture))
                    logging.info('\tNew entries: {}'.format(len(dark_uncal_files)))
                    run_darks = True

                # In order to use a given file we must have at least the
                # uncal version of the file. Get the uncal and rate file
                # lists to align.
                flat_rate_files, flat_rate_files_to_copy = locate_rate_files(flat_uncal_files)
                dark_rate_files, dark_rate_files_to_copy = locate_rate_files(dark_uncal_files)

                # Set up directories for the copied data
                ensure_dir_exists(os.path.join(self.output_dir, 'data'))
                self.data_dir = os.path.join(self.output_dir,
                                             'data/{}_{}'.format(self.instrument.lower(),
                                                                 self.aperture.lower()))
                ensure_dir_exists(self.data_dir)

                # Copy files from filesystem
                if len(flat_uncal_files) > 0:
                    flat_uncal_files, flat_rate_files = self.map_uncal_and_rate_file_lists(flat_uncal_files,
                                                                                           flat_rate_files,
                                                                                           flat_rate_files_to_copy,
                                                                                           'flat')

                if len(dark_uncal_files) > 0:
                    dark_uncal_files, dark_rate_files = self.map_uncal_and_rate_file_lists(dark_uncal_files,
                                                                                           dark_rate_files,
                                                                                           dark_rate_files_to_copy,
                                                                                           'dark')

                # Run the bad pixel monitor
                if run_flats or run_darks:
                    self.process(flat_uncal_files, flat_rate_files, dark_uncal_files, dark_rate_files)

                # Update the query history
                new_entry = {'instrument': self.instrument.upper(),
                             'aperture': aperture,
                             'start_time_mjd': self.query_start,
                             'end_time_mjd': self.query_end,
                             'flat_files_found': len(new_flat_entries[0]),
                             'dark_files_found': len(new_dark_entries[0]),
                             'run_flats': run_flats,
                             'run_darks': run_darks,
                             'run_monitor': run_flats or run_darks,
                             'entry_date': datetime.datetime.now()}
                self.query_table.__table__.insert().execute(new_entry)
                logging.info('\tUpdated the query history table')

        logging.info('Bad Pixel Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Dark()
    monitor.run()

    update_monitor_table(module, start_time, log_file)
