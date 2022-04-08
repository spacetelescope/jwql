#! /usr/bin/env python

"""This module contains code for the bias monitor, which monitors
the bias levels in dark exposures as well as the performance of
the pipeline superbias subtraction over time.

For each instrument, the 0th group of full-frame dark exposures is
saved to a fits file. The median signal levels in these images are
recorded in the ``<Instrument>BiasStats`` database table for the
odd/even rows/columns of each amp.

Next, these images are run through the jwst pipeline up through the
reference pixel correction step. These calibrated images are saved
to a fits file as well as a png file for visual inspection of the
quality of the pipeline calibration. A histogram distribution of
these images, as well as their collapsed row/column and sigma-clipped
mean and standard deviation values, are recorded in the
``<Instrument>BiasStats`` database table.

Author
------
    - Ben Sunnquist
    - Maria A. Pena-Guerrero

Use
---
    This module can be used from the command line as such:

    ::

        python bias_monitor.py
"""

from collections import OrderedDict
import datetime
import logging
import os

from astropy.io import fits
from astropy.stats import sigma_clip, sigma_clipped_stats
from astropy.time import Time
from astropy.visualization import ZScaleInterval
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402 (module import not at top)
from mpl_toolkits.axes_grid1 import make_axes_locatable  # noqa: E402 (module import not at top)
import numpy as np  # noqa: E402 (module import not at top)
from pysiaf import Siaf  # noqa: E402 (module import not at top)
from sqlalchemy.sql.expression import and_  # noqa: E402 (module import not at top)

from jwql.database.database_interface import session  # noqa: E402 (module import not at top)
from jwql.database.database_interface import NIRCamBiasQueryHistory, NIRCamBiasStats, NIRISSBiasQueryHistory  # noqa: E402 (module import not at top)
from jwql.database.database_interface import NIRISSBiasStats, NIRSpecBiasQueryHistory, NIRSpecBiasStats  # noqa: E402 (module import not at top)
from jwql.instrument_monitors import pipeline_tools  # noqa: E402 (module import not at top)
from jwql.shared_tasks.shared_tasks import run_calwebb_detector1  # noqa: E402 (module import not at top)
from jwql.utils import instrument_properties, monitor_utils  # noqa: E402 (module import not at top)
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE  # noqa: E402 (module import not at top)
from jwql.utils.logging_functions import log_info, log_fail  # noqa: E402 (module import not at top)
from jwql.utils.monitor_utils import update_monitor_table  # noqa: E402 (module import not at top)
from jwql.utils.permissions import set_permissions  # noqa: E402 (module import not at top)
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config  # noqa: E402 (module import not at top)


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
        Path into which outputs will be placed.

    data_dir : str
        Path into which new dark files will be copied to be worked on.

    query_start : float
        MJD start date to use for querying MAST.

    query_end : float
        MJD end date to use for querying MAST.

    instrument : str
        Name of instrument used to collect the dark current data.

    aperture : str
        Name of the aperture used for the dark current (e.g.
        ``NRCA1_FULL``).
    """

    def __init__(self):
        """Initialize an instance of the ``Bias`` class."""

    def collapse_image(self, image):
        """Median-collapse the rows and columns of an image.

        Parameters
        ----------
        image : numpy.ndarray
            2D array on which to calculate statistics.

        Returns
        -------
        collapsed_rows : numpy.ndarray
            1D array of the collapsed row values.

        collapsed_columns : numpy.ndarray
            1D array of the collapsed column values.
        """

        collapsed_rows = np.nanmedian(image, axis=1)
        collapsed_columns = np.nanmedian(image, axis=0)

        return collapsed_rows, collapsed_columns

    def determine_pipeline_steps(self):
        """Determines the necessary JWST pipelines steps to run on a
        given dark file.

        Returns
        -------
        pipeline_steps : collections.OrderedDict
            The pipeline steps to run.
        """

        pipeline_steps = OrderedDict({})

        # Determine if the file needs group_scale step run
        if self.read_pattern not in pipeline_tools.GROUPSCALE_READOUT_PATTERNS:
            pipeline_steps['group_scale'] = False
        else:
            pipeline_steps['group_scale'] = True

        # Run the DQ step on all files
        pipeline_steps['dq_init'] = True

        # Only run the superbias step for NIR instruments
        if self.instrument != 'miri':
            pipeline_steps['superbias'] = True
        else:
            pipeline_steps['superbias'] = False

        # Run the refpix step on all files
        pipeline_steps['refpix'] = True

        return pipeline_steps

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
            The full path to the output file.
        """

        output_filename = os.path.join(self.data_dir, os.path.basename(filename).replace('.fits', '_0thgroup.fits'))

        # Write a new fits file containing the primary and science
        # headers from the input file, as well as the 0th group
        # data of the first integration
        hdu = fits.open(filename)
        new_hdu = fits.HDUList([hdu['PRIMARY'], hdu['SCI']])
        new_hdu['SCI'].data = hdu['SCI'].data[0:1, 0:1, :, :]
        new_hdu.writeto(output_filename, overwrite=True)
        hdu.close()
        new_hdu.close()
        set_permissions(output_filename)
        logging.info('\t{} created'.format(output_filename))

        return output_filename

    def file_exists_in_database(self, filename):
        """Checks if an entry for filename exists in the bias stats
        database.

        Parameters
        ----------
        filename : str
            The full path to the uncal filename.

        Returns
        -------
        file_exists : bool
            ``True`` if filename exists in the bias stats database.
        """

        query = session.query(self.stats_table)
        results = query.filter(self.stats_table.uncal_filename == filename).all()

        if len(results) != 0:
            file_exists = True
        else:
            file_exists = False

        session.close()
        return file_exists

    def get_amp_medians(self, image, amps):
        """Calculates the median in the input image for each amplifier
        and for odd and even rows/columns separately.

        Parameters
        ----------
        image : numpy.ndarray
            2D array on which to calculate statistics.

        amps : dict
            Dictionary containing amp boundary coordinates (output from
            ``amplifier_info`` function)
            ``amps[key] = [(xmin, xmax, xstep), (ymin, ymax, ystep)]``.

        Returns
        -------
        amp_medians : dict
            Median values for each amp. Keys are ramp numbers as
            strings with even/odd designation (e.g. ``'1_even'``).
        """

        amp_medians = {}

        for key in amps:
            x_start, x_end, x_step = amps[key][0]
            y_start, y_end, y_step = amps[key][1]

            # Find median value of both even and odd rows/columns for this amp
            if self.instrument != 'nircam':
                amp_med_even = np.nanmedian(image[y_start: y_end, x_start: x_end][1::2, :])
                amp_medians['amp{}_even_med'.format(key)] = amp_med_even
                amp_med_odd = np.nanmedian(image[y_start: y_end, x_start: x_end][::2, :])
                amp_medians['amp{}_odd_med'.format(key)] = amp_med_odd
            else:
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
            2D image array.

        outname : str
            The name given to the output png file.

        Returns
        -------
        output_filename : str
            The full path to the output png file.
        """

        output_filename = os.path.join(self.data_dir, '{}.png'.format(outname))

        # Get image scale limits
        z = ZScaleInterval()
        vmin, vmax = z.get_limits(image)

        # Plot the image
        plt.figure(figsize=(12, 12))
        ax = plt.gca()
        im = ax.imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
        ax.set_title(outname.split('_uncal')[0])

        # Make the colorbar
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.4)
        cbar = plt.colorbar(im, cax=cax)
        cbar.set_label('Signal [DN]')

        # Save the image
        plt.savefig(output_filename, bbox_inches='tight', dpi=200)
        set_permissions(output_filename)
        logging.info('\t{} created'.format(output_filename))

        return output_filename

    def make_histogram(self, data):
        """Creates a histogram of the input data and returns the bin
        centers and the counts in each bin.

        Parameters
        ----------
        data : numpy.ndarray
            The input data.

        Returns
        -------
        counts : numpy.ndarray
            The counts in each histogram bin.

        bin_centers : numpy.ndarray
            The histogram bin centers.
        """

        # Calculate the histogram range as that within 5 sigma from the mean
        data = data.flatten()
        clipped = sigma_clip(data, sigma=3.0, maxiters=5)
        mean, stddev = np.nanmean(clipped), np.nanstd(clipped)
        lower_thresh, upper_thresh = mean - 4 * stddev, mean + 4 * stddev

        # Make the histogram
        counts, bin_edges = np.histogram(data, bins='auto', range=(lower_thresh, upper_thresh))
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        return counts, bin_centers

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

        query = session.query(self.query_table).filter(and_(self.query_table.aperture == self.aperture,
                self.query_table.run_monitor == True)).order_by(self.query_table.end_time_mjd).all()  # noqa: E348 (comparison to true)

        if len(query) == 0:
            query_result = 59607.0  # a.k.a. Jan 28, 2022 == First JWST images (MIRI)
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'.format(self.aperture, query_result)))
        else:
            query_result = query[-1].end_time_mjd

        session.close()
        return query_result

    def process(self, file_list):
        """The main method for processing darks.  See module docstrings
        for further details.

        Parameters
        ----------
        file_list : list
            List of filenames (including full paths) to the dark current
            files.
        """

        for filename in file_list:
            logging.info('\tWorking on file: {}'.format(filename))

            # Get relevant header info for this file
            self.read_pattern = fits.getheader(filename, 0)['READPATT']
            self.expstart = '{}T{}'.format(fits.getheader(filename, 0)['DATE-OBS'], fits.getheader(filename, 0)['TIME-OBS'])

            # Run the file through the necessary pipeline steps
            pipeline_steps = self.determine_pipeline_steps()
            logging.info('\tRunning pipeline on {}'.format(filename))
            try:
                filepath = os.path.dirname(filename)
                filebase = os.path.basename(filename)
                processed_name = filebase[:filebase.rfind("_")] + "_refpix.fits"
                result = run_calwebb_detector1.delay(filebase, self.instrument, path=filepath)
                processed_dir result.get()
                processed_file = os.path.join(processed_dir, processed_name)
                logging.info('\tPipeline complete. Output: {}'.format(processed_file))
            except Exception as e:
                logging.info('\tPipeline processing failed for {}'.format(filename))
                logging.info('\tProcessing raised {}'.format(e))
                os.remove(filename)
                continue

            # Find amplifier boundaries so per-amp statistics can be calculated
            _, amp_bounds = instrument_properties.amplifier_info(processed_file, omit_reference_pixels=True)
            logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

            # Get the uncalibrated 0th group data for this file
            uncal_data = fits.getdata(filename, 'SCI')[0, 0, :, :].astype(float)

            # Calculate the uncal median values of each amplifier for odd/even columns
            amp_medians = self.get_amp_medians(uncal_data, amp_bounds)
            logging.info('\tCalculated uncalibrated image stats: {}'.format(amp_medians))

            # Calculate image statistics on the calibrated image
            cal_data = fits.getdata(processed_file, 'SCI')[0, 0, :, :]
            mean, median, stddev = sigma_clipped_stats(cal_data, sigma=3.0, maxiters=5)
            collapsed_rows, collapsed_columns = self.collapse_image(cal_data)
            counts, bin_centers = self.make_histogram(cal_data)
            logging.info('\tCalculated calibrated image stats: {:.3f} +/- {:.3f}'.format(mean, stddev))

            # Save a png of the calibrated image for visual inspection
            logging.info('\tCreating png of calibrated image')
            output_png = self.image_to_png(cal_data, outname=os.path.basename(processed_file).replace('.fits', ''))

            # Construct new entry for this file for the bias database table.
            # Can't insert values with numpy.float32 datatypes into database
            # so need to change the datatypes of these values.
            bias_db_entry = {'aperture': self.aperture,
                             'uncal_filename': filename,
                             'cal_filename': processed_file,
                             'cal_image': output_png,
                             'expstart': self.expstart,
                             'mean': float(mean),
                             'median': float(median),
                             'stddev': float(stddev),
                             'collapsed_rows': collapsed_rows.astype(float),
                             'collapsed_columns': collapsed_columns.astype(float),
                             'counts': counts.astype(float),
                             'bin_centers': bin_centers.astype(float),
                             'entry_date': datetime.datetime.now()
                             }
            for key in amp_medians.keys():
                bias_db_entry[key] = float(amp_medians[key])

            # Add this new entry to the bias database table
            self.stats_table.__table__.insert().execute(bias_db_entry)
            logging.info('\tNew entry added to bias database table: {}'.format(bias_db_entry))

            # Remove the raw and calibrated files to save memory space
            os.remove(filename)
            os.remove(processed_file)

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
        for instrument in ['nircam', 'niriss', 'nirspec']:
            self.instrument = instrument

            # Identify which database tables to use
            self.identify_tables()

            # Get a list of all possible full-frame apertures for this instrument
            siaf = Siaf(self.instrument)
            possible_apertures = [aperture for aperture in siaf.apertures if siaf[aperture].AperType == 'FULLSCA']

            for aperture in possible_apertures:

                logging.info('Working on aperture {} in {}'.format(aperture, instrument))
                self.aperture = aperture

                # Locate the record of most recent MAST search; use this time
                # (plus a 30 day buffer to catch any missing files from
                # previous run) as the start time in the new MAST search.
                most_recent_search = self.most_recent_search()
                self.query_start = most_recent_search - 30

                # Query MAST for new dark files for this instrument/aperture
                logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))
                new_entries = monitor_utils.mast_query_darks(instrument, aperture, self.query_start, self.query_end)

                # Exclude ASIC tuning data
                len_new_darks = len(new_entries)
                new_entries = monitor_utils.exclude_asic_tuning(new_entries)
                len_no_asic = len(new_entries)
                num_asic = len_new_darks - len_no_asic
                logging.info("\tFiltering out ASIC tuning files removed {} dark files.".format(num_asic))

                logging.info('\tAperture: {}, new entries: {}'.format(self.aperture, len(new_entries)))

                # Set up a directory to store the data for this aperture
                self.data_dir = os.path.join(self.output_dir, 'data/{}_{}'.format(self.instrument.lower(), self.aperture.lower()))
                if len(new_entries) > 0:
                    ensure_dir_exists(self.data_dir)

                # Get any new files to process
                new_files = []
                for file_entry in new_entries:
                    output_filename = os.path.join(self.data_dir, file_entry['filename'])
                    output_filename = output_filename.replace('_uncal.fits', '_uncal_0thgroup.fits').replace('_dark.fits', '_uncal_0thgroup.fits')

                    # Dont process files that already exist in the bias stats database
                    file_exists = self.file_exists_in_database(output_filename)
                    if file_exists:
                        logging.info('\t{} already exists in the bias database table.'.format(output_filename))
                        continue

                    # Save the 0th group image from each new file in the output directory; some dont exist in JWQL filesystem.
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


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = Bias()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
