#! /usr/bin/env python

"""Tests for the ``monitor_mast`` module.

Authors
-------

    Joe Filippazzo

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_monitor_mast.py
"""

from astroquery.mast import Mast
import pytest

from jwql.jwql_monitors import monitor_mast as mm
from jwql.utils.constants import JWST_INSTRUMENT_NAMES


def test_astroquery_mast():
    """Test if the astroquery.mast service can complete a request"""
    service = 'Mast.Caom.Filtered'
    params = {'columns': 'COUNT_BIG(*)', 'filters': [], 'pagesize': 1,
              'page': 1}
    response = Mast.service_request_async(service, params)
    result = response[0].json()

    assert result['status'] == 'COMPLETE'


def test_caom_instrument_keywords():
    """Test to see that the CAOM keywords are the same for all
    instruments"""
    kw = []
    for ins in JWST_INSTRUMENT_NAMES:
        kw.append(mm.instrument_keywords(ins, caom=True)['keyword'].tolist())

    assert kw[0] == kw[1] == kw[2] == kw[3] == kw[4]


def test_filtered_instrument_keywords():
    """Test to see that the instrument specific service keywords are
    different for all instruments"""
    kw = []
    for ins in JWST_INSTRUMENT_NAMES:
        kw.append(mm.instrument_keywords(ins, caom=False)['keyword'].tolist())

    assert kw[0] != kw[1] != kw[2] != kw[3] != kw[4]


def test_instrument_inventory_filtering():
    """Test to see that the instrument inventory can be filtered"""
    filt = 'GR150R'
    data = mm.instrument_inventory('niriss',
                                   add_filters={'filter': filt},
                                   return_data=True)

    filters = [row['filter'] for row in data['data']]

    assert all([i == filt for i in filters])


def test_instrument_dataproduct_filtering():
    """Test to see that the instrument inventory can be filtered
    by data product"""
    dp = 'spectrum'
    data = mm.instrument_inventory('nirspec', dataproduct=dp, caom=True,
                                   return_data=True)

    dps = [row['dataproduct_type'] for row in data['data']]

    assert all([i == dp for i in dps])
