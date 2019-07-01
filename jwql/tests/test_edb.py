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

from astropy.time import Time
import pytest

# Determine if tests are being run on jenkins
ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_mnemonic():
    """Test the query of a single mnemonic."""
    from jwql.edb.engineering_database import get_mnemonic

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    start_time = Time('2019-01-16 00:00:00.000', format='iso')
    end_time = Time('2019-01-16 00:01:00.000', format='iso')

    mnemonic = get_mnemonic(mnemonic_identifier, start_time, end_time)
    assert len(mnemonic.data) == mnemonic.meta['paging']['rows']


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_mnemonic_info():
    """Test retrieval of mnemonic info."""
    from jwql.edb.engineering_database import get_mnemonic_info

    mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'
    info = get_mnemonic_info(mnemonic_identifier)
    assert 'subsystem' in info.keys()


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_mnemonics():
    """Test the query of a list of mnemonics."""
    from jwql.edb.engineering_database import get_mnemonics

    mnemonics = ['SA_ZFGOUTFOV', 'SA_ZFGBADCNT']
    start_time = Time(2018.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    mnemonic_dict = get_mnemonics(mnemonics, start_time, end_time)
    assert len(mnemonic_dict) == len(mnemonics)
