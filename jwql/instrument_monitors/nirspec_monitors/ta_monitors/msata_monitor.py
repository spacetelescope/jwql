#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# HISTORY
#    Feb 2022 - Vr. 1.0: Completed initial version
#    Jul 2022 - Vr. 1.1: Changed keywords to final flight values
#    Aug 2022 - Vr. 1.2: Modified plots according to NIRSpec team input
#    Sep 2022 - Vr. 1.3: Modified ColumnDataSource so that data could be recovered
#                        from an html file of a previous run of the monitor and
#                        included the code to read and format the data from the html file
#    Apr 2024 - Vr. 1.4: Removed html webscraping and now store data in django models

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
    - Melanie Clarke
    - Mees Fix

Use
---
    This module can be used from the command line as follows:
    python msata_monitor.py

"""

# general imports
import os
import logging
from datetime import datetime, timezone, timedelta
from dateutil import parser
from random import randint

import numpy as np
import pandas as pd
from astropy.time import Time
from astropy.io import fits
from bokeh.embed import components
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
from bokeh.plotting import figure, save, output_file

# jwql imports
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils import monitor_utils
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.utils import ensure_dir_exists, filesystem_path, get_config

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # Need to set up django apps before we can access the models
    import django  # noqa: E402 (module level import not at top of file)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()

    from jwql.website.apps.jwql.monitor_models.ta import (
        NIRSpecMsataStats,
        NIRSpecTaQueryHistory,
    )  # noqa: E402 (module level import not at top of file)


class MSATA:
    """Class for executing the NIRSpec MSATA monitor.

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
        """Initialize an instance of the MSATA class"""
        # Very beginning of intake of images: Jan 28, 2022 == First JWST images (MIRI)
        self.query_very_beginning = 59607.0

        # Set instrument and aperture
        self.instrument = "nirspec"
        self.aperture = "NRS_FULL_MSA"

        # dictionary to define required keywords to extract MSATA data and where it lives
        self.keywds2extract = {
            "FILENAME": {
                "loc": "main_hdr",
                "alt_key": None,
                "name": "filename",
                "type": str,
            },
            "DATE-BEG": {
                "loc": "main_hdr",
                "alt_key": None,
                "name": "date_obs",
                "type": str,
            },
            "OBS_ID": {
                "loc": "main_hdr",
                "alt_key": None,
                "name": "visit_id",
                "type": str,
            },
            "FILTER": {
                "loc": "main_hdr",
                "alt_key": "FWA_POS",
                "name": "tafilter",
                "type": str,
            },
            "DETECTOR": {
                "loc": "main_hdr",
                "alt_key": None,
                "name": "detector",
                "type": str,
            },
            "READOUT": {
                "loc": "main_hdr",
                "alt_key": "READPATT",
                "name": "readout",
                "type": str,
            },
            "SUBARRAY": {
                "loc": "main_hdr",
                "alt_key": None,
                "name": "subarray",
                "type": str,
            },
            "NUMREFST": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "num_refstars",
                "type": int,
            },
            "TASTATUS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "ta_status",
                "type": str,
            },
            "STAT_RSN": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "status_rsn",
                "type": str,
            },
            "V2HFOFFS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "v2halffacet",
                "type": float,
            },
            "V3HFOFFS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "v3halffacet",
                "type": float,
            },
            "V2MSACTR": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "v2msactr",
                "type": float,
            },
            "V3MSACTR": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "v3msactr",
                "type": float,
            },
            "FITXOFFS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "lsv2offset",
                "type": float,
            },
            "FITYOFFS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "lsv3offset",
                "type": float,
            },
            "OFFSTMAG": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "lsoffsetmag",
                "type": float,
            },
            "FITROFFS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "lsrolloffset",
                "type": float,
            },
            "FITXSIGM": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "lsv2sigma",
                "type": float,
            },
            "FITYSIGM": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "lsv3sigma",
                "type": float,
            },
            "ITERATNS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "lsiterations",
                "type": int,
            },
            "GUIDERID": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "guidestarid",
                "type": str,
            },
            "IDEAL_X": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "guidestarx",
                "type": float,
            },
            "IDEAL_Y": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "guidestary",
                "type": float,
            },
            "IDL_ROLL": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "guidestarroll",
                "type": float,
            },
            "SAM_X": {"loc": "ta_hdr", "alt_key": None, "name": "samx", "type": float},
            "SAM_Y": {"loc": "ta_hdr", "alt_key": None, "name": "samy", "type": float},
            "SAM_ROLL": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "samroll",
                "type": float,
            },
            "box_peak_value": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "box_peak_value",
                "type": float,
            },
            "reference_star_mag": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "reference_star_mag",
                "type": float,
            },
            "convergence_status": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "convergence_status",
                "type": str,
            },
            "reference_star_number": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "reference_star_number",
                "type": int,
            },
            "lsf_removed_status": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "lsf_removed_status",
                "type": str,
            },
            "lsf_removed_reason": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "lsf_removed_reason",
                "type": str,
            },
            "lsf_removed_x": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "lsf_removed_x",
                "type": float,
            },
            "lsf_removed_y": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "lsf_removed_y",
                "type": float,
            },
            "planned_v2": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "planned_v2",
                "type": float,
            },
            "planned_v3": {
                "loc": "ta_table",
                "alt_key": None,
                "name": "planned_v3",
                "type": float,
            },
            "FITTARGS": {
                "loc": "ta_hdr",
                "alt_key": None,
                "name": "stars_in_fit",
                "type": int,
            },
        }

        # initialize attributes to be set later
        self.source = None
        self.share_tools = []
        self.date_range = None
        self.date_filter = None
        self.date_view = None

    def get_tainfo_from_fits(self, fits_file):
        """Get the TA information from the fits file
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
                if "MSA_TARG_ACQ" in hdu.name:
                    msata = True
                    break
            if not msata:
                return None
            main_hdr = ff[0].header
            try:
                ta_hdr = ff["MSA_TARG_ACQ"].header
                ta_table = ff["MSA_TARG_ACQ"].data
            except KeyError:
                no_ta_ext_msg = "No TARG_ACQ extension in file " + fits_file
                return no_ta_ext_msg
        msata_info = [main_hdr, ta_hdr, ta_table]
        return msata_info

    def get_msata_data(self, new_filenames):
        """Get the TA information from the MSATA text table
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
        msata_dict, no_ta_ext_msgs = {}, []
        for fits_file in new_filenames:
            msata_info = self.get_tainfo_from_fits(fits_file)
            if isinstance(msata_info, str):
                no_ta_ext_msgs.append(msata_info)
                continue
            if msata_info is None:
                continue
            main_hdr, ta_hdr, ta_table = msata_info
            file_data_dict, file_errs = {}, []
            for key, key_dict in self.keywds2extract.items():
                key_name = key_dict["name"]
                if key_name not in file_data_dict:
                    file_data_dict[key_name] = []
                ext = main_hdr
                if key_dict["loc"] == "ta_hdr":
                    ext = ta_hdr
                if key_dict["loc"] == "ta_table":
                    ext = ta_table
                try:
                    val = ext[key]
                    if key == "filename":
                        val = fits_file
                except KeyError:
                    if key_dict["alt_key"] is not None:
                        try:
                            val = ext[key_dict["alt_key"]]
                        except (NameError, TypeError) as error:
                            msg = error + " in file " + fits_file
                            file_errs.append(msg)
                            break
                    else:
                        msg = (
                            "Keyword " + key + " not found. Skipping file " + fits_file
                        )
                        file_errs.append(msg)
                        break
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
                file_data_dict[key_name].append(val)
            # only update the data dictionary if all the keywords were found
            if len(file_errs) == 0:
                # if starting from scratch, simply update
                if len(msata_dict) == 0:
                    msata_dict.update(file_data_dict)
                # if msata_dict is not empty then extend the lists
                else:
                    for msata_dict_key in msata_dict:
                        msata_dict[msata_dict_key].extend(
                            file_data_dict[msata_dict_key]
                        )
            else:
                no_ta_ext_msgs.extend(file_errs)
        # create the pandas dataframe
        msata_df = pd.DataFrame(msata_dict)
        return msata_df, no_ta_ext_msgs

    def add_time_column(self):
        """Add time column to data source, to be used by all plots."""
        date_obs = self.source.data["date_obs"].astype(str)
        time_arr = [self.add_timezone(do_str) for do_str in date_obs]
        self.source.data["time_arr"] = time_arr

    def add_timezone(self, date_str):
        """Method to bypass timezone warning from Django"""
        dt_timezone = parser.parse(date_str).replace(tzinfo=timezone.utc)
        return dt_timezone

    def plt_status(self):
        """Plot the MSATA status versus time.
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        ta_status = self.source.data["ta_status"]
        # check if this column exists in the data already (the other 2 will exist too), else create it
        if "bool_status" not in self.source.data:
            # bokeh does not like to plot strings, turn into numbers
            number_status, status_colors = [], []
            for tas in ta_status:
                if tas.lower() == "unsuccessful":
                    number_status.append(0.0)
                    status_colors.append("red")
                elif "progress" in tas.lower():
                    number_status.append(0.5)
                    status_colors.append("gray")
                else:
                    number_status.append(1.0)
                    status_colors.append("blue")

            # add these to the bokeh data structure
            self.source.data["number_status"] = number_status
            self.source.data["status_colors"] = status_colors

        # create a new bokeh plot
        plot = figure(
            title="MSATA Status [Success=1, In Progress=0.5, Fail=0]",
            x_axis_label="Time",
            y_axis_label="MSATA Status",
            x_axis_type="datetime",
        )
        plot.y_range = Range1d(-0.5, 1.5)
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="number_status",
            source=self.source,
            color="status_colors",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("TA status", "@ta_status"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_residual_offsets(self):
        """Plot the residual Least Squares V2 and V3 offsets
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="MSATA Least Squares Residual V2-V3 Offsets",
            x_axis_label="Least Squares Residual V2 Offset",
            y_axis_label="Least Squares Residual V3 Offset",
        )
        plot.scatter(
            marker="circle",
            x="lsv2offset",
            y="lsv3offset",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )

        v2halffacet, v3halffacet = (
            self.source.data["v2halffacet"],
            self.source.data["v3halffacet"],
        )
        xstart, ystart, ray_length = -1 * v2halffacet[0], -1 * v3halffacet[0], 0.05
        plot.ray(
            x=xstart - ray_length / 2.0,
            y=ystart,
            length=ray_length,
            angle_units="deg",
            angle=0,
            line_color="purple",
            line_width=3,
        )
        plot.ray(
            x=xstart,
            y=ystart - ray_length / 2.0,
            length=ray_length,
            angle_units="deg",
            angle=90,
            line_color="purple",
            line_width=3,
        )
        hflabel = Label(
            x=xstart / 3.0, y=ystart, y_units="data", text="-V2, -V3 half-facets values"
        )
        plot.add_layout(hflabel)
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
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V3 offset", "@lsv3offset"),
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
            title="MSATA Least Squares V2 Offset vs Time",
            x_axis_label="Time",
            y_axis_label="Least Squares Residual V2 Offset",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="lsv2offset",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(-0.5, 0.5)

        # mark origin line
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        time_arr, v2halffacet = (
            self.source.data["time_arr"],
            self.source.data["v2halffacet"],
        )
        hfline = Span(
            location=-1 * v2halffacet[0],
            dimension="width",
            line_color="green",
            line_width=3,
        )
        plot.renderers.extend([hline, hfline])
        hflabel = Label(
            x=time_arr[-1],
            y=-1 * v2halffacet[0],
            y_units="data",
            text="-V2 half-facet value",
        )
        plot.add_layout(hflabel)

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V3 offset", "@lsv3offset"),
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
            title="MSATA Least Squares V3 Offset vs Time",
            x_axis_label="Time",
            y_axis_label="Least Squares Residual V3 Offset",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="lsv3offset",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(-0.5, 0.5)

        # mark origin line
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        time_arr, v3halffacet = (
            self.source.data["time_arr"],
            self.source.data["v3halffacet"],
        )
        hfline = Span(
            location=-1 * v3halffacet[0],
            dimension="width",
            line_color="green",
            line_width=3,
        )
        plot.renderers.extend([hline, hfline])
        hflabel = Label(
            x=time_arr[-1],
            y=-1 * v3halffacet[0],
            y_units="data",
            text="-V3 half-facet value",
        )
        plot.add_layout(hflabel)

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V3 offset", "@lsv3offset"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_lsv2v3offsetsigma(self):
        """Plot the residual Least Squares V2 and V3 sigma offsets
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="MSATA Least Squares Residual V2-V3 Sigma Offsets",
            x_axis_label="Least Squares Residual V2 Sigma Offset",
            y_axis_label="Least Squares Residual V3 Sigma Offset",
        )
        plot.scatter(
            marker="circle",
            x="lsv2sigma",
            y="lsv3sigma",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.x_range = Range1d(-0.1, 0.1)
        plot.y_range = Range1d(-0.1, 0.1)

        # mark origin lines
        vline = Span(location=0, dimension="height", line_color="black", line_width=0.7)
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        plot.renderers.extend([vline, hline])

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V2 sigma", "@lsv2sigma"),
            ("LS V3 offset", "@lsv3offset"),
            ("LS V3 sigma", "@lsv3sigma"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_res_offsets_corrected(self):
        """Plot the residual Least Squares V2 and V3 offsets corrected by the half-facet
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        lsv2offset, lsv3offset = (
            self.source.data["lsv2offset"],
            self.source.data["lsv3offset"],
        )
        v2halffacet, v3halffacet = (
            self.source.data["v2halffacet"],
            self.source.data["v3halffacet"],
        )

        # check if this column exists in the data already, else create it
        if "v2_half_fac_corr" not in self.source.data:
            v2_half_fac_corr, v3_half_fac_corr = [], []
            for idx, v2hf in enumerate(v2halffacet):
                v3hf = v3halffacet[idx]
                v2_half_fac_corr.append(lsv2offset[idx] + v2hf)
                v3_half_fac_corr.append(lsv3offset[idx] + v3hf)

            # add these to the bokeh data structure
            self.source.data["v2_half_fac_corr"] = v2_half_fac_corr
            self.source.data["v3_half_fac_corr"] = v3_half_fac_corr

        # create a new bokeh plot
        plot = figure(
            title="MSATA Least Squares Residual V2-V3 Offsets Half-facet corrected",
            x_axis_label="Least Squares Residual V2 Offset + half-facet",
            y_axis_label="Least Squares Residual V3 Offset + half-facet",
        )
        plot.scatter(
            marker="circle",
            x="v2_half_fac_corr",
            y="v3_half_fac_corr",
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
        xstart, ystart, ray_length = -1 * v2halffacet[0], -1 * v3halffacet[0], 0.05
        plot.ray(
            x=xstart - ray_length / 2.0,
            y=ystart,
            length=ray_length,
            angle_units="deg",
            angle=0,
            line_color="purple",
            line_width=3,
        )
        plot.ray(
            x=xstart,
            y=ystart - ray_length / 2.0,
            length=ray_length,
            angle_units="deg",
            angle=90,
            line_color="purple",
            line_width=3,
        )
        hflabel = Label(
            x=xstart / 3.0, y=ystart, y_units="data", text="-V2, -V3 half-facets values"
        )
        plot.add_layout(hflabel)

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V3 offset", "@lsv3offset"),
            ("V2 half-facet", "@v2halffacet"),
            ("V3 half-facet", "@v3halffacet"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_v2offsigma_time(self):
        """Plot the residual Least Squares V2 sigma Offset versus time

        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="MSATA Least Squares V2 Sigma Offset vs Time",
            x_axis_label="Time",
            y_axis_label="Least Squares Residual V2 Sigma Offset",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="lsv2sigma",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(-0.1, 0.1)

        # mark origin line
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        plot.renderers.extend([hline])

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V2 sigma", "@lsv2sigma"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_v3offsigma_time(self):
        """Plot the residual Least Squares V3 Offset versus time

        Returns
        -------
            p: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="MSATA Least Squares V3 Sigma Offset vs Time",
            x_axis_label="Time",
            y_axis_label="Least Squares Residual V3 Sigma Offset",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="lsv3sigma",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(-0.1, 0.1)

        # mark origin line
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)
        plot.renderers.extend([hline])

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS V3 offset", "@lsv3offset"),
            ("LS V3 sigma", "@lsv3sigma"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_roll_offset(self):
        """Plot the residual Least Squares roll Offset versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="MSATA Least Squares Roll Offset vs Time",
            x_axis_label="Time",
            y_axis_label="Least Squares Residual Roll Offset",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="lsrolloffset",
            source=self.source,
            color="blue",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(-600.0, 600.0)

        # mark origin line
        hline = Span(location=0, dimension="width", line_color="black", line_width=0.7)

        # Maximum accepted roll line and label
        time_arr = self.source.data["time_arr"]
        arlinepos = Span(
            location=120, dimension="width", line_color="green", line_width=3
        )
        arlineneg = Span(
            location=-120, dimension="width", line_color="green", line_width=3
        )
        arlabel = Label(x=time_arr[-1], y=125, y_units="data", text="Max accepted roll")
        plot.add_layout(arlabel)
        plot.renderers.extend([hline, arlinepos, arlineneg])

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V3 offset", "@lsv3offset"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_lsoffsetmag(self):
        """Plot the residual Least Squares Total Slew Magnitude Offset versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # create a new bokeh plot
        plot = figure(
            title="MSATA Least Squares Total Magnitude of the Linear V2, V3 Offset Slew vs Time",
            x_axis_label="Time",
            y_axis_label="sqrt((V2_off)**2 + (V3_off)**2)",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="lsoffsetmag",
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
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS slew mag offset", "@lsoffsetmag"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V3 offset", "@lsv3offset"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        # add shared selection tools
        for tool in self.share_tools:
            plot.add_tools(tool)
        return plot

    def plt_tot_number_of_stars(self):
        """Plot the total number of stars used versus time
        Parameters
        ----------
            None
        Returns
        -------
            plot: bokeh plot object
        """
        # get the number of stars per array
        visit_id = self.source.data["visit_id"]
        reference_star_number = self.source.data["reference_star_number"]

        # check if this column exists in the data already, else create it
        if "tot_number_of_stars" not in self.source.data:
            # create the list of color per visit and tot_number_of_stars
            colors_list, tot_number_of_stars = [], []
            color_dict = {}
            for i, vid in enumerate(visit_id):
                tot_stars = len(reference_star_number[i])
                tot_number_of_stars.append(tot_stars)
                ci = "#%06X" % randint(0, 0xFFFFFF)
                if vid not in color_dict:
                    color_dict[vid] = ci
                colors_list.append(color_dict[vid])

            # add these to the bokeh data structure
            self.source.data["tot_number_of_stars"] = tot_number_of_stars
            self.source.data["colors_list"] = colors_list

        # create a new bokeh plot
        plot = figure(
            title="Total Number of Measurements vs Time",
            x_axis_label="Time",
            y_axis_label="Total number of measurements",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="tot_number_of_stars",
            source=self.source,
            color="colors_list",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.scatter(
            marker="triangle",
            x="time_arr",
            y="stars_in_fit",
            source=self.source,
            color="black",
            size=7,
            fill_alpha=0.3,
            view=self.date_view,
        )
        plot.y_range = Range1d(0.0, 40.0)

        # add tooltips
        hover = HoverTool()
        hover.tooltips = [
            ("File name", "@filename"),
            ("Visit ID", "@visit_id"),
            ("Detector", "@detector"),
            ("Filter", "@tafilter"),
            ("Readout", "@readout"),
            ("Date-Obs", "@date_obs"),
            ("Subarray", "@subarray"),
            ("Stars in fit", "@stars_in_fit"),
            ("LS roll offset", "@lsrolloffset"),
            ("LS slew mag offset", "@lsoffsetmag"),
            ("LS V2 offset", "@lsv2offset"),
            ("LS V3 offset", "@lsv3offset"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

        return plot

    def plt_mags_time(self):
        """Plot the star magnitudes versus time
        Parameters
        ----------
            source: bokeh data object for plotting
        Returns
        -------
            plot: bokeh plot object
        """
        visit_id = self.source.data["visit_id"]
        lsf_removed_status = self.source.data["lsf_removed_status"]
        lsf_removed_reason = self.source.data["lsf_removed_reason"]
        lsf_removed_x = self.source.data["lsf_removed_x"]
        lsf_removed_y = self.source.data["lsf_removed_y"]
        planned_v2 = self.source.data["planned_v2"]
        planned_v3 = self.source.data["planned_v3"]
        reference_star_number = self.source.data["reference_star_number"]
        box_peak_value = self.source.data["box_peak_value"]
        date_obs, time_arr = self.source.data["date_obs"], self.source.data["time_arr"]
        colors_list = self.source.data["colors_list"]
        detector_list = self.source.data["detector"]
        filename = self.source.data["filename"]

        # create the structure matching the number of visits and reference stars
        new_colors_list, vid, dobs, tarr, star_no, status = [], [], [], [], [], []
        peaks, stars_v2, stars_v3, det, fnames = [], [], [], [], []
        for i, _ in enumerate(visit_id):
            v, d, t, c, s, x, y, dt, fn = [], [], [], [], [], [], [], [], []
            for j in range(len(reference_star_number[i])):
                v.append(visit_id[i])
                d.append(date_obs[i])
                t.append(time_arr[i])
                c.append(colors_list[i])
                dt.append(detector_list[i])
                fn.append(filename[i])
                if "not_removed" in lsf_removed_status[i][j]:
                    s.append("SUCCESS")
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
            det.extend(dt)
            fnames.extend(fn)

        # now create the mini ColumnDataSource for this particular plot
        mini_source = {
            "vid": vid,
            "star_no": star_no,
            "status": status,
            "dobs": dobs,
            "time_arr": tarr,
            "det": det,
            "fname": fnames,
            "peaks": peaks,
            "colors_list": new_colors_list,
            "stars_v2": stars_v2,
            "stars_v3": stars_v3,
        }
        mini_source = ColumnDataSource(data=mini_source)

        # hook up the date range slider to this source as well
        callback = CustomJS(
            args=dict(s=mini_source),
            code="""
            s.change.emit();
        """,
        )
        self.date_range.js_on_change("value", callback)
        mini_view = CDSView(filter=self.date_filter)

        # create the bokeh plot
        plot = figure(
            title="MSATA Counts vs Time",
            x_axis_label="Time",
            y_axis_label="box_peak [Counts]",
            x_axis_type="datetime",
        )
        plot.scatter(
            marker="circle",
            x="time_arr",
            y="peaks",
            source=mini_source,
            color="colors_list",
            size=7,
            fill_alpha=0.3,
            view=mini_view,
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
            ("File name", "@fname"),
            ("Visit ID", "@vid"),
            ("Detector", "@det"),
            ("Star No.", "@star_no"),
            ("LS Status", "@status"),
            ("Date-Obs", "@dobs"),
            ("Box peak", "@peaks"),
            ("Measured V2", "@stars_v2"),
            ("Measured V3", "@stars_v3"),
            ("--------", "----------------"),
        ]
        plot.add_tools(hover)

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

        self.date_filter = CustomJSFilter(
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
        self.date_view = CDSView(filter=self.date_filter)

    def mk_plt_layout(self, plot_data):
        """Create the bokeh plot layout

        Parameters
        ----------
        plot_data : pandas.DateFrame
            Pandas data frame of data to plot.
        """

        self.source = ColumnDataSource(data=plot_data)

        # add a time array to the data source
        self.add_time_column()

        # set up selection tools to share
        self.share_tools = [BoxSelectTool()]

        # set up a date range filter widget
        self.setup_date_range()

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
        grid = gridplot(
            [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12],
            ncols=2,
            merge_tools=False,
        )
        box_layout = layout(children=[self.date_range, grid])
        save(box_layout)

        # return the needed components for embedding the results in the MSATA html template
        script, div = components(box_layout)
        return script, div

    def identify_tables(self):
        """Determine which database tables to use for a run of the TA monitor."""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval("{}TaQueryHistory".format(mixed_case_name))
        self.stats_table = eval("{}MsataStats".format(mixed_case_name))

    def file_exists_in_database(self, filename):
        """Checks if an entry for filename exists in the MSATA stats
        database.

        Parameters
        ----------
        filename : str
            The full path to the uncal filename.

        Returns
        -------
        file_exists : bool
            ``True`` if filename exists in the MSATA stats database.
        """
        results = self.stats_table.objects.filter(filename__iexact=filename).values()
        return len(results) != 0

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
        # set the value to add
        val = -999
        list4dict = []
        # create either the list or return the right type of value
        if (
            keywd_dict["loc"] != "ta_table"
        ):  # these cases should be singe values per observation
            if keywd_dict["type"] == float:
                val = float(val)
            if keywd_dict["type"] == str:
                val = str(val)
            list4dict = val
        else:
            for tns in tot_number_of_stars:  # elements the list of lists should have
                list2append = []
                for _ in range(tns):  # elements each sublist should have
                    if keywd_dict["type"] == float:
                        val = float(val)
                    if keywd_dict["type"] == str:
                        val = str(val)
                    list2append.append(val)
                list4dict.append(list2append)
        return list4dict

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
        """Create a text file with all the failed and successful MSATA.
        Parameters
        ----------
            None
        Returns
        -------
            Nothing
        """
        output_success_ta_txtfile = os.path.join(self.output_dir, "msata_success.txt")
        # check if previous file exsists and read the data from it
        if os.path.isfile(output_success_ta_txtfile):
            # now rename the previous file, for backup
            os.rename(
                output_success_ta_txtfile,
                os.path.join(self.output_dir, "prev_msata_success.txt"),
            )
        # get the new data
        ta_success, ta_inprogress, ta_failure = [], [], []
        filenames, ta_status = (
            self.msata_data.loc[:, "filename"],
            self.msata_data.loc[:, "ta_status"],
        )
        for fname, ta_stat in zip(filenames, ta_status):
            # select the appropriate list to append to
            if ta_stat == "SUCCESSFUL":
                ta_success.append(fname)
            elif ta_stat == "IN_PROGRESS":
                ta_inprogress.append(fname)
            else:
                ta_failure.append(fname)
        # find which one is the longest list (to make sure the other lists have the same length)
        successes, inprogress, failures = (
            len(ta_success),
            len(ta_inprogress),
            len(ta_failure),
        )
        longest_list = None
        if successes >= inprogress:
            longest_list = successes
        else:
            longest_list = inprogress
        if longest_list < failures:
            longest_list = failures
        # match length of the lists
        for ta_list in [ta_success, ta_inprogress, ta_failure]:
            remaining_items = longest_list - len(ta_list)
            if remaining_items > 0:
                for _ in range(remaining_items):
                    ta_list.append("")
        # write the new output file
        with open(output_success_ta_txtfile, "w+") as txt:
            txt.write("# MSATA successes and failure file names \n")
            filehdr1 = "# {} Total successful and {} total failed MSATA ".format(
                successes, failures
            )
            filehdr2 = "# {:<50} {:<50} {:<50}".format(
                "Successes", "In_Progress", "Failures"
            )
            txt.write(filehdr1 + "\n")
            txt.write(filehdr2 + "\n")
            for idx, suc in enumerate(ta_success):
                line = "{:<50} {:<50} {:<50}".format(
                    suc, ta_inprogress[idx], ta_failure[idx]
                )
                txt.write(line + "\n")

    def add_msata_data(self):
        """Method to add MSATA data to stats database"""
        # self.msata_data is a pandas dataframe. When creating the django model
        # to store all of the MSATA data, this data was previously extracted and stored
        # into a dataframe. To avoid rewriting self.get_msata_data(), it is easier to
        # iterate over the rows of the returned dataframe and access the metadata this
        # way.
        for _, row in self.msata_data.iterrows():
            stats_db_entry = {
                "filename": row["filename"],
                "date_obs": self.add_timezone(row["date_obs"]),
                "visit_id": row["visit_id"],
                "tafilter": row["tafilter"],
                "detector": row["detector"],
                "readout": row["readout"],
                "subarray": row["subarray"],
                "num_refstars": row["num_refstars"],
                "ta_status": row["ta_status"],
                "v2halffacet": row["v2halffacet"],
                "v3halffacet": row["v3halffacet"],
                "v2msactr": row["v2msactr"],
                "v3msactr": row["v3msactr"],
                "lsv2offset": row["lsv2offset"],
                "lsv3offset": row["lsv3offset"],
                "lsoffsetmag": row["lsoffsetmag"],
                "lsrolloffset": row["lsrolloffset"],
                "lsv2sigma": row["lsv2sigma"],
                "lsv3sigma": row["lsv3sigma"],
                "lsiterations": row["lsiterations"],
                "guidestarid": row["guidestarid"],
                "guidestarx": row["guidestarx"],
                "guidestary": row["guidestary"],
                "guidestarroll": row["guidestarroll"],
                "samx": row["samx"],
                "samy": row["samy"],
                "samroll": row["samroll"],
                "box_peak_value": list(row["box_peak_value"]),
                "reference_star_mag": list(row["reference_star_mag"]),
                "convergence_status": list(row["convergence_status"]),
                "reference_star_number": list(row["reference_star_number"]),
                "lsf_removed_status": list(row["lsf_removed_status"]),
                "lsf_removed_reason": list(row["lsf_removed_reason"]),
                "lsf_removed_x": list(row["lsf_removed_x"]),
                "lsf_removed_y": list(row["lsf_removed_y"]),
                "planned_v2": list(row["planned_v2"]),
                "planned_v3": list(row["planned_v3"]),
                "stars_in_fit": row["stars_in_fit"],
                "entry_date": datetime.now(tz=timezone.utc),
            }

            entry = self.stats_table(**stats_db_entry)
            entry.save()

            logging.info("\tNew entry added to MSATA stats database table")

        logging.info("\tUpdated the MSATA statistics table")

    @log_fail
    @log_info
    def run(self):
        """The main method. See module docstrings for further details."""

        logging.info("Begin logging for msata_monitor")

        # Identify which database tables to use
        self.identify_tables()

        # Get the output directory and setup a directory to store the data
        self.output_dir = os.path.join(get_config()["outputs"], "msata_monitor")
        ensure_dir_exists(self.output_dir)
        # Set up directory to store the data
        ensure_dir_exists(os.path.join(self.output_dir, "data"))
        self.data_dir = os.path.join(
            self.output_dir,
            "data/{}_{}".format(self.instrument.lower(), self.aperture.lower()),
        )
        ensure_dir_exists(self.data_dir)

        # Locate the record of most recent time the monitor was run
        self.query_start = self.most_recent_search()
        self.output_file_name = os.path.join(self.output_dir, "msata_layout.html")

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd
        logging.info("\tQuery times: {} {}".format(self.query_start, self.query_end))

        # Obtain all entries with instrument/aperture combinations:
        new_entries = monitor_utils.mast_query_ta(
            self.instrument, self.aperture, self.query_start, self.query_end
        )
        msata_entries = len(new_entries)
        logging.info(
            "\tQuery has returned {} MSATA files for {}, {}.".format(
                msata_entries, self.instrument, self.aperture
            )
        )

        # Filter new entries to only keep uncal files
        new_entries = self.pull_filenames(new_entries)
        new_entries = self.get_uncal_names(new_entries)
        msata_entries = len(new_entries)
        logging.info(
            "\tThere are {} uncal TA files to run the MSATA monitor.".format(
                msata_entries
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
            logging.info("\tMSATA monitor skipped. No MSATA data found.")
            monitor_run = False
        else:
            # Run the monitor on any new files
            # self.wata_data is a pandas dataframe
            self.msata_data, no_ta_ext_msgs = self.get_msata_data(new_filenames)
            logging.info(
                "\tMSATA monitor found {} new uncal files.".format(len(new_filenames))
            )

            if len(no_ta_ext_msgs) >= 1:
                for item in no_ta_ext_msgs:
                    logging.info(item)
            else:
                logging.info("\tNo TA Ext Msgs Found")

            # Add MSATA data to stats table.
            self.add_msata_data()

            # Query results and convert into pandas df.
            self.query_results = pd.DataFrame(
                list(NIRSpecMsataStats.objects.all().values())
            )

            # Generate plot
            self.mk_plt_layout(self.query_results)

            logging.info(
                "\tNew output plot file will be written as: {}".format(
                    self.output_file_name
                )
            )
            # Once data is added to database table and plots are made, the
            # monitor has run successfully.
            monitor_run = True
            logging.info(
                "\tOutput html plot file created: {}".format(self.output_file_name)
            )
            msata_files_used4plots = len(self.msata_data["visit_id"])
            logging.info(
                "\t{} MSATA files were used to make plots.".format(
                    msata_files_used4plots
                )
            )
            # update the list of successful and failed TAs
            self.update_ta_success_txtfile()
            logging.info("\tMSATA status file was updated")

        # Update the query history
        new_entry = {
            "instrument": "nirspec",
            "aperture": self.aperture,
            "start_time_mjd": self.query_start,
            "end_time_mjd": self.query_end,
            "entries_found": msata_entries,
            "files_found": len(new_filenames),
            "run_monitor": monitor_run,
            "entry_date": datetime.now(tz=timezone.utc),
        }

        entry = self.query_table(**new_entry)
        entry.save()
        logging.info("\tUpdated the query history table")

        logging.info("MSATA Monitor completed successfully.")


if __name__ == "__main__":
    module = os.path.basename(__file__).strip(".py")
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    monitor = MSATA()
    monitor.run()

    monitor_utils.update_monitor_table(module, start_time, log_file)
