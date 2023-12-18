#! /usr/bin/env python

"""This module runs the TA Monitor for all instruments and observing modes.

This module contains code which currently
queries MAST for TA aperture files, records their target locations
in RA/DEC, and the offset to the reference point for the relevant
ROI. It produces an image showing the full aperture and one with a
zoom in on the ROI.

Authors
-------

    - Bryan Hilbert
    - Mike Engesser

Use
---

    This module can be used from the command line as such:

    ::
        python ta_monitor.py
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
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
import numpy as np
import pandas as pd
from photutils.centroids import (centroid_1dg, centroid_2dg, centroid_com, centroid_quadratic)
from pysiaf import Siaf
from pysiaf.utils import rotations
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

#from jwql.database.database_interface import NIRCamTAQueryHistory, NIRISSTAQueryHistory, MIRITAQueryHistory
#from jwql.database.database_interface import NIRCamTAStats, NIRISSTAStats, MIRITAStats
from jwql.database.database_interface import session
from jwql.edb.engdb_oss_msgs import EventLog
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_ABBREVIATIONS, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_INSTRUMENT_NAMES_SHORTHAND, JWST_DATAPRODUCTS
from jwql.utils.logging_functions import configure_logging
from jwql.utils.logging_functions import log_info
from jwql.utils.logging_functions import log_fail
from jwql.utils.monitor_utils import model_query_ta
from jwql.utils.utils import ensure_dir_exists, get_config, filesystem_path
from jwql.website.apps.jwql.models import RootFileInfo


TA_FAILURE_THRESHOLD = 5. # this is arbitrary. for testing only.

# for testing only
MIRI_NON_CORON_TA_APERTURES = ['MIRIM_TAMRS',
                         'MIRIM_TALRS',
                         'MIRIM_TABLOCK'
'MIRIM_TAFULL',
 'MIRIM_TAILLUM',
 'MIRIM_TABRIGHTSKY',
 'MIRIM_TASUB256',
 'MIRIM_TASUB128',
 'MIRIM_TASUB64',
 'MIRIM_TASLITLESSPRISM']


"""
                         'MIRIM_TA1065_UL',
                         'MIRIM_TA1065_UR',
                         'MIRIM_TA1065_LL',
                         'MIRIM_TA1065_LR',
                         'MIRIM_TA1065_CUL',
                         'MIRIM_TA1065_CUR',
                         'MIRIM_TA1065_CLL',
                         'MIRIM_TA1065_CLR'
                        'MIRIM_TA1140_UL',
 'MIRIM_TA1140_UR',
 'MIRIM_TA1140_LL',
 'MIRIM_TA1140_LR',
 'MIRIM_TA1140_CUL',
 'MIRIM_TA1140_CUR',
 'MIRIM_TA1140_CLL',
 'MIRIM_TA1140_CLR'
'MIRIM_TA1550_UL',
 'MIRIM_TA1550_UR',
 'MIRIM_TA1550_LL',
 'MIRIM_TA1550_LR',
 'MIRIM_TA1550_CUL',
 'MIRIM_TA1550_CUR',
 'MIRIM_TA1550_CLL',
 'MIRIM_TA1550_CLR'
'MIRIM_TALYOT_UL',
 'MIRIM_TALYOT_UR',
 'MIRIM_TALYOT_LL',
 'MIRIM_TALYOT_LR',
 'MIRIM_TALYOT_CUL',
 'MIRIM_TALYOT_CUR',
 'MIRIM_TALYOT_CLL',
 'MIRIM_TALYOT_CLR'
]
"""

"""For trending plots, model them on the code used for MSATA and WATA montiors, which have a slider to control date range, etc.
But what about these images that Mike creates below? Could we have each point on a trending plot act as a link to a page
that holds the images? Or have one page for each program ID's images? Or stack all the images into a single page that is
broken down by program ID?
"""

class FullROIImage():
    def __init__(self, data, positions, outfile='', outdir=''):
        """positions is a dictionary that holds the x, y, x_ref, y_ref, x_targ, and y_targ value
        """
        self.data = data
        self.positions = positions
        self.outdir = outdir
        self.outfile = outfile
        self.create()

    def create(self):
        mean, med, std = sigma_clipped_stats(self.data, sigma=5.0)
        vmin = med - 3 * std
        vmax = med + 3 * std

        fig, ax = plt.subplots(1, figsize=(10,10))
        ax.imshow(self.data, vmin=vmin, vmax=vmax, origin='lower', cmap='gist_heat')

        rect = patches.Rectangle((self.positions['x'][0], self.positions['y'][0]), self.positions['x'][1]-self.positions['x'][0],
                                 self.positions['y'][2]-self.positions['y'][0], edgecolor='lime', facecolor="none")
        ax.add_patch(rect)

        plt.scatter(x=self.positions['x_ref'], y=self.positions['y_ref'], marker='x',color='lime')
        #plt.colorbar()

        if not self.outfile:
            file_id = self.filename.split('/')[-1].split('.')[0]
            self.outfile = f'{file_id}_full.png'
        self.output_file = os.path.join(self.outdir, self.outfile)

        plt.savefig(self.output_file, bbox_inches='tight')

class ZoomedROIImage():
    def __init__(self, data, roi_offset, positions, outfile='', outdir=''):
        """positions is a dictionary that holds the x, y, x_ref, y_ref, x_targ, and y_targ value
        """
        self.data = data
        self.roi_offset = roi_offset
        self.positions = positions
        self.outdir = outdir
        self.outfile = outfile
        self.create()

    def create(self):
        """Produces an image showing the ROI and the offset to the target."""

        roi_offset_int = [int(np.floor(self.roi_offset[0])), int(np.floor(self.roi_offset[0]))]
        stamp = self.data[self.roi_offset_int:, self.roi_offset_int:]

        mean, med, std = sigma_clipped_stats(stamp, sigma=5.0)
        vmin = med - 3*std
        vmax = med + 3*std

        fig, ax = plt.subplots(1,figsize=(10,10))
        ax.imshow(stamp, vmin=0, origin='lower',cmap='gist_heat')

        rect = patches.Rectangle((self.positions['x'][0]-self.roi_offset[0],
                                  self.positions['y'][0]-self.roi_offset[1]),
                                 self.positions['x'][1]-self.positions['x'][0],
                                 self.positions['y'][2]-self.positions['y'][0],
                                 linewidth=2,
                                 edgecolor='lime',
                                 facecolor="none")
        ax.add_patch(rect)

        plt.scatter(x=self.positions['x_ref']-self.roi_offset[0],
                    y=self.positions['y_ref']-self.roi_offset[1],
                    marker='x',color='lime')

        plt.scatter(x=self.positions['x_targ']-self.roi_offset[0],
                    y=self.positions['y_targ']-self.roi_offset[1],
                    marker='*', color='y')

        plt.plot([self.positions['x_ref']-self.roi_offset[0],
                  self.positions['x_targ']-self.roi_offset[0]],
                 [self.positions['y_ref']-self.roi_offset[1],
                  self.positions['y_targ']-self.roi_offset[1]],
                 '-',color='w')


        plt.annotate('Offset {:.6f} "'.format(self.offset),
                     (self.positions['x_targ']-self.roi_offset[0]+5,self.positions['y_targ']-self.roi_offset[1]+5),
                     c='lime', fontweight='bold')

        #plt.colorbar()

        if not self.outfile:
            file_id = self.filename.split('/')[-1].split('.')[0]
            self.outfile = f'{file_id}_zoom.png'
        self.output_file = os.path.join(self.outdir, self.outfile)

        plt.savefig(self.output_file, bbox_inches='tight')


class SubROIImage():
    # it's actually not clear if the coronagraphy folks want images like these, or just the trending plot that
    # shows the offset values. Anyway, making these separate classes means we can potentially easily make them
    # for coronagraphic data.
    def __init__(self, data, positions, outfile='', outdir=''):
        """positions is a dictionary that holds the x, y, x_ref, y_ref, x_targ, and y_targ value
        """
        self.data = data
        self.positions = positions
        self.outdir = outdir
        self.outfile = outfile
        self.create()

    def create(self):
        mean, med, std = sigma_clipped_stats(self.data, sigma=5.0)
        vmin = med - 5 * std
        vmax = med + 5 * std



        print('In SubROIImage:')
        print('self.positions: ', self.positions)





        fig, ax = plt.subplots(1, figsize=(10, 10))
        ax.imshow(self.data, vmin=vmin, vmax=vmax, origin='lower',cmap='gist_heat')

        #rect = patches.Rectangle((self.positions['x'][0] - self.positions['x_off'], self.positions['y'][0] - self.positions['y_off']),
        #                          self.positions['x'][1] - self.positions['x'][0], self.positions['y'][2]-self.positions['y'][0],
        #                          edgecolor='lime', facecolor="none")
        minx = np.min(self.positions['x'])
        maxx = np.max(self.positions['x'])
        miny = np.min(self.positions['y'])
        maxy = np.max(self.positions['y'])

        # Subtract 0.49 in order to get the ROI into the coordinate system used by DMS (i.e. pixel 0,0 goes
        # from -0.5, -0.5 to 0.5,0.5). But use 0.49 rather than 0.5 because the rectangle seems to disappear
        # if it runs exactly along the outside of the array.
        rect = patches.Rectangle((minx - self.positions['x_off'] - 0.49, miny - self.positions['y_off'] - 0.49),
                                  maxx - minx, maxy - miny,
                                  edgecolor='lime', facecolor="none")
        ax.add_patch(rect)

        # Show the reference location
        plt.scatter(x=self.positions['x_ref'], y=self.positions['y_ref'],
                    marker='x', color='lime')
        # Show the GENTALOCATE centroid
        plt.scatter(x=self.positions['x_targ'], y=self.positions['y_targ'],
                    marker='o', color='red')

        #plt.colorbar()

        if not self.outfile:
            file_id = self.filename.split('/')[-1].split('.')[0]
            self.outfile = f'{file_id}_sub.png'
        self.output_file = os.path.join(self.outdir, self.outfile)

        plt.savefig(self.output_file, bbox_inches='tight')
        #plt.show()


class TargetInfo():
    """Class that contains metadata and target information for a given JWST file
    """
    def __init__(self, filename):
        self.filename = filename
        self.get_data()

    def get_data(self):
        with fits.open(self.filename) as hdulist:
            self.data = hdulist['SCI'].data
            self.dq = hdulist['DQ'].data

            head0 = hdulist[0].header
            head1 = hdulist[1].header

        self.instrument = head0['INSTRUME'].lower()
        self.detector = head0['DETECTOR']
        self.exp_start_time = head0['DATE-BEG']
        self.exp_end_time = head0['DATE-END']

        # For the purposes of querying the event log in the EDB, the start and end times
        # must have exactly 3 places after the decimal, which translates to a total
        # length of 22 characters.
        self.visit_start_time = head0['VSTSTART'].replace(' ','T')[0:23]
        self.visit_end_time = head0['VISITEND'].replace(' ','T')[0:23]
        self.visit_id = 'V' + head0['VISIT_ID']

        # Get aperture and subarray names
        self.aperture = head0['APERNAME']
        self.subarray = head0['SUBARRAY']

        # Get filter and pupil
        self.filter = head0['FILTER']
        try:
            self.pupil = head0['PUPIL']
        except ValueError:
            self.pupil = None

        # Get the target coordinates. The values stored in the TARG_RA and TARG_DEC
        # header keywords are the calculated RA, Dec of the target at the time of the
        # observation, using the input target RA, Dec from APT in combination with the
        # observation date and the apparent motion.
        self.RA_targ = head0['TARG_RA']
        self.DEC_targ = head0['TARG_DEC']

        # Determine the offset between the region of interest and the aperture
        self.inst_siaf = Siaf(self.instrument)

        # Get RA/DEC of ref point
        self.RA_ref = head1['RA_REF']
        self.DEC_ref = head1['DEC_REF']
        self.V2_ref = head1['V2_REF']
        self.V3_ref = head1['V3_REF']

        # Coordinates from the header are 1-indexed. Subtract 1 to make 0-indexed
        self.x_ref = head1['CRPIX1'] - 1
        self.y_ref = head1['CRPIX2'] - 1
        self.pa_v3 = head1['PA_V3']
        self.roll_ref = head1['ROLL_REF']
        self.pixel_scale_x = head1['CDELT1'] * 3600.  # Convert to arcsec
        self.pixel_scale_y = head1['CDELT2'] * 3600.  # Convert to arcsec

        # Create a Siaf instance for the aperture
        self.ap_siaf = Siaf(self.instrument)[self.aperture]

        # Calculate the coordinates of the aperture corners
        self.calc_corners()

        # Calculate the target's x, y location based on the target's CALCULATED RA, Dec, the
        # ref location's RA, Dec, V2, V3 and using an attitude matrix
        self.calc_target_xy()

    def calc_corners(self):
        """Calculate the coordinates of the corners of the aperture in both detector and science
        coordinates. For "science" coordinates, we mean full frame coordinates in the science frame,
        rather than simpley (0, 32) for a 32x32 subarray.
        """
        # Get corner coordinates in detector coord system
        self.x_corner_det, self.y_corner_det = self.ap_siaf.corners(to_frame='det')

        # Using a Siaf instance for the corresponding full frame aperture, get the subarray
        # corner coordinates in the full frame science coord system.
        if self.instrument == 'niriss':
            suffix = 'CEN'
        else:
            suffix = 'FULL'
        fullframe_aperture = f'{self.aperture.split("_")[0]}_{suffix}'
        fullframe_siaf = self.inst_siaf[fullframe_aperture]
        self.x_corner_ff_sci, self.y_corner_ff_sci = fullframe_siaf.det_to_sci(self.x_corner_det, self.y_corner_det)

    def calc_target_xy(self):
        """Calculate the target's x, y location on the detector. Do this using the reference
        location's RA, Dec, V2, V3, creating an attitude matrix, calculating the target's
        V2, V3, and then converting to x, y
        """
        self.attitude = define_attitude(self.V2_ref, self.V3_ref, self.RA_ref, self.DEC_ref, self.roll_ref)
        self.v2_targ, self.v3_targ = rotations.getv2v3(self.attitude, self.RA_targ, self.DEC_targ)
        self.x_targ, self.y_targ = self.ap_siaf.tel_to_sci(self.v2_targ, self.v3_targ)

        # Coordinates from pysiaf are 1-indexed. Subtract 1 to make 0-indexed
        self.x_targ -= 1
        self.y_targ -= 1

        self.idl_x_targ, self.idl_y_targ = self.ap_siaf.tel_to_idl(self.v2_targ, self.v3_targ)

    def manual_centroid(self, use_ref_loc=True, use_targ_loc=False, half_width=None):
        """Calculate the centroid of the source in the data. This will be compared to the
        results from GENTALOCATE

        Parameters
        ----------
        use_ref_loc : bool
            If True and half_width is not None, the centroiding will be done on a subarray
            of size 2*half_width x 2*half_width around the reference location of the aperture.
        use_targ_loc : bool
            If True and half_width is not None, the centroiding will be done on a subarray
            of size 2*half_width x 2*half_width around the target location of the aperture.
        half_width : int
            If not None, centroiding will be done on a subarray within self.data. If None,
            the entire self.data array will be used

        Returns
        -------
        xc : float
            X-coordinate of the centroid, in pixels

        yc : float
            Y-coordinate of the centroid, in pixels
        """
        if half_width is not None:
            # Extract a subarray
            if use_ref_loc:
                if use_targ_loc:
                    raise ValueError('Both use_ref_loc and use_targ_loc cannot both be True.')
                else:
                    xstart = int(self.x_ref) - half_width
                    xend = int(self.x_ref) + half_width
                    ystart = int(self.y_ref) - half_width
                    yend = int(self.y_ref) + half_width
            elif use_targ_loc:
                xstart = int(self.x_targ) - half_width
                xend = int(self.x_targ) + half_width
                ystart = int(self.y_targ) - half_width
                yend = int(self.y_targ) + half_width

            array = self.data[ystart:yend, xstart:xend]
            dq_array = self.dq[ystart:yend, xstart:xend].astype('bool')
        else:
            array = self.data
            dq_array = self.dq.astype('bool')

        self.manual_x_centroid, self.manual_y_centroid = centroid_com(array, mask=dq_array)




class TAMonitor():

    """Class for executing the TA monitor.

    This class will search for new (since the previous instance of the
    class) TA data in the file system. It will loop over
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
        """Initialize an instance of the ``TAMonitor`` class."""

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
        self.output_dir = '/Volumes/jwst_ins/jwql/nircam1/outputs/TA_monitor/'


    def create_TA_figs(self):

        self.full_img, self.zoom_img, self.sub_img = None, None, None

        positions = {#'x': self.ta_data.x_corner_det, 'y': self.ta_data.y_corner_det,
                     'x': self.ta_data.x_corner_ff_sci, 'y': self.ta_data.y_corner_ff_sci,
                     'x_ref': self.ta_data.x_ref, 'y_ref': self.ta_data.y_ref,
                     #'x_targ': self.ta_data.x_targ, 'y_targ': self.ta_data.y_targ,
                     'x_targ': self.dms_aperture_centroid[0] - 1, 'y_targ': self.dms_aperture_centroid[1] - 1,
                     'x_off': self.roi_offset[0], 'y_off': self.roi_offset[1]}

        print('self.ta_data.subarray:', self.ta_data.subarray)
        print('positions:')
        print(positions)

        if self.ta_data.subarray == 'FULL':

            full = FullROIImage(self.ta_data.data, positions, outfile='full_test.png', outdir=self.img_dir)
            self.full_img = full.output_file
            zoom = ZoomedROIImage(self.ta_data.data, self.roi_offset, positions, outfile='zoom_test.png', outdir=self.img_dir)
            self.zoom_img = zoom.output_file

        else:
            sub = SubROIImage(self.ta_data.data, positions, outfile='sub_test.png', outdir=self.img_dir)
            self.sub_img = sub.output_file



    '''
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
    '''
    def flip_coords_to_DMS(self):
        """Translate the coordinates from the OSS event log from OSS coordinates
        to DMS coordinates. Use the sci coordinate system in pysiaf, for consistency.
        Note, for NIRCam and MIRI, we can translate using pysiaf's det_to_sci, because
        in those cases det == OSS. But for instruments with the fast readout along
        the columns (NIRISS), raw == OSS (and det == ?), so in that case we may
        need to use raw_to_sci.
        """

        """
        test case:
        nircam jw01467001001_02102_00001_nrca3_rate.fits
        event.ta_info:
Out[116]:
{'peak_bkgd': 42213.0,
 'peak_signal': 61541.2548,
 'peak_pixel': array([36., 25.]),
 'aperture_centroid': array([35.7315016, 24.9999652]),
 'detector_centroid': array([1590.7315 , 1402.99997]),
 'convergence': ' SUCCESS',
 'conv_thresh': 0.1}

h['APERNAME']
Out[117]: 'NRCA3_FP1_SUB64'

Check in pysiaf:
In DMS coords, on the full frame detector, this aperture is in the upper left quadrant.
IN OSS coords, on the full frame detector, this aperture in in the upper right quadrant (due to the horizontal flip)


n = pysiaf.Siaf('nircam')['NRCA3_FP1_SUB64']
In [122]: n.corners(to_frame='sci')
Out[122]: (array([ 0.5, 64.5, 64.5,  0.5]), array([ 0.5,  0.5, 64.5, 64.5]))

In [123]: n.corners(to_frame='det')
Out[123]:
(array([1619.5, 1555.5, 1555.5, 1619.5]),  -> these numbers agree with the eventlog, so we confirm that they are OSS coords
 array([1378.5, 1378.5, 1442.5, 1442.5]))

In [124]: n.det_to_sci(1590.7315 , 1402.99997)
Out[124]: (29.268499999999904, 24.999970000000076) --> this does not agree with the aperture centroid in the eventlog, which makes sense.
                                                These values are in the sci coord system, while the aperture coords in the eventlog are OSS coords
35.7 -> OSS x_coord = 1-indexed
64 - 35.7 = 28.3 = 0-indexed, flipped coordinate. To get back to 1-indexed, need to add 1.
28.3 + 1 = 29.3 which agrees with the pysaif output above.

SO: I think all we need to do is:
sci_1indexed = n.det_to_sci(event.ta_info["aperture_centroid"])
sci_aperture_centroid = (sci_1indexed[0] - 1, sci_1indexed[1] - 1)  # this is 0-indexed, sci coords

from jwql.edb.engdb_oss_msgs import EventLog
from astropy.io import fits
file = 'jw01467001001_02102_00001_nrca3_rate.fits'
h = fits.getheader(file,0)
aperture = h['APERNAME']
subarray = h['SUBARRAY']
#visit_start_time = '2022-04-23T04:18:34.558'
#visit_end_time = '2022-04-23T04:47:34.558'
#visit_id = f'V{h["VISIT_ID"]}'
visit_start_time = h['VSTSTART'].replace(' ','T')[0:23]
visit_end_time = h['VISITEND'].replace(' ', 'T')[0:23]
visit_id = f'V{h["VISIT_ID"]}'
event = EventLog(startdate=visit_start_time, enddate=visit_end_time)
event.extract_oss_centroid(visit_id)
event.ta_info

Out[3]:
{'peak_bkgd': 42213.0,
 'peak_signal': 61541.2548,
 'peak_pixel': array([36., 25.]),
 'aperture_centroid': array([35.7315016, 24.9999652]),
 'detector_centroid': array([1590.7315 , 1402.99997]),
 'convergence': ' SUCCESS',
 'conv_thresh': 0.1}

#########THIS WORKS#######
n = pysiaf.Siaf('nircam')[aperture]
#n.det_to_sci(event.ta_info["aperture_centroid"][0], event.ta_info["aperture_centroid"][1])
n.XSciSize - event.ta_info["aperture_centroid"][0] + 1 == n.det_to_sci(1590.7315 , 1402.99997)[0]  # horizontal flip. both 1-indexed. See 2 lines down
event.ta_info["aperture_centroid"][1] == n.det_to_sci(1590.7315 , 1402.99997)[1] # no vertical flip. both 1-indexed
# 2 ways to get the centroid value in DMS science coords.
n.XSciSize - event.ta_info["aperture_centroid"][0] + 1 == n.det_to_sci(event.ta_info['detector_centroid'][0], event.ta_info['detector_centroid'][1])[0]
event.ta_info["aperture_centroid"][1] == n.det_to_sci(event.ta_info['detector_centroid'][0], event.ta_info['detector_centroid'][1])[1]

So, the easy solution, so you dont need to worry about flipping axes is to use:
n.det_to_sci(event.ta_info['detector_centroid'][0], event.ta_info['detector_centroid'][1])
Out[60]: (29.268499999999904, 24.999970000000076)

JWQL check. Peak is in (28, 24) - 0-indexed GOOD!!!
#########################

####another nircam check
file='jw02278001001_02102_00001_nrcalong_rate.fits'
h = fits.getheader(file,0)
aperture = h['APERNAME']
subarray = h['SUBARRAY']
visit_start_time = h['VSTSTART'].replace(' ','T')[0:23]
visit_end_time = h['VISITEND'].replace(' ', 'T')[0:23]
visit_id = f'V{h["VISIT_ID"]}'
event = EventLog(startdate=visit_start_time, enddate=visit_end_time)
event.extract_oss_centroid(visit_id)
event.ta_info
{'peak_bkgd': 5689.0,
 'peak_signal': 11308.2592,
 'peak_pixel': array([33., 29.]),
 'aperture_centroid': array([32.7933815, 29.2572946]),
 'detector_centroid': array([1429.79338, 1548.25729]),
 'convergence': ' SUCCESS',
 'conv_thresh': 0.1}
n.det_to_sci(event.ta_info['detector_centroid'][0], event.ta_info['detector_centroid'][1])
Out[102]: (32.20661999999993, 29.257290000000012)

manual check with JWQL: 31, 28 - 0-indexed, so this agrees.
###########################

Check miri:
MRS - works here as well, but you need to use Siaf('miri')[self.subarray] rather than
Siaf('miri')[self.aperture] in the case where the full frame is used

file = 'jw01275004001_02101_00001_mirimage_rate.fits'
h = fits.getheader(file,0)
aperture = h['APERNAME']
subarray = h['SUBARRAY']
visit_start_time = h['VSTSTART'].replace(' ','T')[0:23]
visit_end_time = h['VISITEND'].replace(' ', 'T')[0:23]
visit_id = f'V{h["VISIT_ID"]}'
event = EventLog(startdate=visit_start_time, enddate=visit_end_time)
event.extract_oss_centroid(visit_id)
event.ta_info
Out[146]:
{'peak_bkgd': 25461.0,
 'peak_signal': 40598.464,
 'peak_pixel': array([25., 25.]),
 'aperture_centroid': array([24.9889652, 25.4824798]),
 'detector_centroid': array([997.988965, 994.48248 ]),
 'convergence': ' SUCCESS',
 'conv_thresh': 0.01}

In [142]: aperture
Out[142]: 'MIRIM_TAMRS'

In [143]: subarray
Out[143]: 'FULL'

#######NOTE!!!! This is different than nircam above. Here we need to use aperture_centroid, but for nircam is was detector_centroid
# This is for miri observations that use full frame
n = pysiaf.Siaf('miri')['MIRIM_'+subarray]
n.det_to_sci(event.ta_info["aperture_centroid"][0], event.ta_info["aperture_centroid"][1])
Out[154]: (24.988965200000052, 25.48247980000002) --> These values agree with those from the event log. still need to subtract 1 in order
                to put in a 0-indexed coord system.


naperture = pysiaf.Siaf('miri')[aperture]
naperture.XDetRef, naperture.YDetRef
Out[75]: (997.5, 993.5)  -> This agrees with a JWQL check of the file. Now how do we get 997, 994 from the eventlog coords?

from jwql, the center looks to be at 997.0, 993.5 (0-indexed), so (998.0, 994.5) when comparing to reported OSS coords. And that
agrees very well with the detector_centroid values above.

corners = naperture.corners(to_frame='det')
Out[77]:
(array([ 973.5, 1021.5, 1021.5,  973.5]),
 array([ 969.5,  969.5, 1017.5, 1017.5]))

The 'detector_centroid' coords directly in the eventlog match up, given the indexing....
det_to_sci does not make any changes here, meaning the two coord systems are the same
but is there a 0.5 pixel offset between the two? I dont think so, because the aperture corners are at xxx.5, and
i am assuming that the aperture starts at the corner of a pixel, rather than in the center.

# This is very close. Is it correct???
np.min(c[0]) + event.ta_info["aperture_centroid"][0]
Out[84]: 998.4889652

In [83]: np.min(c[1]) + event.ta_info["aperture_centroid"][1]
Out[85]: 994.9824798

###############################
#another miri check
file='jw01274012001_02101_00001-seg001_mirimage_rate.fits'
h = fits.getheader(file,0)
aperture = h['APERNAME']
subarray = h['SUBARRAY']
visit_start_time = h['VSTSTART'].replace(' ','T')[0:23]
visit_end_time = h['VISITEND'].replace(' ', 'T')[0:23]
visit_id = f'V{h["VISIT_ID"]}'
event = EventLog(startdate=visit_start_time, enddate=visit_end_time)
event.extract_oss_centroid(visit_id)
event.ta_info
{'peak_bkgd': 41337.0,
 'peak_signal': 53507.0894,
 'peak_pixel': array([24., 23.]),
 'aperture_centroid': array([24.2814062, 23.3507629]),
 'detector_centroid': array([ 38.2814062, 911.350763 ]),
 'convergence': ' SUCCESS',
 'conv_thresh': 0.01}

n = pysiaf.Siaf('miri')['MIRIM_'+subarray]
n.det_to_sci(event.ta_info["aperture_centroid"][0], event.ta_info["aperture_centroid"][1])
Out[111]: (24.2814062, -504.64923710000005)

naperture = pysiaf.Siaf('miri')[aperture]
naperture.XDetRef, naperture.YDetRef
Out[112]: (38.5, 912.5)

JWQL shows a centroid of about (40,380)

In [109]: naperture.corners(to_frame='det')
Out[109]: (array([14.5, 62.5, 62.5, 14.5]), array([888.5, 888.5, 936.5, 936.5]))

In [110]: n.corners(to_frame='det')
Out[110]: (array([ 0.5, 72.5, 72.5,  0.5]), array([528.5, 528.5, 944.5, 944.5]))

In [113]: n.corners(to_frame='sci')
Out[113]: (array([ 0.5, 72.5, 72.5,  0.5]), array([  0.5,   0.5, 416.5, 416.5]))

In [114]: naperture.corners(to_frame='sci')
Out[114]: (array([ 0.5, 48.5, 48.5,  0.5]), array([ 0.5,  0.5, 48.5, 48.5]))

###THIS WORKS. SAME ANSWER AS NIRCAM's ABOVE
# this applies to miri obs that do not use full frame
n.det_to_sci(event.ta_info['detector_centroid'][0], event.ta_info['detector_centroid'][1])
########################
check niriss:

file = 'jw01504001001_02101_00003_nis_rate.fits'
h = fits.getheader(file,0)
aperture = h['APERNAME']
subarray = h['SUBARRAY']
visit_start_time = h['VSTSTART'].replace(' ','T')[0:23]
visit_end_time = h['VISITEND'].replace(' ', 'T')[0:23]
visit_id = f'V{h["VISIT_ID"]}'
event = EventLog(startdate=visit_start_time, enddate=visit_end_time)
event.extract_oss_centroid(visit_id)
event.ta_info
Out[37]:
{'peak_bkgd': 15063.0,
 'peak_signal': 22664.8607,
 'peak_pixel': array([19., 47.]),
 'aperture_centroid': array([19.3073661, 47.3586699]),
 'detector_centroid': array([1928.30737,  978.35867]),
 'convergence': ' SUCCESS',
 'conv_thresh': 0.2}

##### This does not work.....
n = pysiaf.Siaf('niriss')[aperture]
#n.det_to_sci(event.ta_info['detector_centroid'][0], event.ta_info['detector_centroid'][1])
# It looks like for niriss we need to swap x and y (because the fast read direction is along the y axis??)
n.det_to_sci(event.ta_info['detector_centroid'][1], event.ta_info['detector_centroid'][0])
Out[56]: (17.64133000000004, 40.69263000000001)
# I checked this image in jwql and 17.6, 40.6 (1-indexed) looks right for the center. I'm not sure
# where the 19.3, 47.3 in aperture_centroid comes from....
<
# JWQL check, centroid = (16.75, 39.5) 0-indexed
        """

        if self.instrument == 'nircam':
            self.dms_aperture_centroid = self.ta_data.ap_siaf.det_to_sci(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
            self.dms_aperture_centroid_v2v3 = self.ta_data.ap_siaf.det_to_tel(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
            self.full_siaf = self.ta_data.inst_siaf[f'{self.ta_data.aperture.split("_")[0]}_FULL'] #-- but what about coronagraphic ta?
            self.dms_det_centroid = self.full_siaf.det_to_sci(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
        elif self.instrument == 'niriss':
            self.dms_aperture_centroid = self.ta_data.ap_siaf.det_to_sci(self.event.ta_info['detector_centroid'][1], self.event.ta_info['detector_centroid'][0])
            self.dms_aperture_centroid_v2v3 = self.ta_data.ap_siaf.det_to_tel(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
            self.full_siaf = self.ta_data.inst_siaf['NIS_CEN']
            self.dms_det_centroid = self.full_siaf.raw_to_sci(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
        elif self.instrument == 'miri':
            self.full_siaf = Siaf('miri')['MIRIM_FULL'] #-- but what about e.g. coronagraphic ta?
            if self.subarray != 'FULL':
                sub_siaf = self.ta_data.inst_siaf['MIRIM_' + self.subarray]
                self.dms_aperture_centroid = sub_siaf.det_to_sci(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
                self.dms_aperture_centroid_v2v3 = sub_siaf.det_to_tel(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
                self.dms_det_centroid = self.full_siaf.det_to_sci(self.event.ta_info['detector_centroid'][0], self.event.ta_info['detector_centroid'][1])
            else:
                self.dms_aperture_centroid = self.event.ta_info['aperture_centroid']
                self.dms_aperture_centroid_v2v3 = something
                self.dms_det_centroid = self.event.ta_info['detector_centroid']


    # Subtract 1 to put the coordinates in a 0-indexed coordinate system
    # Actually, maybe we shouldn't do this. pysiaf also uses a 1-indexed system, so maybe we should
    # keep all of the values in a 1-indexed system
    #self.dms_sci_centroid = (dms[0] - 1, dms[1] - 1)
    #self.dms_det_centroid = self.ap_siaf.sci_to_det(self.dms_sci_centroid[0], self.dms_sci_centroid[1]) check this







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


    def get_post_ta_data(self):
        """Using a given TA file as a guide, query the Django models for science data
        taken after the TA. If the science data are dispersed, then we can't do any source
        position checks, so return None.
        """
        tmp_list = []

        for ta_rootfile, taconf_rootfile in self.ta_query_results:
            #taconf = entry[1]
            #taconf = self.ta_query_results[entry]
            science_file = self.query_for_post_ta_data(ta_rootfile)

            print(f'science file is: {science_file}')

            if self.instrument == 'miri':
                # If the science file contains dispersed data, we don't want it
                if science_file.filter in ['P750L', 'FND'] or science_file.exp_type != 'MIR_MRS':
                    science_file = None

            elif self.instrument == 'nircam':
                if 'GRISM' in science_file.pupil:
                    science_file = None

            elif self.instrument == 'niriss':
                # Post-TA file for NIRISS should never be dispersed
                pass

            # Update the dictionary such that the value is now a tuple of the TACONFIRM
            # RootFileInfo, and the science file dictionary
            if science_file is not None:
                entry = (ta_rootfile, taconf_rootfile, science_file.root_name)
            else:
                entry = (ta_rootfile, taconf_rootfile, None)
            tmp_list.append(entry)

        # Re-populate self.ta_query_results with the updated 3-tuples
        self.ta_query_results = tmp_list

    def get_refpoint_info(self, hdu_header):
        """Get pointing information associated with the reference location of the
        aperture
        """
        self.RA_ref = hdu_header['RA_REF']
        self.DEC_ref = hdu_header['DEC_REF']
        self.V2_ref = hdu_header['V2_REF']
        self.V3_ref = hdu_header['V3_REF']

        # Indexes from the header are 1-indexed. Subtract 1 to make them 0-indexed
        self.x_ref = hdu_header['CRPIX1'] - 1
        self.y_ref = hdu_header['CRPIX2'] - 1
        #self.pa_v3 = hdu_header['PA_V3']
        self.roll_ref = hdu_header['ROLL_REF']
        self.pixel_scale_x = hdu_header['CDELT1'] * 3600.  # Convert to arcsec
        self.pixel_scale_y = hdu_header['CDELT2'] * 3600.  # Convert to arcsec

    def get_roi_offset(self):
        """Calculate the offset of the ROI from the aperture
        """
        #prob want to use the science frame for the full frame equivalent rather than then detector frame, right?
        #for miri it doesn't matter, but for nircam and niriss the detector coords flip between the two, and people are more
        #used to looking at DMS-oriented frames.

        #self.x, self.y = self.ta_data.ap_siaf.corners(to_frame='det')
        #self.x_ref, self.y_ref = self.ap_siaf.reference_point(to_frame='det') - done in get_refpoint_info()

        if self.instrument == 'miri':
            if self.subarray != 'FULL':
                aper_x, aper_y = self.ta_data.inst_siaf['MIRIM_' + self.subarray].corners(to_frame='det')
                x_off, y_off = aper_x[0], aper_y[0]
            else:
                #x_off, y_off = self.x[0], self.y[0]
                x_off, y_off = self.ta_data.x_corner_det[0], self.ta_data.y_corner_det[0]

            #self.roi_offset = [int(np.floor(x_off)), int(np.floor(y_off))]
            #self.roi_offset_float = [x_off, y_off]

            # Keep the actual ROI offset. Leave any rounding for later.
            self.roi_offset= [x_off, y_off]


        elif self.instrument in ['nircam', 'niriss']:
            aper_x, aper_y = self.ta_data.ap_siaf.corners(to_frame='det')
            #self.roi_offset = [int(np.floor(aper_x[0])), int(np.floor(aper_y[0]))]
            #self.roi_offset_float = [aper_x[0], aper_y[0]]
            #self.roi_offset = [self.ta_data.x_corner_det[0], self.ta_data.y_corner_det[0]]
            self.roi_offset = [self.ta_data.x_corner_ff_sci[0], self.ta_data.y_corner_ff_sci[0]]
            #self.roi_offset = [aper_x[0], aper_y[0]]
            print('This needs to be checked for both nircam and niriss separately')

    def get_ta_metadata(filename):
        """Return metadata from a TACQ file

        Parameters
        ----------
        filename : str
            Full path to a target acq file

        Returns
        -------

        """
        head0 = fits.getheader(file)
        propid = head0['PROGRAM']
        obsnum = head0['OBSERVTN']
        visitstartdate = head0['VSTSTART']
        visitenddate = head0['VISITEND']
        return propid, obsnum, visitstartdate, visitenddate

    def keep_non_coron_ta(self):
        """Remove coronagraphic RootFileInfo entries from the results of nircam and miri
        model queries.
        """
        self.ta_query_results = []

        apertures = [row['aperture'] for row in self.ta_entries]

        if self.instrument == 'nircam':

            # First throw out all entries with MASK or WEDGE in the aperture name
            non_coron = [row for row in self.ta_entries if 'MASK' not in row['aperture'] and 'WEDGE' not in row['aperture']]

        elif self.instrument == 'miri':
            non_coron = [row for row in self.ta_entries if row['aperture'] in MIRI_NON_CORON_TA_APERTURES]


        print('non_coron:', non_coron)


        # Now check each unique program/obsnum for TACQ and TACONFIRM entries
        exptypes = np.array([row['exp_type'] for row in non_coron])

        program_obsnum = np.array([f'{row["root_name"][2:10]}' for row in non_coron])

        # Why is there no obsnum information in this query set? am I referencing it incorrectly?
        #program_obsnum = np.array([f'{row["proposal"]}{row["obsnum"]["obsnum"]}' for row in non_coron])

        unique_program_obsnums = set(program_obsnum)

        print('unique_program_obsnums: ', unique_program_obsnums)

        for probs in unique_program_obsnums:
            match = np.where(program_obsnum == probs)[0]

            print('probs: ', probs)
            print('program_obsnum: ', program_obsnum)


            tas = np.where(exptypes[match] == f'{JWST_INSTRUMENT_NAMES_ABBREVIATIONS[self.instrument]}_TACQ')[0]
            taconfirms = np.where(exptypes[match] == f'{JWST_INSTRUMENT_NAMES_ABBREVIATIONS[self.instrument]}_TACONFIRM')[0]

            print('match: ', match)
            print('tas: ', tas)



            if len(tas) > 1:
                raise ValueError(f"For {self.instrument} program {probs[0:5]}, observation {probs[-3:]}, there appears to be > 1 TACQ file. Unexpected.")
            if len(taconfirms) > 1:
                raise ValueError(f"For {self.instrument} program {probs[0:5]}, observation {probs[-3:]}, there appears to be > 1 TACONFIRM file. Unexpected.")

            # Set up the results as a dictionary where the key is the TACQ RootFileInfo entry, and the value is
            # the TACONFIRM RootFileEntry (this is still ugly)

            print('self.ta_query_results:')
            print(self.ta_query_results)
            print(self.ta_entries)
            print(int(list(match)[tas[0]]))
            print(type(self.ta_entries))
            print(self.ta_entries[int(list(match)[tas[0]])])


            if len(taconfirms) == 1:
                self.ta_query_results.append((self.ta_entries[int(list(match)[tas[0]])], self.ta_entries[int(list(match)[taconfirms[0]])]))
            elif len(taconfirms) == 0:
                self.ta_query_results.append((self.ta_entries[int(list(match)[tas[0]])], None))

    #def manual_centroid(self):
    #    """Calculate the centroid of the source in the data. This will be compared to the
    #    results from GENTALOCATE
    #
    #    Returns
    #    -------
    #    xc : float
    #        X-coordinate of the centroid, in pixels
    #
    #    yc : float
    #        Y-coordinate of the centroid, in pixels
    #    """
    #    return centroid_com(self.data, mask=self.dq.astype('bool'))

    def most_recent_search(self, aperture):
        """Query the query history database and return the information
        on the most recent query for the given ``aperture`` where
        the TA monitor was executed.

        Paramters
        ---------
        aperture : str
            Aperture name of the data of interest

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
                self.query_table.aperture == aperture,
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

    """
    def query_mast(self):
        Use astroquery to search MAST for TA data

        Returns
        -------
        result : list
            List of dictionaries containing the query results


        data_product = JWST_DATAPRODUCTS
        parameters = {"date_obs_mjd": {"min": self.query_start, "max": self.query_end}, "exp_type": self.exp_type}

        result = monitor_mast.instrument_inventory(self.instrument, data_product,
                                                   add_filters=parameters,
                                                   return_data=True)

        return result
    """

    def organize_ta_files(self):
        """Organize the results of the model query. For nircam and miri observations, we want to remove
        coronagraphic entries (including TACONFIRM entries). For NIRISS AMI and SOSS modes, there will be
        3 TA files followed by a TACONFIRM file. The three TA files contain 3 dithers of the same scene.
        We only care about the first of the three, so remove entries for the 2nd and 3rd files from each.

        self.ta_entries is a QuerySet object before this function runs. Afterwards, it will be transformed
        into a dictionary where the keys are the RootFileInfo entries for the TACQ files, and the values
        are the RootFileInfo entries for associated TACONFIRM exposures. Note that not all TACQ exposures
        have an associated TACONFIRM exposure. In that case, the value will be blank.
        """
        if self.instrument in ['nircam', 'miri']:
            self.keep_non_coron_ta()
        elif self.instrument == 'niriss':
            self.remove_dithered_ta_files()
        else:
            raise ValueError(f'Unsupported instrument: {self.instrument}')

    def process(self, ta_file, taconfirm_file, science_file):

        """The main method for processing data. See module docstrings
        for further details.

        Parameters
        ----------
        ta_file : str
            Path to the TA file being worked on
        taconfirm_file : str
            Path to the corresponding TACONFIRM file. ``None`` if there is no file.
        science_file : str
            Path to subsequent science or post-TA file. ``None`` if there is no file.
        """

        logging.info('Processing {}'.format(ta_file))

        # Get data and metadata from the TA file, and get target coords based on metadata
        self.ta_filename = ta_file
        self.ta_data = TargetInfo(self.ta_filename)



        """
        # Get data and metadata
        with fits.open(ta_file) as hdulist:
            self.data = hdulist['SCI'].data
            self.dq = hdulist['DQ'].data

            head0 = hdulist[0].header
            head1 = hdulist[1].header

        self.instrument = head0['INSTRUME'].lower()
        detector = head0['DETECTOR']
        self.exp_start_time = head0['DATE-BEG']
        self.exp_end_time = head0['DATE-END']

        # For the purposes of querying the event log in the EDB, the start and end times
        # must have exactly 3 places after the decimal, which translates to a total
        # length of 22 characters.
        visit_start_time = head0['VSTSTART'].replace(' ','T')[0:23]
        visit_end_time = head0['VISITEND'].replace(' ','T')[0:23]
        visit_id = 'V' + head0['VISIT_ID']

        # get aperture name
        self.aperture = head0['APERNAME']
        self.subarray = head0['SUBARRAY']

        # Get the target coordinates. The values stored in the TARG_RA and TARG_DEC
        # header keywords are the calculated RA, Dec of the target at the time of the
        # observation, using the input target RA, Dec from APT in combination with the
        # observation date and the apparent motion.
        self.RA_targ = head0['TARG_RA']
        self.DEC_targ = head0['TARG_DEC']
        """


        """
        for nircam
         h['SUBARRAY']
Out[29]: 'SUB32TATSGRISM'

In [30]: h['APERNAME']
Out[30]: 'NRCA5_TAGRISMTS32'

In [31]: h['PPS_APER']
Out[31]: 'NRCA5_TAGRISMTS32'

nircam imaging time series uses 32x32 TA aperture on LWB
nircam grism time series uses 32x32 TA aperture on LWA
nircam coronagraphy uses mulitple apertures, always 128x128 in SW or 64x64 in LW, ND square or not (6 apertures per channel)
nircam TA NEVER USES FULL. SO APERTURE VS SUBARRAY WONT BE USEFUL, UNLIKE IN MIRI

niriss soss and ami use TA observations. both use 64x64 subarray
        """


        # Determine the offset between the region of interest and the aperture
        #self.inst_siaf = self.ta_data.inst_siaf
        #self.ap_siaf = self.ta_data.ap_siaf
        self.get_roi_offset()

        # Get RA/DEC of ref point
        #self.get_refpoint_info(head1)

        # Get the calculated RA, Dec of the target
        #self.get_target_pointing()

        # Calculate the target's x, y location based on the ref location's RA, Dec, V2, V3 and creating an attitude matrix
        #self.x_targ, self.y_targ = self.calc_target_xy(self.V2_ref, self.V3_ref, self.RA_ref, self.DEC_ref,
        #                                               self.roll_ref, self.RA_targ, self.DEC_targ)


        # get coordinates of the target in pixels
        # inserting test point because targ values are wrong in header
        # to be fixed when data available


        # x_targ,y_targ = img.meta.wcs.transform('world', 'detector',RA_ref, DEC_ref)
        #self.x_targ, self.y_targ = self.x_ref+5, self.y_ref+5 - this looks to be leftover from his manual test point
        #                                                        how do we calculate this for real, assuming we are not working with a cal file?
        #                                                        This needs to come from the EDB (if its there), or else we need to make a cal file.
        #                                                        Looks like this info is NOT in the EDB. It possibly exists in the MOC somewhere, but
        #                                                        that doesnt help in terms of writing an automated monitor.



        #self.RA_targ, self.DEC_targ = self.ta_model.meta.wcs.transform('detector', 'world', self.x_targ, self.y_targ) - this only works for cal.fits files!!


        # Calculate offset of target from ref point, in arcseconds
        # This is the offset between the refernnce location and the CALCULATED RA, Dec of the target.
        # Keep in mind that this will be wrong if the calcuated RA, Dec is wrong.
        offset_RA = (self.ta_data.RA_ref - self.ta_data.RA_targ) * 3600
        offset_DEC = (self.ta_data.DEC_ref - self.ta_data.DEC_targ) * 3600
        self.offset = np.sqrt(offset_RA**2 + offset_DEC**2)

        logging.info('Target RA: {}, Target DEC: {}'.format(self.ta_data.RA_targ, self.ta_data.DEC_targ))
        logging.info('TA offset: {} "'.format(self.offset))



        """
        ###### WIP get OSS centroid values from the edb

        This seems to work. Other info that may be useful to pull from the RTL (only the postage-stamp coord below are currenly returned)
        '2023-06-12 03:47:11.440000,60107.1577712963,peakValue                                                          = 25461.0000,varchar',
        '2023-06-12 03:47:17.584000,60107.1578424074,"postage-stamp coord (colCentroid, rowCentroid) = (24.9889652, 25.4824798)",varchar',
        '2023-06-12 03:47:18.608000,60107.1578542593,"detector coord (colCentroid, rowCentroid)       = (997.988965, 994.482480)",varchar',


        In [28]: head0['DATE-BEG']
        Out[28]: '2023-06-12T03:45:34.872'

        In [29]: head0['DATE-END']   -------> this is the end of the observation, which is why it is earlier than the centroid calcs below.
        Out[29]: '2023-06-12T03:45:57.072'    we need to remember to pad the end time when running the query.

        '2023-06-12 03:46:17.168000,60107.1571431481,**********************************************,varchar',
        '2023-06-12 03:46:18.192000,60107.1571550000,TARGET LOCATE SUMMARY:,varchar',
        '2023-06-12 03:46:19.216000,60107.1571668519,DETECTOR                                                             = MIRIMAGE,varchar',
        '2023-06-12 03:46:20.240000,60107.1571787037,"(numCols, numRows)                                                     = (5, 5)",varchar',
        '2023-06-12 03:46:36.624000,60107.1573683333,cosmicrayMethod                                                      = STANDARD,varchar',
        '2023-06-12 03:47:09.392000,60107.1577475926,"(backgroundMethod, backgroundValue)                = (FRACTION, 377.000000)",varchar',
        '2023-06-12 03:47:11.440000,60107.1577712963,peakValue                                                          = 25461.0000,varchar',
        '2023-06-12 03:47:12.464000,60107.1577831481,"peak postage-stamp coord (col, row)                    = (25, 25)",varchar',
        '2023-06-12 03:47:13.488000,60107.1577950000,"(total, numIter)                                             = (40598.4640, 4)",varchar',
        '2023-06-12 03:47:15.536000,60107.1578187037,"last iteration diff (col, row)          = (0.000216130465, 0.00501714400)",varchar',
        '2023-06-12 03:47:16.560000,60107.1578305556,"postage-stamp coord (colPeak, rowPeak) = (25, 25)",varchar',
        '2023-06-12 03:47:17.584000,60107.1578424074,"postage-stamp coord (colCentroid, rowCentroid) = (24.9889652, 25.4824798)",varchar',
        '2023-06-12 03:47:18.608000,60107.1578542593,"detector coord (colCentroid, rowCentroid)       = (997.988965, 994.482480)",varchar',
        '2023-06-12 03:47:19.632000,60107.1578661111,"(colMoment2, rowMoment2)                        = (0.00000000e+0, 0.00000000e+0)",varchar',
        '2023-06-12 03:47:20.656000,60107.1578779630,"(colMoment3, rowMoment3)                        = (0.00000000e+0, 0.00000000e+0)",varchar',
        '2023-06-12 03:47:21.680000,60107.1578898148,"(convergenceFlag, convergenceThres)        = (SUCCESS, 0.01000000000)",varchar',
        '2023-06-12 03:47:22.704000,60107.1579016667,**********************************************,varchar',

        """

        """
        eventlog = get_ictm_event_log() # if i recall this can be restricted to a certain timeframe
        vtest = 'V' + head0['VISIT_ID']
        #vtest = 'V01442001001'
        #extract_oss_event_msgs_for_visit(eventlog, vtest) --> This just prints lines from the eventlog. We don't really need to call it here.
        out = extract_oss_SAM(eventlog, vtest)
        print(out)
        cnt = extract_oss_centroid(eventlog, vtest)
        print(cnt)
        xdms = 32.-cnt[0]   #this is the case of a 32x32 TA subarray with x-axis flip between DMS and OSS orientation
        ydms = cnt[1]-1.
        print(xdms,ydms)
        ###### WIP get OSS centroid values from the edb
        """



        ###############################################
        # Second bit of info to check: OSS Centroid accuracy: x, y, offsets between the results of
        # GENTALOCATE and the measured centroid of the star
        # When querying the EDB for the EventLog, we need to be sure to query over a long enough time
        # that the visit start is included in the log entries. If it is not, then
        # the code will not be able to extract the TA information, even if that is included in the
        # extracted log entries. Use the reported visit start and end times from the header
        self.event = EventLog(startdate=self.ta_data.visit_start_time, enddate=self.ta_data.visit_end_time)
        self.event.extract_oss_centroid(self.ta_data.visit_id)
        #detector_ta_centroid = self.event.ta_info["detector_centroid"]  # in raw detector coords? may need to flip
        #self.ta_model.raw_to_sci(xcoords, ycoords)  - I get a NotImplementedError when I try this with a TA aperture using pysiaf

        # Change coordinate system from the OSS aperture and detector systems to DMS aperture and detector systems
        # for nircam and miri, need to convert from det to sci. (det==OSS)
        # for niriss, with the fast readout along columns we need to go from raw to sci (raw==OSS)
        self.flip_coords_to_DMS()

        #####################################################
        # 1. Initial TA accuracy: x, y offsets of the PSF from reference location of the TA aperture
        # (e.g. NRCA2_FSTAMASK210R). This is monitoring essentially the accuracy of the telescope blind pointing.
        # Offset between target x,y and the x,y of the reference location
        delta_x_targ_ref = self.ta_data.x_ref - self.dms_aperture_centroid[0]
        delta_y_targ_ref = self.ta_data.y_ref - self.dms_aperture_centroid[1]
        delta_xy_targ_ref = np.sqrt(delta_x_targ_ref**2 + delta_y_targ_ref**2)
        delta_arcsec_targ_ref = np.sqrt((delta_x_targ_ref * self.ta_data.pixel_scale_x)**2
                                         + (delta_y_targ_ref * self.ta_data.pixel_scale_y)**2)

        delta_v2_targ_ref = self.ta_data.V2_ref - self.dms_aperture_centroid_v2v3[0]
        delta_v3_targ_ref = self.ta_data.V3_ref - self.dms_aperture_centroid_v2v3[1]
        #delta_idlx_targ_ref = self.ta_data.idl_x_targ -
        #delta_idly_targ_ref = self.ta_data.idl_y_targ -

        #request to have the delta above in ideal pixels and V2,V3

        # Now we need an independenly measured centroid value to compare to. e.g. photutils
        # For now let's use a simple call to photutils' centroid_com(). Note that we are supplying
        # data in DMS aperture coords.
        self.ta_data.manual_centroid(use_ref_loc=True, half_width=4)
        x_photutil_centroid = self.ta_data.manual_x_centroid
        y_photutil_centroid = self.ta_data.manual_y_centroid

        # 1st quantity to track in requirements page
        # x, y offsets between the source and the reference location of the aperture (blind pointing accuracy)
        # but this case uses the independently-measured location of the source. Do we really want this?
        # This is a repeat of delta_x_targ_ref above, but using the manually calculated centroid rather than the
        # GENTALOCATE results
        print('Do we really want this?')
        ref_dx = x_photutil_centroid - self.ta_data.x_ref
        ref_dy = y_photutil_centroid - self.ta_data.y_ref

        #####################################################
        # 2. OSS Centroid accuracy3: x, y, offsets between the results of GENTALOCATE and the measured
        # centroid of the star
        centroid_dx = x_photutil_centroid - self.dms_aperture_centroid[0]
        centroid_dy = y_photutil_centroid - self.dms_aperture_centroid[1]

        # Works! but for the nircam A3 example, the photutils centroid is pretty far off.
        print(x_photutil_centroid, self.ta_data.x_ref, ref_dx)
        print(y_photutil_centroid, self.ta_data.y_ref, ref_dy)
        print(x_photutil_centroid, self.dms_aperture_centroid[0], centroid_dx)
        print(y_photutil_centroid, self.dms_aperture_centroid[1], centroid_dy)

        print('Delta xy (pix) between target location (from GENTALOCATE) and reference location: ', delta_xy_targ_ref)
        print('Delta xy (arcsec) between target location (from GENTALOCATE) and reference location: ', delta_arcsec_targ_ref)



        ########################################################
        # Now repeat for the TACONFIRM file, if it exists

        if taconfirm_file is not None:
            taconfirm_data = TargetInfo(taconfirm_file)

            taconfirm_data.manual_centroid(use_ref_loc=True, half_width=4)
            x_taconf_photutil_centroid = taconfirm_data.manual_x_centroid
            y_taconf_photutil_centroid = taconfirm_data.manual_y_centroid
            dx_taconf_centroid_refloc = x_taconf_photutil_centroid - taconfirm_data.x_ref
            dy_taconf_centroid_refloc = y_taconf_photutil_centroid - taconfirm_data.y_ref

            #also translate into ideal x,y and v2,v3

            totaldelta_taconf_centroid_refloc = np.sqrt(dx_taconf_centroid_refloc**2 + dy_taconf_centroid_refloc**2)
            if totaldelta_taconf_centroid_refloc <= TA_FAILURE_THRESHOLD:
                self.ta_status = 'SUCCESS'
            else:
                self.ta_status = 'FAILURE'

            #save self.ta_status, but also compare to self.event.ta_info["convergence"] (and self.event.ta_info["conv_thresh"])

        ########################################################
        # 4. Now we need to examine the SCIENCE image (rather than the TA image)
        # so that we can measure the x, y offset between the target centroid and the
        # reference location of the science aperture. i.e. how well did
        # JWST point based on the information learned from the TA image.
        # Note that in some cases the science data may be GRISM data.

        """
        How do we check this?
        MRS data - target is moved into the MRS aperture, which then leads to IFU data.
        NRC grism time series - LW is dispersed. SW typically uses WL, which will be hard to centroid (can we use a webbpsf psf to help a centroiding function?)
        LRS slit - target is placed in the slit, leading to dispersed data
        LRS slitless - also dispersed data
        niriss ami - 3 TA images (dithered by integer pixels), then a ta confirm, and then science (on a different subarray) Look at 1st TA image
           (for blind pointing info) and then the confirmation image, as well as the science image
        niriss soss - 3 TA images(dithered by integer pixels), then a ta confirm, and then science, which is dispersed.
            Look at 1st TA image and TA confirmation image
        """


        if science_file is not None:
            science_data = TargetInfo(science_file)

            # There are no GENTALOCATE results when dealing with science data, so in this case we'll
            # have to manually calculate a centroid. And we'll have to blindly centroid around the expected
            # location (reference point) and hope that any target there is the target we are interested in.

            # For NIRCam weak lens data, we need to centroid on a much larger area due to the large PSF
            if 'WL' not in science_data.pupil:
                half_width = 4
            else:
                half_width = 30

            science_data.manual_centroid(use_ref_loc=True, half_width=half_width)
            x_sci_photutil_centroid = science_data.manual_x_centroid
            y_sci_photutil_centroid = science_data.manual_y_centroid
            dx_sci_centroid_refloc = x_sci_photutil_centroid - science_data.x_ref
            dy_sci_centroid_refloc = y_sci_photutil_centroid - science_data.y_ref


            print('Post-TA (science) image:')
            print(f'Manual centroid: {x_sci_photutil_centroid}, {y_sci_photutil_centroid}')
            print(f'Delta from reference location (pix): {dx_sci_centroid_refloc}, {dy_sci_centroid_refloc}')
            print('NOTE this this is only meaningful if the target is an astronomical source (rather than just a point within some larger area.)')


            print('Here we could get the WCS of the cal version of the science file and compare the x,y location')
            print('of the target coordinates to the reference location of the aperture.')

        ########################################################
        # For LRS data, use the post-observation image and determine the target centroid.
        # There are well-characterized offsets between each filter and the slit, so image
        # centroids from filtered data can be converted to position in the LRS data, to find
        # the position relative to the slit.

        #what are these well-known offsets?





        """
        # Quantities to save to the database
        self.event.ta_info['convergence'] example value: 'SUCCESS'
        self.event.ta_info['peak_signal'] example value: 40598.464
        self.event.ta_info['peak_background'] example value: 25461.0
        self.event.ta_info['aperture_centroid'] example value: array([24.9889652, 25.4824798]) include 'oss' in DB column name
        self.event.ta_info['detector_centroid'] example value: array([997.988965, 994.48248 ]) include 'oss' in DB column name
        self.dms_aperture_centroid example value: array([24.9889652, 25.4824798]) include 'dms' in DB column name
        self.dms_det_centroid example value: array([997.988965, 994.48248 ]) include 'dms' in DB column name
        self.dms_aperture_centroid translated to xidl, yidl?
        self.dms_det_centroid translated to xidl, yidl?
        delta_x_targ_ref - x offset of targ location from aperture ref location (pix)
        delta_y_targ_ref - y offset of targ location from aperture ref location (pix)
        delta_xy_targ_ref - - total offset of targ location from aperture ref location (pix)
        delta_arcsec_targ_ref - total offset of targ location from aperture ref location (arcsec)
        x_photutil_centroid - x manual centroid of target (pix)
        y_photutil_centroid - y manual centroid of target (pix)
        centroid_dx - x diff between manual centroid and GENTALOCATE (pix)
        centroid_dy - y diff between manual centroid and GENTALOCATE (pix)
        aperture
        subarray
        """




        # create place to store files
        self.output_dir = os.path.join(get_config()['outputs'], 'TA_monitor')
        data_dir =  os.path.join(self.output_dir,'data')
        ensure_dir_exists(data_dir)
        self.img_dir = os.path.join(data_dir, self.ta_data.aperture)
        ensure_dir_exists(self.img_dir)

        #if self.ta_data.aperture in self.TA_names:
        self.create_TA_figs()

        # Insert new data into database
        try:
            TA_db_entry = {'cal_file_name': self.filename,
                           'obs_end_time': end_time,
                           'exp_type': self.exp_type,
                           'aperture': self.ta_data.aperture,
                           'detector': detector,
                           'targx': self.ta_data.x_targ,
                           'targy': self.ta_data.y_targ,
                           'offset': self.offset,
                           'full_im_path': self.full_img,
                           'zoom_im_path': self.zoom_img
                           }

            # commented out fot testing. uncomment later.
            #self.stats_table.__table__.insert().execute(TA_db_entry)

            logging.info("Successfully inserted into database. \n")
        except:
            logging.info("Could not insert entry into database. \n")

        return

    def query_for_post_ta_data(self, rootfile):
        """Given a RootFileInfo instance for a TA observation, query the Django models for
        subsequent science data. Do this only for cases where the science data are not dispersed,
        in which case we can examine the source location.

        Parameters
        ----------
        rootfile : jwql.website.apps.jwql.models.RootFileInfo
            Instance corresponding to TA exposure

        Returns
        -------
        sci_entry : jwql.website.apps.jwql.models.RootFileInfo
            Dictionary of information from the RootFileInfo entry of the science observation
        """
        # Query for all entries for the proposal/obsnum of the TA file
        filter_kwargs = {
            'instrument__iexact': rootfile['instrument'],
            'expstart__gte': rootfile['expstart'],
            'proposal__iexact': rootfile['proposal'],
            'obsnum__obsnum': rootfile['root_name'][7:10] #rootfile.obsnum.obsnum
        }
        root_file_info = RootFileInfo.objects.filter(**filter_kwargs)

        # Strip away the TACQ and TACONFIRM entries.
        non_ta_results = []
        for element in root_file_info:
            if (('TACQ' not in element.exp_type) & ('TACONFIRM' not in element.exp_type)):
                non_ta_results.append(element)

        # There should never be an exposure prior to the TA, so the earliest exptime from the non-TA
        # exposures should be the entry we want.
        expstarts = np.array([e.expstart for e in non_ta_results])
        min_loc = np.where(expstarts == np.min(expstarts))[0]
        sci_entry = non_ta_results[min_loc[0]]

        return sci_entry


    def remove_dithered_ta_files(self):
        """For NIRISS AMI and SOSS TA data, there are three dithers associated with
        each TA sequence. These are followed by a TACONFIRM file. We are only interested
        in the first of the three dithers, so remove the entries for dithers 2 and 3


        for f in root_file_info:
            print(f.instrument, f.exp_type, f.proposal, f.obsnum.obsnum, f.aperture, f.filter, f.pupil)

        NIRISS NIS_TACONFIRM 1093 001 NIS_AMITA F480M NRM
        NIRISS NIS_TACQ 1093 001 NIS_AMITA F480M NRM
        NIRISS NIS_TACQ 1093 001 NIS_AMITA F480M NRM
        NIRISS NIS_TACQ 1093 001 NIS_AMITA F480M NRM
        NIRISS NIS_TACONFIRM 1092 010 NIS_SOSSTA F480M CLEARP
        NIRISS NIS_TACQ 1092 010 NIS_SOSSTA F480M CLEARP
        NIRISS NIS_TACQ 1092 010 NIS_SOSSTA F480M CLEARP
        NIRISS NIS_TACQ 1092 010 NIS_SOSSTA F480M CLEARP
        NIRISS NIS_TACONFIRM 1092 001 NIS_SOSSTA F480M CLEARP
        NIRISS NIS_TACQ 1092 001 NIS_SOSSTA F480M CLEARP
        NIRISS NIS_TACQ 1092 001 NIS_SOSSTA F480M CLEARP
        NIRISS NIS_TACQ 1092 001 NIS_SOSSTA F480M CLEARP
        """
        self.ta_query_results = []

        exptypes = np.array([row['exp_type'] for row in self.ta_entries])
        expstarts = np.array([row['expstart'] for row in self.ta_entries])
        #program_obsnum = np.array([f'{row['proposal']}{row.obsnum.obsnum}' for row in self.ta_entries])
        program_obsnum = np.array([f'{row["root_name"][7:10]}' for row in self.ta_entries])

        unique_program_obsnums = set(program_obsnum)


        print('NIS check')
        print(unique_program_obsnums)
        print(program_obsnum)
        print(expstarts)
        print(exptypes)



        for probs in unique_program_obsnums:
            match = np.where(program_obsnum == probs)[0]
            # For each program/observation combination, we should have 4 entries.
            # 3 TA images and 1 TACONFIRM
            if len(match) != 4:
                raise ValueError(f"WARNING: expected 4 entries for NIRISS TA/TACONFIRM in program {probs[0:-3]}, observation {probs[-3:]} but instead found {len(match)}")


            print('NIS')
            print(match)
            print(expstarts)

            earliest = np.where(expstarts[match] == np.min(expstarts[match]))[0]
            latest = np.where(expstarts[match] == np.max(expstarts[match]))[0]

            # Make sure the earliest file is a TACQ image and the latest is a TACONFIRM
            if exptypes[match][earliest] != 'NIS_TACQ':
                raise ValueError(f"WARNING: earliest file in program {probs[0:-3]}, observation {probs[-3:]} should be NIS_TACQ but is instead {exptypes[match][earliest]}")
            if exptypes[match][latest] != 'NIS_TACONFIRM':
                raise ValueError(f"WARNING: latest file in program {probs[0:-3]}, observation {probs[-3:]} should be NIS_TACONFIRM but is instead {exptypes[match][earliest]}")

            #updated_exp_list.append(self.ta_entries[match][earliest]) this will not work. cannot index the queryset with a numpy array

            # This is super ugly, but should work
            #updated_exp_list.append(self.ta_entries[int(list(match)[earliest[0]])])
            #updated_exp_list.append(self.ta_entries[int(list(match)[latest[0]])])

            # Set up the results as a dictionary where the key is the TACQ RootFileInfo entry, and the value is
            # the TACONFIRM RootFileEntry (this is still ugly)
            self.ta_query_results.append((self.ta_entries[int(list(match)[earliest[0]])], self.ta_entries[int(list(match)[latest[0]])]))

    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for additional info

        Queries MAST for new MIRI TA data and produces images of the ROI.
        Records the target coordinates and offset to the stats database for
        this monitor.
        """

        logging.info('Begin logging for TA Monitor')

        # Get list of exp_types
        #exp_type_list = ['NRC_TACQ', 'MIR_TACQ', 'NRS_TACQ', 'NIS_TACQ']

        # Loop through TA apertures and process new data
        #for exp_type in exp_type_list:
        for instrument in ['nircam', 'niriss', 'miri']:
            logging.info(f'Working on {instrument}')

            self.instrument = instrument
            self.exp_type = [f'{JWST_INSTRUMENT_NAMES_ABBREVIATIONS[instrument]}_TACQ',
                             f'{JWST_INSTRUMENT_NAMES_ABBREVIATIONS[instrument]}_TACONFIRM'
                             ]

            # Identify which tables to use
            #####SKIP FOR NOW IN EARLY DEVELOPMENT. UNCOMMENT LATER
            #self.identify_tables()

            # We start by querying for new data
            #Skip during development at the moment
            #self.query_start = self.most_recent_search()
            #self.query_end = Time.now().mjd

            # Query via django model rather than mast. Leave the aperture value as an empty
            # string so that the query will look for all apertures. This will query for TACQ
            # and TACONFIRM data

            ######!!!!!FOR DEVELOPMENT ######
            # NIRCam
            # 59714 - will get the TA image for NIRCam PID 1068 obs 7 - 2022-05-15 16:23:43
            # jw01068007001_02102_00001-seg001_nrcalong_rate.fits
            # 59714.5 - 59714.8
            #
            # NIRISS
            # AMI
            # JW01093002001_02101_00001_NIS_rate.fits
            # 59722.33 - 59722.375
            # 2022-05-23 08:24
            #
            # SOSS
            # JW01541001001_02101_00001-SEG001_NIS_RATE.fits
            # 2022-06-08T06:16:09.084
            # 59738.25 - 59738.3
            #
            # MIRI
            # LRS - fixed slit
            # JW01033001001_02101_00001_MIRIMAGE_RATE.fits
            # 2022-05-26T10:27:51.288
            # 59725.4 - 59725.5
            #
            # LRS slitless
            # JW01353005001_02101_00001-SEG001_MIRIMAGE_RATE.fits
            # 2023-03-12T23:25:06.923
            # 60015.95 - 60016.
            if instrument == 'nircam':
                self.query_start = 59714.5
                self.query_end = 59714.8
            elif instrument == 'niriss':
                self.query_start = 59722.33
                self.query_end = 59722.380
            elif instrument == 'miri':
                self.query_start = 60112.
                self.query_end = 60138.
            ######!!!!!FOR DEVELOPMENT ######


            self.ta_entries = model_query_ta(self.instrument, '', self.query_start, self.query_end)


            print(self.ta_entries)

            #For nircam: the results are:
            #<QuerySet [<RootFileInfo: jw01068007001_02102_00001-seg001_nrcalong>, <RootFileInfo: jw01068006001_02102_00001-seg001_nrcblong>, <RootFileInfo: jw01068005001_02102_00001-seg001_nrcblong>]>


            # Organize the query results. Remove entries for coron observations and TACQ files we
            # don't care about.
            self.organize_ta_files()

            # At this point, self.ta_query_results is now a list of tuples, with keys equal to the RootFileInfo entries of
            # the TACQ files, and values equal to the RootFileInfo entry for the associated TACONFIRM entries. In
            # this case (non-coron) there will never be >1 TACONFIRM entry associated with a given TACQ entry.

            """
In [22]: root_file_info[0].__dict__
Out[22]:
{'_state': <django.db.models.base.ModelState at 0x7f50c11125e0>,
 'instrument': 'MIRI',
 'obsnum_id': 5740,
 'proposal': '4436',
 'root_name': 'jw04436002001_03103_00002_mirimage',
 'viewed': False,
 'filter': 'P750L',
 'aperture': 'MIRIM_SLIT',
 'detector': 'MIRIMAGE',
 'read_patt_num': 2,
 'read_patt': 'FASTR1',
 'grating': '',
 'subarray': 'FULL',
 'pupil': '',
 'exp_type': 'MIR_LRS-FIXEDSLIT',
 'expstart': 60067.78642318056}

            """


            # Work through self.ta_query_results one entry at a time
            # for each entry, depending on the mode, we will potentially need to query for the science
            # data that followed the ta/taconfirm



            # At this point, the entries in self.ta_query_results should be 3-tuples, with the RootFileInfo
            # obj for the TA file, TACONFIRM file, and that for the following science file. If either of the
            # latter two don't exist, then they will be set to None.

            num_new_tas = len(self.ta_query_results)


            logging.info(f'Number of new TA files: {num_new_tas}')




            if num_new_tas > 0:


                # Query the Django models and retrieve the related science data taken after the TA.
                # For imaging modes, we should grab the first science file after the TA. For LRS, we
                # need to find the post-observation image (if it exists. It was not always required.)
                # Should we bother with this for dispersed data??
                self.get_post_ta_data()

                ta_files_processed = []
                for ta, ta_confirm, science in self.ta_query_results:
                    ta_fullpath, ta_confirm_fullpath, science_fullpath = None, None, None
                    if ta is not None:
                        ta_fullpath = find_in_filesystem(f'{ta["root_name"]}_rate.fits')
                    if ta_confirm is not None:
                        ta_confirm_fullpath = find_in_filesystem(f'{ta_confirm["root_name"]}_rate.fits')
                    if science is not None:
                        science_fullpath = find_in_filesystem(f'{science}_rate.fits')  # or should we grab cal?


                    logging.info(f'TA file: {ta_fullpath}')
                    logging.info(f'TA conf file: {ta_confirm_fullpath}')
                    logging.info(f'Science file: {science_fullpath}')

                    if ta_fullpath is not None:
                        self.process(ta_fullpath, ta_confirm_fullpath, science_fullpath)
                        ta_files_processed.append(f'{ta["root_name"]}_rate.fits')

                if len(ta_files_processed) > 0:
                    monitor_run = True
                else:
                    monitor_run = False
            else:
                monitor_run = False




            new_entry = {'instrument': self.instrument,
                         'exp_type': self.exp_type[0],
                         'start_time_mjd': self.query_start,
                         'end_time_mjd': self.query_end,
                         'files_found': num_new_tas,
                         'files_run': len(ta_files_processed),
                         'run_monitor': monitor_run,
                         'entry_date': datetime.datetime.now()}
            # Skip making a database entry for the moment
            #self.query_table.__table__.insert().execute(new_entry)

            #logging.info(f'\tUpdated the query history table with {sef.instrument} results.')
            #logging.info(f'\t{new_entry}')




class CoronTAMonitor(TAMonitor):
    """TA montior designed specifically to work the coronagraphic observations. Shares some initial
    analysis and plots with the general TA monitor.
    """
    def __init__(self):
        pass


def calc_target_xy(V2_ref, V3_ref, RA_ref, DEC_ref, roll_ref, RA_targ, DEC_targ):
    """Calculate the target's x, y location on the detector. Do this using the reference
    location's RA, Dec, V2, V3, creating an attitude matrix, calculating the target's
    V2, V3, and then converting to x, y
    """
    attitude = define_attitude(V2_ref, V3_ref, RA_ref, DEC_ref, roll_ref)
    v2_targ, v3_targ = rotations.getv2v3(attitude, RA_targ, DEC_targ)
    x_targ, y_targ = self.ap_siaf.tel_to_sci(v2_targ, v3_targ)
    return x_targ, y_targ


def define_attitude(v2_ref, v3_ref, ra_ref, dec_ref, v3pa):
    """
    Define an attitude matrix (pysiaf.utils.rotations)

    Parameters
    ----------
    v3pa:
        position angle of the v3 axis in degrees
    """
    attitude = rotations.attitude(v2_ref, v3_ref, ra_ref, dec_ref, v3pa)
    return attitude

def find_in_filesystem(filename):
    """Locate a file in the filesystem. If it's not present, return None

    Parameters
    ----------
    filename : str
        Name of file to search for. e.g. jw01068001001_02101_00001_nrcalong_rate.fits

    Returns
    -------
    file_full_path : str
        Full pathname of ``filename``. If the file is not found in the filesystem,
        then None is returned.
    """
    try:
        if filename is not None:
            file_full_path = filesystem_path(filename)
        else:
            file_full_path = None
    except FileNotFoundError:
        logging.info(f'\t{filename} not found in filesystem. Skipping.')
        file_full_path = None
    except ValueError:
        logging.info(
            f'\tProvided file {filename} does not follow JWST naming conventions. Skipping.')
        file_full_path = None
    return file_full_path




if __name__ == "__main__":

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    # Call the main function
    monitor = TAMonitor()
    monitor.run()