#! /usr/bin/env python

"""
Target acquistion monitor code

Author
------
    - Bryan Hilbert

Use
---
    To use this module from the command line:

    ::

        python ta_monitor.py

    To only update the trending plots:

    ::

        m = TAMonitor()
        m.make_trending_plots()


Summary

1. Have a list of modes on which the TA monitor will operate
2. For each mode, find the date of the last time the monitor was run. Use this as the MAST query start date
3. Query MAST for any data for that mode between the start date and the current date:

Add dates to this and I think it should work. Returns a list of visit_ids.

from astroquery.mast import Mast
service = 'Mast.Jwst.Filtered.Nircam'

     def set_params(parameters):
    ...:         return [{"paramName" : p, "values" : v} for p, v in parameters.items()]

     keywords = {
    ...:             #'visit_id': [visitid[1:]], # note: drop the initial character 'V'
    ...:             'exp_type': ['NRC_TACQ', 'MIR_TACQ', 'MIR_TACONFIRM', 'NRS_WATA', 'NRS_TACONFIRM', 'NIS_TACQ'],
    ...:             'productLevel': ['2b'],    # we are just interested in the Cal files, not in any rates.
    ...:            }
    params = {'columns': '*',   # -> can probably change columns to just what you need, i.e. visit_id
    ...:           'filters': set_params(keywords)
    ...:          }
t = Mast.service_request(service, params)
visit_id_set = set([row['visit_id'] for row in t])


4. Generate a list of visit IDs. e.g. Vpppppooovvv
5. Run Marshalls code on each
6. Save figures, and collect requested data
7. Put data into database tables
8. webapp:
9. query the database tables and generate trending plots
10. Show saved figures….somewhere
"""

import datetime
import logging
import matplotlib
import os
import warnings

from astroquery.mast import Mast
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_UPPERCASE, ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.utils import current_date_in_mjd, ensure_dir_exists, filesystem_path, get_config

from jwql.instrument_monitors.common_monitors.ta_monitor.target_acq_tools_refactored import auto_ta_results_analysis, get_visit_ta_image

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # Need to set up django apps before we can access the models
    import django  # noqa: E402 (module level import not at top of file)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()

    # Import * is okay here because this module specifically only contains database models
    # for this monitor
    from jwql.website.apps.jwql.monitor_models.claw import *  # noqa: E402 (module level import not at top of file)

matplotlib.use('Agg')
warnings.filterwarnings('ignore', message='Input data contains invalid values (NaNs or infs)*')

class TAMonitor():
    """
    Class for executing the TA monitor.

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




ABOUT READY TO START TESTING ON THE TEST SERVER (OR DEV SERVER?) SO WE HAVE ACCESS TO THE REAL FILESYSTEM





    def __init__(self, instrument):
        """Initialize an instance of the ``TAMonitor`` class.
        """

        self.supported_modes = {'miri': ['MIRI Coronagraphic Imaging',
                                         'MIRI Low Resolution Spectroscopy',
                                         'MIRI Medium Resolution Spectroscopy'],
                                'nircam': [],
                                'nirspec': [],
                                'niriss': []
                                }

        if instrument.lower() in JWST_INSTRUMENT_NAMES:
            self.instrument = instrument.lower()
        else:
            raise ValueError(f'Unrecognized instrument: {instrument}')

        # Get the MAST serive
        self.service = f"Mast.Jwst.Filtered.{self.instrument}"

        # Use the current date/time as the MAST query end date
        self.query_end = current_date_in_mjd()

        # Define and setup the output directories for the claw and background plots.
        #self.output_dir_visit_figs = os.path.join(get_config()['outputs'], 'ta_monitor', 'visit_figs')
        #ensure_dir_exists(self.output_dir_visit_figs)
        #self.working_dir = os.path.join(get_config()['outputs'], 'ta_monitor', 'working_dir')
        #ensure_dir_exists(self.working_dir)

        # Get the database tables
        #self.query_table = NIRCamTAMonitorQueryHistory
        #self.stats_table = NIRCamTAMonitorStats


    def run(self):
        """
        """

        self.get_latest_run_date()
        self.query_mast()
        self.get_list_of_visit_ids()

        # Loop
        for visit_id in self.visit_id_set:
            try:
                ta = auto_ta_results_analysis(visitid, save_localpath=True, localpath=self.working_dir,
                                              output_plot_dir=self.output_dir_visit_figs)

                # Update database tables with TA performance information
                self.update_db_tables(ta)

            except RuntimeError:
                log.warning(f'Expected to find TA files for {visitid}, but none were found.')



    def get_latest_run_date(self):
        """need to query the django model here
        """
        self.query_start = 60000.

    def get_list_of_visit_ids(self):
        """
        """
        self.visit_id_set = set([row['visit_id'] for row in self.ta_info])

    def query_mast(self):
        """
        """

        def set_params(parameters):
            return [{"paramName" : p, "values" : v} for p, v in parameters.items()]

        keywords = {
                    #'visit_id': [visitid[1:]], # note: drop the initial character 'V'
                    #"expstart": [{'min': self.query_start, 'max': self.query_end}],
                    "exp_type": ['NRC_TACQ', 'MIR_TACQ', 'MIR_TACONFIRM', 'NRS_WATA', 'NRS_TACONFIRM', 'NIS_TACQ'],
                    "productLevel": ['2b'],    # focus on cal files
                    }

        params = {'columns': '*',   # -> can probably change columns to just what you need, i.e. visit_id
                  'filters': set_params(keywords)
                  }
        params['filters'].append({"paramName":"expstart","values":[{"min":self.query_start, "max":self.query_end}]})

        self.ta_info = Mast.service_request(self.service, params)

    def update_db_tables(self, info):
        """Update the TA database table with the results from the target_acq_tools
        """
        info.visitid = utils.get_visitid(visitid)
        info.inst = inst.upper()
        info.verbose = verbose
        info.plot = plot
        info.output_plot_dir = output_plot_dir
        info._kwargs = kwargs

        # Per-exposure result lists
        info.visit_ids: list = []
        info.filenames: list = []
        info.deltapos: list = []
        info.deltapos_source: list = []
        info.wcs_offset_pix: list = []
        info.wcs_offset_radec: list = []
        info.xyref: list = []
        info.oss_cen_sci_pythonic: list = []
        info.targ_coords_pix: list = []
        info.ta_cen_coords: list = []
        info.targ_coords: list = []
        info.cen: list = []
        info.oss_sam: list = []
        info.oss_sam_dpa: list = []


