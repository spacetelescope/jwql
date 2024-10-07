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
import warnings

from astropy.convolution import Gaussian2DKernel, convolve
from astropy.io import fits
from astropy.stats import gaussian_fwhm_to_sigma, sigma_clipped_stats
from astropy.table import Table
from astropy.time import Time
from astroquery.mast import Mast
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from photutils.segmentation import detect_sources, detect_threshold
from scipy.ndimage import binary_dilation

from jwql.utils import monitor_utils
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config
from jwst_backgrounds import jbt

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # Need to set up django apps before we can access the models
    import django  # noqa: E402 (module level import not at top of file)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()

    # Import * is okay here because this module specifically only contains database models
    # for this monitor
    from jwql.website.apps.jwql.monitor_models.claw import *  # noqa: E402 (module level import not at top of file)

matplotlib.use('Agg')
warnings.filterwarnings('ignore', message="nan_treatment='interpolate', however, NaN values detected post convolution*")
warnings.filterwarnings('ignore', message='Input data contains invalid values (NaNs or infs)*')


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

    output_dir_claws : str
        Path into which claw stack plots will be placed.

    output_dir_bkg : str
        Path into which background trending plots will be placed.

    query_start : float
        MJD start date to use for querying MAST.

    query_end : float
        MJD end date to use for querying MAST.

    channel : str
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
        self.output_dir_claws = os.path.join(get_config()['outputs'], 'claw_monitor', 'claw_stacks')
        ensure_dir_exists(self.output_dir_claws)
        self.output_dir_bkg = os.path.join(get_config()['outputs'], 'claw_monitor', 'backgrounds')
        ensure_dir_exists(self.output_dir_bkg)

        # Get the claw monitor database tables
        self.query_table = NIRCamClawQueryHistory
        self.stats_table = NIRCamClawStats

    def make_background_plots(self, plot_type='bkg'):
        """Makes plots of the background levels over time in NIRCam data.

        Attributes
        ----------
        plot_type : str
            The type of plot to make, either ``bkg`` for background trending,
            ``bkg_rms`` for background rms trending, or ``model`` for background
            measured vs model trending.
        """

        columns = ['filename', 'filter', 'pupil', 'detector', 'effexptm', 'expstart_mjd', 'entry_date', 'mean', 'median',
                   'stddev', 'frac_masked', 'total_bkg']

        # Get all of the background data.
        background_data = NIRCamClawStats.objects.all().values(*columns)
        df_orig = pd.DataFrame.from_records(background_data)
        # remove any duplicate filename entries, keep the most recent
        df_orig = df_orig.drop_duplicates(subset='filename', keep="last")

        # Get label info based on plot type
        if plot_type == 'bkg':
            plot_title = 'backgrounds'
            plot_label = 'Background [MJy/sr]'
        if plot_type == 'bkg_rms':
            plot_title = 'backgrounds_rms'
            plot_label = 'Background RMS [MJy/sr]'
        if plot_type == 'model':
            plot_title = 'backgrounds_vs_models'
            plot_label = 'Measured / Predicted'

        # Make backgroud trending plots for all wide filters
        for fltr in ['F070W', 'F090W', 'F115W', 'F150W', 'F200W', 'F277W', 'F356W', 'F444W']:
            logging.info('Working on {} trending plots for {}'.format(plot_title, fltr))
            found_limits = False
            if int(fltr[1:4]) < 250:  # i.e. SW
                # in on-sky order, don't change order
                detectors_to_run = ['NRCA2', 'NRCA4', 'NRCB3', 'NRCB1', 'NRCA1', 'NRCA3', 'NRCB4', 'NRCB2']
                grid = plt.GridSpec(2, 4, hspace=.4, wspace=.4, width_ratios=[1, 1, 1, 1])
                fig = plt.figure(figsize=(45, 20))
                fig.suptitle(fltr, fontsize=70)
                frack_masked_thresh = 0.075
            else:  # i.e. LW
                detectors_to_run = ['NRCALONG', 'NRCBLONG']
                grid = plt.GridSpec(1, 2, hspace=.2, wspace=.4, width_ratios=[1, 1])
                fig = plt.figure(figsize=(25, 10))
                fig.suptitle(fltr, fontsize=70, y=1.05)
                frack_masked_thresh = 0.15
            for i, det in enumerate(detectors_to_run):
                logging.info('Working on {}'.format(det))

                # Get relevant data for this filter/detector and remove bad datasets, e.g. crowded fields,
                # extended objects, nebulas, short exposures.
                df = df_orig[(df_orig['filter'] == fltr) & (df_orig['pupil'] == 'CLEAR') & (df_orig['detector'] == det)
                             & (df_orig['effexptm'] > 300) & (df_orig['frac_masked'] < frack_masked_thresh)
                             & (abs(1 - (df_orig['mean'] / df_orig['median'])) < 0.05)]
                if len(df) > 0:
                    df = df.sort_values(by=['expstart_mjd'])

                # Get relevant background stat for plot type
                if plot_type == 'bkg':
                    plot_data = df['median'].values
                if plot_type == 'bkg_rms':
                    df = df[df['stddev'] != 0]  # older data has no accurate stddev measures
                    plot_data = df['stddev'].values
                if plot_type == 'model':
                    df = df[np.isfinite(df['total_bkg'])]  # the claw monitor did not track model measurements at first
                    plot_data = df['median'].values / df['total_bkg'].values
                plot_expstarts = df['expstart_mjd'].values

                # Plot the background data over time
                ax = fig.add_subplot(grid[i])
                ax.scatter(plot_expstarts, plot_data, alpha=0.3)

                # Match scaling in all plots to the first detector with data.
                if len(df) > 0:
                    if found_limits is False:
                        first_mean, first_med, first_stddev = sigma_clipped_stats(plot_data)
                        start_mjd = plot_expstarts.min()
                        end_mjd = Time.now().mjd
                        padding = 0.05 * (end_mjd - start_mjd)
                        start_mjd = start_mjd - padding
                        end_mjd = end_mjd + padding
                        time_tick_vals = np.linspace(start_mjd, end_mjd, 5)
                        time_tick_labels = [Time(m, format='mjd').isot.split('T')[0] for m in time_tick_vals]
                        found_limits = True
                    ax.set_ylim(first_med - 8 * first_stddev, first_med + 8 * first_stddev)

                    # Plot overall median line with shaded stddev
                    mean, med, stddev = sigma_clipped_stats(plot_data)
                    ax.axhline(med, ls='-', color='black')
                    ax.axhspan(med - stddev, med + stddev, color='gray', alpha=0.4, lw=0)
                else:
                    start_mjd, end_mjd, time_tick_vals, time_tick_labels = 0, 1, [0.5], ['N/A']

                # Axis formatting
                ax.set_title(det, fontsize=40)
                ax.set_xlim(start_mjd, end_mjd)
                ax.set_xticks(time_tick_vals)
                ax.set_xticklabels(time_tick_labels, fontsize=20, rotation=45)
                ax.yaxis.set_tick_params(labelsize=20)
                ax.set_ylabel(plot_label, fontsize=30)
                ax.grid(ls='--', color='gray')
            fig.savefig(os.path.join(self.output_dir_bkg, '{}_{}.png'.format(fltr, plot_title)), dpi=180, bbox_inches='tight')
            fig.clf()
            plt.close()

    def process(self):
        """The main method for processing.  See module docstrings for further details.
        """

        # Get detector order and plot settings, depending on the wavelength channel
        if self.channel == 'SW':
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
            files = [fname for fname in files if os.path.exists(fname)][0:20]
            stack = np.ma.ones((len(files), 2048, 2048))
            for n, fname in enumerate(files):
                logging.info('Working on: {}'.format(fname))
                hdu = fits.open(fname)

                # Get plot label info from first image
                if n == 0:
                    obs_start = '{}T{}'.format(hdu[0].header['DATE-OBS'], hdu[0].header['TIME-OBS'])
                    pa_v3 = hdu[1].header['PA_V3']

                # Make source segmap and add the masked data to the stack
                data = hdu['SCI'].data
                dq = hdu['DQ'].data
                threshold = detect_threshold(data, 1.0)
                sigma = 3.0 * gaussian_fwhm_to_sigma  # FWHM = 3.
                kernel = Gaussian2DKernel(sigma, x_size=3, y_size=3)
                kernel.normalize()
                data_conv = convolve(data, kernel)
                segmap_orig = detect_sources(data_conv, threshold, npixels=6)
                segmap_orig = segmap_orig.data
                stack[n] = np.ma.masked_array(data, mask=(segmap_orig != 0) | (dq & 1 != 0))

                # Calculate image stats. Before calculating, expand segmap of extended objects.
                # This is only done after adding the data to the claw stack to avoid flagging the claws
                # themselves from those stacks, but is needed here since extended wings can impact image
                # stats, mainly the stddev.
                objects, object_counts = np.unique(segmap_orig, return_counts=True)
                large_objects = objects[(object_counts > 200) & (objects != 0)]
                segmap_extended = np.zeros(segmap_orig.shape).astype(int)
                for object in large_objects:
                    segmap_extended[segmap_orig == object] = 1
                image_edge_mask = np.zeros(segmap_orig.shape).astype(int)
                image_edge_mask[10:2038, 10:2038] = 1
                segmap_extended[(image_edge_mask == 0) | (dq & 1 != 0)] = 0  # omit edge and other bpix from dilation
                segmap_extended = binary_dilation(segmap_extended, iterations=30).astype(int)
                segmap = segmap_extended + segmap_orig
                mean, med, stddev = sigma_clipped_stats(data[(segmap == 0) & (dq == 0)])

                # Get predicted background level using JWST background tool
                ra, dec = hdu[1].header['RA_V1'], hdu[1].header['DEC_V1']
                if ('N' in self.pupil.upper()) | ('M' in self.pupil.upper()):
                    fltr_wv = self.pupil.upper()
                else:
                    fltr_wv = self.fltr.upper()
                wv = self.filter_wave[fltr_wv]
                date = hdu[0].header['DATE-BEG']
                doy = int(Time(date).yday.split(':')[1])
                try:
                    jbt.get_background(ra, dec, wv, thisday=doy, plot_background=False, plot_bathtub=False,
                                       write_bathtub=True, bathtub_file='background_versus_day.txt')
                    bkg_table = Table.read('background_versus_day.txt', names=('day', 'total_bkg'), format='ascii')
                    total_bkg = bkg_table['total_bkg'][bkg_table['day'] == doy][0]
                except Exception as e:
                    total_bkg = np.nan

                # Add this file's stats to the claw database table. Can't insert values with numpy.float32
                # datatypes into database so need to change the datatypes of these values.
                claw_db_entry = {'filename': os.path.basename(fname),
                                 'proposal': self.proposal,
                                 'obs': self.obs,
                                 'detector': det.upper(),
                                 'filter': self.fltr.upper(),
                                 'pupil': self.pupil.upper(),
                                 'expstart': '{}T{}'.format(hdu[0].header['DATE-OBS'], hdu[0].header['TIME-OBS']),
                                 'expstart_mjd': hdu[0].header['EXPSTART'],
                                 'effexptm': hdu[0].header['EFFEXPTM'],
                                 'ra': ra,
                                 'dec': dec,
                                 'pa_v3': hdu[1].header['PA_V3'],
                                 'mean': float(mean),
                                 'median': float(med),
                                 'stddev': float(stddev),
                                 'frac_masked': len(segmap_orig[(segmap_orig != 0) | (dq & 1 != 0)]) / (segmap_orig.shape[0] * segmap_orig.shape[1]),
                                 'skyflat_filename': os.path.basename(self.outfile),
                                 'doy': float(doy),
                                 'total_bkg': float(total_bkg),
                                 'entry_date': datetime.datetime.now(datetime.timezone.utc)
                                 }
                entry = self.stats_table(**claw_db_entry)
                entry.save()
                hdu.close()

            # Make the normalized skyflat for this detector
            skyflat = np.ma.median(stack, axis=0)
            skyflat = skyflat.filled(fill_value=np.nan)
            skyflat = skyflat / np.nanmedian(skyflat)
            skyflat[~np.isfinite(skyflat)] = 1  # fill missing values

            # Add the skyflat for this detector to the claw stack plot
            if (self.channel == 'SW') & (i > 3):  # skip colobar axis
                idx = i + 1
            else:
                idx = i
            ax = fig.add_subplot(grid[idx])
            if len(skyflat[skyflat != 1]) == 0:
                ax.set_title('N/A', fontsize=fs)
                ax.imshow(skyflat, cmap='coolwarm', vmin=999, vmax=999, origin='lower')
            elif (len(skyflat[skyflat != 1]) > 0) & (found_scale is False):  # match scaling to first non-empty stack
                mean, med, stddev = sigma_clipped_stats(skyflat)
                vmin, vmax = med - 3 * stddev, med + 3 * stddev
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
        mast_table = self.query_mast()
        logging.info('{} files found between {} and {}.'.format(len(mast_table), self.query_start_mjd, self.query_end_mjd))

        # Define pivot wavelengths - last downloaded March 8 2024 from:
        # https://jwst-docs.stsci.edu/jwst-near-infrared-camera/nircam-instrumentation/nircam-filters
        self.filter_wave = {'F070W': 0.704, 'F090W': 0.901, 'F115W': 1.154, 'F140M': 1.404, 'F150W': 1.501, 'F162M': 1.626, 'F164N': 1.644,
                            'F150W2': 1.671, 'F182M': 1.845, 'F187N': 1.874, 'F200W': 1.99, 'F210M': 2.093, 'F212N': 2.12, 'F250M': 2.503,
                            'F277W': 2.786, 'F300M': 2.996, 'F322W2': 3.247, 'F323N': 3.237, 'F335M': 3.365, 'F356W': 3.563, 'F360M': 3.621,
                            'F405N': 4.055, 'F410M': 4.092, 'F430M': 4.28, 'F444W': 4.421, 'F460M': 4.624, 'F466N': 4.654, 'F470N': 4.707,
                            'F480M': 4.834}

        # Create observation-level median stacks for each filter/pupil combo, in pixel-space
        combos = np.array(['{}_{}_{}_{}'.format(str(row['program']), row['observtn'], row['filter'], row['pupil']).lower() for row in mast_table])
        mast_table['combos'] = combos
        monitor_run = False
        for combo in np.unique(combos):
            mast_table_combo = mast_table[mast_table['combos'] == combo]
            if 'long' in mast_table_combo['filename'][0]:
                self.channel = 'LW'
            else:
                self.channel = 'SW'
            self.proposal, self.obs, self.fltr, self.pupil = combo.split('_')
            self.outfile = os.path.join(self.output_dir_claws, 'prop{}_obs{}_{}_{}_cal_norm_skyflat.png'.format(str(self.proposal).zfill(5),
                                        self.obs, self.fltr, self.pupil).lower())
            existing_files = []
            for row in mast_table_combo:
                try:
                    existing_files.append(filesystem_path(row['filename']))
                except Exception as e:
                    pass
            self.files = np.array(existing_files)
            self.detectors = np.array(mast_table_combo['detector'])
            if (not os.path.exists(self.outfile)) & (len(existing_files) == len(mast_table_combo)):
                logging.info('Working on {}'.format(self.outfile))
                self.process()
                monitor_run = True
            else:
                logging.info('{} already exists or is missing cal files ({}/{} files found).'.format(self.outfile, len(existing_files), len(mast_table_combo)))

        # Update the background trending plots, if any new data exists
        if len(mast_table) > 0:
            logging.info('Making background trending plots.')
            self.make_background_plots(plot_type='bkg')
            self.make_background_plots(plot_type='bkg_rms')
            self.make_background_plots(plot_type='model')

        # Update the query history
        new_entry = {'instrument': 'nircam',
                     'start_time_mjd': self.query_start_mjd,
                     'end_time_mjd': self.query_end_mjd,
                     'run_monitor': monitor_run,
                     'entry_date': datetime.datetime.now(datetime.timezone.utc)}
        entry = self.query_table(**new_entry)
        entry.save()

        logging.info('Claw Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = ClawMonitor()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
