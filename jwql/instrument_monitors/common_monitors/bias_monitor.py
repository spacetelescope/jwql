#! /usr/bin/env python

"""This module contains code for the bias monitor.

Author
------
    - Ben Sunnquist

Use
---
    This module can be used from the command line as such:

    ::

        python bias_monitor.py
"""

import logging
import os

from astropy.io import fits
from astropy.time import Time
import numpy as np

from jwql.instrument_monitors.common_monitors.dark_monitor import mast_query_darks
from jwql.utils import instrument_properties
from jwql.utils.utils import filesystem_path, initialize_instrument_monitor, update_monitor_table

class Bias():
    """Class for executing the bias monitor.
    """

    def __init__(self):
        """Initialize an instance of the ``Bias`` class.
        """

    def get_amp_medians(self, image, amps):
        """Calculates the median in the input image for each amplifier
        for odd and even columns separately.

        Parameters
        ----------
        image : numpy.ndarray
            2D array on which to calculate statistics

        amps : dict
            Dictionary containing amp boundary coordinates (output from
            ``amplifier_info`` function)
            ``amps[key] = [(xmin, ymin), (xmax, ymax)]``

        Returns
        -------
        amp_meds : dict
            Median values for each amp. Keys are ramp numbers as
            strings with even/odd designation (e.g. ``'1_even'``)
        """
        
        amp_meds = {}

        for key in amps:
            x_start, y_start = amps[key][0]
            x_end, y_end = amps[key][1]
            
            # Find median value of both even and odd columns for this amp
            amp_med_even = np.nanmedian(image[y_start: y_end, x_start: x_end][:, 1::2])
            amp_meds[key+'_even'] = amp_med_even
            amp_med_odd = np.nanmedian(image[y_start: y_end, x_start: x_end][:, ::2])
            amp_meds[key+'_odd'] = amp_med_odd

        logging.info('\tMean dark rate by amplifier: {}'.format(amp_meds))

        return amp_meds

    def process(self, file_list):
        """The main method for processing darks.  See module docstrings
        for further details.

        Parameters
        ----------
        file_list : list
            List of filenames (including full paths) to the dark current
            files
        """

        for f in file_list:
            logging.info('\tWorking on file: {}'.format(f))

            # Get the pipeline superbias data used to calibrate this file
            # PLACEHOLDER - needs to replace :crds// in sb_file path with actual path
            sb_file = fits.getheader(f, 0)['R_SUPERB']
            sb_data = fits.getdata(sb_file, 'SCI')

            # Get the uncalibrated 0th group data for this file
            uncal_file = f.replace('dark', 'uncal')
            if not os.path.isfile(uncal_file):
                raise FileNotFoundError(
                    '{} does not exist, even though {} does'.format(uncal_file, f))
            uncal_data = fits.getdata(uncal_file, 'SCI')[0][0]

            # Find amplifier boundaries so per-amp statistics can be calculated
            # PLACEHOLDER - THIS FILE DOESNT HAVE DQ ARRAY SO CRASHES, IT HAS PIXELDQ INSTEAD
            # DONT WANT TO INCLUDE REFPIX HERE
            number_of_amps, amp_bounds = instrument_properties.amplifier_info(f)
            logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

            # Calculate median values of each amplifier for odd/even columns 
            # in the uncal 0th group
            amp_meds = self.get_amp_medians(uncal_data, amp_bounds)

            # Find the difference between the uncal 0th group and the superbias
            diff = uncal_data - sb_data

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details.
        """

        logging.info('Begin logging for bias_monitor')

        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'bias_monitor')

        # query_start is a PLACEHOLDER. Use the current time as the end time for MAST query
        self.query_start, self.query_end = 57357.0, Time.now().mjd  # a.k.a. Dec 1, 2015 == CV3

        # Loop over all instruments
        for instrument in ['nircam']:
            self.instrument = instrument

            # PLACEHOLDER Make a list of all possible apertures
            possible_apertures = ['NRCA1_FULL','NRCA2_FULL','NRCA3_FULL','NRCA4_FULL','NRCA5_FULL',
                                  'NRCB1_FULL','NRCB2_FULL','NRCB3_FULL','NRCB4_FULL','NRCB5_FULL']

            for aperture in possible_apertures:

                logging.info('Working on aperture {} in {}'.format(aperture, instrument))

                # Query MAST for new dark files for this instrument/aperture
                logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))
                new_entries = mast_query_darks(instrument, aperture, self.query_start, self.query_end)
                logging.info('\tAperture: {}, new entries: {}'.format(self.aperture, len(new_entries)))

                # Get full paths to the uncal dark files; some dont exist in JWQL filesystem
                new_files = []
                for file_entry in new_entries:
                    try:
                        new_files.append(filesystem_path(file_entry['filename']))
                    except FileNotFoundError:
                        logging.info('{} does not exist in JWQL filesystem'.format(file_entry['filename']))

                # Run the dark monitor on any new files
                if len(new_files) != 0:
                    self.process(new_files)
                else:
                    logging.info(('\tBias monitor skipped. {} new dark files for {}, {}.').format(
                        len(new_files), instrument, aperture))

        logging.info('Bias Monitor completed successfully.')

    def smooth_image(self, image, amps):
        """Smooths an image to remove any amplifier and odd/even column
        dependencies, which are still present after pipeline superbias 
        subtraction.

        Parameters
        ----------
        image : numpy.ndarray
            2D image array to smooth

        amps : dict
            Dictionary containing amp boundary coordinates (output from
            ``amplifier_info`` function)
            ``amps[key] = [(xmin, ymin), (xmax, ymax)]``

        Returns
        -------
        smoothed_image : numpy.ndarray
            2D image array that has had any amplifier and odd/even
            column effects removed.
        """

        smoothed_image = np.zeros(np.shape(image))

        for key in amps:
            x_start, y_start = amps[key][0]
            x_end, y_end = amps[key][1]

            # Remove the median odd/even column values from this amplifier region
            odd_med = np.nanmedian(diff[y_start: y_end, x_start: x_end][:, ::2])
            even_med = np.nanmedian(diff[y_start: y_end, x_start: x_end][:, 1::2])
            smoothed_image[y_start: y_end, x_start: x_end][:, ::2] = image[y_start: y_end, x_start: x_end][:, ::2] - odd_med
            smoothed_image[y_start: y_end, x_start: x_end][:, 1::2] = image[y_start: y_end, x_start: x_end][:, 1::2] - even_med

        return smoothed_image

if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Bias()
    monitor.run()

    #update_monitor_table(module, start_time, log_file)
