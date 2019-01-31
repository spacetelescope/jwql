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
import pytest


@pytest.mark.xfail
def test_get_all_mnemonics():
    """Test the retrieval of all mnemonics."""

    from ..utils.engineering_database import get_all_mnemonic_identifiers

    all_mnemonics = get_all_mnemonic_identifiers()[0]
    assert len(all_mnemonics) > 1000


@pytest.mark.xfail
def test_query_single_mnemonic():
    """Test the query of a mnemonic over a given time range."""

    from ..utils.engineering_database import query_single_mnemonic

    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    mnemonic = query_single_mnemonic(mnemonic_identifier, start_time, end_time)
    assert len(mnemonic.data) == mnemonic.meta['paging']['rows']
