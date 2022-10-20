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

    Returns
    -------
    data : numpy.ndarray

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


def define_fake_test_data():
    """Create some fake data to test with
    """
    # Create fake ramp and rates Signal goes up by 1 in each group
    data = np.zeros((2, 5, 10, 10))
    for group in range(5):
        data[:, group, :, :] = group

    rates = np.ones((2, 10, 10))

    # Add in jumps
    data[0, 3:, 4, 4] += 10.
    data[0, 1:, 3, 3] -= 5.
    data[1, 2:, 2, 2] += 3.

    header = {'TGROUP': 1.0}
    jump_coords = [(0, 3, 4, 4), (0, 1, 3, 3), (1, 2, 2, 2)]
    prior_coords = [(0, 2, 4, 4), (0, 0, 3, 3), (1, 1, 2, 2)]

    return data, rates, header, jump_coords, prior_coords


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


def test_magnitude_fake_data():
    """Test the magnitude method using locally-constructed fake data
    """
    data, rate, header, jump_coords, prior_coords = define_fake_test_data()

    cr = CosmicRay()
    cr.nints = 2
    mag = cr.magnitude(jump_coords[0], prior_coords[0], rate, data, header)
    assert mag == 10.


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


def test_get_cr_mags_fake_data():
    """Test the calculation of multiple CR magnitudes"""
    data, rate, header, jump_coords, prior_coords = define_fake_test_data()
    bin_indices = np.arange(65536*2+1, dtype=np.int32) - 65536

    cr = CosmicRay()
    cr.nints = 2
    mags = cr.get_cr_mags(jump_coords, prior_coords, rate, data, header)
    assert len(mags) == 65536*2+1 # assert that it's a bin
    assert mags[bin_indices[10]] == 1
    assert mags[bin_indices[-5]] == 1
    assert mags[bin_indices[3]] == 1

    cr_one_int = CosmicRay()
    cr_one_int.nints = 1
    int1_jump_coords = [c[1:] for c in jump_coords[0:2]]
    int1_prior_coords = [c[1:] for c in prior_coords[0:2]]
    mags, outliers = cr_one_int.get_cr_mags(int1_jump_coords, int1_prior_coords, rate[0, :, :], data, header)
    assert mags[bin_indices[10]] == 1
    assert mags[bin_indices[-5]] == 1
    assert mags[bin_indices[3]] == 0


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
