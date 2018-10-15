#! /usr/bin/env python

"""Tests for the ``interface_engineering_database`` module.

Authors
-------

    - Johannes Sahlmann


Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_interface_edb.py
"""

# import pytest

from astropy.time import Time

from jwql.interface_engineering_database.interface_edb import query_meta_data, query_mnemonic


def test_query_meta_data():
    """Test the query of mnemonic meta data."""

    mnemonic_identifier = 'SA_ZFGOUTFOV'

    data = query_meta_data(mnemonic_identifier)
    print(data)


def test_query_mnemonic():
    """Test the query of a mnemonic over a given time range."""

    mnemonic_identifier = 'SA_ZFGOUTFOV'

    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')
    data = query_mnemonic(mnemonic_identifier, start_time, end_time)
    print(data)
