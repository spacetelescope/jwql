#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  5 15:19:20 2019

@author: gkanarek
"""

import os

from astropy.time import Time
import pandas as pd

from jwql.bokeh_templating import BokehTemplate
from jwql.utils.utils import get_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class MastMonitor(BokehTemplate):

    def pre_init(self):
        self._embed = True

        # App design
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', "monitor_mast_interface.yaml")

        self.settings = get_config()
        self.output_dir = self.settings['outputs']

        self.read_new_data()

        self.cache_time = Time(0., format='unix')

        self.jwst_bar_colors = self.caom_bar_colors = 3
        self.jwst_datacols = []
        self.caom_datacols = []

    def post_init(self):
        self.update_plots()

    def read_new_data(self):
        """
        Placeholder to read what are currently Pandas dataframe dumps. Replace
        this when we have a new database infrastructure.
        """

        jwst_filepath = os.path.join(self.outputs_dir, 'database_monitor_jwst.json')
        caom_filepath = os.path.join(self.outputs_dir, 'database_monitor_caom.json')

        jwst_modtime = Time(os.stat(jwst_filepath).st_mtime, format='unix')
        caom_modtime = Time(os.stat(caom_filepath).st_mtime, format='unix')

        if jwst_modtime >= self.cache_time:
            self.jwst_df = pd.read_json(jwst_filepath, orient='records')
        if caom_modtime >= self.cache_time:
            self.caom_df = pd.read_json(caom_filepath, orient='records')

        self.cache_time = Time.now()

    def update_plots(self):
        """
        Update the various sources and variables for the MAST monitor bar charts.
        """

        self.read_new_data()

        jwst_groups = list(self.jwst_df['instrument'])
        caom_groups = list(self.caom_df['instrument'])

        self.jwst_datacols = [col for col in list(self.jwst_df.columns) if col != 'instrument']
        self.caom_datacols = [col for col in list(self.caom_df.columns) if col != 'instrument']

        jwst_data = {'groups': jwst_groups}
        caom_data = {'groups': caom_groups}

        for col in self.jwst_datacols:
            jwst_data.update({col: list(self.jwst_df[col])})
        for col in self.caom_datacols:
            caom_data.update({col: list(self.caom_df[col])})

        self.jwst_bar_colors = max(3, len(self.jwst_datacols))
        self.caom_bar_colors = max(3, len(self.caom_datacols))

        jwst_x = [(group, datacol) for group in jwst_groups for datacol in self.jwst_datacols]
        jwst_counts = sum(zip(*[jwst_data[col] for col in self.jwst_datacols]), ())
        caom_x = [(group, datacol) for group in caom_groups for datacol in self.caom_datacols]
        caom_counts = sum(zip(*[caom_data[col] for col in self.caom_datacols]), ())

        self.refs['jwst_source'].data = {'x': jwst_x, 'counts': jwst_counts}
        self.refs['caom_source'].data = {'x': caom_x, 'counts': caom_counts}
