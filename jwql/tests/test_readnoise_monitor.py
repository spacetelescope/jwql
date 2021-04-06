#! /usr/bin/env python

"""Tests for the ``readnoise_monitor`` module.

Authors
-------

    - Ben Sunnquist

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_readnoise_monitor.py
"""

from collections import OrderedDict
import os
import pytest

import numpy as np

from jwql.database.database_interface import NIRCamReadnoiseQueryHistory, NIRCamReadnoiseStats
from jwql.instrument_monitors.common_monitors import readnoise_monitor
from jwql.utils.utils import get_config


ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


def test_determine_pipeline_steps():
    """Test the correct pipeline steps are called"""

    monitor = readnoise_monitor.Readnoise()
    monitor.instrument = 'NIRCAM'
    monitor.read_pattern = 'RAPID'

    # Create dictionary of expected pipeline steps
    pipeline_steps_truth = OrderedDict([('group_scale', False),
                                        ('dq_init', True),
                                        ('superbias', True),
                                        ('refpix', True)])

    # Find the necessary pipeline steps using the readnoise monitor
    pipeline_steps = monitor.determine_pipeline_steps()

    assert pipeline_steps == pipeline_steps_truth


def test_get_amp_stats():
    """Test amp stat calculations"""

    monitor = readnoise_monitor.Readnoise()

    # Create test data and its corresponding amp stats
    data = np.zeros((100, 100))
    amps = {'1': [(0, 100, 1), (0, 100, 1)]}
    amp_stats_truth = {'amp1_mean': 0.0,
                       'amp1_stddev': 0.0,
                       'amp1_n': np.array([10000]),
                       'amp1_bin_centers': np.array([0.0])}

    # Find the amp stats using the readnoise monitor
    amp_stats = monitor.get_amp_stats(data, amps)

    assert amp_stats == amp_stats_truth


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_metadata():
    """Test retrieval of metadata from input file"""

    monitor = readnoise_monitor.Readnoise()
    filename = os.path.join(get_config()['test_dir'], 'readnoise_monitor', 'test_image_1.fits')
    monitor.get_metadata(filename)

    assert monitor.detector == 'NRCA1'
    assert monitor.read_pattern == 'BRIGHT1'
    assert monitor.subarray == 'FULL'
    assert monitor.nints == 3
    assert monitor.ngroups == 4
    assert monitor.substrt1 == 1
    assert monitor.substrt2 == 1
    assert monitor.subsize1 == 2048
    assert monitor.subsize2 == 2048
    assert monitor.date_obs == '2016-01-18'
    assert monitor.time_obs == '04:35:14.523'
    assert monitor.expstart == '2016-01-18T04:35:14.523'


def test_identify_tables():
    """Be sure the correct database tables are identified"""

    monitor = readnoise_monitor.Readnoise()
    monitor.instrument = 'nircam'
    monitor.identify_tables()

    assert monitor.query_table == eval('NIRCamReadnoiseQueryHistory')
    assert monitor.stats_table == eval('NIRCamReadnoiseStats')


def test_make_readnoise_image():
    """Test readnoise image creation"""

    monitor = readnoise_monitor.Readnoise()

    # Create test data and its corresponding readnoise
    data = np.arange(200).reshape(1, 8, 5, 5)
    readnoise_truth = np.zeros((5, 5))

    # Find the readnoise in the test data using the readnoise monitor
    readnoise = monitor.make_readnoise_image(data)

    assert np.all(readnoise == readnoise_truth)


def test_make_histogram():
    """Test histogram creation"""

    monitor = readnoise_monitor.Readnoise()

    # Create test data and its corresponding histogram stats
    data = np.zeros((100, 100))
    counts_truth = [10000]
    bin_centers_truth = [0.0]

    # Find the histogram stats of the test data using the readnoise monitor
    counts, bin_centers = monitor.make_histogram(data)
    counts, bin_centers = list(counts), list(bin_centers)

    assert counts == counts_truth
    assert bin_centers == bin_centers_truth
