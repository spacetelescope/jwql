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
from astroquery.mast import Mast

from jwql.edb.edb_interface import mnemonic_inventory, query_single_mnemonic
from jwql.utils.utils import get_config


@pytest.mark.xfail(raises=(RuntimeError, FileNotFoundError))
def test_get_mnemonic():
    """Test the query of a single mnemonic."""
    from jwql.edb.engineering_database import get_mnemonic

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    start_time = Time('2019-01-16 00:00:00.000', format='iso')
    end_time = Time('2019-01-16 00:01:00.000', format='iso')

    mnemonic = get_mnemonic(mnemonic_identifier, start_time, end_time)
    assert len(mnemonic.data) == mnemonic.meta['paging']['rows']


@pytest.mark.xfail(raises=(RuntimeError, FileNotFoundError))
def test_get_mnemonics():
    """Test the query of a list of mnemonics."""
    from jwql.edb.engineering_database import get_mnemonics

    mnemonics = ['SA_ZFGOUTFOV', 'SA_ZFGBADCNT']
    start_time = Time(2018.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    mnemonic_dict = get_mnemonics(mnemonics, start_time, end_time)
    assert len(mnemonic_dict) == len(mnemonics)


def test_mnemonic_inventory():
    """Test the retrieval of the mnemonic inventory."""
    all_mnemonics = mnemonic_inventory()[0]
    assert len(all_mnemonics) > 1000


@pytest.mark.xfail(raises=(RuntimeError, FileNotFoundError))
def test_query_single_mnemonic():
    """Test the query of a mnemonic over a given time range."""
    settings = get_config()
    MAST_TOKEN = settings['mast_token']

    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2018.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    data, meta, info = query_single_mnemonic(mnemonic_identifier, start_time, end_time,
                                             token=MAST_TOKEN)
    assert len(data) == meta['paging']['rows']


def test_invalid_query():
    """Test that the mnemonic query for an unauthorized user fails."""

    Mast.logout()

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    start_time = Time('2019-01-16 00:00:00.000', format='iso')
    end_time = Time('2019-01-16 00:01:00.000', format='iso')
    try:
        query_single_mnemonic(mnemonic_identifier, start_time, end_time, token='1234')
    except RuntimeError:
        pass
