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
import astropy.units as u
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
    assert np.all(mnemonic.mean == np.array([10., 25., 12., 50.]))
    assert np.all(mnemonic.median == np.array([10., 25., 12., 50.]))
    assert np.all(mnemonic.stdev == np.array([0., 0., 0., 0.]))


def test_full_stats():
    """Test that the statistics calculated over the entire data set are
    correct
    """
    dates = np.array([datetime(2021, 12, 18, 7, n, 0) for n in range(20, 30)])
    data = np.arange(1, 11)
    tab = Table()
    tab["dates"] = dates
    tab["euvalues"] = data
    mnemonic = ed.EdbMnemonic('SOMETHING', Time('2021-12-18T07:20:00'), Time('2021-12-18T07:30:00'), tab, {}, {})
    mnemonic.full_stats()
    assert mnemonic.mean == 5.5
    assert mnemonic.median == 5.5
    assert np.isclose(mnemonic.stdev, 2.8722813232690143)
    assert mnemonic.median_time == datetime(2021, 12, 18, 7, 24, 30)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_mnemonic():
    """Test the query of a single mnemonic."""
    from jwql.edb.engineering_database import get_mnemonic

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    start_time = Time('2021-09-02 00:00:00.000', format='iso')
    end_time = Time('2021-09-02 12:00:00.000', format='iso')

    mnemonic = get_mnemonic(mnemonic_identifier, start_time, end_time)
    assert len(mnemonic) == len(mnemonic.data["dates"])
    assert len(mnemonic) == 2637
    assert mnemonic.meta == {'Count': 1,
                             'TlmMnemonics': [{'TlmMnemonic': 'IMIR_HK_ICE_SEC_VOLT4',
                             'Subsystem': 'MIRI',
                             'RawType': 'FL32',
                             'EUType': 'FL32',
                             'SQLType': 'REAL',
                             'AllPoints': 1}]}
    assert mnemonic.info == {'subsystem': 'MIRI',
                             'tlmMnemonic': 'IMIR_HK_ICE_SEC_VOLT4',
                             'tlmIdentifier': 210961,
                             'description': 'MIR Housekeeping Packet ICE Motor Secondary Voltage 4',
                             'sqlDataType': 'real',
                             'unit': 'V',
                             'longDescription': None}


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_mnemonic_info():
    """Test retrieval of mnemonic info."""
    from jwql.edb.engineering_database import get_mnemonic_info

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    info = get_mnemonic_info(mnemonic_identifier)
    assert info == {'subsystem': 'MIRI',
                    'tlmMnemonic': 'IMIR_HK_ICE_SEC_VOLT4',
                    'tlmIdentifier': 210961,
                    'description': 'MIR Housekeeping Packet ICE Motor Secondary Voltage 4',
                    'sqlDataType': 'real',
                    'unit': 'V',
                    'longDescription': None}


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_mnemonics():
    """Test the query of a list of mnemonics."""
    from jwql.edb.engineering_database import get_mnemonics

    mnemonics = ['SA_ZFGOUTFOV', 'SA_ZFGBADCNT']
    start_time = Time(2018.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    mnemonic_dict = get_mnemonics(mnemonics, start_time, end_time)
    assert len(mnemonic_dict) == len(mnemonics)

def test_add():
    """Test addition (i.e. concatenation) of two EdbMnemonic objects"""
    dates1 = np.array([datetime(2021, 12, 18, 7, n, 0) for n in range(20, 30)])
    data1 = np.array([5, 5, 5, 9, 9, 9, 9, 9, 2, 2])
    tab = Table()
    tab["dates"] = dates1
    tab["euvalues"] = data1
    blocks = [0, 3, 8]
    info = {}
    info['unit'] = 'V'
    info['tlmMnemonic'] = 'TEST_VOLTAGE'
    mnemonic1 = ed.EdbMnemonic('TEST_VOLTAGE', Time('2021-12-18T07:20:00'), Time('2021-12-18T07:30:00'), tab, {}, info, blocks=blocks)

    dates2 = np.array([datetime(2021, 12, 18, 7, n, 0) for n in range(27, 37)])
    data2 = np.array([9, 2, 2, 2, 19, 19, 19, 19, 12, 12])
    tab = Table()
    tab["dates"] = dates2
    tab["euvalues"] = data2
    blocks = [0, 1, 4, 8]
    info = {}
    info['unit'] = 'V'
    info['tlmMnemonic'] = 'TEST_VOLTAGE'
    mnemonic2 = ed.EdbMnemonic('TEST_VOLTAGE', Time('2021-12-18T07:27:00'), Time('2021-12-18T07:33:00'), tab, {}, info, blocks=blocks)

    added = mnemonic1 + mnemonic2
    assert all(added.data["euvalues"] == np.array([5, 5, 5, 9, 9, 9, 9, 9, 2, 2, 2, 19, 19, 19, 19, 12, 12]))
    assert all(added.data["dates"] == np.append(dates1, dates2[3:]))
    assert added.info['unit'] == 'V'

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


def test_multiplication():
    """Test multiplication of two EdbMnemonic objects"""
    dates1 = np.array([datetime(2021, 12, 18, 7, n, 0) for n in range(20, 30)])
    data1 = np.array([5, 5, 5, 9, 9, 9, 9, 9, 2, 2])
    tab = Table()
    tab["dates"] = dates1
    tab["euvalues"] = data1
    blocks1 = [0, 3, 8]
    info = {}
    info['unit'] = 'V'
    info['tlmMnemonic'] = 'TEST_VOLTAGE'
    info['description'] = 'Voltage at some place'
    mnemonic1 = ed.EdbMnemonic('TEST_VOLTAGE', Time('2021-12-18T07:20:00'), Time('2021-12-18T07:30:00'), tab, {}, info, blocks=blocks1)

    dates2 = np.array([datetime(2021, 12, 18, 7, n, 10) for n in range(20, 30)])
    data2 = np.array([15, 15, 15, 19, 19, 19, 19, 19, 12, 12])
    tab = Table()
    tab["dates"] = dates2
    tab["euvalues"] = data2
    blocks2 = [0, 3, 8]
    info = {}
    info['unit'] = 'A'
    info['tlmMnemonic'] = 'TEST_CURRENT'
    info['description'] = 'Current at some place'
    mnemonic2 = ed.EdbMnemonic('TEST_CURRENT', Time('2021-12-18T07:20:10'), Time('2021-12-18T07:30:10'), tab, {}, info, blocks=blocks2)

    prod = mnemonic1 * mnemonic2
    assert all(prod.data["euvalues"].data == np.array([75.0, 75.0, 165.0, 171.0, 171.0, 171.0, 171.0, 26.333333333333336, 24.0]))
    assert all(prod.data["dates"].data == mnemonic1.data["dates"][1:])
    assert all(prod.blocks == np.array([0, 3, 8]))
    assert prod.info['unit'] == 'W'
    assert prod.info['tlmMnemonic'] == 'TEST_VOLTAGE * TEST_CURRENT'


def test_timed_stats():
    """Break up data into chunks of a given duration"""
    dates = np.array([datetime(2021, 12, 18, 12, 0, 0) + timedelta(hours=n) for n in range(0, 75, 2)])
    block_val = np.array([1, 1.1, 1, 1.1, 1, 1.1])
    data = np.concatenate((block_val, block_val+1, block_val+2, block_val+3, block_val+4, block_val+5))
    data = np.append(data, np.array([95., 97.]))

    tab = Table()
    tab["dates"] = dates
    tab["euvalues"] = data
    mnemonic = ed.EdbMnemonic('SOMETHING', Time('2021-12-18T02:00:00'), Time('2021-12-21T14:00:00'), tab, {}, {})

    duration = 12 * u.hour
    mnemonic.timed_stats(duration, sigma=3)
    print(mnemonic.mean)
    print(np.append(np.arange(1.05, 6.05, 1), 96.))
    assert np.all(np.isclose(mnemonic.mean, np.append(np.arange(1.05, 6.06, 1), 96.)))
