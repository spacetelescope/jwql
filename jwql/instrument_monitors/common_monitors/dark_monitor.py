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

import numpy as np

from astropy.stats import sigma_clip
from astropy.time import Time
from jwst import datamodels

from jwql.instrument_monitors import pipeline_tools
from jwql.jwql_monitors import monitor_mast
from jwql.utils import maths, instrument_properties
from jwql.utils.utils import download_mast_data, copy_from_filesystem, get_config, filesystem_path, JWST_INSTRUMENTS, JWST_DATAPRODUCTS


class Dark():
    def __init__(self, new_dark_threshold=10):
        """
        Parameters
        ----------
        new_dark_threshold : int
            Minimum number of new dark current files needed in order to
            run the dark current monitor.
        """
        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'monitor_darks')
        history_file = os.path.join(output_dir, 'mast_query_history.txt')

        # Use the current time as the end time for MAST query
        current_time = Time.now().mjd

        # Open file containing history of queries
        past_queries = ascii.read(history_file)

        # Loop over instrument/aperture combinations, and query MAST for new files
        for row in past_queries:
            starting_time = Time(row['Last_query']).mjd
            new_entries = mast_query_darks(row['Instrument'], row['Aperture'], starting_time, current_time)

            # Check to see if there are enough for
            # the monitor's signal-to-noise requirements
            if len(new_entries) >= new_dark_threshold:
                # Get full paths to the files
                new_filenames = [filesystem_path(file_entry['filename']) for file_entry in new_entries]

                # Copy files from filesystem
                copied, not_copied = copy_from_filesystem(new_filenames, self.output_dir)

                # Short-term fix: if some of the files from the query are not
                # in the filesystem, try downloading them from MAST
                uncopied_basenames = [os.path.basename(infile) for infile in not_copied]
                uncopied_results = [entry if entry['filename'] in uncopied_basenames for entry in new_entries]
                download_mast_data(uncopied_results, self.output_dir)

                # Run the dark monitor
                dark_files = [os.path.join(self.output_dir, filename) for filename in new_filenames]
                self.run(dark_files, row['Instrument'], row['Aperture'])

                # Update the query history for the next call
                specific_query['Last_query'] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                print(("Dark monitor skipped. {} new dark files for {}, {}. {} new files are "
                       "required to run dark current monitor.").format(len(new_entries),
                                                                       row['Instrument'],
                                                                       row['Aperture'],
                                                                       new_dark_threshold))
        logging.info('Dark Monitor completed successfully.')

    def find_amp_boundaries(self, data):
        """Find the row/column numbers corresponding to the boundaries of each amplifier in
        the input file

        data is a datamodel instance

        NIRCam: subarrays are 1 amp (except grism stripe which can be 1 or 4)
        """
        x0 = data.meta.subarray.xstart
        y0 = data.meta.subarray.ystart
        xsize = data.meta.subarray.xsize
        ysize = data.meta.subarray.ysize

        # There is no keyword specifying number of amps used.
        # Calculate from frametime and array size
        sample_time = data.meta.exposure.sample_time
        frame_time = data.meta.exposure.frame_time
        num_amps = number_of_amps(frame_time, sample_time, xsize, ysize)

        # Get the amp boundaries in full frame coordinates
        amp_boundaries = NOMINAL_AMP_BOUNDARIES[data.meta.instrument.name]

        # Shift the amp boundaries into the coordinate system of the
        # aperture of this file
        if num_amps == 1:
            amp_bounds = {'lower_left': ([0], [0]), 'upper_right': ([xsize], [ysize])}
        elif num_amps == 4:
            lower_left_x = amp_boundaries['lower_left']
            amp_bounds = {'lower_left': ([], []), 'upper_right': ([], [])}
        else:
            print('is this case possible with any of the instruments?')
        return amp_bounds

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

    def number_of_amps(frametime, sample_time, array_x_dim, array_y_dim):
        """Calculate the number of amplifiers used to collect the data
        from the array size and exposure time of a single frame
        (This is needed because there is no header keyword specifying
        how many amps were used.)
        """
        if fullframe:
            num_amps = 4
        else:
            if subarray_name not in ['SUBGRISMSTRIPE64', 'SUBGRISMSTRIPE128', 'SUBGRISMSTRIPE256']:
                num_amps = 1
            else:
                # These are the tougher cases. Subarrays that can be
                # used with multiple amp combinations

                # Compare the given frametime with the calculated frametimes
                # using 4 amps or 1 amp.
                amp4_time = instrument_properties.calc_frame_time(instrument, aperture, xdim, ydim,
                                                                  sample_time, amps)
                amp1_time = instrument_properties.calc_frame_time(instrument, aperture, xdim, ydim,
                                                                  sample_time, amps)
                if amp4_time == frametime:
                    num_amps = 4
                elif amp1_time == framtime:
                    num_amps = 1
                else:
                    raise ValueError(("Unable to determine number of amps used for exposure. 4-amp frametime"
                                      "is {}. 1-amp frametime is {}. Reported frametime is {}.")
                                     .format(amp4_time, amp1_time, frametime))
        return num_amps

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

        # Make sure dark subtraction is skipped on dark current files
        required_steps['dark_current'] = False

        but slightly different than the full list....(remove dark sub
            and what steps to skip for MIRI?)

        slope_files = []
        for filename in file_list:
            completed_steps = pipeline_tools.completed_pipeline_steps(filename)
            steps_to_run = pipeline_tools.steps_to_run(required_steps, completed_steps)

            # Run any remaining required pipeline steps
            if all(steps_to_run.values()):
                slope_files.append(filename)
            else:
                processed_file = run_calwebb_detector1(filename, steps_to_run)
                slope_files.append(processed_file)

        # Calculate a mean slope image from the inputs
        slope_image, stdev_image = maths.mean_image(slope_files, sigma_threshold=3)

        # Read in baseline mean slope image and stdev image
        baseline_file = '{}_{}_baseline_slope_and_stdev_images.fits'.format(instrument, aperture)
        baseline_filepath = os.path.join(self.output_dir, 'baseline/', baseline_file)
        with fits.open(baseline_file) as hdu:
            baseline_mean = hdu['MEAN'].data
            baseline_stdev = hdu['STDEV'].data

        # Check the hot/dead pixel population for changes
        new_hot_pix, new_dead_pix = self.hot_dead_pixel_check(slope_image, baseline_mean)
        print('New hot/dead pixels should go? into an ascii file and then a table/image on the webpage?')

        # Check for any pixels that are significanly more noisy than
        # in the baseline stdev image
        new_noisy_pixels = self.noise_check(stdev_image, baseline_stdev)

        # Read in the file containing historical image statistics
        stats_file = '{}_{}_dark_current_statistics.txt'.format(instrument, aperture)
        stats_filepath = os.path.join(self.output_dir, 'stats/', stats_file)
        history = ascii.read(stats_file)

        # Calculate mean and stdev values, and fit a Gaussian to the
        # histogram of the pixels in each amp
        (amp_mean, amp_stdev, gauss_peak, gauss_peak_err, gauss_stdev, gauss_stdev_err) =
        self.stats_by_amp(model.data, model.meta.instrument.name)

        # Add the new statistics to the history file
        for key in stats[0].keys():
            row = [key, amp_mean[key], amp_stdev[key], gauss_peak[key], gauss_peak_err[key],
                   gauss_stdev[key], gauss_stdev_err[key]]
            history.add_row(row)

    def stats_by_amp(self, image, instrument, plot=True):
        """Calculate statistics in the input image for each amplifier
        Warpper around calls to mean_stdev and gaussian_fit"""
        self.find_amp_boundaries(filename) - move this one level up
        statistics = {}
        amp_means = {}
        amp_stdevs = {}
        gaussian_peaks = {}
        gaussian_stdevs = {}
        gaussian_peak_errs = {}
        gaussian_stdev_errs = {}

        Add full image coords to the list of amp_boundaries, so that full frame stats are
        also calculated.
        for x, y in zip(x_boundaries, y_boundaries):
            amp_mean, amp_stdev = maths.mean_stdev(image[y_start: y_end, x_start: x_end])
            key = "{}_{}".format(x, y)
            amp_means[key] = amp_mean
            amp_stdevs[key] = amp_stdev

            lower_bound = (amp_mean - 7*amp_stdev)
            upper_bound = (amp_mean + 7*amp_stdev)
            hist, bin_edges = np.histogram(image[y_start: y_end, x_start: x_end], bins='auto',
                                           range=(lower_bound, upper_bound))
            bin_centers = bin_edges[0: -1] + (bin_edges[1:] - bin_edges[0: -1]) / 2.
            amplitude, peak, width = maths.gaussian1d_fit(bin_centers, hist)
            gaussian_peaks[key] = peak[0]
            gaussian_stdevs[key] = width[0]
            gaussian_peak_errs[key] = peak[1]
            gaussian_stdev_errs[key] = width[1]

            if full_frame:
                maths.double_gaussian_fit(bin_centers, hist, initial_params)

            # If requested, plot the histrogram(s) and Gaussian fits
            if plot:
                make_plot()
                save_somewhere_and_in_format_to_be_displayed_in_webapp()

        return (amp_means, amp_stdevs, gaussian_peaks, gaussian_stdevs, gaussian_peak_errs,
                gaussian_stdev_errs)


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
    history['Last_query'] = last_query_time
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
    for template_name in template_list:
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
