#! /usr/bin/env python

"""This module contains code for the grating wheel monitor, which monitors
the grating wheel positions over time. This code has been adapted from bias_monitor.py

Author
------
    - Teagan King

Use
---
    This module can be used from the command line as such:

    ::

        python grating_monitor.py
"""

from collections import OrderedDict
import datetime
import logging
import os

from astropy.io import fits
from astropy.stats import sigma_clip
from astropy.time import Time
from astropy.visualization import ZScaleInterval
from jwql.edb.engineering_database import get_mnemonic
from jwql.edb.engineering_database import get_mnemonics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
from pysiaf import Siaf
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRSpecGratingQueryHistory, NIRSpecGratingStats
from jwql.instrument_monitors.common_monitors.dark_monitor import mast_query_darks
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, GRATING_TELEMETRY
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.monitor_utils import update_monitor_table
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config, initialize_instrument_monitor


class Grating():
    """Class for executing the grating wheel monitor.

    This class will search for a particular type of file in the file
    system for each instrument and will run the monitor on these files.
    The monitor will output the contents into a new file located in a
    working directory. It will then perform statistical measurements
    on these files in order to monitor the grating wheel telemetry
    over time. Results are all saved to database tables.

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
        Name of instrument used to collect the data.

    aperture : str
        Name of the aperture used (e.g. ``NRS1``).
    """

    def __init__(self):
        """Initialize an instance of the ``Grating`` class."""

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
        """Checks if an entry for filename exists in the grating stats
        database.

        Parameters
        ----------
        filename : str
            The full path to the uncal filename.

        Returns
        -------
        file_exists : bool
            ``True`` if filename exists in the grating stats database.
        """

        query = session.query(self.stats_table)
        results = query.filter(self.stats_table.uncal_filename == filename).all()

        if len(results) != 0:
            file_exists = True
        else:
            file_exists = False

        return file_exists

    def identify_tables(self):
        """Determine which database tables to use for a run of the grating wheel
        monitor.
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}GratingQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}GratingStats'.format(mixed_case_name))

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
        the grating wheel monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the grating wheel monitor was run.
        """
        query = session.query(self.query_table).filter(and_(self.query_table.aperture == self.aperture,
            self.query_table.run_monitor == True)).order_by(self.query_table.end_time_mjd).all()

        if len(query) == 0:
            query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'.format(self.aperture, query_result)))
        else:
            query_result = query[-1].end_time_mjd

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
        start_telemetry_time = Time(Time.now(), format='decimalyear') - 300  # Use telemetry from previous 30 days
        end_telemetry_time = Time(Time.now(), format='decimalyear')

        # Construct new entry for this file for the grating wheel database table.
        for telem in GRATING_TELEMETRY.keys():
            mnemonic = get_mnemonic(telem, start_telemetry_time, end_telemetry_time)
            other_telems = GRATING_TELEMETRY.keys()
            other_telems_dict = {}
            for telems in other_telems:
                other_telems_dict[telems.lower()] = 0.0  # Change to None
            other_telems_dict.pop(telem.lower())
            for time in mnemonic.data['MJD']:
                try:
                    grating_db_entry = {'aperture': self.aperture,
                                        'read_pattern': "temporary",
                                        'expstart': time,
                                        telem.lower(): float(mnemonic.data['euvalue'][np.where(mnemonic.data['MJD'] == time)]),
                                        'run_monitor': False,
                                        'entry_date': datetime.datetime.now()  # need slightly different times to add to database
                                        }
                    grating_db_entry.update(other_telems_dict)
                except TypeError:
                    logging.warning("may be skipping a value with same entry_date. grating_db_entry: {}".format(grating_db_entry))
                    continue   # if repeat entries?

                # Add this new entry to the grating database table
                self.stats_table.__table__.insert().execute(grating_db_entry)
                logging.info('\tNew entry added to grating database table: {}'.format(grating_db_entry))

        # FAILS BECAUSE LISTS OF FLOATS NOT FLOATS...
        # mnemonics = get_mnemonics(GRATING_TELEMETRY, start_telemetry_time, end_telemetry_time)
        # grating_db_entry = {'aperture': self.aperture,
        #                     'read_pattern': "temp",
        #                     'expstart': "temp",
        #                     'inrsh_gwa_adcmgain_time': mnemonics['INRSH_GWA_ADCMGAIN'].data['MJD'],
        #                     'inrsh_gwa_adcmgain': mnemonics['INRSH_GWA_ADCMGAIN'].data['euvalue'],
        #                     'inrsh_gwa_adcmoffset_time': mnemonics['INRSH_GWA_ADCMOFFSET'].data['MJD'],
        #                     'inrsh_gwa_adcmoffset': mnemonics['INRSH_GWA_ADCMOFFSET'].data['euvalue'],
        #                     'inrsh_gwa_motor_vref_time': mnemonics['INRSH_GWA_MOTOR_VREF'].data['MJD'],
        #                     'inrsh_gwa_motor_vref': mnemonics['INRSH_GWA_MOTOR_VREF'].data['euvalue'],
        #                     'inrsi_c_gwa_x_position_time': mnemonics['INRSI_C_GWA_X_POSITION'].data['MJD'],
        #                     'inrsi_c_gwa_x_position': mnemonics['INRSI_C_GWA_X_POSITION'].data['euvalue'],
        #                     'inrsi_c_gwa_y_position_time': mnemonics['INRSI_C_GWA_Y_POSITION'].data['MJD'],
        #                     'inrsi_c_gwa_y_position': mnemonics['INRSI_C_GWA_Y_POSITION'].data['euvalue'],
        #                     'run_monitor': False
        #                     }

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details."""

        logging.info('Begin logging for grating_monitor')

        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()['outputs'], 'grating_monitor')
        ensure_dir_exists(os.path.join(self.output_dir, 'data'))

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd

        self.instrument = 'nirspec'

        # Identify which database tables to use
        self.identify_tables()

        # Get a list of all possible full-frame apertures for this instrument
        siaf = Siaf(self.instrument)
        possible_apertures = [aperture for aperture in siaf.apertures if siaf[aperture].AperType == 'FULLSCA']

        for aperture in possible_apertures:
            logging.info('Working on aperture {} in {}'.format(aperture, self.instrument))
            self.aperture = aperture

            # Locate the record of most recent MAST search; use this time
            # (plus a 30 day buffer to catch any missing files from
            # previous run) as the start time in the new MAST search.
            most_recent_search = self.most_recent_search()
            self.query_start = most_recent_search - 30

            # Query MAST for new dark files for this instrument/aperture
            logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))
            new_entries = mast_query_darks(self.instrument, aperture, self.query_start, self.query_end)
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

                # Dont process files that already exist in the grating stats database
                file_exists = self.file_exists_in_database(output_filename)
                if file_exists:
                    logging.info('\t{} already exists in the grating database table.'.format(output_filename))
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
            # Run the grating monitor on any new files
            # NEED TO CHANGE SUCH THAT MONITOR IS UPDATED WHEN NEW TELEMETRY IS AVAILABLE?
            if len(new_files) == 0:  # WAS >  BUT NEED TO CHANGE!!
                self.process(new_files)
                monitor_run = True
            else:
                logging.info('\tGrating monitor skipped. {} new dark files for {}, {}.'.format(len(new_files), self.instrument, aperture))
                monitor_run = False

            # Update the query history
            new_entry = {'instrument': self.instrument,
                         'aperture': aperture,
                         'start_time_mjd': self.query_start,
                         'end_time_mjd': self.query_end,
                         'entries_found': len(new_entries),
                         'files_found': len(new_files),
                         'run_monitor': monitor_run,
                         'entry_date': datetime.datetime.now()}
            self.query_table.__table__.insert().execute(new_entry)
            logging.info('\tUpdated the query history table')

        logging.info('Grating Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Grating()
    monitor.run()

    update_monitor_table(module, start_time, log_file)
