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

from astropy.io import fits
import numpy as np
import pytest

from jwql.database.database_interface import NIRCamReadnoiseQueryHistory, NIRCamReadnoiseStats, session # ruff: noqa
from jwql.instrument_monitors.common_monitors import readnoise_monitor
from jwql.tests.resources import has_test_db
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


@pytest.mark.skipif(not has_test_db(), reason='Modifies test database.')
def test_process(mocker, tmp_path):
    hdul = fits.HDUList([
        fits.PrimaryHDU(header=fits.Header({
            'DATE-OBS': 'test',
            'TIME-OBS': 'test', 'INSTRUME': 'NIRCam',
            'DETECTOR': 'nrcalong', 'READPATT': 'test',
            'SUBARRAY': 'test'})),
        fits.ImageHDU(np.zeros((10, 10, 10, 10)), name='SCI')])
    filename = str(tmp_path / 'test_uncal_file.fits')
    processed_file = str(tmp_path / 'test_refpix_file.fits')
    hdul.writeto(filename, overwrite=True)
    hdul.writeto(processed_file, overwrite=True)

    monitor = readnoise_monitor.Readnoise()
    monitor.instrument = 'nircam'
    monitor.detector = 'nrcalong'
    monitor.aperture = 'test'
    monitor.read_pattern = 'test'
    monitor.subarray = 'test'
    monitor.nints = 1
    monitor.ngroups = 1
    monitor.expstart = 9999.0
    monitor.data_dir = str(tmp_path)
    monitor.identify_tables()

    assert not monitor.file_exists_in_database(filename)

    # mock the pipeline run
    mocker.patch.object(readnoise_monitor, 'run_parallel_pipeline',
                        return_value={filename: processed_file})
    # mock amplifier info
    mocker.patch.object(readnoise_monitor.instrument_properties, 'amplifier_info',
                        return_value=('test', 'test'))
    mocker.patch.object(monitor, 'get_amp_stats',
                        return_value={'test': 0})
    # mock image creation
    mocker.patch.object(monitor, 'make_readnoise_image',
                        return_value=np.zeros(10))
    mocker.patch.object(monitor, 'make_histogram',
                        return_value=(np.zeros(10), np.zeros(10)))
    mocker.patch.object(monitor, 'image_to_png',
                        return_value=str(tmp_path / 'output.png'))
    # mock crds
    mocker.patch.object(readnoise_monitor.crds, 'getreferences',
                        side_effect=ValueError('no reffile'))

    try:
        monitor.process([filename])
        assert monitor.file_exists_in_database(filename)
    finally:
        # clean up
        query = session.query(monitor.stats_table).filter(
            monitor.stats_table.uncal_filename == filename)
        query.delete()
        session.commit()

        assert not monitor.file_exists_in_database(filename)
