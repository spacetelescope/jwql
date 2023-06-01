#! /usr/bin/env python

"""This module runs the MIRI TA Monitor.

This module contains code for the MIRI TA monitor, which currently
queries MAST for TA aperture files, records their target locations
in RA/DEC, and the offset to the reference point for the relevant
ROI. It produces an image showing the full aperture and one with a
zoom in on the ROI.

Authors
-------

    - Mike Engesser

Use
---

    This module can be used from the command line as such:

    ::
        python MIRI_TA_Monitor.py
"""

# Native Imports
import datetime
import logging
import os
import shutil
from matplotlib import pyplot as plt
import matplotlib.patches as patches

# Third-Party Imports
from astropy.io import fits
from astropy.time import Time
import numpy as np
import pandas as pd
from pysiaf import Siaf
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import NIRCamTAQueryHistory, NIRISSTAQueryHistory, MIRITAQueryHistory
from jwql.database.database_interface import NIRCamTAStats, NIRISSTAStats, MIRITAStats
from jwql.database.database_interface import session
from jwql.jwql_monitors import monitor_mast
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_DATAPRODUCTS
from jwql.utils.logging_functions import configure_logging
from jwql.utils.logging_functions import log_info
from jwql.utils.logging_functions import log_fail
from jwql.utils.utils import ensure_dir_exists, get_config, filesystem_path
from jwst import datamodels

class MIRI_TA_Monitor():

    """Class for executing the MIRI TA monitor.

    This class will search for new (since the previous instance of the
    class) MIRI TA data in the file system. It will loop over
    instrument/aperture combinations and find the number of new files
    available. It will open each file and record the relevant telemetry,
    produce images of the ROIs, and then save results to database tables.

    Attributes
    ----------
    aperture : str
        Name of the aperture used for TA

    data : ndarray
        TA image data

    img : ndarray
        JWST datamodel of the data

    img_dir : str
        Path into which new image files will be stored

    instrument : str
        Name of instrument used to collect the TA

    offset : float
        Offset between the target and the reference point in arcseconds

    output_dir : str
        Path into which outputs will be placed

    query_start : float
        MJD start date to use for querying MAST

    query_end : float
        MJD end date to use for querying MAST

    RA_ref : float
        RA coordinate of the reference point

    DEC_ref : float
        DEC coordinate of the reference point

    RA_targ : float
        RA coordinate of the target

    DEC_targ : float
        DEC coordinate of the target

    query_table : sqlalchemy table
        Table containing the history of cosmic ray monitor queries to MAST
        for each instrument/aperture combination

    ROI_offset : int
        Offset in pixels of the ROI from the origin (0,0)

    stats_table : sqlalchemy table
        Table containing cosmic ray analysis results. Number and
        magnitude of cosmic rays, etc.

    x_targ : float
        X coordinate of the target

    y_targ: float
        Y coordinate of the target

    x : int
        X coordinate of the ROI upper-left corner

    y : int
        Y coordinate of the ROI upper-left corner

    x : float
        X coordinate of the reference point

    y_ref : float
        Y coordinate of the reference point


    Raises
    ------
    FileNotFoundError
        If encountering a file that is not located in its given
        target directory

    ValueError
        If encountering a file not following the JWST file naming
        convention

    ValueError
        If the most recent query search returns more than one entry
    """


    def __init__(self):
        """Initialize an instance of the ``MIRI_TA_Monitor`` class."""

        self.TA_names = ['MIRIM_TAMRS',
                         'MIRIM_TALRS',
                         'MIRIM_TA1065_UR',
                         'MIRIM_TA1065_CUR',
                         'MIRIM_TA1140_UR',
                         'MIRIM_TA1140_CUR'
                         'MIRIM_TA1550_UR',
                         'MIRIM_TA1550_CUR'
                         'MIRIM_TALYOT_UR',
                         'MIRIM_TALYOT_CUR']
        return


    def create_full_fig(self):
        """Produces an image showing the full aperture with the ROI overlaid."""

        mean, med, std = sigma_clipped_stats(self.data, sigma=5.0)
        vmin = med - 3*std
        vmax = med + 3*std

        fig, ax = plt.subplots(1,figsize=(10,10))
        ax.imshow(self.data,vmin=vmin,vmax=vmax, origin='lower',cmap='gist_heat')

        rect = patches.Rectangle((self.x[0],self.y[0]), self.x[1]-self.x[0],
                                 self.y[2]-self.y[0], edgecolor='lime', facecolor="none")
        ax.add_patch(rect)

        plt.scatter(x=self.x_ref, y=self.y_ref, marker='x',color='lime')
        #plt.colorbar()

        file_id = self.filename.split('/')[-1].split('.')[0]
        self.full_img = os.path.join(self.img_dir, file_id+'_full.png')

        plt.savefig(self.full_img, bbox_inches='tight')

        return


    def create_sub_fig(self):

        mean, med, std = sigma_clipped_stats(self.data, sigma=5.0)
        vmin = med - 3*std
        vmax = med + 3*std

        fig, ax = plt.subplots(1,figsize=(10,10))
        ax.imshow(self.data,vmin=vmin,vmax=vmax, origin='lower',cmap='gist_heat')


        rect = patches.Rectangle((self.x[0]-self.x_off,self.y[0]-self.y_off), self.x[1]-self.x[0],
                                 self.y[2]-self.y[0], edgecolor='lime', facecolor="none")
        ax.add_patch(rect)

        plt.scatter(x=self.x_ref-self.x_off, y=self.y_ref-self.y_off, marker='x',color='lime')

        #plt.colorbar()

        file_id = self.filename.split('/')[-1].split('.')[0]
        self.full_img = os.path.join(self.img_dir, file_id+'_full.png')

        plt.savefig(self.full_img, bbox_inches='tight')
        #plt.show()

        return


     def create_TA_figs(self):

        if self.subarray == 'FULL':
            self.create_full_fig()
            self.create_zoomed_fig()
        else:
            self.create_sub_fig()

        return


    def create_zoomed_fig(self):
        """Produces an image showing the ROI and the offset to the target."""

        stamp = self.data[self.roi_offset:,self.roi_offset:]

        mean, med, std = sigma_clipped_stats(stamp, sigma=5.0)
        vmin = med - 3*std
        vmax = med + 3*std


        fig, ax = plt.subplots(1,figsize=(10,10))
        ax.imshow(stamp, vmin=0, origin='lower',cmap='gist_heat')

        rect = patches.Rectangle((self.x[0]-self.roi_offset[0],
                                  self.y[0]-self.roi_offset[1]),
                                 self.x[1]-self.x[0],
                                 self.y[2]-self.y[0],
                                 linewidth=2,
                                 edgecolor='lime',
                                 facecolor="none")
        ax.add_patch(rect)

        plt.scatter(x=self.x_ref-self.roi_offset[0],
                    y=self.y_ref-self.roi_offset[1],
                    marker='x',color='lime')

        plt.scatter(x=self.x_targ-self.roi_offset[0],
                    y=self.y_targ-self.roi_offset[1],
                    marker='*', color='y')

        plt.plot([self.x_ref-self.roi_offset[0],
                  self.x_targ-self.roi_offset[0]],
                 [self.y_ref-self.roi_offset[1],
                  self.y_targ-self.roi_offset[1]],
                 '-',color='w')


        plt.annotate('Offset {:.6f} "'.format(self.offset),
                     (self.x_targ-self.roi_offset[0]+5,self.y_targ-self.roi_offset[1]+5),
                     c='lime', fontweight='bold')

        #plt.colorbar()

        file_id = self.filename.split('/')[-1].split('.')[0]
        self.zoom_img = os.path.join(self.img_dir, file_id+'_zoom.png')

        plt.savefig(self.zoom_img, bbox_inches='tight')

        return

    def identify_tables(self):
        """Determine which database tables to use for a run of the
        TA monitor.

        Uses the instrument variable to get the mixed-case instrument
        name, and uses that name to find the query and stats tables
        for that instrument.
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}TAQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}TAStats'.format(mixed_case_name))


    def get_apernames(self):
        """Get the TA aperture names for an instrument"""

        siaf = Siaf(self.instrument)

        apernames = []
        for aperture_name, aperture in siaf.apertures.items():
            if 'TA' in aperture_name:
                apernames.append(aperture_name)

        return apernames

    def most_recent_search(self):
        """Adapted from Dark Monitor (Bryan Hilbert)

        Query the query history database and return the information
        on the most recent query for the given ``aperture_name`` where
        the TA monitor was executed.

        Returns:
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST
            query where the TA monitor was run.
        """

        sub_query = session.query(self.query_table.exp_type,
                                  func.max(self.query_table.end_time_mjd).label('maxdate')
                                  ).group_by(self.query_table.exp_type).subquery('t2')

        # Note that "self.query_table.run_monitor == True" below is
        # intentional. Switching = to "is" results in an error in the query.
        query = session.query(self.query_table).join(
            sub_query,
            and_(
                self.query_table.exp_type == self.exp_type,
                self.query_table.end_time_mjd == sub_query.c.maxdate,
                self.query_table.run_monitor == True
            )
        ).all()

        query_count = len(query)
        if query_count == 0:
            query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'
                          .format(self.exp_type, query_result)))
        #elif query_count > 1:
         #   raise ValueError('More than one "most recent" query?')
        else:
            query_result = query[0].end_time_mjd

        return query_result


    def query_mast(self):
        """Use astroquery to search MAST for TA data

        Returns
        -------
        result : list
            List of dictionaries containing the query results
        """

        data_product = JWST_DATAPRODUCTS
        parameters = {"date_obs_mjd": {"min": self.query_start, "max": self.query_end}, "exp_type": self.exp_type}

        result = monitor_mast.instrument_inventory(self.instrument, data_product,
                                                   add_filters=parameters,
                                                   return_data=True)

        return result


    def process(self,tafile):

        """The main method for processing data. See module docstrings
        for further details.

        Parameters
        ----------
        tafile : str
            Path to the TA data being worked on
        """

        logging.info('Processing {}'.format(tafile))

        self.filename = tafile

        # get header information
        hdu = fits.open(tafile)

        head0 = hdu[0].header
        head1 = hdu[1].header
        self.data = hdu[1].data

        detector = head0['DETECTOR']
        end_time = head0['DATE-END']

        # get aperture name
        self.aperture = head0['APERNAME']
        self.subarray = head0['SUBARRAY']

        # get reference point for this aperture
        miri_siaf = Siaf('MIRI')
        self.x,self.y = miri_siaf[self.aperture].corners(to_frame='det')
        self.x_ref,self.y_ref=  miri_siaf[self.aperture].reference_point(to_frame='det')

        # determine aperture offsets for subarray
        if self.subarray != 'FULL':
            aper_x, aper_y = miri_siaf['MIRIM_'+self.subarray].corners(to_frame='det')
            x_off, y_off = aper_x[0], aper_y[0]
        else:
            x_off, y_off = self.x[0], self.y[0]

        self.roi_offset = [int(np.floor(x_off)), int(np.floor(y_off))]

        #get RA/DEC of ref point
        self.RA_ref = head1['RA_REF']
        self.DEC_ref = head1['DEC_REF']

        # open datamodel
        self.img = datamodels.open(tafile)

        # get coordinates of the target in pixels
        # inserting test point because targ values are wrong in header
        # to be fixed when data available

        # RA_targ = head0['TARG_RA']
        # DEC_targ = head0['TARG_DEC']

        # x_targ,y_targ = img.meta.wcs.transform('world', 'detector',RA_ref, DEC_ref)
        self.x_targ, self.y_targ = self.x_ref+5, self.y_ref+5
        self.RA_targ, self.DEC_targ = self.img.meta.wcs.transform('detector', 'world', self.x_targ, self.y_targ)


        # get offset of target from ref point
        offset_RA = (self.RA_ref-self.RA_targ)*3600
        offset_DEC = (self.DEC_ref-self.DEC_targ)*3600

        self.offset = np.sqrt(offset_RA**2 + offset_DEC**2)

        logging.info('Target RA: {}, Target DEC: {}'.format(self.RA_targ, self.DEC_targ))
        logging.info('TA offset: {} "'.format(self.offset))

        # create place to store files
        output_dir = os.path.join(get_config()['outputs'], 'MIRI_TA_monitor')
        data_dir =  os.path.join(output_dir,'data')
        ensure_dir_exists(data_dir)
        self.img_dir = os.path.join(data_dir, self.aperture)
        ensure_dir_exists(self.img_dir)

        if self.aperture in self.TA_names:

            self.create_TA_figs()

        # Insert new data into database
        try:
            TA_db_entry = {'cal_file_name': self.filename,
                           'obs_end_time': end_time,
                           'exp_type': self.exp_type,
                           'aperture': self.aperture,
                           'detector': detector,
                           'targx': self.x_targ,
                           'targy': self.y_targ,
                           'offset': self.offset,
                           'full_im_path': self.full_img,
                           'zoom_im_path': self.zoom_img
                           }

            self.stats_table.__table__.insert().execute(TA_db_entry)

            logging.info("Successfully inserted into database. \n")
        except:
            logging.info("Could not insert entry into database. \n")

        return


    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for additional info

        Queries MAST for new MIRI TA data and produces images of the ROI.
        Records the target coordinates and offset to the stats database for
        this monitor.
        """

        logging.info('Begin logging for MIRI TA Monitor')

        # Get list of exp_types
        exp_type_list = ['NRC_TACQ', 'MIR_TACQ', 'NRS_TACQ', 'NIS_TACQ']

        # Loop through TA apertures and process new data
        for exp_type in exp_type_list:

            self.exp_type = exp_type

            logging.info('Working on {}'.format(exp_type))

            # Get instrument name
            if exp_type == 'NRC_TACQ':
                self.instrument = 'nircam'
            elif exp_type == 'MIR_TACQ':
                self.instrument = 'miri'
            elif exp_type == 'NRS_TACQ':
                self.instrument = 'nirspec'
            elif exp_type == 'NIS_TACQ':
                self.instrument = 'niriss'

            # Identify which tables to use
            self.identify_tables()

            # We start by querying MAST for new data
            self.query_start = self.most_recent_search()
            self.query_end = Time.now().mjd

            new_entries = self.query_mast()

            TA_file_list = []
            for file_entry in new_entries['data']:
                try:
                    TA_file_list.append(filesystem_path(file_entry['filename']))
                except FileNotFoundError:
                    logging.info('\t{} not found in target directory'.format(file_entry['filename']))
                except ValueError:
                    logging.info(
                        '\tProvided file {} does not follow JWST naming conventions.'.format(file_entry['filename']))

            # Update Query history
            monitor_run = True

            new_entry = {'instrument': self.instrument,
                         'exp_type': self.exp_type,
                         'start_time_mjd': self.query_start,
                         'end_time_mjd': self.query_end,
                         'files_found': len(TA_file_list),
                         'run_monitor': monitor_run,
                         'entry_date': datetime.datetime.now()}
            self.query_table.__table__.insert().execute(new_entry)

            logging.info('\tUpdated the query history table')

        # ----------------------------------------------------------------
        # Temporary test block using local data
        TA_file_list = os.listdir('./TAdata/ta_data_for_testing/')

        for tafile in TA_file_list:
            if 'mirimage_cal' in tafile:
                try:
                    self.process('./TAdata/ta_data_for_testing/'+tafile)
                except FileNotFoundError:
                    logging.info('Could not find {}'.format(tafile))
                    pass
            else:
                pass
        #-----------------------------------------------------------------
        return


if __name__ == "__main__":

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    # Call the main function
    monitor = MIRI_TA_Monitor()
    monitor.run()
