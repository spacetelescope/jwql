#! /usr/bin/env python

"""This module contains code for the claw monitor.

Author
------
    - Ben Sunnquist

Use
---
    This module can be used from the command line as such:

    ::

        python claw_monitor.py

    To only update the background trending plots:

    ::

        m = ClawMonitor()
        m.make_background_plots()
"""

import datetime
import logging
import os

from astropy.convolution import Gaussian2DKernel, convolve
from astropy.io import fits
from astropy.stats import gaussian_fwhm_to_sigma, sigma_clipped_stats
from astropy.time import Time
from astropy.visualization import ZScaleInterval
from astroquery.mast import Mast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from photutils.segmentation import detect_sources, detect_threshold

from jwql.database.database_interface import session, engine
from jwql.database.database_interface import NIRCamClawQueryHistory, NIRCamClawStats
from jwql.utils import monitor_utils
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config


class ClawMonitor():
    """Class for executing the claw monitor.

    This class searches for all new NIRCam full-frame imaging data
    and creates observation-level, source-masked, median stacks
    for each filter/pupil combination. These stacks are then plotted
    in on-sky orientation and the results are used to identify new
    instances of claws - a scattered light effect seen in NIRCam
    data. Background statistics are also stored for each individual
    image, which are then plotted to track the NIRCam background
    levels over time. Results are all saved to database tables.

    Attributes
    ----------
    outfile : str
        The name of the output plot for a given claw stack combination.

    output_dir : str
        Path into which claw stack plots will be placed.

    output_dir_bkg : str
        Path into which background trending plots will be placed.

    query_start : float
        MJD start date to use for querying MAST.

    query_end : float
        MJD end date to use for querying MAST.

    wv : str
        NIRCam channel for a given claw stack, either ``SW`` or ``LW``.

    proposal : str
        NIRCam proposal number for a given claw stack.

    obs : str
        NIRCam observation number for a given claw stack.

    fltr : str
        NIRCam filter used for a given claw stack.

    pupil : str
        NIRCam pupil used for a given claw stack.

    detectors : str
        The detectors used for a given claw stack combination.

    files : numpy.ndarray
        The names of the individual files belonging to a given claw stack combination.
    """

    def __init__(self):
        """Initialize an instance of the ``ClawMonitor`` class.
        """

        # Define and setup the output directories for the claw and background plots.
        self.output_dir = os.path.join(get_config()['outputs'], 'claw_monitor', 'claw_stacks')
        ensure_dir_exists(self.output_dir)
        self.output_dir_bkg = os.path.join(get_config()['outputs'], 'claw_monitor', 'backgrounds')
        ensure_dir_exists(self.output_dir_bkg)

        # Get the claw monitor database tables
        self.query_table = eval('NIRCamClawQueryHistory')
        self.stats_table = eval('NIRCamClawStats')

    def make_background_plots(self):
        """Makes plots of the background levels over time in NIRCam data.
        """

        # Get all of the background data.
        query = session.query(NIRCamClawStats.filename, NIRCamClawStats.filter, NIRCamClawStats.pupil, NIRCamClawStats.detector,
                              NIRCamClawStats.effexptm, NIRCamClawStats.expstart_mjd, NIRCamClawStats.entry_date, NIRCamClawStats.mean,
                              NIRCamClawStats.median, NIRCamClawStats.frac_masked).all()
        df_orig = pd.DataFrame(query, columns=['filename', 'filter', 'pupil', 'detector', 'effexptm', 'expstart_mjd',
                                               'entry_date', 'mean', 'median', 'frac_masked'])
        df_orig = df_orig.drop_duplicates(subset='filename', keep="last")  # remove any duplicate filename entries, keep the most recent

        # Use the same time xlimits/xticks for all plots
        start_mjd = 59650  # March 2022, middle of commissioning
        end_mjd = Time.now().mjd + 0.05 * (Time.now().mjd - start_mjd)
        time_tick_vals = np.linspace(start_mjd, end_mjd, 5)
        time_tick_labels = [Time(m, format='mjd').isot.split('T')[0] for m in time_tick_vals]

        # Make backgroud trending plots for all wide filters
        for fltr in ['F070W', 'F090W', 'F115W', 'F150W', 'F200W', 'F277W', 'F356W', 'F444W']:
            logging.info('Working on background trending plots for {}'.format(fltr))
            if int(fltr[1:4]) < 250:  # i.e. SW
                detectors_to_run = ['NRCA2', 'NRCA4', 'NRCB3', 'NRCB1', 'NRCA1', 'NRCA3', 'NRCB4', 'NRCB2']   # in on-sky order, don't change order
                grid = plt.GridSpec(2, 4, hspace=.4, wspace=.4, width_ratios=[1, 1, 1, 1])
                fig = plt.figure(figsize=(40, 20))
                fig.suptitle(fltr, fontsize=70)
                frack_masked_thresh = 0.075
            else:  # i.e. LW
                detectors_to_run = ['NRCALONG', 'NRCBLONG']
                grid = plt.GridSpec(1, 2, hspace=.2, wspace=.4, width_ratios=[1, 1])
                fig = plt.figure(figsize=(20, 10))
                fig.suptitle(fltr, fontsize=70, y=1.05)
                frack_masked_thresh = 0.15
            for i, det in enumerate(detectors_to_run):
                logging.info('Working on {}'.format(det))

                # Get relevant data for this filter/detector and remove bad datasets, e.g. crowded fields,
                # extended objects, nebulas, short exposures.
                df = df_orig[(df_orig['filter'] == fltr) & (df_orig['pupil'] == 'CLEAR') & (df_orig['detector'] == det) &
                             (df_orig['effexptm'] > 300) & (df_orig['frac_masked'] < frack_masked_thresh) &
                             (abs(1 - (df_orig['mean'] / df_orig['median'])) < 0.05)]

                # Plot the background levels over time
                ax = fig.add_subplot(grid[i])
                ax.scatter(df['expstart_mjd'], df['median'])

                # Match scaling in all plots to the first detector. Shade median+/-10% region.
                if len(df) > 0:
                    if i == 0:
                        first_med = np.nanmedian(df['median'])
                    ax.set_ylim(first_med - first_med * 0.5, first_med + first_med * 0.5)
                    med = np.nanmedian(df['median'])
                    ax.axhline(med, ls='-', color='black')
                    ax.axhspan(med - med * 0.1, med + med * 0.1, color='gray', alpha=0.4, lw=0)

                # Axis formatting
                ax.set_title(det, fontsize=40)
                ax.set_xlim(start_mjd, end_mjd)
                ax.set_xticks(time_tick_vals)
                ax.set_xticklabels(time_tick_labels, fontsize=20, rotation=45)
                ax.yaxis.set_tick_params(labelsize=20)
                ax.set_ylabel('Background [MJy/sr]', fontsize=30)
                # ax.set_xlabel('Date [YYYY-MM-DD]')
                ax.grid(ls='--', color='gray')
            fig.savefig(os.path.join(self.output_dir_bkg, '{}_backgrounds.png'.format(fltr)), dpi=180, bbox_inches='tight')
            fig.clf()
            plt.close()

    def process(self):
        """The main method for processing.  See module docstrings for further details.
        """

        # Get detector order and plot settings, depending on the wavelength channel
        if self.wv == 'SW':
            detectors_to_run = ['NRCA2', 'NRCA4', 'NRCB3', 'NRCB1', 'NRCA1', 'NRCA3', 'NRCB4', 'NRCB2']  # in on-sky order, don't change order
            cols, rows = 5, 2
            grid = plt.GridSpec(rows, cols, hspace=.2, wspace=.2, width_ratios=[1, 1, 1, 1, .1])
            fig = plt.figure(figsize=(40, 20))
            cbar_fs = 20
            fs = 30
        else:
            detectors_to_run = ['NRCALONG', 'NRCBLONG']
            cols, rows = 3, 1
            grid = plt.GridSpec(rows, cols, hspace=.2, wspace=.2, width_ratios=[1, 1, .1])
            fig = plt.figure(figsize=(20, 10))
            cbar_fs = 10
            fs = 20

        # Make source-masked, median-stack of each detector's images
        found_scale = False
        for i, det in enumerate(detectors_to_run):
            logging.info('Working on {}'.format(det))
            files = self.files[self.detectors == det]
            # Remove missing files; to avoid memory/speed issues, only use the first 20 files,
            # which should be plenty to see any claws.
            files = [f for f in files if os.path.exists(f)][0:20]
            stack = np.ma.ones((len(files), 2048, 2048))
            for n, f in enumerate(files):
                logging.info('Working on: {}'.format(f))
                h = fits.open(f)

                # Get plot label info from first image
                if n == 0:
                    obs_start = '{}T{}'.format(h[0].header['DATE-OBS'], h[0].header['TIME-OBS'])
                    pa_v3 = h[1].header['PA_V3']

                # Make source segmap, add the masked data to the stack, and get background stats
                data = h['SCI'].data
                dq = h['DQ'].data
                threshold = detect_threshold(data, 1.0)
                sigma = 3.0 * gaussian_fwhm_to_sigma  # FWHM = 3.
                kernel = Gaussian2DKernel(sigma, x_size=3, y_size=3)
                kernel.normalize()
                data_conv = convolve(data, kernel)
                segmap = detect_sources(data_conv, threshold, npixels=6)
                segmap = segmap.data
                segmap[dq & 1 != 0] = 1  # flag DO_NOT_USE pixels
                stack[n] = np.ma.masked_array(data, mask=segmap != 0)
                mean, med, stddev = sigma_clipped_stats(data[segmap == 0])

                # Add this file's stats to the claw database table. Can't insert values with numpy.float32
                # datatypes into database so need to change the datatypes of these values.
                claw_db_entry = {'filename': os.path.basename(f),
                                 'proposal': self.proposal,
                                 'obs': self.obs,
                                 'detector': det.upper(),
                                 'filter': self.fltr.upper(),
                                 'pupil': self.pupil.upper(),
                                 'expstart': '{}T{}'.format(h[0].header['DATE-OBS'], h[0].header['TIME-OBS']),
                                 'expstart_mjd': h[0].header['EXPSTART'],
                                 'effexptm': h[0].header['EFFEXPTM'],
                                 'ra': h[1].header['RA_V1'],
                                 'dec': h[1].header['DEC_V1'],
                                 'pa_v3': h[1].header['PA_V3'],
                                 'mean': float(mean),
                                 'median': float(med),
                                 'stddev': float(stddev),
                                 'frac_masked': len(segmap[segmap != 0]) / (segmap.shape[0] * segmap.shape[1]),
                                 'skyflat_filename': os.path.basename(self.outfile),
                                 'entry_date': datetime.datetime.now()
                                 }
                with engine.begin() as connection:
                    connection.execute(self.stats_table.__table__.insert(), claw_db_entry)
                h.close()

            # Make the normalized skyflat for this detector
            skyflat = np.ma.median(stack, axis=0)
            skyflat = skyflat.filled(fill_value=np.nan)
            skyflat = skyflat / np.nanmedian(skyflat)
            skyflat[~np.isfinite(skyflat)] = 1  # fill missing values

            # Add the skyflat for this detector to the claw stack plot
            if (self.wv == 'SW') & (i > 3):  # skip colobar axis
                idx = i + 1
            else:
                idx = i
            ax = fig.add_subplot(grid[idx])
            if len(skyflat[skyflat != 1]) == 0:
                ax.set_title('N/A', fontsize=fs)
                ax.imshow(skyflat, cmap='coolwarm', vmin=999, vmax=999, origin='lower')
            elif (len(skyflat[skyflat != 1]) > 0) & (found_scale is False):  # match scaling to first non-empty stack
                z = ZScaleInterval()
                vmin, vmax = z.get_limits(skyflat)
                found_scale = True
                ax.set_title(det, fontsize=fs)
                im = ax.imshow(skyflat, cmap='coolwarm', vmin=vmin, vmax=vmax, origin='lower')
            else:
                ax.set_title(det, fontsize=fs)
                im = ax.imshow(skyflat, cmap='coolwarm', vmin=vmin, vmax=vmax, origin='lower')
            ax.axes.get_xaxis().set_ticks([])
            ax.axes.get_yaxis().set_ticks([])

        # Add colobar, save figure if any claw stacks exist
        if found_scale:
            fig.suptitle('PID-{} OBS-{} {} {}\n{}  pa_v3={}\n'.format(self.proposal, self.obs, self.fltr.upper(),
                         self.pupil.upper(), obs_start.split('.')[0], pa_v3), fontsize=fs * 1.5)
            cax = fig.add_subplot(grid[0:rows, cols - 1:cols])
            cbar = fig.colorbar(im, cax=cax, orientation='vertical')
            cbar.ax.tick_params(labelsize=cbar_fs)
            fig.savefig(self.outfile, dpi=100, bbox_inches='tight')
        fig.clf()
        plt.close()
        logging.info('Claw stacks complete: {}'.format(self.outfile))

    def query_mast(self):
        """Query MAST for new NIRCam full-frame imaging data.

        Returns
        -------
        t : astropy.table.table.Table
            A table summarizing the new nircam imaging data.
        """

        server = "https://mast.stsci.edu"
        JwstObs = Mast()
        JwstObs._portal_api_connection.MAST_REQUEST_URL = server + "/portal_jwst/Mashup/Mashup.asmx/invoke"
        JwstObs._portal_api_connection.MAST_DOWNLOAD_URL = server + "/jwst/api/v0.1/download/file"
        JwstObs._portal_api_connection.COLUMNS_CONFIG_URL = server + "/portal_jwst/Mashup/Mashup.asmx/columnsconfig"
        JwstObs._portal_api_connection.MAST_BUNDLE_URL = server + "/jwst/api/v0.1/download/bundle"
        service = 'Mast.Jwst.Filtered.Nircam'
        FIELDS = ['filename', 'program', 'observtn', 'category', 'instrume', 'productLevel', 'filter',
                  'pupil', 'subarray', 'detector', 'datamodl', 'date_beg_mjd', 'effexptm']
        params = {"columns": ",".join(FIELDS),
                  "filters": [{"paramName": "pupil", "values": ['CLEAR', 'F162M', 'F164N', 'F323N', 'F405N', 'F466N', 'F470N']},
                              {"paramName": "exp_type", "values": ['NRC_IMAGE']},
                              {"paramName": "datamodl", "values": ['ImageModel']},  # exclude calints, which are cubemodel
                              {"paramName": "productLevel", "values": ['2b']},  # i.e. cal.fits
                              {"paramName": "subarray", "values": ['FULL']}, ]
                  }
        t = JwstObs.service_request(service, params)
        t = t[(t['date_beg_mjd'] > self.query_start_mjd) & (t['date_beg_mjd'] < self.query_end_mjd)]
        t.sort('date_beg_mjd')
        filetypes = np.array([row['filename'].split('_')[-1].replace('.fits', '') for row in t])
        t = t[filetypes == 'cal']  # only want cal.fits files, no e.g. i2d.fits

        return t

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details."""

        logging.info('Begin logging for claw_monitor')

        # Query MAST for new NIRCam full-frame imaging data from the last 2 days
        self.query_end_mjd = Time.now().mjd
        self.query_start_mjd = self.query_end_mjd - 2
        t = self.query_mast()
        logging.info('{} files found between {} and {}.'.format(len(t), self.query_start_mjd, self.query_end_mjd))

        # Create observation-level median stacks for each filter/pupil combo, in pixel-space
        combos = np.array(['{}_{}_{}_{}'.format(str(row['program']), row['observtn'], row['filter'], row['pupil']).lower() for row in t])
        t['combos'] = combos
        monitor_run = False
        for combo in np.unique(combos):
            tt = t[t['combos'] == combo]
            if 'long' in tt['filename'][0]:
                self.wv = 'LW'
            else:
                self.wv = 'SW'
            self.proposal, self.obs, self.fltr, self.pupil = combo.split('_')
            self.outfile = os.path.join(self.output_dir, 'prop{}_obs{}_{}_{}_cal_norm_skyflat.png'.format(str(self.proposal).zfill(5),
                                        self.obs, self.fltr, self.pupil).lower())
            self.files = np.array([filesystem_path(row['filename']) for row in tt])
            self.detectors = np.array(tt['detector'])
            if not os.path.exists(self.outfile):
                logging.info('Working on {}'.format(self.outfile))
                self.process()
                monitor_run = True
            else:
                logging.info('{} already exists'.format(self.outfile))

        # Update the background trending plots, if any new data exists
        if len(t) > 0:
            logging.info('Making background trending plots.')
            self.make_background_plots()

        # Update the query history
        new_entry = {'instrument': 'nircam',
                     'start_time_mjd': self.query_start_mjd,
                     'end_time_mjd': self.query_end_mjd,
                     'run_monitor': monitor_run,
                     'entry_date': datetime.datetime.now()}
        with engine.begin() as connection:
            connection.execute(self.query_table.__table__.insert(), new_entry)

        logging.info('Claw Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = ClawMonitor()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
