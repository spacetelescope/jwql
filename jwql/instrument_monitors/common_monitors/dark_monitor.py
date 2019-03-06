#! /usr/bin/env python

"""This module contains code for the dark current monitor, whichxxxxxxx
blah blah blah

Author
------

    - Bryan Hilbert

Use
---

    This module can be imported and used as such:

    ::

        from jwql.instrument_monitors.common_monitors import dark_monitor
        something

        or

        command line call here


Basic flow:

Identify files to use
Retrieve from MAST
If files are not rate images, run calwebb_detector1 to get rate images
      (look into dark pipeline. what steps are done?)

Combine into mean slope image with  (pixel-by-pixel) sigma-clipping
      also produce stdev image at same time
Calculate sigma-clipped mean and stdev for each amplifier - add to trending plot
For each amp, fit mean image with “two gaussian components” - compare to previous results/trending plot
Compare mean slope image to a baseline image - create ratio to show any new hot/dead pixels and flag these

THESE ARE READNOISE CHECKS:
(OR DO WE WANT TO REMOVE 1/f noise FIRST OR ANYTHING LIKE THAT?)
In stdev image, flag pixels with values above threshold (as noisy).
Maybe compare to a baseline noise image and flag pixels that are different by threshold as newly noisy.
"""
import glob  # only during testing
import matplotlib.pyplot as plt  # only for testing
import numpy as np
import os

from astropy.io import fits
from astropy.modeling import models
from astropy.stats import sigma_clip
from astropy.time import Time
from jwst import datamodels
from pysiaf import Siaf
from sqlalchemy import Table

from jwql.database.database_interface import base
from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamDarkQueries
from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils import maths, instrument_properties, permissions
from jwql.utils.constants import AMPLIFIER_BOUNDARIES, JWST_INSTRUMENT_NAMES, JWST_DATAPRODUCTS
from jwql.utils.utils import copy_files, download_mast_data, ensure_dir_exists, get_config, \
                             filesystem_path


class Dark():
    def __init__(self, new_dark_threshold=10, testing=False):
        """
        Parameters
        ----------
        new_dark_threshold : int
            Minimum number of new dark current files needed in order to
            run the dark current monitor. This means that this class needs
            to be instantiated for each instrument/detector/subarray
            combination

        testing : bool
            For pytest. If True, an instance of Dark is created, but no
            other code is executed.
        """
        if not testing:
            # Get the output directory
            #self.output_dir = os.path.join(get_config()['outputs'], 'monitor_darks')
            print('Use the real outptut directory above before merging')
            self.output_dir = '~/python_repos/test_jwql/test_dark_monitor'
            #history_file = os.path.join(self.output_dir, 'mast_query_history.txt')

            # Use the current time as the end time for MAST query
            current_time_mjd = Time.now().mjd

            # Loop over all instruments
            for instrument in JWST_INSTRUMENT_NAMES:

                # Get a list of all possible apertures from pysiaf
                possible_apertures = Siaf(instrument).apernames

                # Locate the record of the most recent MAST search
                for aperture in possible_apertures:
                    most_recent_queries = self.most_recent_search(NIRCamDarkQueries, aperture)
                    self.instrument = instrument
                    self.aperture = aperture
                    self.query_start = most_recent_queries['end_time']
                    self.query_end = current_time_mjd

                    # Query MAST using the aperture and the time of the
                    # most recent previous search as the starting time
                    new_entries = mast_query_darks(instrument, aperture, self.query_start, self.query_end)

                    # Check to see if there are enough new files to meet
                    # the monitor's signal-to-noise requirements
                    if len(new_entries) >= new_dark_threshold:
                        # Get full paths to the files
                        new_filenames = [filesystem_path(file_entry['filename']) for file_entry in new_entries]

                        # Set up directories for the copied data
                        ensure_dir_exists(os.path.join(self.output_dir, 'data'))
                        self.data_dir = os.path.join(self.output_dir, 'data/{}_{}'.format(self.instrument.lower(),
                                                                                          self.aperture.lower()))
                        ensure_dir_exists(self.data_dir)

                        # Copy files from filesystem
                        copied, not_copied = copy_files(new_filenames, self.data_dir)

                        # Short-term fix: if some of the files from the query are not
                        # in the filesystem, try downloading them from MAST
                        # **********This should most likely be removed before merging********
                        if len(not_copied) > 0:
                            uncopied_basenames = [os.path.basename(infile) for infile in not_copied]
                            uncopied_results = [entry for entry in new_entries if entry['filename'] in uncopied_basenames]
                            download_mast_data(uncopied_results, self.output_dir)

                        # Run the dark monitor
                        #dark_files = [os.path.join(self.output_dir, filename) for filename in new_filenames]
                        dark_files = copied
                        print('later add MAST results to this list')
                        self.run(dark_files, instrument, aperture)
                        monitor_run = True
                    else:
                        print(("Dark monitor skipped. {} new dark files for {}, {}. {} new files are "
                               "required to run dark current monitor.").format(len(new_entries),
                                                                               row['Instrument'],
                                                                               row['Aperture'],
                                                                               new_dark_threshold))
                        monitor_run = False

                    # Update the query history
                    new_entry = {'instrument': instrument, 'aperture': aperture,
                                 'start_time_mjd': self.query_start, 'end_time_mjd': current_time,
                                 'files_found': len(new_entries), 'run_monitor': monitor_run}
                    NIRCamDarkQueries.insert().execute(new_entry)

            logging.info('Dark Monitor completed successfully.')

    def add_bad_pix(self, coordinates, pixel_type, files):
        """
        Add a set of bad pixels to the bad pixel database

        Parameters
        ----------
        coordinates : tup
            Tuple of two lists, containing x,y coordinates of bad pixels.
            (Output of np.where call)

        pixel_type : str
            Type of bad pixel. Options are 'dead', 'hot' and 'noisy'

        files : list
            List of fits files which were used to identify the bad pixels
        """
        entries = []
        for x, y in zip(coordinates[0], coordinates[1]):
            entry = {'detector': self.detector, 'x_coord': x, 'y_coord': y, 'type': pixel_type,
                     'source_files': files}
            entries.append(entry)
        NIRCamDarkPixelStats.insert().execute(entries)

    def get_metadata(self, filename):
        """Collect basic metadata from filename that will be needed later

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
        except KeyError as e:
            print(e)

    def exclude_existing_badpix(self, badpix, pixel_type):
        """Given a set of coordinates of bad pixels, determine which of
        these pixels have been previously identified and remove them
        from the list

        Parameters
        ----------
        badpix : tup
            Tuple of lists containing x and y pixel coordinates. (Output
            of numpy.where call)

        pixel_type : str
            Type of bad pixel being examined. Options are 'hot', 'dead',
            and 'noisy'

        Returns
        -------
        new_pixels_x : list
            List of x coordinates of new bad pixels

        new_pixels_y : list
            List of y coordinates of new bad pixels

        """
        if pixel_type not in ['hot', 'dead', 'noisy']:
            raise ValueError('Unrecognized bad pixel type: {}'.format(pixel_type))

        db_entries = session.query(NIRCamDarkPixelStats) \
            .filter(NIRCamDarkPixelStats.type == pixel_type) \
            .filter(NIRCamDarkPixelStats.detector == self.detector) \
            .all()

        already_found = []
        for foundx, foundy in zip(db_entries['x_coord'], db_entries['y_coord']):
            already_found.append((foundx, foundy))

        # Check to see if each pixel already appears in teh database for
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
        """Get the ratio of the slope image to a baseline slope image.
        Pixels in the ratio image with values above hot_threshold will
        be marked as newly hot, and those with ratio values less than
        dead_threshold will be marked as newly dead.

        Parameters
        ----------
        mean_image : numpy.ndarray
            2D array containing the slope image from the new data

        comparison_image : numpy.ndarray
            2D array containing the baseline slope image to compare
            against the new slope image.

        hot_threshold : float
            (mean_image / comparison_image) ratio value above which
            a pixel is considered newly hot.

        dead_threshold : float
            mean_image / comparison_image) ratio value below which
            a pixel is considered newly dead.

        Returns
        -------
        hotpix : tuple
            Tuple (of lists) containing x,y coordinates of newly hot pixels

        deadpix : tuple
            Tuple (of lists) containing x,y coordinates of newly dead pixels
        """
        ratio = mean_image / comparison_image
        hotpix = np.where(ratio > hot_threshold)
        deadpix = np.where(ratio < dead_threshold)
        return hotpix, deadpix

    def most_recent_search(table_name, aperture_name):
        subq = session.query(table_name.aperture_name,
                             func.max(table_name.end_time_mjd).label('maxdate')
                             ).group_by(table_name.aperture_name).subquery('t2')

        query = session.query(table_name).join(
            subq,
            and_(
                table_name.aperture_name == subq.c.aperture_name,
                table_name.end_time_mjd == subq.c.maxdate,
                table_name.run_monitor is True
            )
        )

        query_count = query.count()
        if not query count:
            query = {'end_time': 57357.0}  # Dec 1, 2015 == CV3
        return query

    def noise_check(self, new_noise_image, baseline_noise_image, threshold=1.5):
        """Get the ratio of the stdev (noise) image to a baseline noise
        image. Pixels in the ratio image with values above threshold
        will be marked as newly noisy.

        Parameters
        ----------
        new_noise_image : numpy.ndarray
            2D array containing the noise image from the new data

        baseline_noise_image : numpy.ndarray
            2D array containing the baseline noise image to compare
            against the new noise image.

        threshold : float
            (new_noise_image / baseline_noise_image) ratio value above
            which a pixel is considered newly noisey.

        Returns
        -------
        noisy : tuple
            Tuple of x,y coordinates of newly noisy pixels
        """
        ratio = new_noise_image / baseline_noise_image
        noisy = np.where(ratio > threshold)
        return noisy

    def read_baseline_slope_image(self, filename):
        """Read in a baseline mean slope image and associated standard
        deviation image from the give fits file

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

    def run(self, file_list, instrument, aperture):
        """MAIN FUNCTION

        Parameters
        ----------
        file_list : list
            List of filenames (including full paths) to the dark
            current files

        instrument : str
            Instrument name

        aperture : str
            Aperture name of the files (e.g. 'NRCA1_FULL') From
            'apername' field in the MAST query results
        """
        required_steps = pipeline_tools.get_pipeline_steps(instrument)

        print('REQUIRED STEPS:', required_steps)

        # Modify the list of pipeline steps to skip those not needed
        # for the preparation of dark current data
        required_steps['dark_current'] = False
        print('what steps to skip for MIRI?')

        slope_files = []
        for filename in file_list:
            completed_steps = pipeline_tools.completed_pipeline_steps(filename)
            print('but if a step was skipped, often you cant go back and run it. e.g. you cant run persistence after things have been linearized.')
            print('so maybe in this case we just want to run jump and ramp fitting and be done. persistence is not run as part of the dark pipeline')
            print('but linearization is. Maybe we assume this wont be a problem')
            steps_to_run = pipeline_tools.steps_to_run(filename, required_steps, completed_steps)

            for key in steps_to_run:
                if key in ['jump', 'rate']:
                    steps_to_run[key] = True
                else:
                    steps_to_run[key] = False
            print('COMPLETED STEPS:', completed_steps)
            print('STEPS TO RUN:', steps_to_run)

            # Run any remaining required pipeline steps
            if any(steps_to_run.values()) is False:
                slope_files.append(filename)
            else:
                processed_file = pipeline_tools.run_calwebb_detector1_steps(filename, steps_to_run)
                slope_files.append(processed_file)

        print('slope files are: ', slope_files)
        # Basic metadata that will be needed later
        self.get_metadata(slope_files[0])

        # Read in all slope images and place into a list
        slope_image_stack = pipeline_tools.image_stack(slope_files)

        # Calculate a mean slope image from the inputs
        slope_image, stdev_image = maths.mean_image(slope_image_stack, sigma_threshold=3)
        mean_slope_file = self.save_mean_slope_image(slope_image, stdev_imge, slope_files)
        dark_db_entry['mean_dark_image_file'] = mean_slope_file

        # Search for new hot/dead/noisy pixels----------------------------
        # Read in baseline mean slope image and stdev image
        #baseline_file = '{}_{}_baseline_slope_and_stdev_images.fits'.format(instrument, aperture)
        #baseline_filepath = os.path.join(self.output_dir, 'baseline/', baseline_file)
        #baseline_mean, baseline_stev = self.read_baseline_slope_image(baseline_filepath)
        print('baseline check removed for testing')
        baseline_mean = np.zeros((2048, 2048)) + 0.004
        baseline_stdev = np.zeros((2048, 2048)) + 0.004

        # Check the hot/dead pixel population for changes
        new_hot_pix, new_dead_pix = self.find_hot_dead_pixels(slope_image, baseline_mean)

        # Shift the coordinates to be in full frame coordinate system
        new_hot_pix = self.shift_to_full_frame(new_hot_pix)
        new_dead_pix = self.shift_to_full_frame(new_dead_pix)

        # Exclude hot and dead pixels found previously
        new_hot_pix = self.exclude_existing_badpix(new_hot_pix, 'hot')
        new_dead_pix = self.exclude_existing_badpix(new_dead_pix, 'dead')

        # Add new hot and dead pixels to the database
        self.add_bad_pix(new_hot_pix, 'hot', file_list)
        self.add_bad_pix(new_dead_pix, 'dead', file_list)

        print('Found {} new hot pixels'.format(len(new_hot_pix)))
        print('Add logging')

        # Check for any pixels that are significanly more noisy than
        # in the baseline stdev image
        new_noisy_pixels = self.noise_check(stdev_image, baseline_stdev)

        # Shift coordinates to be in full_frame coordinate system
        new_noisy_pixels = self.shift_to_full_frame(new_noisy_pixels)

        # Exclude previously found noisy pixels
        new_noisy_pixels = self.exclude_existing_badpix(new_noisy_pixels, 'noisy')

        # Add new noisy pixels to the database
        self.add_bad_pix(new_noisy_pix, 'noisy', file_list)

        # Calculate image statistics--------------------------------------
        # Read in the file containing historical image statistics
        stats_file = '{}_{}_dark_current_statistics.txt'.format(instrument, aperture)
        stats_filepath = os.path.join(self.output_dir, 'stats/', stats_file)
        #history = ascii.read(stats_file)

        # Find amplifier boundaries so per-amp statistics can be calculated
        number_of_amps, amp_bounds = instrument_properties.amplifier_info(slope_files[0])

        print('AMP_BOUNDS:')
        print(amp_bounds)

        # Calculate mean and stdev values, and fit a Gaussian to the
        # histogram of the pixels in each amp
        (amp_mean, amp_stdev, gauss_param, gauss_chisquared, double_gauss_params, double_gauss_chisquared
            histogram, bins) = \
            self.stats_by_amp(slope_image, amp_bounds)

        print('Maybe move this to a separate function')
        for key in amp_mean:
            dark_db_entry = {'aperture': aperture, 'amplifier': key, 'mean': amp_mean[key],
                             'stdev': amp_stdev[key],
                             'source_files': file_list,
                             'gauss_amplitude': gauss_param[key][0],
                             'gauss_peak': gauss_param[key][1],
                             'gauss_width': gauss_param[key][2],
                             'gauss_chisq': gauss_chisquared[key],
                             'double_gauss_amplitide1': double_gauss_params[key][0],
                             'double_gauss_peak1': double_gauss_params[key][1],
                             'double_gauss_width1': double_gauss_params[key][2],
                             'double_gauss_amplitide2': double_gauss_params[key][3],
                             'double_gauss_peak2': double_gauss_params[key][4],
                             'double_gauss_width2': double_gauss_params[key][5],
                             'double_gauss_chisq': double_gauss_chisquared[key],
                             'mean_dark_image_file': mean_slope_file,
                             'hist_dark_values': histogram,
                             'hist_amplitudes': bins
                             }
            NIRCamDarkDarkCurrent.insert().execute(dark_db_entry)

        print(('what about updating the baseline dark slope image? Should that be done after'
               'each run of the monitor where the dark current is found to be ok?'))
        print(('or should the baseline simply be the dark slope image produced by the'
               'last run of the dark monitor where the dark current was found to be ok?'))

    def save_mean_slope_image(self, slope_img, stdev_img, files):
        """Save the mean slope image and associated stdev image to a file

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
        mean_slope_dir = os.path.join(get_config()['outputs'], 'monitor_darks/mean_slope_images/')
        ensure_dir_exists(mean_slope_dir)
        output_filename = os.path.join(mean_slope_dir, output_filename)
        primary_hdu = fits.PrimaryHDU()
        primary_hdu.header['INSTRUME'] = (self.instrument, 'JWST instrument')
        primary_hdu.header['APERTURE'] = (self.aperture, 'Aperture name')
        primary_hdu.header['QRY_STRT'] = (self.query_start, 'MAST Query start time (MJD)')
        primary_hdu.header['QRY_END'] = (self.query_end, 'MAST Query end time (MJD)')
        primary_hdu.header['FILES'] = (files, 'File used to construct the mean slope image')
        mean_img_hdu = fits.ImageHDU(slope_img, name='MEAN')
        stdev_img_hdu = fits.ImageHDU(stdev_img, name='STDEV')
        hdu_list = fits.HDUList([primary_hdu, mean_img_hdu, stdev_img_hdu])
        hdu_list.writeto(output_filename, overwrite=True)
        permissions.set_permissions(output_filename)
        return output_filename

    def shift_to_full_frame(self, coords):
        """Shift the input list of pixels from the subarray coordinate
        system to the full frame coordinate system

        Parameters
        ----------
        coords : tup

        Returns
        -------
        coords : tup
        """
        x = coords[0]
        x += self.x0
        y = coords[1]
        y += self.y0
        return (x, y)

    def stats_by_amp(self, image, amps, chisq_threshold=1.1, plot=True):
        """Calculate statistics in the input image for each amplifier
        Warpper around calls to mean_stdev and gaussian_fit

        Parameters
        ----------
        image : numpy.ndarray
            2D array on which to calculate statistics

        amps : dict
            Dictionary containing amp boundary coordinates
            (output from amplifier_info function)

        Returns
        -------
        some stuff
        """
        amp_means = {}
        amp_stdevs = {}
        gaussian_params = {}
        gaussian_chi_squared = {}
        double_gaussian_params = {}
        double_gaussian_chi_squared = {}

        # Add full image coords to the list of amp_boundaries, so that full
        # frame stats are also calculated.
        image_shape = image.shape
        if image_shape == (2048, 2048):
            amps['5'] = [(0, 0), (2048, 2048)]

        for key in amps:
            x_start, y_start = amps[key][0]
            x_end, y_end = amps[key][1]

            # Basic statistics, sigma clipped areal mean and stdev
            amp_mean, amp_stdev = maths.mean_stdev(image[y_start: y_end, x_start: x_end])
            amp_means[key] = amp_mean
            amp_stdevs[key] = amp_stdev

            # Create a histogram
            lower_bound = (amp_mean - 7 * amp_stdev)
            upper_bound = (amp_mean + 7 * amp_stdev)
            print('remove_refpix_before_making_histograms, maybe by adjusting amp boundaries?')
            hist, bin_edges = np.histogram(image[y_start: y_end, x_start: x_end], bins='auto',
                                           range=(lower_bound, upper_bound))
            bin_centers = (bin_edges[1:] + bin_edges[0: -1]) / 2.
            initial_params = [np.max(hist), amp_mean, amp_stdev]

            # Fit a Gaussian to the histogram. Save best-fit params and
            # uncertainties, as well as reduced chi squared
            amplitude, peak, width = maths.gaussian1d_fit(bin_centers, hist, initial_params)
            gaussian_params[key] = [amplitude, peak, width]
            gauss_fit_model = models.Gaussian1D(amplitude=amplitude[0], mean=peak[0], stddev=width[0])
            gauss_fit = gauss_fit_model(bin_centers)

            positive = hist > 0
            degrees_of_freedom = len(hist) - 3


            gaussian_chi_squared[key] = np.sum((gauss_fit[positive] - hist[positive])**2 / hist[positive]) / degrees_of_freedom


            f, a = plt.subplots()
            a.plot(bin_centers, hist, color='black')
            a.plot(bin_centers, gauss_fit, color='red')
            plt.show()
            print('add bin_centers and gauss_fit to database table')


            # If chisq is large enough to suggest a bad fit, save the
            # histogram and fit for later plotting
            #if gaussian_chi_squared[key] > chisq_threshold:
            #    where_do_we_send_this(key, bin_centers, hist, gauss_fit)

            # Double Gaussian fit only for full frame data (and only for
            # NIRISS at the moment.)
            if key == '5':
                if self.instrument.upper() in ['NIRISS', 'NIRCAM']:
                    initial_params = (np.max(hist), amp_mean, amp_stdev * 0.8,
                                      np.max(hist) / 7., amp_mean / 2., amp_stdev * 0.9)
                    double_gauss_params, double_gauss_sigma = maths.double_gaussian_fit(bin_centers, hist,
                                                                                        initial_params)
                    double_gaussian_params[key] = [[param, sig] for param, sig in zip(double_gauss_params,
                                                                                      double_gauss_sigma)]
                    double_gauss_fit = maths.double_gaussian(bin_centers, *double_gauss_params)
                    degrees_of_freedom = len(bin_centers) - 6
                    double_gaussian_chi_squared[key] = np.sum((double_gauss_fit[positive] - hist[positive])**2
                                                              / hist[positive]) / degrees_of_freedom


                    f, a = plt.subplots()
                    a.plot(bin_centers, hist, color='black')
                    a.plot(bin_centers, gauss_fit, color='red')
                    a.plot(bin_centers, double_gauss_fit, color='blue')
                    plt.show()



                else:
                    double_gaussian_params[key] = [(None, None)]
                    double_gaussian_chi_squared[key] = None
                print('add bin_centers and double_gauss_fit to database table')
                    # If chisq is large enough to suggest a bad fit, save the
                    # histogram and fit for later plotting
                    #if gaussian_chi_squared[key] > chisq_threshold:
                    #    where_do_we_send_this(key, bin_centers, hist, double_gauss_fit)
                    #    save_to_an_ascii_file_to_be_read_in_by_webb_app()
                    #    or_do_we_have_webb_app_plot_all_histograms()

        print('RESULTS OF STATS_BY_AMP:')
        print(amp_means, amp_stdevs, gaussian_params, gaussian_chi_squared, double_gaussian_params,
                double_gaussian_chi_squared)
        print('add results to database table')
        return (amp_means, amp_stdevs, gaussian_params, gaussian_chi_squared, double_gaussian_params,
                double_gaussian_chi_squared, hist, bin_centers)


if __name__ == '__main__':
    #logging.configure_logging()
    monitor = Dark()


def create_history_file():
    """Create the initial version of the query history file that will
    be used with the dark current monitor
    """
    import pysiaf

    # Get the name of the file to save the table to
    file_base = 'mast_query_history.txt'
    output_dir = os.path.join(get_config()['outputs'], 'monitor_darks')
    history_file = os.path.join(output_dir, file_base)

    # Make the time of the last MAST query far back in time for this
    # initial version of the file
    initial_time = '2012-01-01T00:00:00'

    instruments = []
    apertures = []
    last_query_time = []

    # Add a row for each instrument/aperture combination
    for instrument in JWST_INSTRUMENTS:
        siaf = pysiaf.Siaf(instrument)
        apertures.extend(list(siaf.apernames))
        instruments.extend([instrument] * len(apertures))
        last_query_time.extend([initial_time] * len(apertures))

    # Create and populate table
    history = Table()
    history['Instrument'] = instruments
    history['Aperture'] = apertures
    history['Last_Query'] = last_query_time
    history.meta['comments'] = [('This file contains a table listing the ending time of the last '
                                 'query to MAST for each instrument/aperture')]
    history.write(history_file, format='ascii')
    print('New version of the MAST query history file ({}) generated.'.format(file_base))


def mast_query_darks(instrument, aperture, start_date, end_date):
    """Query MAST for dark current data

    Parameters
    ----------
    instrument : str

    aperture : str
        (e.g. NRCA1_FULL)

    start_date : ?

    end_date : ?

    Returns
    -------
    something
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
        dark_template = 'NRS_DARK'
    elif instrument.lower() == 'fgs':
        instrument = 'FGS'
        dark_template = 'FGS_DARK'
    elif instrument.lower() == 'miri':
        instrument = 'MIRI'
        dark_template = ['MIR_DARKALL', 'MIR_DARKIMG', 'MIR_DARKMRS']

    # monitor_mast.instrument_inventory does not allow list inputs to the added_filters
    # input (or at least if you do provide a list, then it becomes a nested list when
    # it sends the query to MAST. The nested list is subsequently ignored by MAST.)
    # So query once for each dark template, and combine outputs into a single list.
    query_results = []
    for template_name in dark_template:
        # Create dictionary of parameters to add
        parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                      "apername": aperture, "exp_type": template_name}

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                  add_filters=parameters, return_data=True, caom=False)
        if len(query['data']) > 0:
            query_results.extend(query['data'])
    return query_results


def advancedSearchCounts():
    """Example function for MAST query from MAST website. Should be able to delete before merging
    https://mast.stsci.edu/api/v0/pyex.html
    """
    service = "Mast.Jwst.Filtered.NIRCAM"
    params = {"columns": "*",
              "filters": [{"paramName": "date_obs_mjd", "values": [{"min": 56843.1, "max": 58640.2}]},
                          {"paramName": "apername", "values": ['NRCA1_FULL']},
                          {"paramName": "exp_type", "values": ['NRC_DARK']}
                          ]
              }
    response = Mast.service_request_async(service, params)
    return response[0].json
