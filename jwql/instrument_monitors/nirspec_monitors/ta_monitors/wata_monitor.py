#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# HISTORY
#    Feb 2022 - Vr. 1.0: Completed initial version


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
from datetime import datetime
from astropy.time import Time
from astropy.io import fits
from sqlalchemy.sql.expression import and_
from bokeh.io import output_file
from bokeh.plotting import figure, show, save
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
                #print('\n WARNING! This file is not WATA: ', fits_file)
                #print('  Skiping wata_monitor for this file  \n')
                return None
            main_hdr = ff[0].header
            ta_hdr = ff['TARG_ACQ'].header
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
        # structure to define required keywords to extract and where they live
        keywds2extract = {'DATE-OBS': {'loc': 'main_hdr', 'alt_key': None, 'name': 'date_obs'},
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
                          'TA_ITERS': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'iterations'},
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
                          'V2_RESID': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'v2_offset'},
                          'V3_RESID': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'v3_offset'},
                          'SAM_X': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'sam_x'},
                          'SAM_Y': {'loc': 'ta_hdr', 'alt_key': None, 'name': 'sam_y'}
                          }
        # fill out the dictionary  to create the dataframe
        wata_dict = {}
        for fits_file in new_filenames:
            wata_info = self.get_tainfo_from_fits(fits_file)
            if wata_info is None:
                continue
            main_hdr, ta_hdr = wata_info
            for key, key_dict in keywds2extract.items():
                key_name = key_dict['name']
                if key_name not in wata_dict:
                    wata_dict[key_name] = []
                ext = main_hdr
                if key_dict['loc'] == 'ta_hdr':
                    ext = ta_hdr
                try:
                    val = ext[key]
                except:
                    val = ext[key_dict['alt_key']]
                wata_dict[key_name].append(val)
        # create the pandas dataframe
        wata_df = pd.DataFrame(wata_dict)
        wata_df.index = wata_df.index + 1
        return wata_df
            

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
        # bokeh does not like to plot strings, turn  into binary type
        bool_status, time_arr, status_colors = [], [], []
        for tas, do_str in zip(ta_status, date_obs):
            if 'success' in tas.lower():
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
                    color='status_colors', size=7, fill_alpha=0.5)
        #output_file("wata_status.html")
        hover = HoverTool()
        hover.tooltips=[('Visit ID', '@visit_id'),
                        ('TA status', '@ta_status'),
                        ('Filter', '@tafilter'),
                        ('Readout', '@readout'),
                        ('Date-Obs', '@date_obs'),
                        ('Magnitude', '@star_mag')
                        ]
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
                    color="purple", size=7, fill_alpha=0.5)
        plot.x_range = Range1d(-0.5, 0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin lines
        vline = Span(location=0, dimension='height', line_color='black', line_width=0.7)
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([vline, hline])
        hover = HoverTool()
        hover.tooltips=[('Visit ID', '@visit_id'),
                        ('TA status', '@ta_status'),
                        ('Filter', '@tafilter'),
                        ('Readout', '@readout'),
                        ('Date-Obs', '@date_obs'),
                        ('Magnitude', '@star_mag')
                        ]
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
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([hline])
        hover = HoverTool()
        hover.tooltips=[('Visit ID', '@visit_id'),
                        ('TA status', '@ta_status'),
                        ('Filter', '@tafilter'),
                        ('Readout', '@readout'),
                        ('Date-Obs', '@date_obs'),
                        ('Magnitude', '@star_mag')
                        ]
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
        plot.circle(x='time_arr', y='v2_offset', source=self.source,
                    color="blue", size=7, fill_alpha=0.5)
        plot.y_range = Range1d(-0.5, 0.5)
        # mark origin line
        hline = Span(location=0, dimension='width', line_color='black', line_width=0.7)
        plot.renderers.extend([hline])
        hover = HoverTool()
        hover.tooltips=[('Visit ID', '@visit_id'),
                        ('TA status', '@ta_status'),
                        ('Filter', '@tafilter'),
                        ('Readout', '@readout'),
                        ('Date-Obs', '@date_obs'),
                        ('Magnitude', '@star_mag')
                        ]
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
                    color="blue", size=7, fill_alpha=0.5)#, legend_label='F140X NRSRAPID')
        plot.circle(x='time_arr', y='nrsrapidd6_f140x', source=self.source,
                    color="blue", size=12, fill_alpha=0.5)#, legend_label='F140X NRSRAPIDD6')
        plot.triangle(x='time_arr', y='nrsrapid_f110w', source=self.source,
                      color="orange", size=8, fill_alpha=0.7)#, legend_label='F110W NRSRAPID')
        plot.triangle(x='time_arr', y='nrsrapidd6_f110w', source=self.source,
                      color="orange", size=13, fill_alpha=0.7)#, legend_label='F110W NRSRAPIDD6')
        plot.square(x='time_arr', y='nrsrapid_clear', source=self.source,
                    color="gray", size=7, fill_alpha=0.4)#, legend_label='CLEAR NRSRAPID')
        plot.square(x='time_arr', y='nrsrapidd6_clear', source=self.source,
                    color="gray", size=12, fill_alpha=0.4)#, legend_label='CLEAR NRSRAPIDD6')
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
        hover.tooltips=[('Visit ID', '@visit_id'),
                        ('TA status', '@ta_status'),
                        ('Filter', '@tafilter'),
                        ('Readout', '@readout'),
                        ('Date-Obs', '@date_obs'),
                        ('Box peak', '@max_val_box')
                        ]
        plot.add_tools(hover)
        return plot


    def plt_centroid(self):
        """ Plot the WATA centroid
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(title="WATA Centroid", x_axis_label='Column',
                      y_axis_label='Row')
        limits = [10, 25]
        plot.x_range = Range1d(limits[0], limits[1])
        plot.y_range = Range1d(limits[0], limits[1])
        plot.circle(x='corr_col', y='corr_row', source=self.source,
                    color="purple", size=7, fill_alpha=0.5)
        plot.x_range = Range1d(0.0, 32.0)
        plot.y_range = Range1d(0.0, 32.0)
        hover = HoverTool()
        hover.tooltips=[('Visit ID', '@visit_id'),
                        ('TA status', '@ta_status'),
                        ('Filter', '@tafilter'),
                        ('Readout', '@readout'),
                        ('Date-Obs', '@date_obs'),
                        ('Magnitude', '@star_mag'),
                        ('Box Centr Col', '@corr_col'),
                        ('Box Centr Row', '@corr_row'),
                        ('Det Centr Col', '@detector_final_col'),
                        ('Det Centr Row', '@detector_final_row')
                        ]
        plot.add_tools(hover)
        return plot


    def mk_plt_layout(self):
        """Create the bokeh plot layout"""
        self.source = ColumnDataSource(data=self.wata_data)
        output_file(os.path.join(self.output_dir, "wata_layout.html"))
        p1 = self.plt_status()
        p2 = self.plt_residual_offsets()
        p3 = self.plt_v2offset_time()
        p4 = self.plt_v3offset_time()
        p5 = self.plt_centroid()
        p6 = self.plt_mag_time()
        # make grid
        grid = gridplot([p1, p2, p3, p4, p5, p6], ncols=2, merge_tools=False)
        #show(grid)
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
        the wata monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the wata monitor was run.
        """
        query = session.query(self.query_table).filter(and_(self.query_table.aperture == self.aperture,
                              self.query_table.run_monitor == True)).order_by(self.query_table.end_time_mjd).all()

        dates = np.zeros(0)
        for instance in query:
            dates = np.append(dates, instance.end_time_mjd)

        query_count = len(dates)
        if query_count == 0:
            query_result = 59607.0  # a.k.a. Jan 28, 2022 == First JWST images (MIRI)
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'.format(self.aperture, query_result)))
        else:
            query_result = np.max(dates)

        return query_result


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
        self.query_end = Time.now().mjd
        logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

        # Query MAST using the aperture and the time of the
        # most recent previous search as the starting time
        new_entries = monitor_utils.mast_query_ta(self.instrument, self.aperture, self.query_start, self.query_end)
        wata_entries = len(new_entries)
        logging.info('\tMAST query has returned {} new WATA files for {}, {} to run the WATA monitor.'.format(wata_entries, self.instrument, self.aperture))

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
        self.script, self.div = None, None
        monitor_run = False
        if len(new_filenames) > 0:
            # get the data
            try:
                self.wata_data = self.get_wata_data(new_filenames)
                # make the plots
                self.script, self.div = self.mk_plt_layout()
                monitor_run = True
            except:
                logging.info('\tWATA monitor skipped. No WATA data found.')

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
        self.query_table.__table__.insert().execute(new_entry)
        logging.info('\tUpdated the query history table')

        logging.info('WATA Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = WATA()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)

