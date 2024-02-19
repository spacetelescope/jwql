#! /usr/bin/env python

"""Tests for the ``dark_monitor`` module.

Authors
-------

    - Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_dark_monitor.py
"""

import datetime
import os
import pytest

from astropy.time import Time
import numpy as np

from jwql.database import database_interface as di
from jwql.instrument_monitors.common_monitors import dark_monitor
from jwql.tests.resources import has_test_db
from jwql.utils.monitor_utils import mast_query_darks
from jwql.utils.utils import get_config
from jwql.utils.constants import ON_GITHUB_ACTIONS


def test_find_hot_dead_pixels():
    """Test hot and dead pixel searches"""
    monitor = dark_monitor.Dark()

    # Create "baseline" image
    comparison_image = np.zeros((10, 10)) + 1.

    # Create mean slope image to compare
    mean_image = np.zeros((10, 10)) + 1.
    mean_image[0, 0] = 1.7
    mean_image[1, 1] = 2.2
    mean_image[7, 7] = 4.5
    mean_image[5, 5] = 0.12
    mean_image[6, 6] = 0.06
    mean_image[7, 3] = 0.09

    hot, dead = monitor.find_hot_dead_pixels(mean_image, comparison_image, hot_threshold=2., dead_threshold=0.1)
    assert len(hot) == 2
    assert np.all(hot[0] == np.array([1, 7]))
    assert np.all(hot[1] == np.array([1, 7]))
    assert len(dead) == 2
    assert np.all(dead[0] == np.array([6, 7]))
    assert np.all(dead[1] == np.array([6, 3]))


@pytest.mark.skip(reason='Needs update: different values than expected')
@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_metadata():
    """Test retrieval of metadata from input file"""

    monitor = dark_monitor.Dark()
    filename = os.path.join(get_config()['test_dir'], 'dark_monitor', 'test_image_1.fits')
    monitor.get_metadata(filename)

    assert monitor.detector == 'NRCA1'
    assert monitor.x0 == 0
    assert monitor.y0 == 0
    assert monitor.xsize == 10
    assert monitor.ysize == 10
    assert monitor.sample_time == 10
    assert monitor.frame_time == 10.5


@pytest.mark.skip(reason='Needs update: no data returned')
@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Currently no data in astroquery.mast.  This can be removed for JWST operations.')
def test_mast_query_darks():
    """Test that the MAST query for darks is functional"""

    instrument = 'NIRCAM'
    aperture = 'NRCA1_FULL'
    readpatt = 'BRIGHT2'
    start_date = Time("2016-01-01T00:00:00").mjd
    end_date = Time("2018-01-01T00:00:00").mjd
    query = mast_query_darks(instrument, aperture, readpatt, start_date, end_date)
    apernames = [entry['apername'] for entry in query]
    filenames = [entry['filename'] for entry in query]

    truth_filenames = ['jw82600013001_02103_00003_nrca1_dark.fits',
                       'jw82600013001_02103_00001_nrca1_dark.fits',
                       'jw82600013001_02103_00002_nrca1_dark.fits',
                       'jw82600016001_02103_00002_nrca1_dark.fits',
                       'jw82600016001_02103_00001_nrca1_dark.fits',
                       'jw82600016001_02103_00004_nrca1_dark.fits',
                       'jw82600016001_02103_00003_nrca1_dark.fits']

    assert len(query) >= 7
    for truth_filename in truth_filenames:
        assert truth_filename in filenames


def test_noise_check():
    """Test the search for noisier than average pixels"""

    noise_image = np.zeros((10, 10)) + 0.5
    baseline = np.zeros((10, 10)) + 0.5

    noise_image[3, 3] = 0.8
    noise_image[6, 6] = 0.6
    noise_image[9, 9] = 1.0

    baseline[5, 5] = 1.0
    noise_image[5, 5] = 1.25

    monitor = dark_monitor.Dark()
    noisy = monitor.noise_check(noise_image, baseline, threshold=1.5)

    assert len(noisy[0]) == 2
    assert np.all(noisy[0] == np.array([3, 9]))
    assert np.all(noisy[1] == np.array([3, 9]))


def test_shift_to_full_frame():
    """Test pixel coordinate shifting to be in full frame coords"""

    monitor = dark_monitor.Dark()
    monitor.x0 = 512
    monitor.y0 = 512

    coordinates = (np.array([6, 7]), np.array([6, 3]))
    new_coords = monitor.shift_to_full_frame(coordinates)

    assert np.all(new_coords[0] == np.array([518, 519]))
    assert np.all(new_coords[1] == np.array([518, 515]))


@pytest.mark.skipif(not has_test_db(), reason='Modifies test database.')
def test_add_bad_pix():
    coord = ([1, 2, 3], [4, 5, 6])
    pixel_type = 'test_new_pixel_type'
    files = ['test.fits']
    obs_start = obs_mid = obs_end = datetime.datetime.now()
    baseline = 'baseline.fits'
    mean_file = 'meanfile.fits'

    dark = dark_monitor.Dark()
    dark.instrument = 'nircam'
    dark.detector = 'nrcalong'
    dark.identify_tables()

    try:
        dark.add_bad_pix(coord, pixel_type, files, mean_file,
                         baseline, obs_start, obs_mid, obs_end)
        new_entries = di.session.query(dark.pixel_table).filter(
            dark.pixel_table.type == pixel_type)

        assert new_entries.count() == 1
        assert new_entries[0].baseline_file == baseline
        assert np.all(new_entries[0].x_coord == coord[0])
        assert np.all(new_entries[0].y_coord == coord[1])
    finally:
        # clean up
        di.session.query(dark.pixel_table).filter(
            dark.pixel_table.type == pixel_type).delete()
        di.session.commit()
        assert di.session.query(dark.pixel_table).filter(
            dark.pixel_table.type == pixel_type).count() == 0


@pytest.mark.skipif(not has_test_db(), reason='Modifies test database.')
def test_exclude_existing_badpix():
    coord = ([9999], [9999])
    pixel_type = 'hot'

    dark = dark_monitor.Dark()
    dark.instrument = 'nircam'
    dark.detector = 'nrcalong'
    dark.identify_tables()

    # bad pixel type should raise error
    with pytest.raises(ValueError) as err:
        dark.exclude_existing_badpix(coord, 'test_bad_type')
    assert 'bad pixel type' in str(err)

    files = ['test.fits']
    obs_start = obs_mid = obs_end = datetime.datetime.now()
    baseline = 'test_baseline.fits'
    mean_file = 'test_meanfile.fits'
    try:
        # new pixel should not be found
        new_x, new_y = dark.exclude_existing_badpix(coord, pixel_type)
        assert new_x == [9999]
        assert new_y == [9999]

        # add pixel, test again
        dark.add_bad_pix(coord, pixel_type, files, mean_file,
                         baseline, obs_start, obs_mid, obs_end)
        new_entries = di.session.query(dark.pixel_table).filter(
            dark.pixel_table.baseline_file == baseline)

        assert new_entries.count() == 1

        # new pixel should be found
        new_x, new_y = dark.exclude_existing_badpix(coord, pixel_type)
        assert new_x == []
        assert new_y == []

    finally:
        # clean up
        di.session.query(dark.pixel_table).filter(
            dark.pixel_table.baseline_file == baseline).delete()
        di.session.commit()
        assert di.session.query(dark.pixel_table).filter(
            dark.pixel_table.baseline_file == baseline).count() == 0
