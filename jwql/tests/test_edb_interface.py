#! /usr/bin/env python
"""Tests for the ``engineering_database`` module.

Authors
-------

    - Johannes Sahlmann


Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_edb_interface.py
"""

import pytest

from astropy.time import Time

from jwst.lib import engdb_tools


from ..utils.engineering_database import query_single_mnemonic, get_all_mnemonics

def test_get_all_mnemonics():
    """Test the retrieval of all mnemonics."""
    all = get_all_mnemonics(verbose=True)


def est_query_single_mnemonic():
    """Test the query of a mnemonic over a given time range."""

    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    print()
    mnemonic = query_single_mnemonic(mnemonic_identifier, start_time, end_time, verbose=True)



# from jwql.interface_engineering_database.interface_edb import query_meta_data, query_mnemonic
#
#
# @pytest.mark.xfail # temporary until `internal` Jenkins becomes available
# def test_query_meta_data():
#     """Test the query of mnemonic meta data."""
#
#     mnemonic_identifier = 'SA_ZFGOUTFOV'
#
#     data = query_meta_data(mnemonic_identifier)
#     print(data)
#
#
# @pytest.mark.xfail # temporary until `internal` Jenkins becomes available
def est_query_mnemonic():
    """Test the query of a mnemonic over a given time range."""

    engdb = engdb_tools.ENGDB_Service()

    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    records = engdb.get_records(mnemonic_identifier, start_time, end_time)
    n_data_records = len(records['Data'])
    assert n_data_records == records['Count']
    # print(len(records['Data']))
    print('\n', records)
    data = engdb.get_values(mnemonic_identifier, start_time, end_time, include_bracket_values=True)
    n_data_values = len(data)
    # print(len(data))
    print(data)
    assert n_data_records == n_data_values

    # get meta data
    # meta = engdb.get_meta(mnemonic=mnemonic_identifier)
    # print(meta)
    # assert meta['TlmMnemonics'][0]['TlmMnemonic'] == mnemonic_identifier


def est_query_meta():
    """Test the query of a mnemonic meta data."""

    engdb = engdb_tools.ENGDB_Service()

    mnemonic_identifier = 'SA_Z'
    # mnemonic_identifier = ''

    # get meta data
    meta = engdb.get_meta(mnemonic=mnemonic_identifier)
    print(meta)
    assert mnemonic_identifier in meta['TlmMnemonics'][0]['TlmMnemonic']
    assert meta['Count'] > 1

