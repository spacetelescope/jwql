#! /usr/bin/env python

"""Tests for the bad pixel monitor module.

Authors
-------

    - Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_badpix_monitor.py
"""
import datetime

import numpy as np
import os
import pytest

from jwst.datamodels import dqflags

from jwql.database.database_interface import session
from jwql.instrument_monitors.common_monitors import bad_pixel_monitor
from jwql.tests.resources import has_test_db

# Determine if tests are being run on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


def test_bad_map_to_list():
    """Check that bad pixel locations are correctly retrieved from an image
    """
    # Create empty DQ image
    image = np.zeros((7, 7), dtype=np.uint16)

    # Set bad pixel locations
    do_not_use = ([0, 2, 4, 6], [0, 2, 4, 6])
    hot = ([0, 1, 3, 5], [0, 2, 4, 6])
    rc = ([0, 2, 4, 6], [0, 1, 3, 5])

    # Populate with bad pixels
    image[do_not_use] = dqflags.pixel['DO_NOT_USE']
    image[hot] += dqflags.pixel['HOT']
    image[rc] += dqflags.pixel['RC']

    # Call the bad pixel monitor
    x_do_not_use, y_do_not_use = bad_pixel_monitor.bad_map_to_list(image, 'DO_NOT_USE')
    x_hot, y_hot = bad_pixel_monitor.bad_map_to_list(image, 'HOT')
    x_rc, y_rc = bad_pixel_monitor.bad_map_to_list(image, 'RC')

    # Test
    assert do_not_use == (y_do_not_use, x_do_not_use)
    assert hot == (y_hot, x_hot)
    assert rc == (y_rc, x_rc)


def test_check_for_sufficient_files():
    """Be sure that the file threshold values are being used correctly
    """
    input_files = ['file1.fits', 'file2.fits', 'file1.fits', 'file3.fits', 'file1.fits']
    instrument = 'nircam'
    aperture = 'NRCA1_FULL'
    threshold = 2
    file_type = 'darks'

    files, to_run = bad_pixel_monitor.check_for_sufficient_files(input_files, instrument, aperture, threshold, file_type)
    assert files == ['file1.fits', 'file2.fits', 'file3.fits']
    assert to_run is True

    threshold = 4
    files, to_run = bad_pixel_monitor.check_for_sufficient_files(input_files, instrument, aperture, threshold, file_type)
    assert files is None
    assert to_run is False


def test_exclude_crds_mask_pix():
    """Test that bad pixel images are differentiated correctly
    """
    common_bad = ([0, 1, 2, 3, 4], [0, 1, 2, 3, 4])
    bad1_only = ([0, 1, 3, 4], [4, 3, 1, 0])
    bad2_only = ([3, 3, 3, 3], [0, 1, 2, 4])

    bad1 = np.zeros((5, 5), dtype=np.uint8)
    bad1[common_bad] = 1
    bad1[bad1_only] = 2

    bad2 = np.zeros((5, 5), dtype=np.uint8)
    bad2[common_bad] = 1
    bad2[bad2_only] = 4

    # Create a mask to help with indexing
    mask = np.zeros(bad1.shape, dtype=bool)
    mask[bad1_only] = True

    diff = bad_pixel_monitor.exclude_crds_mask_pix(bad1, bad2)
    assert np.all(diff[mask] == 2)
    assert np.all(diff[~mask] == 0)

    # Test the reverse case
    mask = np.zeros(bad2.shape, dtype=bool)
    mask[bad2_only] = True

    diff = bad_pixel_monitor.exclude_crds_mask_pix(bad2, bad1)
    assert np.all(diff[mask] == 4)
    assert np.all(diff[~mask] == 0)


def test_filter_query_results():
    """Test MAST query filtering to extract most common filter/pupil and
    acceptable readout patterns
    """
    badpix = bad_pixel_monitor.BadPixels()
    badpix.instrument = 'nircam'

    dict1 = {'filter': 'F070W', 'pupil': 'CLEAR', 'readpatt': 'RAPID'}
    dict2 = {'filter': 'F090W', 'pupil': 'CLEAR', 'readpatt': 'BRIGHT1'}
    dict3 = {'filter': 'F070W', 'pupil': 'CLEAR', 'readpatt': 'BRIGHT1'}
    query_results = [dict1, dict2, dict1, dict1, dict3, dict1]

    filtered = badpix.filter_query_results(query_results, 'flat')

    assert filtered == [dict1, dict1, dict1, dict1]

    # NIRSpec
    badpix.instrument = 'nirspec'

    dict1 = {'filter': 'F070W', 'grating': 'CLEAR', 'readpatt': 'NRSRAPID'}
    dict2 = {'filter': 'F070W', 'grating': 'CLEAR', 'readpatt': 'NRSIRS2'}
    dict3 = {'filter': 'F070W', 'grating': 'CLEAR', 'readpatt': 'NRSRAPID'}
    query_results = [dict1, dict2, dict1, dict1, dict3, dict1]

    filtered = badpix.filter_query_results(query_results, 'flat')

    assert filtered == [dict1, dict1, dict1, dict3, dict1]


nrc_list = ['NRCA1_FULL', 'NRCB1_FULL', 'NRCA2_FULL', 'NRCB2_FULL', 'NRCA3_FULL', 'NRCB3_FULL',
            'NRCA4_FULL', 'NRCB4_FULL', 'NRCA5_FULL', 'NRCB5_FULL']
nis_list = ['NIS_CEN']
nrs_list = ['NRS1_FULL', 'NRS2_FULL']
miri_list = [('MIRIMAGE', 'MIRIM_FULL'), ('MIRIFULONG', 'MIRIM_FULL'), ('MIRIFUSHORT', 'MIRIM_FULL')]
fgs_list = ['FGS1_FULL', 'FGS2_FULL']


@pytest.mark.parametrize("instrument,expected_list", [("nircam", nrc_list), ("niriss", nis_list),
                                                      ("nirspec", nrs_list), ("miri", miri_list), ("fgs", fgs_list)])
def test_get_possible_apertures(instrument, expected_list):
    """Make sure the correct apertures are returned for the given instrument
    """
    badpix = bad_pixel_monitor.BadPixels()
    badpix.instrument = instrument
    ap_list = badpix.get_possible_apertures()
    assert ap_list == expected_list


def test_identify_tables():
    """Be sure the correct database tables are identified
    """
    badpix = bad_pixel_monitor.BadPixels()
    badpix.instrument = 'nircam'
    badpix.identify_tables()
    assert badpix.query_table == eval('NIRCamBadPixelQueryHistory')
    assert badpix.pixel_table == eval('NIRCamBadPixelStats')


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_locate_rate_files():
    """Test that rate files are found in filesystem"""

    uncal_files = ['jw02733002001_02101_00001_mirimage_uncal.fits',
                   'jw02733002001_02101_00002_mirimage_uncal.fits']
    ratefiles, ratefiles2copy = bad_pixel_monitor.locate_rate_files(uncal_files)

    rates = [os.path.basename(entry) for entry in ratefiles]
    rates2copy = [os.path.basename(entry) for entry in ratefiles2copy]

    expected = ['jw02733002001_02101_00001_mirimage_rateints.fits',
                'jw02733002001_02101_00002_mirimage_rateints.fits']
    assert rates == expected
    assert rates2copy == expected


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_locate_uncal_files():
    """Test the filesystem search for uncal files
    """
    file1 = 'jw02733002001_02101_00001_mirimage_rate.fits'
    file2 = 'jw02733002001_02101_00002_mirimage_uncal.fits'
    query_results = [{'filename': file1},
                     {'filename': file2}]

    found = bad_pixel_monitor.locate_uncal_files(query_results)

    found_base = [os.path.basename(entry) for entry in found]
    assert found_base[0] == file1.replace('rate', 'uncal')
    assert found_base[1] == file2


def test_make_crds_parameter_dict():
    """Test that the dictionary to be used for CRDS queries is properly
    created
    """
    badpix = bad_pixel_monitor.BadPixels()
    badpix.instrument = 'nircam'
    badpix.detector = 'nrcalong'
    params = badpix.make_crds_parameter_dict()
    assert params['INSTRUME'] == 'NIRCAM'
    assert params['DETECTOR'] == 'NRCALONG'
    assert params['CHANNEL'] == 'LONG'


@pytest.mark.skipif(not has_test_db(), reason='Modifies test database.')
def test_add_bad_pix():
    coord = ([1, 2, 3], [4, 5, 6])
    pixel_type = 'test_new_pixel_type'
    files = ['test.fits']
    obs_start = obs_mid = obs_end = datetime.datetime.now()
    baseline = 'baseline.fits'

    badpix = bad_pixel_monitor.BadPixels()
    badpix.instrument = 'nircam'
    badpix.detector = 'nrcalong'
    badpix.identify_tables()

    try:
        badpix.add_bad_pix(coord, pixel_type, files, obs_start,
                           obs_mid, obs_end, baseline)
        new_entries = session.query(badpix.pixel_table).filter(
            badpix.pixel_table.type == pixel_type)

        assert new_entries.count() == 1
        assert new_entries[0].baseline_file == baseline
        assert np.all(new_entries[0].x_coord == coord[0])
        assert np.all(new_entries[0].y_coord == coord[1])
    finally:
        # clean up
        session.query(badpix.pixel_table).filter(
            badpix.pixel_table.type == pixel_type).delete()
        session.commit()
        assert session.query(badpix.pixel_table).filter(
            badpix.pixel_table.type == pixel_type).count() == 0


@pytest.mark.skipif(not has_test_db(), reason='Modifies test database.')
def test_exclude_existing_badpix():
    coord = ([9999], [9999])
    pixel_type = 'hot'

    badpix = bad_pixel_monitor.BadPixels()
    badpix.instrument = 'nircam'
    badpix.detector = 'nrcalong'
    badpix.identify_tables()

    # bad pixel type should raise error
    with pytest.raises(ValueError) as err:
        badpix.exclude_existing_badpix(coord, 'test_bad_type')
    assert 'bad pixel type' in str(err)

    # new pixel should not be found
    new_x, new_y = badpix.exclude_existing_badpix(coord, pixel_type)
    assert new_x == [9999]
    assert new_y == [9999]

    # add pixel, test again
    files = ['test.fits']
    obs_start = obs_mid = obs_end = datetime.datetime.now()
    baseline = 'test_baseline.fits'

    try:
        badpix.add_bad_pix(coord, pixel_type, files, obs_start,
                           obs_mid, obs_end, baseline)
        new_entries = session.query(badpix.pixel_table).filter(
            badpix.pixel_table.baseline_file == baseline)

        assert new_entries.count() == 1

        # new pixel should be found
        new_x, new_y = badpix.exclude_existing_badpix(coord, pixel_type)
        assert new_x == []
        assert new_y == []

    finally:
        # clean up
        session.query(badpix.pixel_table).filter(
            badpix.pixel_table.baseline_file == baseline).delete()
        session.commit()
        assert session.query(badpix.pixel_table).filter(
            badpix.pixel_table.baseline_file == baseline).count() == 0
