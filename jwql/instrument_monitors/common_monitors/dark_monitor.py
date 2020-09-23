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

    - Bryan Hilbert

Use
---

    This module can be used from the command line as such:

    ::

        python dark_monitor.py
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
from jwql.database.database_interface import NIRCamDarkQueryHistory, NIRCamDarkPixelStats, NIRCamDarkDarkCurrent
from jwql.database.database_interface import NIRISSDarkQueryHistory, NIRISSDarkPixelStats, NIRISSDarkDarkCurrent
from jwql.database.database_interface import MIRIDarkQueryHistory, MIRIDarkPixelStats, MIRIDarkDarkCurrent
from jwql.database.database_interface import NIRSpecDarkQueryHistory, NIRSpecDarkPixelStats, NIRSpecDarkDarkCurrent
from jwql.database.database_interface import FGSDarkQueryHistory, FGSDarkPixelStats, FGSDarkDarkCurrent
from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils import calculations, instrument_properties
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_DATAPRODUCTS
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.monitor_utils import initialize_instrument_monitor, update_monitor_table
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path

THRESHOLDS_FILE = os.path.join(os.path.split(__file__)[0], 'dark_monitor_file_thresholds.txt')


def mast_query_darks(instrument, aperture, start_date, end_date):
    """Use ``astroquery`` to search MAST for dark current data

    Parameters
    ----------
    instrument : str
        Instrument name (e.g. ``nircam``)

    aperture : str
        Detector aperture to search for (e.g. ``NRCA1_FULL``)

    start_date : float
        Starting date for the search in MJD

    end_date : float
        Ending date for the search in MJD

    Returns
    -------
    query_results : list
        List of dictionaries containing the query results
    """

    # Make sure instrument is correct case
    if instrument.lower() == 'nircam':
        instrument = 'NIRCam'
        dark_template = ['NRC_DARK']
    elif instrument.lower() == 'niriss':
        instrument = 'NIRISS'
        dark_template = ['NIS_DARK']
    elif instrument.lower() == 'nirspec':
        instrument = 'NIRSpec'
        dark_template = ['NRS_DARK']
    elif instrument.lower() == 'fgs':
        instrument = 'FGS'
        dark_template = ['FGS_DARK']
    elif instrument.lower() == 'miri':
        instrument = 'MIRI'
        dark_template = ['MIR_DARKALL', 'MIR_DARKIMG', 'MIR_DARKMRS']

    # monitor_mast.instrument_inventory does not allow list inputs to
    # the added_filters input (or at least if you do provide a list, then
    # it becomes a nested list when it sends the query to MAST. The
    # nested list is subsequently ignored by MAST.)
    # So query once for each dark template, and combine outputs into a
    # single list.
    query_results = []
    for template_name in dark_template:

        # Create dictionary of parameters to add
        parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                      "apername": aperture, "exp_type": template_name}

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                  add_filters=parameters, return_data=True, caom=False)
        if 'data' in query.keys():
            if len(query['data']) > 0:
                query_results.extend(query['data'])

    return query_results


class Dark():
    """Class for executing the dark current monitor.

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
        Table containing lists of hot/dead/noisy pixels found for each
        instrument/detector

    stats_table : sqlalchemy table
        Table containing dark current analysis results. Mean/stdev
        values, histogram information, Gaussian fitting results, etc.

    Raises
    ------
    ValueError
        If encountering an unrecognized bad pixel type

    ValueError
        If the most recent query search returns more than one entry
    """

    def __init__(self):
        """Initialize an instance of the ``Dark`` class."""

    def add_bad_pix(self, coordinates, pixel_type, files, mean_filename, baseline_filename,
                    observation_start_time, observation_mid_time, observation_end_time):
        """Add a set of bad pixels to the bad pixel database table

        Parameters
        ----------
        coordinates : tuple
            Tuple of two lists, containing x,y coordinates of bad
            pixels (Output of ``np.where`` call)

        pixel_type : str
            Type of bad pixel. Options are ``dead``, ``hot``, and
            ``noisy``

        files : list
            List of fits files which were used to identify the bad
            pixels

        mean_filename : str
            Name of fits file containing the mean dark rate image used
            to find these bad pixels

        baseline_filename : str
            Name of fits file containing the baseline dark rate image
            used to find these bad pixels

        observation_start_time : datetime.datetime
            Observation time of the earliest file in ``files``

        observation_mid_time : datetime.datetime
            Average of the observation times in ``files``

        observation_end_time : datetime.datetime
            Observation time of the latest file in ``files``
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
                 'mean_dark_image_file': os.path.basename(mean_filename),
                 'baseline_file': os.path.basename(baseline_filename),
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
            self.sample_time = header['TSAMPLE']
            self.frame_time = header['TFRAME']
            self.read_pattern = header['READPATT']

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

    def find_hot_dead_pixels(self, mean_image, comparison_image, hot_threshold=2., dead_threshold=0.1):
        """Create the ratio of the slope image to a baseline slope
        image. Pixels in the ratio image with values above
        ``hot_threshold`` will be marked as hot, and those with ratio
        values less than ``dead_threshold`` will be marked as dead.

        Parameters
        ----------
        mean_image : numpy.ndarray
            2D array containing the slope image from the new data

        comparison_image : numpy.ndarray
            2D array containing the baseline slope image to compare
            against the new slope image.

        hot_threshold : float
            ``(mean_image / comparison_image)`` ratio value above which
            a pixel is considered hot.

        dead_threshold : float
            ``(mean_image / comparison_image)`` ratio value below which
            a pixel is considered dead.

        Returns
        -------
        hotpix : tuple
            Tuple (of lists) containing x,y coordinates of newly hot
            pixels

        deadpix : tuple
            Tuple (of lists) containing x,y coordinates of newly dead
            pixels
        """

        # Avoid divide by zeros
        zeros = comparison_image == 0.
        comparison_image[zeros] = 1.
        mean_image[zeros] += 1.

        ratio = mean_image / comparison_image
        hotpix = np.where(ratio > hot_threshold)
        deadpix = np.where(ratio < dead_threshold)

        return hotpix, deadpix

    def get_baseline_filename(self):
        """Query the database and return the filename of the baseline
        (comparison) mean dark slope image to use when searching for
        new hot/dead/noisy pixels. For this we assume that the most
        recent baseline file for the given detector is the one to use.

        Returns
        -------
        filename : str
            Name of fits file containing the baseline image
        """

        subq = session.query(self.pixel_table.detector,
                             func.max(self.pixel_table.entry_date).label('maxdate')
                             ).group_by(self.pixel_table.detector).subquery('t2')

        query = session.query(self.pixel_table).join(
            subq,
            and_(
                self.pixel_table.detector == self.detector,
                self.pixel_table.entry_date == subq.c.maxdate
            )
        )

        count = query.count()
        if not count:
            filename = None
        else:
            filename = query.all()[0].baseline_file
            # Specify the full path
            filename = os.path.join(self.output_dir, 'mean_slope_images', filename)
            logging.info('Baseline filename: {}'.format(filename))

        return filename

    def identify_tables(self):
        """Determine which database tables to use for a run of the dark
        monitor
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}DarkQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
        self.stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))

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

    def noise_check(self, new_noise_image, baseline_noise_image, threshold=1.5):
        """Create the ratio of the stdev (noise) image to a baseline
        noise image. Pixels in the ratio image with values above
        ``threshold`` will be marked as newly noisy.

        Parameters
        ----------
        new_noise_image : numpy.ndarray
            2D array containing the noise image from the new data

        baseline_noise_image : numpy.ndarray
            2D array containing the baseline noise image to compare
            against the new noise image.

        threshold : float
            ``(new_noise_image / baseline_noise_image)`` ratio value
            above which a pixel is considered newly noisey.

        Returns
        -------
        noisy : tuple
            Tuple (of lists) of x,y coordinates of newly noisy pixels
        """

        # Avoid divide by zeros
        zeros = baseline_noise_image == 0.
        baseline_noise_image[zeros] = 1.
        new_noise_image[zeros] += 1.

        ratio = new_noise_image / baseline_noise_image
        noisy = np.where(ratio > threshold)

        return noisy

    def process(self, file_list):
        """The main method for processing darks.  See module docstrings
        for further details.

        Parameters
        ----------
        file_list : list
            List of filenames (including full paths) to the dark current
            files
        """

        # Basic metadata that will be needed later
        self.get_metadata(file_list[0])

        # Determine which pipeline steps need to be executed
        required_steps = pipeline_tools.get_pipeline_steps(self.instrument)
        logging.info('\tRequired calwebb1_detector pipeline steps to have the data in the '
                     'correct format:')
        for item in required_steps:
            logging.info('\t\t{}: {}'.format(item, required_steps[item]))

        # Modify the list of pipeline steps to skip those not needed for the
        # preparation of dark current data
        required_steps['dark_current'] = False
        required_steps['persistence'] = False

        # NIRSpec IR^2 readout pattern NRSIRS2 is the only one with
        # nframes not a power of 2
        if self.read_pattern not in pipeline_tools.GROUPSCALE_READOUT_PATTERNS:
            required_steps['group_scale'] = False

        # Run pipeline steps on files, generating slope files
        slope_files = []
        for filename in file_list:

            completed_steps = pipeline_tools.completed_pipeline_steps(filename)
            steps_to_run = pipeline_tools.steps_to_run(required_steps, completed_steps)

            logging.info('\tWorking on file: {}'.format(filename))
            logging.info('\tPipeline steps that remain to be run:')
            for item in steps_to_run:
                logging.info('\t\t{}: {}'.format(item, steps_to_run[item]))

            # Run any remaining required pipeline steps
            if any(steps_to_run.values()) is False:
                slope_files.append(filename)
            else:
                processed_file = filename.replace('.fits', '_{}.fits'.format('rate'))

                # If the slope file already exists, skip the pipeline call
                if not os.path.isfile(processed_file):
                    logging.info('\tRunning pipeline on {}'.format(filename))
                    processed_file = pipeline_tools.run_calwebb_detector1_steps(os.path.abspath(filename), steps_to_run)
                    logging.info('\tPipeline complete. Output: {}'.format(processed_file))

                else:
                    logging.info('\tSlope file {} already exists. Skipping call to pipeline.'
                                 .format(processed_file))
                    pass

                slope_files.append(processed_file)

                # Delete the original dark ramp file to save disk space
                os.remove(filename)

        obs_times = []
        logging.info('\tSlope images to use in the dark monitor for {}, {}:'.format(self.instrument, self.aperture))
        for item in slope_files:
            logging.info('\t\t{}'.format(item))
            # Get the observation time for each file
            obstime = instrument_properties.get_obstime(item)
            obs_times.append(obstime)

        # Find the earliest and latest observation time, and calculate
        # the mid-time.
        min_time = np.min(obs_times)
        max_time = np.max(obs_times)
        mid_time = instrument_properties.mean_time(obs_times)

        # Read in all slope images and place into a list
        slope_image_stack, slope_exptimes = pipeline_tools.image_stack(slope_files)

        # Calculate a mean slope image from the inputs
        slope_image, stdev_image = calculations.mean_image(slope_image_stack, sigma_threshold=3)
        mean_slope_file = self.save_mean_slope_image(slope_image, stdev_image, slope_files)
        logging.info('\tSigma-clipped mean of the slope images saved to: {}'.format(mean_slope_file))

        # ----- Search for new hot/dead/noisy pixels -----
        # Read in baseline mean slope image and stdev image
        # The baseline image is used to look for hot/dead/noisy pixels,
        # but not for comparing mean dark rates. Therefore, updates to
        # the baseline can be minimal.

        # Limit checks for hot/dead/noisy pixels to full frame data since
        # subarray data have much shorter exposure times and therefore lower
        # signal-to-noise
        aperture_type = Siaf(self.instrument)[self.aperture].AperType
        if aperture_type == 'FULLSCA':
            baseline_file = self.get_baseline_filename()
            if baseline_file is None:
                logging.warning(('\tNo baseline dark current countrate image for {} {}. Setting the '
                                 'current mean slope image to be the new baseline.'.format(self.instrument, self.aperture)))
                baseline_file = mean_slope_file
                baseline_mean = deepcopy(slope_image)
                baseline_stdev = deepcopy(stdev_image)
            else:
                logging.info('\tBaseline file is {}'.format(baseline_file))
                baseline_mean, baseline_stdev = self.read_baseline_slope_image(baseline_file)

            # Check the hot/dead pixel population for changes
            new_hot_pix, new_dead_pix = self.find_hot_dead_pixels(slope_image, baseline_mean)

            # Shift the coordinates to be in full frame coordinate system
            new_hot_pix = self.shift_to_full_frame(new_hot_pix)
            new_dead_pix = self.shift_to_full_frame(new_dead_pix)

            # Exclude hot and dead pixels found previously
            new_hot_pix = self.exclude_existing_badpix(new_hot_pix, 'hot')
            new_dead_pix = self.exclude_existing_badpix(new_dead_pix, 'dead')

            # Add new hot and dead pixels to the database
            logging.info('\tFound {} new hot pixels'.format(len(new_hot_pix[0])))
            logging.info('\tFound {} new dead pixels'.format(len(new_dead_pix[0])))
            self.add_bad_pix(new_hot_pix, 'hot', file_list, mean_slope_file, baseline_file, min_time, mid_time, max_time)
            self.add_bad_pix(new_dead_pix, 'dead', file_list, mean_slope_file, baseline_file, min_time, mid_time, max_time)

            # Check for any pixels that are significantly more noisy than
            # in the baseline stdev image
            new_noisy_pixels = self.noise_check(stdev_image, baseline_stdev)

            # Shift coordinates to be in full_frame coordinate system
            new_noisy_pixels = self.shift_to_full_frame(new_noisy_pixels)

            # Exclude previously found noisy pixels
            new_noisy_pixels = self.exclude_existing_badpix(new_noisy_pixels, 'noisy')

            # Add new noisy pixels to the database
            logging.info('\tFound {} new noisy pixels'.format(len(new_noisy_pixels[0])))
            self.add_bad_pix(new_noisy_pixels, 'noisy', file_list, mean_slope_file, baseline_file, min_time, mid_time, max_time)

        # ----- Calculate image statistics -----

        # Find amplifier boundaries so per-amp statistics can be calculated
        number_of_amps, amp_bounds = instrument_properties.amplifier_info(slope_files[0])
        logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

        # Calculate mean and stdev values, and fit a Gaussian to the
        # histogram of the pixels in each amp
        (amp_mean, amp_stdev, gauss_param, gauss_chisquared, double_gauss_params, double_gauss_chisquared,
            histogram, bins) = self.stats_by_amp(slope_image, amp_bounds)

        # Construct new entry for dark database table
        source_files = [os.path.basename(item) for item in file_list]
        for key in amp_mean.keys():
            dark_db_entry = {'aperture': self.aperture, 'amplifier': key, 'mean': amp_mean[key],
                             'stdev': amp_stdev[key],
                             'source_files': source_files,
                             'obs_start_time': min_time,
                             'obs_mid_time': mid_time,
                             'obs_end_time': max_time,
                             'gauss_amplitude': list(gauss_param[key][0]),
                             'gauss_peak': list(gauss_param[key][1]),
                             'gauss_width': list(gauss_param[key][2]),
                             'gauss_chisq': gauss_chisquared[key],
                             'double_gauss_amplitude1': double_gauss_params[key][0],
                             'double_gauss_peak1': double_gauss_params[key][1],
                             'double_gauss_width1': double_gauss_params[key][2],
                             'double_gauss_amplitude2': double_gauss_params[key][3],
                             'double_gauss_peak2': double_gauss_params[key][4],
                             'double_gauss_width2': double_gauss_params[key][5],
                             'double_gauss_chisq': double_gauss_chisquared[key],
                             'mean_dark_image_file': os.path.basename(mean_slope_file),
                             'hist_dark_values': bins,
                             'hist_amplitudes': histogram,
                             'entry_date': datetime.datetime.now()
                             }
            self.stats_table.__table__.insert().execute(dark_db_entry)

    def read_baseline_slope_image(self, filename):
        """Read in a baseline mean slope image and associated standard
        deviation image from the given fits file

        Parameters
        ----------
        filename : str
            Name of fits file to be read in

        Returns
        -------
        mean_image : numpy.ndarray
            2D mean slope image

        stdev_image : numpy.ndarray
            2D stdev image
        """

        try:
            with fits.open(filename) as hdu:
                mean_image = hdu['MEAN'].data
                stdev_image = hdu['STDEV'].data
            return mean_image, stdev_image
        except (FileNotFoundError, KeyError) as e:
            logging.warning('Trying to read {}: {}'.format(filename, e))

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further
        details.
        """

        logging.info('Begin logging for dark_monitor')

        apertures_to_skip = ['NRCALL_FULL', 'NRCAS_FULL', 'NRCBS_FULL']

        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'dark_monitor')

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
            possible_apertures = list(Siaf(instrument).apernames)
            possible_apertures = [ap for ap in possible_apertures if ap not in apertures_to_skip]

            for aperture in possible_apertures:
                logging.info('')
                logging.info('Working on aperture {} in {}'.format(aperture, instrument))

                # Find the appropriate threshold for the number of new files needed
                match = aperture == limits['Aperture']
                file_count_threshold = limits['Threshold'][match]

                # Locate the record of the most recent MAST search
                self.aperture = aperture
                self.query_start = self.most_recent_search()
                logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

                # Query MAST using the aperture and the time of the
                # most recent previous search as the starting time
                new_entries = mast_query_darks(instrument, aperture, self.query_start, self.query_end)

                logging.info('\tAperture: {}, new entries: {}'.format(self.aperture, len(new_entries)))

                # Check to see if there are enough new files to meet the
                # monitor's signal-to-noise requirements
                if len(new_entries) >= file_count_threshold:
                    logging.info('\tSufficient new dark files found for {}, {} to run the dark monitor.'
                                 .format(self.instrument, self.aperture))

                    # Get full paths to the files
                    new_filenames = []
                    for file_entry in new_entries:
                        try:
                            new_filenames.append(filesystem_path(file_entry['filename']))
                        except FileNotFoundError:
                            logging.warning('\t\tUnable to locate {} in filesystem. Not including in processing.'
                                            .format(file_entry['filename']))

                    # Set up directories for the copied data
                    ensure_dir_exists(os.path.join(self.output_dir, 'data'))
                    self.data_dir = os.path.join(self.output_dir,
                                                 'data/{}_{}'.format(self.instrument.lower(),
                                                                     self.aperture.lower()))
                    ensure_dir_exists(self.data_dir)

                    # Copy files from filesystem
                    dark_files, not_copied = copy_files(new_filenames, self.data_dir)

                    logging.info('\tNew_filenames: {}'.format(new_filenames))
                    logging.info('\tData dir: {}'.format(self.data_dir))
                    logging.info('\tCopied to working dir: {}'.format(dark_files))
                    logging.info('\tNot copied: {}'.format(not_copied))

                    # Run the dark monitor
                    self.process(dark_files)
                    monitor_run = True

                else:
                    logging.info(('\tDark monitor skipped. {} new dark files for {}, {}. {} new files are '
                                  'required to run dark current monitor.').format(
                        len(new_entries), instrument, aperture, file_count_threshold[0]))
                    monitor_run = False

                # Update the query history
                new_entry = {'instrument': instrument,
                             'aperture': aperture,
                             'start_time_mjd': self.query_start,
                             'end_time_mjd': self.query_end,
                             'files_found': len(new_entries),
                             'run_monitor': monitor_run,
                             'entry_date': datetime.datetime.now()}
                self.query_table.__table__.insert().execute(new_entry)
                logging.info('\tUpdated the query history table')

        logging.info('Dark Monitor completed successfully.')

    def save_mean_slope_image(self, slope_img, stdev_img, files):
        """Save the mean slope image and associated stdev image to a
        file

        Parameters
        ----------
        slope_img : numpy.ndarray
            2D array containing the mean slope image

        stdev_img : numpy.ndarray
            2D array containing the stdev image associated with the mean
            slope image.

        files : list
            List of input files used to construct the mean slope image

        Returns
        -------
        output_filename : str
            Name of fits file to save mean and stdev images within
        """

        output_filename = '{}_{}_{}_to_{}_mean_slope_image.fits'.format(self.instrument.lower(),
                                                                        self.aperture.lower(),
                                                                        self.query_start, self.query_end)

        mean_slope_dir = os.path.join(get_config()['outputs'], 'dark_monitor', 'mean_slope_images')
        ensure_dir_exists(mean_slope_dir)
        output_filename = os.path.join(mean_slope_dir, output_filename)
        logging.info("Name of mean slope image: {}".format(output_filename))

        primary_hdu = fits.PrimaryHDU()
        primary_hdu.header['INSTRUME'] = (self.instrument, 'JWST instrument')
        primary_hdu.header['APERTURE'] = (self.aperture, 'Aperture name')
        primary_hdu.header['QRY_STRT'] = (self.query_start, 'MAST Query start time (MJD)')
        primary_hdu.header['QRY_END'] = (self.query_end, 'MAST Query end time (MJD)')

        files_string = 'FILES USED: '
        for filename in files:
            files_string += '{}, '.format(filename)

        primary_hdu.header.add_history(files_string)
        mean_img_hdu = fits.ImageHDU(slope_img, name='MEAN')
        stdev_img_hdu = fits.ImageHDU(stdev_img, name='STDEV')
        hdu_list = fits.HDUList([primary_hdu, mean_img_hdu, stdev_img_hdu])
        hdu_list.writeto(output_filename, overwrite=True)
        set_permissions(output_filename)

        return output_filename

    def shift_to_full_frame(self, coords):
        """Shift the input list of pixels from the subarray coordinate
        system to the full frame coordinate system

        Parameters
        ----------
        coords : tup
            (x, y) pixel coordinates in subarray coordinate system

        Returns
        -------
        coords : tup
            (x, y) pixel coordinates in full frame coordinate system
        """

        x = coords[0]
        x += self.x0
        y = coords[1]
        y += self.y0

        return (x, y)

    def stats_by_amp(self, image, amps):
        """Calculate statistics in the input image for each amplifier as
        well as the full image

        Parameters
        ----------
        image : numpy.ndarray
            2D array on which to calculate statistics

        amps : dict
            Dictionary containing amp boundary coordinates (output from
            ``amplifier_info`` function)
            ``amps[key] = [(xmin, xmax, xstep), (ymin, ymax, ystep)]``

        Returns
        -------
        amp_means : dict
            Sigma-clipped mean value for each amp. Keys are amp numbers
            as strings (e.g. ``'1'``)

        amp_stdevs : dict
            Sigma-clipped standard deviation for each amp. Keys are amp
            numbers as strings (e.g. ``'1'``)

        gaussian_params : dict
            Best-fit Gaussian parameters to the dark current histogram.
            Keys are amp numbers as strings. Values are three-element
            lists ``[amplitude, peak, width]``. Each element in the list
            is a tuple of the best-fit value and the associated
            uncertainty.

        gaussian_chi_squared : dict
            Reduced chi-squared for the best-fit parameters. Keys are
            amp numbers as strings

        double_gaussian_params : dict
            Best-fit double Gaussian parameters to the dark current
            histogram. Keys are amp numbers as strings. Values are six-
            element lists. (3-elements * 2 Gaussians).
            ``[amplitude1, peak1, stdev1, amplitude2, peak2, stdev2]``
            Each element of the list is a tuple containing the best-fit
            value and associated uncertainty.

        double_gaussian_chi_squared : dict
            Reduced chi-squared for the best-fit parameters. Keys are
            amp numbers as strings

        hist : numpy.ndarray
            1D array of histogram values

        bin_centers : numpy.ndarray
            1D array of bin centers that match the ``hist`` values.
        """

        amp_means = {}
        amp_stdevs = {}
        gaussian_params = {}
        gaussian_chi_squared = {}
        double_gaussian_params = {}
        double_gaussian_chi_squared = {}

        # Add full image coords to the list of amp_boundaries, so that full
        # frame stats are also calculated.
        if 'FULL' in self.aperture:
            maxx = 0
            maxy = 0
            for amp in amps:
                mxx = amps[amp][0][1]
                mxy = amps[amp][1][1]
                if mxx > maxx:
                    maxx = copy(mxx)
                if mxy > maxy:
                    maxy = copy(mxy)
            amps['5'] = [(0, maxx, 1), (0, maxy, 1)]
            logging.info(('\tFull frame exposure detected. Adding the full frame to the list '
                          'of amplifiers upon which to calculate statistics.'))

        for key in amps:
            x_start, x_end, x_step = amps[key][0]
            y_start, y_end, y_step = amps[key][1]
            indexes = np.mgrid[y_start: y_end: y_step, x_start: x_end: x_step]

            # Basic statistics, sigma clipped areal mean and stdev
            amp_mean, amp_stdev = calculations.mean_stdev(image[indexes[0], indexes[1]])
            amp_means[key] = amp_mean
            amp_stdevs[key] = amp_stdev

            # Create a histogram
            lower_bound = (amp_mean - 7 * amp_stdev)
            upper_bound = (amp_mean + 7 * amp_stdev)

            hist, bin_edges = np.histogram(image[indexes[0], indexes[1]], bins='auto',
                                           range=(lower_bound, upper_bound))
            bin_centers = (bin_edges[1:] + bin_edges[0: -1]) / 2.
            initial_params = [np.max(hist), amp_mean, amp_stdev]

            # Fit a Gaussian to the histogram. Save best-fit params and
            # uncertainties, as well as reduced chi squared
            amplitude, peak, width = calculations.gaussian1d_fit(bin_centers, hist, initial_params)
            gaussian_params[key] = [amplitude, peak, width]

            gauss_fit_model = models.Gaussian1D(amplitude=amplitude[0], mean=peak[0], stddev=width[0])
            gauss_fit = gauss_fit_model(bin_centers)

            positive = hist > 0
            degrees_of_freedom = len(hist) - 3.
            total_pix = np.sum(hist[positive])
            p_i = gauss_fit[positive] / total_pix
            gaussian_chi_squared[key] = (np.sum((hist[positive] - (total_pix * p_i) ** 2) / (total_pix * p_i))
                                         / degrees_of_freedom)

            # Double Gaussian fit only for full frame data (and only for
            # NIRISS, NIRCam at the moment.)
            if key == '5':
                if self.instrument.upper() in ['NIRISS', 'NIRCAM']:
                    initial_params = (np.max(hist), amp_mean, amp_stdev * 0.8,
                                      np.max(hist) / 7., amp_mean / 2., amp_stdev * 0.9)
                    double_gauss_params, double_gauss_sigma = calculations.double_gaussian_fit(bin_centers, hist, initial_params)
                    double_gaussian_params[key] = [[param, sig] for param, sig in zip(double_gauss_params, double_gauss_sigma)]
                    double_gauss_fit = calculations.double_gaussian(bin_centers, *double_gauss_params)
                    degrees_of_freedom = len(bin_centers) - 6.
                    dp_i = double_gauss_fit[positive] / total_pix
                    double_gaussian_chi_squared[key] = np.sum((hist[positive] - (total_pix * dp_i) ** 2) / (total_pix * dp_i)) / degrees_of_freedom

                else:
                    double_gaussian_params[key] = [[0., 0.] for i in range(6)]
                    double_gaussian_chi_squared[key] = 0.
            else:
                double_gaussian_params[key] = [[0., 0.] for i in range(6)]
                double_gaussian_chi_squared[key] = 0.

        logging.info('\tMean dark rate by amplifier: {}'.format(amp_means))
        logging.info('\tStandard deviation of dark rate by amplifier: {}'.format(amp_means))
        logging.info('\tBest-fit Gaussian parameters [amplitude, peak, width]'.format(gaussian_params))
        logging.info('\tReduced chi-squared associated with Gaussian fit: {}'.format(gaussian_chi_squared))
        logging.info('\tBest-fit double Gaussian parameters [amplitude1, peak1, width1, amplitude2, peak2, '
                     'width2]'.format(double_gaussian_params))
        logging.info('\tReduced chi-squared associated with double Gaussian fit: {}'
                     .format(double_gaussian_chi_squared))

        return (amp_means, amp_stdevs, gaussian_params, gaussian_chi_squared, double_gaussian_params,
                double_gaussian_chi_squared, hist.astype(np.float), bin_centers)


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Dark()
    monitor.run()

    update_monitor_table(module, start_time, log_file)
