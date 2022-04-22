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

import os

from astropy.io import fits
import numpy as np
import pytest

from jwql.instrument_monitors.common_monitors.cosmic_ray_monitor import CosmicRay
from jwql.database.database_interface import MIRICosmicRayQueryHistory
from jwql.utils.utils import get_config

ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


def define_test_data(nints):
    """Define the data to test with.

    Parameters
    ----------
    nints : int
        The number of integrations
    """
    if nints == 1:
        data = np.ones((2, 5, 10, 10))
        rate_data = np.ones((10, 10))
    else:
        data = np.ones((2, 5, 10, 10))
        rate_data = np.ones((2, 10, 10))

    filesystem = get_config()['filesystem']
    filename = os.path.join(filesystem, 'public', 'jw00623', 'jw00623087001', 'jw00623087001_07101_00001_mirimage_rate.fits')
    aperture = 'MIRIM_FULL'

    return data, rate_data, filename, aperture


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_jump_data():
    """Test the ``get_jumpy_data`` function"""

    cr = CosmicRay()
    _, _, filename, _ = define_test_data(2)

    header, data, dq = cr.get_jump_data(filename)

    assert type(header) == fits.header.Header
    assert type(data) == np.ndarray
    assert type(dq) == np.ndarray


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_rate_data():
    """Test the ``get_rate_data`` function"""

    cr = CosmicRay()
    _, _, filename, _ = define_test_data(2)

    data = cr.get_rate_data(filename)

    assert type(data) == np.ndarray


def test_get_cr_rate():
    """Test the ``get_cr_rate`` function"""

    cr = CosmicRay()
    jumps = 100
    header = fits.header.Header()
    header['EFFEXPTM'] = 110.
    header['TGROUP'] = 10.
    header['SUBSIZE1'] = 50.
    header['SUBSIZE2'] = 50.

    rate = cr.get_cr_rate(jumps, header)
    assert rate == 0.0004


def test_group_before():
    """Test the ``group_before`` function"""

    cr = CosmicRay()

    jump_locations = [(2, 1, 1)]
    cr.nints = 1

    assert cr.group_before(jump_locations) == [(1, 1, 1)]

    jump_locations = [(1, 2, 1, 1)]
    cr.nints = 2

    assert cr.group_before(jump_locations) == [(1, 1, 1, 1)]


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_magnitude():
    """Test the ``magnitude`` method"""

    cr = CosmicRay()

    cr.nints = 5
    data, rate_data, filename, aperture = define_test_data(cr.nints)
    header = fits.getheader(filename)
    coord = (1, 2, 1, 1)
    coord_gb = (1, 1, 1, 1)
    mag = cr.magnitude(coord, coord_gb, rate_data, data, header)
    assert mag == -2.77504

    cr.nints = 1
    data, rate_data, filename, aperture = define_test_data(cr.nints)
    coord = (1, 1, 1)
    coord_gb = (0, 1, 1)
    mag = cr.magnitude(coord, coord_gb, rate_data, data, header)
    assert mag == -2.77504


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_cr_mags():
    """Test the ``get_cr_mags`` function"""

    cr = CosmicRay()

    jump_locations = [(2, 1, 1)]
    jump_locations_pre = [(1, 1, 1)]
    cr.nints = 1
    data, rate_data, filename, aperture = define_test_data(cr.nints)
    header = fits.getheader(filename)

    mags = cr.get_cr_mags(jump_locations, jump_locations_pre, rate_data, data, header)
    assert mags == [-2.77504]

    jump_locations = [(1, 2, 1, 1)]
    jump_locations_pre = [(1, 1, 1, 1)]
    cr.nints = 5
    data, rate_data, filename, aperture = define_test_data(cr.nints)

    mags = cr.get_cr_mags(jump_locations, jump_locations_pre, rate_data, data, header)
    assert mags == [-2.77504]


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_most_recent_search():
    """Test the ``most_recent_search`` function"""

    cr = CosmicRay()
    _, _, _, aperture = define_test_data(1)

    cr.aperture = aperture
    cr.query_table = MIRICosmicRayQueryHistory

    result = cr.most_recent_search()

    assert isinstance(result, float)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_query_mast():
    """Test the ``query_mast`` function"""

    cr = CosmicRay()
    _, _, _, aperture = define_test_data(1)

    cr.aperture = aperture
    cr.instrument = 'miri'
    cr.query_start = 57357.0
    cr.query_end = 57405.0

    result = cr.query_mast()

    assert len(result) == 5
