#! /usr/bin/env python

"""This module runs the Cosmic Ray Monitor.

This module contains code for the cosmic ray monitor, which currently
checks the number and magnitude of jumps in all observations performed
using a subset of apertures for each instrument. The code first checks
MAST for any new observations that have not yet been run through the monitor. It
then copies those files to a working directory, where they are run
through the pipeline, and for which the output is stored in a new
directory for each observation. Each observation is then analyzed for
jumps due to cosmic rays, of which the number and magnitude are
recorded. This information is then inserted into the stats database
table.

Authors
-------

    - Mike Engesser
    - Matt Bourque
    - Bryan Hilbert

Use
---

    This module can be used from the command line as such:

    ::
        python cosmic_ray_monitor.py
"""

# Native Imports
from collections import defaultdict
import datetime
from glob import glob
import logging
import numpy as np
import os
import re
import shutil

# Third-Party Imports
from astropy.io import fits
from astropy.time import Time
from jwst.datamodels import dqflags
import numpy as np
from pysiaf import Siaf
from sqlalchemy import func
from sqlalchemy.exc import StatementError, DataError, DatabaseError, InvalidRequestError, OperationalError
from sqlalchemy.sql.expression import and_

# Local imports
from jwql.database.database_interface import MIRICosmicRayQueryHistory
from jwql.database.database_interface import MIRICosmicRayStats
from jwql.database.database_interface import NIRCamCosmicRayQueryHistory
from jwql.database.database_interface import NIRCamCosmicRayStats
from jwql.database.database_interface import NIRISSCosmicRayQueryHistory
from jwql.database.database_interface import NIRISSCosmicRayStats
from jwql.database.database_interface import NIRSpecCosmicRayQueryHistory
from jwql.database.database_interface import NIRSpecCosmicRayStats
from jwql.database.database_interface import FGSCosmicRayQueryHistory
from jwql.database.database_interface import FGSCosmicRayStats
from jwql.database.database_interface import session
from jwql.jwql_monitors import monitor_mast
from jwql.shared_tasks.shared_tasks import only_one, run_pipeline, run_parallel_pipeline
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_DATAPRODUCTS
from jwql.utils.logging_functions import configure_logging
from jwql.utils.logging_functions import log_info
from jwql.utils.logging_functions import log_fail
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path, grouper


class CosmicRay:
    """Class for executing the cosmic ray monitor.

    This class will search for new (since the previous instance of the
    class) data in the file system. It will loop over
    instrument/aperture combinations and find the number of new files
    available. It will copy the files over to a working directory and
    run the monitor. This will count the number and magnitude of all
    cosmic rays in each new exposure. Results are all saved to
    database tables.

    Attributes
    ----------
    output_dir : str
        Path into which outputs will be placed

    data_dir : str
        Path into which new files will be copied to be worked on

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
        Table containing the history of cosmic ray monitor queries to MAST
        for each instrument/aperture combination

    stats_table : sqlalchemy table
        Table containing cosmic ray analysis results. Number and
        magnitude of cosmic rays, etc.

    Raises
    ------
    ValueError
        If encountering a file not following the JWST file naming
        convention

    ValueError
        If the most recent query search returns more than one entry
    """

    def __init__(self):
        """Initialize an instance of the ``Cosmic_Ray`` class."""

    def filter_bases(self, file_list):
        """Filter a list of input files. Strip off everything after the last
        underscore (e.g. "i2d.fits"), and keep only once instance of the
        remaining basename.

        Parameters
        ----------
        file_list : list
            List of fits files

        Returns
        -------
        good_files : list
            Filtered list of uncal file names
        """
        good_files = []
        for filename in file_list:
            # Search the first part of the filename for letters. (e.g. jw01059007003
            # without the jw). If there aren't any, then it's not a stage 3 product and
            # we can continue.
            substr = filename[2:13]
            letters = re.findall("\D", substr)  # noqa: W605
            if len(letters) == 0:
                rev = filename[::-1]
                under = rev.find('_')
                base = rev[under + 1:][::-1]
                uncal_file = f'{base}_uncal.fits'
                if uncal_file not in good_files:
                    good_files.append(uncal_file)
        return good_files

    def identify_tables(self):
        """Determine which database tables to use for a run of the
        cosmic ray monitor.

        Uses the instrument variable to get the mixed-case instrument
        name, and uses that name to find the query and stats tables
        for that instrument.
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}CosmicRayQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}CosmicRayStats'.format(mixed_case_name))

    def get_cr_mags(self, jump_locs, jump_locs_pre, rateints, jump_data, jump_head):
        """Gets the magnitude of each cosmic ray.

        Computes a list of magnitudes using the coordinate of the
        detected jump compared to the magnitude of the same pixel in
        the group prior to the jump.

        Parameters:
        ----------

        jump_locs: list
            List of coordinates to a pixel marked with a jump.

        jump_locs_pre: list
            List of matching coordinates one group before jump_locs.

        rateints: ndarray
            Array in DN/s.

        jump_data: ndarray
            Ndarray containing image data cube

        jump_head: FITS Header
            FITS header unit containing information about the jump data

        Returns:
        -------

        mags: numpy.array
            A histogram of cosmic ray magnitudes, from -65536 to 65536, with the number of
            cosmic rays of each magnitude.

        """
        mag_bins = np.arange(65536 * 2 + 1, dtype=int) - 65536
        mags = np.zeros_like(mag_bins, dtype=int)
        outliers = []
        num_outliers = 0
        total = 0

        for coord, coord_gb in zip(jump_locs, jump_locs_pre):
            total += 1
            mag = self.magnitude(coord, coord_gb, rateints, jump_data, jump_head)
            if abs(mag) > 65535:
                num_outliers += 1
                outliers.append(int(mag))
            else:
                mags[mag_bins[mag]] += 1

        logging.info("{} of {} cosmic rays are beyond bin boundaries".format(num_outliers, total))
        return [int(m) for m in mags], outliers

    def file_exists_in_database(self, filename):
        """Checks if an entry for filename exists in the cosmic ray stats
        database.

        Parameters
        ----------
        filename : str
            The full path to the uncal filename.

        Returns
        -------
        file_exists : bool
            ``True`` if filename exists in the bias stats database.
        """

        query = session.query(self.stats_table)
        results = query.filter(self.stats_table.source_file == filename).all()

        if len(results) != 0:
            file_exists = True
        else:
            file_exists = False

        session.close()
        return file_exists

    def files_in_database(self):
        """Checks all entries in the cosmic ray stats database.

        Returns
        -------
        files : list
            All files in the stats database
        """

        query = session.query(self.stats_table.source_file)
        results = query.all()
        session.close()
        return results

    def get_cr_rate(self, cr_num, header):
        """Given a number of CR hits, as well as the header from an observation file,
        calculate the rate of CR hits per pixel

        Parameters
        ----------
        cr_num : int
            Number of jump flags identified in a particular exposure

        header : astropy.io.fits.header.Header
            Header of the exposure file

        Returns
        -------
        rate : float
            Rate of CR flags per pixel per second
        """

        # Note that the pipeline's jump step is unable to find CR hits in
        # the initial group. So let's subtract one group time from the effective
        # exposure time in order to get the exposure time that was acutally
        # searched
        efftime = header['EFFEXPTM']
        group_time = header['TGROUP']
        efftime -= group_time

        num_pix = (header['SUBSIZE1'] * header['SUBSIZE2'])

        rate = cr_num / num_pix / efftime
        return rate

    def get_jump_data(self, jump_filename):
        """Opens and reads a given .FITS file containing cosmic rays.

        Parameters:
        ----------
        jump_filename: str
            Path to file.

        Returns:
        -------
        head: FITS header
            Header containing file information

        data: NoneType
            FITS data

        dq: ndarray
            Data Quality array containing jump flags.

        """
        try:
            with fits.open(jump_filename) as hdu:
                head = hdu[0].header
                data = hdu[1].data
                dq = hdu[3].data
        except (IndexError, FileNotFoundError):
            logging.warning(f'Could not open jump file: {jump_file} Skipping')
            head = data = dq = None

        return head, data, dq

    def get_jump_locs(self, dq):
        """Uses the data quality array to find the location of all
        jumps in the data.

        Parameters:
        ----------
        dq: ndarray
            Data Quality array containing jump flags.

        Returns:
        -------
        jump_locs: list
            List of coordinates to a pixel marked with a jump.
        """

        temp = np.where(dq & dqflags.pixel["JUMP_DET"] > 0)

        jump_locs = []

        if len(temp) == 4:
            for i in range(len(temp[0])):
                jump_locs.append((temp[0][i], temp[1][i], temp[2][i], temp[3][i]))
        elif len(temp) == 3:
            for i in range(len(temp[0])):
                jump_locs.append((temp[0][i], temp[1][i], temp[2][i]))
        elif len(temp) == 0:
            # This is the (unlikely) case where the data contain no flagged CRs
            pass
        else:
            logging.error(f'dq has {len(temp)} dimensions. We expect it to have 3 or 4.')

        return jump_locs

    def get_rate_data(self, rate_filename):
        """Opens and reads a given .FITS file.

        Parameters:
        ----------
        rate_filename: str
            Path to file.

        Returns:
        -------
        data: NoneType
            FITS data
        """
        try:
            data = fits.getdata(rate_filename)
        except FileNotFoundError:
            logging.warning(f'Could not open rate file: {rate_file} Skipping')
            data = None

        return data

    def group_before(self, jump_locs):
        """Creates a list of coordinates one group before given jump
        coordinates.

        Parameters:
        ----------
        jump_locs: list
            List of coordinates to a pixel marked with a jump.

        Returns:
        -------
        jump_locs_pre: list
            List of matching coordinates one group before jump_locs.
        """

        jump_locs_pre = []

        if len(jump_locs) == 0:
            logging.error("No entries in jump_locs!")
            return []

        if len(jump_locs[0]) == 4:
            for coord in jump_locs:
                jump_locs_pre.append((coord[0], coord[1] - 1, coord[2], coord[3]))
        elif len(jump_locs[0]) == 3:
            for coord in jump_locs:
                jump_locs_pre.append((coord[0] - 1, coord[1], coord[2]))
        else:
            logging.error(f'jump_locs has {len(jump_locs[0])} dimensions. Expecting 3 or 4.')

        return jump_locs_pre

    def magnitude(self, coord, coord_gb, rateints, data, head):
        """Calculates the magnitude of a list of jumps given their
        coordinates in an array of pixels.

        Parameters:
        ----------
        coord: tuple
            Coordinate of jump.

        coord_gb: tuple
            Coordinate of jump pixel one group before.

        head: FITS header
            Header containing file information.

        rateints: ndarray
            Array in DN/s.

        Returns:
        -------
        cr_mag: float
            the magnitude of the cosmic ray
        """

        grouptime = head['TGROUP']

        if self.nints == 1:
            rate = rateints[coord[-2]][coord[-1]]
            cr_mag = data[0][coord[0]][coord[1]][coord[2]] \
                - data[0][coord_gb[0]][coord_gb[1]][coord_gb[2]] \
                - rate * grouptime

        else:
            rate = rateints[coord[0]][coord[-2]][coord[-1]]
            cr_mag = data[coord] - data[coord_gb] - rate * grouptime

        return int(np.round(np.nan_to_num(cr_mag)))

    def most_recent_search(self):
        """Adapted from Dark Monitor (Bryan Hilbert)

        Query the query history database and return the information
        on the most recent query for the given ``aperture_name`` where
        the cosmic ray monitor was executed.

        Returns:
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST
            query where the cosmic ray monitor was run.
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
                self.query_table.run_monitor == True  # noqa: E712
            )
        ).all()

        query_count = len(query)
        if query_count == 0:
            query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'
                          .format(self.aperture, query_result)))
        else:
            query_result = query[0].end_time_mjd

        return query_result

    def possible_apers(self, inst):
        """Return possible apertures to check for cosmic rays

        Parameters:
        ----------
        inst: str
            The name of the instrument of interest

        Returns:
        -------
        apers: list
            A list of possible apertures to check for the given
            instrument
        """
        if inst.lower() == 'nircam':
            apers = ['NRCA1_FULL',
                     'NRCA2_FULL',
                     'NRCA3_FULL',
                     'NRCA4_FULL',
                     'NRCA5_FULL',

                     'NRCB1_FULL',
                     'NRCB2_FULL',
                     'NRCB3_FULL',
                     'NRCB4_FULL',
                     'NRCB5_FULL']

        if inst.lower() == 'miri':
            apers = ['MIRIM_FULL',
                     'MIRIM_ILLUM',
                     'MIRIM_BRIGHTSKY',
                     'MIRIM_SUB256',
                     'MIRIM_SUB128',
                     'MIRIM_SUB64',
                     'MIRIM_CORON1065',
                     'MIRIM_CORON1140',
                     'MIRIM_CORON1550',
                     'MIRIM_CORONLYOT',
                     'MIRIM_SLITLESSPRISM',
                     'MIRIFU_CHANNEL1A',
                     'MIRIFU_CHANNEL1B'
                     'MIRIFU_CHANNEL1C',
                     'MIRIFU_CHANNEL2A',
                     'MIRIFU_CHANNEL2B'
                     'MIRIFU_CHANNEL2C',
                     'MIRIFU_CHANNEL3A',
                     'MIRIFU_CHANNEL3B'
                     'MIRIFU_CHANNEL3C',
                     'MIRIFU_CHANNEL4A',
                     'MIRIFU_CHANNEL4B',
                     'MIRIFU_CHANNEL4C']

        if inst.lower() == 'niriss':
            apers = ['NIS_CEN']

        if inst.lower() == 'nirspec':
            apers = ['NRS_FULL_MSA']

        if inst.lower() == 'fgs':
            apers = ['FGS1_FULL', 'FGS2_FULL']

        return apers

    def process(self, file_list):
        """The main method for processing files. See module docstrings
        for further details.

        Parameters
        ----------
        file_list : list
            List of filenames (including full paths) to the cosmic ray
            files
        """
        for file_chunk in grouper(file_list, 100):
        
            input_files = []
            in_ext = "uncal"
            out_exts = defaultdict(lambda: ['jump', '0_ramp_fit'])
            instrument = self.instrument
            existing_files = {}
            no_coord_files = []

            for file_name in file_chunk:

                # Dont process files that already exist in the bias stats database
                logging.info("Checking for {} in database".format(os.path.basename(file_name)))
                file_exists = self.file_exists_in_database(os.path.basename(file_name))
                if file_exists:
                    logging.info('\t{} already exists in the bias database table.'.format(file_name))
                    continue

                dir_name = '_'.join(file_name.split('_')[:4])  # file_name[51:76]

                self.obs_dir = os.path.join(self.data_dir, dir_name)
                ensure_dir_exists(self.obs_dir)
                logging.info(f'Setting obs_dir to {self.obs_dir}')

                if 'uncal' in file_name:
                    head = fits.getheader(file_name)
                    self.nints = head['NINTS']

                    copied, failed_to_copy = copy_files([file_name], self.obs_dir)
                    # If the file cannot be copied to the working directory, skip it
                    if len(failed_to_copy) > 0:
                        continue

                    # Next we run the pipeline on the files to get the proper outputs
                    uncal_file = os.path.join(self.obs_dir, os.path.basename(file_name))
                    jump_file = uncal_file.replace("uncal", "jump")
                    rate_file = uncal_file.replace("uncal", "0_ramp_fit")
                    if self.nints > 1:
                        rate_file = rate_file.replace("0_ramp_fit", "1_ramp_fit")

                    if (not os.path.isfile(jump_file)) or (not os.path.isfile(rate_file)):
                        logging.info("Adding {} to calibration tasks".format(uncal_file))

                        short_name = os.path.basename(uncal_file).replace('_uncal.fits', '')

                        input_files.append(uncal_file)
                        if self.nints > 1:
                            out_exts[short_name] = ['jump', '1_ramp_fit']
                    else:
                        logging.info("Calibrated files for {} already exist".format(uncal_file))
                        existing_files[uncal_file] = [jump_file, rate_file]

            output_files = run_parallel_pipeline(input_files, in_ext, out_exts, instrument, jump_pipe=True)
            for file_name in existing_files:
                if file_name not in input_files:
                    input_files.append(file_name)
                    output_files[file_name] = existing_files[file_name]

            for file_name in file_chunk:

                head = fits.getheader(file_name)
                self.nints = head['NINTS']

                dir_name = '_'.join(os.path.basename(file_name).split('_')[:2])  # file_name[51:76]
                self.obs_dir = os.path.join(self.data_dir, dir_name)

                obs_files = output_files[file_name]

                # Next we analyze the cosmic rays in the new data
                for output_file in obs_files:
                    logging.info("Checking output file {}".format(output_file))

                    if 'jump' in output_file:
                        logging.debug("Adding jump file {}".format(os.path.basename(output_file)))
                        jump_file = os.path.join(self.obs_dir, os.path.basename(output_file))

                    if self.nints == 1:
                        logging.debug("Looking for single integration rate file")
                        if '0_ramp_fit' in output_file:
                            logging.debug("Adding rate file {}".format(os.path.basename(output_file)))
                            rate_file = os.path.join(self.obs_dir, os.path.basename(output_file))

                    elif self.nints > 1:
                        logging.debug("Looking for multi-integration rate file")
                        if '1_ramp_fit' in output_file:
                            logging.debug("Adding rate file {}".format(os.path.basename(output_file)))
                            rate_file = os.path.join(self.obs_dir, os.path.basename(output_file))

                logging.info(f'\tUsing {jump_file} and {rate_file} to monitor CRs.')

                jump_head, jump_data, jump_dq = self.get_jump_data(jump_file)
                rate_data = self.get_rate_data(rate_file)
                if jump_head is None or rate_data is None:
                    continue

                jump_locs = self.get_jump_locs(jump_dq)
                if len(jump_locs) == 0:
                    no_coord_files.append(os.path.basename(file_name))
                jump_locs_pre = self.group_before(jump_locs)
                cosmic_ray_num = len(jump_locs)

                logging.info(f'\tFound {cosmic_ray_num} CR-flags.')

                # Translate CR count into a CR rate per pixel, so that all exposures
                # can go on one plot regardless of exposure time and aperture size
                cr_rate = self.get_cr_rate(cosmic_ray_num, jump_head)
                logging.info(f'\tNormalizing by time and area, this is {cr_rate} jumps/sec/pixel.')

                # Get observation time info
                obs_start_time = jump_head['EXPSTART']
                obs_end_time = jump_head['EXPEND']
                start_time = Time(obs_start_time, format='mjd', scale='utc').isot.replace('T', ' ')
                end_time = Time(obs_end_time, format='mjd', scale='utc').isot.replace('T', ' ')

                cosmic_ray_mags, outlier_mags = self.get_cr_mags(jump_locs, jump_locs_pre, rate_data, jump_data, jump_head)

                # Insert new data into database
                try:
                    logging.info("Inserting {} in database".format(os.path.basename(file_name)))
                    cosmic_ray_db_entry = {'entry_date': datetime.datetime.now(),
                                           'aperture': self.aperture,
                                           'source_file': os.path.basename(file_name),
                                           'obs_start_time': start_time,
                                           'obs_end_time': end_time,
                                           'jump_count': cosmic_ray_num,
                                           'jump_rate': cr_rate,
                                           'magnitude': cosmic_ray_mags,
                                           'outliers': outlier_mags
                                           }
                    self.stats_table.__table__.insert().execute(cosmic_ray_db_entry)

                    logging.info("Successfully inserted into database. \n")

                    # Delete fits files in order to save disk space
                    logging.info("Removing pipeline products in order to save disk space. \n")
                    try:
                        for file in [file_name, jump_file, rate_file]:
                            if os.path.isfile(file):
                                os.remove(file)
                        if os.path.exists(self.obs_dir):
                            os.rmdir(self.obs_dir)
                    except OSError as e:
                        logging.error(f"Unable to delete {self.obs_dir}")
                        logging.error(e)
                except (StatementError, DataError, DatabaseError, InvalidRequestError, OperationalError) as e:
                    logging.error("Could not insert entry into database. \n")
                    logging.error(e)

                if len(no_coord_files) > 0:
                    logging.error("{} files had no jump co-ordinates".format(len(no_coord_files)))
                    for file_name in no_coord_files:
                        logging.error("\t{} had no jump co-ordinates".format(file_name))


    def pull_filenames(self, file_info):
        """Extract filenames from the list of file information returned from
        query_mast.

        Parameters
        ----------
        file_info : dict
            Dictionary of file information returned by ``query_mast``

        Returns
        -------
        files : list
            List of filenames (without paths) extracted from ``file_info``
        """
        files = [element['filename'] for element in file_info['data']]
        return files

    @log_fail
    @log_info
    @only_one(key='cosmic_ray_monitor')
    def run(self):
        """The main method. See module docstrings for additional info

        Queries MAST for new MIRI data and copies it to a working
        directory where it is run through the JWST pipeline. The output
        of the 'jump' and 'rate' steps is used to determine the number
        and magnitudes of cosmic rays which is then saved to the
        database.
        """

        logging.info('Begin logging for cosmic_ray_monitor')

        self.query_end = Time.now().mjd

        for instrument in JWST_INSTRUMENT_NAMES:
            self.instrument = instrument

            # Identify which tables to use
            self.identify_tables()

            # Get a list of possible apertures
            possible_apertures = self.possible_apers(instrument)

            for aperture in possible_apertures:

                logging.info('')
                logging.info('Working on aperture {} in {}'.format(aperture, instrument))

                self.aperture = aperture

                # We start by querying MAST for new data
                self.query_start = self.most_recent_search()

                logging.info('\tMost recent query: {}'.format(self.query_start))
                logging.info(f'\tQuerying MAST from {self.query_start} to {self.query_end}')
                new_entries = self.query_mast()
                logging.info(f'\tNew MAST query returned dictionary with {len(new_entries["data"])} files.')
                new_entries = self.pull_filenames(new_entries)

                # Filter new entries so we omit stage 3 results and keep only base names
                new_entries = self.filter_bases(new_entries)
                logging.info(f'\tAfter filtering to keep only uncal files, we are left with {len(new_entries)} files')

                for fname in new_entries:
                    logging.info(f'{fname}')

                new_filenames = []
                for file_entry in new_entries:
                    try:
                        new_filenames.append(filesystem_path(file_entry))
                    except FileNotFoundError:
                        logging.info('\t{} not found in target directory'.format(file_entry))
                    except ValueError:
                        logging.info(
                            '\tProvided file {} does not follow JWST naming conventions.'.format(file_entry))

                # Next we copy new files to the working directory
                output_dir = os.path.join(get_config()['outputs'], 'cosmic_ray_monitor')

                self.data_dir = os.path.join(output_dir, 'data')
                ensure_dir_exists(self.data_dir)

                self.process(cosmic_ray_files)

                monitor_run = True

                new_entry = {'instrument': self.instrument,
                             'aperture': self.aperture,
                             'start_time_mjd': self.query_start,
                             'end_time_mjd': self.query_end,
                             'files_found': len(new_entries),
                             'run_monitor': monitor_run,
                             'entry_date': datetime.datetime.now()}
                self.query_table.__table__.insert().execute(new_entry)
                logging.info('\tUpdated the query history table')

    def query_mast(self):
        """Use astroquery to search MAST for cosmic ray data

        Parameters:
        ----------
        start_date : float
            Starting date for the search in MJD
        end_date : float
            Ending date for the search in MJD

        Returns
        -------
        result : list
            List of dictionaries containing the query results
        """

        data_product = JWST_DATAPRODUCTS
        parameters = {"date_obs_mjd": {"min": self.query_start, "max": self.query_end}, "apername": self.aperture}

        result = monitor_mast.instrument_inventory(self.instrument, data_product,
                                                   add_filters=parameters,
                                                   return_data=True)

        return result


if __name__ == '__main__':
    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    # Call the main function
    monitor = CosmicRay()
    monitor.run()
