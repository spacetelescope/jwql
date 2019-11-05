#! /usr/bin/env python

"""This module contains code for the bias monitor, which monitors
the bias levels in dark exposures as well as the performance of
the pipeline superbias subtraction over time.

For each instrument, the 0th group of full-frame dark exposures is
saved to a fits file. The median signal levels in these images are
recorded in the ``<Instrument>BiasStats`` database table for the
odd/even columns of each amp.

Next, these images are run through the jwst pipeline up through the
reference pixel correction step. These calibrated images are saved
to a fits file as well as a png file for visual inspection of the
quality of the pipeline calibration. The median-collpsed row and
column values, as well as the sigma-clipped mean and standard
deviation of these images, are recorded in the
``<Instrument>BiasStats`` database table.

Author
------
    - Ben Sunnquist

Use
---
    This module can be used from the command line as such:

    ::

        python bias_monitor.py
"""

import datetime
import logging
import os

from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from astropy.visualization import ZScaleInterval
from jwst.dq_init import DQInitStep
from jwst.group_scale import GroupScaleStep
from jwst.refpix import RefPixStep
from jwst.saturation import SaturationStep
from jwst.superbias import SuperBiasStep
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
from pysiaf import Siaf
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamBiasQueryHistory, NIRCamBiasStats
from jwql.instrument_monitors import pipeline_tools
from jwql.instrument_monitors.common_monitors.dark_monitor import mast_query_darks
from jwql.utils import instrument_properties
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config, initialize_instrument_monitor, update_monitor_table

class Bias():
    """Class for executing the bias monitor.

    This class will search for new full-frame dark current files in
    the file system for each instrument and will run the monitor on
    these files. The monitor will extract the 0th group from the new
    dark files and output the contents into a new file located in
    a working directory. It will then perform statistical measurements
    on these files before and after pipeline calibration in order to
    monitor the bias levels over time as well as ensure the pipeline
    superbias is sufficiently calibrating new data. Results are all
    saved to database tables.

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
        """Initialize an instance of the ``Bias`` class."""

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

        output_filename = os.path.join(self.data_dir, os.path.basename(filename).replace('.fits', '_0thgroup.fits'))

        # Write a new fits file containing the primary and science
        # headers from the input file, as well as the 0th group
        # data of the first integration
        if not os.path.isfile(output_filename):
            hdu = fits.open(filename)
            new_hdu = fits.HDUList([hdu['PRIMARY'], hdu['SCI']])
            new_hdu['SCI'].data = hdu['SCI'].data[0:1, 0:1, :, :]
            new_hdu.writeto(output_filename)
            hdu.close()
            new_hdu.close()
            set_permissions(output_filename)
            logging.info('\t{} created'.format(output_filename))
        else:
            logging.info('\t{} already exists'.format(output_filename))

        return output_filename

    def file_exists_in_database(self, filename):
        """Checks if an entry for filename exists in the bias stats
        database.

        Parameters
        ----------
        filename : str
            The full path to the uncal filename

        Returns
        -------
        file_exists : bool
            ``True`` if filename exists in the bias stats database
        """

        query = session.query(self.stats_table)
        results = query.filter(self.stats_table.uncal_filename == filename).all()

        if len(results) != 0:
            file_exists = True
        else:
            file_exists = False

        return file_exists

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
            ``amps[key] = [(xmin, xmax, xstep), (ymin, ymax, ystep)]``

        Returns
        -------
        amp_medians : dict
            Median values for each amp. Keys are ramp numbers as
            strings with even/odd designation (e.g. ``'1_even'``)
        """

        amp_medians = {}

        for key in amps:
            x_start, x_end, x_step = amps[key][0]
            y_start, y_end, y_step = amps[key][1]

            # Find median value of both even and odd columns for this amp
            amp_med_even = np.nanmedian(image[y_start: y_end, x_start: x_end][:, 1::2])
            amp_medians['amp{}_even_med'.format(key)] = amp_med_even
            amp_med_odd = np.nanmedian(image[y_start: y_end, x_start: x_end][:, ::2])
            amp_medians['amp{}_odd_med'.format(key)] = amp_med_odd

        return amp_medians

    def identify_tables(self):
        """Determine which database tables to use for a run of the bias
        monitor.
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}BiasQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}BiasStats'.format(mixed_case_name))

    def image_to_png(self, image, outname):
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

            plt.savefig(output_filename, bbox_inches='tight', dpi=200)
            set_permissions(output_filename)
            logging.info('\t{} created'.format(output_filename))
        else:
            logging.info('\t{} already exists'.format(output_filename))

        return output_filename

    def most_recent_search(self):
        """Query the query history database and return the information
        on the most recent query for the given ``aperture_name`` where
        the bias monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the bias monitor was run.
        """

        sub_query = session.query(
            self.query_table.aperture,
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
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'.format(self.aperture, query_result)))
        elif query_count > 1:
            raise ValueError('More than one "most recent" query?')
        else:
            query_result = query[0].end_time_mjd

        return query_result

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

            # Skip processing if an entry for this file already exists in
            # the bias stats database.
            file_exists = self.file_exists_in_database(filename)
            if file_exists:
                logging.info('\t{} already exists in the bias database table.'.format(filename))
                continue

            # Get the exposure start time of this file
            expstart = '{}T{}'.format(fits.getheader(filename, 0)['DATE-OBS'], fits.getheader(filename, 0)['TIME-OBS'])

            # Determine if the file needs group_scale in pipeline run
            read_pattern = fits.getheader(filename, 0)['READPATT']
            if read_pattern not in pipeline_tools.GROUPSCALE_READOUT_PATTERNS:
                group_scale = False
            else:
                group_scale = True

            # Run the file through the pipeline up through the refpix step
            logging.info('\tRunning pipeline on {}'.format(filename))
            processed_file = self.run_early_pipeline(filename, odd_even_rows=False, odd_even_columns=True, use_side_ref_pixels=True, group_scale=group_scale)
            logging.info('\tPipeline complete. Output: {}'.format(processed_file))

            # Find amplifier boundaries so per-amp statistics can be calculated
            _, amp_bounds = instrument_properties.amplifier_info(processed_file, omit_reference_pixels=True)
            logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

            # Get the uncalibrated 0th group data for this file
            uncal_data = fits.getdata(filename, 'SCI')[0, 0, :, :].astype(float)

            # Calculate the uncal median values of each amplifier for odd/even columns
            amp_medians = self.get_amp_medians(uncal_data, amp_bounds)
            logging.info('\tCalculated uncalibrated image stats: {}'.format(amp_medians))

            # Calculate image statistics and the collapsed row/column values
            # in the calibrated image
            cal_data = fits.getdata(processed_file, 'SCI')[0, 0, :, :]
            dq = fits.getdata(processed_file, 'PIXELDQ')
            mean, median, stddev = sigma_clipped_stats(cal_data[dq==0], sigma=3.0, maxiters=5)
            logging.info('\tCalculated calibrated image stats: {:.3f} +/- {:.3f}'.format(mean, stddev))
            collapsed_rows, collapsed_columns = self.collapse_image(cal_data)
            logging.info('\tCalculated collapsed row/column values of calibrated image.')

            # Save a png of the calibrated image for visual inspection
            logging.info('\tCreating png of calibrated image')
            output_png = self.image_to_png(cal_data, outname=os.path.basename(processed_file).replace('.fits',''))

            # Construct new entry for this file for the bias database table.
            # Can't insert values with numpy.float32 datatypes into database
            # so need to change the datatypes of these values.
            bias_db_entry = {'aperture': self.aperture,
                             'uncal_filename': filename,
                             'cal_filename': processed_file,
                             'cal_image': output_png,
                             'expstart': expstart,
                             'mean': float(mean),
                             'median': float(median),
                             'stddev': float(stddev),
                             'collapsed_rows': collapsed_rows.astype(float),
                             'collapsed_columns': collapsed_columns.astype(float),
                             'entry_date': datetime.datetime.now()
                            }
            for key in amp_medians.keys():
                bias_db_entry[key] = float(amp_medians[key])

            # Add this new entry to the bias database table
            self.stats_table.__table__.insert().execute(bias_db_entry)
            logging.info('\tNew entry added to bias database table: {}'.format(bias_db_entry))

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details."""

        logging.info('Begin logging for bias_monitor')

        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()['outputs'], 'bias_monitor')
        ensure_dir_exists(os.path.join(self.output_dir, 'data'))

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd

        # Loop over all instruments
        for instrument in ['nircam']:
            self.instrument = instrument

            # Identify which database tables to use
            self.identify_tables()

            # Get a list of all possible full-frame apertures for this instrument
            siaf = Siaf(self.instrument)
            possible_apertures = [aperture for aperture in siaf.apertures if siaf[aperture].AperType=='FULLSCA']

            for aperture in possible_apertures:

                logging.info('Working on aperture {} in {}'.format(aperture, instrument))
                self.aperture = aperture

                # Locate the record of the most recent MAST search; use this time
                # (plus a 30 day buffer to catch any missing files from the previous
                # run) as the start time in the new MAST search.
                most_recent_search = self.most_recent_search()
                self.query_start = most_recent_search - 30

                # Query MAST for new dark files for this instrument/aperture
                logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))
                new_entries = mast_query_darks(instrument, aperture, self.query_start, self.query_end)
                logging.info('\tAperture: {}, new entries: {}'.format(self.aperture, len(new_entries)))

                # Set up a directory to store the data for this aperture
                self.data_dir = os.path.join(self.output_dir, 'data/{}_{}'.format(self.instrument.lower(), self.aperture.lower()))
                if len(new_entries) > 0:
                    ensure_dir_exists(self.data_dir)

                # Save the 0th group image from each new file in the output directory;
                # some dont exist in JWQL filesystem.
                new_files = []
                for file_entry in new_entries:
                    try:
                        filename = filesystem_path(file_entry['filename'])
                        uncal_filename = filename.replace('_dark', '_uncal')
                        if not os.path.isfile(uncal_filename):
                            logging.info('\t{} does not exist in JWQL filesystem, even though {} does'.format(uncal_filename, filename))
                        else:
                            new_file = self.extract_zeroth_group(uncal_filename)
                            new_files.append(new_file)
                    except FileNotFoundError:
                        logging.info('\t{} does not exist in JWQL filesystem'.format(file_entry['filename']))

                # Run the bias monitor on any new files
                if len(new_files) > 0:
                    self.process(new_files)
                    monitor_run = True
                else:
                    logging.info('\tBias monitor skipped. {} new dark files for {}, {}.'.format(len(new_files), instrument, aperture))
                    monitor_run = False

                # Update the query history
                new_entry = {'instrument': instrument,
                             'aperture': aperture,
                             'start_time_mjd': self.query_start,
                             'end_time_mjd': self.query_end,
                             'entries_found': len(new_entries),
                             'files_found': len(new_files),
                             'run_monitor': monitor_run,
                             'entry_date': datetime.datetime.now()}
                self.query_table.__table__.insert().execute(new_entry)
                logging.info('\tUpdated the query history table')

        logging.info('Bias Monitor completed successfully.')

    def run_early_pipeline(self, filename, odd_even_rows=False, odd_even_columns=True,
                           use_side_ref_pixels=True, group_scale=False):
        """Runs the early steps of the jwst pipeline (dq_init, saturation,
        superbias, refpix) on uncalibrated files and outputs the result.

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

        output_filename = filename.replace('_uncal', '').replace('.fits', '_superbias_refpix.fits')

        if not os.path.isfile(output_filename):
            # Run the group_scale and dq_init steps on the input file
            if group_scale:
                model = GroupScaleStep.call(filename)
                model = DQInitStep.call(model)
            else:
                model = DQInitStep.call(filename)

            # Run the saturation and superbias steps
            model = SaturationStep.call(model)
            model = SuperBiasStep.call(model)

            # Run the refpix step and save the output
            model = RefPixStep.call(model, odd_even_rows=odd_even_rows, odd_even_columns=odd_even_columns, use_side_ref_pixels=use_side_ref_pixels)
            model.save(output_filename)
            set_permissions(output_filename)
        else:
            logging.info('\t{} already exists'.format(output_filename))

        return output_filename


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Bias()
    monitor.run()

    update_monitor_table(module, start_time, log_file)
