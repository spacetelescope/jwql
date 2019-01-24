#! /usr/bin/env python
"""Module to interface the JWST Engineering Database.

This module provides ``jwql`` with functions to interface and query the
 JWST Engineering Database.

Authors
-------

    - Johannes Sahlmann

Use
---

    This module can be imported and used with

    ::

        from jwql.engineering_database import query_single_mnemonic
        query_single_mnemonic(mnemonic_identifier, start_time, end_time)

    Required arguments:

    ``mnemonic_identifier`` - String representation of a mnemonic name.
    ``start_time`` - astropy.time.Time instance
    ``end_time`` - astropy.time.Time instance

Notes
-----
    This module is built on top of the engineering database tools provided by the jwst pipeline
    package (https://github.com/spacetelescope/jwst/blob/master/jwst/lib/engdb_tools.py)

TODO
----
    interpolate: return table including delta_t to nearest datapoint

    add function find `similar` mnemonics (same category etc.)



"""
import astropy
from astropy.table import Table
from astroquery.mast import Mast
import numpy as np

from jwql.utils.utils import get_config

# should use oauth.register_oauth()
settings = get_config()
mast_token = settings['mast_token']

Mast.login(token=mast_token)

mast_edb_timeseries_service = 'Mast.JwstEdb.GetTimeseries.All'
mast_edb_dictionary_service = 'Mast.JwstEdb.Dictionary'
mast_edb_mnemonic_service = 'Mast.JwstEdb.Mnemonics'

class EdbMnemonic():
    """Class to hold and manipulate results of EngDB queries."""

    def __init__(self, mnemonic_identifier, start_time, end_time, data, meta, info):
        """Populate attributes and separate data into timestamp and value."""
        self.mnemonic_identifier = mnemonic_identifier
        self.start_time = start_time
        self.end_time = end_time
        self.data = data
        self.meta = meta
        self.info = info

    def __str__(self):
        """Return string describing the instance."""
        return 'EdbMnemonic {} with {} records between {} and {}'.format(
            self.mnemonic_identifier, len(self.data), self.start_time.isot,
            self.end_time.isot)

    def interpolate(self, date, **kwargs):
        """Interpolate value at times specified in data argument."""
        raise NotImplementedError


def process_mast_service_request_result(result):
    """Parse the result of a MAST EDB query into a astropy data table and a meta dictionary.

    Parameters
    ----------
    result : 

    Returns
    -------

    """
    json_data = result[0].json()
    if json_data['status'] != 'COMPLETE':
        raise RuntimeError('mnemonic query did not complete!')

    # timestamp-value pairs in the form of an astropy table
    data = Table(json_data['data'])

    #collect meta data
    meta = {}
    for key in json_data.keys():
        if key.lower() != 'data':
            meta[key] = json_data[key]

    return data, meta


def query_single_mnemonic(mnemonic_identifier, start_time, end_time):
    """Query the EDB to return the mnemonic readings between start_time and end_time.

    Parameters
    ----------
    mnemonic_identifier: str
        Can be full mnemonic or can contain wildcard syntax.
    start_time: astropy.time.Time instance
        Start time
    end_time: astropy.time.Time instance
        End time

    Returns
    -------
        mnemonic : instance of EdbMnemonic
            Object that contains the returned data

    """
    if not isinstance(start_time, astropy.time.core.Time):
        raise RuntimeError('Please specify a valid start time (instance of astropy.time.core.Time)')

    if not isinstance(end_time, astropy.time.core.Time):
        raise RuntimeError('Please specify a valid end time (instance of astropy.time.core.Time)')

    parameters = {'mnemonic': mnemonic_identifier, 'start': start_time.iso, 'end': end_time.iso}
    out = Mast.service_request_async(mast_edb_timeseries_service, parameters)
    data, meta = process_mast_service_request_result(out)
    info = query_mnemonic_info(mnemonic_identifier)

    # create and return instance
    mnemonic = EdbMnemonic(mnemonic_identifier, start_time, end_time, data, meta, info)
    return mnemonic


def query_mnemonic_info(mnemonic_identifier):
    """Query the EDB to return the mnemonic description.

    Parameters
    ----------
    mnemonic_identifier: str
        Can be full mnemonic or can contain wildcard syntax.

    Returns
    -------
        info : dict
            Object that contains the returned data

    """
    parameters = {"mnemonic": "{}".format(mnemonic_identifier)}
    out = Mast.service_request_async(mast_edb_dictionary_service, parameters)
    info = out[0].json()['data'][0]
    return info


def get_all_mnemonic_identifiers():
    """Return identifiers and meta data for all mnemonics in the engineering database."""
    out = Mast.service_request_async(mast_edb_mnemonic_service, {})
    data, meta = process_mast_service_request_result(out)

    return data, meta
