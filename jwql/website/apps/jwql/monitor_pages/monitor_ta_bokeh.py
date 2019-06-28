#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 19 15:41:04 2019

@author: gkanarek
"""

import os
from astropy.table import Table
import numpy as np

from jwql.utils.utils import get_config
from jwql.bokeh_templating import BokehTemplate

script_dir = os.path.dirname(os.path.abspath(__file__))

div_text = """Postage Stamp {refstar_no} Input Parameters<br>
v2, v3 desired; {v2_desired:+.5f}, {v3_desired:+.5f}<br>
NRS{detector:1d} col , row corner; {col_corner_stamp}, {row_corner_stamp}<br>
GWA X, Y tilt; {gwa_x_tilt:.5f}, {gwa_y_tilt:.5f}<br>
<br>
Gentalocate Results<br>
background measured {bkg_measured:.3f}<br>
locate col, row, flux: {col_locate_onebase:2d}, {row_locate_onebase:2d}, {checkbox_flux:.1f}<br>
centroid col, row, flux: {col_center_onebase:.3f}, {row_center_onebase:.3f}, {centroid_flux:.1f}<br>
detector col, row: {col_detector_center:.5f}, {row_detector_center:.5f}<br>
Centroid success: {centroid_success}<br>
<br>
TA Transform Results<br>
V2, V3 Measured: {v2_measured:.5f}, {v3_measured:.5f}<br>
Expected SIAF DET y, x: {y_siaf_expected:.5f}, {x_siaf_expected:.5f}"""

default_stamp = {'x': [0], 'y': [0], 'dh': [1], 'dw': [1],
        'slope1': [[[1,0], [0, 1]]], 'slope2': [[[1,0], [0, 1]]],
        'crj': [[[1,0], [0, 1]]], 'bkg': [[[1,0], [0, 1]]],
        'flat': [[[1,0], [0, 1]]]}

default_checkbox = {'l': [0], 'r': [1], 'b': [0], 't': [1], 'x': [0], 'y': [0]}

class MonitorTA(BokehTemplate):
    
    ta_table_file = "stamp_list_image1_output.fits"
    
    def pre_init(self):
        self._embed = True
        
        #App design
        self.format_string = None
        self.interface_file = os.path.join(script_dir, 'yaml',
                                           "monitor_ta_interface.yaml")
        
        self.settings = get_config()
        self.output_dir = self.settings['outputs']
        
        self.load_data()
        self.selected_stamp = -1
        
        
        self._stamp_vmin = {x: 0. for x in ['slope1', 'slope2', 'crj', 
                                           'bkg', 'flat']}
        self._stamp_vmax = {x: 1. for x in ['slope1', 'slope2', 'crj', 
                                           'bkg', 'flat']}
        
    def post_init(self):
        v2_offset, v3_offset = zip(*self.stamps_table['v2v3_offsets'])
        v2m, v3m = map(np.array, zip(*self.stamps_table['v2v3_measured']))
        v2d, v3d = map(np.array, zip(*self.stamps_table['v2v3_desired']))
        
        #avg_v2 = (v2m + v2d) / 2.
        #avg_v3 = (v3m + v3d) / 2.
        #v2m, v2d = v2m - avg_v2, v2d - avg_v2
        #v3m, v3d = v3m - avg_v3, v3d - avg_v3
        
        self.refs["offsets_source"].data = {'dv2': v2_offset, 'dv3': v3_offset,
                                            'v2m': v2m, 'v3m': v3m, 'v2d': v2d, 'v3d': v3d,
                                            'v2l': list(zip(v2m, v2d)), 'v3l': list(zip(v3m, v3d)),
                                            'refstar_no': self.stamps_table['refstar_no'].data}
        self.refs["offsets_xr"].start = min(v2_offset) - 0.5
        self.refs["offsets_xr"].end = max(v2_offset) + 0.5
        self.refs["offsets_yr"].start = min(v3_offset) - 0.5
        self.refs["offsets_yr"].end = max(v3_offset) + 0.5
        
        self.refs["summary_xr"].start = min(v2m.tolist() + v2d.tolist()) - 0.5
        self.refs["summary_xr"].end = max(v2m.tolist() + v2d.tolist()) + 0.5
        self.refs["summary_yr"].start = min(v3m.tolist() + v3d.tolist()) - 0.5
        self.refs["summary_yr"].end = max(v3m.tolist() + v3d.tolist()) + 0.5
        
        for field in ['slope1', 'slope2', 'crj', 'bkg', 'flat']:
            self.refs[field+"_fig"].toolbar.logo = None
            self.refs[field+"_fig"].toolbar_location = None
            
    
    def load_data(self, filename=None):
        if not filename:
            filename = self.ta_table_file
            
        self.stamps_table = Table.read(os.path.join(self.output_dir, 'monitor_ta',
                                                    filename), format='fits')
        self.stamps_table.add_index('refstar_no')
    
    def output_text(self):
        if self.selected_stamp < 0:
            return ""
        stamp = self.stamps_table[self.selected_stamp]
        pars = {'refstar_no': stamp['refstar_no'], 
                'v2_desired': stamp['v2v3_desired'][0],
                'v3_desired': stamp['v2v3_desired'][1],
                'detector': stamp['detector'],
                'col_corner_stamp': stamp['corner_stamp'][0],
                'row_corner_stamp': stamp['corner_stamp'][1],
                'gwa_x_tilt': stamp['gwa_tilt'][0],
                'gwa_y_tilt': stamp['gwa_tilt'][1],
                'bkg_measured': stamp['bkg_measured'],
                'col_locate_onebase': stamp['locate_onebase'][0],
                'row_locate_onebase': stamp['locate_onebase'][1],
                'checkbox_flux': stamp['checkbox_flux'],
                'col_center_onebase': stamp['center_onebase'][0],
                'row_center_onebase': stamp['center_onebase'][1],
                'centroid_flux': stamp['centroid_flux'],
                'col_detector_center': stamp['detector_center'][0],
                'row_detector_center': stamp['detector_center'][1],
                'centroid_success': stamp['centroid_success'],
                'v2_measured': stamp['v2v3_measured'][0],
                'v3_measured': stamp['v2v3_measured'][1],
                'y_siaf_expected': stamp['siaf_expected'][0],
                'x_siaf_expected': stamp['siaf_expected'][1]}
        return div_text.format(**pars)
    
    def select_stamp(self, attr, old, new):
        
        field_names = ['slope1', 'slope2', 'crj', 'bkg_subtracted', 'stamp_flat']
        field_keys = ['slope1', 'slope2', 'crj', 'bkg', 'flat']
        if not new:
            self.selected_stamp = -1
            source_data = default_stamp.copy()
            col_lft = row_bot = 0
            col_rgt = row_top = 1
            checkbox_data = default_checkbox.copy()
        else:
            idx = new[0]
            refstar_no = self.refs["offsets_source"].data['refstar_no'][idx]
            self.selected_stamp = self.stamps_table.loc_indices[refstar_no]
            stamp = self.stamps_table.loc[refstar_no]
            col_lft, col_rgt, row_bot, row_top = stamp['extent_slope1']
            x = col_lft
            dw = col_rgt - col_lft
            y = row_bot
            dh = row_top - row_bot
            source_data = {'x': [x], 'y': [y], 'dw': [dw], 'dh': [dh]}
            source_data.update({f: [stamp[field]] for f, field in zip(field_keys, field_names)})
            checkbox_x, checkbox_y = stamp['locate_onebase'] + stamp['corner_stamp']
            delta = stamp['check_box_size'] / 2.0
            cx, cy = stamp['detector_center']
            checkbox_data = dict(l=[checkbox_x - delta - 1], r=[checkbox_x + delta], 
                                 b=[checkbox_y - delta - 1], t=[checkbox_y + delta],
                                 x=[cx], y=[cy + 1])
            
            
        self.refs["stamp_source"].data = source_data
        self.refs["stamp_xr"].start = col_lft
        self.refs["stamp_xr"].end = col_rgt
        self.refs["stamp_yr"].start = row_bot
        self.refs["stamp_yr"].end = row_top
        self.refs["checkbox_source"].data = checkbox_data
        
        self._stamp_vmin = {'slope1': np.percentile(source_data['slope1'], 25.),
                            'slope2': np.percentile(source_data['slope1'], 25.),
                            'crj': np.percentile(source_data['slope1'], 25.),
                            'bkg': np.percentile(source_data['bkg'], 25.),
                            'flat': 0}
        self._stamp_vmax = {'slope1': np.percentile(source_data['slope1'], 99.5),
                            'slope2': np.percentile(source_data['slope1'], 99.5),
                            'crj': np.percentile(source_data['slope1'], 99.5),
                            'bkg': np.percentile(source_data['bkg'], 100.),
                            'flat': 65536}
        self.update_colors()
        
        self.refs["output_div"].text = self.output_text()
    
    def update_colors(self):
        for field in ['slope1', 'slope2', 'crj', 'bkg', 'flat']:
            self.refs[field+"_mapper"].low = self._stamp_vmin[field]
            self.refs[field+"_mapper"].high = self._stamp_vmax[field]