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
"""

import logging
import os

from astropy.io import fits
from astropy.time import Time
from astropy.visualization import ZScaleInterval
from astroquery.mast import Mast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from jwql.utils import monitor_utils
from jwql.utils.logging_functions import log_info, log_fail


class ClawMonitor():
    """Class for executing the claw monitor.
    """

    def __init__(self):
        """Initialize an instance of the ``ClawMonitor`` class.
        """

    def process(self):
        """The main method for processing.  See module docstrings for further details.
        """

        # Get detector order and plot settings, depending on the wavelength channel
        if self.wv == 'SW':
            detectors_to_run = ['NRCA2', 'NRCA4', 'NRCB3', 'NRCB1', 'NRCA1', 'NRCA3', 'NRCB4', 'NRCB2']  # in on-sky order, don't change order
            cols, rows = 5, 2
            grid = plt.GridSpec(rows, cols, hspace=.2, wspace=.2, width_ratios=[1,1,1,1,.1])
            fig = plt.figure(figsize=(40, 20))
            cbar_fs = 20
            fs = 30
        else:
            detectors_to_run = ['NRCALONG', 'NRCBLONG']
            cols, rows = 3, 1
            grid = plt.GridSpec(rows, cols, hspace=.2, wspace=.2, width_ratios=[1,1,.1])
            fig = plt.figure(figsize=(20, 10))
            cbar_fs = 15
            fs = 25
        
        # Make source-masked, median-stack of each detector's images, and add them to the plot
        for det in detectors_to_run:
            files = self.files[self.detectors == det]
            print(det)
            print(files)
            print('------')

    def query_mast(self):
        """Query MAST for new nircam full-frame imaging data.

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
        FIELDS = ['filename','program', 'observtn','category','instrume', 'productLevel', 'filter', 
                  'pupil', 'subarray', 'detector','datamodl','date_beg_mjd', 'effexptm']
        params = {"columns":",".join(FIELDS),
                "filters":[
                {"paramName":"pupil","values":['CLEAR','F162M','F164N','F323N','F405N','F466N','F470N']},
                {"paramName":"exp_type","values":['NRC_IMAGE']},
                {"paramName":"datamodl", "values":['ImageModel']},  # exclude calints, which are cubemodel
                {"paramName":"productLevel", "values":['2b']},  # i.e. cal.fits
                {"paramName":"subarray", "values":['FULL']},
                ]
                }
        t = JwstObs.service_request(service, params)
        t = t[t['date_beg_mjd']>self.query_start_mjd]
        t.sort('date_beg_mjd')
        filetypes = np.array([row['filename'].split('_')[-1].replace('.fits','') for row in t])
        t = t[filetypes=='cal']  # only want cal.fits files, no e.g. i2d.fits

        return t

    #@log_fail  # todo uncomment
    #@log_info  # todo uncomment
    def run(self):
        """The main method.  See module docstrings for further details."""

        logging.info('Begin logging for claw_monitor')
        self.output_dir = '/Users/bsunnquist/Downloads/'  # todo change this to os.path.join(get_config()['outputs'], 'claw_monitor')
        self.data_dir = '/ifs/jwst/wit/nircam/commissioning/'  # todo change this to path of cal.fits files

        # Query MAST for new imaging data from the last 3 days
        self.query_end_mjd = Time.now().mjd
        self.query_start_mjd = self.query_end_mjd - 3
        print(self.query_end_mjd, self.query_start_mjd)
        t = self.query_mast()
        print(t)

        # Create observation-level median stacks for each filter/pupil combo, in pixel-space
        combos = np.array(sorted(['{}_{}_{}_{}'.format(str(row['program']), row['observtn'], row['filter'], row['pupil']).lower() for row in t]))
        t['combos'] = combos
        for combo in np.unique(combos)[0:2]:  # todo take off 0:2
            tt = t[t['combos']==combo]
            if 'long' in tt['filename'][0]:
                self.wv = 'LW'
            else:
                self.wv = 'SW'
            self.proposal, self.obs, self.fltr, self.pupil = combo.split('_')
            self.outfile = os.path.join(self.output_dir, 'prop{}_obs{}_{}_{}_cal_norm_skyflat.png'.format(str(self.proposal).zfill(5), self.obs, self.fltr, self.pupil).lower())
            self.files = np.array([os.path.join(self.data_dir, '{}'.format(str(self.proposal).zfill(5)), 'obsnum{}'.format(self.obs), row['filename']) for row in tt])  # todo change to server filepath
            self.detectors = np.array(tt['detector'])
            if not os.path.exists(self.outfile):
                self.process()
            else:
                print('{} already exists'.format(self.outfile))

        logging.info('Claw Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    #start_time, log_file = monitor_utils.initialize_instrument_monitor(module)   # todo uncomment

    monitor = ClawMonitor()
    monitor.run()

    #monitor_utils.update_monitor_table(module, start_time, log_file)   # todo uncomment
