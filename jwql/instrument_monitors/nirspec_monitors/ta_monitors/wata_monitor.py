#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# HISTORY
#    Feb 2022 - Vr. 1.0: Completed initial version
#    Sep 2022 - Vr. 1.1: Modified ColumnDataSource so that data could be recovered
#                        from an html file of a previous run of the monitor and
#                        included the code to read and format the data from the html file


"""
This module contains the code for NIRSpec the Wide Aperture Target
Acquisition (WATA) monitor, which monitors the TA offsets.

This monitor displays the comparison of desired versus measured TA.

This monitor also displays V2, V3 offsets over time.

Author
______
    - Maria Pena-Guerrero

Use
---
    This module can be used from the command line as follows:
    python wata_monitor.py

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
from sqlalchemy.sql.expression import and_
from bokeh.io import output_file
from bokeh.plotting import figure, save
from bokeh.models import ColumnDataSource, Range1d
from bokeh.models.tools import HoverTool
from bokeh.layouts import gridplot
from bokeh.models import Span, Label
from bokeh.embed import components

# jwql imports
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils import monitor_utils
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.database.database_interface import session, engine
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config


class WATA():
    """ Class for executint the NIRSpec WATA monitor.

    This class will search for new WATA current files in the file systems
    for NIRSpec and will run the monitor on these files. The monitor will
    extract the TA information from the file headers and perform all
    statistical measurements. Results will be saved to the WATA database.

    Attributes
    ----------
    output_dir : str
        Path into which outputs will be placed.

    data_dir : str
        Path into which new dark files will be copied to be worked on.

    query_start : float
        MJD start date to use for querying MAST.

    query_end : float
        MJD end date to use for querying MAST.

    aperture : str
        Name of the aperture used for the dark current (e.g.
        "NRS_FULL_MSA", "NRS_S1600A1_SLIT").
    """

    def __init__(self):
        """ Initialize an instance of the WATA class """
        # Very beginning of intake of images: Jan 28, 2022 == First JWST images (MIRI)
        self.query_very_beginning = 59607.0

        # structure to define required keywords to extract and where they live
        self.keywds2extract = {'FILENAME': {'loc': 'main_hdr', 'alt_key': None, 'name': 'filename', 'type': str},
                               'DATE-OBS': {'loc': 'main_hdr', 'alt_key': None, 'name': 'date_obs'},
                               'OBS_ID': {'loc': 'main_hdr', 'alt_key': 'OBSID', 'name': 'visit_id'},
                               'FILTER': {'loc': 'main_hdr', 'alt_key': 'FWA_POS', 'name': 'tafilter'},
                               'READOUT': {'loc': 'main_hdr', 'alt_key': 'READPATT', 'name': 'readout'},
                               'TASTATUS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'ta_status'},
                               'STAT_RSN': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'status_reason'},
                               'REFSTNAM': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'star_name'},
                               'REFSTRA': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'star_ra'},
                               'REFSTDEC': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'star_dec'},
                               'REFSTMAG': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'star_mag'},
                               'REFSTCAT': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'star_catalog'},
                               'V2_PLAND': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'planned_v2'},
                               'V3_PLAND': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'planned_v3'},
                               'EXTCOLST': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'stamp_start_col'},
                               'EXTROWST': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'stamp_start_row'},
                               'TA_DTCTR': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'star_detector'},
                               'BOXPKVAL': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'max_val_box'},
                               'BOXPKCOL': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'max_val_box_col'},
                               'BOXPKROW': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'max_val_box_row'},
                               'TA_ITERS': {'loc': 'ta_hdr', 'alt_key': 'CENITERS', 'name': 'iterations'},
                               'CORR_COL': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'corr_col'},
                               'CORR_ROW': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'corr_row'},
                               'IMCENCOL': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'stamp_final_col'},
                               'IMCENROW': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'stamp_final_row'},
                               'DTCENCOL': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'detector_final_col'},
                               'DTCENROW': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'detector_final_row'},
                               'SCIXCNTR': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'final_sci_x'},
                               'SCIYCNTR': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'final_sci_y'},
                               'TARGETV2': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'measured_v2'},
                               'TARGETV3': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'measured_v3'},
                               'V2_REF': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'ref_v2'},
                               'V3_REF': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'ref_v3'},
                               'V2_RESID': {'loc': 'ta_hdr', 'alt_key': 'V2_OFFST', 'name': 'v2_offset'},
                               'V3_RESID': {'loc': 'ta_hdr', 'alt_key': 'V3_OFFST', 'name': 'v3_offset'},
                               'SAM_X': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'sam_x'},
                               'SAM_Y': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'sam_y'}}

    def get_tainfo_from_fits(self, fits_file):
        """ Get the TA information from the fits file
        Parameters
        ----------
        fits_file: str
            This is the fits file for a specific WATA

        Returns
        -------
        hdr: dictionary
            Dictionary of the primary extension
        """
        wata = False
        with fits.open(fits_file) as ff:
            # make sure this is a WATA file
            for hdu in ff:
                if 'TARG_ACQ' in hdu.name:
                    wata = True
                    break
            if not wata:
                # print('\n WARNING! This file is not WATA: ', fits_file)
                # print('  Skiping wata_monitor for this file  \n')
                return None
            main_hdr = ff[0].header
            try:
                ta_hdr = ff['TARG_ACQ'].header
            except KeyError:
                no_ta_ext_msg = 'No TARG_ACQ extension in file '+fits_file
                return no_ta_ext_msg
        wata_info = [main_hdr, ta_hdr]
        return wata_info

    def get_wata_data(self, new_filenames):
        """ Create the data array for the WATA input files
        Parameters
        ----------
        new_filenames: list
            List of WATA file names to consider

        Returns
        -------
        wata_df: data frame object
            Pandas data frame containing all WATA data
        """
        # fill out the dictionary to create the dataframe
        wata_dict, no_ta_ext_msgs = {}, []
        for fits_file in new_filenames:
            wata_info = self.get_tainfo_from_fits(fits_file)
            if isinstance(wata_info, str):
                no_ta_ext_msgs.append(wata_info)
                continue
            if wata_info is None:
                continue
            main_hdr, ta_hdr = wata_info
            for key, key_dict in self.keywds2extract.items():
                key_name = key_dict['name']
                if key_name not in wata_dict:
                    wata_dict[key_name] = []
                ext = main_hdr
                if key_dict['loc'] == 'ta_hdr':
                    ext = ta_hdr
                try:
                    val = ext[key]
                    if key == 'filename':
                        val = fits_file
                except KeyError:
                    val = ext[key_dict['alt_key']]
                wata_dict[key_name].append(val)
        # create the pandas dataframe
        wata_df = pd.DataFrame(wata_dict)
        return wata_df, no_ta_ext_msgs

    def plt_status(self):
        """ Plot the WATA status (passed = 0 or failed = 1).
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        ta_status, date_obs = self.source.data['ta_status'], self.source.data['date_obs']
        # check if this column exists in the data already (the other 2 will exist too), else create it
        try:
            time_arr = self.source.data['time_arr']
            bool_status = self.source.data['bool_status']
            status_colors = self.source.data['status_colors']
        except KeyError:
            # bokeh does not like to plot strings, turn  into binary type
            bool_status, time_arr, status_colors = [], [], []
            for tas, do_str in zip(ta_status, date_obs):
                if 'unsuccessful' not in tas.lower():
                    bool_status.append(1)
                    status_colors.append('blue')
                else:
                    bool_status.append(0)
                    status_colors.append('red')
                # convert time string into an array of time (this is in UT)
                t = datetime.fromisoformat(do_str)
                time_arr.append(t)
            # add these to the bokeh data structure
            self.source.data["time_arr"] = time_arr
            self.source.data["ta_status_bool"] = bool_status
            self.source.data["status_colors"] = status_colors
        # create a new bokeh plot
        plot = figure(title="WATA Status [Succes=1, Fail=0]", x_axis_label='Time',
                      y_axis_label='WATA Status', x_axis_type='datetime',)
        plot.y_range = Range1d(-0.5, 1.5)
        plot.circle(x='time_arr', y='ta_status_bool', source=self.source,
                    color='status_colors', size=7, fill_alpha=0.3)
        # output_file("wata_status.html")
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('TA status', '@ta_status'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Magnitude', '@star_mag')]

        plot.add_tools(hover)
        return plot

    def plt_residual_offsets(self):
        """ Plot the residual V2 and V3 offsets
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="WATA Residual V2-V3 Offsets", x_axis_label='Residual V2 Offset',
                      y_axis_label='Residual V3 Offset')
        plot.circle(x='v2_offset', y='v3_offset', source=self.source,
                    color="blue", size=7, fill_alpha=0.3)
        plot.x_range = Range1d(-0.5, 0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin lines
        vline = Span(location=0, dimension='height', line_color='black', line_width=0.7)
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([vline, hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('TA status', '@ta_status'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Magnitude', '@star_mag')]

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
        plot = figure(title="WATA V2 Offset vs Time", x_axis_label='Time',
                      y_axis_label='Residual V2 Offset', x_axis_type='datetime')
        plot.circle(x='time_arr', y='v2_offset', source=self.source,
                    color="blue", size=7, fill_alpha=0.3)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('TA status', '@ta_status'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Magnitude', '@star_mag')]

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
        plot = figure(title="WATA V3 Offset vs Time", x_axis_label='Time',
                      y_axis_label='Residual V3 Offset', x_axis_type='datetime')
        plot.circle(x='time_arr', y='v3_offset', source=self.source,
                    color="blue", size=7, fill_alpha=0.3)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([hline])
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('TA status', '@ta_status'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Magnitude', '@star_mag')]

        plot.add_tools(hover)
        return plot

    def plt_mag_time(self):
        """ Plot the star magnitude versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # calculate the pseudo magnitudes
        max_val_box, time_arr = self.source.data['max_val_box'], self.source.data['time_arr']
        # check if this column exists in the data already (the other 2 will exist too), else create it
        try:
            nrsrapid_f140x = self.source.data["nrsrapid_f140x"]
            nrsrapid_f110w = self.source.data["nrsrapid_f110w"]
            nrsrapid_clear = self.source.data["nrsrapid_clear"]
            nrsrapidd6_f140x = self.source.data["nrsrapidd6_f140x"]
            nrsrapidd6_f110w = self.source.data["nrsrapidd6_f110w"]
            nrsrapidd6_clear = self.source.data["nrsrapidd6_clear"]
        except KeyError:
            # create the arrays per filter and readout pattern
            nrsrapid_f140x, nrsrapid_f110w, nrsrapid_clear = [], [], []
            nrsrapidd6_f140x, nrsrapidd6_f110w, nrsrapidd6_clear = [], [], []
            filter_used, readout = self.source.data['tafilter'], self.source.data['readout']
            for i, val in enumerate(max_val_box):
                if '140' in filter_used[i]:
                    if readout[i].lower() == 'nrsrapid':
                        nrsrapid_f140x.append(val)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                    elif readout[i].lower() == 'nrsrapidd6':
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(val)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                elif '110' in filter_used[i]:
                    if readout[i].lower() == 'nrsrapid':
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(val)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                    elif readout[i].lower() == 'nrsrapidd6':
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(val)
                        nrsrapidd6_clear.append(np.NaN)
                else:
                    if readout[i].lower() == 'nrsrapid':
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(val)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                    elif readout[i].lower() == 'nrsrapidd6':
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(val)
            # add to the bokeh data structure
            self.source.data["nrsrapid_f140x"] = nrsrapid_f140x
            self.source.data["nrsrapid_f110w"] = nrsrapid_f110w
            self.source.data["nrsrapid_clear"] = nrsrapid_clear
            self.source.data["nrsrapidd6_f140x"] = nrsrapidd6_f140x
            self.source.data["nrsrapidd6_f110w"] = nrsrapidd6_f110w
            self.source.data["nrsrapidd6_clear"] = nrsrapidd6_clear
        # create a new bokeh plot
        plot = figure(title="WATA Counts vs Time", x_axis_label='Time',
                      y_axis_label='box_peak [Counts]', x_axis_type='datetime')
        plot.circle(x='time_arr', y='nrsrapid_f140x', source=self.source,
                    color="purple", size=7, fill_alpha=0.4)
        plot.circle(x='time_arr', y='nrsrapidd6_f140x', source=self.source,
                    color="purple", size=12, fill_alpha=0.4)
        plot.triangle(x='time_arr', y='nrsrapid_f110w', source=self.source,
                      color="orange", size=8, fill_alpha=0.4)
        plot.triangle(x='time_arr', y='nrsrapidd6_f110w', source=self.source,
                      color="orange", size=13, fill_alpha=0.4)
        plot.square(x='time_arr', y='nrsrapid_clear', source=self.source,
                    color="gray", size=7, fill_alpha=0.4)
        plot.square(x='time_arr', y='nrsrapidd6_clear', source=self.source,
                    color="gray", size=12, fill_alpha=0.4)
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
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('TA status', '@ta_status'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Box peak', '@max_val_box')]

        plot.add_tools(hover)
        return plot

    def get_unsucessful_ta(self, arr_name):
        """ Find unsucessful TAs in this set (to be plotted in red)
        Parameters
        ----------
            arr_name: str, name of the array of interest
        Returns
        -------
            new_list_failed: list, failed TA values from array of interest
            new_list_else: list, non-failed TA values from array of interest
        """
        bool_status = self.source.data["ta_status_bool"]
        new_list_failed, new_list_else = [], []
        for idx, val in enumerate(self.source.data[arr_name]):
            if bool_status[idx] == 0.0:
                new_list_failed.append(val)
                new_list_else.append(np.NaN)
            else:
                new_list_failed.append(np.NaN)
                new_list_else.append(val)
        return new_list_failed, new_list_else

    def plt_centroid(self):
        """ Plot the WATA centroid
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # get the failed TAs to plot in red
        try:
            corr_col_failed = self.source.data["corr_col_failed"]
        except KeyError:
            corr_col_failed, corr_col_not_failed = self.get_unsucessful_ta('corr_col')
            corr_row_failed, corr_row_not_failed = self.get_unsucessful_ta('corr_row')
            # add these to the bokeh data structure
            self.source.data["corr_col_failed"] = corr_col_failed
            self.source.data["corr_col_not_failed"] = corr_col_not_failed
            self.source.data["corr_row_failed"] = corr_row_failed
            self.source.data["corr_row_not_failed"] = corr_row_not_failed
        # create a new bokeh plot
        plot = figure(title="WATA Centroid", x_axis_label='Column',
                      y_axis_label='Row')
        limits = [10, 25]
        plot.x_range = Range1d(limits[0], limits[1])
        plot.y_range = Range1d(limits[0], limits[1])
        plot.circle(x='corr_col_not_failed', y='corr_row_not_failed', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.circle(x='corr_col_failed', y='corr_row_failed', source=self.source,
                    color="red", size=7, fill_alpha=0.5)
        plot.x_range = Range1d(0.0, 32.0)
        plot.y_range = Range1d(0.0, 32.0)
        hover = HoverTool()
        hover.tooltips = [('Visit ID', '@visit_id'),
                          ('TA status', '@ta_status'),
                          ('Filter', '@tafilter'),
                          ('Readout', '@readout'),
                          ('Date-Obs', '@date_obs'),
                          ('Magnitude', '@star_mag'),
                          ('Box Centr Col', '@corr_col'),
                          ('Box Centr Row', '@corr_row'),
                          ('Det Centr Col', '@detector_final_col'),
                          ('Det Centr Row', '@detector_final_row')]

        plot.add_tools(hover)
        return plot

    def mk_plt_layout(self):
        """Create the bokeh plot layout"""
        self.source = ColumnDataSource(data=self.wata_data)
        # make sure all arrays are lists in order to later be able to read the data
        # from the html file
        for item in self.source.data:
            if not isinstance(self.source.data[item], (str, float, int, list)):
                self.source.data[item] = self.source.data[item].tolist()
        # set the output html file name and create the plot grid
        output_file(self.output_file_name)
        p1 = self.plt_status()
        p2 = self.plt_residual_offsets()
        p3 = self.plt_v2offset_time()
        p4 = self.plt_v3offset_time()
        p5 = self.plt_centroid()
        p6 = self.plt_mag_time()
        # make grid
        grid = gridplot([p1, p2, p3, p4, p5, p6], ncols=2, merge_tools=False)
        save(grid)
        # return the needed components for embeding the results in the WATA html template
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
        the wata monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the wata monitor was run.
        """
        query = session.query(self.query_table).filter(and_(self.query_table.aperture == self.aperture,
                                                            self.query_table.run_monitor is True)).order_by(self.query_table.end_time_mjd).all()

        dates = np.zeros(0)
        for instance in query:
            dates = np.append(dates, instance.end_time_mjd)

        query_count = len(dates)
        if query_count == 0:
            query_result = self.query_very_beginning
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'.format(self.aperture, self.query_very_beginning)))
        else:
            query_result = np.max(dates)

        return query_result

    def get_expected_data(self, keywd_dict, tot_number_of_stars):
        """This function gets the value append to the dictionary key in the expected format.
        Parameters
        ----------
        keywd_dict: dictonary
            Dictionary corresponding to the file keyword
        tot_number_of_stars: integer
            Number of stars in the observation
        Returns
        -------
        val4dict: value
            Value appended to the data structure; either string, float or integer
        """
        # set the value to add
        val = -999
        # return the right type of value
        if keywd_dict['type'] == float:
            val = float(val)
        if keywd_dict['type'] == str:
            val = str(val)
        val4dict = val
        return val4dict

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
        prev_data: pandas dataframe
            Contains all expected columns to be combined with the new data
        latest_prev_obs: str
            Date of the latest observation in the previously plotted data
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
        # find the latest observation date
        time_in_millis = max(prev_data_dict['time_arr'])
        latest_prev_obs = Time(time_in_millis / 1000., format='unix')
        latest_prev_obs = latest_prev_obs.mjd
        # put data in expected format
        prev_data_expected_cols = {}
        visit_ids = prev_data_dict['visit_id']
        for file_keywd, keywd_dict in self.keywds2extract.items():
            key = keywd_dict['name']
            if key in prev_data_dict:
                # case when the html stored thing is just an object but does not have data
                if len(prev_data_dict[key]) < len(visit_ids):
                    list4dict = self.get_expected_data(keywd_dict, visit_ids)
                    prev_data_expected_cols[key] = list4dict
                # case when nothing special to do
                else:
                    prev_data_expected_cols[key] = prev_data_dict[key]
            else:
                list4dict = self.get_expected_data(keywd_dict, visit_ids)
                prev_data_expected_cols[key] = list4dict
        # now convert to a panda dataframe to be combined with the new data
        prev_data = pd.DataFrame(prev_data_expected_cols)
        return prev_data, latest_prev_obs

    def pull_filenames(self, file_info):
        """Extract filenames from the list of file information returned from
        query_mast.

        Parameters
        ----------
        file_info : dict
            Dictionary of file information returned by ``query_mast``

        Returns
        -------
        files : list
            List of filenames (without paths) extracted from ``file_info``
        """
        files = []
        for list_element in file_info:
            if 'filename' in list_element:
                files.append(list_element['filename'])
        return files

    def get_uncal_names(self, file_list):
        """Replace the last suffix for _uncal and return list.
        Parameters
        ----------
        file_list : list
            List of fits files
        Returns
        -------
        good_files : list
            Filtered list of uncal file names
        """
        good_files = []
        for filename in file_list:
            # Names look like: jw01133003001_02101_00001_nrs2_cal.fits
            if '_uncal' not in filename:
                suffix2replace = filename.split('_')[-1]
                filename = filename.replace(suffix2replace, 'uncal.fits')
            if filename not in good_files:
                good_files.append(filename)
        return good_files

    def get_uncal_names(self, file_list):
        """Replace the last suffix for _uncal and return list.
        Parameters
        ----------
        file_list : list
            List of fits files
        Returns
        -------
        good_files : list
            Filtered list of uncal file names
        """
        good_files = []
        for filename in file_list:
            # Names look like: jw01133003001_02101_00001_nrs2_cal.fits
            if '_uncal' not in filename:
                suffix2replace = filename.split('_')[-1]
                filename = filename.replace(suffix2replace, 'uncal.fits')
            if filename not in good_files:
                good_files.append(filename)
        return good_files

    def update_ta_success_txtfile(self):
        """Create a text file with all the failed and successful WATA.
        Parameters
        ----------
            None
        Returns
        -------
            Nothing
        """
        output_success_ta_txtfile = os.path.join(self.output_dir, "wata_success.txt")
        # check if previous file exsists and read the data from it
        if os.path.isfile(output_success_ta_txtfile):
            # now rename the the previous file, for backup
            os.rename(output_success_ta_txtfile, os.path.join(self.output_dir, "prev_wata_success.txt"))
        # get the new data
        ta_success, ta_failure = [], []
        filenames, ta_status = self.wata_data.loc[:,'filename'], self.wata_data.loc[:,'ta_status']
        for fname, ta_stat in zip(filenames, ta_status):
            # select the appriopriate list to append to
            if ta_stat == 'SUCCESSFUL':
                ta_success.append(fname)
            else:
                ta_failure.append(fname)
        # find which one is the longest list (to make sure the other lists have the same length)
        successes, failures = len(ta_success), len(ta_failure)
        longest_list = None
        if successes >= failures:
            longest_list = successes
        else:
            longest_list = failures
        # match length of the lists
        for ta_list in [ta_success, ta_failure]:
            remaining_items = longest_list - len(ta_list)
            if remaining_items != 0:
                for _ in range(remaining_items):
                    ta_list.append("")
        # write the new output file
        with open(output_success_ta_txtfile, 'w+') as txt:
            txt.write("# WATA successes and failure file names \n")
            filehdr1 = "# {} Total successful and {} total failed WATA ".format(successes, failures)
            filehdr2 = "# {:<50} {:<50}".format("Successes", "Failures")
            txt.write(filehdr1 + "\n")
            txt.write(filehdr2 + "\n")
            for idx, suc in enumerate(ta_success):
                line = "{:<50} {:<50}".format(suc, ta_failure[idx])
                txt.write(line + "\n")

    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for further details."""

        logging.info('Begin logging for wata_monitor')

        # define WATA variables
        self.instrument = "nirspec"
        self.aperture = "NRS_S1600A1_SLIT"

        # Identify which database tables to use
        self.identify_tables()

        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()['outputs'], 'wata_monitor')
        ensure_dir_exists(self.output_dir)
        # Set up directories for the copied data
        ensure_dir_exists(os.path.join(self.output_dir, 'data'))
        self.data_dir = os.path.join(self.output_dir,
                                     'data/{}_{}'.format(self.instrument.lower(),
                                                         self.aperture.lower()))
        ensure_dir_exists(self.data_dir)

        # Locate the record of most recent MAST search; use this time
        self.query_start = self.most_recent_search()
        # get the data of the plots previously created and set the query start date
        self.prev_data = None
        self.output_file_name = os.path.join(self.output_dir, "wata_layout.html")
        logging.info('\tNew output plot file will be written as: {}'.format(self.output_file_name))
        if os.path.isfile(self.output_file_name):
            self.prev_data, self.query_start = self.get_data_from_html(self.output_file_name)
            logging.info('\tPrevious data read from html file: {}'.format(self.output_file_name))
            # move this plot to a previous version
            os.rename(self.output_file_name, os.path.join(self.output_dir, "prev_wata_layout.html"))
        # fail save - start from the beginning if there is no html file
        else:
            self.query_start = self.query_very_beginning
            logging.info('\tPrevious output html file not found. Starting MAST query from Jan 28, 2022 == First JWST images (MIRI)')

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd
        logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

        # Query MAST using the aperture and the time of the
        # most recent previous search as the starting time
        new_entries = monitor_utils.mast_query_ta(self.instrument, self.aperture, self.query_start, self.query_end)
        wata_entries = len(new_entries)
        logging.info('\tMAST query has returned {} WATA files for {}, {}.'.format(wata_entries, self.instrument, self.aperture))

        # Filter new entries to only keep uncal files
        new_entries = self.pull_filenames(new_entries)
        new_entries = self.get_uncal_names(new_entries)
        wata_entries = len(new_entries)
        logging.info('\tThere are {} uncal TA files to run the WATA monitor.'.format(wata_entries))

        # Get full paths to the files
        new_filenames = []
        for filename_of_interest in new_entries:
            try:
                new_filenames.append(filesystem_path(filename_of_interest))
                logging.warning('\tFile {} included for processing.'.format(filename_of_interest))
            except FileNotFoundError:
                logging.warning('\t\tUnable to locate {} in filesystem. Not including in processing.'.format(filename_of_interest))

        if len(new_filenames) == 0:
            logging.warning('\t\t ** Unable to locate any file in filesystem. Nothing to process. ** ')

        # Run the monitor on any new files
        self.script, self.div, self.wata_data = None, None, None
        monitor_run = False
        if len(new_filenames) > 0:   # new data was found
            # get the data
            self.new_wata_data, no_ta_ext_msgs = self.get_wata_data(new_filenames)
            if len(no_ta_ext_msgs) >= 1:
                for item in no_ta_ext_msgs:
                    logging.info(item)
            if self.new_wata_data is not None:
                # concatenate with previous data
                if self.prev_data is not None:
                    self.wata_data = pd.concat([self.prev_data, self.new_wata_data])
                    logging.info('\tData from previous html output file and new data concatenated.')
                else:
                    self.wata_data = self.new_wata_data
                    logging.info('\tOnly new data was found - no previous html file.')
            else:
                logging.info('\tWATA monitor skipped. No WATA data found.')
        # make sure to return the old data if no new data is found
        elif self.prev_data is not None:
            self.wata_data = self.prev_data
            logging.info('\tNo new data found. Using data from previous html output file.')
        # do the plots if there is any data
        if self.wata_data is not None:
            self.script, self.div = self.mk_plt_layout()
            monitor_run = True
            logging.info('\tOutput html plot file created: {}'.format(self.output_file_name))
            wata_files_used4plots = len(self.wata_data['visit_id'])
            logging.info('\t{} WATA files were used to make plots.'.format(wata_files_used4plots))
            # update the list of successful and failed TAs
            self.update_ta_success_txtfile()
            logging.info('\t{} WATA status file was updated')
        else:
            logging.info('\tWATA monitor skipped.')

        # Update the query history
        new_entry = {'instrument': self.instrument,
                     'aperture': self.aperture,
                     'start_time_mjd': self.query_start,
                     'end_time_mjd': self.query_end,
                     'entries_found': wata_entries,
                     'files_found': len(new_filenames),
                     'run_monitor': monitor_run,
                     'entry_date': datetime.now()}

        with engine.begin() as connection:
            connection.execute(self.query_table.__table__.insert(), new_entry)
        logging.info('\tUpdated the query history table')

        logging.info('WATA Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = WATA()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
