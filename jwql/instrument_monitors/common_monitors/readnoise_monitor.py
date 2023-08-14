#! /usr/bin/env python

"""This module contains code for the readnoise monitor, which monitors
the readnoise levels in dark exposures as well as the accuracy of
the pipeline readnoise reference files over time.

For each instrument, the readnoise, technically the correlated double
sampling (CDS) noise, is found by calculating the standard deviation
through a stack of consecutive frame differences in each dark exposure.
The sigma-clipped mean and standard deviation in each of these readnoise
images, as well as histogram distributions, are recorded in the
``<Instrument>ReadnoiseStats`` database table.

Next, each of these readnoise images are differenced with the current
pipeline readnoise reference file to identify the need for new reference
files. A histogram distribution of these difference images, as well as
the sigma-clipped mean and standard deviation, are recorded in the
``<Instrument>ReadnoiseStats`` database table. A png version of these
difference images is also saved for visual inspection.

Author
------
    - Ben Sunnquist

Use
---
    This module can be used from the command line as such:

    ::

        python readnoise_monitor.py
"""

from collections import OrderedDict
import datetime
import logging
import os
import shutil

from astropy.io import fits
from astropy.stats import sigma_clip
from astropy.time import Time
from astropy.visualization import ZScaleInterval
import crds
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E348 (comparison to true)
import numpy as np  # noqa: E348 (comparison to true)
from pysiaf import Siaf  # noqa: E348 (comparison to true)
from sqlalchemy.sql.expression import and_  # noqa: E348 (comparison to true)

from jwql.database.database_interface import FGSReadnoiseQueryHistory, FGSReadnoiseStats  # noqa: E348 (comparison to true)
from jwql.database.database_interface import MIRIReadnoiseQueryHistory, MIRIReadnoiseStats  # noqa: E348 (comparison to true)
from jwql.database.database_interface import NIRCamReadnoiseQueryHistory, NIRCamReadnoiseStats  # noqa: E348 (comparison to true)
from jwql.database.database_interface import NIRISSReadnoiseQueryHistory, NIRISSReadnoiseStats  # noqa: E348 (comparison to true)
from jwql.database.database_interface import NIRSpecReadnoiseQueryHistory, NIRSpecReadnoiseStats  # noqa: E348 (comparison to true)
from jwql.database.database_interface import session, engine  # noqa: E348 (comparison to true)
from jwql.shared_tasks.shared_tasks import only_one, run_pipeline, run_parallel_pipeline  # noqa: E348 (comparison to true)
from jwql.instrument_monitors import pipeline_tools  # noqa: E348 (comparison to true)
from jwql.utils import instrument_properties, monitor_utils  # noqa: E348 (comparison to true)
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE  # noqa: E348 (comparison to true)
from jwql.utils.logging_functions import log_info, log_fail  # noqa: E348 (comparison to true)
from jwql.utils.monitor_utils import update_monitor_table  # noqa: E348 (comparison to true)
from jwql.utils.permissions import set_permissions  # noqa: E348 (comparison to true)
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config, copy_files  # noqa: E348 (comparison to true)


class Readnoise():
    """Class for executing the readnoise monitor.

    This class will search for new dark current files in the file
    system for each instrument and will run the monitor on these
    files. The monitor will create a readnoise image for each of the
    new dark files. It will then perform statistical measurements
    on these readnoise images, as well as their differences with the
    current pipeline readnoise reference file, in order to monitor
    the readnoise levels over time as well as ensure the pipeline
    readnoise reference file is sufficiently capturing the current
    readnoise behavior. Results are all saved to database tables.

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
        """Initialize an instance of the ``Readnoise`` class."""

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
        if self.instrument.upper() != 'MIRI':
            pipeline_steps['superbias'] = True
        else:
            pipeline_steps['superbias'] = False

        # Run the refpix step on all files
        pipeline_steps['refpix'] = True

        return pipeline_steps

    def file_exists_in_database(self, filename):
        """Checks if an entry for filename exists in the readnoise stats
        database.

        Parameters
        ----------
        filename : str
            The full path to the uncal filename.

        Returns
        -------
        file_exists : bool
            ``True`` if filename exists in the readnoise stats database.
        """

        query = session.query(self.stats_table)
        results = query.filter(self.stats_table.uncal_filename == filename).all()

        if len(results) != 0:
            file_exists = True
        else:
            file_exists = False

        session.close()
        return file_exists

    def get_amp_stats(self, image, amps):
        """Calculates the sigma-clipped mean and stddev, as well as the
        histogram stats in the input image for each amplifier.

        Parameters
        ----------
        image : numpy.ndarray
            2D array on which to calculate statistics.

        amps : dict
            Dictionary containing amp boundary coordinates (output from
            ``amplifier_info`` function)
            ``amps[key] = [(xmin, xmax, xstep), (ymin, ymax, ystep)]``

        Returns
        -------
        amp_stats : dict
            Contains the image statistics for each amp.
        """

        amp_stats = {}

        for key in amps:
            x_start, x_end, x_step = amps[key][0]
            y_start, y_end, y_step = amps[key][1]

            # Find sigma-clipped mean/stddev values for this amp
            amp_data = image[y_start: y_end: y_step, x_start: x_end: x_step]
            clipped = sigma_clip(amp_data, sigma=3.0, maxiters=5)
            amp_stats['amp{}_mean'.format(key)] = np.nanmean(clipped)
            amp_stats['amp{}_stddev'.format(key)] = np.nanstd(clipped)

            # Find the histogram stats for this amp
            n, bin_centers = self.make_histogram(amp_data)
            amp_stats['amp{}_n'.format(key)] = n
            amp_stats['amp{}_bin_centers'.format(key)] = bin_centers

        return amp_stats

    def get_metadata(self, filename):
        """Collect basic metadata from a fits file.

        Parameters
        ----------
        filename : str
            Name of fits file to examine.
        """

        header = fits.getheader(filename)

        try:
            self.detector = header['DETECTOR']
            self.read_pattern = header['READPATT']
            self.subarray = header['SUBARRAY']
            self.nints = header['NINTS']
            self.ngroups = header['NGROUPS']
            self.substrt1 = header['SUBSTRT1']
            self.substrt2 = header['SUBSTRT2']
            self.subsize1 = header['SUBSIZE1']
            self.subsize2 = header['SUBSIZE2']
            self.date_obs = header['DATE-OBS']
            self.time_obs = header['TIME-OBS']
            self.expstart = '{}T{}'.format(self.date_obs, self.time_obs)
        except KeyError as e:
            logging.error(e)

    def identify_tables(self):
        """Determine which database tables to use for a run of the
        readnoise monitor.
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}ReadnoiseQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}ReadnoiseStats'.format(mixed_case_name))

    def image_to_png(self, image, outname):
        """Outputs an image array into a png file.

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
        zscale = ZScaleInterval()
        vmin, vmax = zscale.get_limits(image)

        # Plot the image
        plt.figure(figsize=(12, 12))
        im = plt.imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
        plt.colorbar(im, label='Readnoise Difference (most recent dark - reffile) [DN]')
        plt.title('{}'.format(outname))

        # Save the figure
        plt.savefig(output_filename, bbox_inches='tight', dpi=200)
        set_permissions(output_filename)
        logging.info('\t{} created'.format(output_filename))

        return output_filename

    def make_crds_parameter_dict(self):
        """Construct a paramter dictionary to be used for querying CRDS
        for the current reffiles in use by the JWST pipeline.

        Returns
        -------
        parameters : dict
            Dictionary of parameters, in the format expected by CRDS.
        """

        parameters = {}
        parameters['INSTRUME'] = self.instrument.upper()
        parameters['DETECTOR'] = self.detector.upper()
        parameters['READPATT'] = self.read_pattern.upper()
        parameters['SUBARRAY'] = self.subarray.upper()
        parameters['DATE-OBS'] = datetime.date.today().isoformat()
        current_date = datetime.datetime.now()
        parameters['TIME-OBS'] = current_date.time().isoformat()

        return parameters

    def make_histogram(self, data):
        """Creates a histogram of the input data and returns the bin
        centers  and the counts in each bin.

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

        # Some images, e.g. readnoise images, will never have values below zero
        if (lower_thresh < 0) & (len(data[data < 0]) == 0):
            lower_thresh = 0.0

        # Make the histogram
        counts, bin_edges = np.histogram(data, bins='auto', range=(lower_thresh, upper_thresh))
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        return counts, bin_centers

    def make_readnoise_image(self, data):
        """Calculates the readnoise for the given input dark current
        ramp.

        Parameters
        ----------
        data : numpy.ndarray
            The input ramp data. The data shape is assumed to be a 4D
            array in DMS format (integration, group, y, x).

        Returns
        -------
        readnoise : numpy.ndarray
            The 2D readnoise image.
        """

        logging.info('\tCreating readnoise image')
        num_ints, num_groups, num_y, num_x = data.shape

        # Calculate the readnoise in slices to avoid memory issues on large files.
        slice_width = 20
        cols_idx = np.array(np.arange(num_x)[::slice_width])
        readnoise = np.zeros((num_y, num_x))
        for idx in cols_idx:
            # Create a stack of correlated double sampling (CDS) images using input
            # ramp data, combining multiple integrations if necessary.
            for integration in range(num_ints):
                if num_groups % 2 == 0:
                    cds = data[integration, 1::2, :, idx:idx + slice_width] - data[integration, ::2, :, idx:idx + slice_width]
                else:
                    # Omit the last group if the number of groups is odd
                    cds = data[integration, 1::2, :, idx:idx + slice_width] - data[integration, ::2, :, idx:idx + slice_width][:-1]

                if integration == 0:
                    cds_stack = cds
                else:
                    cds_stack = np.concatenate((cds_stack, cds), axis=0)

            # Calculate readnoise by taking the clipped stddev through CDS stack
            clipped = sigma_clip(cds_stack, sigma=3.0, maxiters=3, axis=0)
            readnoise_slice = np.ma.std(clipped, axis=0)

            # Add the readnoise in this slice to the full readnoise image
            readnoise[:, idx:idx + slice_width] = readnoise_slice

        return readnoise

    def most_recent_search(self):
        """Query the query history database and return the information
        on the most recent query for the given ``aperture_name`` where
        the readnoise monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the readnoise monitor was run.
        """

        query = session.query(self.query_table).filter(and_(self.query_table.aperture == self.aperture,
                self.query_table.run_monitor == True)).order_by(self.query_table.end_time_mjd).all()  # noqa: E712 (comparison to True)

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
        files_to_calibrate = []
        for file in file_list:
            processed_file = file.replace("uncal", "refpix")
            if not os.path.isfile(processed_file):
                files_to_calibrate.append(file)
        
        # Run the files through the necessary pipeline steps
        outputs = run_parallel_pipeline(files_to_calibrate, "uncal", "refpix", self.instrument)

        for filename in file_list:
            logging.info('\tWorking on file: {}'.format(filename))

            # Get relevant header information for this file
            self.get_metadata(filename)
            
            if filename in outputs:
                processed_file = outputs[filename]
            else:
                refpix_file = filename.replace("uncal", "refpix")
                if os.path.isfile(refpix_file):
                    processed_file = refpix_file
                else:
                    # Processed file not available
                    logging.warning("Calibrated file {} not found".format(refpix_file))
                    logging.warning("Skipping file {}".format(filename))
                    continue

            # Find amplifier boundaries so per-amp statistics can be calculated
            _, amp_bounds = instrument_properties.amplifier_info(processed_file, omit_reference_pixels=True)
            logging.info('\tAmplifier boundaries: {}'.format(amp_bounds))

            # Get the ramp data; remove first 5 groups and last group for MIRI to avoid reset/rscd effects
            cal_data = fits.getdata(processed_file, 'SCI', uint=False)
            if self.instrument == 'MIRI':
                cal_data = cal_data[:, 5:-1, :, :]

            # Make the readnoise image
            readnoise_outfile = os.path.join(self.data_dir, os.path.basename(processed_file.replace('.fits', '_readnoise.fits')))
            readnoise = self.make_readnoise_image(cal_data)
            # fits.writeto(readnoise_outfile, readnoise, overwrite=True)
            # logging.info('\tReadnoise image saved to {}'.format(readnoise_outfile))

            # Calculate the full image readnoise stats
            clipped = sigma_clip(readnoise, sigma=3.0, maxiters=5)
            full_image_mean, full_image_stddev = np.nanmean(clipped), np.nanstd(clipped)
            full_image_n, full_image_bin_centers = self.make_histogram(readnoise)
            logging.info('\tReadnoise image stats: {:.5f} +/- {:.5f}'.format(full_image_mean, full_image_stddev))

            # Calculate readnoise stats in each amp separately
            amp_stats = self.get_amp_stats(readnoise, amp_bounds)
            logging.info('\tReadnoise image stats by amp: {}'.format(amp_stats))

            # Get the current JWST Readnoise Reference File data
            parameters = self.make_crds_parameter_dict()
            try:
                reffile_mapping = crds.getreferences(parameters, reftypes=['readnoise'])
                readnoise_file = reffile_mapping['readnoise']
                logging.info('\tPipeline readnoise reffile is {}'.format(readnoise_file))
                pipeline_readnoise = fits.getdata(readnoise_file)
            except Exception as e:
                logging.warning('\tError retrieving pipeline readnoise reffile - assuming all zeros.')
                logging.warning('\tError {} was raised'.format(e))
                pipeline_readnoise = np.zeros(readnoise.shape)

            # Find the difference between the current readnoise image and the pipeline readnoise reffile, and record image stats.
            # Sometimes, the pipeline readnoise reffile needs to be cutout to match the subarray.
            if readnoise.shape != pipeline_readnoise.shape:
                try:
                    p_substrt1, p_substrt2 = fits.getheader(readnoise_file)['SUBSTRT1'], fits.getheader(readnoise_file)['SUBSTRT2']
                except KeyError:
                    p_substrt1, p_substrt2 = 1, 1
                x1, y1 = self.substrt1 - p_substrt1, self.substrt2 - p_substrt2
                x2, y2 = x1 + self.subsize1, y1 + self.subsize2
                pipeline_readnoise = pipeline_readnoise[y1:y2, x1:x2]
                if pipeline_readnoise.shape != readnoise.shape:
                    logging.warning('\tError cutting out pipeline readnoise - assuming all zeros.')
                    pipeline_readnoise = np.zeros(readnoise.shape)
            readnoise_diff = readnoise - pipeline_readnoise
            clipped = sigma_clip(readnoise_diff, sigma=3.0, maxiters=5)
            diff_image_mean, diff_image_stddev = np.nanmean(clipped), np.nanstd(clipped)
            diff_image_n, diff_image_bin_centers = self.make_histogram(readnoise_diff)
            logging.info('\tReadnoise difference image stats: {:.5f} +/- {:.5f}'.format(diff_image_mean, diff_image_stddev))

            # Save a png of the readnoise difference image for visual inspection
            logging.info('\tCreating png of readnoise difference image')
            readnoise_diff_png = self.image_to_png(readnoise_diff, outname=os.path.basename(readnoise_outfile).replace('.fits', '_diff'))

            # Construct new entry for this file for the readnoise database table.
            # Can't insert values with numpy.float32 datatypes into database
            # so need to change the datatypes of these values.
            readnoise_db_entry = {'uncal_filename': filename,
                                  'aperture': self.aperture,
                                  'detector': self.detector,
                                  'subarray': self.subarray,
                                  'read_pattern': self.read_pattern,
                                  'nints': self.nints,
                                  'ngroups': self.ngroups,
                                  'expstart': self.expstart,
                                  'readnoise_filename': readnoise_outfile,
                                  'full_image_mean': float(full_image_mean),
                                  'full_image_stddev': float(full_image_stddev),
                                  'full_image_n': full_image_n.astype(float),
                                  'full_image_bin_centers': full_image_bin_centers.astype(float),
                                  'readnoise_diff_image': readnoise_diff_png,
                                  'diff_image_mean': float(diff_image_mean),
                                  'diff_image_stddev': float(diff_image_stddev),
                                  'diff_image_n': diff_image_n.astype(float),
                                  'diff_image_bin_centers': diff_image_bin_centers.astype(float),
                                  'entry_date': datetime.datetime.now()
                                  }
            for key in amp_stats.keys():
                if isinstance(amp_stats[key], (int, float)):
                    readnoise_db_entry[key] = float(amp_stats[key])
                else:
                    readnoise_db_entry[key] = amp_stats[key].astype(float)

            # Add this new entry to the readnoise database table
            with engine.begin() as connection:
                connection.execute(self.stats_table.__table__.insert(), readnoise_db_entry)
            logging.info('\tNew entry added to readnoise database table')

            # Remove the raw and calibrated files to save memory space
            os.remove(filename)
            os.remove(processed_file)

    @log_fail
    @log_info
    @only_one(key='readnoise_monitor')
    def run(self):
        """The main method.  See module docstrings for further
        details.
        """

        logging.info('Begin logging for readnoise_monitor\n')

        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()['outputs'], 'readnoise_monitor')
        ensure_dir_exists(os.path.join(self.output_dir, 'data'))

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd

        # Loop over all instruments
        for instrument in JWST_INSTRUMENT_NAMES:
            self.instrument = instrument

            # Identify which database tables to use
            self.identify_tables()

            # Get a list of all possible apertures for this instrument
            siaf = Siaf(self.instrument)
            possible_apertures = list(siaf.apertures)

            for aperture in possible_apertures:

                logging.info('\nWorking on aperture {} in {}'.format(aperture, instrument))
                self.aperture = aperture

                # Locate the record of the most recent MAST search; use this time
                # (plus a buffer to catch any missing files from the previous
                # run) as the start time in the new MAST search.
                most_recent_search = self.most_recent_search()
                self.query_start = most_recent_search - 70

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
                checked_files = []
                for file_entry in new_entries:
                    output_filename = os.path.join(self.data_dir, file_entry['filename'].replace('_dark', '_uncal'))

                    # Sometimes both the dark and uncal name of a file is picked up in new_entries
                    if output_filename in checked_files:
                        logging.info('\t{} already checked in this run.'.format(output_filename))
                        continue
                    checked_files.append(output_filename)

                    # Dont process files that already exist in the readnoise stats database
                    file_exists = self.file_exists_in_database(output_filename)
                    if file_exists:
                        logging.info('\t{} already exists in the readnoise database table.'.format(output_filename))
                        continue

                    # Save any new uncal files with enough groups in the output directory; some dont exist in JWQL filesystem
                    try:
                        filename = filesystem_path(file_entry['filename'])
                        uncal_filename = filename.replace('_dark', '_uncal')
                        if not os.path.isfile(uncal_filename):
                            logging.info('\t{} does not exist in JWQL filesystem, even though {} does'.format(uncal_filename, filename))
                        else:
                            num_groups = fits.getheader(uncal_filename)['NGROUPS']
                            num_ints = fits.getheader(uncal_filename)['NINTS']
                            if instrument == 'miri':
                                total_cds_frames = int((num_groups - 6) / 2) * num_ints
                            else:
                                total_cds_frames = int(num_groups / 2) * num_ints
                            # Skip processing if the file doesnt have enough groups/ints to calculate the readnoise.
                            # MIRI needs extra since they omit the first five and last group before calculating the readnoise.
                            if total_cds_frames >= 10:
                                shutil.copy(uncal_filename, self.data_dir)
                                logging.info('\tCopied {} to {}'.format(uncal_filename, output_filename))
                                set_permissions(output_filename)
                                new_files.append(output_filename)
                            else:
                                logging.info('\tNot enough groups/ints to calculate readnoise in {}'.format(uncal_filename))
                    except FileNotFoundError:
                        logging.info('\t{} does not exist in JWQL filesystem'.format(file_entry['filename']))

                # Run the readnoise monitor on any new files
                if len(new_files) > 0:
                    self.process(new_files)
                    monitor_run = True
                else:
                    logging.info('\tReadnoise monitor skipped. {} new dark files for {}, {}.'.format(len(new_files), instrument, aperture))
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
                with engine.begin() as connection:
                    connection.execute(self.query_table.__table__.insert(), new_entry)
                logging.info('\tUpdated the query history table')

        logging.info('Readnoise Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = Readnoise()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
