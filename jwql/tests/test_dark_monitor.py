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

import os
import pytest

from astropy.time import Time
import numpy as np

from jwql.instrument_monitors.common_monitors import dark_monitor
from jwql.utils.utils import get_config

ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


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


@pytest.mark.skipif(ON_JENKINS,
                    reason='Requires access to central storage.')
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


def test_mast_query_darks():
    """Test that the MAST query for darks is functional"""

    instrument = 'NIRCAM'
    aperture = 'NRCA1_FULL'
    start_date = Time("2016-01-01T00:00:00").mjd
    end_date = Time("2018-01-01T00:00:00").mjd
    query = dark_monitor.mast_query_darks(instrument, aperture, start_date, end_date)
    apernames = [entry['apername'] for entry in query]
    filenames = [entry['filename'] for entry in query]

    truth_filenames = ['jw96003001001_02201_00001_nrca1_dark.fits',
                       'jw82600013001_02102_00002_nrca1_dark.fits',
                       'jw82600013001_02101_00001_nrca1_dark.fits',
                       'jw82600013001_02103_00003_nrca1_dark.fits',
                       'jw82600013001_02103_00001_nrca1_dark.fits',
                       'jw82600013001_02103_00002_nrca1_dark.fits',
                       'jw82600016001_02101_00002_nrca1_dark.fits',
                       'jw82600016001_02101_00001_nrca1_dark.fits',
                       'jw82600013001_02102_00001_nrca1_dark.fits',
                       'jw82600016001_02103_00002_nrca1_dark.fits',
                       'jw82600016001_02103_00001_nrca1_dark.fits',
                       'jw82600016001_02103_00004_nrca1_dark.fits',
                       'jw82600016001_02103_00003_nrca1_dark.fits',
                       'jw82600016001_02102_00001_nrca1_dark.fits']

    assert len(query) == 14
    assert apernames == [aperture]*len(query)
    assert filenames == truth_filenames


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
