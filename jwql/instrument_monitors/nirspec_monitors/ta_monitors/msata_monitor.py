#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# HISTORY
#    Feb 2022 - Vr. 1.0: Completed initial version
#    Jul 2022 - Vr. 1.1: Changed keywords to final flight values
#    Aug 2022 - Vr. 1.2: Modified plots according to NIRSpec team input
#    Sep 2022 - Vr. 1.3: Modified ColumnDataSource so that data could be recovered
#                        from an html file of a previous run of the monitor and
#                        included the code to read and format the data from the html file


"""
This module contains the code for the NIRSpec Multi Shutter Array Target
Acquisition (MSATA) monitor, which monitors the TA offsets, including
the roll for MSATA.

This monitor displays details of individual MSATA stars and details of
fitting and rejection procedure (least square fit).

This monitor also displays V2, V3, and roll offsets over time.

Author
______
    - Maria Pena-Guerrero

Use
---
    This module can be used from the command line as follows:
    python msata_monitor.py

"""


# general imports
import os
import logging
import numpy as np
import pandas as pd
import json
from bs4 import BeautifulSoup
from datetime import datetime
from astropy.time import Time
from astropy.io import fits
from random import randint
from sqlalchemy.sql.expression import and_
from bokeh.plotting import figure, output_file, show, save
from bokeh.models import ColumnDataSource, Range1d
from bokeh.models.tools import HoverTool
from bokeh.layouts import gridplot
from bokeh.models import Span, Label
from bokeh.embed import components

# jwql imports
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils import monitor_utils
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.database.database_interface import session
from jwql.database.database_interface import NIRSpecTAQueryHistory, NIRSpecTAStats
from jwql.jwql_monitors import monitor_mast
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config, filename_parser


class MSATA():
    """ Class for executint the NIRSpec MSATA monitor.

    This class will search for new MSATA current files in the file systems
    for NIRSpec and will run the monitor on these files. The monitor will
    extract the TA information from the fits file headers and perform all
    statistical measurements. Results will be saved to the MSATA database.

    Attributes
    ----------
    output_dir : str
        Path into which outputs will be placed.

    data_dir : str
        Path into which new dark files will be copied to be worked on.

    aperture : str
        Name of the aperture used for the dark current (i.e.
        "NRS_FULL_MSA", "NRS_S1600A1_SLIT")

    query_start : float
        MJD start date to use for querying MAST.

    query_end : float
        MJD end date to use for querying MAST.

    """

    def __init__(self):
        """ Initialize an instance of the MSATA class """
        # dictionary to define required keywords to extract MSATA data and where it lives
        self.keywds2extract = {'DATE-OBS': {'loc': 'main_hdr', 'alt_key': None, 'name': 'date_obs', 'type': str},
                               'OBS_ID': {'loc': 'main_hdr', 'alt_key': None, 'name': 'visit_id', 'type': str},
                               'FILTER': {'loc': 'main_hdr', 'alt_key': 'FWA_POS', 'name': 'tafilter', 'type': str},
                               'DETECTOR': {'loc': 'main_hdr', 'alt_key': None, 'name': 'detector', 'type': str},
                               'READOUT': {'loc': 'main_hdr', 'alt_key': 'READPATT', 'name': 'readout', 'type': str},
                               'SUBARRAY': {'loc': 'main_hdr', 'alt_key': None, 'name': 'subarray', 'type': str},
                               'NUMREFST': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'num_refstars', 'type': int},
                               'TASTATUS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'ta_status', 'type': str},
                               'STAT_RSN': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'status_rsn', 'type': str},
                               'V2HFOFFS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'v2halffacet', 'type': float},
                               'V3HFOFFS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'v3halffacet', 'type': float},
                               'V2MSACTR': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'v2msactr', 'type': float},
                               'V3MSACTR': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'v3msactr', 'type': float},
                               'FITXOFFS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'lsv2offset', 'type': float},
                               'FITYOFFS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'lsv3offset', 'type': float},
                               'OFFSTMAG': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'lsoffsetmag', 'type': float},
                               'FITROFFS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'lsrolloffset', 'type': float},
                               'FITXSIGM': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'lsv2sigma', 'type': float},
                               'FITYSIGM': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'lsv3sigma', 'type': float},
                               'ITERATNS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'lsiterations', 'type': int},
                               'GUIDERID': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'guidestarid', 'type': str},
                               'IDEAL_X': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'guidestarx', 'type': float},
                               'IDEAL_Y': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'guidestary', 'type': float},
                               'IDL_ROLL': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'guidestarroll', 'type': float},
                               'SAM_X': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'samx', 'type': float},
                               'SAM_Y': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'samy', 'type': float},
                               'SAM_ROLL': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'samroll', 'type': float},
                               'box_peak_value': {'loc': 'ta_table', 'alt_key': None, 'name': 'box_peak_value', 'type': float},
                               'reference_star_mag': {'loc': 'ta_table', 'alt_key': None, 'name': 'reference_star_mag', 'type': float},
                               'convergence_status': {'loc': 'ta_table', 'alt_key': None, 'name': 'convergence_status', 'type': str},
                               'reference_star_number': {'loc': 'ta_table', 'alt_key': None, 'name': 'reference_star_number', 'type': int},
                               'lsf_removed_status': {'loc': 'ta_table', 'alt_key': None, 'name': 'lsf_removed_status', 'type': str},
                               'lsf_removed_reason': {'loc': 'ta_table', 'alt_key': None, 'name': 'lsf_removed_reason', 'type': str},
                               'lsf_removed_x': {'loc': 'ta_table', 'alt_key': None, 'name': 'lsf_removed_x', 'type': float},
                               'lsf_removed_y': {'loc': 'ta_table', 'alt_key': None, 'name': 'lsf_removed_y', 'type': float},
                               'planned_v2': {'loc': 'ta_table', 'alt_key': None, 'name': 'planned_v2', 'type': float},
                               'planned_v3': {'loc': 'ta_table', 'alt_key': None, 'name': 'planned_v3', 'type': float},
                               'FITTARGS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'stars_in_fit', 'type': int}}

    def get_tainfo_from_fits(self, fits_file):
        """ Get the TA information from the fits file
        Parameters
        ----------
        fits_file: str
            This is the fits file for a specific MSATA

        Returns
        -------
        msata_info: list, contains main header, and TA extension header and data
        """
        msata = False
        with fits.open(fits_file) as ff:
            # make sure this is a MSATA file
            for hdu in ff:
                if 'MSA_TARG_ACQ' in hdu.name:
                    msata = True
                    break
            if not msata:
                # print('\n WARNING! This file is not MSATA: ', fits_file)
                # print('  Skiping msata_monitor for this file  \n')
                return None
            main_hdr = ff[0].header
            ta_hdr = ff['MSA_TARG_ACQ'].header
            ta_table = ff['MSA_TARG_ACQ'].data
        msata_info = [main_hdr, ta_hdr, ta_table]
        return msata_info

    def get_msata_data(self, new_filenames):
        """ Get the TA information from the MSATA text table
        Parameters
        ----------
        new_filenames: list
            List of MSATA file names to consider

        Returns
        -------
        msata_df: data frame object
            Pandas data frame containing all MSATA data
        """
        # fill out the dictionary to create the dataframe
        msata_dict = {}
        for fits_file in new_filenames:
            msata_info = self.get_tainfo_from_fits(fits_file)
            if msata_info is None:
                continue
            main_hdr, ta_hdr, ta_table = msata_info
            for key, key_dict in self.keywds2extract.items():
                key_name = key_dict['name']
                if key_name not in msata_dict:
                    msata_dict[key_name] = []
                ext = main_hdr
                if key_dict['loc'] == 'ta_hdr':
                    ext = ta_hdr
                if key_dict['loc'] == 'ta_table':
                    ext = ta_table
                try:
                    val = ext[key]
                except KeyError:
                    val = ext[key_dict['alt_key']]
                """ UNCOMMENT THIS BLOCK IN CASE WE DO WANT TO GET RID OF the 999.0 values
                # remove the 999 values for arrays
                if isinstance(val, np.ndarray):
                    if val.dtype.char == 'd' or val.dtype.char == 'f':
                        val = np.where(abs(val) != 999.0, val, 0.0)
                # remove the 999 from single values
                elif not isinstance(val, str):
                    if float(abs(val)) == 999.0:
                        val = 0.0
                """
                msata_dict[key_name].append(val)
        # create the pandas dataframe
        msata_df = pd.DataFrame(msata_dict)
        msata_df.index = msata_df.index + 1
        return msata_df

    def plt_status(self):
        """ Plot the MSATA status versus time.
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # ta_status, date_obs = source.data['ta_status'], source.data['date_obs']
        date_obs = self.source.data['date_obs']
        ta_status = self.source.data['ta_status']
        # bokeh does not like to plot strings, turn  into numbers
        number_status, time_arr, status_colors = [], [], []
        for tas, do_str in zip(ta_status, date_obs):
            if 'success' in tas.lower():
                number_status.append(1.0)
                status_colors.append('blue')
            elif 'progress' in tas.lower():
                number_status.append(0.5)
                status_colors.append('green')
            else:
                number_status.append(0.0)
                status_colors.append('red')
            # convert time string into an array of time (this is in UT)
            t = datetime.fromisoformat(do_str)
            time_arr.append(t)
        # add these to the bokeh data structure
        self.source.data["time_arr"] = time_arr
        self.source.data["number_status"] = number_status
        self.source.data["status_colors"] = status_colors
        # create a new bokeh plot
        plot = figure(title="MSATA Status [Succes=1, In_Progress=0.5, Fail=0]", x_axis_label='Time',
                      y_axis_label='MSATA Status', x_axis_type='datetime',)
        plot.y_range = Range1d(-0.5, 1.5)
        plot.circle(x='time_arr', y='number_status', source=self.source,
                    color='status_colors', size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('TA status', '@ta_status'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray')]

        plot.add_tools(hover)
        return plot

    def plt_residual_offsets(self):
        """ Plot the residual Least Squares V2 and V3 offsets
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares Residual V2-V3 Offsets",
                      x_axis_label='Least Squares Residual V2 Offset',
                      y_axis_label='Least Squares Residual V3 Offset')
        plot.circle(x='lsv2offset', y='lsv3offset', source=self.source,
                    color="purple", size=7, fill_alpha=0.4)
        v2halffacet, v3halffacet = self.source.data['v2halffacet'], self.source.data['v3halffacet']
        xstart, ystart, ray_length = -1 * v2halffacet[0], -1 * v3halffacet[0], 0.05
        plot.ray(x=xstart - ray_length / 2.0, y=ystart, length=ray_length, angle_units="deg", angle=0)
        plot.ray(x=xstart, y=ystart - ray_length / 2.0, length=ray_length, angle_units="deg", angle=90)
        hflabel = Label(x=xstart / 3.0, y=ystart, y_units='data', text='-V2, -V3 half-facets values')
        plot.add_layout(hflabel)
        plot.x_range = Range1d(-0.5, 0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin lines
        vline = Span(location=0, dimension='height', line_color='black', line_width=0.7)
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([vline, hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V3 offset', '@lsv3offset')]

        plot.add_tools(hover)
        return plot

    def plt_v2offset_time(self):
        """ Plot the residual V2 versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares V2 Offset vs Time", x_axis_label='Time',
                      y_axis_label='Least Squares Residual V2 Offset', x_axis_type='datetime')
        plot.circle(x='time_arr', y='lsv2offset', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        time_arr, v2halffacet = self.source.data['time_arr'], self.source.data['v2halffacet']
        hfline = Span(location=-1 * v2halffacet[0], dimension='width', line_color='green', line_width=3)
        plot.renderers.extend([hline, hfline])
        hflabel = Label(x=time_arr[-1], y=-1 * v2halffacet[0], y_units='data', text='-V2 half-facet value')
        plot.add_layout(hflabel)
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V3 offset', '@lsv3offset')]

        plot.add_tools(hover)
        return plot

    def plt_v3offset_time(self):
        """ Plot the residual V3 versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares V3 Offset vs Time", x_axis_label='Time',
                      y_axis_label='Least Squares Residual V3 Offset', x_axis_type='datetime')
        plot.circle(x='time_arr', y='lsv3offset', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        time_arr, v3halffacet = self.source.data['time_arr'], self.source.data['v3halffacet']
        hfline = Span(location=-1 * v3halffacet[0], dimension='width', line_color='green', line_width=3)
        plot.renderers.extend([hline, hfline])
        hflabel = Label(x=time_arr[-1], y=-1 * v3halffacet[0], y_units='data', text='-V3 half-facet value')
        plot.add_layout(hflabel)
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V3 offset', '@lsv3offset')]

        plot.add_tools(hover)
        return plot

    def plt_lsv2v3offsetsigma(self):
        """ Plot the residual Least Squares V2 and V3 sigma offsets
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares Residual V2-V3 Sigma Offsets",
                      x_axis_label='Least Squares Residual V2 Sigma Offset',
                      y_axis_label='Least Squares Residual V3 Sigma Offset')
        plot.circle(x='lsv2sigma', y='lsv3sigma', source=self.source,
                    color="purple", size=7, fill_alpha=0.4)
        plot.x_range = Range1d(-0.1, 0.1)
        plot.y_range = Range1d(-0.1, 0.1)
        # mark origin lines
        vline = Span(location=0, dimension='height', line_color='black', line_width=0.7)
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([vline, hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V2 sigma', '@lsv2sigma'),
                          ('LS V3 offset', '@lsv3offset'),
                          ('LS V3 sigma', '@lsv3sigma')]

        plot.add_tools(hover)
        return plot

    def plt_res_offsets_corrected(self):
        """ Plot the residual Least Squares V2 and V3 offsets corrected by the half-facet
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        lsv2offset, lsv3offset = self.source.data['lsv2offset'], self.source.data['lsv3offset']
        v2halffacet, v3halffacet = self.source.data['v2halffacet'], self.source.data['v3halffacet']
        v2_half_fac_corr, v3_half_fac_corr = [], []
        for idx, v2hf in enumerate(v2halffacet):
            v3hf = v3halffacet[idx]
            v2_half_fac_corr.append(lsv2offset[idx] + v2hf)
            v3_half_fac_corr.append(lsv3offset[idx] + v3hf)
        # add these to the bokeh data structure
        self.source.data["v2_half_fac_corr"] = v2_half_fac_corr
        self.source.data["v3_half_fac_corr"] = v3_half_fac_corr
        plot = figure(title="MSATA Least Squares Residual V2-V3 Offsets Half-facet corrected",
                      x_axis_label='Least Squares Residual V2 Offset + half-facet',
                      y_axis_label='Least Squares Residual V3 Offset + half-facet')
        plot.circle(x='v2_half_fac_corr', y='v3_half_fac_corr', source=self.source,
                    color="purple", size=7, fill_alpha=0.4)
        plot.x_range = Range1d(-0.5, 0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin lines
        vline = Span(location=0, dimension='height', line_color='black', line_width=0.7)
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([vline, hline])
        xstart, ystart, ray_length = -1 * v2halffacet[0], -1 * v3halffacet[0], 0.05
        plot.ray(x=xstart - ray_length / 2.0, y=ystart, length=ray_length, angle_units="deg", angle=0)
        plot.ray(x=xstart, y=ystart - ray_length / 2.0, length=ray_length, angle_units="deg", angle=90)
        hflabel = Label(x=xstart / 3.0, y=ystart, y_units='data', text='-V2, -V3 half-facets values')
        plot.add_layout(hflabel)
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V3 offset', '@lsv3offset'),
                          ('V2 half-facet', '@v2halffacet'),
                          ('V3 half-facet', '@v3halffacet')]

        plot.add_tools(hover)
        return plot

    def plt_v2offsigma_time(self):
        """ Plot the residual Least Squares V2 sigma Offset versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares V2 Sigma Offset vs Time", x_axis_label='Time',
                      y_axis_label='Least Squares Residual V2 Sigma Offset', x_axis_type='datetime')
        plot.circle(x='time_arr', y='lsv2sigma', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-0.1, 0.1)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V2 sigma', '@lsv2sigma')]

        plot.add_tools(hover)
        return plot

    def plt_v3offsigma_time(self):
        """ Plot the residual Least Squares V3 Offset versus time
        Parameters
        ----------
            None
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares V3 Sigma Offset vs Time", x_axis_label='Time',
                      y_axis_label='Least Squares Residual V3 Sigma Offset', x_axis_type='datetime')
        plot.circle(x='time_arr', y='lsv3sigma', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-0.1, 0.1)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS V3 offset', '@lsv3offset'),
                          ('LS V3 sigma', '@lsv3sigma')]

        plot.add_tools(hover)
        return plot

    def plt_roll_offset(self):
        """ Plot the residual Least Squares roll Offset versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares Roll Offset vs Time", x_axis_label='Time',
                      y_axis_label='Least Squares Residual Roll Offset', x_axis_type='datetime')
        plot.circle(x='time_arr', y='lsrolloffset', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-600.0, 600.0)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        # Maximum accepted roll line and label
        time_arr = self.source.data['time_arr']
        arlinepos = Span(location=120, dimension='width', line_color='green', line_width=3)
        arlineneg = Span(location=-120, dimension='width', line_color='green', line_width=3)
        arlabel = Label(x=time_arr[-1], y=125, y_units='data', text='Max accepted roll')
        plot.add_layout(arlabel)
        plot.renderers.extend([hline, arlinepos, arlineneg])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V3 offset', '@lsv3offset')]

        plot.add_tools(hover)
        return plot

    def plt_lsoffsetmag(self):
        """ Plot the residual Least Squares Total Slew Magnitude Offset versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="MSATA Least Squares Total Magnitude of the Linear V2, V3 Offset Slew vs Time", x_axis_label='Time',
                      y_axis_label='sqrt((V2_off)**2 + (V3_off)**2)', x_axis_type='datetime')
        plot.circle(x='time_arr', y='lsoffsetmag', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS slew mag offset', '@lsoffsetmag'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V3 offset', '@lsv3offset')]

        plot.add_tools(hover)
        return plot

    def plt_tot_number_of_stars(self):
        """ Plot the total number of stars used versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # get the number of stars per array
        visit_id = self.source.data['visit_id']
        reference_star_number = self.source.data['reference_star_number']
        stars_in_fit = self.source.data['stars_in_fit']
        date_obs, time_arr = self.source.data['date_obs'], self.source.data['time_arr']
        # create the list of color per visit and tot_number_of_stars
        colors_list, tot_number_of_stars = [], []
        color_dict = {}
        for i, _ in enumerate(visit_id):
            tot_stars = len(reference_star_number[i])
            tot_number_of_stars.append(tot_stars)
            ci = '#%06X' % randint(0, 0xFFFFFF)
            if visit_id[i] not in color_dict:
                color_dict[visit_id[i]] = ci
            colors_list.append(color_dict[visit_id[i]])
        # add these to the bokeh data structure
        self.source.data["tot_number_of_stars"] = tot_number_of_stars
        self.source.data["colors_list"] = colors_list
        # create a new bokeh plot
        plot = figure(title="Total Number of Measurements vs Time", x_axis_label='Time',
                      y_axis_label='Total number of measurements', x_axis_type='datetime')
        plot.circle(x='time_arr', y='tot_number_of_stars', source=self.source,
                    color='colors_list', size=7, fill_alpha=0.5)
        plot.triangle(x='time_arr', y='stars_in_fit', source=self.source,
                      color='black', size=7, fill_alpha=0.5)
        plot.y_range = Range1d(0.0, 40.0)
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Subarray', '@subarray'),
                          ('Stars in fit', '@stars_in_fit'),
                          ('LS roll offset', '@lsrolloffset'),
                          ('LS slew mag offset', '@lsoffsetmag'),
                          ('LS V2 offset', '@lsv2offset'),
                          ('LS V3 offset', '@lsv3offset')]

        plot.add_tools(hover)
        return plot

    def plt_mags_time(self):
        """ Plot the star magnitudes versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            plot: bokeh plot object
        """
        visit_id = self.source.data['visit_id']
        lsf_removed_status = self.source.data['lsf_removed_status']
        lsf_removed_reason = self.source.data['lsf_removed_reason']
        lsf_removed_x = self.source.data['lsf_removed_x']
        lsf_removed_y = self.source.data['lsf_removed_y']
        planned_v2 = self.source.data['planned_v2']
        planned_v3 = self.source.data['planned_v3']
        reference_star_number = self.source.data['reference_star_number']
        visits_stars_mags = self.source.data['reference_star_mag']
        box_peak_value = self.source.data['box_peak_value']
        date_obs, time_arr = self.source.data['date_obs'], self.source.data['time_arr']
        colors_list = self.source.data['colors_list']
        # create the structure matching the number of visits and reference stars
        new_colors_list, vid, dobs, tarr, star_no, status = [], [], [], [], [], []
        peaks, stars_v2, stars_v3 = [], [], []
        for i, _ in enumerate(visit_id):
            v, d, t, c, s, x, y = [], [], [], [], [], [], []
            for j in range(len(reference_star_number[i])):
                v.append(visit_id[i])
                d.append(date_obs[i])
                t.append(time_arr[i])
                c.append(colors_list[i])
                if 'not_removed' in lsf_removed_status[i][j]:
                    s.append('SUCCESS')
                    x.append(planned_v2[i][j])
                    y.append(planned_v3[i][j])
                else:
                    s.append(lsf_removed_reason[i][j])
                    x.append(lsf_removed_x[i][j])
                    y.append(lsf_removed_y[i][j])
            vid.extend(v)
            dobs.extend(d)
            tarr.extend(t)
            star_no.extend(reference_star_number[i])
            status.extend(s)
            new_colors_list.extend(c)
            stars_v2.extend(x)
            stars_v3.extend(y)
            peaks.extend(box_peak_value[i])
        # now create the mini ColumnDataSource for this particular plot
        mini_source = {'vid': vid, 'star_no': star_no, 'status': status,
                       'dobs': dobs, 'tarr': tarr,
                       'peaks': peaks, 'colors_list': new_colors_list,
                       'stars_v2': stars_v2, 'stars_v3': stars_v2}
        mini_source = ColumnDataSource(data=mini_source)
        # create a the bokeh plot
        plot = figure(title="MSATA Counts vs Time", x_axis_label='Time', y_axis_label='box_peak [Counts]',
                      x_axis_type='datetime')
        plot.circle(x='tarr', y='peaks', source=mini_source,
                    color='colors_list', size=7, fill_alpha=0.5)
        # add count saturation warning lines
        loc1, loc2, loc3 = 45000.0, 50000.0, 60000.0
        hline1 = Span(location=loc1, dimension='width', line_color='green', line_width=3)
        hline2 = Span(location=loc2, dimension='width', line_color='yellow', line_width=3)
        hline3 = Span(location=loc3, dimension='width', line_color='red', line_width=3)
        plot.renderers.extend([hline1, hline2, hline3])
        label1 = Label(x=time_arr[-1], y=loc1, y_units='data', text='45000 counts')
        label2 = Label(x=time_arr[-1], y=loc2, y_units='data', text='50000 counts')
        label3 = Label(x=time_arr[-1], y=loc3, y_units='data', text='60000 counts')
        plot.add_layout(label1)
        plot.add_layout(label2)
        plot.add_layout(label3)
        plot.y_range = Range1d(-1000.0, 62000.0)
        # add hover
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@vid'),
                          ('Star No.', '@star_no'),
                          ('LS Status', '@status'),
                          ('Date-Obs', '@dobs'),
                          ('Box peak', '@peaks'),
                          ('Measured V2', '@stars_v2'),
                          ('Measured V3', '@stars_v3')]

        plot.add_tools(hover)
        return plot

    def mk_plt_layout(self):
        """Create the bokeh plot layout"""
        self.source = ColumnDataSource(data=self.msata_data)
        # make sure all arrays are lists in order to later be able to read the data
        # from the html file
        for item in self.source.data:
            if not isinstance(self.source.data[item], (str, float, int, list)):
                self.source.data[item] = self.source.data[item].tolist()
        # set the output html file name and create the plot grid
        output_file(self.output_file_name)
        p1 = self.plt_status()
        p2 = self.plt_residual_offsets()
        p3 = self.plt_res_offsets_corrected()
        p4 = self.plt_v2offset_time()
        p5 = self.plt_v3offset_time()
        p6 = self.plt_lsv2v3offsetsigma()
        p7 = self.plt_v2offsigma_time()
        p8 = self.plt_v3offsigma_time()
        p9 = self.plt_roll_offset()
        p10 = self.plt_lsoffsetmag()
        p12 = self.plt_tot_number_of_stars()
        p11 = self.plt_mags_time()
        # make grid
        grid = gridplot([p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12],
                        ncols=2, merge_tools=False)
        # show(grid)
        save(grid)
        # return the needed components for embeding the results in the MSATA html template
        script, div = components(grid)
        return script, div

    def identify_tables(self):
        """Determine which database tables to use for a run of the TA monitor."""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}TAQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}TAStats'.format(mixed_case_name))

    def most_recent_search(self):
        """Query the query history database and return the information
        on the most recent query for the given 'aperture_name' where
        the msata monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the msata monitor was run.
        """
        query = session.query(self.query_table).filter(and_(self.query_table.aperture == self.aperture,
                                                            self.query_table.run_monitor == True)).order_by(self.query_table.end_time_mjd).all()

        dates = np.zeros(0)
        for instance in query:
            dates = np.append(dates, instance.end_time_mjd)

        query_count = len(dates)
        if query_count == 0:
            query_result = 59607.0  # a.k.a. Jan 28, 2022 == First JWST images (MIRI)
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'
                         .format(self.aperture, query_result)))
        else:
            query_result = np.max(dates)

        return query_result

    def get_data_from_html(self, html_file):
        """
        This function gets the data from the Bokeh html file created with
        the NIRSpec TA monitor script.
        Parameters
        ----------
        html_file: str
            File created by the monitor script
        Returns
        -------
        prev_data_dict: dictionary
            Dictionary containing all data used in the plots
        """

        # open the html file and get the contents
        htmlFileToBeOpened = open(html_file, "r")
        contents = htmlFileToBeOpened.read()
        soup = BeautifulSoup(contents, 'html.parser')

        # now read as python dictionary and search for the data
        prev_data_dict = {}
        html_data = json.loads(soup.find('script', type='application/json').string)
        for key, val in html_data.items():
            if 'roots' in val:   # this is a dictionary
                if 'references' in val['roots']:
                    for item in val['roots']['references']:    # this is a list
                        # each item of the list is a dictionary
                        for item_key, item_val in item.items():
                            if 'data' in item_val:
                                # finally the data dictionary!
                                for data_key, data_val in item_val['data'].items():
                                    prev_data_dict[data_key] = data_val
        # set to None if dictionary is empty
        if not bool(prev_data_dict):
            prev_data_dict = None
        return prev_data_dict

    def construct_expected_data(self, keywd_dict, tot_number_of_stars):
        """This function creates the list to append to the dictionary key in the expected format.
        Parameters
        ----------
        keywd_dict: dictonary
            Dictionary corresponding to the file keyword
        tot_number_of_stars: integer
            Number of stars in the observation
        Returns
        -------
        list4dict: list
            List to be appended to the data structure. Has the right length but no real values
        """
        list4dict = []
        for tns in tot_number_of_stars:   # elements the list of lists should have
            # set the value to add
            val = -999
            # create either the list or return the right type of value
            if keywd_dict['loc'] != 'ta_table':  # these cases should be singe values per observation
                if keywd_dict['type'] == float:
                    val = float(val)
                if keywd_dict['type'] == str:
                    val = str(val)
                list4dict = val
            else:
                list2append = []
                for _ in range(tns):   # elements each sublist should have
                    if keywd_dict['type'] == float:
                        val = float(val)
                    if keywd_dict['type'] == str:
                        val = str(val)
                    list2append.append(val)
                list4dict.append(list2append)
        return list4dict

    def prev_data2expected_format(self, prev_data_dict):
        """Add all the necessary columns to match expected format to combine previous
        and new data.
        Parameters
        ----------
        prev_data_dict: dictionary
            Dictionary containing all data used in the Bokeh html file plots
        Returns
        -------
        prev_data: pandas dataframe
            Contains all expected columns to be combined with the new data
        latest_prev_obs: str
            Date of the latest observation in the previously plotted data
        """
        latest_prev_obs = max(prev_data_dict['tarr'])
        prev_data_expected_cols = {}
        tot_number_of_stars = prev_data_dict['tot_number_of_stars']
        for file_keywd, keywd_dict in self.keywds2extract.items():
            key = keywd_dict['name']
            if key in prev_data_dict:
                # case when all the info of all visits and ref stars is in the same list
                if len(prev_data_dict[key]) > len(tot_number_of_stars):
                    correct_arrangement = []
                    correct_start_idx, correct_end_idx = 0, tot_number_of_stars[0]
                    for idx, tns in enumerate(tot_number_of_stars):
                        list2append = prev_data_dict[key][correct_start_idx: correct_end_idx]
                        correct_arrangement.append(list2append)
                        correct_start_idx = correct_end_idx
                        correct_end_idx += tns
                    prev_data_expected_cols[key] = correct_arrangement
                # case when the html stored thing is just an object but does not have data
                elif len(prev_data_dict[key]) < len(tot_number_of_stars):
                    list4dict = self.construct_expected_data(keywd_dict, tot_number_of_stars)
                    prev_data_expected_cols[key] = list4dict
                # case when nothing special to do
                else:
                    prev_data_expected_cols[key] = prev_data_dict[key]
            else:
                list4dict = self.construct_expected_data(keywd_dict, tot_number_of_stars)
                prev_data_expected_cols[key] = list4dict
        # now convert to a panda dataframe to be combined with the new data
        prev_data = pd.DataFrame(prev_data_expected_cols)
        return prev_data, latest_prev_obs

    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for further details."""

        logging.info('Begin logging for msata_monitor')

        # define MSATA variables
        self.instrument = "nirspec"
        self.aperture = "NRS_FULL_MSA"

        # Identify which database tables to use
        self.identify_tables()

        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()['outputs'], 'msata_monitor')
        ensure_dir_exists(self.output_dir)
        # Set up directory to store the data
        ensure_dir_exists(os.path.join(self.output_dir, 'data'))
        self.data_dir = os.path.join(self.output_dir,
                                     'data/{}_{}'.format(self.instrument.lower(),
                                                         self.aperture.lower()))
        ensure_dir_exists(self.data_dir)

        # Locate the record of most recent MAST search; use this time
        self.query_start = self.most_recent_search()
        # get the data of the plots previously created and set the query start date
        self.prev_data = None
        self.output_file_name = os.path.join(self.output_dir, "msata_layout.html")
        if os.path.isfile(self.output_file_name):
            prev_data_dict = self.get_data_from_html(self.output_file_name)
            self.prev_data, self.query_start = self.prev_data2expected_format(prev_data_dict)
            logging.info('\tPrevious data read from html file: {}'.format(self.output_file_name))

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd
        logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

        # Query MAST using the aperture and the time of the
        # most recent previous search as the starting time
        new_entries = monitor_utils.mast_query_ta(self.instrument, self.aperture, self.query_start, self.query_end)
        msata_entries = len(new_entries)
        logging.info('\tMAST query has returned {} new MSATA files for {}, {} to run the MSATA monitor.'.format(msata_entries, self.instrument, self.aperture))

        # Get full paths to the files
        new_filenames = []
        for entry_dict in new_entries:
            filename_of_interest = entry_dict['productFilename']
            try:
                new_filenames.append(filesystem_path(filename_of_interest))
            except FileNotFoundError:
                logging.warning('\t\tUnable to locate {} in filesystem. Not including in processing.'.format(filename_of_interest))

        if len(new_filenames) == 0:
            logging.warning('\t\t ** Unable to locate any file in filesystem. Nothing to process. ** ')

        # Run the monitor on any new files
        logging.info('\tMSATA monitor found {} new uncal files.'.format(len(new_filenames)))
        self.script, self.div, self.msata_data = None, None, None
        monitor_run = False
        if len(new_filenames) > 0:   # new data was found
            # get the data
            self.new_msata_data = self.get_msata_data(new_filenames)
            if self.new_msata_data is not None:
                # concatenate with previous data
                if self.prev_data is not None:
                    self.msata_data = pd.concat([self.prev_data, self.new_msata_data])
                else:
                    self.msata_data = self.new_msata_data
            else:
                logging.info('\tMSATA monitor skipped. No MSATA data found.')
        # make sure to return the old data if no new data is found
        elif self.prev_data is not None:
            self.msata_data = self.prev_data
        # make the plots if there is data
        if self.msata_data is not None:
            self.script, self.div = self.mk_plt_layout()
            monitor_run = True
        else:
            logging.info('\tMSATA monitor skipped.')

        # Update the query history
        new_entry = {'instrument': 'nirspec',
                     'aperture': self.aperture,
                     'start_time_mjd': self.query_start,
                     'end_time_mjd': self.query_end,
                     'entries_found': msata_entries,
                     'files_found': len(new_filenames),
                     'run_monitor': monitor_run,
                     'entry_date': datetime.now()}
        self.query_table.__table__.insert().execute(new_entry)
        logging.info('\tUpdated the query history table')

        logging.info('MSATA Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = MSATA()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
