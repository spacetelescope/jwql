#! /usr/bin/env python

"""This module runs the Cosmic Ray Monitor.

This module contains code for the cosmic ray monitor, which currently
checks the number and magnitude of jumps in all observations performed
with MIRI and NIRCam. The code first checks MAST for any new MIRI or
NIRCam observations that have not yet been run through the monitor. It
then copies those files to a working directory, where they are run
through the pipeline, and for which the output is stored in a new
directory for each observation. Each observation is then analyzed for
jumps due to cosmic rays, of which the number and magnitude are
recorded. This information is then inserted into the stats database
table.

Authors
-------

    - Mike Engesser

Use
---

    This module can be used from the command line as such:

    ::
        python cosmic_ray_monitor.py
"""

# Native Imports
import datetime
import logging
import os
import shutil

# Third-Party Imports
from astropy.io import fits
from astropy.time import Time
import julian
from jwst.datamodels import dqflags
import numpy as np
from pysiaf import Siaf
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

# Local imports
from jwql.database.database_interface import MIRICosmicRayQueryHistory
from jwql.database.database_interface import MIRICosmicRayStats
from jwql.database.database_interface import NIRCamCosmicRayQueryHistory
from jwql.database.database_interface import NIRCamCosmicRayStats
from jwql.database.database_interface import session
from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_DATAPRODUCTS
from jwql.utils.logging_functions import configure_logging
from jwql.utils.logging_functions import log_info
from jwql.utils.logging_functions import log_fail
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path


class CosmicRay:
    """Class for executing the cosmic ray monitor.

    This class will search for new (since the previous instance of the
    class) MIRI and NIRCam data in the file system. It will loop over
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
            letters = re.findall("\D", substr)
            if len(letters) == 0:
                rev = filename[::-1]
                under = rev.find('_')
                base = rev[under + 1:][::-1]
                if base not in good_files:
                    good_files.append(f'{base}_uncal.fits')
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

        mags: list
            A list of cosmic ray magnitudes corresponding to each jump.

        """

        mags = []
        for coord, coord_gb in zip(jump_locs, jump_locs_pre):
            mags.append(self.magnitude(coord, coord_gb, rateints, jump_data, jump_head))

        return mags


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

        hdu = fits.open(jump_filename)

        head = hdu[0].header
        data = hdu[1].data

        dq = hdu[3].data

        hdu.close()

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

        if self.nints > 1:
            for i in range(len(temp[0])):
                jump_locs.append((temp[0][i], temp[1][i], temp[2][i], temp[3][i]))
        else:
            for i in range(len(temp[0])):
                jump_locs.append((temp[0][i], temp[1][i], temp[2][i]))

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

        data = fits.getdata(rate_filename)

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

        if self.nints > 1:
            for coord in jump_locs:
                jump_locs_pre.append((coord[0], coord[1] - 1, coord[2], coord[3]))
        else:
            for coord in jump_locs:
                jump_locs_pre.append((coord[0] - 1, coord[1], coord[2]))

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

        return cr_mag


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
                self.query_table.run_monitor == True
            )
        ).all()

        query_count = len(query)
        if query_count == 0:
            query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'
                          .format(self.aperture, query_result)))
        #elif query_count > 1:
         #   raise ValueError('More than one "most recent" query?')
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

        for file_name in file_list:
            if 'uncal' in file_name:
                dir_name = '_'.join(file_name.split('_')[:4])  # file_name[51:76]

                self.obs_dir = os.path.join(self.data_dir, dir_name)
                ensure_dir_exists(self.obs_dir)

                head = fits.getheader(file_name)
                self.nints = head['NINTS']

                try:
                    copy_files([file_name], self.obs_dir)
                except:
                    logging.info('Failed to copy {} to observation dir.'.format(file_name))
                    pass

                # Next we run the pipeline on the files to get the proper outputs
                uncal_file = os.path.join(self.obs_dir, os.path.basename(file_name))

                try:
                    pipeline_tools.calwebb_detector1_save_jump(uncal_file, self.obs_dir, ramp_fit=True, save_fitopt=False)
                except:
                    logging.info('Failed to complete pipeline steps on {}.'.format(uncal_file))
                    pass

                # Next we analyze the cosmic rays in the new data
                obs_files = os.listdir(self.obs_dir)
                for output_file in obs_files:

                    if 'jump' in output_file:
                        jump_file = os.path.join(self.obs_dir, output_file)

                    if self.nints == 1:
                        if '0_ramp_fit' in output_file:
                            rate_file = os.path.join(self.obs_dir, output_file)

                    elif self.nints > 1:
                        if '1_ramp_fit' in output_file:
                            rate_file = os.path.join(self.obs_dir, output_file)

                try:
                    jump_head, jump_data, jump_dq = self.get_jump_data(jump_file)
                except:
                    logging.info('Could not open jump file: {}'.format(jump_file))

                try:
                    rate_data = self.get_rate_data(rate_file)
                except:
                    logging.info('Could not open rate file: {}'.format(rate_file))

                jump_locs = self.get_jump_locs(jump_dq)
                jump_locs_pre = self.group_before(jump_locs)

                eff_time = jump_head['EFFEXPTM']

                # Get observation time info
                obs_start_time = jump_head['EXPSTART']
                obs_end_time = jump_head['EXPEND']
                start_time = julian.from_jd(obs_start_time, fmt='mjd')
                end_time = julian.from_jd(obs_end_time, fmt='mjd')

                cosmic_ray_num = len(jump_locs)
                cosmic_ray_mags = self.get_cr_mags(jump_locs, jump_locs_pre, rate_data, jump_data, jump_head)

                # Insert new data into database
                try:
                    cosmic_ray_db_entry = {'entry_date': datetime.datetime.now(),
                                           'aperture': self.aperture,
                                           'source_file': file_name,
                                           'obs_start_time': start_time,
                                           'obs_end_time': end_time,
                                           'jump_count': cosmic_ray_num,
                                           'magnitude': cosmic_ray_mags
                                           }
                    self.stats_table.__table__.insert().execute(cosmic_ray_db_entry)

                    logging.info("Successfully inserted into database. \n")
                except:
                    logging.info("Could not insert entry into database. \n")

                # Delete fits files in order to save disk space
                logging.info("Removing pipeline products in order to save disk space. \n")
                for obsfile in obs_files:
                    try:
                        os.remove(obsfile)
                    except OSError:
                        logging.info(f"Unable to delete {obsfile}")
                        pass
                os.rmdir(self.obs_dir)
                os.remove(file_name)

    @log_fail
    @log_info
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
            if instrument == 'miri' or instrument == 'nircam':
                self.instrument = instrument

                # Identify which tables to use
                self.identify_tables()

                # Get a list of possible apertures
                #possible_apertures = list(Siaf(instrument).apernames)
                possible_apertures = self.possible_apers(instrument)

                # Use this line instead to save time while testing
                #possible_apertures = ['MIRIM_FULL', 'NRCB4_FULL']

                for aperture in possible_apertures:

                    logging.info('')
                    logging.info('Working on aperture {} in {}'.format(aperture, instrument))

                    self.aperture = aperture

                    # We start by querying MAST for new data
                    self.query_start = self.most_recent_search()

                    logging.info('\tMost recent query: {}'.format(self.query_start))

                    new_entries = self.query_mast()

                    # Filter new entries so we omit stage 3 results and keep only base names
                    new_entries = self.filter_bases(new_entries)

                    # for testing purposes only
                    #new_filenames = get_config()['local_test_data']
                    new_filenames = []

                    for file_entry in new_entries:
                        try:
                            new_filenames.append(filesystem_path(file_entry['filename']))
                        except FileNotFoundError:
                            logging.info('\t{} not found in target directory'.format(file_entry['filename']))
                        except ValueError:
                            logging.info(
                                '\tProvided file {} does not follow JWST naming conventions.'.format(file_entry['filename']))

                    # Next we copy new files to the working directory
                    output_dir = os.path.join(get_config()['outputs'], 'cosmic_ray_monitor')

                    #self.data_dir = get_config()['local_test_dir']  # for testing purposes only

                    self.data_dir =  os.path.join(output_dir,'data')
                    ensure_dir_exists(self.data_dir)

                    cosmic_ray_files, not_copied = copy_files(new_filenames, self.data_dir)

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
