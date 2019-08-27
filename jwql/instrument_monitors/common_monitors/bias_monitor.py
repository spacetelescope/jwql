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
from collections import OrderedDict
import numpy as np

from jwql.instrument_monitors import pipeline_tools
from jwql.instrument_monitors.common_monitors.dark_monitor import mast_query_darks
from jwql.utils import instrument_properties
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config, initialize_instrument_monitor, update_monitor_table

class Bias():
    """Class for executing the bias monitor.

    This class will search for new full-frame dark current files in 
    the file system for each instrument and will run the monitor on
    these files. The monitor will extract the 0th group from the new
    dark files and output the contents into a new file located in
    a working directory. It will then perform statistical measurements
    on these files before and after pipeline superbias subtraction in
    order to monitor the bias levels over time as well as ensure the
    pipeline superbias is sufficiently calibrating new data. Results 
    are all saved to database tables.

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
    """

    def __init__(self):
        """Initialize an instance of the ``Bias`` class.
        """

    def collapse_image(self, image):
        """Median-collapse the rows and columns of an image.

        Parameters
        ----------
        image : numpy.ndarray
            2D array on which to calculate statistics

        Returns
        -------
        collapsed_rows : numpy.ndarray
            1D array of the collapsed row values
        
        collapsed_columns : numpy.ndarray
            1D array of the collapsed column values
        """

        collapsed_rows = np.nanmedian(image, axis=1)
        collapsed_columns = np.nanmedian(image, axis=0)

        return collapsed_rows, collapsed_columns

    def extract_zeroth_group(self, filename):
        """Extracts the 0th group of a fits image and outputs it into
        a new fits file.
        
        Parameters
        ----------
        filename : str
            The fits file from which the 0th group will be extracted.

        Returns
        -------
        output_filename : str
            The full path to the output file
        """

        output_filename = os.path.join(self.data_dir,
            os.path.basename(filename).replace('.fits', '_0thgroup.fits'))
        
        # Write a new fits file containing the primary and science
        # headers from the input file, as well as the 0th group
        # data of the first integration
        if not os.path.isfile(output_filename):
            hdu = fits.open(filename)
            new_hdu = fits.HDUList([hdu['PRIMARY'], hdu['SCI']])
            new_hdu['SCI'].data = hdu['SCI'].data[0:1, 0:1, :, :]
            new_hdu.writeto(output_filename)

            # Close the fits files
            hdu.close()
            new_hdu.close()
            logging.info('\t{} created'.format(output_filename))
        else:
            logging.info('\t{} already exists'.format(output_filename))
            pass

        return output_filename

    def get_amp_medians(self, image, amps):
        """Calculates the median in the input image for each amplifier
        and for odd and even columns separately.

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

        for filename in file_list:
            logging.info('\tWorking on file: {}'.format(filename))

            # Get the uncalibrated 0th group data for this file
            uncal_data = fits.getdata(filename, 'SCI')[0, 0, :, :].astype(float)

            # Find amplifier boundaries so per-amp statistics can be calculated
            # TODO - THIS FILE DOESNT HAVE DQ ARRAY SO CANT IGNORE REFPIX
            _, amp_bounds = instrument_properties.amplifier_info(filename, omit_reference_pixels=False)
            logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

            # Calculate median values of each amplifier for odd/even columns 
            # in the uncal 0th group
            amp_meds = self.get_amp_medians(uncal_data, amp_bounds)
            logging.info('\tCalculated uncal image stats: {}'.format(amp_meds))

            # Run the uncal data through the pipeline superbias step
            steps_to_run = OrderedDict([('superbias', True)])
            processed_file = filename.replace('.fits', '_superbias.fits')
            if not os.path.isfile(processed_file):
                logging.info('\tRunning pipeline superbias correction on {}'.format(filename))
                processed_file = pipeline_tools.run_calwebb_detector1_steps(os.path.abspath(filename), steps_to_run)
                logging.info('\tPipeline superbias correction complete. Output: {}'.format(processed_file))
            else:
                logging.info('\tSuperbias-calibrated file {} already exists. Skipping call to pipeline.'
                             .format(processed_file))
                pass

            # Calculate median values of each amplifier for odd/even columns 
            # in the superbias-calibrated 0th group
            cal_data = fits.getdata(processed_file, 'SCI')[0, 0, :, :]
            amp_meds = self.get_amp_medians(cal_data, amp_bounds)
            logging.info('\tCalculated superbias-calibrated image stats: {}'.format(amp_meds))

            # Smooth the superbias-calibrated image to remove any odd/even 
            # or amplifier effects to allow for visual inspection of how well
            # the superbias correction performed
            # TODO - need to output png of this image?
            smoothed_cal_data = self.smooth_image(cal_data, amp_bounds)
            logging.info('\tSmoothed the superbias-calibrated image.')

            # Calculate the collapsed row and column values in the smoothed image
            # to see how well the superbias calibration performed
            collapsed_rows, collapsed_columns = self.collapse_image(smoothed_cal_data)
            logging.info('\tCalculated the collapsed row/column values of the smoothed '
                         'superbias-calibrated image.')

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details.
        """

        logging.info('Begin logging for bias_monitor')

        # Get the output directory
        self.output_dir = os.path.join(get_config()['outputs'], 'bias_monitor')

        # query_start is a TODO. Use the current time as the end time for MAST query
        self.query_start, self.query_end = 57357.0, Time.now().mjd  # a.k.a. Dec 1, 2015 == CV3

        # Loop over all instruments
        for instrument in ['nircam']:
            self.instrument = instrument

            # TODO Make a list of all possible apertures
            possible_apertures = ['NRCA1_FULL', 'NRCA2_FULL', 'NRCA3_FULL', 'NRCA4_FULL', 'NRCA5_FULL',
                                  'NRCB1_FULL', 'NRCB2_FULL', 'NRCB3_FULL', 'NRCB4_FULL', 'NRCB5_FULL']

            for aperture in possible_apertures[0:1]: #test

                logging.info('Working on aperture {} in {}'.format(aperture, instrument))
                self.aperture = aperture

                # Set up directories to store the copied data
                ensure_dir_exists(os.path.join(self.output_dir, 'data'))
                self.data_dir = os.path.join(self.output_dir,
                                             'data/{}_{}'.format(self.instrument.lower(),
                                                                 self.aperture.lower()))
                ensure_dir_exists(self.data_dir)

                # Query MAST for new dark files for this instrument/aperture
                logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))
                new_entries = mast_query_darks(instrument, aperture, self.query_start, self.query_end)
                logging.info('\tAperture: {}, new entries: {}'.format(self.aperture, len(new_entries)))

                # Save the 0th group image from each new file in the output directory;
                # some dont exist in JWQL filesystem.
                new_files = []
                for file_entry in new_entries[0:1]: #test
                    try:
                        filename = filesystem_path(file_entry['filename'])
                        uncal_filename = filename.replace('_dark', '_uncal')
                        if not os.path.isfile(uncal_filename):
                            logging.info('{} does not exist in JWQL filesystem, even though '
                                         '{} does'.format(uncal_filename, filename))
                            pass
                        else:
                            new_file = self.extract_zeroth_group(uncal_filename)
                            new_files.append(new_file)
                    except FileNotFoundError:
                        logging.info('{} does not exist in JWQL filesystem'.format(file_entry['filename']))
                        pass

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
            odd_med = np.nanmedian(image[y_start: y_end, x_start: x_end][:, ::2])
            even_med = np.nanmedian(image[y_start: y_end, x_start: x_end][:, 1::2])
            smoothed_image[y_start: y_end, x_start: x_end][:, ::2] = image[y_start: y_end, x_start: x_end][:, ::2] - odd_med
            smoothed_image[y_start: y_end, x_start: x_end][:, 1::2] = image[y_start: y_end, x_start: x_end][:, 1::2] - even_med

        return smoothed_image


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Bias()
    monitor.run()

    #update_monitor_table(module, start_time, log_file)
