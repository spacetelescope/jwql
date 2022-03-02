#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# HISTORY
#    Feb 2022 - Vr. 1.0: Completed initial version


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
    python nrs_ta_monitors.py
    
"""


# general imports
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from astropy.io import fits
from random import randint
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


class MSATA():
    """ Class for executint the NIRSpec WATA monitor.
    
    This class will search for new WATA current files in the file systems
    for NIRSpec and will run the monitor on these files. The monitor will
    extract the TA information from the file headers and perform all
    statistical measurements. Results will be saved to the MSATA database.
    
    Alternatively, the class can use the dictionaries provided created by
    the NIRSpec Python Implementation of OSS TA (which we call 'the
    replica') and obtain the TA information from there.
    
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
                print('\n WARNING! This file is not MSATA: ', fits_file)
                print('  Exiting msata_monitor.py  \n')
                exit()
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
        # from the main header
        detector, date_obs, visit_id, filter, readout, subarray = [], [], [], [], [], []
        # from the TA header
        num_refstars, ta_status, status_rsn = [], [], []
        v2halffacet, v3halffacet, v2msactr, v3msactr = [], [], [], []
        lsv2offset, lsv3offset, lsoffsetmag, lsrolloffset = [], [], [], []
        lsv2sigma, lsv3sigma, lsiterations, lsfintargs = [], [], [], []
        guidestarid, guidestarx, guidestary, guidestarroll = [], [], [], []
        samx, samy, samroll = [], [], []
        # from the TA fits table
        reference_star_mag, convergence_status, reference_star_number = [], [], []
        lsf_removed_status, lsf_removed_reason = [], []
        lsf_removed_x, lsf_removed_y = [], []
        found_v2, found_v3, box_peak_value = [], [], []
        for fits_file in new_filenames:
            msata_info = self.get_tainfo_from_fits(fits_file)
            main_hdr, ta_hdr, ta_table = msata_info
            date_obs.append(main_hdr['DATE-OBS'])
            visit_id.append(main_hdr['OBS_ID'])  # PropID+VisitID+VisitGrpID+SeqID+ActID
            try:
                filter.append(main_hdr['FILTER'])
            except:
                filter.append(main_hdr['FWA_POS'])
            detector.append(main_hdr['DETECTOR'])
            readout.append(main_hdr['READOUT'])
            subarray.append(main_hdr['SUBARRAY'])
            num_refstars.append(ta_hdr['NUMREFST'])
            ta_status.append(ta_hdr['TASTATUS'])
            status_rsn.append(ta_hdr['STAT_RSN'])
            v2halffacet.append(ta_hdr['V2HFOFFS'])
            v3halffacet.append(ta_hdr['V3HFOFFS'])
            v2msactr.append(ta_hdr['V2MSACTR'])
            v3msactr.append(ta_hdr['V3MSACTR'])
            lsv2offset.append(ta_hdr['FITXOFFS'])
            lsv3offset.append(ta_hdr['FITYOFFS'])
            lsoffsetmag.append(ta_hdr['OFFSTMAG'])
            lsrolloffset.append(ta_hdr['FITROFFS'])
            lsv2sigma.append(ta_hdr['FITXSIGM'])
            lsv3sigma.append(ta_hdr['FITYSIGM'])
            lsiterations.append(ta_hdr['ITERATNS'])
            guidestarid.append(ta_hdr['GUIDERID'])
            guidestarx.append(ta_hdr['IDEAL_X'])
            guidestary.append(ta_hdr['IDEAL_Y'])
            guidestarroll.append(ta_hdr['IDL_ROLL'])
            samx.append(ta_hdr['SAM_X'])
            samy.append(ta_hdr['SAM_Y'])
            samroll.append(ta_hdr['SAM_ROLL'])
            # now from the TA table
            box_peak_value.append(ta_table['box_peak_value'])
            reference_star_mag.append(ta_table['reference_star_mag'])
            convergence_status.append(ta_table['convergence_status'])
            reference_star_number.append(ta_table['reference_star_number'])
            lsf_removed_status.append(ta_table['lsf_removed_status'])
            lsf_removed_reason.append(ta_table['lsf_removed_reason'])
            lsf_removed_x.append(ta_table['lsf_removed_x'])
            lsf_removed_y.append(ta_table['lsf_removed_y'])
            found_v2.append(ta_table['found_v2'])
            found_v3.append(ta_table['found_v3'])
        # create the pandas dataframe
        msata_df = pd.DataFrame({'date_obs': date_obs, 'visit_id': visit_id,
                                 'filter': filter, 'readout': readout,
                                 'detector': detector, 'subarray': subarray,
                                 'ta_status': ta_status, 'status_rsn': status_rsn,
                                 'v2halffacet': v2halffacet, 'v3halffacet': v3halffacet,
                                 'v2msactr': v2msactr, 'v3msactr': v3msactr,
                                 'lsv2offset': lsv2offset, 'lsv3offset': lsv3offset,
                                 'lsoffsetmag': lsoffsetmag, 'lsrolloffset': lsrolloffset,
                                 'lsv2sigma': lsv2sigma, 'lsv3sigma': lsv3sigma,
                                 'lsiterations': lsiterations, 'guidestarid': guidestarid,
                                 'guidestarx': guidestarx, 'guidestary': guidestary,
                                 'guidestarroll': guidestarroll,
                                 'samx': samx, 'samy': samy, 'samroll': samroll,
                                 'box_peak_value': box_peak_value,
                                 'reference_star_mag': reference_star_mag,
                                 'convergence_status': convergence_status,
                                 'reference_star_number': reference_star_number,
                                 'lsf_removed_status': lsf_removed_status,
                                 'lsf_removed_reason': lsf_removed_reason,
                                 'lsf_removed_x': lsf_removed_x,
                                 'lsf_removed_y': lsf_removed_y,
                                 'found_v2': found_v2,
                                 'found_v3': found_v3
                                })
        msata_df.index = msata_df.index + 1
        return msata_df


    def plt_slewsize_vs_time(self, data):
        """ Plot the slew size versus time
        Parameters
        ----------
        data: pandas data frame
            This is the data frame that contains all MSATA.

        Returns
        -------
        p: bokeh plot object
        """
        # to get the times we need the fits files
        pass


    def plt_status(self, source):
        """ Plot the MSATA status versus time.
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
        p = figure(title="MSATA Status [Succes=1, Fail=0]", x_axis_label='Time',
                   y_axis_label='MSATA Status', x_axis_type='datetime',)
        limits = [-0.5, 1.5]
        p.circle(x='time_arr', y='ta_status_bool', source=source,
                 color='status_colors', size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('TA status', '@ta_status'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray')
        ]
        p.add_tools(hover)
        return p


    def plt_residual_offsets(self, source):
        """ Plot the residual Least Squares V2 and V3 offsets
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="MSATA Least Squares Residual V2-V3 Offsets",
                   x_axis_label='Least Squares Residual V2 Offset',
                   y_axis_label='Least Squares Residual V3 Offset')
        p.circle(x='lsv2offset', y='lsv3offset', source=source,
                 color="purple", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V3 offset', '@lsv3offset')
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
        p = figure(title="MSATA Least Squares V2 Offset vs Time", x_axis_label='Time',
                   y_axis_label='Least Squares Residual V2 Offset', x_axis_type='datetime')
        p.circle(x='time_arr', y='lsv2offset', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V3 offset', '@lsv3offset')
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
        p = figure(title="MSATA Least Squares V3 Offset vs Time", x_axis_label='Time',
                   y_axis_label='Least Squares Residual V3 Offset', x_axis_type='datetime')
        p.circle(x='time_arr', y='lsv3offset', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V3 offset', '@lsv3offset')
        ]
        p.add_tools(hover)
        return p


    def plt_lsv2v3offsetsigma(self, source):
        """ Plot the residual Least Squares V2 and V3 sigma offsets
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="MSATA Least Squares Residual V2-V3 Sigma Offsets",
                   x_axis_label='Least Squares Residual V2 Sigma Offset',
                   y_axis_label='Least Squares Residual V3 Sigma Offset')
        p.circle(x='lsv2sigma', y='lsv3sigma', source=source,
                 color="purple", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V2 sigma', '@lsv2sigma'),
            ('LS V3 offset', '@lsv3offset'),
            ('LS V3 sigma', '@lsv3sigma')
        ]
        p.add_tools(hover)
        return p


    def plt_res_offsets_corrected(self, source):
        """ Plot the residual Least Squares V2 and V3 offsets corrected by the half-facet
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        lsv2offset, lsv3offset = source.data['lsv2offset'], source.data['lsv3offset']
        v2halffacet, v3halffacet = source.data['v2halffacet'], source.data['v3halffacet']
        v2_half_fac_corr = lsv2offset + v2halffacet
        v3_half_fac_corr = lsv3offset + v3halffacet
        # add these to the bokeh data structure
        source.data["v2_half_fac_corr"] = v2_half_fac_corr
        source.data["v3_half_fac_corr"] = v3_half_fac_corr
        p = figure(title="MSATA Least Squares Residual V2-V3 Offsets Half-facet corrected",
                   x_axis_label='Least Squares Residual V2 Offset + half-facet',
                   y_axis_label='Least Squares Residual V3 Offset + half-facet')
        p.circle(x='v2_half_fac_corr', y='v3_half_fac_corr', source=source,
                 color="purple", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V3 offset', '@lsv3offset'),
            ('V2 half-facet', '@v2halffacet'),
            ('V3 half-facet', '@v3halffacet')
        ]
        p.add_tools(hover)
        return p


    def plt_v2offsigma_time(self, source):
        """ Plot the residual Least Squares V2 sigma Offset versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="MSATA Least Squares V2 Sigma Offset vs Time", x_axis_label='Time',
                   y_axis_label='Least Squares Residual V2 Sigma Offset', x_axis_type='datetime')
        p.circle(x='time_arr', y='lsv2sigma', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V2 sigma', '@lsv2sigma')
        ]
        p.add_tools(hover)
        return p


    def plt_v3offsigma_time(self, source):
        """ Plot the residual Least Squares V3 Offset versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="MSATA Least Squares V3 Sigma Offset vs Time", x_axis_label='Time',
                   y_axis_label='Least Squares Residual V3 Sigma Offset', x_axis_type='datetime')
        p.circle(x='time_arr', y='lsv3sigma', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS V3 offset', '@lsv3offset'),
            ('LS V3 sigma', '@lsv3sigma')
        ]
        p.add_tools(hover)
        return p


    def plt_roll_offset(self, source):
        """ Plot the residual Least Squares roll Offset versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="MSATA Least Squares Roll Offset vs Time", x_axis_label='Time',
                   y_axis_label='Least Squares Residual Roll Offset', x_axis_type='datetime')
        p.circle(x='time_arr', y='lsrolloffset', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V3 offset', '@lsv3offset')
        ]
        p.add_tools(hover)
        return p


    def plt_lsoffsetmag(self, source):
        """ Plot the residual Least Squares Total Slew Magnitude Offset versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        p = figure(title="MSATA Least Squares Total Magnitude of the Linear V2, V3 Offset Slew vs Time", x_axis_label='Time',
                   y_axis_label='sqrt((V2_off)**2 + (V3_off)**2)', x_axis_type='datetime')
        p.circle(x='time_arr', y='lsoffsetmag', source=source,
                 color="blue", size=7, fill_alpha=0.5)
        hover = HoverTool()
        hover.tooltips=[
            ('Visit ID', '@visit_id'),
            ('Filter', '@filter'),
            ('Readout', '@readout'),
            ('Date-Obs', '@date_obs'),
            ('Subarray', '@subarray'),
            ('LS roll offset', '@lsrolloffset'),
            ('LS slew mag offset', '@lsoffsetmag'),
            ('LS V2 offset', '@lsv2offset'),
            ('LS V3 offset', '@lsv3offset')
        ]
        p.add_tools(hover)
        return p


    def plt_mags_time(self, source):
        """ Plot the star magnitudes versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            p: bokeh plot object
        """
        visit_id = source.data['visit_id']
        lsf_removed_status = source.data['lsf_removed_status']
        lsf_removed_reason = source.data['lsf_removed_reason']
        lsf_removed_x = source.data['lsf_removed_x']
        lsf_removed_y = source.data['lsf_removed_y']
        found_v2 = source.data['found_v2']
        found_v3 = source.data['found_v3']
        reference_star_number = source.data['reference_star_number']
        visits_stars_mags = source.data['reference_star_mag']
        box_peak_value = source.data['box_peak_value']
        date_obs, time_arr = source.data['date_obs'], source.data['time_arr']
        # create the list of color per visit
        colors_list = []
        # create the structure matching the number of visits and reference stars
        vid, dobs, tarr, star_no, status = [], [], [], [], []
        peaks, visit_mags, stars_v2, stars_v3 = [], [], [], []
        for i, _ in enumerate(visit_id):
            mags, v, d, t, c, s, x, y  = [], [], [], [], [], [], [], []
            ci = '#%06X' % randint(0, 0xFFFFFF)
            for j in range(len(reference_star_number[i])):
                # calculate the pseudo magnitude
                m = -2.5 * np.log(box_peak_value[i][j])
                mags.append(m)
                v.append(visit_id[i])
                d.append(date_obs[i])
                t.append(time_arr[i])
                c.append(ci)
                if 'not_removed' in lsf_removed_status[i][j]:
                    s.append('SUCCESS')
                    x.append(found_v2[i][j])
                    y.append(found_v3[i][j])
                else:
                    s.append(lsf_removed_reason[i][j])
                    x.append(lsf_removed_x[i][j])
                    y.append(lsf_removed_y[i][j])
            vid.extend(v)
            dobs.extend(d)
            tarr.extend(t)
            star_no.extend(reference_star_number[i])
            status.extend(s)
            visit_mags.extend(mags)
            colors_list.extend(c)
            stars_v2.extend(x)
            stars_v3.extend(y)
            peaks.extend(box_peak_value[i])
        # now create the mini ColumnDataSource for this particular plot
        mini_source={'vid': vid, 'star_no': star_no, 'status': status,
                     'dobs': dobs, 'tarr': tarr, 'visit_mags': visit_mags,
                     'peaks': peaks, 'colors_list': colors_list,
                     'stars_v2': stars_v2, 'stars_v3': stars_v2
                    }
        mini_source = ColumnDataSource(data=mini_source)
        # create a the bokeh plot
        p = figure(title="MSATA Star Pseudo Magnitudes vs Time", x_axis_label='Time',
                   y_axis_label='Star  -2.5*log(box_peak)', x_axis_type='datetime')
        p.circle(x='tarr', y='visit_mags', source=mini_source,
                 color='colors_list', size=7, fill_alpha=0.5)
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
        hover.tooltips=[('Visit ID', '@vid'),
                        ('Star No.', '@star_no'),
                        ('LS Status', '@status'),
                        ('Date-Obs', '@dobs'),
                        ('Box peak', '@peaks'),
                        ('Pseudo mag', '@visit_mags'),
                        ('Measured V2', '@stars_v2'),
                        ('Measured V3', '@stars_v3')
                        ]
        p.add_tools(hover)
        return p
        
        
    def mk_plt_layout(self):
        """Create the bokeh plot layout"""
        source = self.msata_data
        source = ColumnDataSource(data=source)
        output_file("msata_layout.html")
        p1 = self.plt_status(source)
        p2 = self.plt_residual_offsets(source)
        p3 = self.plt_res_offsets_corrected(source)
        p4 = self.plt_v2offset_time(source)
        p5 = self.plt_v3offset_time(source)
        p6 = self.plt_lsv2v3offsetsigma(source)
        p7 = self.plt_v2offsigma_time(source)
        p8 = self.plt_v3offsigma_time(source)
        p9 = self.plt_roll_offset(source)
        p10 = self.plt_lsoffsetmag(source)
        p11 = self.plt_mags_time(source)
        # make grid
        grid = gridplot([p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11],
                        ncols=2, merge_tools=False)
        #show(grid)
        save(p)


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


    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for further details."""
        
        logging.info('Begin logging for wata_monitor')
        
        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()['outputs'], 'msata_monitor')
        ensure_dir_exists(os.path.join(self.output_dir, 'data'))

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd
        
        # define MSATA variables
        self.instrument = "nirspec"
        self.aperture = "NRS_FULL_MSA"
        
        # Locate the record of the most recent MAST search
        self.query_start = self.most_recent_search()
        logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

        # Query MAST using the aperture and the time of the
        # most recent previous search as the starting time
        new_entries = monitor_utils.mast_query_ta(instrument, aperture, self.query_start, self.query_end, readpatt=self.readpatt)
        msata_entries = len(new_entries)
        logging.info('\tMAST query has returned {} new WATA files for {}, {}, {} to run the dark monitor.'.format(msata_entries, self.instrument, self.aperture, self.readpatt))
        
        # Get full paths to the files
        new_filenames = []
        for file_entry in new_entries:
            try:
                new_filenames.append(filesystem_path(file_entry['filename']))
            except FileNotFoundError:
                logging.warning('\t\tUnable to locate {} in filesystem. Not including in processing.'.format(file_entry['filename']))
        
        # get the data
        self.msata_data = self.get_msata_data(new_filenames)
    
        # make the plots
        self.mk_plt_layout()

        # Update the query history
        new_entry = {'instrument': 'nirspec',
                    'aperture': aperture,
                    'readpattern': self.readpatt,
                    'start_time_mjd': self.query_start,
                    'end_time_mjd': self.query_end,
                    'files_found': len(new_entries),
                    'run_monitor': monitor_run,
                    'entry_date': datetime.datetime.now()}
        self.query_table.__table__.insert().execute(new_entry)
        logging.info('\tUpdated the query history table')

        logging.info('MSATA Monitor completed successfully.')

                
if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = MSATA()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
