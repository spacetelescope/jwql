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

        pytest -s test_edb.py
"""

import os

from astropy.table import Table
from astropy.time import Time
from datetime import datetime, timedelta
import numpy as np
import pytest

from jwql.edb import engineering_database as ed

# Determine if tests are being run on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

def test_daily_stats():
    """Test that the daily statistics are calculated correctly
    """
    dates = np.array([datetime(2021, 12, 18, 12, 0, 0) + timedelta(hours=n) for n in range(0, 75, 2)])
    data = [10.] * 12
    data.extend([25.] * 12)
    data.extend([12.] * 12)
    data.extend([50.] * 2)
    tab = Table()
    tab["dates"] = dates
    tab["euvalues"] = data
    mnemonic = ed.EdbMnemonic('SOMETHING', Time('2021-12-18T02:00:00'), Time('2021-12-21T14:00:00'), tab, {}, {})

    mnemonic.daily_stats()
    assert np.all(self.mean == np.array([10., 25., 12., 50.]))
    assert np.all(self.median == np.array([10., 25., 12., 50.]))
    assert np.all(self.stdev == np.array([0., 0., 0., 0.]))



def test_full_stats():
    """Test that the statistics calculated over the entire data set are
    correct
    """
    dates = np.array([datetime(2021, 12, 18, 7, n, 0) for n in range(20, 30)])
    data = np.arange(1, 11)
    tab = Table()
    tab["dates"] = dates
    tab["euvalues"] = data
    mnemonic = ed.EdbMnemonic('SOMETHING', Time('2021-12-18T07:20:00'), Time('2021-12-18T07:30:00'), tab, {}, {}, blocks=blocks)
    mnemonic.full_stats()
    assert mnemonic.mean == 5.5
    assert mnemonic.median = 5.5
    assert np.isclose(mnemonic.stdev, 2.8722813232690143)
    assert mnemonic.median_time = datetime(2021, 12, 18, 7, 24, 30)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_mnemonic():
    """Test the query of a single mnemonic."""
    from jwql.edb.engineering_database import get_mnemonic

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    start_time = Time('2019-01-16 00:00:00.000', format='iso')
    end_time = Time('2019-01-16 00:01:00.000', format='iso')

    mnemonic = get_mnemonic(mnemonic_identifier, start_time, end_time)
    assert len(mnemonic.data) == mnemonic.meta['paging']['rows']


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_mnemonic_info():
    """Test retrieval of mnemonic info."""
    from jwql.edb.engineering_database import get_mnemonic_info

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    info = get_mnemonic_info(mnemonic_identifier)
    assert 'subsystem' in info.keys()


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_mnemonics():
    """Test the query of a list of mnemonics."""
    from jwql.edb.engineering_database import get_mnemonics

    mnemonics = ['SA_ZFGOUTFOV', 'SA_ZFGBADCNT']
    start_time = Time(2018.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    mnemonic_dict = get_mnemonics(mnemonics, start_time, end_time)
    assert len(mnemonic_dict) == len(mnemonics)


def test_interpolation():
    """Test interpolation of an EdbMnemonic object"""
    dates = np.array([datetime(2021, 12, 18, 7, n, 0) for n in range(20, 30)])
    data = np.arange(1, 11)
    tab = Table()
    tab["dates"] = dates
    tab["euvalues"] = data
    blocks = [0, 3, 8]
    mnemonic = ed.EdbMnemonic('SOMETHING', Time('2021-12-18T07:20:00'), Time('2021-12-18T07:30:00'), tab, {}, {}, blocks=blocks)

    # Note that the first element of interp_times is before the earliest value
    # of the mnemonic time, so it should be ignored.
    base_interp = datetime(2021, 12, 18, 7, 19, 30)
    interp_times = [base_interp + timedelta(seconds = 30 * n) for n in range(0, 20)]

    mnemonic.interpolate(interp_times)
    assert all(mnemonic.data["dates"].data == interp_times[1:])
    assert all(mnemonic.data["euvalues"].data == np.arange(10, 101, 5) / 10.)
    assert all(mnemonic.blocks == np.array([0, 6, 16]))


