#! /usr/bin/env python

"""Tests for the ``grating_monitor`` module.

Authors
-------

    - Teagan King

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_grating_monitor.py
"""

import os
import pytest
import shutil

from astropy.io import fits
import numpy as np

from jwql.database.database_interface import NIRSpecGratingQueryHistory, NIRSpecGratingStats
from jwql.instrument_monitors.common_monitors import grating_monitor
from jwql.utils.utils import get_config

ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


# @pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
# def test_query_mast():
#     """Test the ``query_mast`` function
#     NEED TO UPDATE
#     """

#     gw = grating_monitor()
#     _, _, _, aperture = define_test_data(1)

#     gw.aperture = aperture
#     gw.instrument = 'nirspec'
#     gw.query_start = 57357.0
#     gw.query_end = 57405.0

#     result = gw.query_mast()

#     assert len(result) == 5
