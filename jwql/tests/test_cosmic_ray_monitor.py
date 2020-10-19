#! /usr/bin/env python

"""Tests for the cosmic ray monitor module.
    
    Authors
    -------
    
    - Mike Engesser
    
    Use
    ---
    
    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::
    
    pytest -s test_cosmic_ray_monitor.py
    """

import pytest
import cosmic_ray_monitor as crm
import numpy as np
from astropy.io import fits

from jwql.database.database_interface import MIRICosmicRayQueryHistory

def define_test_data(nints):
    if nints == 1:
        data = np.ones((2, 5, 10, 10))
        rate_data = np.ones((10, 10))
    else:
        data = np.ones((2, 5, 10, 10))
        rate_data = np.ones((2, 10, 10))

    file = "jw00000000000_00000_00000_MIRIMAGE_uncal.fits"
    aperture = "MIRIM_FULL"

return data, rate_data, file, aperture


def test_get_jump_data():
    _ = define_test_data(2)
    file = _[2]
    
    head, data, dq = crm.get_jump_data(file)
    
    assert type(head) == fits.header.Header
    assert type(data) == np.ndarray
    assert type(dq) == np.ndarray


def test_get_rate_data():
    _ = define_test_data(1)
    file = _[2]
    
    data = crm.get_rate_data(file)
    
    assert type(data) == np.ndarray


def test_get_cr_rate():
    jump_locs = np.arange(100).tolist()
    t = 5
    
    rate = crm.get_cr_rate(jump_locs, t)
    
    assert rate == 20.0


def test_group_before():
    jump_locs = [(2, 1, 1)]
    nints = 1
    
    assert crm.group_before(jump_locs, nints) == [(1, 1, 1)]
    
    jump_locs = [(1, 2, 1, 1)]
    nints = 2
    
    assert crm.group_before(jump_locs, nints) == [(1, 1, 1, 1)]


def test_magnitude():
    
    nints = 5
    data, rate_data, file, aperture = define_test_data(nints)
    head = fits.getheader(file)
    coord = (1, 2, 1, 1)
    coord_gb = (1, 1, 1, 1)
    mag = crm.magnitude(coord, coord_gb, rate_data, data, head, nints)
    assert mag == -2.77504
    
    nints = 1
    data, rate_data, file, aperture = define_test_data(nints)
    coord = (1, 1, 1)
    coord_gb = (0, 1, 1)
    mag = crm.magnitude(coord, coord_gb, rate_data, data, head, nints)
    assert mag == -2.77504


def test_get_cr_mags():
    
    jump_locs = [(2, 1, 1)]
    jump_locs_pre = [(1, 1, 1)]
    nints = 1
    data, rate_data, file, aperture = define_test_data(nints)
    head = fits.getheader(file)
    
    mags = crm.get_cr_mags(jump_locs, jump_locs_pre, rate_data, data, head, nints)
    assert mags == [-2.77504]
    
    jump_locs = [(1, 2, 1, 1)]
    jump_locs_pre = [(1, 1, 1, 1)]
    nints = 5
    data, rate_data, file, aperture = define_test_data(nints)
    
    mags = crm.get_cr_mags(jump_locs, jump_locs_pre, rate_data, data, head, nints)
    assert mags == [-2.77504]


def test_most_recent_search():
    
    _ = define_test_data(1)
    aperture = _[3]
    
    query_table = MIRICosmicRayQueryHistory
    
    result = crm.most_recent_search(aperture,query_table)
    
    assert result == 57357.0


def test_query_mast():
    
    start_date = 57357.0
    end_date = 57405.0
    
    result = crm.query_mast(start_date, end_date)
    
    assert len(result) == 5
