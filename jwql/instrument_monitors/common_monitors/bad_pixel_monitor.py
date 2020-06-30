#! /usr/bin/env python

"""This module contains code for the bad/dead pixel monitor.

The monitor calls the ``bad_pixel_mask.py`` module in the
``spacetelescope/jwst_reffiles`` package in order to identify bad
pixels. (``https://github.com/spacetelescope/jwst_reffiles``)

The definitions of the bad pixel types to be searched for are given
in the jwst package:
``https://jwst-pipeline.readthedocs.io/en/stable/jwst/references_general/
references_general.html#data-quality-flags``

The bad pixel search is composed of two different parts, each of which
can be run independently.

1. Internal flat field exposures are used to search for ``DEAD``,
``LOW QE``, ``OPEN``, and ``ADJACENT TO OPEN`` pixels.

2. Dark current exposures are used to search for ``NOISY``, ``HOT``,
``RC``, ``TELEGRAPH``, and ``LOW_PEDESTAL`` pixels.

Both of these modules expect input data in at least 2 calibration
states. In practice, the bad pixel monitor will search MAST for the
appropriate dark current and flat field files. In both cases, a given
file is considered useful if the uncal (and potentially the rate)
versions of the file are present in the archive. For files where the
uncal version only is found, the pipeline is run to produce the rate
file.

Once a sufficient number of new flats or darks are identified, the bad
pixel montior is called. The ``bad_pixel_file_thresholds.txt`` file
contains a list of the minimum number of new files necessary to run the
monitor for each instrument and aperture.

For the flat field files, the pipeline is run on the uncal files far
enough to produce cosmic ray flagged (jump) files. These are also
needed for the bad pixel search.

The ``jwst_reffiles`` ``bad_pixel_mask.py`` is run, and returns a map of
bad pixels for each of the various bad pixel mnemonics. The
``bad_pixel_monitor`` then downloads the latest bad pixel mask in CRDS
for the given instrument and detector/aperture, and this is compared to
the new map of bad pixels. For each bad pixel mnemonic, any pixels
flagged as bad that are not bad in the current reference file are saved
to the (e.g. ``NIRCamBadPixelStats``) database table.

Author
------

    - Bryan Hilbert

Use
---

    This module can be used from the command line as such:

    ::

        python bad_pixel_monitor.py

Notes
-----

The bad pixel flat that utilizes flat field ramps can't be used with
NIRCam since NIRCam has no internal lamp and therefore will not be
taking any more internal flat field images. Could perhaps be used with
a series of external undithered observations, but that's something to
think about later.

Templates to use: ``FGS_INTFLAT``, ``NIS_LAMP``, ``NRS_LAMP``,
``MIR_DARK``
"""

from copy import deepcopy
import datetime
import logging
import os

from astropy.io import ascii, fits
from astropy.time import Time
from jwst.datamodels import dqflags
from jwst_reffiles.bad_pixel_mask import bad_pixel_mask
import numpy as np
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamBadPixelQueryHistory, NIRCamBadPixelStats
from jwql.database.database_interface import NIRISSBadPixelQueryHistory, NIRISSBadPixelStats
from jwql.database.database_interface import MIRIBadPixelQueryHistory, MIRIBadPixelStats
from jwql.database.database_interface import NIRSpecBadPixelQueryHistory, NIRSpecBadPixelStats
from jwql.database.database_interface import FGSBadPixelQueryHistory, FGSBadPixelStats
from jwql.instrument_monitors import pipeline_tools
from jwql.utils import crds_tools, instrument_properties
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, \
                                 FLAT_EXP_TYPES, DARK_EXP_TYPES
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.mast_utils import mast_query
from jwql.utils.monitor_utils import initialize_instrument_monitor, update_monitor_table
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path

THRESHOLDS_FILE = os.path.join(os.path.split(__file__)[0], 'bad_pixel_file_thresholds.txt')


def bad_map_to_list(badpix_image, mnemonic):
    """Given an DQ image and a bad pixel mnemonic, create a list of
    (x,y) locations of this type of bad pixel in ``badpix_image``

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
        List of x locations within ``badpix_image`` containing
        ``mnemonic`` pixels.

    y_loc : list
        List of x locations within ``badpix_image`` containing
        ``mnemonic`` pixels.
    """
    mnemonic = mnemonic.upper()
    possible_mnemonics = dqflags.pixel.keys()
    if mnemonic not in possible_mnemonics:
        raise ValueError("ERROR: Unrecognized bad pixel mnemonic: {}".format(mnemonic))

    # Find locations of this type of bad pixel
    y_loc, x_loc = np.where(badpix_image & dqflags.pixel[mnemonic] > 0)

    # Convert from numpy int to python native int, in order to avoid SQL
    # error when adding to the database tables.
    y_location = [int(element) for element in y_loc]
    x_location = [int(element) for element in x_loc]

    return x_location, y_location


def check_for_sufficient_files(uncal_files, instrument_name, aperture_name, threshold_value, file_type):
    """From a list of files of a given type (flats or darks), check to
    see if there are enough files to call the bad pixel monitor. The
    number of files must be equal to or greater than the provided
    ``threshold_value``.

    Parameters
    ----------
    uncal_files : list
        List of filenames

    instrument_name : str
        Name of JWST instrument (e.g. ``nircam``) that the data are
        from. This is used only in logging statements

    aperture_name : str
        Name of aperture (e.g.`` NRCA1_FULL``) that the data are from.
        This is used only in logging statements

    threshold_value : int
        Minimum number of files required in order to run the bad pixel
        monitor

    file_type : str
        Either `darks`` or ``flats``. This is used only in the logging
        statements.

    Returns
    -------
    uncal_files : list
        List of sorted, unique files from the input file list. Set to
        ``None`` if the number of unique files is under the threshold

    run_data : bool
        Whether or not the bad pixel monitor will be called on these
        files.
    """
    if file_type not in ['darks', 'flats']:
        raise ValueError('Input file_type must be "darks" or "flats"')
    file_type_singular = file_type.strip('s')

    if len(uncal_files) > 0:
        uncal_files = sorted(list(set(uncal_files)))

    if len(uncal_files) < threshold_value:
        logging.info(('\tBad pixels from {} skipped. {} new {} files for {}, {} found. {} new files are '
                      'required to run bad pixels from {} portion of monitor.')
                      .format(file_type, len(uncal_files), file_type_singular, instrument_name, aperture_name, threshold_value, file_type))
        uncal_files = None
        run_data = False

    else:
        logging.info('\tSufficient new files found for {}, {} to run the bad pixel from {} portion of the monitor.'
                     .format(instrument_name, aperture_name, file_type))
        logging.info('\tNew entries: {}'.format(len(uncal_files)))
        run_data = True
    return uncal_files, run_data


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
        2D array of bad pixel flags contained in ``bad_pix``
        but not ``existing_bad_pix``
    """
    return bad_pix - (bad_pix & existing_bad_pix)

def locate_rate_files(uncal_files):
    """Given a list of uncal (raw) files, generate a list of
    corresponding rate files. For each uncal file, if the rate file
    is present in the filesystem, add the name of the rate file (if
    a rateints file exists, use that) to the list of files. If no
    rate file is present, add ``None`` to the list.

    Parameters
    ----------
    uncal_files : list
        List of uncal files to use as the basis of the search

    Returns
    -------
    rate_files : list
        List of rate files. This list corresponds 1-to-1 with
        ``uncal_files``. Any missing rate files are listed as None.

    rate_files_to_copy : list
        Same as ``rate_files`` but without the None entries. This is
        a list of only the rate files that exist in the filesystem
    """
    if uncal_files is None:
        return None, None

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
    """Given a MAST query result, locate the raw version
    (``uncal.fits``) of the listed files in the filesystem.

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
        suffix = filename.split('_')[-1].replace('.fits', '')
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

    This class will search for new (since the previous instance of the
    class) dark current and internal flat field files in the filesystem.
    It will loop over instrument/aperture combinations and find the
    number of new dark/flat files available. If there are enough, it
    will copy the files over to a working directory and run the monitor.

    This will use the ``jwst_reffiles`` package to locate new bad
    pixels, which will be returned as a map. This map will be compared
    to the current bad pixel reference file (``dq_init``) in CRDS, and
    any the coordinates and type of any new bad pixels will be saved in
    a database table.

    Attributes
    ----------
    aperture : str
        Aperture name of the data (e.g. ``NRCA1_FULL``)

    dark_query_start : float
        Date (in ``MJD``) of the ending range of the previous MAST query
        where the bad pixel from darks monitor was run.

    data_dir : str
        Directory that contains the files copied from MAST to be used
        by the bad pixel monitor

    detector : str
        Detector associated with the data (e.g. ``NRCA1``)

    flat_query_start : float
        Date (in MJD) of the ending range of the previous MAST query
        where the bad pixel from flats monitor was run.

    instrument : str
        Name of the JWST instrument the data are from

    nints : int
        Number of integrations in the exposure

    output_dir : str
        Top level output directory associated with the bad pixel
        monitor, as retrieved from the JWQL config file

    pixel_table : sqlalchemy table
        Database table containing lists of bad pixels identified
        during runs of the bad pixel monitor

    query_end : float
        MJD of the execution time of the bad pixel monitor. This is
        used as the ending time of the MAST query.

    query_table : sqlalchemy table
        Database table containing the history of MAST queries
        for the bad pixel monitor.

    Raises
    ------
    ValueError
        If NINT or DETECTOR is missing from input file header

    ValueError
        If an unrecognized bad pixel mnemonic is encountered

    ValueError
        If the number of uncal and rate files does not match

    ValueError
        If the most recent query search returns more than one entry
    """

    def __init__(self):
        """Initialize an instance of the ``BadPixels`` class."""

    def add_bad_pix(self, coordinates, pixel_type, files, obs_start_time, obs_mid_time, obs_end_time, baseline_file):
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

        obs_start_time : datetime.datetime
            Observation time of the earliest file in ``files``

        obs_mid_time : datetime.datetime
            Average of the observation times in ``files``

        obs_end_time : datetime.datetime
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
                 'obs_start_time': obs_start_time,
                 'obs_mid_time': obs_mid_time,
                 'obs_end_time': obs_end_time,
                 'baseline_file': baseline_file,
                 'entry_date': datetime.datetime.now()}
        self.pixel_table.__table__.insert().execute(entry)

    def filter_query_results(self, results, datatype):
        """Filter MAST query results. For input flats, keep only those
        with the most common filter/pupil/grating combination. For both
        flats and darks, keep only those with the most common readout
        pattern.

        Parameters
        ----------
        results : list
            List of query results, as returned by ``mast_query()``

        datatype : str
            Type of data being filtered. ``flat`` or ``dark``.

        Returns
        -------
        readpatt_filtered : list
            Filtered list of query results.
        """
        # Need to filter all instruments' results by filter. Choose filter with the most files
        # Only for flats
        if ((datatype == 'flat') and (self.instrument != 'fgs')):
            if self.instrument in ['nircam', 'niriss']:
                filter_on = 'pupil'
            elif self.instrument == 'nirspec':
                filter_on = 'grating'
            elif self.instrument == 'miri':
                filter_on = 'filter'

            filter_list = ['{}:{}'.format(entry['filter'], entry[filter_on]) for entry in results]
            filter_set = list(set(filter_list))

            # Find the filter with the largest number of entries
            maxnum = 0
            maxfilt = ''
            for filt in filter_set:
                if filter_list.count(filt) > maxnum:
                    maxnum = filter_list.count(filt)
                    maxfilt = filt
            filter_name, other_name = maxfilt.split(':')

            filtered = []
            for entry in results:
                if ((str(entry['filter']) == filter_name) and (str(entry[filter_on]) == other_name)):
                    filtered.append(entry)

            results = deepcopy(filtered)

        # All instruments: need to filter by readout pattern. Any pattern name not containing "IRS2" is ok
        # choose readout pattern with the most entries
        readpatt_list = [entry['readpatt'] for entry in results]
        readpatt_set = list(set(readpatt_list))

        maxnum = 0
        maxpatt = ''
        for patt in readpatt_set:
            if ((readpatt_list.count(patt) > maxnum) and ('IRS2' not in patt)):
                maxnum = readpatt_list.count(patt)
                maxpatt = patt

        # Find the readpattern with the largest number of entries
        readpatt_filtered = []
        for entry in results:
            if entry['readpatt'] == maxpatt:
                readpatt_filtered.append(entry)

        return readpatt_filtered

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
            self.nints = header['NINTS']

        except KeyError as e:
            logging.error(e)

    def get_possible_apertures(self):
        """Generate a list of possible SIAF apertures for the given
        instrument.

        Returns
        -------
        possible_aperture : list
            List of acceptible apertures for self.instrument
        """
        if self.instrument == 'nircam':
            possible_apertures = []
            for i in range(1, 6):
                possible_apertures.append('NRCA{}_FULL'.format(i))
                possible_apertures.append('NRCB{}_FULL'.format(i))
        if self.instrument == 'niriss':
            possible_apertures = ['NIS_CEN']
        if self.instrument == 'miri':
            # Since MIRI is organized a little bit differently than the
            # other instruments, you can't use aperture names to uniquely
            # identify the full frame darks/flats from a given detector.
            # Instead you must use detector names.
            possible_apertures = [('MIRIMAGE', 'MIRIM_FULL'), ('MIRIFULONG', 'MIRIM_FULL'), ('MIRIFUSHORT', 'MIRIM_FULL')]
        if self.instrument == 'fgs':
            possible_apertures = ['FGS1_FULL', 'FGS2_FULL']
        if self.instrument == 'nirspec':
            possible_apertures = ['NRS1_FULL', 'NRS2_FULL']
        return possible_apertures

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
        directory. Any requested files that are not in the filesystem
        are noted and skipped. Return the file lists with skipped files
        removed.

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
            Observation type (``dark`` or ``flat``). Used only for
            logging

        Returns
        -------
        uncal_files : list
            List of the input raw files with any that failed to copy
            removed

        rate_files : list
            List of the input rate files with any that failed to copy
            removed (if the uncal also failed) or set to None (if only
            the rate file failed)
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
                bad_index = uncal_files.index(badfile)
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

    def most_recent_search(self, file_type='dark'):
        """Query the query history database and return the information
        on the most recent query for the given ``aperture_name`` where
        the dark monitor was executed.

        Parameters
        ----------
        file_type : str
            ``dark`` or ``flat``. Specifies the type of file whose
            previous search time is queried.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the dark monitor was run.
        """
        if file_type.lower() == 'dark':
            mjd_field = self.query_table.dark_end_time_mjd
        elif file_type.lower() == 'flat':
            mjd_field = self.query_table.flat_end_time_mjd

        sub_query = session.query(self.query_table.aperture,
                                  func.max(mjd_field).label('maxdate')
                                  ).group_by(self.query_table.aperture).subquery('t2')

        # Note that "self.query_table.run_monitor == True" below is
        # intentional. Switching = to "is" results in an error in the query.
        query = session.query(self.query_table).join(
            sub_query,
            and_(
                self.query_table.aperture == self.aperture,
                mjd_field == sub_query.c.maxdate,
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
            if file_type.lower() == 'dark':
                query_result = query[0].dark_end_time_mjd
            elif file_type.lower() == 'flat':
                query_result = query[0].flat_end_time_mjd

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
        if self.instrument.upper() == 'NIRCAM':
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
            files. These should all be for the same detector and
            aperture and correspond one-to-one with
            ``illuminated_raw_files``. For cases where a raw file exists
            but no slope file, the slope file should be None

        dark_raw_files : list
            List of filenames (including full paths) of raw (uncal) dark
            files. These should all be for the same detector and
            aperture.

        dark_slope_files : list
            List of filenames (including full paths) of dark current
            slope files. These should all be for the same detector and
            aperture and correspond one-to-one with ``dark_raw_files``.
            For cases where a raw file exists but no slope file, the
            slope file should be ``None``
        """
        # Illuminated files - run entirety of calwebb_detector1 for uncal
        # files where corresponding rate file is 'None'
        all_files = []
        badpix_types = []
        badpix_types_from_flats = ['DEAD', 'LOW_QE', 'OPEN', 'ADJ_OPEN']
        badpix_types_from_darks = ['HOT', 'RC', 'OTHER_BAD_PIXEL', 'TELEGRAPH']
        illuminated_obstimes = []
        if illuminated_raw_files:
            index = 0
            badpix_types.extend(badpix_types_from_flats)
            for uncal_file, rate_file in zip(illuminated_raw_files, illuminated_slope_files):
                self.get_metadata(uncal_file)
                if rate_file == 'None':
                    jump_output, rate_output, _ = pipeline_tools.calwebb_detector1_save_jump(uncal_file, self.data_dir,
                                                                                             ramp_fit=True, save_fitopt=False)
                    if self.nints > 1:
                        illuminated_slope_files[index] = rate_output.replace('0_ramp_fit', '1_ramp_fit')
                    else:
                        illuminated_slope_files[index] = deepcopy(rate_output)
                    index += 1

                # Get observation time for all files
                illuminated_obstimes.append(instrument_properties.get_obstime(uncal_file))

            all_files = deepcopy(illuminated_slope_files)

            min_illum_time = min(illuminated_obstimes)
            max_illum_time = max(illuminated_obstimes)
            mid_illum_time = instrument_properties.mean_time(illuminated_obstimes)

        # Dark files - Run calwebb_detector1 on all uncal files, saving the
        # Jump step output. If corresponding rate file is 'None', then also
        # run the ramp-fit step and save the output
        dark_jump_files = []
        dark_fitopt_files = []
        dark_obstimes = []
        if dark_raw_files:
            index = 0
            badpix_types.extend(badpix_types_from_darks)
            # In this case we need to run the pipeline on all input files,
            # even if the rate file is present, because we also need the jump
            # and fitops files, which are not saved by default
            for uncal_file, rate_file in zip(dark_raw_files, dark_slope_files):
                jump_output, rate_output, fitopt_output = pipeline_tools.calwebb_detector1_save_jump(uncal_file, self.data_dir,
                                                                                                     ramp_fit=True, save_fitopt=True)
                self.get_metadata(uncal_file)
                dark_jump_files.append(jump_output)
                dark_fitopt_files.append(fitopt_output)
                if self.nints > 1:
                    #dark_slope_files[index] = rate_output.replace('rate', 'rateints')
                    dark_slope_files[index] = rate_output.replace('0_ramp_fit', '1_ramp_fit')
                else:
                    dark_slope_files[index] = deepcopy(rate_output)
                dark_obstimes.append(instrument_properties.get_obstime(uncal_file))
                index += 1

            if len(all_files) == 0:
                all_files = deepcopy(dark_slope_files)
            else:
                all_files = all_files + dark_slope_files

            min_dark_time = min(dark_obstimes)
            max_dark_time = max(dark_obstimes)
            mid_dark_time = instrument_properties.mean_time(dark_obstimes)

        # For the dead flux check, filter out any files that have less than
        # 4 groups
        dead_flux_files = []
        if illuminated_raw_files:
            for illum_file in illuminated_raw_files:
                ngroup = fits.getheader(illum_file)['NGROUPS']
                if ngroup >= 4:
                    dead_flux_files.append(illum_file)
        if len(dead_flux_files) == 0:
            dead_flux_files = None

        # Instrument-specific preferences from jwst_reffiles meetings
        if self.instrument in ['nircam', 'niriss', 'fgs']:
            dead_search_type = 'sigma_rate'
        elif self.instrument in ['miri', 'nirspec']:
            dead_search_type = 'absolute_rate'

        flat_mean_normalization_method = 'smoothed'

        # Call the bad pixel search module from jwst_reffiles. Lots of
        # other possible parameters. Only specify the non-default params
        # in order to make things easier to read.
        query_string = 'darks_{}_flats_{}_to_{}'.format(self.dark_query_start, self.flat_query_start, self.query_end)
        output_file = '{}_{}_{}_bpm.fits'.format(self.instrument, self.aperture, query_string)
        output_file = os.path.join(self.output_dir, output_file)
        bad_pixel_mask.bad_pixels(flat_slope_files=illuminated_slope_files, dead_search_type=dead_search_type,
                                  flat_mean_normalization_method=flat_mean_normalization_method,
                                  run_dead_flux_check=True, dead_flux_check_files=dead_flux_files, flux_check=35000,
                                  dark_slope_files=dark_slope_files, dark_uncal_files=dark_raw_files,
                                  dark_jump_files=dark_jump_files, dark_fitopt_files=dark_fitopt_files, plot=False,
                                  output_file=output_file, author='jwst_reffiles', description='A bad pix mask',
                                  pedigree='GROUND', useafter='2222-04-01 00:00:00',
                                  history='This file was created by JWQL', quality_check=False)

        # Read in the newly-created bad pixel file
        set_permissions(output_file)
        badpix_map = fits.getdata(output_file)

        # Locate and read in the current bad pixel mask
        parameters = self.make_crds_parameter_dict()
        mask_dictionary = crds_tools.get_reffiles(parameters, ['mask'], download=True)
        baseline_file = mask_dictionary['mask']

        if 'NOT FOUND' in baseline_file:
            logging.warning(('\tNo baseline bad pixel file for {} {}. Any bad '
                             'pixels found as part of this search will be considered new'.format(self.instrument, self.aperture)))
            baseline_file = new_badpix_file
            yd, xd = badpix_mask.shape
            baseline_badpix_mask = np.zeros((yd, xd), type=np.int)
        else:
            logging.info('\tBaseline bad pixel file is {}'.format(baseline_file))
            baseline_badpix_mask = fits.getdata(baseline_file)

        # Exclude hot and dead pixels in the current bad pixel mask
        #new_hot_pix = self.exclude_existing_badpix(new_hot_pix, 'hot')
        new_since_reffile = exclude_crds_mask_pix(badpix_map, baseline_badpix_mask)

        # Create a list of the new instances of each type of bad pixel
        for bad_type in badpix_types:
            bad_location_list = bad_map_to_list(new_since_reffile, bad_type)

            # Add new hot and dead pixels to the database
            logging.info('\tFound {} new {} pixels'.format(len(bad_location_list[0]), bad_type))

            if bad_type in badpix_types_from_flats:
                self.add_bad_pix(bad_location_list, bad_type, illuminated_slope_files, min_illum_time, mid_illum_time, max_illum_time, baseline_file)
            elif bad_type in badpix_types_from_darks:
                self.add_bad_pix(bad_location_list, bad_type, dark_slope_files, min_dark_time, mid_dark_time, max_dark_time, baseline_file)
            else:
                raise ValueError("Unrecognized type of bad pixel: {}. Cannot update database table.".format(bad_type))

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details.

        There are 2 parts to the bad pixel monitor:
        1. Bad pixels from illuminated data
        2. Bad pixels from dark data

        For each, we will query MAST, copy new files from the filesystem
        and pass the list of copied files into the ``process()`` method.
        """
        logging.info('Begin logging for bad_pixel_monitor')

        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'bad_pixel_monitor')

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
            possible_apertures = self.get_possible_apertures()

            for aperture in possible_apertures:
                grating = None
                detector_name = None
                lamp = None

                # NIRSpec flats use the MIRROR grating.
                if self.instrument == 'nirspec':
                    grating = 'MIRROR'

                # MIRI is unlike the other instruments. We basically treat
                # the detector as the aperture name because there is no
                # aperture name for a full frame MRS exposure.
                if self.instrument == 'miri':
                    detector_name, aperture_name = aperture
                    self.aperture = detector_name
                else:
                    self.aperture = aperture
                    aperture_name = aperture

                # In flight, NIRISS plans to take darks using the LINE2 lamp
                if self.instrument == 'niriss':
                    lamp = 'LINE2'

                # What lamp is most appropriate for NIRSpec?
                if self.instrument == 'nirspec':
                    lamp = 'LINE2'

                # What lamp is most appropriate for FGS?
                #if self.instrument == 'fgs':
                #    lamp = 'G2LAMP1'

                logging.info('')
                logging.info('Working on aperture {} in {}'.format(aperture, self.instrument))

                # Find the appropriate threshold for the number of new files needed
                match = self.aperture == limits['Aperture']
                flat_file_count_threshold = limits['FlatThreshold'][match].data[0]
                dark_file_count_threshold = limits['DarkThreshold'][match].data[0]

                # Locate the record of the most recent MAST search
                self.flat_query_start = self.most_recent_search(file_type='flat')
                self.dark_query_start = self.most_recent_search(file_type='dark')
                logging.info('\tFlat field query times: {} {}'.format(self.flat_query_start, self.query_end))
                logging.info('\tDark current query times: {} {}'.format(self.dark_query_start, self.query_end))

                # Query MAST using the aperture and the time of the most
                # recent previous search as the starting time.
                flat_templates = FLAT_EXP_TYPES[instrument]
                dark_templates = DARK_EXP_TYPES[instrument]

                new_flat_entries = mast_query(instrument, flat_templates, self.flat_query_start, self.query_end,
                                              aperture=aperture_name, grating=grating, detector=detector_name,
                                              lamp=lamp)
                new_dark_entries = mast_query(instrument, dark_templates, self.dark_query_start, self.query_end,
                                              aperture=aperture_name, detector=detector_name)

                # Filter the results
                # Filtering could be different for flats vs darks.
                # Kevin says we shouldn't need to worry about mixing lamps in the data used to create the bad pixel
                # mask. In flight, data will only be taken with LINE2, LEVEL 5. Currently in MAST all lamps are
                # present, but Kevin is not concerned about variations in flat field strucutre.

                # NIRISS - results can include rate, rateints, trapsfilled
                # MIRI - Jane says they now use illuminated data for dead pixel checks, just like other insts.
                # NIRSpec - can be cal, x1d, rate, rateints. Can have both cal and x1d so filter repeats
                # FGS - rate, rateints, trapsfilled
                # NIRCam - no int flats

                # The query results can contain multiple entries for files
                # in different calibration states (or for different output
                # products), so we need to filter the list for duplicate
                # entries and for the calibration state we are interested
                # in before we know how many new entries there really are.

                # In the end, we need rate files as well as uncal files
                # because we're going to need to create jump files.
                # In order to use a given file we must have at least the
                # uncal version of the file. Get the uncal and rate file
                # lists to align.

                if new_flat_entries:
                    new_flat_entries = self.filter_query_results(new_flat_entries, datatype='flat')
                    flat_uncal_files = locate_uncal_files(new_flat_entries)
                    flat_uncal_files, run_flats = check_for_sufficient_files(flat_uncal_files, instrument, aperture, flat_file_count_threshold, 'flats')
                    flat_rate_files, flat_rate_files_to_copy = locate_rate_files(flat_uncal_files)
                else:
                    run_flats = False
                    flat_uncal_files, flat_rate_files, flat_rate_files_to_copy = None, None, None

                if new_dark_entries:
                    new_dark_entries = self.filter_query_results(new_dark_entries, datatype='dark')
                    dark_uncal_files = locate_uncal_files(new_dark_entries)
                    dark_uncal_files, run_darks = check_for_sufficient_files(dark_uncal_files, instrument, aperture, dark_file_count_threshold, 'darks')
                    dark_rate_files, dark_rate_files_to_copy = locate_rate_files(dark_uncal_files)
                else:
                    run_darks = False
                    dark_uncal_files, dark_rate_files, dark_rate_files_to_copy = None, None, None

                # Set up directories for the copied data
                ensure_dir_exists(os.path.join(self.output_dir, 'data'))
                self.data_dir = os.path.join(self.output_dir, 'data/{}_{}'.format(self.instrument.lower(), self.aperture.lower()))
                ensure_dir_exists(self.data_dir)

                # Copy files from filesystem
                if run_flats:
                    flat_uncal_files, flat_rate_files = self.map_uncal_and_rate_file_lists(flat_uncal_files, flat_rate_files, flat_rate_files_to_copy, 'flat')
                if run_darks:
                    dark_uncal_files, dark_rate_files = self.map_uncal_and_rate_file_lists(dark_uncal_files, dark_rate_files, dark_rate_files_to_copy, 'dark')

                # Run the bad pixel monitor
                if run_flats or run_darks:
                    self.process(flat_uncal_files, flat_rate_files, dark_uncal_files, dark_rate_files)

                # Update the query history
                if dark_uncal_files is None:
                    num_dark_files = 0
                else:
                    num_dark_files = len(dark_uncal_files)

                if flat_uncal_files is None:
                    num_flat_files = 0
                else:
                    num_flat_files = len(flat_uncal_files)

                new_entry = {'instrument': self.instrument.upper(),
                             'aperture': self.aperture,
                             'dark_start_time_mjd': self.dark_query_start,
                             'dark_end_time_mjd': self.query_end,
                             'flat_start_time_mjd': self.flat_query_start,
                             'flat_end_time_mjd': self.query_end,
                             'dark_files_found': num_dark_files,
                             'flat_files_found': num_flat_files,
                             'run_bpix_from_darks': run_darks,
                             'run_bpix_from_flats': run_flats,
                             'run_monitor': run_flats or run_darks,
                             'entry_date': datetime.datetime.now()}
                self.query_table.__table__.insert().execute(new_entry)
                logging.info('\tUpdated the query history table')

        logging.info('Bad Pixel Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = BadPixels()
    monitor.run()

    update_monitor_table(module, start_time, log_file)
