#! /usr/bin/env python

"""Tests for the ``bias`` module.

Authors
-------

    Joe Filippazzo

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_bias.py
"""

import pytest

from jwql.jwql_monitors import bias
from jwql.utils.constants import JWST_INSTRUMENT_NAMES


def test_fetch_data():
    """Test if the fetch_data function produces data"""
    md = bias.measure_bias('niriss', None, None, test=10)

    assert md.shape == (10, 2048, 2048)
