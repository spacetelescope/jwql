#!/usr/bin/env python
"""Tests for the dbmonitor module.

Authors
-------

    - Joe Filippazzo


Use
---

    These tests can be run via the command line (omit the -s to suppress verbose output to stdout):

    ::
        pytest -s test_dbmonitor.py

"""

from ..dbmonitor import dbmonitor as db
from ..utils.utils import JWST_INSTRUMENTS


def test_caom_keywords():
    """Test to see that the CAOM keywords are the same for all instruments"""
    kw = []
    for ins in JWST_INSTRUMENTS:
        kw.append(db.instrument_keywords(ins, caom=True)['keyword'].tolist())

    assert kw[0] == kw[1] == kw[2] == kw[3] == kw[4]
