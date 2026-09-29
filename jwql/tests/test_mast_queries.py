#! /usr/bin/env python

"""Tests for the ``mast_utils`` module.

Authors
-------

    Joe Filippazzo

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_mast_utils.py
"""

import os
import pytest

from astroquery.mast import Mast

from jwql.utils import mast_queries as mq


file_test_data = [('nircam', 'jw01068001001_02102_00003_nrcb3_rate.fits', ['001']),
                  ('nircam', 'jw01068-o001_t005_nircam_clear-f356w-sub160_i2d.fits', ['001']),
                  ('MIRI', 'jw12772001001_03104_00003_mirifulong_s3d.fits', ['001']),
                  ('Miri', 'jw12772-o001_t001_miri_ch3-long_x1d.fits', ['001'])
                  ]

@pytest.mark.parametrize("instrument,filename,expected", file_test_data)
def test_get_file_obs_nums():
    assert mq.get_file_obs_nums(instrument, filename) == expected


prog_test_data = [('nircam', 1068, ['001', '002', '003', '004', '005', '006', '007']),
                  ('NIRCAM', '1068', ['001', '002', '003', '004', '005', '006', '007']),
                  ('Nircam', '01068', ['001', '002', '003', '004', '005', '006', '007'])]

@pytest.mark.parametrize("instrument,program,expected", prog_test_data)
def test_get_program_obs_nums():
    assert mq.get_program_obs_nums(instrument, program) == expected
