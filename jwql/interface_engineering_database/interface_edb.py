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

import os
import requests

# read jwql configuration file
from jwql.utils.utils import get_config
settings = get_config()

# set the base url for the JWST engineering database
BASE_URL = settings['edb_base_url']


def execute_query(url_string, parameters=None, verbose=True):
    """Execute the query which consists in reading the URL.

    Parameters
    ----------
    url_string
    parameters
    verbose

    Returns
    -------

    """

    session = requests.Session()

    result = session.get(url_string, params=parameters, verify=False)

    if verbose:
        print('\nExecuted query:\n{}'.format(result.url))


    return result


def parse_query_result(result):
    """Parse URL query result, e.g. convert json to dictionary.

    Parameters
    ----------
    result

    Returns
    -------

    """

    if 'json' in result.headers['Content-Type']:
        data = result.json()
    else:
        raise NotImplementedError

    return data



def query_meta_data(mnemonic_identifier, result_format='json', verbose=True):
    """Query the EDB to return the metadata of mnemonics.

    Parameters
    ----------
    mnemonic_identifier: str
        Can be full mnemonic or can contain wildcard syntax.
    format : str
        Can be either `xml` or `json`. Defaults to `xml`

    Returns
    -------
        data: dict

    """

    if result_format=='json':
        format_str = ''
    elif result_format=='xml':
        format_str = 'xml'
        raise NotImplementedError
    else:
        raise RuntimeError('Format must be one of [`json`, `xml`]. It is {}'.format(result_format))

    url = os.path.join(BASE_URL, format_str, 'MetaData', 'TlmMnemonics', mnemonic_identifier)

    result = execute_query(url)

    data = parse_query_result(result)

    return data


def query_mnemonic(mnemonic_identifier, start_time, end_time, result_format='json', verbose=True):
    """Query the EDB to return the mnemonic readings between start_time and end_time.


    Parameters
    ----------
    mnemonic_identifier: str
        Can be full mnemonic or can contain wildcard syntax.
    start_time: astropy.time.Time instance
        Start time
    end_time: astropy.time.Time instance
        End time
    format : str
        Can be either `xml` or `json`. Defaults to `json`

    Returns
    -------
        data: dict

    """

    if result_format=='json':
        format_str = ''
    elif result_format=='xml':
        format_str = 'xml'
        raise NotImplementedError
    else:
        raise RuntimeError('Format must be one of [`json`, `xml`]. It is {}'.format(result_format))

    request_parameters = {}
    if start_time is not None:
        request_parameters['stime'] = start_time.isot
    else:
        raise RuntimeError('Please specify a valid start time')

    if end_time is not None:
        request_parameters['etime'] = end_time.isot
    else:
        raise RuntimeError('Please specify a valid end time')

    url = os.path.join(BASE_URL, format_str, 'Data', mnemonic_identifier)

    result = execute_query(url, parameters=request_parameters)

    data = parse_query_result(result)

    return data
