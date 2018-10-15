#! /usr/bin/env python
"""Module to interface the JWST Engineering Database.

This module provides ``jwql`` with functions to interface and query the
 JWST Engineering Database.

The module provides functionality to query database mnemonics.

Authors
-------

    - Johannes Sahlmann

Use
---

    This module can be imported and used with

    ::

        from jwql.interface_engineering_database.interface_edb import query_meta_data
        query_meta_data(mnemonic_identifier)

    Required arguments:

    ``mnemonic_identifier`` - String representation of a mnemonic name.

Notes
-----

    Some code was adapted from the EngDB.py script my Andre Martel.

TODO
----

    Identify list of valid mnemonics (at runtime?)

"""

import astropy
from astropy.table import Table
from jwst.lib import engdb_tools
import numpy as np

engdb = engdb_tools.ENGDB_Service()


class EdbMnemonic():
    """Class to hold and manipulate results of EngDB queries"""

    def __init__(self, mnemonic_identifier, start_time, end_time, data, meta):
        self.mnemonic_identifier = mnemonic_identifier
        self.start_time = start_time
        self.end_time = end_time
        self.data = data
        self.meta = meta

        # decode data (tuple of lists)
        self.record_times = np.array(self.data[0])
        self.record_values = np.array(self.data[1])

    def __str__(self):
        """Return string describing the instance."""
        return 'EdbMnemonic {} with {} records between {} and {}'.format(self.mnemonic_identifier, len(self.record_times), self.start_time.isot, self.end_time.isot)

    def interpolate(self, date, **kwargs):
        """Interpolate value at times specified in data argument."""
        raise NotImplementedError


def query_single_mnemonic(mnemonic_identifier, start_time, end_time, verbose=False):
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
        data: dict

    """

    if not isinstance(start_time, astropy.time.core.Time):
        raise RuntimeError('Please specify a valid start time (instance of astropy.time.core.Time)')

    if not isinstance(end_time, astropy.time.core.Time):
        raise RuntimeError('Please specify a valid end time (instance of astropy.time.core.Time)')

    data = engdb.get_values(mnemonic_identifier, start_time, end_time, include_bracket_values=True, include_obstime=True, zip=False)
    meta = engdb.get_meta(mnemonic=mnemonic_identifier)

    # create and return instance
    mnemonic = EdbMnemonic(mnemonic_identifier, start_time, end_time, data, meta)
    if verbose:
        print(mnemonic)
        print(mnemonic.data)
        print(mnemonic.meta)

    return mnemonic


def get_all_mnemonics(verbose=False):
    """Return identifiers and meta data for all mnemonics in the engineering database."""
    meta = engdb.get_meta(mnemonic='')  # use wildcard syntax
    if verbose:
        print('EngDB contains {} mnemonics'.format(meta['Count']))
        # print(meta)

    print(meta['TlmMnemonics'])
    table = Table[meta['TlmMnemonics']]
    table.pprint()


# import os
# import requests
#
# # read jwql configuration file
# from jwql.utils.utils import get_config
# settings = get_config()
#
# # set the base url for the JWST engineering database
# BASE_URL = settings['edb_base_url']


#
# def execute_query(url_string, parameters=None, verbose=True):
#     """Execute the query which consists in reading the URL.
#
#     Parameters
#     ----------
#     url_string
#     parameters
#     verbose
#
#     Returns
#     -------
#
#     """
#
#     session = requests.Session()
#
#     result = session.get(url_string, params=parameters, verify=False)
#
#     if verbose:
#         print('\nExecuted query:\n{}'.format(result.url))
#
#
#     return result
#
#
# def parse_query_result(result):
#     """Parse URL query result, e.g. convert json to dictionary.
#
#     Parameters
#     ----------
#     result
#
#     Returns
#     -------
#
#     """
#
#     if 'json' in result.headers['Content-Type']:
#         data = result.json()
#     else:
#         raise NotImplementedError
#
#     return data
#
#
#
# def query_meta_data(mnemonic_identifier, result_format='json', verbose=True):
#     """Query the EDB to return the metadata of mnemonics.
#
#     Parameters
#     ----------
#     mnemonic_identifier: str
#         Can be full mnemonic or can contain wildcard syntax.
#     format : str
#         Can be either `xml` or `json`. Defaults to `xml`
#
#     Returns
#     -------
#         data: dict
#
#     """
#
#     if result_format=='json':
#         format_str = ''
#     elif result_format=='xml':
#         format_str = 'xml'
#         raise NotImplementedError
#     else:
#         raise RuntimeError('Format must be one of [`json`, `xml`]. It is {}'.format(result_format))
#
#     url = os.path.join(BASE_URL, format_str, 'MetaData', 'TlmMnemonics', mnemonic_identifier)
#
#     result = execute_query(url)
#
#     data = parse_query_result(result)
#
#     return data
#
#
# def query_mnemonic(mnemonic_identifier, start_time, end_time, result_format='json', verbose=True):
#     """Query the EDB to return the mnemonic readings between start_time and end_time.
#
#
#     Parameters
#     ----------
#     mnemonic_identifier: str
#         Can be full mnemonic or can contain wildcard syntax.
#     start_time: astropy.time.Time instance
#         Start time
#     end_time: astropy.time.Time instance
#         End time
#     format : str
#         Can be either `xml` or `json`. Defaults to `json`
#
#     Returns
#     -------
#         data: dict
#
#     """
#
#     if result_format=='json':
#         format_str = ''
#     elif result_format=='xml':
#         format_str = 'xml'
#         raise NotImplementedError
#     else:
#         raise RuntimeError('Format must be one of [`json`, `xml`]. It is {}'.format(result_format))
#
#     request_parameters = {}
#     if start_time is not None:
#         request_parameters['stime'] = start_time.isot
#     else:
#         raise RuntimeError('Please specify a valid start time')
#
#     if end_time is not None:
#         request_parameters['etime'] = end_time.isot
#     else:
#         raise RuntimeError('Please specify a valid end time')
#
#     url = os.path.join(BASE_URL, format_str, 'Data', mnemonic_identifier)
#
#     result = execute_query(url, parameters=request_parameters)
#
#     data = parse_query_result(result)
#
#     return data
