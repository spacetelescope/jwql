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
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from astropy.visualization import ZScaleInterval
from collections import OrderedDict
from jwst.dq_init import DQInitStep
from jwst.group_scale import GroupScaleStep
from jwst.refpix import RefPixStep
from jwst.superbias import SuperBiasStep
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

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

    def image_stats(self, image):
        """Calculates sigma_clipped stats in an image.

        Parameters
        ----------
        image : numpy.ndarray
            2D image array

        Returns
        -------
        mean : float
            The sigma-clipped mean of the image
        stdev : float
            The sigma-clipped standard deviation of the image
        """

    def image_to_png(self, image, outname, title=''):
        """Ouputs an image array into a png file.

        Parameters
        ----------
        image : numpy.ndarray
            2D image array

        outname : str
            The name given to the output png file

        Returns
        -------
        output_filename : str
            The full path to the output png file
        """

        output_filename = os.path.join(self.data_dir, '{}.png'.format(outname))

        if not os.path.isfile(output_filename):
            # Get image scale limits
            z = ZScaleInterval()
            vmin, vmax = z.get_limits(image)

            # Plot the image
            plt.figure(figsize=(12,12))
            ax = plt.gca()
            im = ax.imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
            ax.set_title('{}'.format(outname))

            # Make the colorbar
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.4)
            cbar = plt.colorbar(im, cax=cax)
            cbar.set_label('Signal [DN]')

            # Save the plot
            plt.savefig(output_filename, bbox_inches='tight', dpi=200)
            logging.info('\t{} created'.format(output_filename))
        else:
            logging.info('\t{} already exists'.format(output_filename))
            pass

        return output_filename

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

            # Determine if the file needs group_scale in pipeline run
            read_pattern = fits.getheader(filename, 0)['READPATT']
            if read_pattern not in pipeline_tools.GROUPSCALE_READOUT_PATTERNS:
                group_scale = False
            else:
                group_scale = True

            # Run the file through the pipeline up through the refpix step
            logging.info('\tRunning pipeline on {}'.format(filename))
            processed_file = self.run_pipeline(filename, odd_even_rows=False, 
                odd_even_columns=True, use_side_ref_pixels=True, group_scale=group_scale)
            logging.info('\tPipeline complete. Output: {}'.format(processed_file))

            # Find amplifier boundaries so per-amp statistics can be calculated
            _, amp_bounds = instrument_properties.amplifier_info(processed_file, 
                omit_reference_pixels=True)
            logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

            # Get the uncalibrated 0th group data for this file
            uncal_data = fits.getdata(filename, 'SCI')[0, 0, :, :].astype(float)

            # Calculate the uncal median values of each amplifier for odd/even columns
            amp_meds = self.get_amp_medians(uncal_data, amp_bounds)
            logging.info('\tCalculated uncalibrated image stats: {}'.format(amp_meds))

            # Calculate image statistics and the collapsed row/column values 
            # in the calibrated image
            cal_data = fits.getdata(processed_file, 'SCI')[0, 0, :, :]
            mean, median, stddev = sigma_clipped_stats(cal_data, sigma=3.0, maxiters=5)
            logging.info('\tCalculated calibrated image stats: {:.3f} +/- {:.3f}'\
                .format(mean, stddev))
            collapsed_rows, collapsed_columns = self.collapse_image(cal_data)
            logging.info('\tCalculated collapsed row/column values of calibrated image.')

            # Save a png of the calibrated image for visual inspection
            output_png = self.image_to_png(cal_data, 
                outname=os.path.basename(processed_file).replace('.fits',''))

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

    def run_pipeline(self, filename, odd_even_rows=False, odd_even_columns=True, 
                     use_side_ref_pixels=True, group_scale=False):
        """Runs the early steps of the jwst pipeline (dq_init, superbias, 
        refpix) on uncalibrated files and outputs the result.
        
        Parameters
        ----------
        filename : str
            File on which to run the pipeline steps

        odd_even_rows : bool
            Option to treat odd and even rows separately during refpix step

        odd_even_columns : bools
            Option to treat odd and even columns separately during refpix step

        use_side_ref_pixels : bool
            Option to perform the side refpix correction during refpix step

        group_scale : bool
            Option to rescale pixel values to correct for instances where 
            on-board frame averaging did not result in the proper values

        Returns
        -------
        output_filename : str
            The full path to the calibrated file
        """

        output_filename = filename.replace('_uncal', '')\
                                  .replace('.fits', '_superbias_refpix.fits')
        
        if not os.path.isfile(output_filename):                       
            # Run the group_scale and dq_init steps on the input file
            if group_scale == True:
                model = GroupScaleStep.call(filename)
                model = DQInitStep.call(model)
            else:
                model = DQInitStep.call(filename)
            
            # Run the superbias step
            model = SuperBiasStep.call(model)

            # Run the refpix step and save the output
            model = RefPixStep.call(model, odd_even_rows=odd_even_rows, 
                odd_even_columns=odd_even_columns, use_side_ref_pixels=use_side_ref_pixels)
            model.save(output_filename)
        else:
            logging.info('\t{} already exists'.format(output_filename))
            pass

        return output_filename


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Bias()
    monitor.run()

    #update_monitor_table(module, start_time, log_file)
