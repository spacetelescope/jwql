#! /usr/bin/env python

"""Module for dealing with JWST DMS Engineering Database mnemonics.

This module provides ``jwql`` with convenience classes and functions
to retrieve and manipulate mnemonics from the JWST DMS EDB. It uses
the ``engdb_tools`` module of the ``jwst`` package to interface the
EDB directly.

Authors
-------

    - Johannes Sahlmann
    - Mees Fix

Use
---

    This module can be imported and used with

    ::

        from jwql.edb.engineering_database import get_mnemonic
        get_mnemonic(mnemonic_identifier, start_time, end_time)

    Required arguments:

    ``mnemonic_identifier`` - String representation of a mnemonic name.
    ``start_time`` - astropy.time.Time instance
    ``end_time`` - astropy.time.Time instance

Notes
-----
    There are two possibilities for MAST authentication:

    1. A valid MAST authentication token is present in the local
    ``jwql`` configuration file (config.json).
    2. The MAST_API_TOKEN environment variable is set to a valid
    MAST authentication token.

    When querying mnemonic values, the underlying MAST service returns
    data that include the datapoint preceding the requested start time
    and the datapoint that follows the requested end time.
"""
import calendar
from collections import OrderedDict
from datetime import datetime, timedelta
import warnings

from astropy.stats import sigma_clipped_stats
from astropy.table import Table
from astropy.time import Time
import astropy.units as u
from astroquery.mast import Mast
from bokeh.embed import components
from bokeh.plotting import figure, show
import numpy as np

from jwst.lib.engdb_tools import ENGDB_Service
from jwql.utils.credentials import get_mast_base_url, get_mast_token

MAST_EDB_MNEMONIC_SERVICE = 'Mast.JwstEdb.Mnemonics'
MAST_EDB_DICTIONARY_SERVICE = 'Mast.JwstEdb.Dictionary'


class EdbMnemonic:
    """Class to hold and manipulate results of DMS EngDB queries."""

    def __init__(self, mnemonic_identifier, start_time, end_time, data, meta, info, blocks=None):
        """Populate attributes.

        Parameters
        ----------
        mnemonic_identifier : str
            Telemetry mnemonic identifier
        start_time : astropy.time.Time instance
            Start time
        end_time : astropy.time.Time instance
            End time
        data : astropy.table.Table
            Table representation of the returned data.
        meta : dict
            Additional information returned by the query
        info : dict
            Auxiliary information on the mnemonic (description,
            category, unit)
        blocks : list
            Index numbers corresponding to the beginning of separate blocks
            of data. This can be used to calculate separate statistics for
            each block.

        """

        self.mnemonic_identifier = mnemonic_identifier
        self.requested_start_time = start_time
        self.requested_end_time = end_time
        self.data = data

        if len(self.data) == 0:
            self.data_start_time = None
            self.data_end_time = None
        else:
            self.data_start_time = Time(np.min(self.data['dates']), scale='utc')
            self.data_end_time = Time(np.max(self.data['dates']), scale='utc')

        self.meta = meta
        self.info = info
        self.blocks = blocks

    def __add__(self, mnem):
        """Allow EdbMnemonic instances to be added (i.e. combine their data).
        info and metadata will not be touched. Data will be updated. Duplicate
        rows due to overlapping dates will be removed. The overlap is assumed to
        be limited to a single section of the end of once EdbMnemonic instance and
        the beginning of the other instance. Either one of the two instances to be
        added can contain the earlier dates. The function will check the starting
        date of each instance and treat the earlier starting date as the instance
        that is first. Blocks will be updated to account for removed duplicate rows.

        Parameters
        ----------
        mnem : jwql.edb.engineering_database.EdbMnemonic
            Instance to be added to the current instance
        """
        #new_tab = vstack([self.data, mnem.data])
        if np.min(self.data["dates"]) < np.min(mnem.data["dates"]):
            early_dates = self.data["dates"].data
            late_dates = mnem.data["dates"].data
            early_data = self.data["euvalues"].data
            late_data = mnem.data["euvalues"].data
            early_blocks = self.blocks
            late_blocks = mnem.blocks
        else:
            early_dates = mnem.data["dates"].data
            late_dates = self.data["dates"].data
            early_data = mnem.data["euvalues"].data
            late_data = self.data["euvalues"].data
            early_blocks = mnem.blocks
            late_blocks = self.blocks

        # Remove any duplicates, based on the dates entries
        # Keep track of the indexes of the removed rows, so that any blocks
        # information can be updated
        all_dates = np.append(early, late)
        unique_dates, unq_idx = np.unique(all_dates, return_index=True)

        # Combine the data and keep only unique elements
        all_data = np.append(early_data, late_data)
        unique_data = all_data[unq_idx]

        # This assumes that if there is overlap between the two date arrays, that
        # the overlap all occurs in a single continuous block at the beginning of
        # the later set of dates. It will not do the right thing if you ask it to
        # (e.g.) interleave two sets of dates.
        overlap_len = len(unique_times) - len(all_dates)

        # Shift the block values for the later instance to account for any removed
        # duplicate rows
        if late_blocks is not None:
            new_late_blocks = late_blocks - overlap_len
            if early_blocks is None:
                new_blocks = new_late_blocks
            else:
                new_blocks = np.append(early_blocks, new_late_blocks)
        else:
            if early_blocks is not None:
                new_blocks = early_blocks
            else:
                new_blocks = None

        self.data = Table([unique_dates, unique_data], names=('dates', 'euvalues'))
        self.blocks = new_blocks

        self.data_start_time = Time(np.min(self.data['dates']), scale='utc')
        self.data_end_time = Time(np.max(self.data['dates']), scale='utc')

    def __mul__(self, mnem):
        """Allow EdbMnemonic instances to be multiplied (i.e. combine their data).
        info will be updated with new units if possible. Data will be updated.
        Blocks will not be updated, under the assumption that the times in self.data
        will all be kept, and therefore self.blocks will remain correct after
        multiplication.

        Parameters
        ----------
        mnem : jwql.edb.engineering_database.EdbMnemonic
            Instance to be added to the current instance
        """
        # First, interpolate the data in mnem onto the same times as self.data
        interp_mnem = mnem.interpolate(self, self.data["dates"])
        self.data["euvalues"] = self.data["euvalues"] * interp_mnem.data["euvalues"]
        combined_unit = (u.Unit(self.info['unit']) * u.Unit(mnem.unit['unit'])).compose()[0]
        self.info['unit'] = f'{combined_unit}'
        self.info['tlmMnemonic'] = f'{self.info['tlmMnemonic']} * {mnem.info['tlmMnemonic']}'
        self.info['description'] = f'({self.info['description']}) * ({mnem.info['description']})'

    def __str__(self):
        """Return string describing the instance."""
        return 'EdbMnemonic {} with {} records between {} and {}'.format(
            self.mnemonic_identifier, len(self.data), self.data_start_time.isot,
            self.data_end_time.isot)

    def block_stats(self, mnem_data, sigma=3):
        """Calculate stats for a mnemonic where we want a mean value for
        each block of good data, where blocks are separated by times where
        the data are ignored.

        Parameters
        ----------
        sigma : int
            Number of sigma to use for sigma clipping
        """
        means = []
        medians = []
        stdevs = []
        medtimes = []
        for i, index in enumerate(self.blocks[0:-1]):
            meanval, medianval, stdevval = sigma_clipped_stats(self.data["euvalues"][index:mnem_data.blocks[i+1]], sigma=sigma)
            medtimes.append(calc_median_time(self.data["dates"][index:mnem_data.blocks[i+1]]))
            #medtimes.append(np.median(self.data["dates"][index:mnem_data.blocks[i+1]]))

        #    OR:
        #for time_tup in mnem_data.time_pairs:
        #    good = np.where((mnem_data.data["MJD"] >= time_tup[0]) & (mnem_data.data["MJD"] < time_tup[1]))
        #    meanval, medianval, stdevval = sigma_clipped_stats(mnem_data.data["data"][good], sigma=sigma)
        #    medtimes.append(np.median(mnem_data.data["MJD"][good]))

            means.append(meanval)
            medians.append(medianval)
            stdevs.append(stdevval)
        self.mean = means
        self.median = medians
        self.stdev = stdevs
        self.median_time = medtimes
        return mnem_data

    def daily_stats(self, sigma=3):
        """Calculate the statistics for each day in the data
        contained in data["data"]. Should we add a check for a
        case where the final block of time is <<1 day?

        Parameters
        ----------
        sigma : int
            Number of sigma to use for sigma clipping

        AS IS BELOW, THIS WILL IGNORE ANY PARTIAL DAYS! SHOULD WE
        UPDATE TO INCLUDE THE CALCULATIONS FOR THOSE? E.G. AS-IS,
        IF YOU HAVE 23 HOURS WORTH OF DATA, THIS FUNCTION WILL NOT
        CALCULATE ANYTHING. OR IF YOU HAVE 24+23 HOURS OF DATA, IT WILL
        ONLY CALCULATE STATS FOR THE FIRST 24 HOUR PERIOD.
        """
        min_date = np.min(self.data["dates"])
        num_days = (np.max(self.data["dates"]) - min_date).days

        # If all the data are within a day, set num_days=1 in order to get
        # a starting and ending time within limits below
        if num_days == 0:
            num_days = 1

        limits = np.array([min_date + timedelta(days=x) for x in range(num_days+1)])
        means, meds, devs, times = [], [], [], []
        for i in range(len(limits) - 1):
            good = np.where((self.data["dates"] >= limits[i]) & (self.data["dates"] < limits[i+1]))
            avg, med, dev = sigma_clipped_stats(self.data["euvalues"][good], sigma=sigma)
            means.append(avg)
            meds.append(med)
            devs.append(dev)
            times.append(limits[i] + (limits[i+1] - limits[i]) / 2.)
        self.mean = means
        self.median = meds
        self.stdev = devs
        self.median_times = times

    def full_stats(self, sigma=3):
        """Calculate the mean/median/stdev of the data

        Parameters
        ----------
        sigma : int
            Number of sigma to use for sigma clipping

        move this to be an attribute of EdbMnemonic class
        """
        self.mean, self.median, self.stdev = sigma_clipped_stats(self.data["euvalues"], sigma=sigma)
        self.median_time = calc_median_time(self.data["dates"])

    def interpolate(self, times):
        """Interpolate data euvalues at specified datetimes.

        Parameters
        ----------
        times : list
            List of datetime objects describing the times to interpolate to
        """
        new_tab = Table()
        interp_times = np.array([create_time_offset(ele, self.data["dates"][0]) for ele in times])
        mnem_times = np.array([create_time_offset(ele, self.data["dates"][0]) for ele in self.data["dates"]])

        # Do not extrapolate. Any requested interoplation times that are outside the range
        # or the original data will be ignored.
        good_times = ((interp_times >= mnem_times[0]) & (interp_times <= mnem_times[-1]))
        interp_times = interp_times[good_times]

        new_tab["euvalues"] = np.interp(interp_times, mnem_times, self.data["euvalues"])
        new_tab["dates"] = np.array([add_time_offset(ele, self.data["dates"][0]) for ele in interp_times])
        self.data = new_tab

        # Adjust any block values to account for the interpolated data
        new_blocks = []
        if self.blocks is not None:
            for index in self.blocks:
                good = np.where(interp_times >= mnem_times[index])[0]
                if len(good) > 0:
                    new_blocks.append(good[0])
            self.blocks = np.array(new_blocks)

    """
    def bokeh_plot(self, show_plot=False):
        Make basic bokeh plot showing value as a function of time.

        Returns
        -------
        [div, script] : list
            List containing the div and js representations of figure.


        abscissa = self.data['dates']
        ordinate = self.data['euvalues']

        p1 = figure(tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type='datetime',
                    title=self.mnemonic_identifier, x_axis_label='Time',
                    y_axis_label='Value ({})'.format(self.info['unit']))
        p1.line(abscissa, ordinate, line_width=1, line_color='blue', line_dash='dashed')
        p1.circle(abscissa, ordinate, color='blue')

        if show_plot:
            show(p1)
        else:
            script, div = components(p1)

            return [div, script]
        """


    def bokeh_plot(self, show_plot=False, save=False, out_dir='./', nominal_value=None, yellow_limits=None, red_limts=None):
        """Make basic bokeh plot showing value as a function of time.
        Paramters
        ---------
        show_plot : bool
            If True, show plot on screen rather than returning div and script

        save : bool
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

        Returns
        -------
        [div, script] : list
            List containing the div and js representations of figure.
        """
        if save:
            output_file(os.path.join(out_dir, f"telem_plot_{name}.html"))

        fig = figure(tools='pan,box_zoom,reset,wheel_zoom,save,hover', x_axis_type='datetime',
                    title=self.mnemonic_identifier, x_axis_label='Time',
                    y_axis_label=f'Value ({self.info["unit"]})')
        fig.line(self.data['dates'], self.data['euvalues'], line_width=1, line_color='blue')
        fig.circle(self.data['dates'], self.data['euvalues'], color='blue', alpha=0.5)

        # If there is a nominal value provided, plot a dashed line for it
        if nominal_value is not None:
            fig.line(self.data['dates'], np.repeat(nominal_value, len(self.data['dates'])), color='black',
                     line_dash='dashed', alpha=0.5)

        # If limits for warnings/errors are provided, create colored background boxes
        if yellow_limits is not None or red_limits is not None:
            fig = add_limit_boxes(fig, yellow=yellow_limits, red=red_limits)

        # Make the x axis tick labels look nice
        fig.xaxis.formatter=DatetimeTickFormatter(
                    hours=["%d %b %H:%M"],
                    days=["%d %b %H:%M"],
                    months=["%d %b %Y %H:%M"],
                    years=["%d %b %Y"]
                )
        fig.xaxis.major_label_orientation = np.pi/4

        if show_plot:
            show(p1)
        else:
            script, div = components(p1)
            return [div, script]

def add_time_offset(offset, dt_obj):
    """Add an offset to an input datetime object

    Parameters
    ----------
    offset : float
        Number of seconds to be added

    dt_obj : datetime.datetime
        Datetime object to which the seconds are added

    Returns
    -------
    obj : datetime.datetime
        Sum of the input datetime objects and the offset seconds.
    """
    return dt_obj + timedelta(seconds=offset)


def calc_median_time(time_arr):
    """Calcualte the median time of the input time_arr

    Parameters
    ----------
    time_arr : numpy.ndarray
        1D array of datetime objects

    Returns
    -------
    med_time : datetime.datetime
        Median time, as a datetime object
    """
    offsets = np.array([create_time_offset(ele, time_arr[0]) for ele in time_arr])
    med = np.median(offsets)
    med_time = add_time_offset(med, time_arr[0])
    return med_time


def create_time_offset(dt_obj, epoch):
    """Subtract input epoch from a datetime object and return the
    residual number of seconds

    Paramters
    ---------
    dt_obj : datetime.datetime
        Original datetiem object

    epoch : datetime.datetime
        Datetime to be subtracted from dt_obj

    Returns
    -------
    obj : float
        Number of seconds between dt_obj and epoch
    """
    return (dt_obj - epoch).total_seconds()


def get_mnemonic(mnemonic_identifier, start_time, end_time):
    """Execute query and return a ``EdbMnemonic`` instance.

    The underlying MAST service returns data that include the
    datapoint preceding the requested start time and the datapoint
    that follows the requested end time.

    Parameters
    ----------
    mnemonic_identifier : str
        Telemetry mnemonic identifiers, e.g. ``SA_ZFGOUTFOV``
    start_time : astropy.time.Time instance
        Start time
    end_time : astropy.time.Time instance
        End time

    Returns
    -------
    mnemonic : instance of EdbMnemonic
        EdbMnemonic object containing query results
    """

    base_url = get_mast_base_url()

    service = ENGDB_Service(base_url)  # By default, will use the public MAST service.
    data = service.get_values(mnemonic_identifier, start_time, end_time, include_obstime=True)
    meta = service.get_meta(mnemonic_identifier)

    dates = [datetime.strptime(row.obstime.iso, "%Y-%m-%d %H:%M:%S.%f") for row in data]
    values = [row.value for row in data]

    data = Table({'dates': dates, 'euvalues': values})
    info = get_mnemonic_info(mnemonic_identifier)

    # create and return instance
    mnemonic = EdbMnemonic(mnemonic_identifier, start_time, end_time, data, meta, info)
    return mnemonic


def get_mnemonics(mnemonics, start_time, end_time):
    """Query DMS EDB with a list of mnemonics and a time interval.

    Parameters
    ----------
    mnemonics : list or numpy.ndarray
        Telemetry mnemonic identifiers, e.g. ``['SA_ZFGOUTFOV',
        'IMIR_HK_ICE_SEC_VOLT4']``
    start_time : astropy.time.Time instance
        Start time
    end_time : astropy.time.Time instance
        End time

    Returns
    -------
    mnemonic_dict : dict
        Dictionary. keys are the queried mnemonics, values are
        instances of EdbMnemonic

    """

    if not isinstance(mnemonics, (list, np.ndarray)):
        raise RuntimeError('Please provide a list/array of mnemonic_identifiers')

    mnemonic_dict = OrderedDict()
    for mnemonic_identifier in mnemonics:
        # fill in dictionary
        mnemonic_dict[mnemonic_identifier] = get_mnemonic(mnemonic_identifier, start_time, end_time)

    return mnemonic_dict


def get_mnemonic_info(mnemonic_identifier):
    """Return the mnemonic description.

    Parameters
    ----------
    mnemonic_identifier : str
        Telemetry mnemonic identifier, e.g. ``SA_ZFGOUTFOV``

    Returns
    -------
    info : dict
        Object that contains the returned data
    """

    mast_token = get_mast_token()
    return query_mnemonic_info(mnemonic_identifier, token=mast_token)


def is_valid_mnemonic(mnemonic_identifier):
    """Determine if the given string is a valid EDB mnemonic.

    Parameters
    ----------
    mnemonic_identifier : str
        The mnemonic_identifier string to be examined.

    Returns
    -------
    bool
        Is mnemonic_identifier a valid EDB mnemonic?
    """

    inventory = mnemonic_inventory()[0]
    if mnemonic_identifier in inventory['tlmMnemonic']:
        return True
    else:
        return False


def mnemonic_inventory():
    """Return all mnemonics in the DMS engineering database.
    No authentication is required, this information is public.
    Since this is a rather large and quasi-static table (~15000 rows),
    it is cached using functools.

    Returns
    -------
    data : astropy.table.Table
        Table representation of the mnemonic inventory.
    meta : dict
        Additional information returned by the query.
    """

    out = Mast.service_request_async(MAST_EDB_MNEMONIC_SERVICE, {})
    data, meta = process_mast_service_request_result(out)

    # convert numerical ID to str for homogenity (all columns are str)
    data['tlmIdentifier'] = data['tlmIdentifier'].astype(str)

    return data, meta


def process_mast_service_request_result(result, data_as_table=True):
    """Parse the result of a MAST EDB query.

    Parameters
    ----------
    result : list of requests.models.Response instances
        The object returned by a call to ``Mast.service_request_async``
    data_as_table : bool
        If ``True``, return data as astropy table, else return as json

    Returns
    -------
    data : astropy.table.Table
        Table representation of the returned data.
    meta : dict
        Additional information returned by the query
    """

    json_data = result[0].json()
    if json_data['status'] != 'COMPLETE':
        raise RuntimeError('Mnemonic query did not complete.\nquery status: {}\nmessage: {}'.format(
            json_data['status'], json_data['msg']))

    try:
        # timestamp-value pairs in the form of an astropy table
        if data_as_table:
            data = Table(json_data['data'])
        else:
            data = json_data['data'][0]
    except KeyError:
        warnings.warn('Query did not return any data. Returning None')
        return None, None

    # collect meta data
    meta = {}
    for key in json_data.keys():
        if key.lower() != 'data':
            meta[key] = json_data[key]

    return data, meta


def query_mnemonic_info(mnemonic_identifier, token=None):
    """Query the EDB to return the mnemonic description.

    Parameters
    ----------
    mnemonic_identifier : str
        Telemetry mnemonic identifier, e.g. ``SA_ZFGOUTFOV``
    token : str
        MAST token

    Returns
    -------
    info : dict
        Object that contains the returned data
    """

    parameters = {"mnemonic": "{}".format(mnemonic_identifier)}
    result = Mast.service_request_async(MAST_EDB_DICTIONARY_SERVICE, parameters)
    info = process_mast_service_request_result(result, data_as_table=False)[0]

    return info
