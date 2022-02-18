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

from collections import OrderedDict
import copy
from datetime import datetime
import os
import tempfile
import warnings

from astropy.table import Table
from astropy.time import Time
from astroquery.mast import Mast
from bokeh.embed import components
from bokeh.plotting import figure, show
import numpy as np

from jwst.lib.engdb_tools import ENGDB_Service
from jwql.utils.credentials import get_mast_base_url, get_mast_token
from jwql.utils.utils import get_config

MAST_EDB_MNEMONIC_SERVICE = 'Mast.JwstEdb.Mnemonics'
MAST_EDB_DICTIONARY_SERVICE = 'Mast.JwstEdb.Dictionary'

# Temporary until JWST operations: switch to test string for MAST request URL
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')
if not ON_GITHUB_ACTIONS:
    Mast._portal_api_connection.MAST_REQUEST_URL = get_config()['mast_request_url']


class EdbMnemonic:
    """Class to hold and manipulate results of DMS EngDB queries."""

    def __init__(self, mnemonic_identifier, start_time, end_time, data, meta, info):
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

    def __str__(self):
        """Return string describing the instance."""
        return 'EdbMnemonic {} with {} records between {} and {}'.format(
            self.mnemonic_identifier, len(self.data), self.data_start_time.isot,
            self.data_end_time.isot)

    def interpolate(self, times, **kwargs):
        """Interpolate value at specified times."""
        raise NotImplementedError

    def bokeh_plot(self, show_plot=False):
        """Make basic bokeh plot showing value as a function of time.

        Parameters
        ----------
        show_plot : boolean
            A switch to show the plot in the browser or not.

        Returns
        -------
        [div, script] : list
            List containing the div and js representations of figure.
        """

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

    def bokeh_plot_text_data(self, show_plot=False):
        """Make basic bokeh plot showing value as a function of time.

        Parameters
        ----------
        show_plot : boolean
            A switch to show the plot in the browser or not.

        Returns
        -------
        [div, script] : list
            List containing the div and js representations of figure.
        """

        abscissa = self.data['dates']
        ordinate = self.data['euvalues']

        p1 = figure(tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type='datetime',
                    title=self.mnemonic_identifier, x_axis_label='Time')

        override_dict = {}  # Dict instructions to set y labels
        unique_values = np.unique(ordinate)  # Unique values in y data

        # Enumerate i to plot 1, 2, ... n in y and then numbers as dict keys
        # and text as value. This will tell bokeh to change which numerical
        # values to text.
        for i, value in enumerate(unique_values):
            index = np.where(ordinate == value)[0]
            override_dict[i] = value
            dates = abscissa[index].astype(np.datetime64)
            y_values = list(np.ones(len(index), dtype=int) * i)
            p1.line(dates, y_values, line_width=1, line_color='blue', line_dash='dashed')
            p1.circle(dates, y_values, color='blue')

        p1.yaxis.ticker = list(override_dict.keys())
        p1.yaxis.major_label_overrides = override_dict

        if show_plot:
            show(p1)
        else:
            script, div = components(p1)

            return [div, script]

    def get_table_data(self):
        """Get data needed to make interactivate table in template."""

        # generate tables for display and download in web app
        display_table = copy.deepcopy(self.data)

        # temporary html file,
        # see http://docs.astropy.org/en/stable/_modules/astropy/table/
        tmpdir = tempfile.mkdtemp()
        file_name_root = 'mnemonic_exploration_result_table'
        path_for_html = os.path.join(tmpdir, '{}.html'.format(file_name_root))
        with open(path_for_html, 'w') as tmp:
            display_table.write(tmp, format='jsviewer')
        html_file_content = open(path_for_html, 'r').read()

        return html_file_content


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
