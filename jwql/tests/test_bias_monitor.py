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
import shutil

from astropy.io import fits
import numpy as np

from jwql.database.database_interface import NIRCamBiasQueryHistory, NIRCamBiasStats
from jwql.instrument_monitors.common_monitors import bias_monitor
from jwql.utils.utils import get_config

ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


def test_collapse_image():
    """Test that the image is collapsed correctly along its axes"""

    monitor = bias_monitor.Bias()

    # Create test data and its corresponding collapsed arrays
    image = np.arange(100).reshape(10, 10)
    collapsed_rows_truth = np.arange(4.5, 95, 10)
    collapsed_columns_truth = np.arange(45, 55)

    # Find the collapsed arrays using the bias monitor
    collapsed_rows, collapsed_columns = monitor.collapse_image(image)

    assert np.all(collapsed_rows == collapsed_rows_truth)
    assert np.all(collapsed_columns == collapsed_columns_truth)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_extract_zeroth_group():
    """Test the zeroth group file creation"""

    monitor = bias_monitor.Bias()
    monitor.data_dir = os.path.join(get_config()['test_dir'], 'bias_monitor')

    # Create a copy of the test file and get its zeroth group data
    test_file = os.path.join(monitor.data_dir, 'test_image_1.fits')
    data_truth = fits.getdata(test_file, 'SCI')[0, 0, :, :]
    filename = test_file.replace('.fits', '_copy.fits')
    shutil.copy(test_file, filename)

    # Extract the zeroth group using the bias monitor
    output_filename = monitor.extract_zeroth_group(filename)
    os.chmod(output_filename, 508)
    data = fits.getdata(output_filename, 'SCI')[0, 0, :, :]

    # Remove the copied test file and its zeroth group file so this test can be properly repeated
    os.remove(output_filename)
    os.remove(filename)

    assert np.all(data == data_truth)


def test_get_amp_medians():
    """Test that the amp medians are calculated correctly"""

    monitor = bias_monitor.Bias()
    monitor.instrument = 'nircam'

    # Create test data and its corresponding amp medians
    image = np.arange(144).reshape(12, 12)
    amps = {'1': [(0, 6, 1), (0, 12, 1)],
            '2': [(6, 12, 1), (0, 12, 1)]}
    amp_medians_truth = {'amp1_even_med': 69.0,
                         'amp1_odd_med': 68.0,
                         'amp2_even_med': 75.0,
                         'amp2_odd_med': 74.0}

    # Find the amp medians using the bias monitor
    amp_medians = monitor.get_amp_medians(image, amps)

    assert amp_medians == amp_medians_truth


def test_identify_tables():
    """Be sure the correct database tables are identified"""

    monitor = bias_monitor.Bias()
    monitor.instrument = 'nircam'
    monitor.identify_tables()

    assert monitor.query_table == eval('NIRCamBiasQueryHistory')
    assert monitor.stats_table == eval('NIRCamBiasStats')


def test_make_histogram():
    """Test histogram creation"""

    monitor = bias_monitor.Bias()

    # Create test data and its corresponding histogram stats
    data = np.zeros((100, 100))
    counts_truth = [10000]
    bin_centers_truth = [0.0]

    # Find the histogram stats of the test data using the bias monitor
    counts, bin_centers = monitor.make_histogram(data)
    counts, bin_centers = list(counts), list(bin_centers)

    assert counts == counts_truth
    assert bin_centers == bin_centers_truth
