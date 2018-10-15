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

"""
import astropy
from astropy.table import Table
from jwst.lib import engdb_tools
import numpy as np

engdb = engdb_tools.ENGDB_Service()


class EdbMnemonic():
    """Class to hold and manipulate results of EngDB queries."""

    def __init__(self, mnemonic_identifier, start_time, end_time, data, meta):
        """Populate attributes and separate data into timestamp and value."""
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
        return 'EdbMnemonic {} with {} records between {} and {}'.format(
            self.mnemonic_identifier, len(self.record_times), self.start_time.isot,
            self.end_time.isot)

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

    data = engdb.get_values(mnemonic_identifier, start_time, end_time, include_bracket_values=True,
                            include_obstime=True, zip=False)
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

    keys = [key for key, val in meta['TlmMnemonics'][0].items()]
    rows = meta['TlmMnemonics']
    for i in range(meta['Count']):
        values = [rows[i][key] for key in keys]
        if i == 0:
            table = Table()
            for key, value in meta['TlmMnemonics'][i].items():
                table[key] = [value]
        else:
            table.add_row(values)

    if verbose:
        print('EngDB contains {} mnemonics'.format(meta['Count']))
        table.pprint()

    return table
