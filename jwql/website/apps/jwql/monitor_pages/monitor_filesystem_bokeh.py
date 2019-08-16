#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 14:09:18 2019

@author: gkanarek
"""

import json
import os

from astropy.table import Table, vstack
from astropy.time import Time

from jwql.bokeh_templating import BokehTemplate
from jwql.utils.utils import get_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FIG_FORMATS = """
Figure:
    tools: 'pan,box_zoom,reset,wheel_zoom,save'
    x_axis_type: 'datetime'
    x_axis_label: 'Date'
    sizing_mode: 'stretch_both'
Line:
    line_width: 2
"""


class MonitorFilesystem(BokehTemplate):

    def pre_init(self):
        self._embed = True

        # App design
        self.format_string = FIG_FORMATS
        self.interface_file = os.path.join(SCRIPT_DIR, "yaml", "monitor_filesystem_interface.yaml")

        # Get path, directories and files in system and count files in all directories
        self.settings = get_config()
        self.filesystem = self.settings['filesystem']
        self.outputs_dir = os.path.join(self.settings['outputs'],
                                        'monitor_filesystem')

        self.allowed_types = ['fits_files', 'uncal', 'cal', 'rate', 'rateints',
                              'i2d', 'nrc', 'nrs', 'nis', 'mir', 'gui']

        # Load any existing data
        self.initial_load()

        self.types_k = ['circle', 'diamond', 'square', 'triangle',
                        'asterisk'] + ['x'] * 6
        self.types_y = ['fits', 'uncal', 'cal', 'rate', 'rateint',
                        'i2d', 'nrc', 'nrs', 'nis', 'mir', 'fgs']
        self.types_c = ['black', 'red', 'blue', 'green', 'orange', 'purple',
                        'midnightblue', 'springgreen', 'darkcyan',
                        'dodgerblue', 'darkred']
        self.types_l = ['Total FITS files', 'Uncalibrated FITS files',
                        'Calibrated FITS files', 'Rate FITS files',
                        'Rateints FITS files', 'I2D FITS files',
                        'NIRCam FITS files', 'NIRSpec FITS files',
                        'NIRISS FITS files', 'MIRI FITS files',
                        'FGS FITS files']

    def post_init(self):
        self.update_plots(full=True)

    def initial_load(self):
        statsfile = os.path.join(self.outputs_dir, 'statsfile.json')
        filebytype = os.path.join(self.outputs_dir, 'filesbytype.json')
        sizebytype = os.path.join(self.outputs_dir, 'sizebytype.json')

        self.statistics = Table(names=['timestamp', 'file_count', 'total',
                                       'available', 'used', 'percent_used'],
                                dtype=[Time, int, int, int, int, float])
        self.statistics['percent_used'].format = "%.1f"
        if os.path.exists(statsfile):
            with open(statsfile) as f:
                stats = json.load(f)
            times, fc, tot, avail, used, perc = zip(*stats)
            self.statistics['timestamp'] = Time(times)
            self.statistics['file_count'] = map(int, fc)
            self.statistics['total'] = map(int, tot)
            self.statistics['available'] = map(int, avail)
            self.statistics['used'] = map(int, used)
            self.statistics['percent_used'] = map(float, perc)

        self.ftypes = Table(names=['timestamp'] + self.allowed_types,
                            dtype=[Time] + [int] * 11)
        if os.path.exists(filebytype):
            with open(filebytype) as f:
                fbytype = json.load(f)
            times, *ftypes = zip(*fbytype)
            self.ftypes['timestamp'] = Time(times)
            for c, colname in enumerate(self.allowed_types):
                self.ftypes[colname] = map(int, ftypes[c])

        self.stypes = Table(names=['timestamp'] + self.allowed_types,
                            dtype=[Time] + [float] * 11)
        if os.path.exists(sizebytype):
            with open(sizebytype) as f:
                sbytype = json.load(f)
            times, *stypes = zip(*sbytype)
            self.stypes['timestamp'] = Time(times)
            for c, colname in enumerate(self.allowed_types):
                self.stypes[colname] = map(int, stypes[c])

    def update_plots(self, full=False):

        if full:
            # Initialize each ColumnDataSource so that we can use stream() later
            self.refs['source_filecount'].data = {
                'dates': self.statistics['timestamp'].datetime64,
                'filecount': self.statistics['file_count'].data}

            self.refs['source_stats'].data = {
                'dates': self.statistics['timestamp'].datetime64,
                'systemsize': self.statistics['total'].data.astype(float) / (1024.**3),
                'freesize': self.statistics['available'].data.astype(float) / (1024.**3),
                'usedsize': self.statistics['used'].data.astype(float) / (1024.**3)}

            ftype_dict = {'dates': self.ftypes['timestamp'].datetime64}
            ftype_dict.update({x: self.ftypes[y].data for x, y in zip(self.types_y,
                               self.allowed_types)})
            self.refs['source_files'].data = ftype_dict

            stype_dict = {'dates': self.stypes['timestamp'].datetime64}
            stype_dict.update({x: self.stypes[y].data for x, y in zip(self.types_y,
                               self.allowed_types)})
            self.refs['source_sizes'].data = stype_dict
        else:
            new_stats, new_files, new_sizes = self.read_new_data()
            if new_stats:
                self.refs['source_filecount'].stream({
                    'dates': new_stats['timestamp'].datetime64,
                    'filecount': new_stats['file_count'].data})
                self.refs['source_stats'].stream({
                    'dates': new_stats['timestamp'].datetime64,
                    'systemsize': new_stats['total'].data,
                    'freesize': new_stats['available'].data,
                    'usedsize': new_stats['used'].data})
            if new_files:
                ftype_dict = {'dates': new_files['timestamp'].datetime64}
                ftype_dict.update({x: new_files[y].data for x, y in zip(self.types_y,
                                   self.allowed_types)})
                self.refs['source_files'].stream(ftype_dict)

            if new_sizes:
                stype_dict = {'dates': new_sizes['timestamp'].datetime64}
                stype_dict.update({x: new_sizes[y].data / (1024.**3)
                    for x, y in zip(self.types_y, self.allowed_types)})
                self.refs['source_sizes'].data = stype_dict

        if not self.statistics:
            self.latest_timestamp = Time(0., format='unix')
        else:
            self.latest_timestamp = self.statistics['timestamp'].max()

    def read_new_data(self):
        """
        Algorithm:
            1. Read in the json files (this step will be replaced when we move
               away from json) into tables.
            2. Create new tables from all rows which have been added since the
               last timestamp in the current tables.
            3. Concatenate the new tables with a vertical join.
            4. Return the new tables so they can be streamed to the plots.
        """
        statsfile = os.path.join(self.outputs_dir, 'statsfile.json')
        filebytype = os.path.join(self.outputs_dir, 'filesbytype.json')
        sizebytype = os.path.join(self.outputs_dir, 'sizebytype.json')

        # Have any of the files been modified since the last timestamp?
        stats_modtime = Time(os.stat(statsfile).st_mtime, format='unix')
        files_modtime = Time(os.stat(filebytype).st_mtime, format='unix')
        sizes_modtime = Time(os.stat(sizebytype).st_mtime, format='unix')

        new_stats = Table(names=self.statistics.colnames,
                          dtype=self.statistics.dtype)
        new_files = Table(names=self.ftypes.colnames,
                          dtype=self.ftypes.dtype)
        new_sizes = Table(names=self.stypes.colnames,
                          dtype=self.stypes.dtype)

        if stats_modtime > self.latest_timestamp:
            with open(statsfile) as f:
                stats = json.load(f)
            times, fc, tot, avail, used, perc = zip(*stats)
            times = Time(times)
            new_rows = times > self.latest_timestamp
            new_stats['timestamp'] = times[new_rows]
            new_stats['file_count'] = map(int, fc[new_rows])
            new_stats['total'] = map(int, tot[new_rows])
            new_stats['available'] = map(int, avail[new_rows])
            new_stats['used'] = map(int, used[new_rows])
            new_stats['percent_used'] = map(float, perc[new_rows])

            self.statistics = vstack([self.statistics, new_stats])

        if files_modtime > self.latest_timestamp:
            with open(filebytype) as f:
                fbytype = json.load(f)
            times, *ftypes = zip(*fbytype)
            times = Time(times)
            new_rows = times > self.latest_timestamp
            new_files['timestamp'] = times[new_rows]
            for c, colname in enumerate(self.allowed_types):
                new_files[colname] = map(int, ftypes[c][new_rows])

            self.ftypes = vstack([self.ftypes, new_files])

        if sizes_modtime > self.latest_timestamp:
            with open(sizebytype) as f:
                sbytype = json.load(f)
            times, *stypes = zip(*sbytype)
            times = Time(times)
            new_rows = times > self.latest_timestamp
            new_sizes['timestamp'] = times[new_rows]
            for c, colname in enumerate(self.allowed_types):
                new_sizes[colname] = map(int, stypes[c][new_rows])

            self.stypes = vstack([self.stypes, new_sizes])

        return new_stats, new_files, new_sizes
