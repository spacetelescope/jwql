#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# HISTORY
#    Feb 2022 - Vr. 1.0: Completed initial version
#    Sep 2022 - Vr. 1.1: Modified ColumnDataSource so that data could be recovered
#                        from an html file of a previous run of the monitor and
#                        included the code to read and format the data from the html file
#    Apr 2024 - Vr. 1.2: Removed html webscraping and now store data in django models

"""
This module contains the code for the NIRSpec Wide Aperture Target
Acquisition (WATA) monitor, which monitors the TA offsets.

This monitor displays the comparison of desired versus measured TA.

This monitor also displays V2, V3 offsets over time.

Author
______
    - Maria Pena-Guerrero
    - Melanie Clarke
    - Mees Fix

Use
---
    This module can be used from the command line as follows:
    python wata_monitor.py

"""

# general imports
import os
import logging
from datetime import datetime, timezone, timedelta
from dateutil import parser

import numpy as np
import pandas as pd
from astropy.time import Time
from astropy.io import fits
from bokeh.embed import components
from bokeh.io import output_file
from bokeh.layouts import gridplot, layout
from bokeh.models import (
    ColumnDataSource,
    Range1d,
    CustomJS,
    CustomJSFilter,
    CDSView,
    Span,
    Label,
    DateRangeSlider,
)
from bokeh.models.tools import HoverTool, BoxSelectTool
from bokeh.plotting import figure, save

# jwql imports
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils import monitor_utils
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import (
    ensure_dir_exists,
    filesystem_path,
    get_config,
)


if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # Need to set up django apps before we can access the models
    import django  # noqa: E402 (module level import not at top of file)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()

    from jwql.website.apps.jwql.monitor_models.ta import (
        NIRSpecWataStats,
        NIRSpecTaQueryHistory,
    )  # noqa: E402 (module level import not at top of file)


class WATA:
    """Class for executing the NIRSpec WATA monitor.

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
        """Initialize an instance of the WATA class"""
        # define WATA variables
        self.instrument = "nirspec"
        self.aperture = "NRS_S1600A1_SLIT"

        # Very beginning of intake of images: Jan 28, 2022 == First JWST images (MIRI)
        self.query_very_beginning = 59607.0

        # structure to define required keywords to extract and where they live
        self.keywds2extract = {
            "FILENAME": {
                "loc": "main_hdr",
                "alt_key": None,
                "name": "filename",
                "type": str,
            },
            "DATE-BEG": {"loc": "main_hdr", "alt_key": None, "name": "date_obs"},
            "OBS_ID": {"loc": "main_hdr", "alt_key": "OBSID", "name": "visit_id"},
            "FILTER": {"loc": "main_hdr", "alt_key": "FWA_POS", "name": "tafilter"},
            "READOUT": {"loc": "main_hdr", "alt_key": "READPATT", "name": "readout"},
            "TASTATUS": {"loc": "ta_hdr", "alt_key": None, "name": "ta_status"},
            "STAT_RSN": {"loc": "ta_hdr", "alt_key": None, "name": "status_reason"},
            "REFSTNAM": {"loc": "ta_hdr", "alt_key": None, "name": "star_name"},
            "REFSTRA": {"loc": "ta_hdr", "alt_key": None, "name": "star_ra"},
            "REFSTDEC": {"loc": "ta_hdr", "alt_key": None, "name": "star_dec"},
            "REFSTMAG": {"loc": "ta_hdr", "alt_key": None, "name": "star_mag"},
            "REFSTCAT": {"loc": "ta_hdr", "alt_key": None, "name": "star_catalog"},
            "V2_PLAND": {"loc": "ta_hdr", "alt_key": None, "name": "planned_v2"},
            "V3_PLAND": {"loc": "ta_hdr", "alt_key": None, "name": "planned_v3"},
            "EXTCOLST": {"loc": "ta_hdr", "alt_key": None, "name": "stamp_start_col"},
            "EXTROWST": {"loc": "ta_hdr", "alt_key": None, "name": "stamp_start_row"},
            "TA_DTCTR": {"loc": "ta_hdr", "alt_key": None, "name": "star_detector"},
            "BOXPKVAL": {"loc": "ta_hdr", "alt_key": None, "name": "max_val_box"},
            "BOXPKCOL": {"loc": "ta_hdr", "alt_key": None, "name": "max_val_box_col"},
            "BOXPKROW": {"loc": "ta_hdr", "alt_key": None, "name": "max_val_box_row"},
            "TA_ITERS": {"loc": "ta_hdr", "alt_key": "CENITERS", "name": "iterations"},
            "CORR_COL": {"loc": "ta_hdr", "alt_key": None, "name": "corr_col"},
            "CORR_ROW": {"loc": "ta_hdr", "alt_key": None, "name": "corr_row"},
            "IMCENCOL": {"loc": "ta_hdr", "alt_key": None, "name": "stamp_final_col"},
            "IMCENROW": {"loc": "ta_hdr", "alt_key": None, "name": "stamp_final_row"},
            "DTCENCOL": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "detector_final_col",
            },
            "DTCENROW": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "detector_final_row",
            },
            "SCIXCNTR": {"loc": "ta_hdr", "alt_key": None, "name": "final_sci_x"},
            "SCIYCNTR": {"loc": "ta_hdr", "alt_key": None, "name": "final_sci_y"},
            "TARGETV2": {"loc": "ta_hdr", "alt_key": None, "name": "measured_v2"},
            "TARGETV3": {"loc": "ta_hdr", "alt_key": None, "name": "measured_v3"},
            "V2_REF": {"loc": "ta_hdr", "alt_key": None, "name": "ref_v2"},
            "V3_REF": {"loc": "ta_hdr", "alt_key": None, "name": "ref_v3"},
            "V2_RESID": {"loc": "ta_hdr", "alt_key": "V2_OFFST", "name": "v2_offset"},
            "V3_RESID": {"loc": "ta_hdr", "alt_key": "V3_OFFST", "name": "v3_offset"},
            "SAM_X": {"loc": "ta_hdr", "alt_key": None, "name": "sam_x"},
            "SAM_Y": {"loc": "ta_hdr", "alt_key": None, "name": "sam_y"},
        }

        # initialize attributes to be set later
        self.source = None
        self.share_tools = []
        self.date_range = None
        self.date_view = None

    def get_tainfo_from_fits(self, fits_file):
        """Get the TA information from the fits file
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
                if "TARG_ACQ" in hdu.name:
                    wata = True
                    break
            if not wata:
                return None
            main_hdr = ff[0].header
            try:
                ta_hdr = ff["TARG_ACQ"].header
            except KeyError:
                no_ta_ext_msg = "No TARG_ACQ extension in file " + fits_file
                return no_ta_ext_msg
        wata_info = [main_hdr, ta_hdr]
        return wata_info

    def get_wata_data(self, new_filenames):
        """Create the data array for the WATA input files
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
                key_name = key_dict["name"]
                if key_name not in wata_dict:
                    wata_dict[key_name] = []
                ext = main_hdr
                if key_dict["loc"] == "ta_hdr":
                    ext = ta_hdr
                try:
                    val = ext[key]
                    if key == "filename":
                        val = fits_file
                except KeyError:
                    val = ext[key_dict["alt_key"]]
                wata_dict[key_name].append(val)
        # create the pandas dataframe
        wata_df = pd.DataFrame(wata_dict)
        return wata_df, no_ta_ext_msgs

    def add_time_column(self):
        """Add time column to data source, to be used by all plots."""
        date_obs = self.source.data["date_obs"].astype(str)
        time_arr = [self.add_timezone(do_str) for do_str in date_obs]
        self.source.data["time_arr"] = time_arr

    def plt_status(self):
        """Plot the WATA status (passed = 0 or failed = 1).
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        ta_status = self.source.data["ta_status"]

        # check if this column exists in the data already, else create it
        if "bool_status" not in self.source.data:
            # bokeh does not like to plot strings, turn into binary type
            bool_status, status_colors = [], []
            for tas in ta_status:
                if "unsuccessful" not in tas.lower():
                    bool_status.append(1)
                    status_colors.append("blue")
                else:
                    bool_status.append(0)
                    status_colors.append("red")

            # add these to the bokeh data structure
            self.source.data["ta_status_bool"] = bool_status
            self.source.data["status_colors"] = status_colors

        # create a new bokeh plot
        plot = figure(
            title="WATA Status [Success=1, Fail=0]",
            x_axis_label="Time",
            y_axis_label="WATA Status",
            x_axis_type="datetime",
        )
        plot.y_range = Range1d(-0.5, 1.5)
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="ta_status_bool",
            source=self.source,
            color="status_colors",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )

        # make tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("TA status", "@ta_status"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Magnitude", "@star_mag"),
            ("--------", "----------------"),
        ]

        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_residual_offsets(self):
        """Plot the residual V2 and V3 offsets
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="WATA Residual V2-V3 Offsets",
            x_axis_label="Residual V2 Offset",
            y_axis_label="Residual V3 Offset",
        )
        plot.scatter(
            marker="circle",
            x="v2_offset",
            y="v3_offset",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.x_range = Range1d(-0.5, 0.5)
        plot.y_range = Range1d(-0.5, 0.5)

        # mark origin lines
        vline = Span(location=0, dimension="height", line_color="black", line_width=0.7)
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        plot.renderers.extend([vline, hline])

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("TA status", "@ta_status"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Magnitude", "@star_mag"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_v2offset_time(self):
        """Plot the residual V2 versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="WATA V2 Offset vs Time",
            x_axis_label="Time",
            y_axis_label="Residual V2 Offset",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="v2_offset",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(-0.5, 0.5)

        # mark origin line
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        plot.renderers.extend([hline])

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("TA status", "@ta_status"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Magnitude", "@star_mag"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_v3offset_time(self):
        """Plot the residual V3 versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="WATA V3 Offset vs Time",
            x_axis_label="Time",
            y_axis_label="Residual V3 Offset",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="triangle",
            x="time_arr",
            y="v3_offset",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(-0.5, 0.5)

        # mark origin line
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        plot.renderers.extend([hline])

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("TA status", "@ta_status"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Magnitude", "@star_mag"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_mag_time(self):
        """Plot the star magnitude versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # calculate the pseudo magnitudes
        max_val_box, time_arr = (
            self.source.data["max_val_box"],
            self.source.data["time_arr"],
        )

        # check if this column exists in the data already, else create it
        if "nrsrapid_f140x" not in self.source.data:
            # create the arrays per filter and readout pattern
            nrsrapid_f140x, nrsrapid_f110w, nrsrapid_clear = [], [], []
            nrsrapidd6_f140x, nrsrapidd6_f110w, nrsrapidd6_clear = [], [], []
            filter_used, readout = (
                self.source.data["tafilter"],
                self.source.data["readout"],
            )
            for i, val in enumerate(max_val_box):
                if "140" in filter_used[i]:
                    if readout[i].lower() == "nrsrapid":
                        nrsrapid_f140x.append(val)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                    elif readout[i].lower() == "nrsrapidd6":
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(val)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                elif "110" in filter_used[i]:
                    if readout[i].lower() == "nrsrapid":
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(val)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                    elif readout[i].lower() == "nrsrapidd6":
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(np.NaN)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(val)
                        nrsrapidd6_clear.append(np.NaN)
                else:
                    if readout[i].lower() == "nrsrapid":
                        nrsrapid_f140x.append(np.NaN)
                        nrsrapid_f110w.append(np.NaN)
                        nrsrapid_clear.append(val)
                        nrsrapidd6_f140x.append(np.NaN)
                        nrsrapidd6_f110w.append(np.NaN)
                        nrsrapidd6_clear.append(np.NaN)
                    elif readout[i].lower() == "nrsrapidd6":
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
        plot = figure(
            title="WATA Counts vs Time",
            x_axis_label="Time",
            y_axis_label="box_peak [Counts]",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="nrsrapid_f140x",
            source=self.source,
            color="purple",
            size=7,
            fill_alpha=0.4,
            view=self.date_view,
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="nrsrapidd6_f140x",
            source=self.source,
            color="purple",
            size=12,
            fill_alpha=0.4,
            view=self.date_view,
        )
        plot.scatter(
            marker="triangle",
            x="time_arr",
            y="nrsrapid_f110w",
            source=self.source,
            color="orange",
            size=8,
            fill_alpha=0.4,
            view=self.date_view,
        )
        plot.scatter(
            marker="triangle",
            x="time_arr",
            y="nrsrapidd6_f110w",
            source=self.source,
            color="orange",
            size=13,
            fill_alpha=0.4,
            view=self.date_view,
        )
        plot.scatter(
            marker="square",
            x="time_arr",
            y="nrsrapid_clear",
            source=self.source,
            color="gray",
            size=7,
            fill_alpha=0.4,
            view=self.date_view,
        )
        plot.scatter(
            marker="square",
            x="time_arr",
            y="nrsrapidd6_clear",
            source=self.source,
            color="gray",
            size=12,
            fill_alpha=0.4,
            view=self.date_view,
        )

        # add count saturation warning lines
        loc1, loc2, loc3 = 45000.0, 50000.0, 60000.0
        hline1 = Span(
            location=loc1, dimension="width", line_color="green", line_width=3
        )
        hline2 = Span(
            location=loc2, dimension="width", line_color="yellow", line_width=3
        )
        hline3 = Span(location=loc3, dimension="width", line_color="red", line_width=3)
        plot.renderers.extend([hline1, hline2, hline3])

        label1 = Label(x=time_arr[-1], y=loc1, y_units="data", text="45000 counts")
        label2 = Label(x=time_arr[-1], y=loc2, y_units="data", text="50000 counts")
        label3 = Label(x=time_arr[-1], y=loc3, y_units="data", text="60000 counts")
        plot.add_layout(label1)
        plot.add_layout(label2)
        plot.add_layout(label3)
        plot.y_range = Range1d(-1000.0, 62000.0)

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("TA status", "@ta_status"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Box peak", "@max_val_box"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def get_unsuccessful_ta(self, arr_name):
        """Find unsuccessful TAs in this set (to be plotted in red)
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
        """Plot the WATA centroid
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # get the failed TAs to plot in red
        if "corr_col_failed" not in self.source.data:
            corr_col_failed, corr_col_not_failed = self.get_unsuccessful_ta("corr_col")
            corr_row_failed, corr_row_not_failed = self.get_unsuccessful_ta("corr_row")

            # add these to the bokeh data structure
            self.source.data["corr_col_failed"] = corr_col_failed
            self.source.data["corr_col_not_failed"] = corr_col_not_failed
            self.source.data["corr_row_failed"] = corr_row_failed
            self.source.data["corr_row_not_failed"] = corr_row_not_failed

        # create a new bokeh plot
        plot = figure(title="WATA Centroid", x_axis_label="Column", y_axis_label="Row")
        limits = [10, 25]
        plot.x_range = Range1d(limits[0], limits[1])
        plot.y_range = Range1d(limits[0], limits[1])
        plot.scatter(
            marker="circle",
            x="corr_col_not_failed",
            y="corr_row_not_failed",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.5,
            view=self.date_view,
        )
        plot.scatter(
            x="corr_col_failed",
            y="corr_row_failed",
            source=self.source,
            color="red",
            size=7,
            fill_alpha=0.5,
            view=self.date_view,
        )
        plot.x_range = Range1d(0.0, 32.0)
        plot.y_range = Range1d(0.0, 32.0)

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("TA status", "@ta_status"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Magnitude", "@star_mag"),
            ("Box Centr Col", "@corr_col"),
            ("Box Centr Row", "@corr_row"),
            ("Det Centr Col", "@detector_final_col"),
            ("Det Centr Row", "@detector_final_row"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def setup_date_range(self):
        """Set up a date range filter, defaulting to the last week of data."""
        end_date = datetime.now(tz=timezone.utc)
        one_week_ago = end_date.date() - timedelta(days=7)
        first_data_point = np.min(self.source.data["time_arr"]).date()
        last_data_point = np.max(self.source.data["time_arr"]).date()
        if last_data_point < one_week_ago:
            # keep at least one point in the plot if there was
            # no TA data this week
            start_date = last_data_point
        else:
            start_date = one_week_ago

        # allowed range is from the first ever data point to today
        self.date_range = DateRangeSlider(
            title="Date range displayed",
            start=first_data_point,
            end=end_date,
            value=(start_date, end_date),
            step=1,
        )

        callback = CustomJS(
            args=dict(s=self.source),
            code="""
            s.change.emit();
        """,
        )
        self.date_range.js_on_change("value", callback)

        filt = CustomJSFilter(
            args=dict(slider=self.date_range),
            code="""
                var indices = [];
                var start = slider.value[0];
                var end = slider.value[1];

                for (var i=0; i < source.get_length(); i++) {
                    if (source.data['time_arr'][i] >= start
                            && source.data['time_arr'][i] <= end) {
                        indices.push(true);
                    } else {
                        indices.push(false);
                    }
                }
                return indices;
                """,
        )
        self.date_view = CDSView(filter=filt)

    def mk_plt_layout(self, plot_data):
        """Create the bokeh plot layout

        Parameters
        ----------
        plot_data : pandas.DataFrame
            Dataframe of data to plot in bokeh
        """

        self.source = ColumnDataSource(data=plot_data)

        # add a time array to the data source
        self.add_time_column()

        # set up selection tools to share
        self.share_tools = [BoxSelectTool()]

        # set up a date range filter widget
        self.setup_date_range()

        # set the output html file name and create the plot grid
        p1 = self.plt_status()
        p2 = self.plt_residual_offsets()
        p3 = self.plt_v2offset_time()
        p4 = self.plt_v3offset_time()
        p5 = self.plt_centroid()
        p6 = self.plt_mag_time()

        # make grid
        grid = gridplot([p1, p2, p3, p4, p5, p6], ncols=2, merge_tools=False)
        box_layout = layout(children=[self.date_range, grid])

        self.script, self.div = components(box_layout)

    def file_exists_in_database(self, filename):
        """Checks if an entry for filename exists in the wata stats
        database.

        Parameters
        ----------
        filename : str
            The full path to the uncal filename.

        Returns
        -------
        file_exists : bool
            ``True`` if filename exists in the WATA stats database.
        """
        results = self.stats_table.objects.filter(filename__iexact=filename).values()
        return len(results) != 0

    def identify_tables(self):
        """Determine which database tables to use for a run of the TA monitor."""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval("{}TaQueryHistory".format(mixed_case_name))
        self.stats_table = eval("{}WataStats".format(mixed_case_name))

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
        filters = {"aperture__iexact": self.aperture, "run_monitor": True}

        record = (
            self.query_table.objects.filter(**filters).order_by("-end_time_mjd").first()
        )

        if record is None:
            query_result = self.query_very_beginning
            logging.info(
                (
                    "\tNo query history for {}. Beginning search date will be set to {}.".format(
                        self.aperture, self.query_very_beginning
                    )
                )
            )
        else:
            query_result = record.end_time_mjd

        return query_result

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
            if "filename" in list_element:
                files.append(list_element["filename"])
            elif "root_name" in list_element:
                files.append(list_element["root_name"])
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
            if filename.endswith(".fits"):
                # MAST names look like: jw01133003001_02101_00001_nrs2_cal.fits
                suffix2replace = filename.split("_")[-1]
                filename = filename.replace(suffix2replace, "uncal.fits")
            else:
                # rootnames look like: jw01133003001_02101_00001_nrs2
                filename += "_uncal.fits"
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
        # check if previous file exists and read the data from it
        if os.path.isfile(output_success_ta_txtfile):
            # now rename the previous file, for backup
            os.rename(
                output_success_ta_txtfile,
                os.path.join(self.output_dir, "prev_wata_success.txt"),
            )
        # get the new data
        ta_success, ta_failure = [], []
        filenames, ta_status = (
            self.wata_data.loc[:, "filename"],
            self.wata_data.loc[:, "ta_status"],
        )
        for fname, ta_stat in zip(filenames, ta_status):
            # select the appropriate list to append to
            if ta_stat == "SUCCESSFUL":
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
        with open(output_success_ta_txtfile, "w+") as txt:
            txt.write("# WATA successes and failure file names \n")
            filehdr1 = "# {} Total successful and {} total failed WATA ".format(
                successes, failures
            )
            filehdr2 = "# {:<50} {:<50}".format("Successes", "Failures")
            txt.write(filehdr1 + "\n")
            txt.write(filehdr2 + "\n")
            for idx, suc in enumerate(ta_success):
                line = "{:<50} {:<50}".format(suc, ta_failure[idx])
                txt.write(line + "\n")

    def add_timezone(self, date_str):
        """Method to bypass timezone warning from Django"""
        dt_timezone = parser.parse(date_str).replace(tzinfo=timezone.utc)
        return dt_timezone

    def add_wata_data(self):
        """Method to add WATA data to stats database"""
        # self.wata_data is a pandas dataframe. When creating the django model
        # to store all of the WATA data, this data was previously extracted and stored
        # into a dataframe. To avoid rewriting self.get_wata_data(), it is easier to
        # iterate over the rows of the returned dataframe and access the metadata this
        # way.
        for _, row in self.wata_data.iterrows():
            stats_db_entry = {
                "filename": row["filename"],
                "date_obs": self.add_timezone(row["date_obs"]),
                "visit_id": row["visit_id"],
                "tafilter": row["tafilter"],
                "readout": row["readout"],
                "ta_status": row["ta_status"],
                "star_name": row["star_name"],
                "star_ra": row["star_ra"],
                "star_dec": row["star_dec"],
                "star_mag": row["star_mag"],
                "star_catalog": row["star_catalog"],
                "planned_v2": row["planned_v2"],
                "planned_v3": row["planned_v3"],
                "stamp_start_col": row["stamp_start_col"],
                "stamp_start_row": row["stamp_start_row"],
                "star_detector": row["star_detector"],
                "max_val_box": row["max_val_box"],
                "max_val_box_col": row["max_val_box_col"],
                "max_val_box_row": row["max_val_box_row"],
                "iterations": row["iterations"],
                "corr_col": row["corr_col"],
                "corr_row": row["corr_row"],
                "stamp_final_col": row["stamp_final_col"],
                "stamp_final_row": row["stamp_final_row"],
                "detector_final_col": row["detector_final_col"],
                "detector_final_row": row["detector_final_row"],
                "final_sci_x": row["final_sci_x"],
                "final_sci_y": row["final_sci_y"],
                "measured_v2": row["measured_v2"],
                "measured_v3": row["measured_v3"],
                "ref_v2": row["ref_v2"],
                "ref_v3": row["ref_v3"],
                "v2_offset": row["v2_offset"],
                "v3_offset": row["v3_offset"],
                "sam_x": row["sam_x"],
                "sam_y": row["sam_y"],
                "entry_date": datetime.now(tz=timezone.utc),
            }

            entry = self.stats_table(**stats_db_entry)
            entry.save()

            logging.info("\tNew entry added to WATA stats database table")

        logging.info("\tUpdated the WATA statistics table")

    def plots_for_app(self):
        """Utility function to access div and script objects for
        embedding bokeh in JWQL application.
        """
        # Query results and convert into pandas df.
        self.query_results = pd.DataFrame(
            list(NIRSpecWataStats.objects.all().values())
        )
        # Generate plot
        self.mk_plt_layout(self.query_results)

    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for further details."""

        logging.info("Begin logging for wata_monitor")

        # Identify which database tables to use
        self.identify_tables()

        # Locate the record of most recent time the monitor was run
        self.query_start = self.most_recent_search()

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd
        logging.info("\tQuery times: {} {}".format(self.query_start, self.query_end))

        # Obtain all entries with instrument/aperture combinations:
        new_entries = monitor_utils.model_query_ta(
            self.instrument, self.aperture, self.query_start, self.query_end
        )
        wata_entries = len(new_entries)
        logging.info(
            "\tQuery has returned {} WATA files for {}, {}.".format(
                wata_entries, self.instrument, self.aperture
            )
        )

        # Filter new entries to only keep uncal files
        new_entries = self.pull_filenames(new_entries)
        new_entries = self.get_uncal_names(new_entries)
        wata_entries = len(new_entries)
        logging.info(
            "\tThere are {} uncal TA files to run the WATA monitor.".format(
                wata_entries
            )
        )

        # Check if filenames RootFileInfo model are in data storgage
        new_filenames = []
        for filename_of_interest in new_entries:
            if self.file_exists_in_database(filename_of_interest):
                logging.warning(
                    "\t\tFile {} in database already, passing.".format(
                        filename_of_interest
                    )
                )
                continue
            else:
                try:
                    new_filenames.append(filesystem_path(filename_of_interest))
                    logging.warning(
                        "\t\tFile {} included for processing.".format(
                            filename_of_interest
                        )
                    )
                except FileNotFoundError:
                    logging.warning(
                        "\t\tUnable to locate {} in filesystem. Not including in processing.".format(
                            filename_of_interest
                        )
                    )

        # If there are no new files, monitor is skipped
        if len(new_filenames) == 0:
            logging.info(
                "\t\t ** Unable to locate any file in filesystem. Nothing to process. ** "
            )
            logging.info("\tWATA monitor skipped. No WATA data found.")
            monitor_run = False
        else:
            # Run the monitor on any new files
            # self.wata_data is a pandas dataframe
            self.wata_data, no_ta_ext_msgs = self.get_wata_data(new_filenames)

            # Log msgs from TA files.
            if len(no_ta_ext_msgs) >= 1:
                for item in no_ta_ext_msgs:
                    logging.info(item)
            else:
                logging.info("\t No TA Ext Msgs Found")

            # Add WATA data to stats table.
            self.add_wata_data()

            # Once data is added to database table and plots are made, the
            # monitor has run successfully.
            monitor_run = True
            wata_files_used4plots = len(self.wata_data["visit_id"])
            logging.info(
                "\t{} WATA files were used to make plots.".format(wata_files_used4plots)
            )

            # update the list of successful and failed TAs
            self.update_ta_success_txtfile()

            logging.info("\tWATA status file was updated")

        # Update the query history
        new_entry = {
            "instrument": self.instrument,
            "aperture": self.aperture,
            "start_time_mjd": self.query_start,
            "end_time_mjd": self.query_end,
            "entries_found": wata_entries,
            "files_found": len(new_filenames),
            "run_monitor": monitor_run,
            "entry_date": datetime.now(tz=timezone.utc),
        }

        entry = self.query_table(**new_entry)
        entry.save()
        logging.info("\tUpdated the query history table")

        logging.info("WATA Monitor completed successfully.")


if __name__ == "__main__":
    module = os.path.basename(__file__).strip(".py")
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = WATA()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
