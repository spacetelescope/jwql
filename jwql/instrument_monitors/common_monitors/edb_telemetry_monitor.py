#! /usr/bin/env python

"""
######################################################################
Engineering Database Mnemonics Trending Monitor (EDB Trending Monitor)
######################################################################

This module contains code for the Engineering Database Telemetry monitor. For a given mnemonic,
this monitor retrieves telemetry data from the EDB, filters the data based on optional conditions,
calculates some basic statistics on the data, and plots the data.

There is a list of mnemonics to monitor for each instrument, in the form of a json file. For each
mnemonic, the file specifies the conditions for filtering the data. This may include filtering based
on the values of the mnemonic's own data (e.g. keep only entries where the voltage is < 0.25V), and/or
filtering based on the values of dependency mnemonics. For example, keep data for mnemonic A only
when mnemonic B is > 0.25V and mnemonic C is less than 38K.

Statistics
----------

After filtering the data, the monitor calcualtes statistics. The monitor supports several different types
averaging. These include:

1. **daily_means** - This is designed for mnemonics whose values do not change much over the course of a
day. In this case, mnemonic data is retrieved over a small amount of time each day (e.g. 12:00 - 12:15).
From these data, a daily mean is calculated. For all other types of telemetry, the EDB queries span
the full day.

2. **block_means** - These are mnemonics where the user wishes to see mean values associated with each
block of entries in the retrieved and filtered data. For example, you want to examine a voltage at times
when some other current is less than 0.25A. The script will read in all telemetry data, and filter out
data points for times where the current did not meet the criteria. It will then calculate the mean of
each remaining block of continuous good data. So if the data were good from 2:00 to 2:30, then bad until
3:00, and good again from 3:00-4:00, then the monitor will calculate a mean value for the 2:00-2:30
period, and a mean from the 3:00-4:00 period.

3. **time_interval** - Mnemonics in this category have their data retrieved and filtered, and then averaged
over the requested time interval. For example, if the user sets a time interval of 5 minutes, then the
monitor caculates the mean value within each 5-minute block of the total time range of the data, and plots
the average values.

4. **every_change** - This is the most complex case. Mnemonics in this category have their data filtered
and organized based on the value of a secondary mnemonic. For example, the IMIR_HK_GW14_POS_RATIO returns
a measure of the position of MIRI's grating wheel. We can plot this position as a function of the commanded
location of the grating wheel, which is provided by IMIR_HK_GW14_CUR_POS. In this case, the monitor will
loop over the commanded positions and for each, gather the measured position information. The measured
positions associated with each commanded position will then be plotted separately. Note that this use
of "every change" is separate from the idea of every-change telemetry, in which telemetry points are
only generated at times when the telemetry value changes. Some of the mnemonics in the EDB do contain
change-only telemetry data, but this should be largely invisible to the EDB Telemetry Monitor user.

5. **all** - In this case, no averaging is done. (Although filtering is still done) All filtered data
are kept as they are retrived from the EDB, and plotted without any modification.

6. **all+daily_means** - This is a combination of the "all" and "daily_means" cases above. All data points
are retrieved from the EDB and optionally filtered by dependencies. Then daily means are calculated.
Both the full set of data and the daily means are plotted, along with deviations from the mean.

7. **all+block_means** - This is a combination of the "all" and "block_means" cases above. All data points
are retrieved from the EDB and optionally filtered by dependencies. Then means for each block of good data
are calculated. Both the full set of data and the means are plotted, along with deviations from the mean.

8. **all+time_interval** - This is a combination of the "all" and "time_interval" cases above. All data points
are retrieved from the EDB and optionally filtered by dependencies. Then means are calculated for each block
of time lasting the duration of the time interval. Both the full set of data and the means are plotted, along
with deviations from the mean.

JSON file format
----------------

The type of data averaging is at the top level of the JSON file. Values must match the 8 types described above.
The entry for each mnemonic has several pieces of information, described below.

- **name**: Name of the mnemonic as it appears in the EDB.
- **database_id** Optional name to use in the plot title for this mnemonic. Any averaged data saved to the JWQL database will be saved under this name if it is present.
- **description**: Summary describing the data contained in the mnemonic. Placed in the plot title.
- **dependency**: This is a list of mnemonics and conditions that will be used to filter the data
- **plot_data**: Description of how the data are to be plotted. There are two options: "nominal", in which case
  the mnemonic data are plotted as-is, and "*<mnem>" where <mnem> is the name of another mnemonic. In this case, the
  data for this second mnemonic are retrieved using the same dependencies as the primary mnemonic. The primary mnemonic
  and this second mnemonic are then multiplied together and plotted. This option was designed around plotting power as
  the product of current and voltage.

A further option for the **"plot_data"** field is the addition of a comma-separated list of statistics to be overplotted.
Options are: "mean", "median", "max", and "min". Note that this is a little confusing, because in many cases the menmonic's
data will already contain the median value of the data (and the original data as returned from the EDB will not be
available). The monitor realized this though, so if you specify "mean" for a mnemonic in the "daily_mean" list, it will simply
plot the same data twice, on top of itself.

As an example, in order to plot the daily mean and maximum values of the product of SE_ZIMIRICEA and SE_ZBUSVLT, the plot_data
entry would be: "*SE_ZBUSVLT,max". If you also wanted to plot the minimum daily value, the entry would be: "*SE_ZBUSVLT,max,min".
And similarly, to plot SE_ZIMIRICEA on its own (not as a product), the plot_data entries shown above would become: "nominal,max"
and "nominal,max,min".

* **nominal_value**: Optional. The "expected" value for this mnemonic. If provided, a horizontal dashed line will be added at this value.
* **yellow_limits**: Optional. This is a list of two values that describe the lower and upper limits of the expected range of the mnemonic's value. If these are present, a green background is added to the plot at values between these limits. Outside of these limits, the background is yellow.
* **red_limits**: Optional. Similar to yellow_limits above. In this case the lower and upper limits represent the thresholds outside of which there may be a problem. In this case, the background of the plot outside of these values is red.
* **plot_category**: This is the name of the tab on the website into which this plot should be placed.
* **mean_time_block**: Optional. This is only used for ``time_interval`` mnemonics. It describes the length of time over which to bin and average the data. The value consists of a number and a unit of time: e.g. "15_minutes"

Below we present details on how to construct json entries for these specific cases.

"daily_means" entries
=====================
Here is an example of two **daily_mean** telemetry entries in the json file. In both, SE_ZIMIRICEA values are retrieved.
For the first plot, data are only kept for the times where the following dependencies are true:

1. SE_ZIMIRICEA is > 0.2 A
2. IMIR_HK_ICE_SEC_VOLT1 is < 1 V
3. IMIR_HK_IMG_CAL_LOOP is OFF
4. IMIR_HK_IFU_CAL_LOOP is OFF
5. IMIR_HK_POM_LOOP is OFF

For the second plot, data are kept for the times where:

1. IMIR_HK_ICE_SEC_VOLT1 is > 25 V

Note that the "database_id" entry is used to differentiate the plot labels of these two cases, as well as their entries in the JWQLDB.
In both cases, the data are plotted as the product of SE_ZIMIRICEA and SE_ZBUSVLT. In the second case, the maximum daily value is also
plotted. Both plots are placed in the ``power`` tab on the webpage.

.. code-block:: json

    {
        "daily_means": [
            {
                "name": "SE_ZIMIRICEA",
                "database_id": "SE_ZIMIRICEA_NO_OPS",
                "description": "ICE drive current (no ops)",
                "dependency": [
                    {
                        "name": "SE_ZIMIRICEA",
                        "relation": ">",
                        "threshold": 0.2
                    },
                    {
                        "name": "IMIR_HK_ICE_SEC_VOLT1",
                        "relation": "<",
                        "threshold": 1
                    },
                    {
                        "name": "IMIR_HK_IMG_CAL_LOOP",
                        "relation": "=",
                        "threshold": "OFF"
                    },
                    {
                        "name": "IMIR_HK_IFU_CAL_LOOP",
                        "relation": "=",
                        "threshold": "OFF"
                    },
                    {
                        "name": "IMIR_HK_POM_LOOP",
                        "relation": "=",
                        "threshold": "OFF"
                    }
                ],
                "plot_data": "*SE_ZBUSVLT",
                "nominal_value": 7.57,
                "yellow_limits": [7.0, 8.13],
                "plot_category": "power"
            },
            {
                "name": "SE_ZIMIRICEA",
                "database_id": "SE_ZIMIRICEA_OPS",
                "description": "ICE drive current (ops)",
                "dependency": [
                    {
                        "name": "IMIR_HK_ICE_SEC_VOLT1",
                        "relation": ">",
                        "threshold": 25
                    }
                ],
                "plot_data": "*SE_ZBUSVLT,max",
                "nominal_value": 11.13,
                "yellow_limits": [10.23, 12.02],
                "plot_category": "power"
            }
        ]
    }


For a case with no dependencies, the "dependencies" keyword can be left empty:

.. code-block:: json

    {
        "name": "INRC_ICE_DC_VOL_P5_DIG",
        "description": "ICE HK +5V voltage for digital electronics",
        "dependency": [],
        "plot_data": "nominal",
        "yellow_limits": [4.99, 5.04],
        "red_limits": [4.5, 5.5],
        "plot_category": "ice_voltage"
    }


"block_means" entries
=====================
In the example shown below, we want to plot IMIR_HK_ICE_SEC_VOLT1 at times when it has values higher
than 25V. In this case, the EDB monitor will find times when the voltage is under the 25V limit. These
times will separate the blocks of time when the voltage does meet the threshold value. It then calculates
and plots the median voltage within each of these blocks.

.. code-block:: json

    "block_means":[
        {
            "name": "IMIR_HK_ICE_SEC_VOLT1",
            "database_id": "IMIR_HK_ICE_SEC_VOLT1_OPS",
            "description": "ICE Secondary Voltage (HV) 1",
            "dependency": [
                {
                    "name": "IMIR_HK_ICE_SEC_VOLT1",
                    "relation": ">",
                    "threshold": 25
                }
            ],
            "plot_data": "nominal",
            "nominal_value": 39.24,
            "yellow_limits": [39.14, 39.34],
            "plot_category": "ICE_voltage"
        }

"time_interval" entries
=======================

For mnemonics to be averaged over some time period, use the "mean_time_block" entry.
The value of mean_time_block should be a number followed by an underscore and a unit
of time. Currently, the unit must contain one of "min", "sec", "hour", or "day". The
monitor looks for one of these strings within the mean_time_block entry, meaning that
"second", "seconds", "minutes", "minute", "hours", "days", etc are all valid entries.

In the example below, the EDB monitor will bin the SE_ZINRCICE1 data into 5 minute blocks,
and calculate and plot the mean of each block.

.. code-block:: json

    "time_interval": [
        {
            "name": "SE_ZINRCICE1",
            "description": "ICE1 current",
            "mean_time_block": "5_min",
            "dependency": [],
            "plot_data": "nominal",
            "yellow_limits": [0.36, 0.8],
            "red_limits": [0, 1.367],
            "plot_category": "box_current"
        }
    ]

"every_change" entries
======================

This is a complex case and at the moment is customized for the MIRI filter wheel position
mnemonics such as IMIR_HK_FW_POS_RATIO. In this case, the EDB monitor will retrieve data for
the filter wheel position, which is a float at each time. It will also retrive the commmanded
position of the filter wheel, which is a string at each time (e.g. OPEN, CLOSED). It then divides
the filter wheel postiion data into groups based on the value of the commanded position (i.e. group
together all of the postion data when the commanded position is OPEN). It then computes the median
value of the filter position within each continuous block of time where the commanded position is
constant. This median value is then normalized by the expected location value (retrieved from
constants.py). One line is plotted for each commanded position.

.. code-block:: json

    "every_change": [
        {
            "name": "IMIR_HK_FW_POS_RATIO",
            "description": "FW normalized position sensor voltage ratio",
            "dependency": [
                {
                    "name": "IMIR_HK_FW_CUR_POS",
                    "relation": "none",
                    "threshold": 0
                }
            ],
            "plot_data": "nominal",
            "yellow_limits": [-1.6, 1.6],
            "plot_category": "Position_sensors"
        }
    ]

"all" entries
=============
In this case, no grouping or averaging of data from the EDB are done. Data are retrieved from the EDB,
filtered by any dependencies, and plotted.

.. code-block:: json

    "all": [
        {
            "name": "SE_ZINRCICE1",
            "description": "ICE1 current",
            "dependency": [],
            "plot_data": "nominal",
            "yellow_limits": [0.36, 0.8],
            "red_limits": [0, 1.367],
            "plot_category": "box_current"
        },
        {
            "name": "SE_ZINRCICE2",
            "description": "ICE2 current",
            "dependency": [],
            "plot_data": "nominal",
            "yellow_limits": [0.38, 0.86],
            "red_limits": [0, 1.372],
            "plot_category": "box_current"
        }
    ]

"all+daily_means" entries
=========================
This is a combination of the "daily_means" and "all" cases above.

"all+block_means" entries
=========================
This is a combination of the "all" and "block_means" cases above.

"all+time_interval" entries
===========================
This is a combination of the "all" and "time_interval" cases above.


Summary of the EDB monitor operation
------------------------------------

The monitor is set up to find the total span of time over which the plots are requested
(with the default being contolled by the value in jwql.utils.constants). It loops over
each mnemonic and breaks the total time to be queried up into 24-hour long blocks. It then
queries the EDB once for each day-long block, filters the data based on any dependencies given
and then calculates statistics. Breaking the queries up into day-long blocks is done in order
to avoid having the EDB return a very large table, which could cause memory problems, or slow
the monitor down. This is a possibility because in some cases, mnemonic values are present at
cadences of > 1 Hz.

After data are filtered and averaged (and combined with the data of a second mnemonic if they
are being plotted as a product), any new data are saved to the JWQL database. This will prevent
having to repeat the calculations during future queries. For mnemonics where no averaging is
done, we do not save anything in the JWQL databases, in order to save memory.

Each time a query is initiated, the JWQL database is checked first and any relevent data are
retrieved. In this way, we only query the EDB for new data.

The monitor creates one plot for each specified mnemonic. These plots are organized into
"plot_categories", as seen in the json examples above. All plots for a given category are placed
together in a bokeh gridplot. Each gridplot (i.e. plot_category) is then placed in a separate
bokeh tab, in order to try and keep related plots together while not overwhelming the user
with too many plots at once. The tabbed plots are written out to a json file. When the user
clicks on the EDB Telemetry Monitor link on the web app, this json file is read in and embedded
into the html file that is displayed. With this method, EDB queries and data calculations are all
done asynchronously, which means that the EDB Telemetry Monitor web page shoudl be fast to load.

Author
------
    - Bryan Hilbert

Use
---
    This module can be called from the command line like this:

    ::

        python edb_telemetry_monitor.py

"""
import argparse
from collections import defaultdict
from copy import deepcopy
import datetime
import json
import logging
import numpy as np
import os
from requests.exceptions import HTTPError
import urllib

from astropy.stats import sigma_clipped_stats
from astropy.table import Table
from astropy.time import Time, TimeDelta
import astropy.units as u
from bokeh.embed import components, json_item
from bokeh.layouts import gridplot
from bokeh.models import BoxAnnotation, ColumnDataSource, DatetimeTickFormatter, HoverTool, Range1d
from bokeh.models.layouts import TabPanel, Tabs
from bokeh.plotting import figure, output_file, save, show
from bokeh.palettes import Turbo256
from jwql.database import database_interface
from jwql.database.database_interface import NIRCamEDBDailyStats, NIRCamEDBBlockStats, \
    NIRCamEDBTimeIntervalStats, NIRCamEDBEveryChangeStats, NIRISSEDBDailyStats, NIRISSEDBBlockStats, \
    NIRISSEDBTimeIntervalStats, NIRISSEDBEveryChangeStats, MIRIEDBDailyStats, MIRIEDBBlockStats, \
    MIRIEDBTimeIntervalStats, MIRIEDBEveryChangeStats, FGSEDBDailyStats, FGSEDBBlockStats, \
    FGSEDBTimeIntervalStats, FGSEDBEveryChangeStats, NIRSpecEDBDailyStats, NIRSpecEDBBlockStats, \
    NIRSpecEDBTimeIntervalStats, NIRSpecEDBEveryChangeStats, session, engine
from jwql.edb import engineering_database as ed
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import condition
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import utils
from jwql.shared_tasks.shared_tasks import only_one
from jwql.utils import monitor_utils
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.constants import EDB_DEFAULT_PLOT_RANGE, JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, MIRI_POS_RATIO_VALUES
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import ensure_dir_exists, get_config


ALLOWED_COMBINATION_TYPES = ['all+daily_means', 'all+block_means', 'all+every_change', 'all+time_interval']


class EdbMnemonicMonitor():
    """Class for executing the EDB Telemetry Monitor

    This class will search for and retrieve new telemetry data associated with the given
    mnemonics from the engineering database. These data will be filtered based on
    dependency menmonic details, and optioanlly averaged over some time period. These
    data will then be combined with data from previous runs of the EDB Telemetry
    Monitor, which have been stored in the JWQL database. The resulting data is
    then plotted.

    Attributes
    ----------
    query_results : dict
        Dictionary containing EDB query results for all mnemonics for the current session.

    figures : dict
        Dictionary of Bokeh figures. Keys are the plot_category, and values are lists of
        Bokeh figure objects.

    history_table : sqlalchemy table
        Table containing a history of the queries made for the mnemonic type

    _usename : str
        Key to use when specifying the mnemonic's identity

    query_cadence : datetime.datetime
        How often the EDB should be queried. Currently set to 1 day.

    plot_output_dir : str
        Directory into which the json file containing the gridded plots should be saved

    instrument : str
        Name of the instrument whose mnemonics are being investigated

    _plot_start : datetime.datetime
        Fallback date for the plot start. Only used if the plot contains no data.

    _plot_end : datetime.datetime
        Fallback date for the plot end. Only used if the plot contains no data.

    requested_start_time : datetime.datetime
        Earliest start time for the current run of the EDB Monitor

    requested_end_time : datetime.datetime
        Latest end time for the current run of the EDB Monitor


    Raises
    ------
    NotImplementedError
        If multiple dependencies are provided for an "every_change" mnemonic, or if the
        dependency values are not strings

    ValueError
        If the user requests to plot every_change data as the product of two mnemonics

    ValueError
        If the user gives a list of mnemonics to query (rather than getting them from a
        json file), but starting and ending dates for the plot are not specified

    NotImplementedError
        If the user specifies a plot type other than "nominal" or the product of two
        mnemonics

    ValueError
        If the user calls plot_every_change_data and requests multiple output types
        for the resulting figure

    """
    def __init__(self):
        self.query_results = {}

    def add_figure(self, fig, key):
        """Add Bokeh figure to the dictionary of figures

        Parameters
        ----------
        fig : bokeh.plotting.figure
            Plot of a single mnemonic

        key : str
            Key under which to store the plot
        """
        if key in self.figures:
            self.figures[key].append(fig)
        else:
            self.figures[key] = [fig]

    def add_new_block_db_entry(self, mnem, query_time):
        """Add a new entry to the database table for any kind
        of telemetry type other than "all" (which does not save
        data in the database) and "every_change" (which needs a
        custom table.)

        Parameters
        ----------
        mnem : jwql.edb.engineering_database.EdbMnemonic
            Mnemonic information

        query_time : datetime.datetime
            Start time of the query
        """
        logging.info(f"Adding new entry for {mnem.mnemonic_identifier} to history table.")
        times = mnem.data["dates"].data
        data = mnem.data["euvalues"].data
        stdevs = mnem.stdev
        times = ensure_list(times)
        data = ensure_list(data)
        stdevs = ensure_list(stdevs)
        medians = ensure_list(mnem.median)
        maxs = ensure_list(mnem.max)
        mins = ensure_list(mnem.min)

        # Make sure the max and min values are floats rather than ints
        if len(maxs) > 0:
            if (isinstance(maxs[0], int) | isinstance(maxs[0], np.integer)):
                maxs = [float(v) for v in maxs]
        else:
            print('len of maxs is zero! {mnem.mnemonic_identifier}, {maxs}, {mins}, {medians}')
        if len(mins) > 0:
            if (isinstance(mins[0], int) | isinstance(mins[0], np.integer)):
                mins = [float(v) for v in mins]
        if len(medians) > 0:
            if (isinstance(medians[0], int) | isinstance(medians[0], np.integer)):
                medians = [float(v) for v in medians]

        db_entry = {'mnemonic': mnem.mnemonic_identifier,
                    'latest_query': query_time,
                    'times': times,
                    'data': data,
                    'stdev': stdevs,
                    'median': medians,
                    'max': maxs,
                    'min': mins,
                    'entry_date': datetime.datetime.now()
                    }
        with engine.begin() as connection:
            connection.execute(self.history_table.__table__.insert(), db_entry)

    def add_new_every_change_db_entry(self, mnem, mnem_dict, dependency_name, query_time):
        """Add new entries to the database table for "every change"
        mnemonics. Add a separate entry for each dependency value.

        Parameters
        ----------
        mnem : str
            Name of the mnemonic whose data is being saved

        mnem_dict : dict
            Dictionary containing every_change data as output by organize_every_change()

        dependency_name : str
            Name of mnemonic whose values the changes in mnemonic are based on

        query_time : datetime.datetime
            Start time of the query
        """
        # We create a separate database entry for each unique value of the
        # dependency mnemonic.
        logging.info(f"Adding new entries for {mnem} to history table.")
        for key, value in mnem_dict.items():
            (times, values, medians, stdevs) = value
            times = ensure_list(times)
            values = ensure_list(values)

            # medians and stdevs will be single-element lists, so provide the
            # 0th element to the database entry
            db_entry = {'mnemonic': mnem,
                        'dependency_mnemonic': dependency_name,
                        'dependency_value': key,
                        'mnemonic_value': values,
                        'time': times,
                        'median': medians[0],
                        'stdev': stdevs[0],
                        'latest_query': query_time,
                        'entry_date': datetime.datetime.now()
                        }
            with engine.begin() as connection:
                connection.execute(
                    self.history_table.__table__.insert(), db_entry)

    def calc_timed_stats(self, mnem_data, bintime, sigma=3):
        """Not currently used.
        Calculate stats for telemetry using time-based averaging.
        This works on data that have potentially been filtered. How do
        we treated any breaks in the data due to the filtering? Enforce
        a new bin at each filtered block of data? Blindly average by
        time and ignore any missing data due to filtering? The former
        makes more sense to me

        Parameters
        ----------
        mnem_data : jwql.edb.engineering_database.EdbMnemonic
            Mnemonic data to be averaged

        bintime : astropy.time.Quantity
            Time to use for binning and averaging data

        Returns
        -------
        all_means : list
            List of mean values

        all_meds : list
            List of median values

        all_stdevs : list
            List of stadnard deviations

        all_times : list
            List of times associated with the means, medians, and standard deviations
        """
        all_means = []
        all_meds = []
        all_stdevs = []
        all_times = []

        minimal_delta = 1 * u.sec  # modify based on units of time
        for i in range(len(mnem_data.blocks) - 1):
            block_min_time = mnem_data.data["dates"][mnem_data.blocks[i]]
            block_max_time = mnem_data.data["dates"][mnem_data.blocks[i + 1]]
            bin_times = np.arange(block_min_time, block_max_time + minimal_delta, bintime)
            all_times.extend((bin_times[1:] - bin_times[0:-1]) / 2.)  # for plotting later

            for b_idx in range(len(bin_times) - 1):
                good_points = np.where((mnem_data.data["dates"] >= bin_times[b_idx]) & (mnem_data.data["dates"] < bin_times[b_idx + 1]))
                bin_mean, bin_med, bin_stdev = sigma_clipped_stats(mnem_data.data["data"][good_points], sigma=sigma)
                all_means.append(bin_mean)
                all_meds.append(bin_med)
                all_stdevs.append(bin_stdev)
        return all_means, all_meds, all_stdevs, all_times

    @log_fail
    @log_info
    @only_one(key='edb_monitor')
    def execute(self, mnem_to_query=None, plot_start=None, plot_end=None):
        """Top-level wrapper to run the monitor. Take a requested list of mnemonics to
        process, or assume that mnemonics will be processed.

        Parameters
        ----------
        mnem_to_query : dict
            Mnemonic names to query. This should be a dictionary with the instrument
            names as keys and a list of mnemonic names as the value. This option is
            intended for use when someone requests, from the website, an expanded timeframe
            compared to the default. The monitor will then look up the details
            of each mnemonic (i.e. dependencies, averaging) from the standard
            json file, and will run the query using query_start and query_end.

        plot_start : datetime.datetime
            Start time to use for the query when requested from the website. Note
            that the query will be broken up into multiple queries, each spanning
            the default amount of time, in order to prevent querying for too much
            data at one time.

        plot_end : datetime.datetime
            End time to use for the query when requested from the website.
        """
        # This is a dictionary that will hold the query results for multiple mnemonics,
        # in an effort to minimize the number of EDB queries and save time.
        self.query_results = {}

        # The cadence with which the EDB is queried. This is different than the query
        # duration. This is the cadence of the query starts, while the duration is the
        # block of time to query over. For example, a cadence of 1 day and a duration
        # of 15 minutes means that the EDB will be queried over 12:00am - 12:15am each
        # day.
        self.query_cadence = datetime.timedelta(days=1)

        # Set up directory structure to hold the saved plots
        config = get_config()
        outputs_dir = os.path.join(config["outputs"], "edb_telemetry_monitor")
        ensure_dir_exists(outputs_dir)

        # Case where the user is requesting the monitor run for some subset of
        # mnemonics for some non-standard time span
        if mnem_to_query is not None:
            if plot_start is None or plot_end is None:
                raise ValueError(("If mnem_to_query is provided, plot_start and plot_end "
                                  "must also be provided."))

            for instrument_name in JWST_INSTRUMENT_NAMES:
                if instrument_name in mnem_to_query:
                    # Read in a list of mnemonics that the instrument teams want to monitor
                    # From either a text file, or a edb_mnemonics_montior database table
                    monitor_dir = os.path.dirname(os.path.abspath(__file__))

                    # Define the output directory in which the html files will be saved
                    self.plot_output_dir = os.path.join(outputs_dir, instrument_name)
                    ensure_dir_exists(self.plot_output_dir)

                    # File of mnemonics to monitor
                    mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', f'{instrument_name}_mnemonics_to_monitor.json')

                    # Read in file with nominal list of mnemonics
                    with open(mnemonic_file) as json_file:
                        mnem_dict = json.load(json_file)

                    # Filter to keep only the requested mnemonics
                    filtered_mnemonic_dict = {}
                    for telem_type in mnem_dict:
                        for mnemonic in mnem_dict[telem_type]:
                            if mnemonic["name"] in mnem_to_query:
                                if telem_type not in filtered_mnemonic_dict:
                                    filtered_mnemonic_dict[telem_type] = []
                                filtered_mnemonic_dict[telem_type].append(mnemonic)

                    self.run(instrument_name, filtered_mnemonic_dict, plot_start=plot_start, plot_end=plot_end)
                    logging.info(f'Monitor complete for {instrument_name}')
        else:
            # Here, no input was provided on specific mnemonics to run, so we run the entire suite
            # as defined by the json files. This is the default operation.

            # Loop over instruments
            for instrument_name in JWST_INSTRUMENT_NAMES:
                monitor_dir = os.path.dirname(os.path.abspath(__file__))

                # File of mnemonics to monitor
                mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', f'{instrument_name}_mnemonics_to_monitor.json')

                # Define the output directory in which the html files will be saved
                self.plot_output_dir = os.path.join(outputs_dir, instrument_name)
                ensure_dir_exists(self.plot_output_dir)

                # Read in file with nominal list of mnemonics
                with open(mnemonic_file) as json_file:
                    mnem_dict = json.load(json_file)

                # Run with the entire dictionary
                self.run(instrument_name, mnem_dict, plot_start=plot_start, plot_end=plot_end)
                logging.info(f'Monitor complete for {instrument_name}')

        logging.info(f'EDB Telemetry Monitor completed successfully.')

    def filter_telemetry(self, mnem, data, dep_list):
        """
        Filter telemetry data for a single mnemonic based on a list of
        conditions/dependencies, as well as a time.

        Parameters
        ----------
        mnem : str
            Name of the mnemonic whose dependencies will be queried

        data : jwql.edb.engineering_database.EdbMnemonic
            Information and query results for a single mnemonic

        dep_list : list
            List of dependencies for a given mnemonic. Each element of the list
            is a dictionary containing the keys: name, relation, and threshold.
            In nominal operations, these are read out of the json file listing the
            mnemonics to be monitored.

        Returns
        -------
        filtered : jwql.edb.engineering_database.EdbMnemonic
            Filtered information and query results for a single mnemonic
        """
        if len(dep_list) == 0:
            return data

        all_conditions = []
        for dependency in dep_list:

            if dependency["name"] != mnem:
                # If the dependency to retrieve is different than the mnemonic being filtered,
                # get the dependency's times and values from the EDB.
                dep_mnemonic = self.get_dependency_data(dependency, data.requested_start_time, data.requested_end_time)

            else:
                # If we are just filtering the mnemonic based on it's own values, then there is
                # no need to query the EDB
                dep_mnemonic = {}
                dep_mnemonic["dates"] = data.data["dates"]
                dep_mnemonic["euvalues"] = data.data["euvalues"]

            if len(dep_mnemonic["dates"]) > 0:
                # For each dependency, get a list of times where the data are considered good
                # (e.g. the voltage is greater than 0.25)
                time_boundaries = condition.relation_test(dep_mnemonic, dependency["relation"], dependency["threshold"])

                # Add these times to the list of times associated with all dependencies.
                all_conditions.append(time_boundaries)
            else:
                # In this case, the query for dependency data returned an empty array. With no information
                # on the dependency, it seems like we have to throw out the data for the mnemonic of
                # interest, because there is no way to know if the proper conditions have been met.
                logging.info((f'No data for dependency {dependency["name"]} between {data.requested_start_time} and {data.requested_end_time}, '
                              f'so ignoring {mnem} data for the same time period.'))

                filtered = empty_edb_instance(data.mnemonic_identifier, data.requested_start_time,
                                              data.requested_end_time, meta=data.meta, info=data.info)
                return filtered

        # Now find the mnemonic's data that during times when all conditions were met
        full_condition = condition.condition(all_conditions)

        # For change only data, like SE_ZIMIRICEA, interpolate values to match the start and stop
        # times of all conditions in order to prevent a very stable value (meaning few datapoints)
        # from being interpreted as having no data during the time period of the conditions
        if data.meta['TlmMnemonics'][0]['AllPoints'] == 0:
            boundary_times = []
            for cond in all_conditions:
                for time_pair in cond.time_pairs:
                    boundary_times.extend([time_pair[0], time_pair[1]])
            # If we have a valid list of start/stop times (i.e. no None entries), then
            # add data for those points to the exsiting collection of date/value points.
            # To do this we use interpolate, but afterwards the data will still be change-
            # only.
            if None not in boundary_times:
                existing_dates = np.array(data.data["dates"])
                unique_boundary_dates = np.unique(np.array(boundary_times))
                interp_dates = sorted(np.append(existing_dates, unique_boundary_dates))
                data.interpolate(interp_dates)

        full_condition.extract_data(data.data)

        # Put the results into an instance of EdbMnemonic
        filtered = ed.EdbMnemonic(data.mnemonic_identifier, data.requested_start_time, data.requested_end_time,
                                  full_condition.extracted_data, data.meta, data.info, blocks=full_condition.block_indexes)
        return filtered

    def find_all_changes(self, mnem_data, dep_list):
        """Identify indexes of data to create separate blocks for each value of the
        condition. This is for the "every_change" mnemonics, where we want to create a
        mean value for all telemetry data acquired for each value of some dependency
        mnemonic.

        For now, this function assumes that we only have one dependency. I'm not sure
        how it would work with multiple dependencies.

        Parameters
        ----------
        mnem_data : jwql.edb.engineering_database.EdbMnemonic
            EDBMnemonic instance to be searched

        dep_list : list
            List of dependency mnemonic names. Currently should be a 1-element list

        Returns
        -------
        mnem_data : jwql.edb.engineering_database.EdbMnemonic
            EDBMnemonic instance that was input, with ```blocks``` and ```every_change_values```
            attributes added.
        """
        if len(dep_list) > 1:
            raise NotImplementedError("Not sure how to work with every_change data with multiple dependencies.")

        # If the mnemonic instance is empty, then populate the blocks and every_change_values
        # attributes with defaults, and exit
        if len(mnem_data) == 0:
            mnem_data.blocks = [0, 1]
            mnem_data.every_change_values = [np.nan]
            return mnem_data

        # Retrieve the data for the dependency to use
        dependency = self.get_dependency_data(dep_list[0], mnem_data.requested_start_time,
                                              mnem_data.requested_end_time)

        # If the dependency data are empty, then we can't define blocks. Set the entire range
        # of data to a single block. Since filter_data is called before find_all_changes, we
        # *should* never end up in here, as missing dependency data should zero out the main
        # mnemonic in there.
        if len(dependency) == 0:
            mnem_data.blocks = [0, len(mnem)]
            mnem_data.every_change_values = [np.nan]

        # Make sure the data values for the dependency are strings.
        if type(dependency["euvalues"][0]) != np.str_:
            raise NotImplementedError("find_all_changes() is not set up to handle non-strings in the dependency data")
        else:
            # Find indexes within the data table where the value of the dependency changes.
            change_indexes = np.where(dependency["euvalues"][:-1] != dependency["euvalues"][1:])[0]

            # Increase values by 1 to get the correct index for the full data length
            if len(change_indexes) > 0:
                change_indexes += 1

            # Add 0 as the first element
            change_indexes = np.insert(change_indexes, 0, 0)

            # Add the largest index as the final element
            change_indexes = np.insert(change_indexes, len(change_indexes), len(dependency["euvalues"]))

            # If dates differ between the mnemonic of interest and the dependency, then interpolate to match
            # If the mnemonic of interest is change-only data, then we need to interpolate onto a list of dates
            # that include those originally in the mnemonic plus those in the dependency)
            if (len(dependency["dates"]) != len(mnem_data.data["dates"].value)) or not np.all(dependency["dates"] == mnem_data.data["dates"].value):
                if mnem_data.meta['TlmMnemonics'][0]['AllPoints'] != 0:
                    mnem_data.interpolate(dependency["dates"])
                else:
                    # In practice, we should never end up in this block, because change-only data are transformed
                    # into every-point data after being returned by the query. It might be useful to keep this
                    # here for now, in case that situation changes later.
                    all_dates = sorted(np.append(np.array(dependency["dates"]), np.array(mnem_data.data["dates"].data)))
                    mnem_data.interpolate(all_dates)

                    # We also need to interpolate the dependency onto the same dates here, so that we know
                    # the new indexes where the values change
                    temp_dep = ed.EdbMnemonic(dep_list[0]['name'], dependency["dates"][0], dependency["dates"][-1],
                                              dependency, meta={'TlmMnemonics': [{'AllPoints': 1}]}, info={}, blocks=change_indexes)
                    temp_dep.interpolate(all_dates)
                    change_indexes = temp_dep.blocks

            # Get the dependency values for each change.
            vals = dependency["euvalues"][change_indexes[0:-1]].data

            # Place the dependency values in the every_change_values attribute, and the corresponding
            # indexes where the changes happen into the blocks attribute.
            mnem_data.blocks = change_indexes
            mnem_data.every_change_values = vals

        return mnem_data

    def generate_query_start_times(self, starting_time):
        """Generate a list of starting and ending query times such that the entire time range
        is covered, but we are only querying the EDB for one day's worth of data at a time.
        Start times are once per day between the previous query time and the present. End
        times are the start times plus the query duration.

        Parameters
        ----------
        starting_time : datetime.datetime
            Datetime specifying the earliest time to query the EDB

        Returns
        -------
        query_starting_times : list
            List of datetime objects giving start times for EDB queries on a daily basis

        query_ending_times : list
            List of datetime objects giving ending times for EDB queries on a daily basis
        """
        if starting_time is None:
            query_starting_times = None
            query_ending_times = None
            logging.info(f'Query start times: None')
        else:
            query_starting_times = []
            query_ending_times = []
            dtime = self._plot_end - starting_time
            if dtime > self.query_duration:
                full_days = dtime.days
                partial_day = dtime.seconds
                # If the time span is not a full day, but long enough to cover the query_duration,
                # then we can fit in a final query on the last day
                if partial_day > self.query_duration.total_seconds():
                    full_days += 1
            else:
                # If the time between the query start and the plot end time
                # is less than the query duration, then we do not query the EDB.
                # The next run of the monitor will be used to cover that time.
                return None, None

            for delta in range(full_days):
                tmp_start = starting_time + datetime.timedelta(days=delta)
                query_starting_times.append(tmp_start)
                query_ending_times.append(tmp_start + self.query_duration)

            # Make sure the end time of the final query is before the current time.
            # If it is after the present time, remove start,end pairs until the
            # latest ending time is before the present. It's better to throw out
            # the entire start,end entry rather than shorten the final start,end
            # pair because that can potentially cause a block of time to be skipped
            # over on the next run of the monitor.
            if query_ending_times[-1] > self._today:
                query_ending_times = np.array(query_ending_times)
                query_starting_times = np.array(query_starting_times)
                valid_ending_times = query_ending_times <= self._today
                query_starting_times = query_starting_times[valid_ending_times]
                query_ending_times = query_ending_times[valid_ending_times]
        return query_starting_times, query_ending_times

    def get_dependency_data(self, dependency, starttime, endtime):
        """Find EDB data for the mnemonic listed as a dependency. Keep a dcitionary up to
        date with query results for all dependencies, in order to minimize the number of
        queries we have to make. Return the requested dependency's time and data values
        in a dictionary.

        Parameters
        ----------
        dependency : dict
            The name of the mnemonic to seach for should be the value associated with the
            "name" key.

        starttime : datetime.datetime
            Staritng time for the query

        endtime : datetime.datetime
            Ending time for the query

        Returns
        -------
        dep_mnemonic : dict
            Data for the dependency mnemonic. Keys are "dates" and "euvalues". This is
            essentially the data in the ```data``` attribute of an EDBMnemonic instance
        """
        # If we have already queried the EDB for the dependency's data in the time
        # range of interest, then use that data rather than re-querying.
        if dependency["name"] in self.query_results:

            # We need the full time to be covered
            if ((self.query_results[dependency["name"]].requested_start_time <= starttime)
            and (self.query_results[dependency["name"]].requested_end_time >= endtime)):

                logging.info(f'Dependency {dependency["name"]} is already present in self.query_results.')

                # Extract data for the requested time range
                matching_times = np.where((self.query_results[dependency["name"]].data["dates"] >= starttime)
                                        & (self.query_results[dependency["name"]].data["dates"] <= endtime))
                dep_mnemonic = {"dates": self.query_results[dependency["name"]].data["dates"][matching_times],
                                "euvalues": self.query_results[dependency["name"]].data["euvalues"][matching_times]}

                logging.info(f'Length of returned data: {len(dep_mnemonic["dates"])}')
            else:
                # If what we have from previous queries doesn't cover the time range we need, then query the EDB.
                logging.info(f'Dependency {dependency["name"]} is present in self.query results, but does not cover the needed time. Querying EDB for the dependency.')
                mnemonic_data = ed.get_mnemonic(dependency["name"], starttime, endtime)
                logging.info(f'Length of returned data: {len(mnemonic_data)}, {starttime}, {endtime}')

                # Place the data in a dictionary
                dep_mnemonic = {"dates": mnemonic_data.data["dates"], "euvalues": mnemonic_data.data["euvalues"]}

                # This is to save the data so that we may avoid an EDB query next time
                # Add the new data to the saved query results. This should also filter out
                # any duplicate rows.
                self.query_results[dependency["name"]] = self.query_results[dependency["name"]] + mnemonic_data
        else:
            # In this case, the dependency is not present at all in the dictionary of past query results.
            # So here we again have to query the EDB.
            logging.info(f'Dependency {dependency["name"]} is not in self.query_results. Querying the EDB.')
            self.query_results[dependency["name"]] = ed.get_mnemonic(dependency["name"], starttime, endtime)
            logging.info(f'Length of data: {len(self.query_results[dependency["name"]])}, {starttime}, {endtime}')

            dep_mnemonic = {"dates": self.query_results[dependency["name"]].data["dates"],
                            "euvalues": self.query_results[dependency["name"]].data["euvalues"]}

        return dep_mnemonic

    def get_history(self, mnemonic, start_date, end_date, info={}, meta={}):
        """Retrieve data for a single mnemonic over the given time range from the JWQL
        database (not the EDB).

        Parameters
        ----------
        mnemonic : str
            Name of mnemonic whose data is to be retrieved

        start_date : datetime.datetime
            Beginning date of data retrieval

        end_date : datetime.datetime
            Ending date of data retrieval

        info : dict
            Info dictionary for an EDBMnemonic instance.

        meta : dict
            Meta dictionary for an EDBMnemonic instance.

        Returns
        -------
        hist : jwql.edb.engineering_database.EdbMnemonic
            Retrieved data
        """
        data = session.query(self.history_table) \
            .filter(self.history_table.mnemonic == mnemonic,
                    self.history_table.latest_query > start_date,
                    self.history_table.latest_query < end_date)

        all_dates = []
        all_values = []
        all_medians = []
        all_means = []
        all_maxs = []
        all_mins = []
        # Each row contains a list of dates and data that could have elements
        # outside of the plot range. Return only the points inside the desired
        # plot range
        for row in data:
            good = np.where((np.array(row.times) > self._plot_start) & (np.array(row.times) < self._plot_end))[0]
            times = list(np.array(row.times)[good])
            data = list(np.array(row.data)[good])
            medians = list(np.array(row.median)[good])
            maxs = list(np.array(row.max)[good])
            mins = list(np.array(row.min)[good])
            all_dates.extend(times)
            all_values.extend(data)
            all_means.extend(data)
            all_medians.extend(medians)
            all_maxs.extend(maxs)
            all_mins.extend(mins)

        tab = Table([all_dates, all_values], names=('dates', 'euvalues'))
        hist = ed.EdbMnemonic(mnemonic, start_date, end_date, tab, meta, info)
        hist.median = all_medians
        hist.median_times = all_dates
        hist.max = all_maxs
        hist.min = all_mins
        hist.mean = all_means
        return hist

    def get_history_every_change(self, mnemonic, start_date, end_date):
        """Retrieve data from the JWQL database for a single mnemonic over the given time range
        for every_change data (e.g. IMIR_HK_FW_POS_RATIO, where we need to calculate and store
        an average value for each block of time where IMIR_HK_FW_CUR_POS has a different value.
        This has nothing to do with 'change-only' data as stored in the EDB.

        Parameters
        ----------
        mnemonic : str
            Name of mnemonic whose data is to be retrieved

        start_date : datetime.datetime
            Beginning date of data retrieval

        end_date : datetime.datetime
            Ending date of data retrieval

        Returns
        -------
        hist : dict
            Retrieved data. Keys are the value of the dependency mnemonic,
            and each value is a 3-tuple. The tuple contains the times, values,
            and mean value of the primary mnemonic corresponding to the times
            that they dependency mnemonic has the value of the key.
        """
        data = session.query(self.history_table) \
            .filter(self.history_table.mnemonic == mnemonic,
                    self.history_table.latest_query > start_date,
                    self.history_table.latest_query < end_date)

        # Set up the dictionary to contain the data
        hist = {}

        # Place the data from the database into the appropriate key
        for row in data:
            if row.dependency_value in hist:
                if len(hist[row.dependency_value]) > 0:
                    times, values, medians, devs = hist[row.dependency_value]

                    """
                    if row.dependency_value == 'F1000W':
                        print('BEFORE NEXT ENTRY, RETRIEVED DATA:')
                        for e in times:
                            print(e)
                            print('')
                        for e in medians:
                            print(e)
                            print('')
                    """




                else:
                    times = []
                    values = []
                    medians = []
                    devs = []

                # Keep only data that fall at least partially within the plot range
                if (((np.min(row.time) > self._plot_start) & (np.min(row.time) < self._plot_end))
                | ((np.max(row.time) > self._plot_start) & (np.max(row.time) < self._plot_end))):
                    times.append(row.time)
                    values.append(row.mnemonic_value)
                    medians.append([row.median])
                    devs.append([row.stdev])
                    hist[row.dependency_value] = (times, values, medians, devs)

                    """
                    if row.dependency_value == 'F1000W':
                        print('AFTER NEXT ENTRY:')
                        for e in times:
                            print(e)
                            print('')
                        for e in medians:
                            print(e)
                            print('')
                        for e in hist[row.dependency_value][0]:
                            print(e)
                            print('')
                        for e in hist[row.dependency_value][2]:
                            print(e)
                            print('')
                    """







            else:
                if (((np.min(row.time) > self._plot_start) & (np.min(row.time) < self._plot_end))
                | ((np.max(row.time) > self._plot_start) & (np.max(row.time) < self._plot_end))):
                    hist[row.dependency_value] = ([row.time], [row.mnemonic_value], [[row.median]], [[row.stdev]])
                    if row.dependency_value == 'F1000W':
                        print('INITIAL ENTRY:')
                        for e in hist[row.dependency_value][0]:
                            print(e)
                            print('')
                        for e in hist[row.dependency_value][2]:
                            print(e)
                            print('')




        return hist

    def get_mnemonic_info(self, mnemonic, starting_time, ending_time, telemetry_type):
        """Wrapper around the code to query the EDB, filter the result, and calculate
        appropriate statistics for a single mnemonic

        Parameters
        ----------
        mnemonic : dict
            Dictionary of information about the mnemonic to be processed. Dictionary
            as read in from the json file of mnemonics to be monitored.

        starting_time : datetime.datetime
            Beginning time for query

        ending_time : datetime.datetime
            Ending time for query

        telemetry_type : str
            How the telemetry will be processed. This is the top-level heirarchy from
            the json file containing the mnemonics. e.g. "daily_means", "every_change"

        Returns
        -------
        good_mnemonic_data : jwql.edb.engineering_database.EdbMnemonic
            EdbMnemonic instance containing filtered data for the given mnemonic
        """
        logging.info(f'Querying EDB for: {mnemonic["name"]} from {starting_time} to {ending_time}')

        try:
            mnemonic_data = ed.get_mnemonic(mnemonic["name"], starting_time, ending_time)

            if len(mnemonic_data) == 0:
                logging.info(f"No data returned from EDB for {mnemonic['name']} between {starting_time} and {ending_time}")
                return None
            else:
                logging.info(f'Retrieved from EDB, {mnemonic["name"]} between {starting_time} and {ending_time} contains {len(mnemonic_data)} data points.')

            # If the mnemonic has an alternative name (due to e.g. repeated calls for that mnemonic but with
            # different averaging schemes), then update the mnemonic_identifier in the returned EdbMnemonic
            # instance. This will allow different versions to be saved in the database. For example, monitoring
            # a current value when a corresponding voltage value is low (i.e. turned off) and when it is high
            # (turned on).
            if "database_id" in mnemonic:
                mnemonic_data.mnemonic_identifier = mnemonic["database_id"]
            else:
                mnemonic_data.mnemonic_identifier = mnemonic["name"]

        except (urllib.error.HTTPError, HTTPError):
            # Sanity check that the mnemonic is available in the EDB.
            logging.info(f'{mnemonic["name"]} not accessible with current search.')
            return None

        # Filter the data to keep only those values/times where the dependency conditions are met.
        if ((len(mnemonic["dependency"]) > 0) and (telemetry_type != "every_change")):
            good_mnemonic_data = self.filter_telemetry(mnemonic["name"], mnemonic_data, mnemonic['dependency'])
            logging.info(f'After filtering by dependencies, the number of data points is {len(good_mnemonic_data)}')
        else:
            # No dependencies. Keep all the data
            good_mnemonic_data = mnemonic_data
            good_mnemonic_data.blocks = [0]

        if telemetry_type == "every_change":
            # If this is "every_change" data (i.e. we want to find the mean value of the mnemonic corresponding to
            # each block of time when some dependency mnemonic changes value), then locate those changes in the
            # dependency data here. Note that this adds the "every_change_values" attribute, which is not present
            # for other telemety types, but will be needed for plotting and saving data in the database.
            good_mnemonic_data = self.find_all_changes(good_mnemonic_data, mnemonic['dependency'])

        if telemetry_type == 'time_interval':
            good_mnemonic_data.mean_time_block = utils.get_averaging_time_duration(mnemonic["mean_time_block"])

        # If the filtered data contains enough entries, then proceed.
        if len(good_mnemonic_data) > 0:
            logging.info(f'get_mnemonic_info returning data of length {len(good_mnemonic_data)}')
            return good_mnemonic_data
        else:
            logging.info(f'get_mnemonic_info returning data with zero length')
            return None

    def identify_tables(self, inst, tel_type):
        """Determine which database tables to use for a given type of telemetry.

        Parameters
        ----------
        inst : str
            Name of instrument (e.g. nircam)

        tel_type : str
            Type of telemetry. This comes from the json file listing all mnemonics to be monitored.
            Examples include "every_change", "daily", "all", etc
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst]
        if '_means' in tel_type:
            tel_type = tel_type.strip('_means')
        tel_type = tel_type.title().replace('_', '')
        self.history_table_name = f'{mixed_case_name}EDB{tel_type}Stats'
        self.history_table = getattr(database_interface, f'{mixed_case_name}EDB{tel_type}Stats')

    def most_recent_search(self, telem_name):
        """Query the database and return the information
        on the most recent query, indicating the last time the
        EDB Mnemonic monitor was executed.

        Parameters
        ----------
        telem_name : str
            Mnemonic to search for

        Returns
        -------
        query_result : datetime.datetime
            Date of the ending range of the previous query
        """
        query = session.query(self.history_table).filter(self.history_table.mnemonic == telem_name).order_by(self.history_table.latest_query).all()

        if len(query) == 0:
            base_time = '2022-11-15 00:00:0.0'
            query_result = datetime.datetime.strptime(base_time, '%Y-%m-%d %H:%M:%S.%f')
            logging.info(f'\tNo query history for {telem_name}. Returning default "previous query" date of {base_time}.')
        else:
            query_result = query[-1].latest_query
            logging.info(f'For {telem_name}, the previous query time is {query_result}')

        return query_result

    def multiday_mnemonic_query(self, mnemonic_dict, starting_time_list, ending_time_list, telemetry_type):
        """Wrapper function. In order to avoid any issues with giant tables, for a given mnemonic we query the
        EDB for only one day's worth of data at a time. For each day we retrieve the data, retrieve the data
        for any dependencies, filter the data based on the dependencies, and then perform any requested
        averaging before moving on to the next day.

        Parameters
        ----------
        mnemonic_dict : dict
            Dictionary of information for a single mnemonic. This comes from the json file describing all
            mnemonics to be monitored

        starting_time_list : list
            List of datetime values indicating beginning query times

        ending_time_list : list
            List of datetime values indicating the end time of each query

        telemetry_type : str
            Type of telemetry being retrieved. This is from the top-level of the json file describing
            all mnemonics to be monitored. Examples include "every_change", "daily", "all".

        Returns
        -------
        all_data : jwql.edb.engineering_database.EdbMnemonic
            EDBMnemonic instance containing the mnemonic's filtered, averaged data spanning the entire
            time range between the earliest start time and latest end time. Note that if averaging is
            done, then the data table in this instance contains the averaged data. The original data
            is not returned.
        """
        multiday_table = Table()
        multiday_median_times = []
        multiday_mean_vals = []
        multiday_stdev_vals = []
        multiday_median_vals = []
        multiday_max_vals = []
        multiday_min_vals = []
        multiday_every_change_data = []
        info = {}
        meta = {}
        identifier = mnemonic_dict[self._usename]

        # In cases where a mnemonic is going to be plotted as a product of itself with another mnemonic,
        # construct a name that reflects this fact and use it in the mnemonic_identifer attribute. This
        # will then end up as the plot title later.
        if '*' in mnemonic_dict["plot_data"]:
            # Strip off any comma-separated list of what to plot
            second_part = mnemonic_dict["plot_data"].split(',')[0]
            # Define the mnemonic identifier to be <mnemonic_name_1>*<mnemonic_name_2>
            product_identifier = f'{mnemonic_dict[self._usename]}{second_part}'
            logging.info(f'In multiday, product_identifier is: {product_identifier}')

        # Work one start time/end time pair at a time.
        for i, (starttime, endtime) in enumerate(zip(starting_time_list, ending_time_list)):
            # This function wraps around the EDB query and dependency filtering.
            mnemonic_info = self.get_mnemonic_info(mnemonic_dict, starttime, endtime, telemetry_type)

            # If data are returned, do the appropriate averaging
            if mnemonic_info is not None:

                identifier = mnemonic_info.mnemonic_identifier
                info = mnemonic_info.info
                meta = mnemonic_info.meta

                # Calculate mean/median/stdev
                mnemonic_info = calculate_statistics(mnemonic_info, telemetry_type)

                # If this mnemonic is going to be plotted as a product with another mnemonic, then
                # retrieve the second mnemonic info here
                if '*' in mnemonic_dict["plot_data"]:

                    if telemetry_type == 'every_change':
                        raise ValueError("Plotting product of two mnemonics is not supported for every-change data.")

                    temp_dict = deepcopy(mnemonic_dict)
                    temp_dict["name"] = mnemonic_dict["plot_data"].split(',')[0].strip('*')
                    product_mnemonic_info = self.get_mnemonic_info(temp_dict, starttime, endtime, telemetry_type)
                    logging.info(f'Length of data for product mnemonic: {len(mnemonic_info)}')

                    if product_mnemonic_info is None:
                        logging.info(f'{temp_dict["name"]} to use as product has no data between {starttime} and {endtime}.\n\n')
                        continue

                    # If either mnemonic is change-only data, then first interpolate it
                    # onto the dates of the other. If they are both every-change data,
                    # then interpolate onto the mnemonic with the smaller date range
                    if mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] == 0:
                        if product_mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] == 0:
                            # If both mnemonics are change-only, then we need to translate them both
                            # to all-points.
                            delta_t = timedelta(seconds=1.)
                            mnem_numpts = (mnemonic_info.data["dates"][-1] - mnemonic_info.data["dates"][0]) / delta_t + 1
                            mnem_new_dates = [mnemonic_info.data["dates"][0] + i * delta_t for i in range(len(mnem_numpts))]

                            prod_numpts = (product_mnemonic_info.data["dates"][-1] - product_mnemonic_info.data["dates"][0]) / delta_t + 1
                            prod_new_dates = [product_mnemonic_info.data["dates"][0] + i * delta_t for i in range(len(prod_numpts))]

                            # Interpolate each onto its new list of allPoints dates. When they are multiplied below,
                            # they will be interpolated onto the same list of dates.
                            mnemonic_info.interpolate(mnem_new_dates)
                            product_mnemonic_info.interpolate(prod_new_dates)

                            # Update metadata to reflect that these are now allPoints data
                            product_mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] = 1
                        else:
                            mnemonic_info.interpolate(product_mnemonic_info.data["dates"])
                        # Now that we have effectively converted the change-only data into allPoints data,
                        # modify the metadata to reflect that
                        mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] = 1
                    else:
                        if product_mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] == 0:
                            # Interpolate onto the allPoints set of dates, and update the metadata
                            product_mnemonic_info.interpolate(mnemonic_info.data["dates"])
                            product_mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] = 1
                        else:
                            pass

                    # Multiply the mnemonics together to get the quantity to be plotted
                    combined = mnemonic_info * product_mnemonic_info
                    logging.info(f'Length of data for product of mnemonics: {len(combined)}')

                    # Calculate mean/median/stdev of the product data
                    mnemonic_info = calculate_statistics(combined, telemetry_type)

                # Combine information from multiple days here. If averaging is done, keep track of
                # only the averaged data. If no averaging is done, keep all data.
                if telemetry_type != 'all':
                    multiday_median_times.extend(mnemonic_info.median_times)
                    multiday_mean_vals.extend(mnemonic_info.mean)
                    multiday_median_vals.extend(mnemonic_info.median)
                    multiday_max_vals.extend(mnemonic_info.max)
                    multiday_min_vals.extend(mnemonic_info.min)
                    multiday_stdev_vals.extend(mnemonic_info.stdev)
                    if telemetry_type == 'every_change':
                        multiday_every_change_data.extend(mnemonic_info.every_change_values)
                else:
                    multiday_median_times.extend(mnemonic_info.data["dates"].data)
                    multiday_mean_vals.extend(mnemonic_info.data["euvalues"].data)
                    multiday_stdev_vals.extend(mnemonic_info.stdev)
                    multiday_median_vals.extend(mnemonic_info.median)
                    multiday_max_vals.extend(mnemonic_info.max)
                    multiday_min_vals.extend(mnemonic_info.min)

            else:
                logging.info(f'{mnemonic_dict["name"]} has no data between {starttime} and {endtime}.')
                continue

        # If all daily queries return empty results, get the info metadata from the EDB, so
        # that we can at least populate that in the output EDBMnemonic instance.
        if len(info) == 0:
            info = ed.get_mnemonic_info(mnemonic_dict["name"])

        # Combine the mean values and median time data from multiple days into a single EdbMnemonic
        # instance.
        multiday_table["dates"] = multiday_median_times

        if telemetry_type != 'all':
            multiday_table["euvalues"] = multiday_median_vals
        else:
            multiday_table["euvalues"] = multiday_mean_vals

        all_data = ed.EdbMnemonic(identifier, starting_time_list[0], ending_time_list[-1],
                                  multiday_table, meta, info)
        all_data.stdev = multiday_stdev_vals
        all_data.mean = multiday_mean_vals
        all_data.median = multiday_median_vals
        all_data.max = multiday_max_vals
        all_data.min = multiday_min_vals
        all_data.median_times = multiday_median_times

        # If it is an every_change mnemonic, then we need to also keep track of the dependency
        # values that correspond to the mean values.
        if telemetry_type == 'every_change':
            all_data.every_change_values = multiday_every_change_data

        # Set the mnemonic identifier to be <mnemonic_name_1>*<mnemonic_name_2>
        # This will be used in the title of the plot later
        if '*' in mnemonic_dict["plot_data"]:
            all_data.mnemonic_identifier = product_identifier

        logging.info(f'DONE retrieving/filtering/averaging data for {mnemonic_dict["name"]}')
        return all_data

    def run(self, instrument, mnemonic_dict, plot_start=None, plot_end=None):
        """Run the monitor on a single mnemonic.

        Parameters
        ----------
        instrument : str
            Instrument name (e.g. nircam)

        mnemonic_dict : dict
            Dictionary of information for a single mnemonic. Keys include: "name", "description",
            "depenency", "plot_data", "yellow_limits", "red_limits", "plot_category". In normal
            operation, this is read in from the json file that lists all mnemonics to be monitored

        plot_start : datetime.datetime
            Starting time for the output plot

        plot_end : datetime.datetime
            Ending time for the output plot
        """
        # Container to hold and organize all plots
        self.figures = {}
        self.instrument = instrument
        self._today = datetime.datetime.now()

        # Set the limits for the telemetry plots if necessary
        if plot_start is None:
            plot_start = self._today - datetime.timedelta(days=EDB_DEFAULT_PLOT_RANGE)

        if plot_end is None:
            plot_end = self._today




        # SPEED UP TESTING. REMOVE BEFORE MERGING
        plot_start = self._today - datetime.timedelta(days=3.)
        plot_end = self._today






        # Only used as fall-back plot range for cases where there is no data
        self._plot_start = plot_start
        self._plot_end = plot_end

        # At the top level, we loop over the different types of telemetry. These types
        # largely control if/how the data will be averaged.
        for telemetry_kind in mnemonic_dict:   # ['every_change']']
            telem_type = telemetry_kind
            logging.info(f'Working on telemetry_type: {telem_type}')

            # For the combined telemetry types (e.g. "all+daily_mean") break up
            # into its component parts. Work on the second part (e.g. "daily_mean")
            # first, and then the "all" part afterwards
            if telemetry_kind in ALLOWED_COMBINATION_TYPES:
                telem_type = telemetry_kind.split('+')[1]
                logging.info(f'Working first on {telem_type}')

            # Figure out the time duration over which the mnemonic should be queried. In
            # most cases this is just a full day. In some cases ("daily_average" telem_type)
            # the query will span a shorter time since the mnemonic won't change much over
            # a full day.
            self.query_duration = utils.get_query_duration(telem_type)

            # Determine which database tables are needed based on instrument. A telemetry
            # type of "all" indicates that no time-averaging is done, and therefore the
            # data are not stored in the JWQL database (for database table size reasons).
            if telem_type != 'all':
                self.identify_tables(instrument, telem_type)

            # Work on one mnemonic at a time
            for mnemonic in mnemonic_dict[telemetry_kind]:
                logging.info(f'Working on {mnemonic["name"]}')

                # It seems that some mnemonics that were previously in the EDB are no longer
                # present. Check for the existence of the mnemonic before proceeding. If the
                # mnemonic is not present in the EDB, make a note in the log and move on to
                # the next one.
                present_in_edb = ed.get_mnemonic_info(mnemonic["name"])
                if not present_in_edb:
                    logging.info(f'WARNING: {mnemonic["name"]} is not present in the EDB. Skipping')
                    continue  # Move on to the next mnemonic

                create_new_history_entry = True

                # Only two types of plots are currently supported. Plotting the data in the EdbMnemonic
                # directly, and plotting it as the product with a second EdbMnemonic
                if '*' not in mnemonic["plot_data"] and 'nominal' not in mnemonic["plot_data"]:
                    raise NotImplementedError(('The plot_data entry in the mnemonic dictionary can currently only '
                                               'be "nominal" or "*<MNEMONIC_NAME>", indicating that the current '
                                               'mnemonic should be plotted as the product of the mnemonic*<MNEMONIC_NAME>. '
                                               'e.g. for a mnemonic that reports current, plot the data as a power by '
                                               'multiplying with a mnemonic that reports voltage. No other mnemonic '
                                               'combination schemes have been implemented.'))

                # A mnemonic that is being monitored in more than one way will have a secondary name to
                # use for the database, stored in the "database_id" key.
                self._usename = 'name'
                if 'database_id' in mnemonic:
                    self._usename = 'database_id'

                # Construct the mnemonic identifer to be used for database entries and plot titles
                if '*' in mnemonic["plot_data"]:
                    # Define the mnemonic identifier to be <mnemonic_name_1>*<mnemonic_name_2>
                    term2 = mnemonic["plot_data"].split(',')[0]
                    product_identifier = f'{mnemonic[self._usename]}{term2}'
                else:
                    product_identifier = mnemonic[self._usename]

                if telem_type != 'all':
                    # Find the end time of the previous query from the database.
                    most_recent_search = self.most_recent_search(product_identifier)

                    # For daily_means mnemonics, we force the search to always start at noon, and
                    # have a 1 day cadence
                    if telem_type == 'daily_means':
                        most_recent_search = datetime.datetime.combine(most_recent_search.date(), datetime.time(hour=12))

                    logging.info(f'Most recent search is {most_recent_search}.')
                    logging.info(f'Query cadence is {self.query_cadence}')

                    if plot_end > (most_recent_search + self.query_cadence):
                        # Here we need to query the EDB to cover the entire plot range
                        logging.info("Plot range extends outside the time contained in the JWQLDB. Need to query the EDB.")
                        logging.info(f"Plot_end: {plot_end}")
                        logging.info(f"Most recent search: {most_recent_search}")
                        logging.info(f"Search end: {most_recent_search + self.query_cadence}")
                        starttime = most_recent_search + self.query_cadence
                        logging.info(f"New starttime: {starttime}")
                    else:
                        # Here the entire plot range is before the most recent search,
                        # so all we need to do is query the JWQL database for the data.
                        logging.info(f"Plot time span contained entirely in JWQLDB. No need to query EDB.")
                        create_new_history_entry = False
                        starttime = None




                    # SPEED UP TESTING - REMOVE BEFORE MERGING
                    starttime = plot_start



                else:
                    # In the case where telemetry data have no averaging done, we do not store the data
                    # in the JWQL database, in order to save space. So in this case, we will retrieve
                    # all of the data from the EDB directly, from some default start time until the
                    # present day.
                    starttime = plot_start
                    create_new_history_entry = False

                query_start_times, query_end_times = self.generate_query_start_times(starttime)
                logging.info(f'Query start times: {query_start_times}')
                logging.info(f'Query end times: {query_end_times}')

                if telem_type != 'all':
                    if query_start_times is not None:

                        # Query the EDB/JWQLDB, filter by dependencies, and perform averaging
                        new_data = self.multiday_mnemonic_query(mnemonic, query_start_times, query_end_times, telem_type)

                    else:
                        # In this case, all the data needed are already in the JWQLDB, so return an empty
                        # EDBMnemonic instance. This will be combined with the data from the JWQLDB later.
                        info = ed.get_mnemonic_info(mnemonic["name"])
                        new_data = empty_edb_instance(mnemonic[self._usename], plot_start, plot_end, info=info)
                        new_data.mnemonic_identifier = product_identifier
                        logging.info(f'All data needed are already in JWQLDB.')
                        create_new_history_entry = False
                else:
                    # For data where no averaging is done, all data must be retrieved from EDB. They are not
                    # stored in the JWQLDB
                    new_data = self.multiday_mnemonic_query(mnemonic, query_start_times, query_end_times, telem_type)

                # Save the averaged/smoothed data and dates/times to the database, but only for cases where we
                # are averaging. For cases with no averaging the database would get too large too quickly. In
                # that case the monitor will re-query the EDB for the entire history each time.
                if telem_type != "all":

                    # "every_change" data must be treated differently from other types of averaging, since
                    # those mnemonics have their data separated into collections based on the value of a
                    # dependency.
                    if telem_type != 'every_change':

                        # Retrieve the historical data from the database, so that we can add the new data
                        # to it
                        historical_data = self.get_history(new_data.mnemonic_identifier, plot_start, plot_end, info=new_data.info,
                                                           meta=new_data.meta)
                        ending = starttime
                        if ending is None:
                            ending = plot_end
                        historical_data.requested_end_time = ending

                        logging.info(f'Retrieved data from JWQLDB. Number of data points: {len(historical_data)}')

                        # Add the data newly filtered and averaged data retrieved from the EDB to the JWQLDB
                        # If no new data were retrieved from the EDB, then there is no need to add an entry to the JWQLDB
                        if create_new_history_entry:
                            self.add_new_block_db_entry(new_data, query_start_times[-1])
                            logging.info('New data added to the JWQLDB.')
                        else:
                            logging.info("No new data retrieved from EDB, so no new entry added to JWQLDB")

                        # Now add the new data to the historical data
                        mnemonic_info = new_data + historical_data
                        logging.info(f'Combined new data plus historical data contains {len(mnemonic_info)} data points.')
                    else:
                        # "every_change" data is more complex, and requires custom functions
                        # Retrieve the historical data from the database, so that we can add the new data
                        # to it
                        historical_data = self.get_history_every_change(new_data.mnemonic_identifier, plot_start, plot_end)
                        logging.info(f'Retrieved data from JWQLDB. Number of data points per key:')
                        for key in historical_data:
                            logging.info(f'Key: {key}, Num of Points: {len(historical_data[key][0])}')
                        if historical_data == {}:
                            logging.info('No historical data')

                        # Before we can add the every-change data to the database, organize it to make it
                        # easier to access. Note that every_change_data is now a dict rather than an EDBMnemonic instance
                        every_change_data = organize_every_change(new_data)

                        # Add new data to JWQLDB.
                        # If no new data were retrieved from the EDB, then there is no need to add an entry to the JWQLDB
                        if create_new_history_entry:
                            #self.add_new_every_change_db_entry(new_data.mnemonic_identifier, every_change_data, mnemonic['dependency'][0]["name"],
                            #                                   query_start_times[-1])
                            pass     # UNCOMMENT ABOVE BEFORE MERGING
                        else:
                            logging.info("No new data retrieved from EDB, so no new entry added to JWQLDB")

                        # Combine the historical data with the new data from the EDB
                        for key in every_change_data:
                            logging.info(f'Key: {key}, Num of Points: {len(every_change_data[key][0])}')
                        logging.info(f'Total number of points in new_data from the EDB: {len(new_data)}')

                        # Note that the line below will change mnemonic_info into a dictionary
                        mnemonic_info = add_every_change_history(historical_data, every_change_data)

                        logging.info(f'Combined new data plus historical data. Number of data points per key:')
                        for key in mnemonic_info:
                            logging.info(f'Key: {key}, Num of Points: {len(mnemonic_info[key][0])}')

                else:
                    mnemonic_info = new_data

                # For a telemetry_kind that is a combination of all+something, here we work on the "all" part.
                if telemetry_kind in ALLOWED_COMBINATION_TYPES:
                    temp_telem_type = "all"

                    # Query the EDB/JWQLDB, filter by dependencies, and perform averaging
                    full_query_start_times, full_query_end_times = self.generate_query_start_times(self._plot_start)
                    additional_data = self.multiday_mnemonic_query(mnemonic, full_query_start_times, full_query_end_times, temp_telem_type)

                    # Now arrange the data in a way that makes sense. Place the non-averaged data collected above
                    # into self.data, and the averaged data into the self.mean and self.median_times attributes
                    mnemonic_info.mean = mnemonic_info.data["euvalues"].value
                    mnemonic_info.median_times = mnemonic_info.data["dates"].value
                    tmp_table = Table()
                    tmp_table["dates"] = additional_data.data["dates"]
                    tmp_table["euvalues"] = additional_data.data["euvalues"]
                    mnemonic_info.data = tmp_table

                # Create plot
                # If there is a nominal value, or yellow/red limits to be included in the plot, get those here
                nominal = utils.check_key(mnemonic, "nominal_value")
                yellow = utils.check_key(mnemonic, "yellow_limits")
                red = utils.check_key(mnemonic, "red_limits")

                # Make the plot title as useful as possible. Include the description from the input json
                # file. If there is none, fall back to the description from MAST. If that is also not
                # present, then the title will be only the mnemonic name.
                if 'description' in mnemonic:
                    plot_title = f'{new_data.mnemonic_identifier}: {mnemonic["description"]}'
                elif 'description' in new_data.info:
                    plot_title = f'{new_data.mnemonic_identifier}: {new_data.info["description"]}'
                else:
                    plot_title = new_data.mnemonic_identifier

                if telemetry_kind == 'every_change':
                    # For every_change data, the plot is more complex, and we must use the custom
                    # plot_every_change_data() method. Again, return the figure object without saving it.
                    figure = plot_every_change_data(mnemonic_info, new_data.mnemonic_identifier, new_data.info["unit"],
                                                    savefig=False, out_dir=self.plot_output_dir, show_plot=False, return_components=False,
                                                    return_fig=True, title=plot_title, minimal_start=self._plot_start,
                                                    minimal_end=self._plot_end)

                elif telemetry_kind in ALLOWED_COMBINATION_TYPES:
                    figure = mnemonic_info.plot_data_plus_devs(savefig=False, out_dir=self.plot_output_dir, nominal_value=nominal,
                                                               yellow_limits=yellow, red_limits=red, return_components=False,
                                                               return_fig=True, show_plot=False, title=plot_title)
                else:
                    # For telemetry types other than every_change, the data will be contained in an instance of
                    # and EDBMnemonic. In this case, we can create the plot using the bokeh_plot method. The default
                    # behavior is to return the Bokeh figure itself, rather than the script and div. Also, do not
                    # save the figure and return the figure, or else Bokeh will later fail with an error that figure
                    # elements are shared between documents.
                    plot_mean = False
                    plot_median = False
                    plot_max = False
                    plot_min = False
                    plot_parts = mnemonic["plot_data"].split(',')
                    if 'median' in plot_parts:
                        # Assume that we want to plot only one of the mean and median
                        plot_median = True
                        plot_mean = False
                    if 'max' in plot_parts:
                        plot_max = True
                    if 'min' in plot_parts:
                        plot_min = True

                    figure = mnemonic_info.bokeh_plot(savefig=False, out_dir=self.plot_output_dir, nominal_value=nominal,
                                                      yellow_limits=yellow, red_limits=red, return_components=False,
                                                      return_fig=True, show_plot=False, title=plot_title, plot_mean=plot_mean,
                                                      plot_median=plot_median, plot_max=plot_max, plot_min=plot_min)

                # Add the figure to a dictionary that organizes the plots by plot_category
                self.add_figure(figure, mnemonic["plot_category"])

        # Create a tabbed, gridded set of plots for each category of plot, and save as a json file.
        self.tabbed_figure()

    def tabbed_figure(self, ncols=2):
        """Create a tabbed object containing a panel of gridded plots in each tab.

        Parameters
        ----------
        ncols : int
            Number of columns of plots in each plot tab
        """
        panel_list = []
        for key, plot_list in self.figures.items():
            grid = gridplot(plot_list, ncols=ncols, merge_tools=False)

            # Create one panel for each plot category
            panel_list.append(TabPanel(child=grid, title=key))

        # Assign the panels to Tabs
        tabbed = Tabs(tabs=panel_list, tabs_location='left')

        # Save the tabbed plot to a json file
        item_text = json.dumps(json_item(tabbed, "tabbed_edb_plot"))
        basename = f'edb_{self.instrument}_tabbed_plots.json'
        output_file = os.path.join(self.plot_output_dir, basename)
        with open(output_file, 'w') as outfile:
            outfile.write(item_text)
        logging.info(f'JSON file with tabbed plots saved to {output_file}')


def add_every_change_history(dict1, dict2):
    """Combine two dictionaries that contain every change data. For keys that are
    present in both dictionaries, remove any duplicate entries based on date.

    For the every change data at the moment (MIRI), the key values
    are filter names, and the values are data corresponding to those
    filters. The median and stdev values for each filter come from
    MIRI_POS_RATIO_VALUES in constants.py. So for a given filter, it
    is safe (and in fact necessary for plotting purposes) to have only
    a single value for the median, and the same for stdev. So in combining
    the dictionaries, we combine dates and data values, but keep only a
    single value for median and stdev.

    Parameters
    ----------
    dict1 : dict
        First dictionary to combine

    dict2 : dict
        Second dictionary to combine

    Returns
    -------
    combined : collections.defaultdict
        Combined dictionary
    """
    combined = defaultdict(list)

    """
    Looks good
    print('Before combining:')
    print(dict1['F1000W'][0])
    print(dict1['F1000W'][2])
    print('')
    for e in dict1['F1000W'][0]:
        print(e)
    for e in dict1['F1000W'][2]:
        print(e)
    """


    print('dict1 keys: ', dict1.keys())
    print('dict2 keys: ', dict2.keys())





    for key, value in dict1.items():
        all_dates = []
        all_values = []
        all_medians = []
        all_devs = []


        print(key)
        print(type(value))  # tuple
        print(type(value[0]))  # list (of lists)
        print(value[0]) #- list of lists
        print('')
        for v0, v2 in zip(value[0], value[2]):
            print(type(v0), v0)
            print(type(v2), v2)
            print('')
        print('')
        #stop
        #print(type(dict2[key][0]), dict2[key][0])




        if key in dict2:


            #if key == 'OPAQUE':
                #print(dict1[key]) #- tuple(array of times, array of data, list of medians, list of stdevs)


            #print(type(value[0]))
            #print(type(np.array(value[0])))


            #print(np.min(np.array(value[0])))
            #print(np.min(dict2[key][0]))

            min_time_dict1 = min(min(m) for m in value[0])
            if min_time_dict1 < np.min(dict2[key][0]):
                #all_dates = np.append(value[0], dict2[key][0])
                #all_data = np.append(value[1], dict2[key][1])

                all_dates = value[0]
                all_dates.append(list(dict2[key][0]))

                all_values = value[1]
                all_values.append(list(dict2[key][1]))

                all_medians = value[2]
                all_medians.append(list(dict2[key][2]))

                all_devs = value[3]
                all_devs.append(list(dict2[key][3]))

                #all_medians = np.append(value[2], dict2[key][2])
                #all_devs = np.append(value[3], dict2[key][3])
            else:
                # Seems unlikely we'll ever want to be here. This would be
                # for a case where a given set of values has an earliest date
                # that is earlier than anything in the database.
                #all_dates = np.append(dict2[key][0], value[0])
                #all_data = np.append(dict2[key][1], value[1])
                #all_medians = np.append(dict2[key][2], value[2])
                #all_devs = np.append(dict2[key][3], value[3])
                all_dates = [list(dict2[key][0])]
                all_dates.extend(value[0])

                all_values = [list(dict2[key][1])]
                all_values.extend(value[1])

                all_medians = [list(dict2[key][2])]
                all_medians.extend(value[2])

                all_devs = [list(dict2[key][3])]
                all_devs.extend(value[3])

            # Remove any duplicates
            #unique_dates, unique_idx = np.unique(all_dates, return_index=True)
            #all_dates = all_dates[unique_idx]
            #all_data = all_data[unique_idx]

            # Not sure how to treat duplicates here. If we remove duplicates, then
            # the mean values may not be valid any more. For example, if there is a
            # 4 hour overlap, but each mean is for a 24 hour period. We could remove
            # those 4 hours of entries, but then what would we do with the mean values
            # that cover those times. Let's instead warn the user if there are duplicate
            # entries, but don't take any action
            #unique_dates = np.unique(all_dates, return_index=False)
            #if len(unique_dates) != len(all_dates):
            #    n_duplicates = len(unique_dates) != len(all_dates)
            #    logging.info((f"WARNING - There are {n_duplicates} duplicate entries in the "
            #                  f"every-change history (total length {value[0]}) and the new entry "
            #                  f"(total length {dict2[key][0]}). Keeping and plotting all values, "
            #                  "but be sure the data look ok."))
            updated_value = (all_dates, all_values, all_medians, all_devs)
            combined[key] = updated_value
        else:
            if key == 'OPAQUE':
                print(key)
                print(value[0])
                print(value[1])
                print(value[2])
                print(value[3])
                stop
            print(key)
            print(value)
            #stop
            combined[key] = value

        if key == 'OPAQUE':
            print('before dict2 only keys:')
            for e in combined[key][0]:
                print(e)
                print('')
            print('')
            for e in combined[key][2]:
                print(e)
                print('')
            print('')
            #stop




        logging.info(f'In add_every_change_history: key: {key}, len data: {len(all_dates)}, median: {all_medians}, dev: {all_devs}')
    # Add entries for keys that are in dict2 but not dict1
    for key, value in dict2.items():
        if key not in dict1:
            #combined[key] = value
            dates =[]
            vals = []
            meds = []
            devs = []
            dates.append(list(value[0]))
            vals.append(list(value[1]))
            meds.append(list(value[2]))
            devs.append(list(value[3]))
            combined[key] = (dates, vals, meds, devs)


        logging.info(f'dict2 only add_every_change_history: key: {key}, len data: {len(value[0])}, median: {dict2[key][2]}, dev: {dict2[key][3]}')


    #print('after dict2 only keys:')
    #for e in combined['F1000W'][0]:
    #    print(e)
    #print('')
    #for e in combined['F1000W'][2]:
    #    print(e)
    return combined


def calculate_statistics(mnemonic_instance, telemetry_type):
    """Wrapper function around the various methods that can be used to calculate mean/median/
    stdev values for a given mnemonic. The method used depends on the type of telemetry.

    Parameters
    ----------
    mnemonic_instance : jwql.edb.engineering_database.EdbMnemonic
        EdbMnemonic instance containing the telemetry data to be averaged.

    telemetry_type : str
        Type of telemetry. Examples include "daily", "every_change", "all". These values
        come from the top-level json file that lists the mnemonics to be monitored.

    Returns
    -------
    mnemonic_instance : jwql.edb.engineering_database.EdbMnemonic
        Modified EdbMnemonic instance with the "mean", "median", and "stdev" attributes
        populated.
    """
    if telemetry_type == "daily_means":
        mnemonic_instance.daily_stats()
    elif telemetry_type == "block_means":
        mnemonic_instance.block_stats()
    elif telemetry_type == "every_change":
        mnemonic_instance.block_stats_filter_positions()
        # mnemonic_instance.block_stats(ignore_vals=[0.], ignore_edges=True, every_change=True)
    elif telemetry_type == "time_interval":
        mnemonic_instance.timed_stats()
    elif telemetry_type == "all":
        mnemonic_instance.full_stats()
    return mnemonic_instance


def define_options(parser=None, usage=None, conflict_handler='resolve'):
    if parser is None:
        parser = argparse.ArgumentParser(usage=usage, conflict_handler=conflict_handler)

    parser.add_argument('--mnem_to_query', type=str, default=None, help='Mnemonic to query for')
    parser.add_argument('--plot_start', type=str, default=None, help='Start time for EDB monitor query. Expected format: "2022-10-31"')
    parser.add_argument('--plot_end', type=str, default=None, help='End time for EDB monitor query. Expected format: "2022-10-31"')
    return(parser)


def empty_edb_instance(name, beginning, ending, meta={}, info={}):
    """Create an EdbMnemonic instance with an empty data table

    Parameters
    ----------
    name : str
        Name of mnemonic to attach to the empty EdbMnemonic instance

    beginning : datetime.datetime
        Starting time value associated with empty instance

    ending : datetime.datetime
        Ending time value associated with empty instance

    meta : dict
        Meta data dictionary to attach to meta attribute

    info : dict
        Info dictionary to attach to info attribute

    Returns
    -------
    var : jwql.edb.engineering_database.EdbMnemonic
        Empty instance of EdbMnemonic
    """
    tab = Table()
    tab["dates"] = []
    tab["euvalues"] = []
    return ed.EdbMnemonic(name, beginning, ending, tab, meta, info)


def ensure_list(var):
    """Be sure that var is a list. If not, make it one.

    Parameters
    ----------
    var : list or str or float or int
        Variable to be checked

    Returns
    -------
    var : list
        var, translated into a list if necessary
    """
    if not isinstance(var, list) and not isinstance(var, np.ndarray):
        return [var]
    else:
        return var


def organize_every_change(mnemonic):
    """Given an EdbMnemonic instance containing every_change data,
    organize the information such that there are single 1d arrays
    of data and dates for each of the dependency values. This will
    make plotting and saving in the database much more straight
    forward. Note that this is intended to be run on an EdbMnenonic
    instance that has come out of multiday_mnemonic_query, so that
    the data table contains averaged values. In this case, the
    data in the data table will line up with the values given in
    the every_change_values attribute.

    Parameters
    ----------
    mnemonic : jwql.edb.engineering_database.EdbMnemonic
        Object containing all data

    Returns
    -------
    all_data : dict
        Dictionary of organized results. Keys are the dependency values,
        and values are tuples. The first element of each tuple is a list
        of dates, the second element is a list of data values, and the third
        is a the sigma-clipped mean value of the data.
    """
    all_data = {}

    # If the input mnemonic is empty, return an empty dictionary
    if len(mnemonic) == 0:
        return all_data

    unique_vals = np.unique(mnemonic.every_change_values)

    if not isinstance(mnemonic.every_change_values, np.ndarray):
        every_change = np.array(mnemonic.every_change_values)
    else:
        every_change = mnemonic.every_change_values

    # For each dependency value, pull out the corresponding mnemonic values and times.
    for val in unique_vals:
        good = np.where(every_change == str(val))[0]  # val is np.str_ type. need to convert to str
        val_times = mnemonic.data["dates"].data[good]
        val_data = mnemonic.data["euvalues"].data[good]

        # Normalize by the expected value
        medianval, stdevval = MIRI_POS_RATIO_VALUES[mnemonic.mnemonic_identifier.split('_')[2]][val]

        all_data[val] = (val_times, val_data, [medianval], [stdevval])

    return all_data


def plot_every_change_data(data, mnem_name, units, show_plot=False, savefig=True, out_dir='./', nominal_value=None, yellow_limits=None,
                           red_limits=None, xrange=(None, None), yrange=(None, None), title=None, return_components=True, return_fig=False,
                           minimal_start=None, minimal_end=None):
    """Create a plot for mnemonics where we want to see the behavior within
    each change

    Parameters
    ----------
    data : collections.defaultdict
        Dictionary containing every_change data to be plotted. Keys should be the values of the
        dependency mnemonic, and values should be 3-tuples (list of datetimes, list of data,
        mean value)

    mnem_name : str
        Name of the mnemonic being plotted. This will be used to generate a filename in the
        case where the figure is saved.

    units : astropy.units.unit
        Units associated with the data. This will be used as the y-axis label in the plot

    show_plot : bool
        If True, show plot on screen rather than returning div and script

    savefig : bool
        If True, file is saved to html file

    out_dir : str
        Directory into which the html file is saved

    nominal_value : float
        Expected or nominal value for the telemetry. If provided, a horizontal dashed line
        at this value will be added.

    yellow_limits : list
        2-element list giving the lower and upper limits outside of which the telemetry value
        is considered non-nominal. If provided, the area of the plot between these two values
        will be given a green background, and that outside of these limits will have a yellow
        background.

    red_limits : list
        2-element list giving the lower and upper limits outside of which the telemetry value
        is considered worse than in the yellow region. If provided, the area of the plot outside
        of these two values will have a red background.

    xrange : tuple
        Tuple of min, max datetime values to use as the plot range in the x direction.

    yrange : tuple
        Tuple of min, max datetime values to use as the plot range in the y direction.

    title : str
        Will be used as the plot title. If None, mnem_name will be used as the title

    return_components : bool
        If True, the components (script, div) of the figure will be returned

    return_fig : bool
        If True, the Bokeh figure will be returned

    minimal_start : datetime.datetime
        In the case where the data to be plotted consists of no or only one point, use this
        as the earliest date in the plot

    minimal_end : datetime.datetime
        In the case where the data to be plotted consists of no or only one point, use this
        as the latest date in the plot

    Returns
    -------
    obj : list or bokeh.plotting.figure
        If return_components is True, returned object will be a list of [div, script]
        If return_figure is True, a bokeh.plotting.figure will be returned

    """
    # Make sure that only one output type is specified, or bokeh will get mad
    options = np.array([show_plot, savefig, return_components, return_fig])
    if np.sum(options) > 1:
        trues = np.where(options)[0]
        raise ValueError((f'{options[trues]} are set to True in plot_every_change_data. Bokeh '
                          'will only allow one of these to be True.'))

    # Create a useful plot title if necessary
    if title is None:
        title = mnem_name

    # yellow and red limits must come in pairs
    if yellow_limits is not None:
        if len(yellow_limits) != 2:
            yellow_limits = None
    if red_limits is not None:
        if len(red_limits) != 2:
            red_limits = None

    # Create figure
    fig = figure(tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type='datetime',
                 title=title, x_axis_label='Time', y_axis_label=f'{units}')

    if savefig:
        filename = os.path.join(out_dir, f"telem_plot_{mnem_name.replace(' ', '_')}.html")
        logging.info(f'Saving plot to: {filename}')

    colors = [int(len(Turbo256) / len(data)) * e for e in range(len(data))]

    # Find the min and max values in the x-range. These may be used for plotting
    # the nominal_value line later. Initialize here, and then dial them in based
    # on the data.
    min_time = datetime.datetime.today()
    max_time = datetime.datetime(2021, 12, 25)

    logging.info('In plot_every_change_data:')
    for (key, value), color in zip(data.items(), colors):
        if len(value) > 0:
            val_times, val_data, normval, stdevval = value

            print(key)
            print(value)

            print('in plotting code')
            print('val_times is:')
            print(val_times)
            print('\n')
            print('normval is:')
            print(normval)
            print('')

            # At this point, val_times and val_data will be a list of numpy arrays
            # normval and stdevval will be lists. First, iterate through the lists
            # and normalize the data values in each element by the corresponding
            # normval (expected value)
            all_val_data = []
            all_val_times = []

            print('val_data:')
            print(val_data)
            print('')

            for time_ele, data_ele, norm_ele in zip(val_times, val_data, normval):


                print(data_ele)
                print('')
                print(time_ele)
                print('\n\n')



                if type(data_ele[0]) not in [np.str_, str]:


                    print(type(data_ele), data_ele)
                    print(type(norm_ele), norm_ele)

                    data_ele_arr = np.array(data_ele) / norm_ele[0]
                    #data_ele /= norm_ele[0]
                    all_val_data.extend(list(data_ele_arr))
                    all_val_times.extend(time_ele)
                    logging.info(f'key: {key}, len_data: {len(data_ele)}, firstentry: {data_ele[0]}, stats: {norm_ele}')

            all_val_data = np.array(all_val_data)
            all_val_times = np.array(all_val_times)
            dependency_val = np.repeat(key, len(all_val_times))
            #val_data = np.array(val_data)
            #dependency_val = np.repeat(key, len(val_times))

            # Normalize by normval (the expected value) so that all data will fit on one plot easily
            #if type(val_data[0]) not in [np.str_, str]:
            #    logging.info(f'key: {key}, len_data: {len(val_data)}, firstentry: {val_data[0]}, stats: {normval}, {stdevval}')
            #    val_data /= normval

            source = ColumnDataSource(data={'x': all_val_times, 'y': all_val_data, 'dep': dependency_val})

            ldata = fig.line(x='x', y='y', line_width=1, line_color=Turbo256[color], source=source, legend_label=key)
            cdata = fig.circle(x='x', y='y', fill_color=Turbo256[color], size=8, source=source, legend_label=key)

            hover_tool = HoverTool(tooltips=[('Value', '@dep'),
                                             ('Data', '@y{1.11111}'),
                                             ('Date', '@x{%d %b %Y %H:%M:%S}')
                                             ], mode='mouse', renderers=[cdata])
            hover_tool.formatters = {'@x': 'datetime'}
            fig.tools.append(hover_tool)

            if np.min(all_val_times) < min_time:
                min_time = np.min(all_val_times)
            if np.max(all_val_times) > max_time:
                max_time = np.max(all_val_times)

    # If the input dictionary is empty, then create an empty plot with reasonable
    # x range
    if len(data.keys()) == 0:
        null_dates = [minimal_start, minimal_end]
        source = ColumnDataSource(data={'x': null_dates, 'y': [0, 0], 'dep': ['None', 'None']})
        ldata = fig.line(x='x', y='y', line_width=1, line_color='black', source=source, legend_label='None')
        ldata.visible = False
        totpts = 0
    else:
        numpts = [len(val) for key, val in data.items()]
        totpts = np.sum(np.array(numpts))

    # For a plot with zero or one point, set the x and y range to something reasonable
    if totpts < 2:
        fig.x_range = Range1d(minimal_start - datetime.timedelta(days=1), minimal_end)
        bottom, top = (-1, 1)
        if yellow_limits is not None:
            bottom, top = yellow_limits
        if red_limits is not None:
            bottom, top = red_limits
        fig.y_range = Range1d(bottom, top)

    # If there is a nominal value provided, plot a dashed line for it
    if nominal_value is not None:
        fig.line([min_time, max_time], [nominal_value, nominal_value], color='black',
                 line_dash='dashed', alpha=0.5)

    # If limits for warnings/errors are provided, create colored background boxes
    if yellow_limits is not None or red_limits is not None:
        fig = add_limit_boxes(fig, yellow=yellow_limits, red=red_limits)

    # Make the x axis tick labels look nice
    fig.xaxis.formatter = DatetimeTickFormatter(microseconds="%d %b %H:%M:%S.%3N",
                                                seconds="%d %b %H:%M:%S.%3N",
                                                hours="%d %b %H:%M",
                                                days="%d %b %H:%M",
                                                months="%d %b %Y %H:%M",
                                                years="%d %b %Y"
                                                )
    fig.xaxis.major_label_orientation = np.pi / 4

    # Force the axes' range if requested
    if xrange[0] is not None:
        fig.x_range.start = xrange[0].timestamp() * 1000.
    if xrange[1] is not None:
        fig.x_range.end = xrange[1].timestamp() * 1000.
    if yrange[0] is not None:
        fig.y_range.start = yrange[0]
    if yrange[1] is not None:
        fig.y_range.end = yrange[1]

    fig.legend.location = "top_left"
    fig.legend.click_policy = "hide"

    if savefig:
        output_file(filename=filename, title=mnem_name)
        save(fig)
        set_permissions(filename)

    if show_plot:
        show(fig)
    if return_components:
        script, div = components(fig)
        return [div, script]
    if return_fig:
        return fig


if __name__ == '__main__':
    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)

    parser = define_options()
    args = parser.parse_args()

    plot_start_dt = None
    plot_end_dt = None
    if args.plot_start is not None:
        plot_start_dt = datetime.datetime.strptime(args.plot_start, '%Y-%m-%d')
    if args.plot_end is not None:
        plot_end_dt = datetime.datetime.strptime(args.plot_end, '%Y-%m-%d')

    monitor = EdbMnemonicMonitor()
    monitor.execute(args.mnem_to_query, plot_start_dt, plot_end_dt)
    monitor_utils.update_monitor_table(module, start_time, log_file)
