#! /usr/bin/env python
"""Module to interface the JWST DMS Engineering Database.

This module provides ``jwql`` with functions to interface and query the
JWST DMS Engineering Database. It is designed to have minimal
dependencies on non-builtin python packages.

Authors
-------

    - Johannes Sahlmann

Use
---

    This module can be imported and used with

    ::

        from jwql.edb import edb_interface
        edb_interface.query_single_mnemonic(mnemonic_identifier,
        start_time, end_time)

    Required arguments:

    ``mnemonic_identifier`` - String representation of a mnemonic name.
    ``start_time`` - astropy.time.Time instance
    ``end_time`` - astropy.time.Time instance

Notes
-----
    This module is built on top of ``astroquery.mast`` and uses
    JWST-specific MAST services.
    The user has to provide a valid MAST authentication token
    or be authenticated.

References
----------
    The MAST JWST EDB web portal is located at
    ``https://mast.stsci.edu/portal/Mashup/Clients/JwstEdb/JwstEdb.html``

Dependencies
------------
    - astropy
    - astroquery

"""
from functools import lru_cache

from astropy.table import Table
from astropy.time import Time
from astroquery.mast import Mast

mast_edb_timeseries_service = 'Mast.JwstEdb.GetTimeseries.All'
mast_edb_dictionary_service = 'Mast.JwstEdb.Dictionary'
mast_edb_mnemonic_service = 'Mast.JwstEdb.Mnemonics'


def mast_authenticate(token=None):
    """Verify MAST authentication status, login if needed."""
    if Mast.authenticated() is False:
        if token is None:
            raise ValueError('You are not authenticated in MAST. Please provide a valid token.')
        else:
            Mast.login(token=token)


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


@lru_cache()
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
    out = Mast.service_request_async(mast_edb_mnemonic_service, {})
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
        If True, return data as astropy table, else return as json

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
        raise RuntimeError('Query did not return any data.')

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
    mast_authenticate(token=token)

    parameters = {"mnemonic": "{}".format(mnemonic_identifier)}
    result = Mast.service_request_async(mast_edb_dictionary_service, parameters)
    info = process_mast_service_request_result(result, data_as_table=False)[0]
    return info


def query_single_mnemonic(mnemonic_identifier, start_time, end_time, token=None):
    """Query DMS EDB to get the mnemonic readings in a time interval.

    Parameters
    ----------
    mnemonic_identifier : str
        Telemetry mnemonic identifier, e.g. 'SA_ZFGOUTFOV'
    start_time : astropy.time.Time instance
        Start time
    end_time : astropy.time.Time instance
        End time
    token : str
        MAST token

    Returns
    -------
    data, meta, info : tuple
        Table and two dictionaries with the results of the query

    """
    mast_authenticate(token=token)

    if not is_valid_mnemonic(mnemonic_identifier):
        raise RuntimeError('Mnemonic identifier is invalid!')

    if not isinstance(start_time, Time):
        raise RuntimeError('Please specify a valid start time (instance of astropy.time.core.Time)')

    if not isinstance(end_time, Time):
        raise RuntimeError('Please specify a valid end time (instance of astropy.time.core.Time)')

    parameters = {'mnemonic': mnemonic_identifier, 'start': start_time.iso, 'end': end_time.iso}
    result = Mast.service_request_async(mast_edb_timeseries_service, parameters)
    data, meta = process_mast_service_request_result(result)

    # get auxiliary information (description, subsystem, ...)
    info = query_mnemonic_info(mnemonic_identifier)

    return data, meta, info
