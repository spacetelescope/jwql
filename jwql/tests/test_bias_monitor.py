#! /usr/bin/env python

"""Tests for the ``bias_monitor`` module.

Authors
-------

    - Ben Sunnquist

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_bias_monitor.py
"""

import os
import pytest

import numpy as np

from jwql.database.database_interface import NIRCamBiasQueryHistory, NIRCamBiasStats
from jwql.instrument_monitors.common_monitors import bias_monitor


ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


def test_identify_tables():
    """Be sure the correct database tables are identified"""

    monitor = bias_monitor.Bias()
    monitor.instrument = 'nircam'
    monitor.identify_tables()

    assert monitor.query_table == eval('NIRCamBiasQueryHistory')
    assert monitor.stats_table == eval('NIRCamBiasStats')
