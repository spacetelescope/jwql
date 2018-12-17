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
from jwst import datamodels

from jwql.utils import maths, instrument_properties


class Dark():
    def __init__(self):
        # Search for new files
        new_files = file_query(to_mast, or_to_filesystem)

        # If there are new files, separate by instrument, detector,
        # and aperture.
        for filename in new_files:
            info = get_info_through_header_or_filesystem_database

        # Check to see if there are enough for
        # the monitor's signal-to-noise requirements
        for instrument, detector, aperture in info:
            if number_of_matching_files > threshold_value:
                files_to_use = get_list_of_matching_files
                self.run(files_to_use)
            else:
                print(("Not enough new data for {}, {}, {} to run dark current monitor.")
                      .format(instrument, detector, aperture))
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

    def mean_slope_image(self, file_list, sigma_threshold=3):
        """Combine a list of slope images into a mean slope image,
        using sigma-clipping

        Parameters
        ----------
        file_list : list
            List of filenames to be included in the mean calculations

        sigma_threshold : int
            Number of sigma to use when sigma-clipping values in each
            pixel

        Returns
        -------
        mean_image : numpy.ndarray
            2D sigma-clipped mean image

        stdev_image : numpy.ndarray
            2D sigma-clipped standard deviation image
        """
        for i, input_file in enumerate(file_list):
            model = datamodels.open(input_file)
            image = model.data

            # Stack all inputs together into a single 3D image cube
            if i == 0:
                ndim_base = image.shape
                if len(ndim_base) == 3:
                    cube = copy.deepcopy(image)
                elif len(ndim_base) == 2:
                    cube = np.expand_dims(image, 0)

            ndim = image.shape
            if ndim_base[-2:] == ndim[-2:]:
                if len(ndim) == 2:
                    image = np.expand_dims(image, 0)
                elif len(ndim) > 3:
                    raise ValueError("4-dimensional input images not supported.")
                cube = np.vstack((cube, image))
            else:
                raise ValueError("Input images are of inconsistent size in x/y dimension.")

        # Create mean and standard deviation images, using sigma-
        # clipping on a pixel-by-pixel basis
        clipped_cube = sigma_clip(cube, sigma=sigma_threshold, axis=0, masked=False)
        mean_image = np.mean(clipped_cube, axis=0)
        std_image = np.nanstd(clipped_cube, axis=0)
        return mean_image, std_image

    def number_of_amps(frametime, sample_time, array_x_dim, array_y_dim):
        """Calculate the number of amplifiers used to collect the data
        from the array size and exposure time of a single frame
        (This is needed because there is no header keyword specifying
        how many amps were used.)
        """
        if fullframe:
            num_amps = 4
        else:
            if subarray_name not in []:
                num_amps = 1
            else:
                # These are the tougher cases. Subarrays that can be
                # used with multiple amp combinations

                # Compare the given frametime with the calculated frametimes
                # using 4 amps or 1 amp.
                amp4_time = instrument_properties.calc_frame_time(instrument, aperture, xdim, ydim, sample_time, amps)
                amp1_time = instrument_properties.calc_frame_time(instrument, aperture, xdim, ydim, sample_time, amps)
                if amp4_time == frametime:
                    num_amps = 4
                elif amp1_time == framtime:
                    num_amps = 1
                else:
                    raise ValueError(("Unable to determine number of amps used for exposure. 4-amp frametime"
                                      "is {}. 1-amp frametime is {}. Reported frametime is {}.")
                                     .format(amp4_time, amp1_time, frametime))
        return num_amps

    def run(self, file_list):
        """MAIN FUNCTION"""
        # First run calwebb_detector1 if necessary
        if inputs_are_raw:
            run_calwebb_detector1(input_files)
            slope_files = [pipeline_output_files]
        else:
            slope_files = file_list

        # Calculate a mean slope image from the inputs
        should we move mean_slope_image into utils? or maybe make a static method?
        could be useful for other monitors
        slope_image, stdev_image = self.mean_slope_image(slope_files, sigma_threshold=3)

        # Read in the file containing historical image statistics
        stats_file = somewhere_and_based_on_instrument_detector_aperture
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
            make_sure_later_plotter_can_handle_this_mix_of_amps()

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

            # If requested, plot the histrogram(s) and Gaussian fits
            if plot:
                make_plot()
                save_somewhere_and_in_format_to_be_displayed_in_webapp()

        return (amp_means, amp_stdevs, gaussian_peaks, gaussian_stdevs, gaussian_peak_errs,
                gaussian_stdev_errs)


if __name__ == '__main__':
    #logging.configure_logging()
    monitor = Dark()
