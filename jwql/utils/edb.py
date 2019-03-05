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

from astropy.time import Time
import jwql.utils.engineering_database as edb

def test_query_single_mnemonic():
    """Test the query of a mnemonic over a given time range."""

    mnemonic_identifier = 'SE_ZIMIRICEA'
    start_time = Time(2018.01, format='decimalyear')
    end_time = Time(2018.02, format='decimalyear')

    mnemonic = edb.query_single_mnemonic(mnemonic_identifier, start_time, end_time)
    print(mnemonic)

def main():
    data, meta = edb.get_all_mnemonic_identifiers()
    print(data)
    test_query_single_mnemonic()

if __name__ == "__main__":
    main()
