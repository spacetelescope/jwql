#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 19 15:41:04 2019
@author: gkanarek
"""

from pathlib import Path
from glob import glob
import json
import numpy as np
import os

from jwql.utils.utils import get_config
from jwql.bokeh_templating import BokehTemplate

script_dir = Path(__file__).parent
yaml_dir = script_dir / 'yaml'

div_text = """Postage Stamp {refstar_no} Input Parameters<br>
v2, v3 desired; {v2_desired:+.5f}, {v3_desired:+.5f}<br>
NRS{detector:1d} col , row corner; {col_corner_stamp}, {row_corner_stamp}<br>
GWA X, Y tilt; {gwa_x_tilt:.5f}, {gwa_y_tilt:.5f}<br>
<br>
Gentalocate Results<br>
background measured {bkg_measured:.3f}<br>
locate col, row, flux: {col_locate:3.0f}, {row_locate:3.0f}, {checkbox_flux:.1f}<br>
centroid col, row, flux: {col_center:.3f}, {row_center:.3f}, {centroid_flux:.1f}<br>
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

def collect_visit_data(output_dir):
    #scrape the existing visits for LS data. this needs to be a standard routine in the monitor script
    if isinstance(output_dir, str):
        visit_dirs = glob(os.path.join(output_dir, 'V*'))
    else:
        visit_dirs = output_dir.glob('V*/')
    visits = {}
    for vd in visit_dirs:
        vid = os.path.basename(vd)
        visit = {'path': vd}
        lsr_file = os.path.join(vd, vid + '_least_squares_dict_replicaTA.json')
        with open(lsr_file, 'r') as f:
            visit['replica_ls'] = json.load(f)
        lso_file = os.path.join(vd, vid + '_oss_least_squares_output_replicaTA.json')
        with open(lso_file, 'r') as f:
            visit['oss_ls'] = json.load(f)
        visits[vid] = visit
    return visits

class MonitorTA(BokehTemplate):
    
    def pre_init(self, **kwargs):
        self._embed = True
        
        #App design
        self.format_string = None
        self.interface_file = yaml_dir / "monitor_ta_interface.yaml"
        
        with (yaml_dir / 'monitor_ta_detail_panel.yaml').open() as f:
            self.visit_panel_template = f.read()
        
        self.settings = get_config()
        self.output_dir = Path(self.settings['outputs']) / 'ta_monitor'
        
        self.selected_stamps = {}
        self.visit_data = {}
        self.available_visits = []
        
        self._stamp_vmin = {x: 0. for x in ['slope1', 'slope2', 'crj', 
                                           'bkg', 'flat']}
        self._stamp_vmax = {x: 1. for x in ['slope1', 'slope2', 'crj', 
                                           'bkg', 'flat']}
    
    def post_init(self):
        self.load_trending_data()
        self.update_trend_plots()
        self.refs["v2v3_offsets_trend_fig"].legend.click_policy = "hide"
        self.refs["time_offsets_trend_fig"].legend.click_policy = "hide"
    
    def load_trending_data(self):
        """
        Collect the trending data and calculate axis ranges.
        This is a separate function so that it can be called to refresh
        the trend plots without reloading the page."""
        self.output_dir = '/Users/pena/Documents/PyCharmProjects/nirspec/commissioning/sandbox/bokeh_ta_monitor/outputs/ta_monitor'
        print("output_dir={} (exists: {})".format(self.output_dir, os.path.exists(self.output_dir)))
        self.all_visits = collect_visit_data(self.output_dir)
        
        self.collated_trend_data = {'visit_num': [], 'visit': [], 
                                    'rep_v2': [], 'rep_v2_lo': [], 
                                    'rep_v2_hi': [], 'rep_v3': [], 
                                    'rep_v3_lo': [], 'rep_v3_hi': [],
                                    'rep_theta': [], 'rep_theta_lo': [], 
                                    'rep_theta_hi': [], 'oss_v3': [], 
                                    'oss_v3_lo': [], 'oss_v3_hi': [],
                                    'oss_v2': [], 'oss_v2_lo': [], 
                                    'oss_v2_hi': [], 'oss_theta': []}
        v2_vals, v3_vals = [], []
        for i, (vid, visit) in enumerate(sorted(self.all_visits.items())):
            self.collated_trend_data['visit_num'].append(i)
            self.collated_trend_data['visit'].append(vid)
            rv2 = visit['replica_ls']['mean_v2']
            rv2s = visit['replica_ls']['std_dev_v2']
            rv3 = visit['replica_ls']['mean_v3']
            rv3s = visit['replica_ls']['std_dev_v3']
            rth = visit['replica_ls']['mean_roll']
            rths = visit['replica_ls']['std_dev_theta']
            self.collated_trend_data['rep_v2'].append(rv2)
            self.collated_trend_data['rep_v2_lo'].append(rv2 - rv2s)
            self.collated_trend_data['rep_v2_hi'].append(rv2 + rv2s)
            self.collated_trend_data['rep_v3'].append(rv3)
            self.collated_trend_data['rep_v3_lo'].append(rv3 - rv3s)
            self.collated_trend_data['rep_v3_hi'].append(rv3 + rv3s)
            self.collated_trend_data['rep_theta'].append(rth)
            self.collated_trend_data['rep_theta_lo'].append(rth - rths)
            self.collated_trend_data['rep_theta_hi'].append(rth + rths)
            ov2 = visit['oss_ls']['mean_v2']
            ov2s = visit['oss_ls']['std_dev_v2']
            ov3 = visit['oss_ls']['mean_v3']
            ov3s = visit['oss_ls']['std_dev_v3']
            oth = visit['oss_ls']['mean_theta']
            self.collated_trend_data['oss_v2'].append(ov2)
            self.collated_trend_data['oss_v2_lo'].append(ov2 - ov2s)
            self.collated_trend_data['oss_v2_hi'].append(ov2 + ov2s)
            self.collated_trend_data['oss_v3'].append(ov3)
            self.collated_trend_data['oss_v3_lo'].append(ov3 - ov3s)
            self.collated_trend_data['oss_v3_hi'].append(ov3 + ov3s)
            self.collated_trend_data['oss_theta'].append(oth)
            v2_vals.extend([rv2+rv2s, rv2-rv2s, ov2+ov2s, ov2-ov2s])
            v3_vals.extend([rv3+rv3s, rv3-rv3s, ov3+ov3s, ov3-ov3s])
            
        v2r_lo, v2r_hi = min(v2_vals), max(v2_vals)
        dv2 = (v2r_hi - v2r_lo) * 0.05
        v3r_lo, v3r_hi = min(v3_vals), max(v3_vals)
        dv3 = (v3r_hi - v3r_lo) * 0.05
            
        v2r = [v2r_lo - dv2, v2r_hi + dv2]
        v3r = [v3r_lo - dv3, v3r_hi + dv3]
        
        self.trend_ranges = {}
        self.trend_ranges['v2_range'] = v2r
        self.trend_ranges['v3_range'] = v3r
        self.trend_ranges['v2v3_range'] = [min(v2r + v3r), max(v2r + v3r)]
        self.available_visits = self.collated_trend_data['visit']
    
    
    def update_trend_plots(self):
        """
        Populate the trend plots and axis ranges with the collated trending data.
        """
        
        v2_lo, v2_hi = self.trend_ranges['v2_range']
        v3_lo, v3_hi = self.trend_ranges['v3_range']
        v23_lo, v23_hi = self.trend_ranges['v2v3_range']
        
        self.refs['v2_offsets_trend_range'].start = v2_lo
        self.refs['v2_offsets_trend_range'].end = v2_hi
        self.refs['v3_offsets_trend_range'].start = v3_lo
        self.refs['v3_offsets_trend_range'].end = v3_hi
        self.refs['visit_offsets_trend_xr'].factors = self.collated_trend_data['visit']
        self.refs['visit_offsets_trend_yr'].start = v23_lo
        self.refs['visit_offsets_trend_yr'].end = v23_hi
        
        self.refs['trend_source'].data = self.collated_trend_data
        self.refs['visit_select'].options = ["  "] + self.available_visits
        
        visits_fig = self.refs["time_offsets_trend_fig"]
        
        self.refs["rep_v2_err_time"].js_link("visible", 
                             visits_fig.select(name="rep_v2")[0], "visible")
        self.refs["rep_v3_err_time"].js_link("visible", 
                             visits_fig.select(name="rep_v3")[0], "visible")
        self.refs["oss_v2_err_time"].js_link("visible", 
                             visits_fig.select(name="oss_v2")[0], "visible")
        self.refs["oss_v3_err_time"].js_link("visible", 
                             visits_fig.select(name="oss_v3")[0], "visible")
    
    def load_visit_data(self, vid):
        visit_file = self.all_visits[vid]['path'] / (vid + '_centroid_output_replicaTA.json')
        with visit_file.open() as f:
            self.visit_data[vid] = {'data': json.load(f)}
        
        stamps_file = self.all_visits[vid]['path'] / (vid + '_stamp_image_output_replicaTA.json')
        with stamps_file.open() as f:
            self.visit_data[vid]['stamps'] = json.load(f)
        
        collated_visit = {'dv2': [], 'dv3': [], 'v2m': [], 'v3m': [], 'v2d': [], 
                          'v3d': [], 'refstar_no': [], 'nrs': [], 'ccs': [], 
                          'rcs': [], 'gxt': [], 'gyt': [], 'bkg': [], 'cl1': [],
                          'rl1': [], 'cbx': [], 'cc1': [], 'rc1': [], 'cfx': [],
                          'cdc': [], 'rdc': [], 'csc': [], 'ysx': [], 'xsx': [],
                          'v2_offset': [], 'v3_offset': []}
        for star in self.visit_data[vid]['data']:
            collated_visit['refstar_no'].append(star['refstar_no'])
            collated_visit['v2d'].append(star['v2_desired'])
            collated_visit['v3d'].append(star['v3_desired'])
            collated_visit['v2m'].append(star['v2_measured'])
            collated_visit['v3m'].append(star['v3_measured'])
            collated_visit['dv2'].append(star['v2_offsets'])
            collated_visit['dv3'].append(star['v3_offsets'])
            collated_visit['nrs'].append(star['detector'])
            collated_visit['ccs'].append(star['col_corner_stamp'])
            collated_visit['rcs'].append(star['row_corner_stamp'])
            collated_visit['gxt'].append(star['gwa_x_tilt'])
            collated_visit['gyt'].append(star['gwa_y_tilt'])
            collated_visit['bkg'].append(star['bkg_measured'])
            collated_visit['cl1'].append(star['col_locate'])
            collated_visit['rl1'].append(star['row_locate'])
            collated_visit['cbx'].append(star['checkbox_flux'])
            collated_visit['cc1'].append(star['col_center'])
            collated_visit['rc1'].append(star['row_center'])
            collated_visit['cfx'].append(star['centroid_flux'])
            collated_visit['cdc'].append(star['col_detector_center'])
            collated_visit['rdc'].append(star['row_detector_center'])
            collated_visit['csc'].append(star['centroid_success'])
            collated_visit['ysx'].append(star['y_siaf_expected'])
            collated_visit['xsx'].append(star['x_siaf_expected'])
            collated_visit['v2_offset'].append(star['v2_offsets'])
            collated_visit['v3_offset'].append(star['v3_offsets'])
        
        self.visit_data[vid]['collated'] = collated_visit
        v2_lo = min(collated_visit['v2_offset'])
        v2_hi = max(collated_visit['v2_offset'])
        dv2 = (v2_hi - v2_lo) * 0.05
        v3_lo = min(collated_visit['v3_offset'])
        v3_hi = max(collated_visit['v3_offset'])
        dv3 = (v3_hi - v3_lo) * 0.05
        self.visit_data[vid]['ranges'] = [v2_lo - dv2, v2_hi + dv2,
                                          v3_lo - dv3, v3_hi + dv3]
    
    def select_visit(self, attr, old, new):
        if not new or new == "  ":
            self.selected_vid = None
            self.refs['visit_select'].value = "  "
            self.refs['detail_button'].disabled = True
            self.refs['trend_source'].selected.indices = []
            return
        if attr == "indices":
            idx = new[0]
            self.selected_vid = self.refs['trend_source'].data['visit'][idx]
        else:
            self.selected_vid = new
        self.refs['visit_select'].value = self.selected_vid
        self.refs['detail_button'].disabled = False
        self.refs['trend_source'].selected.indices = [self.available_visits.index(self.selected_vid)]
    
    def open_visit_panel(self):
        vid = self.selected_vid
        if vid not in self.visit_data:
            self.load_visit_data(vid)
        panelstring = self.visit_panel_template.format(vid=vid)
        new_widgets = self.parse_string(panelstring)
        new_panel = new_widgets[0][-1]
        self.refs["msata_tabs"].tabs.append(new_panel)
        self.refs["offsets_source_visit_{}".format(vid)].data = self.visit_data[vid]['collated']
        v2_lo, v2_hi, v3_lo, v3_hi = self.visit_data[vid]['ranges']
        self.refs["offsets_xr_visit_{}".format(vid)].start = v2_lo
        self.refs["offsets_xr_visit_{}".format(vid)].end = v2_hi
        self.refs["offsets_yr_visit_{}".format(vid)].start = v3_lo
        self.refs["offsets_yr_visit_{}".format(vid)].end = v3_hi
            
        v2off = self.visit_data[vid]['collated']['v2_offset']
        v3off = self.visit_data[vid]['collated']['v3_offset']
        
        v2_hist, v2_bins = np.histogram(v2off)
        v3_hist, v3_bins = np.histogram(v3off)
        bottom = np.zeros_like(v2_hist)
        self.refs["resid_source_visit_{}".format(vid)].data = {'bottom': bottom,
                                                               'v2_l': v2_bins[:-1],
                                                               'v2_r': v2_bins[1:],
                                                               'v2_t': v2_hist,
                                                               'v3_l': v3_bins[:-1],
                                                               'v3_r': v3_bins[1:],
                                                               'v3_t': v3_hist}
        self.refs["resid_xr_visit_{}".format(vid)].start = 0
        self.refs["resid_xr_visit_{}".format(vid)].end = v3_hist.max()
        self.refs["resid_yr_visit_{}".format(vid)].start = 0
        self.refs["resid_yr_visit_{}".format(vid)].end = v2_hist.max()
        self.refs["resid_hist_v2_visit_{}".format(vid)].toolbar.logo = None
        self.refs["resid_hist_v2_visit_{}".format(vid)].toolbar_location = None
        self.refs["resid_hist_v3_visit_{}".format(vid)].toolbar.logo = None
        self.refs["resid_hist_v3_visit_{}".format(vid)].toolbar_location = None
        
    def output_text(self, vid):
        if self.selected_stamps.get(vid, -1) < 0:
            return ""
        idx = self.selected_stamps[vid]
        stamp = self.visit_data[vid]['data'][idx]
        return div_text.format(**stamp)
    
    def select_stamp(self, attr, old, new):
        #identify active visit id
        tab_idx = self.refs['msata_tabs'].active
        active_panel = self.refs['msata_tabs'].tabs[tab_idx]
        vid = active_panel.tags[0]
        vis = True
        
        #generate the stamps and output info
        field_keys = ['slope1', 'slope2', 'crj', 'bkg', 'flat']
        if not new:
            self.selected_stamps[vid] = -1
            source_data = default_stamp.copy()
            col_lft = row_bot = 0
            col_rgt = row_top = 1
            checkbox_data = default_checkbox.copy()
            vis = False
        else:
            idx = new[0]
            self.selected_stamps[vid] = idx
            stamp_data = self.visit_data[vid]['data'][idx]
            stamps = self.visit_data[vid]['stamps'][stamp_data['refstar_no']]
            col_lft, col_rgt, row_bot, row_top = stamps['extent'] #need this info...
            x = col_lft
            dw = col_rgt - col_lft
            y = row_bot
            dh = row_top - row_bot
            source_data = {'x': [x], 'y': [y], 'dw': [dw], 'dh': [dh]}
            source_data.update({f: [stamps[f]] for f in field_keys}) #need this info...
            checkbox_x = stamp_data['col_locate'] + stamp_data['col_corner_stamp']
            checkbox_y = stamp_data['row_locate'] + stamp_data['row_corner_stamp']
            delta = stamp_data['check_box_size'] / 2.0
            cx, cy = stamp_data['col_detector_center'], stamp_data['row_detector_center']
            checkbox_data = dict(l=[checkbox_x - delta - 1], r=[checkbox_x + delta], 
                                 b=[checkbox_y - delta - 1], t=[checkbox_y + delta],
                                 x=[cx], y=[cy + 1])
            
            
        self.refs["stamp_source_visit_{}".format(vid)].data = source_data
        self.refs["stamp_xr_visit_{}".format(vid)].start = col_lft
        self.refs["stamp_xr_visit_{}".format(vid)].end = col_rgt
        self.refs["stamp_yr_visit_{}".format(vid)].start = row_bot
        self.refs["stamp_yr_visit_{}".format(vid)].end = row_top
        self.refs["checkbox_source_visit_{}".format(vid)].data = checkbox_data
        
        vmin = {'slope1': np.percentile(source_data['slope1'], 25.),
                'slope2': np.percentile(source_data['slope1'], 25.),
                'crj': np.percentile(source_data['slope1'], 25.),
                'bkg': np.percentile(source_data['bkg'], 25.),
                'flat': 0}
        vmax = {'slope1': np.percentile(source_data['slope1'], 99.5),
                'slope2': np.percentile(source_data['slope1'], 99.5),
                'crj': np.percentile(source_data['slope1'], 99.5),
                'bkg': np.percentile(source_data['bkg'], 100.),
                'flat': 65536}
        for field in ['slope1', 'slope2', 'crj', 'bkg', 'flat']:
            self.refs["{}_mapper_visit_{}".format(field, vid)].low = vmin[field]
            self.refs["{}_mapper_visit_{}".format(field, vid)].high = vmax[field]
            self.refs["{}_fig_visit_{}".format(field, vid)].visible = vis
        
        self.refs["output_div_visit_{}".format(vid)].text = self.output_text(vid)
    
            
MonitorTA()

