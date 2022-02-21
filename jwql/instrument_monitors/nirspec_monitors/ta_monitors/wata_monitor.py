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
from astropy.io import fits
from bokeh.io import output_file
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, Range1d
from bokeh.models.tools import HoverTool
from bokeh.layouts import gridplot
from bokeh.models import Span, Label

# jwql imports
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils import monitor_utils
from jwql.database.database_interface import session
from jwql.database.database_interface import NIRSpecTAQueryHistory, NIRSpecTAStats
from jwql.jwql_monitors import monitor_mast


class WATA():
    """ Class for executint the NIRSpec WATA monitor.
    
    This class will search for new WATA current files in the file systems
    for NIRSpec and will run the monitor on these files. The monitor will
    extract the TA information from the file headers and perform all
    statistical measurements. Results will be saved to the WATA database.
    
    Alternatively, the class can use the dictionaries provided created by
    the NIRSpec Python Implementation of OSS TA (which we call 'the
    replica') and obtain the TA information from there.
    
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
                print('\n WARNING! This file is not WATA: ', fits_file)
                print('  Exiting wata_monitor.py  \n')
                exit()
            hdr = ff[0].header
        return hdr
    
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
        # create the lists to populate
        date_obs, visit_id, filter, readout = [], [], [], []
        ta_status, status_reason, star_name = [], [], []
        star_ra, star_dec, star_mag, star_catalog = [], [], [], []
        planned_v2, planned_v3, stamp_start_col, stamp_start_row = [], [], [], []
        star_detector, max_val_box, max_val_box_col, max_val_box_row = [], [], [], []
        iterations, corr_col, corr_row = [], [], []
        stamp_final_col, stamp_final_row = [], []
        detector_final_col, detector_final_row = [], []
        final_sci_x, final_sci_y = [], []
        measured_v2, measured_v3, ref_v2, ref_v3 = [], [], [],[]
        v2_offset, v3_offset, sam_x, sam_y = [], [], [], []
        for fits_file in new_filenames:
            hdr = self.get_tainfo_from_fits(fits_file)
            date_obs.append(hdr['DATE-OBS'])
            visit_id.append(hdr['OBS_ID'])  # PropID+VisitID+VisitGrpID+SeqID+ActID
            try:
                filter.append(hdr['FILTER'])
            except:
                filter.append(hdr['FWA_POS'])
            readout.append(hdr['READOUT'])
            ta_status.append(hdr['TASTATUS'])
            status_reason.append(hdr['STAT_RSN'])
            star_name.append(hdr['REFSTNAM'])
            star_ra.append(hdr['REFSTRA'])
            star_dec.append(hdr['REFSTDEC'])
            star_mag.append(hdr['REFSTMAG'])
            star_catalog.append(hdr['REFSTCAT'])
            planned_v2.append(hdr['V2_PLAND'])
            planned_v3.append(hdr['V3_PLAND'])
            stamp_start_col.append(hdr['EXTCOLST'])
            stamp_start_row.append(hdr['EXTROWST'])
            star_detector.append(hdr['TA_DTCTR'])
            max_val_box.append(hdr['BOXPKVAL'])
            max_val_box_col.append(hdr['BOXPKCOL'])
            max_val_box_row.append(hdr['BOXPKROW'])
            iterations.append(hdr['CENITERS'])
            corr_col.append(hdr['CORR_COL'])
            corr_row.append(hdr['CORR_ROW'])
            stamp_final_col.append(hdr['IMCENCOL'])
            stamp_final_row.append(hdr['IMCENROW'])
            detector_final_col.append(hdr['DTCENCOL'])
            detector_final_row.append(hdr['DTCENROW'])
            final_sci_x.append(hdr['SCIXCNTR'])
            final_sci_y.append(hdr['SCIYCNTR'])
            measured_v2.append(hdr['TARGETV2'])
            measured_v3.append(hdr['TARGETV3'])
            ref_v2.append(hdr['V2_REF'])
            ref_v3.append(hdr['V3_REF'])
            v2_offset.append(hdr['V2_OFFST'])
            v3_offset.append(hdr['V3_OFFST'])
            sam_x.append(hdr['SAM_X'])
            sam_y.append(hdr['SAM_Y'])
        # create the pandas dataframe
        wata_df = pd.DataFrame({'date_obs': date_obs, 'visit_id': visit_id,
                                'filter': filter, 'readout': readout, 'ta_status': ta_status,
                                'status_reason': status_reason, 'star_name': star_name,
                                'star_ra': star_ra, 'star_dec': star_dec,
                                'star_mag': star_mag, 'star_catalog': star_catalog,
                                'planned_v2': planned_v2, 'planned_v3': planned_v3,
                                'stamp_start_col': stamp_start_col, 'stamp_start_row': stamp_start_row,
                                'star_detector': star_detector, 'max_val_box': max_val_box,
                                'max_val_box_col': max_val_box_col, 'max_val_box_row': max_val_box_row,
                                'iterations': iterations, 'corr_col': corr_col, 'corr_row': corr_row,
                                'stamp_final_col': stamp_final_col, 'stamp_final_row': stamp_final_row,
                                'detector_final_col': detector_final_col, 'detector_final_row': detector_final_row,
                                'final_sci_x': final_sci_x, 'final_sci_y': final_sci_y,
                                'measured_v2': measured_v2, 'measured_v3': measured_v3,
                                'ref_v2': ref_v2, 'ref_v3': ref_v3,
                                'v2_offset': v2_offset, 'v3_offset': v3_offset,
                                'sam_x': sam_x, 'sam_y': sam_y
                               })
        wata_df.index = wata_df.index + 1
        return wata_df
            

    def plt_status(self, source):
        """ Plot the WATA status (passed = 0 or failed = 1).
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        ta_status, date_obs = source.data['ta_status'], source.data['date_obs']
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
        source.data["time_arr"] = time_arr
        source.data["ta_status_bool"] = bool_status
        source.data["status_colors"] = status_colors
        # create a new bokeh plot
        p = figure(title="WATA Status [Succes=1, Fail=0]", x_axis_label='Time',
                   y_axis_label='WATA Status', x_axis_type='datetime',)
        limits = [-0.5, 1.5]
        p.circle(x='time_arr', y='ta_status_bool', source=source,
                 color='status_colors', size=7, fill_alpha=0.5)
        #output_file("wata_status.html")
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('TA status', '@ta_status'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Magnitude', '@star_mag')
        ]
        p.add_tools(hover)
        return p


    def plt_residual_offsets(self, source):
        """ Plot the residual V2 and V3 offsets
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="WATA Residual V2-V3 Offsets", x_axis_label='Residual V2 Offset',
                   y_axis_label='Residual V3 Offset')
        p.circle(x='v2_offset', y='v3_offset', source=source,
                 color="purple", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('TA status', '@ta_status'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Magnitude', '@star_mag')
        ]
        p.add_tools(hover)
        return p


    def plt_v2offset_time(self, source):
        """ Plot the residual V2 versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="WATA V2 Offset vs Time", x_axis_label='Time',
                   y_axis_label='Residual V2 Offset', x_axis_type='datetime')
        p.circle(x='time_arr', y='v2_offset', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('TA status', '@ta_status'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Magnitude', '@star_mag')
        ]
        p.add_tools(hover)
        return p


    def plt_v3offset_time(self, source):
        """ Plot the residual V3 versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="WATA V3 Offset vs Time", x_axis_label='Time',
                   y_axis_label='Residual V3 Offset', x_axis_type='datetime')
        p.circle(x='time_arr', y='v2_offset', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('TA status', '@ta_status'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Magnitude', '@star_mag')
        ]
        p.add_tools(hover)
        return p


    def plt_mag_time(self, source):
        """ Plot the star magnitude versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # calculate the pseudo magnitudes
        max_val_box, time_arr = source.data['max_val_box'], source.data['time_arr']
        pseudo_mag = []
        for peak in max_val_box:
            m = -2.5 * np.log(peak)
            pseudo_mag.append(m)
        # add to the bokeh data structure
        source.data["pseudo_mag"] = pseudo_mag
        # create a new bokeh plot
        p = figure(title="WATA Star Pseudo Magnitude vs Time", x_axis_label='Time',
                   y_axis_label='Star  -2.5*log(box_peak)', x_axis_type='datetime')
        p.circle(x='time_arr', y='pseudo_mag', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        p.y_range.flipped = True
        # add count saturation warning lines
        loc1 = -2.5 * np.log(45000.0)
        loc2 = -2.5 * np.log(50000.0)
        loc3 = -2.5 * np.log(60000.0)
        hline1 = Span(location=loc1, dimension='width', line_color='green', line_width=3)
        hline2 = Span(location=loc2, dimension='width', line_color='yellow', line_width=3)
        hline3 = Span(location=loc3, dimension='width', line_color='red', line_width=3)
        p.renderers.extend([hline1, hline2, hline3])
        label1 = Label(x=time_arr[-1], y=loc1, y_units='data', text='45000 counts')
        label2 = Label(x=time_arr[-1], y=loc2, y_units='data', text='50000 counts')
        label3 = Label(x=time_arr[-1], y=loc3, y_units='data', text='60000 counts')
        p.add_layout(label1)
        p.add_layout(label2)
        p.add_layout(label3)
        # add hover
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('TA status', '@ta_status'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Box peak', '@max_val_box'),
            ('Pseudo mag', '@pseudo_mag')
        ]
        p.add_tools(hover)
        return p


    def plt_centroid(self, source):
        """ Plot the WATA centroid
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="WATA Centroid", x_axis_label='Column',
                   y_axis_label='Row')
        limits = [10, 25]
        p.x_range = Range1d(limits[0], limits[1])
        p.y_range = Range1d(limits[0], limits[1])
        p.circle(x='corr_col', y='corr_row', source=source,
                   color="purple", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('TA status', '@ta_status'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Magnitude', '@star_mag'),
            ('Box Centr Col', '@corr_col'),
            ('Box Centr Row', '@corr_row'),
            ('Det Centr Col', '@detector_final_col'),
            ('Det Centr Row', '@detector_final_row')
        ]
        p.add_tools(hover)
        return p


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
        query = session.query(self.query_table).filter(self.query_table.aperture == self.aperture,
                                                       self.query_table.readpattern == self.readpatt). \
                              filter(self.query_table.run_monitor == True)

        dates = np.zeros(0)
        for instance in query:
            dates = np.append(dates, instance.end_time_mjd)

        query_count = len(dates)
        if query_count == 0:
            query_result = 59607.0  # a.k.a. Jan 28, 2022 == First JWST images (MIRI)
            logging.info(('\tNo query history for {} with {}. Beginning search date will be set to {}.'
                         .format(self.aperture, self.readpatt, query_result)))
        else:
            query_result = np.max(dates)

        return query_result


    def mk_plt_layout(self):
        """Create the bokeh plot layout"""
        source = self.wata_data
        source = ColumnDataSource(data=source)
        output_file("wata_layout.html")
        p1 = self.plt_status(source)
        p2 = self.plt_residual_offsets(source)
        p3 = self.plt_v2offset_time(source)
        p4 = self.plt_v3offset_time(source)
        p5 = self.plt_centroid(source)
        p6 = self.plt_mag_time(source)
        # make grid
        grid = gridplot([p1, p2, p3, p4, p5, p6], ncols=2, merge_tools=False)
        #show(grid)
        save(p)


    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for further details."""
        
        logging.info('Begin logging for wata_monitor')
        
        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()['outputs'], 'wata_monitor')
        ensure_dir_exists(os.path.join(self.output_dir, 'data'))

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd
        
        # define WATA variables
        self.instrument = "nirspec"
        self.aperture = "NRS_S1600A1_SLIT"
        
        # Locate the record of the most recent MAST search
        self.query_start = self.most_recent_search()
        logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

        # Query MAST using the aperture and the time of the
        # most recent previous search as the starting time
        new_entries = monitor_utils.mast_query_ta(instrument, aperture, self.query_start, self.query_end, readpatt=self.readpatt)
        wata_entries = len(new_entries)
        logging.info('\tMAST query has returned {} new WATA files for {}, {}, {} to run the dark monitor.'.format(wata_entries, self.instrument, self.aperture, self.readpatt))
        
        # Get full paths to the files
        new_filenames = []
        for file_entry in new_entries:
            try:
                new_filenames.append(filesystem_path(file_entry['filename']))
            except FileNotFoundError:
                logging.warning('\t\tUnable to locate {} in filesystem. Not including in processing.'.format(file_entry['filename']))
        self.wata_data = self.get_wata_data(new_filenames)
    
        # make the plots
        self.mk_plt_layout()
        
        # Update the query history
        new_entry = {'instrument': self.instrument,
                    'aperture': self.aperture,
                    'readpattern': self.readpatt,
                    'start_time_mjd': self.query_start,
                    'end_time_mjd': self.query_end,
                    'files_found': len(new_entries),
                    'run_monitor': monitor_run,
                    'entry_date': datetime.datetime.now()}
        self.query_table.__table__.insert().execute(new_entry)
        logging.info('\tUpdated the query history table')

        logging.info('WATA Monitor completed successfully.')

                
if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = WATA()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)

