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
from glob import glob
import logging
import os

from astropy.io import ascii, fits
from astropy.modeling import models
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from bokeh.io import export_png
from bokeh.models import ColorBar, ColumnDataSource, HoverTool, Legend
from bokeh.models import LinearColorMapper
from bokeh.plotting import figure
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
from jwql.shared_tasks.shared_tasks import only_one, run_pipeline, run_parallel_pipeline
from jwql.utils import calculations, instrument_properties, monitor_utils
from jwql.utils.constants import ASIC_TEMPLATES, DARK_MONITOR_MAX_BADPOINTS_TO_PLOT, JWST_INSTRUMENT_NAMES
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_DATAPRODUCTS, RAPID_READPATTERNS
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path

THRESHOLDS_FILE = os.path.join(os.path.split(__file__)[0], 'dark_monitor_file_thresholds.txt')


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

        # Change to int from numpy.int64 because the latter can't be put into the
        # database apparently.
        x_coord = [int(x) for x in coordinates[0]]
        y_coord = [int(y) for y in coordinates[1]]

        source_files = [os.path.basename(item) for item in files]
        entry = {'detector': self.detector,
                 'x_coord': x_coord,
                 'y_coord': y_coord,
                 'type': pixel_type,
                 'source_files': source_files,
                 'obs_start_time': observation_start_time,
                 'obs_mid_time': observation_mid_time,
                 'obs_end_time': observation_end_time,
                 'mean_dark_image_file': os.path.basename(mean_filename),
                 'baseline_file': os.path.basename(baseline_filename),
                 'entry_date': datetime.datetime.now()}
        self.pixel_table.__table__.insert().execute(entry)

    def create_mean_slope_figure(self, image, num_files, hotxy=None, deadxy=None, noisyxy=None, baseline_file=None):
        """Create and save a png containing the mean dark slope image,
        to be displayed in the web app

        Parameters
        ----------
        image : numpy.ndarray
            2D array of the dark slop image

        num_files : int
            Number of individual exposures that went into creating the mean slope image

        hotxy : tup
            2-tuple of lists that give x, y coordinates of possible new hot pixels

        deadxy : tup
            2-tuple of lists that give x, y coordinates of possible new hot pixels

        noisyxy : tup
            2-tuple of lists that give x, y coordinates of possible new hot pixels

        baseline_file : str
            Name of fits file containing the mean slope image to which ``image`` was compared
            when looking for new hot/dead/noisy pixels
        """
        output_filename = '{}_{}_{}_to_{}_mean_slope_image.png'.format(self.instrument.lower(),
                                                                       self.aperture.lower(),
                                                                       self.query_start, self.query_end)

        mean_slope_dir = os.path.join(get_config()['outputs'], 'dark_monitor', 'mean_slope_images')

        ensure_dir_exists(mean_slope_dir)
        output_filename = os.path.join(mean_slope_dir, output_filename)
        logging.info("Name of mean slope image: {}".format(output_filename))

        if image is not None:
            # Get info on image for better display later
            ny, nx = image.shape
            img_mn, img_med, img_dev = sigma_clipped_stats(image[4: ny - 4, 4: nx - 4])

            # Create figure
            start_time = Time(float(self.query_start), format='mjd').tt.datetime.strftime("%m/%d/%Y")
            end_time  = Time(float(self.query_end), format='mjd').tt.datetime.strftime("%m/%d/%Y")

            self.plot = figure(title=f'{self.aperture}: {num_files} files. {start_time} to {end_time}', tools='')
            #                   tools='pan,box_zoom,reset,wheel_zoom,save')
            self.plot.x_range.range_padding = self.plot.y_range.range_padding = 0

            # Create the color mapper that will be used to scale the image
            mapper = LinearColorMapper(palette='Viridis256', low=(img_med-5*img_dev) ,high=(img_med+5*img_dev))

            # Plot image and add color bar
            imgplot = self.plot.image(image=[image], x=0, y=0, dw=nx, dh=ny,
                                      color_mapper=mapper, level="image")

            color_bar = ColorBar(color_mapper=mapper, width=8, title='DN/sec')
            self.plot.add_layout(color_bar, 'right')

            # Add hover tool for all pixel values
            #hover_tool = HoverTool(tooltips=[('(x, y):', '($x{int}, $y{int})'),
            #                                 ('value:', '@image')
            #                                 ],
            #                       renderers=[imgplot])
            #self.plot.tools.append(hover_tool)

            if (('FULL' in self.aperture) or ('_CEN' in self.aperture)):

                if hotxy is not None:
                    # Create lists of hot/dead/noisy pixel values if present
                    hot_vals = []
                    for x, y in zip(hotxy[0], hotxy[1]):
                        if ((x < nx) & (y < ny)):
                            hot_vals.append(image[y, x])
                else:
                    hot_vals = None

                if deadxy is not None:
                    dead_vals = []
                    for x, y in zip(deadxy[0], deadxy[1]):
                        if ((x < nx) & (y < ny)):
                            dead_vals.append(image[y, x])
                else:
                    dead_vals = None

                if noisyxy is not None:
                    noisy_vals = []
                    for x, y in zip(noisyxy[0], noisyxy[1]):
                        if ((x < nx) & (y < ny)):
                            noisy_vals.append(image[y, x])
                else:
                    noisy_vals = None

                hot_legend = self.overplot_bad_pix("hot", hotxy, hot_vals)
                dead_legend = self.overplot_bad_pix("dead", deadxy, dead_vals)
                noisy_legend = self.overplot_bad_pix("noisy", noisyxy, noisy_vals)

                # Collect information about the file this image was compared against
                if baseline_file is not None:
                    base_parts = os.path.basename(baseline_file).split('_')

                    # Get the starting and ending time from the filename.
                    base_start = Time(float(base_parts[3]), format='mjd').tt.datetime
                    base_end = Time(float(base_parts[5]), format='mjd').tt.datetime
                    base_start_time = base_start.strftime("%m/%d/%Y")
                    base_end_time  = base_end.strftime("%m/%d/%Y")
                    legend_title = f'Compared to dark from {base_start_time} to {base_end_time}'
                else:
                    legend_title = 'Compared to previous mean dark'
                legend = Legend(items=[hot_legend, dead_legend, noisy_legend],
                                location="center",
                                orientation='vertical',
                                title = legend_title)

                self.plot.add_layout(legend, 'below')

            # Save the plot in a png
            export_png(self.plot, filename=output_filename)
            set_permissions(output_filename)


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
            self.x0 = header['SUBSTRT1'] - 1
            self.y0 = header['SUBSTRT2'] - 1
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
        
        if len(badpix[0]) == 0:
            logging.warning("\tNo new {} pixels to check.".format(pixel_type))
            return ([], [])
        
        logging.info("\tChecking {} potential new {} pixels".format(len(badpix[0]), pixel_type))

        if pixel_type not in ['hot', 'dead', 'noisy']:
            raise ValueError('Unrecognized bad pixel type: {}'.format(pixel_type))

        logging.info("\t\tRunning database query")
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
        found_x = np.array([x[0] for x in already_found])
        found_y = np.array([x[1] for x in already_found])

        msg = "\t\tChecking pixels against list of {} existing {} pixels"
        logging.info(msg.format(len(found_x), pixel_type))
        # Check to see if each pixel already appears in the database for
        # the given bad pixel type
        new_pixels_x = []
        new_pixels_y = []
        for x, y in zip(badpix[0], badpix[1]):
            ind_x = np.where(found_x == x)
            ind_y = np.where(found_y == y)
            if len(np.intersect1d(ind_x[0], ind_y[0])) == 0:
                new_pixels_x.append(x)
                new_pixels_y.append(y)
        
        logging.info("\t\tKeeping {} {} pixels".format(len(new_pixels_x), pixel_type))
#             pixel = (x, y)
#             if pixel not in already_found:
#                 new_pixels_x.append(x)
#                 new_pixels_y.append(y)

        session.close()
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

        session.close()
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
        query = session.query(self.query_table).filter(self.query_table.aperture == self.aperture,
                                                       self.query_table.readpattern == self.readpatt). \
                filter(self.query_table.run_monitor == True)  # noqa: E348 (comparison to true)

        dates = np.zeros(0)
        for instance in query:
            dates = np.append(dates, instance.end_time_mjd)

        query_count = len(dates)
        if query_count == 0:
            query_result = 59607.0  # a.k.a. Jan 28, 2022 == First JWST images (MIRI)
            logging.info(('\tNo query history for {} with {}. Beginning search date will be set to {}.'
                         .format(self.aperture, self.readpatt, query_result)))
        else:
            query_result = np.max(dates)

        session.close()
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

    def overplot_bad_pix(self, pix_type, coords, values):
        """Add a scatter plot of potential new bad pixels to the plot

        Paramters
        ---------
        pix_type : str
            Type of bad pixel. "hot", "dead", or "noisy"

        coords : tup
            2-tuple of lists, containing the x and y coordinates of the bad pixels

        values : list
            Values in the mean dark image at the locations of the bad pixels

        Returns
        -------
        legend_item : tup
            Tuple of legend text and associated plot. Will be converted into
            a LegendItem and added to the plot legend
        """
        if coords is None:
            coords = ([], [])
            values = []

        numpix = len(coords[0])

        colors = {"hot": "red", "dead": "blue", "noisy": "pink"}
        adjective = {"hot": "hotter", "dead": "lower", "noisy": "noisier"}
        sources = {}
        badpixplots = {}
        hover_tools = {}

        # Need to make sources a dict because we can't use the same variable name
        # for multiple ColumnDataSources
        sources = {}
        badpixplots = {}

        # If the number of pixels to overplot is higher than the threshold,
        # then empty the coords list. This way we can still create a
        # legend entry for them
        if numpix > DARK_MONITOR_MAX_BADPOINTS_TO_PLOT:
            coords = ([], [])
            values = []

        sources[pix_type] = ColumnDataSource(data=dict(pixels_x=coords[0],
                                                       pixels_y=coords[1],
                                                       values=values
                                                      )
                                             )

        # Overplot the bad pixel locations
        badpixplots[pix_type] = self.plot.circle(x=f'pixels_x', y=f'pixels_y',
                                                 source=sources[pix_type], color=colors[pix_type])

        # Create hover tools for the bad pixel types
        #hover_tools[pix_type] = HoverTool(tooltips=[(f'{pix_type} (x, y):', '(@pixels_x, @pixels_y)'),
        #                                            ('value:', f'@values'),
        #                                            ],
        #                                    renderers=[badpixplots[pix_type]])
        # Add tool to plot
        #self.plot.tools.append(hover_tools[pix_type])

        # Add to the legend
        if  numpix > 0:
            if numpix <= DARK_MONITOR_MAX_BADPOINTS_TO_PLOT:
                text = f"{numpix} pix {adjective[pix_type]} than baseline"
            else:
                text = f"{numpix} pix {adjective[pix_type]} than baseline (not shown)"
        else:
            text = f"No new {adjective[pix_type]}"

        # Create a tuple to be added to the plot legend
        legend_item = (text, [badpixplots[pix_type]])
        return legend_item

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

        # Run pipeline steps on files, generating slope files
        pipeline_files = []
        slope_files = []
        for filename in file_list:

            logging.info('\tWorking on file: {}'.format(filename))

            rate_file = filename.replace("dark", "rate")
            rate_file_name = os.path.basename(rate_file)
            local_rate_file = os.path.join(self.data_dir, rate_file_name)

            if os.path.isfile(local_rate_file):
                logging.info("\t\tFile {} exists, skipping pipeline".format(local_rate_file))
                slope_files.append(local_rate_file)
            else:
                logging.info("\t\tAdding {} to calibration set".format(filename))
                pipeline_files.append(filename)

        outputs = run_parallel_pipeline(pipeline_files, "dark", "rate", self.instrument)
        for filename in file_list:
            processed_file = filename.replace("_dark", "_rate")
            if processed_file not in slope_files and os.path.isfile(processed_file):
                slope_files.append(processed_file)
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

        try:

            # Read in all slope images and place into a list
            slope_image_stack, slope_exptimes = pipeline_tools.image_stack(slope_files)

            # Calculate a mean slope image from the inputs
            slope_image, stdev_image = calculations.mean_image(slope_image_stack, sigma_threshold=3)
            mean_slope_file = self.save_mean_slope_image(slope_image, stdev_image, slope_files)

            # Free up memory
            del slope_image_stack

            # ----- Search for new hot/dead/noisy pixels -----
            # Read in baseline mean slope image and stdev image
            # The baseline image is used to look for hot/dead/noisy pixels,
            # but not for comparing mean dark rates. Therefore, updates to
            # the baseline can be minimal.

            # Limit checks for hot/dead/noisy pixels to full frame data since
            # subarray data have much shorter exposure times and therefore lower
            # signal-to-noise
            new_hot_pix = None
            new_dead_pix = None
            new_noisy_pixels = None
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
                logging.info("\tFinding new hot/dead pixels")
                new_hot_pix, new_dead_pix = self.find_hot_dead_pixels(slope_image, baseline_mean)

                # Shift the coordinates to be in full frame coordinate system
                logging.info("\tShifting hot pixels to full frame")
                new_hot_pix = self.shift_to_full_frame(new_hot_pix)
                logging.info("\tShifting dead pixels to full frame")
                new_dead_pix = self.shift_to_full_frame(new_dead_pix)

                # Exclude hot and dead pixels found previously
                logging.info("\tExcluding previously-known hot pixels")
                new_hot_pix = self.exclude_existing_badpix(new_hot_pix, 'hot')
                logging.info("\tExcluding previously-known dead pixels")
                new_dead_pix = self.exclude_existing_badpix(new_dead_pix, 'dead')

                # Add new hot and dead pixels to the database
                logging.info('\tFound {} new hot pixels'.format(len(new_hot_pix[0])))
                self.add_bad_pix(new_hot_pix, 'hot', file_list, mean_slope_file, baseline_file, min_time, mid_time, max_time)
                logging.info('\tFound {} new dead pixels'.format(len(new_dead_pix[0])))
                self.add_bad_pix(new_dead_pix, 'dead', file_list, mean_slope_file, baseline_file, min_time, mid_time, max_time)

                # Check for any pixels that are significantly more noisy than
                # in the baseline stdev image
                logging.info("\tChecking for noisy pixels")
                new_noisy_pixels = self.noise_check(stdev_image, baseline_stdev)

                # Shift coordinates to be in full_frame coordinate system
                logging.info("\tShifting noisy pixels to full frame")
                new_noisy_pixels = self.shift_to_full_frame(new_noisy_pixels)

                # Exclude previously found noisy pixels
                logging.info("\tExcluding existing bad pixels from noisy pixels")
                new_noisy_pixels = self.exclude_existing_badpix(new_noisy_pixels, 'noisy')

                # Add new noisy pixels to the database
                logging.info('\tFound {} new noisy pixels'.format(len(new_noisy_pixels[0])))
                self.add_bad_pix(new_noisy_pixels, 'noisy', file_list, mean_slope_file, baseline_file, min_time, mid_time, max_time)
            
            logging.info("Creating Mean Slope Image {}".format(slope_image))
            # Create png file of mean slope image. Add bad pixels only for full frame apertures
            self.create_mean_slope_figure(slope_image, len(slope_files), hotxy=new_hot_pix, deadxy=new_dead_pix,
                                          noisyxy=new_noisy_pixels, baseline_file=baseline_file)
            logging.info('\tSigma-clipped mean of the slope images saved to: {}'.format(mean_slope_file))

            # ----- Calculate image statistics -----

            # Find amplifier boundaries so per-amp statistics can be calculated
            number_of_amps, amp_bounds = instrument_properties.amplifier_info(slope_files[0])
            logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

            # Calculate mean and stdev values, and fit a Gaussian to the
            # histogram of the pixels in each amp
            (amp_mean, amp_stdev, gauss_param, gauss_chisquared, double_gauss_params, double_gauss_chisquared,
                histogram, bins) = self.stats_by_amp(slope_image, amp_bounds)

            # Remove the input files in order to save disk space
            files_to_remove = glob(f'{self.data_dir}/*fits')
            for filename in files_to_remove:
                os.remove(filename)

        except Exception as e:
            logging.critical("ERROR: {}".format(e))
            raise e

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
                             'hist_dark_values': bins[key],
                             'hist_amplitudes': histogram[key],
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
    @only_one(key='dark_monitor')
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

            # Get a list of all possible readout patterns associated with the aperture
            possible_readpatts = RAPID_READPATTERNS[instrument]

            for aperture in possible_apertures:
                logging.info('')
                logging.info('Working on aperture {} in {}'.format(aperture, instrument))

                # Find appropriate threshold for the number of new files needed
                match = aperture == limits['Aperture']

                # If the aperture is not listed in the threshold file, we need
                # a default
                if not np.any(match):
                    file_count_threshold = 30
                    logging.warning(('\tAperture {} is not present in the threshold file. Continuing '
                                     'with the default threshold of 30 files.'.format(aperture)))
                else:
                    file_count_threshold = limits['Threshold'][match][0]
                self.aperture = aperture

                # We need a separate search for each readout pattern
                for readpatt in possible_readpatts:
                    self.readpatt = readpatt
                    logging.info('\tWorking on readout pattern: {}'.format(self.readpatt))

                    # Locate the record of the most recent MAST search
                    self.query_start = self.most_recent_search()
                    logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

                    # Query MAST using the aperture and the time of the
                    # most recent previous search as the starting time
                    new_entries = monitor_utils.mast_query_darks(instrument, aperture, self.query_start, self.query_end, readpatt=self.readpatt)

                    # Exclude ASIC tuning data
                    len_new_darks = len(new_entries)
                    new_entries = monitor_utils.exclude_asic_tuning(new_entries)
                    len_no_asic = len(new_entries)
                    num_asic = len_new_darks - len_no_asic
                    logging.info("\tFiltering out ASIC tuning files removed {} dark files.".format(num_asic))

                    logging.info('\tAperture: {}, Readpattern: {}, new entries: {}'.format(self.aperture, self.readpatt,
                                                                                           len(new_entries)))

                    # Check to see if there are enough new files to meet the
                    # monitor's signal-to-noise requirements
                    if len(new_entries) >= file_count_threshold:
                        logging.info('\tMAST query has returned sufficient new dark files for {}, {}, {} to run the dark monitor.'
                                     .format(self.instrument, self.aperture, self.readpatt))

                        # Get full paths to the files
                        new_filenames = []
                        for file_entry in new_entries:
                            try:
                                new_filenames.append(filesystem_path(file_entry['filename']))
                            except FileNotFoundError:
                                logging.warning('\t\tUnable to locate {} in filesystem. Not including in processing.'
                                                .format(file_entry['filename']))

                        # In some (unusual) cases, there are files in MAST with the correct aperture name
                        # but incorrect array sizes. Make sure that the new files all have the expected
                        # aperture size
                        temp_filenames = []
                        bad_size_filenames = []
                        expected_ap = Siaf(instrument)[aperture]
                        expected_xsize = expected_ap.XSciSize
                        expected_ysize = expected_ap.YSciSize
                        for new_file in new_filenames:
                            with fits.open(new_file) as hdulist:
                                xsize = hdulist[0].header['SUBSIZE1']
                                ysize = hdulist[0].header['SUBSIZE2']
                            if xsize == expected_xsize and ysize == expected_ysize:
                                temp_filenames.append(new_file)
                            else:
                                bad_size_filenames.append(new_file)
                        if len(temp_filenames) != len(new_filenames):
                            logging.info('\tSome files returned by MAST have unexpected aperture sizes. These files will be ignored: ')
                            for badfile in bad_size_filenames:
                                logging.info('\t\t{}'.format(badfile))
                        new_filenames = deepcopy(temp_filenames)

                        # If it turns out that the monitor doesn't find enough
                        # of the files returned by the MAST query to meet the threshold,
                        # then the monitor will not be run
                        if len(new_filenames) < file_count_threshold:
                            logging.info(("\tFilesystem search for the files identified by MAST has returned {} files. "
                                          "This is less than the required minimum number of files ({}) necessary to run "
                                          "the monitor. Quitting.").format(len(new_filenames), file_count_threshold))
                            monitor_run = False
                        else:
                            logging.info(("\tFilesystem search for the files identified by MAST has returned {} files.")
                                         .format(len(new_filenames)))
                            monitor_run = True

                        if monitor_run:
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

                    else:
                        logging.info(('\tDark monitor skipped. MAST query has returned {} new dark files for '
                                     '{}, {}, {}. {} new files are required to run dark current monitor.')
                                     .format(len(new_entries), instrument, aperture, self.readpatt, file_count_threshold))
                        monitor_run = False

                    # Update the query history
                    new_entry = {'instrument': instrument,
                                 'aperture': aperture,
                                 'readpattern': self.readpatt,
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

        hist : dict
            Dictionary of 1D arrays of histogram values

        bins : dict
            Dictionary of 1D arrays of bin centers that match the ``hist`` values.
        """

        amp_means = {}
        amp_stdevs = {}
        gaussian_params = {}
        gaussian_chi_squared = {}
        double_gaussian_params = {}
        double_gaussian_chi_squared = {}
        hists = {}
        bins = {}

        # Add full image coords to the list of amp_boundaries, so that full
        # frame stats are also calculated.
        if self.aperture in FULL_FRAME_APERTURES[self.instrument.upper()]:
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

            # If the number of bins is smaller than the number of paramters
            # to be fit, then we need to increase the number of bins
            if len(bin_edges) < 7:
                logging.info('\tToo few histogram bins in initial fit. Forcing 10 bins.')
                hist, bin_edges = np.histogram(image[indexes[0], indexes[1]], bins=10,
                                               range=(lower_bound, upper_bound))

            bin_centers = (bin_edges[1:] + bin_edges[0: -1]) / 2.
            hists[key] = hist.astype(float)
            bins[key] = bin_centers
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
            gaussian_chi_squared[key] = (np.sum((hist[positive] - (total_pix * p_i) ** 2) / (total_pix * p_i)) / degrees_of_freedom)

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
        logging.info('\tBest-fit Gaussian parameters [amplitude, peak, width]: {}'.format(gaussian_params))
        logging.info('\tReduced chi-squared associated with Gaussian fit: {}'.format(gaussian_chi_squared))
        logging.info('\tBest-fit double Gaussian parameters [amplitude1, peak1, width1, amplitude2, peak2, '
                     'width2]: {}'.format(double_gaussian_params))
        logging.info('\tReduced chi-squared associated with double Gaussian fit: {}'
                     .format(double_gaussian_chi_squared))

        return (amp_means, amp_stdevs, gaussian_params, gaussian_chi_squared, double_gaussian_params,
                double_gaussian_chi_squared, hists, bins)


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = Dark()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
