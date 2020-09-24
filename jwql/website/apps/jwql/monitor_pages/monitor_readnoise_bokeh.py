#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 18 04:30:18 2020

@author: bsunnquist
"""

from jwql.utils.utils import get_config
from jwql.bokeh_templating import BokehTemplate
from pathlib import Path
import numpy as np

script_dir = Path(__file__).parent

class ReadnoiseMonitor(BokehTemplate):

    # Combine instrument and aperture into a single property because we
    # do not want to invoke the setter unless both are updated
    @property
    def aperture_info(self):
        return (self._instrument, self._aperture)

    @aperture_info.setter
    def aperture_info(self, info):
        self._instrument, self._aperture = info
        self.pre_init()
        self.post_init()

    def pre_init(self):
        self._instrument = 'NIRCam'
        self._aperture = 'NRCA1_FULL'
        self._embed = True
        
        self.format_string = None
        self.interface_file = script_dir / 'yaml' / 'monitor_readnoise_interface.yaml'
        
        self.settings = get_config()
    
    def post_init(self):
        # read in output from somewhere
        dummy_data = np.arange(100) / 100.
        dummy_time = np.arange(100) / 5.
        
        self.refs["mean_readnoise_source"].data = {'time': dummy_time, 
                                                   'mean_rn': dummy_data}
        self.refs["mean_readnoise_xr"].start = dummy_time.min()
        self.refs["mean_readnoise_xr"].end = dummy_time.max()
        self.refs["mean_readnoise_yr"].start = dummy_data.min()
        self.refs["mean_readnoise_yr"].end = dummy_data.max()

ReadnoiseMonitor()
