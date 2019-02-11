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

from astropy.io import ascii, fits
from astropy.modeling import models
from astropy.stats import sigma_clip
from astropy.time import Time
from jwst import datamodels

from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils import maths, instrument_properties
from jwql.utils.utils import copy_files, download_mast_data, ensure_dir_exists, get_config, \
                             filesystem_path, AMPLIFIER_BOUNDARIES, JWST_INSTRUMENTS, JWST_DATAPRODUCTS


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
            history_file = os.path.join(self.output_dir, 'mast_query_history.txt')

            # Use the current time as the end time for MAST query
            current_time = Time.now()
            current_time_mjd = current_time.mjd

            # Open file containing history of queries
            past_queries = ascii.read(history_file)

            # Loop over instrument/aperture combinations, and query MAST for new files
            for row in past_queries:
                starting_time = Time(row['Last_Query']).mjd
                new_entries = mast_query_darks(row['Instrument'], row['Aperture'], starting_time, current_time_mjd)

                # Check to see if there are enough for
                # the monitor's signal-to-noise requirements
                if len(new_entries) >= new_dark_threshold:
                    # Get full paths to the files
                    new_filenames = [filesystem_path(file_entry['filename']) for file_entry in new_entries]

                    # Set up directories for the copied data
                    ensure_dir_exists(os.path.join(self.output_dir, 'data'))
                    self.data_dir = os.path.join(self.output_dir, 'data/{}_{}'.format(row['Instrument'].lower(),
                                                                                  row['Aperture'].lower()))
                    ensure_dir_exists(self.data_dir)

                    # Copy files from filesystem
                    copied, not_copied = copy_files(new_filenames, self.data_dir)

                    # Short-term fix: if some of the files from the query are not
                    # in the filesystem, try downloading them from MAST
                    if len(not_copied) > 0:
                        uncopied_basenames = [os.path.basename(infile) for infile in not_copied]
                        uncopied_results = [entry for entry in new_entries if entry['filename'] in uncopied_basenames]
                        download_mast_data(uncopied_results, self.output_dir)

                    # Run the dark monitor
                    #dark_files = [os.path.join(self.output_dir, filename) for filename in new_filenames]
                    dark_files = copied
                    print('later add MAST results to this list')
                    self.run(dark_files, row['Instrument'], row['Aperture'])

                    # Update the query history for the next call
                    row['Last_Query'] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                else:
                    print(("Dark monitor skipped. {} new dark files for {}, {}. {} new files are "
                           "required to run dark current monitor.").format(len(new_entries),
                                                                           row['Instrument'],
                                                                           row['Aperture'],
                                                                           new_dark_threshold))
            logging.info('Dark Monitor completed successfully.')
        #else:
        #    self.instrument == ''
        #    self.x0 = 0
        #    self.y0 = 0
        #    self.xsize = 0
        #    self.ysize = 0
        #    self.sample_time = 0
        #    self.frame_time = 0


    def get_metadata(self, filename):
        """Collect basic metadata from filename that will be needed later

        Parameters
        ----------
        filename : str
            Name of fits file to examine
        """
        header = fits.getheader(filename)
        try:
            self.instrument = header['INSTRUME']
            self.x0 = header['SUBSTRT1']
            self.y0 = header['SUBSTRT2']
            self.xsize = header['SUBSIZE1']
            self.ysize = header['SUBSIZE2']
            self.sample_time = header['TSAMPLE']
            self.frame_time = header['TFRAME']
        except KeyError as e:
            print(e)

    def hot_dead_pixel_check(self, mean_image, comparison_image, hot_threshold=2., dead_threshold=0.1):
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
            Tuple of x,y coordinates of newly hot pixels

        deadpix : tuple
            Tuple of x,y coordinates of newly dead pixels
        """
        ratio = mean_image / comparison_image
        hotpix = np.where(ratio > hot_threshold)
        deadpix = np.where(ratio < dead_threshold)
        return hotpix, deadpix

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

        # Read in all slope images and place into a list
        slope_image_stack = pipeline_tools.image_stack(slope_files)

        # Calculate a mean slope image from the inputs
        slope_image, stdev_image = maths.mean_image(slope_image_stack, sigma_threshold=3)

        # Basic metadata that will be needed later
        self.get_metadata(slope_files[0])

        # Search for new hot/dead/noisy pixels----------------------------
        # Read in baseline mean slope image and stdev image
        #baseline_file = '{}_{}_baseline_slope_and_stdev_images.fits'.format(instrument, aperture)
        #baseline_filepath = os.path.join(self.output_dir, 'baseline/', baseline_file)
        #baseline_mean, baseline_stev = self.read_baseline_slope_image(baseline_filepath)
        print('baseline check removed for testing')
        baseline_mean = np.zeros((2048, 2048)) + 0.004
        baseline_stdev = np.zeros((2048, 2048)) + 0.004

        # Check the hot/dead pixel population for changes
        new_hot_pix, new_dead_pix = self.hot_dead_pixel_check(slope_image, baseline_mean)

        print('Found {} new hot pixels'.format(len(new_hot_pix)))
        print(len(new_hot_pix[0]))


        # Shift the coordinates to be in full frame coordinate system
        new_hot_pix = self.shift_to_full_frame(new_hot_pix)
        new_dead_pix = self.shift_to_full_frame(new_dead_pix)
        print('New hot/dead pixels should go? into an ascii file and then a table/image on the webpage?')

        # Check for any pixels that are significanly more noisy than
        # in the baseline stdev image
        new_noisy_pixels = self.noise_check(stdev_image, baseline_stdev)

        # Shift coordinates to be in full_frame coordinate system
        new_noisy_pixels = self.shift_to_full_frame(new_noisy_pixels)
        print('New noisy pixels should go where?')

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
        (amp_mean, amp_stdev, gauss_param, gauss_chisquared, double_gauss_params, double_gauss_chisquared) = \
         self.stats_by_amp(slope_image, amp_bounds, instrument)

        # Add the new statistics to the history file
        #for key in stats[0].keys():
        #    row = [key, amp_mean[key], amp_stdev[key], gauss_peak[key], gauss_peak_err[key],
        #           gauss_stdev[key], gauss_stdev_err[key]]
        #    history.add_row(row)

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

    def stats_by_amp(self, image, amps, instrument_name, chisq_threshold=1.1, plot=True):
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


            # If chisq is large enough to suggest a bad fit, save the
            # histogram and fit for later plotting
            #if gaussian_chi_squared[key] > chisq_threshold:
            #    where_do_we_send_this(key, bin_centers, hist, gauss_fit)

            # Double Gaussian fit only for full frame data (and only for
            # NIRISS at the moment.)
            if key == '5':
                if instrument_name.upper() in ['NIRISS', 'NIRCAM']:
                    initial_params = (np.max(hist), amp_mean, amp_stdev * 0.8,
                                      np.max(hist) / 7., amp_mean / 2., amp_stdev * 0.9)
                    double_gauss_params, double_gauss_sigma = maths.double_gaussian_fit(bin_centers, hist,
                                                                                        initial_params)
                    double_gaussian_params[key] = [(param, sig) for param, sig in zip(double_gauss_params,
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

                    # If chisq is large enough to suggest a bad fit, save the
                    # histogram and fit for later plotting
                    #if gaussian_chi_squared[key] > chisq_threshold:
                    #    where_do_we_send_this(key, bin_centers, hist, double_gauss_fit)
                    #    save_to_an_ascii_file_to_be_read_in_by_webb_app()
                    #    or_do_we_have_webb_app_plot_all_histograms()

        print('RESULTS OF STATS_BY_AMP:')
        print(amp_means, amp_stdevs, gaussian_params, gaussian_chi_squared, double_gaussian_params,
                double_gaussian_chi_squared)
        return (amp_means, amp_stdevs, gaussian_params, gaussian_chi_squared, double_gaussian_params,
                double_gaussian_chi_squared)


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
