#!/usr/bin/env python
"""Tests for the ``utils`` module.

Authors
-------

    - Lauren Chambers
    - Matthew Bourque

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_utils.py
"""

import os
from pathlib import Path
import pytest

from bokeh.models import LinearColorMapper
from bokeh.plotting import figure
import numpy as np

from jwql.utils.constants import ON_GITHUB_ACTIONS
from jwql.utils.utils import copy_files, get_config, filename_parser, filesystem_path, save_png, _validate_config


FILENAME_PARSER_TEST_DATA = [

    # Test full path
    ('/test/dir/to/the/file/public/jw90002/jw90002001001/jw90002001001_02102_00001_nis_rateints.fits',
     {'activity': '02',
      'detector': 'nis',
      'exposure_id': '00001',
      'filename_type': 'stage_1_and_2',
      'instrument': 'niriss',
      'observation': '001',
      'parallel_seq_id': '1',
      'program_id': '90002',
      'recognized_filename': True,
      'suffix': 'rateints',
      'visit': '001',
      'visit_group': '02',
      'file_root': 'jw90002001001_02102_00001_nis',
      'group_root': 'jw90002001001_02102_00001'}),

    # Test full stage 1 and 2 filename
    ('jw00327001001_02101_00002_nrca1_rate.fits',
     {'activity': '01',
      'detector': 'nrca1',
      'exposure_id': '00002',
      'filename_type': 'stage_1_and_2',
      'instrument': 'nircam',
      'observation': '001',
      'parallel_seq_id': '1',
      'program_id': '00327',
      'recognized_filename': True,
      'suffix': 'rate',
      'visit': '001',
      'visit_group': '02',
      'file_root': 'jw00327001001_02101_00002_nrca1',
      'group_root': 'jw00327001001_02101_00002'}),

    # Test root stage 1 and 2 filename
    ('jw00327001001_02101_00002_nrca1',
     {'activity': '01',
      'detector': 'nrca1',
      'exposure_id': '00002',
      'filename_type': 'stage_1_and_2',
      'instrument': 'nircam',
      'observation': '001',
      'parallel_seq_id': '1',
      'program_id': '00327',
      'recognized_filename': True,
      'visit': '001',
      'visit_group': '02',
      'file_root': 'jw00327001001_02101_00002_nrca1',
      'group_root': 'jw00327001001_02101_00002'}),

    # Test stage 2 MSA metadata filename
    ('jw01118008001_01_msa.fits',
        {'filename_type': 'stage_2_msa',
         'instrument': 'nirspec',
         'observation': '008',
         'program_id': '01118',
         'recognized_filename': True,
         'visit': '001',
         'detector': 'Unknown',
         'file_root': 'jw01118008001_01_msa',
         'group_root': 'jw01118008001_01_msa'}),

    # Test full stage 2c filename
    ('jw94015002002_02108_00001_mirimage_o002_crf.fits',
     {'ac_id': 'o002',
      'activity': '08',
      'detector': 'mirimage',
      'exposure_id': '00001',
      'filename_type': 'stage_2c',
      'instrument': 'miri',
      'observation': '002',
      'parallel_seq_id': '1',
      'program_id': '94015',
      'recognized_filename': True,
      'suffix': 'crf',
      'visit': '002',
      'visit_group': '02',
      'file_root': 'jw94015002002_02108_00001_mirimage',
      'group_root': 'jw94015002002_02108_00001'}),

    # Test root stage 2c filename
    ('jw90001001003_02101_00001_nis_o001',
     {'ac_id': 'o001',
      'activity': '01',
      'detector': 'nis',
      'exposure_id': '00001',
      'filename_type': 'stage_2c',
      'instrument': 'niriss',
      'observation': '001',
      'parallel_seq_id': '1',
      'program_id': '90001',
      'recognized_filename': True,
      'visit': '003',
      'visit_group': '02',
      'file_root': 'jw90001001003_02101_00001_nis',
      'group_root': 'jw90001001003_02101_00001'}),

    # Test full stage 3 filename with target_id
    ('jw80600-o009_t001_miri_f1130w_i2d.fits',
     {'ac_id': 'o009',
      'filename_type': 'stage_3_target_id',
      'instrument': 'miri',
      'optical_elements': 'f1130w',
      'program_id': '80600',
      'recognized_filename': True,
      'suffix': 'i2d',
      'target_id': 't001',
      'detector': 'Unknown',
      'file_root': 'jw80600-o009_t001_miri_f1130w',
      'group_root': 'jw80600-o009_t001_miri_f1130w'}),

    # Test full stage 3 filename with target_id and different ac_id
    ('jw80600-c0001_t001_miri_f1130w_i2d.fits',
     {'ac_id': 'c0001',
      'filename_type': 'stage_3_target_id',
      'instrument': 'miri',
      'optical_elements': 'f1130w',
      'program_id': '80600',
      'recognized_filename': True,
      'suffix': 'i2d',
      'target_id': 't001',
      'detector': 'Unknown',
      'file_root': 'jw80600-c0001_t001_miri_f1130w',
      'group_root': 'jw80600-c0001_t001_miri_f1130w'}),

    # Test full stage 3 filename with source_id
    ('jw80600-o009_s00001_miri_f1130w_i2d.fits',
     {'ac_id': 'o009',
      'filename_type': 'stage_3_source_id',
      'instrument': 'miri',
      'optical_elements': 'f1130w',
      'program_id': '80600',
      'recognized_filename': True,
      'source_id': 's00001',
      'suffix': 'i2d',
      'detector': 'Unknown',
      'file_root': 'jw80600-o009_s00001_miri_f1130w',
      'group_root': 'jw80600-o009_s00001_miri_f1130w'}),

    # Test stage 3 filename with target_id and epoch
    ('jw80600-o009_t001-epoch1_miri_f1130w_i2d.fits',
     {'ac_id': 'o009',
      'filename_type': 'stage_3_target_id_epoch',
      'instrument': 'miri',
      'epoch': '1',
      'optical_elements': 'f1130w',
      'program_id': '80600',
      'recognized_filename': True,
      'suffix': 'i2d',
      'target_id': 't001',
      'detector': 'Unknown',
      'file_root': 'jw80600-o009_t001-epoch1_miri_f1130w',
      'group_root': 'jw80600-o009_t001-epoch1_miri_f1130w'}),

    # Test stage 3 filename with source_id and epoch
    ('jw80600-o009_s00001-epoch1_miri_f1130w_i2d.fits',
     {'ac_id': 'o009',
      'filename_type': 'stage_3_source_id_epoch',
      'instrument': 'miri',
      'epoch': '1',
      'optical_elements': 'f1130w',
      'program_id': '80600',
      'recognized_filename': True,
      'source_id': 's00001',
      'suffix': 'i2d',
      'detector': 'Unknown',
      'file_root': 'jw80600-o009_s00001-epoch1_miri_f1130w',
      'group_root': 'jw80600-o009_s00001-epoch1_miri_f1130w'}),

    # Test root stage 3 filename with target_id
    ('jw80600-o009_t001_miri_f1130w',
     {'ac_id': 'o009',
      'filename_type': 'stage_3_target_id',
      'instrument': 'miri',
      'optical_elements': 'f1130w',
      'program_id': '80600',
      'recognized_filename': True,
      'target_id': 't001',
      'detector': 'Unknown',
      'file_root': 'jw80600-o009_t001_miri_f1130w',
      'group_root': 'jw80600-o009_t001_miri_f1130w'}),

    # Test root stage 3 filename with source_id
    ('jw80600-o009_s00001_miri_f1130w',
     {'ac_id': 'o009',
      'filename_type': 'stage_3_source_id',
      'instrument': 'miri',
      'optical_elements': 'f1130w',
      'program_id': '80600',
      'recognized_filename': True,
      'source_id': 's00001',
      'detector': 'Unknown',
      'file_root': 'jw80600-o009_s00001_miri_f1130w',
      'group_root': 'jw80600-o009_s00001_miri_f1130w'}),

    # Test full time series filename
    ('jw00733003001_02101_00002-seg001_nrs1_rate.fits',
     {'activity': '01',
      'detector': 'nrs1',
      'exposure_id': '00002',
      'filename_type': 'time_series',
      'instrument': 'nirspec',
      'observation': '003',
      'parallel_seq_id': '1',
      'program_id': '00733',
      'recognized_filename': True,
      'segment': '001',
      'suffix': 'rate',
      'visit': '001',
      'visit_group': '02',
      'file_root': 'jw00733003001_02101_00002-seg001_nrs1',
      'group_root': 'jw00733003001_02101_00002-seg001'}),

    # Test full time series filename for stage 2c
    ('jw00733003001_02101_00002-seg001_nrs1_o001_crfints.fits',
     {'ac_id': 'o001',
      'activity': '01',
      'detector': 'nrs1',
      'exposure_id': '00002',
      'filename_type': 'time_series_2c',
      'instrument': 'nirspec',
      'observation': '003',
      'parallel_seq_id': '1',
      'program_id': '00733',
      'recognized_filename': True,
      'segment': '001',
      'suffix': 'crfints',
      'visit': '001',
      'visit_group': '02',
      'file_root': 'jw00733003001_02101_00002-seg001_nrs1',
      'group_root': 'jw00733003001_02101_00002-seg001'}),

    # Test root time series filename
    ('jw00733003001_02101_00002-seg001_nrs1',
     {'activity': '01',
      'detector': 'nrs1',
      'exposure_id': '00002',
      'filename_type': 'time_series',
      'instrument': 'nirspec',
      'observation': '003',
      'parallel_seq_id': '1',
      'program_id': '00733',
      'recognized_filename': True,
      'segment': '001',
      'visit': '001',
      'visit_group': '02',
      'file_root': 'jw00733003001_02101_00002-seg001_nrs1',
      'group_root': 'jw00733003001_02101_00002-seg001'}),

    # Test full guider ID filename
    ('jw00729011001_gs-id_1_image_cal.fits',
     {'date_time': None,
      'filename_type': 'guider',
      'guide_star_attempt_id': '1',
      'guider_mode': 'id',
      'instrument': 'fgs',
      'observation': '011',
      'program_id': '00729',
      'recognized_filename': True,
      'suffix': 'image_cal',
      'visit': '001',
      'detector': 'Unknown',
      'file_root': 'jw00729011001_gs-id_1',
      'group_root': 'jw00729011001_gs-id_1'}),

    # Test full guider ID filename with 2-digit attempts
    ('jw00729011001_gs-id_12_image_cal.fits',
     {'date_time': None,
      'filename_type': 'guider',
      'guide_star_attempt_id': '12',
      'guider_mode': 'id',
      'instrument': 'fgs',
      'observation': '011',
      'program_id': '00729',
      'recognized_filename': True,
      'suffix': 'image_cal',
      'visit': '001',
      'detector': 'Unknown',
      'file_root': 'jw00729011001_gs-id_12',
      'group_root': 'jw00729011001_gs-id_12'}),

    # Test root guider ID filename
    ('jw00327001001_gs-id_2',
     {'date_time': None,
      'filename_type': 'guider',
      'guide_star_attempt_id': '2',
      'guider_mode': 'id',
      'instrument': 'fgs',
      'observation': '001',
      'program_id': '00327',
      'recognized_filename': True,
      'visit': '001',
      'detector': 'Unknown',
      'file_root': 'jw00327001001_gs-id_2',
      'group_root': 'jw00327001001_gs-id_2'}),

    # Test root guider ID filename with 2-digit attempts
    ('jw00327001001_gs-id_12',
     {'date_time': None,
      'filename_type': 'guider',
      'guide_star_attempt_id': '12',
      'guider_mode': 'id',
      'instrument': 'fgs',
      'observation': '001',
      'program_id': '00327',
      'recognized_filename': True,
      'visit': '001',
      'detector': 'Unknown',
      'file_root': 'jw00327001001_gs-id_12',
      'group_root': 'jw00327001001_gs-id_12'}),

    # Test full guider non-ID filename
    ('jw86600048001_gs-fg_2016018175411_stream.fits',
     {'date_time': '2016018175411',
      'filename_type': 'guider',
      'guide_star_attempt_id': None,
      'guider_mode': 'fg',
      'instrument': 'fgs',
      'observation': '048',
      'program_id': '86600',
      'recognized_filename': True,
      'suffix': 'stream',
      'visit': '001',
      'detector': 'Unknown',
      'file_root': 'jw86600048001_gs-fg_2016018175411',
      'group_root': 'jw86600048001_gs-fg_2016018175411'}),

    # Test root guider non-ID filename
    ('jw00729011001_gs-acq2_2019155024808',
     {'date_time': '2019155024808',
      'filename_type': 'guider',
      'guide_star_attempt_id': None,
      'guider_mode': 'acq2',
      'instrument': 'fgs',
      'observation': '011',
      'program_id': '00729',
      'recognized_filename': True,
      'visit': '001',
      'detector': 'Unknown',
      'file_root': 'jw00729011001_gs-acq2_2019155024808',
      'group_root': 'jw00729011001_gs-acq2_2019155024808'}),

    # Test segmented guider file
    ('jw01118005001_gs-fg_2022150070312-seg002_uncal.fits',
     {'date_time': '2022150070312',
      'filename_type': 'guider_segment',
      'guide_star_attempt_id': None,
      'guider_mode': 'fg',
      'instrument': 'fgs',
      'observation': '005',
      'program_id': '01118',
      'recognized_filename': True,
      'segment': '002',
      'suffix': 'uncal',
      'visit': '001',
      'detector': 'Unknown',
      'file_root': 'jw01118005001_gs-fg_2022150070312-seg002',
      'group_root': 'jw01118005001_gs-fg_2022150070312-seg002'}),

    # Test msa file
    ('jw02560013001_01_msa.fits',
     {'program_id': '02560',
      'recognized_filename': True,
      'observation': '013',
      'visit': '001',
      'filename_type': 'stage_2_msa',
      'instrument': 'nirspec',
      'detector': 'Unknown',
      'file_root': 'jw02560013001_01_msa',
      'group_root': 'jw02560013001_01_msa'})
]


def test_copy_files():
    """Test that files are copied successfully"""

    # Create an example file to be copied
    data_dir = os.path.dirname(__file__)
    file_to_copy = 'file.txt'
    original_file = os.path.join(data_dir, file_to_copy)
    Path(original_file).touch()
    assert os.path.exists(original_file), 'Failed to create original test file.'

    # Make a copy one level up
    new_location = os.path.abspath(os.path.join(data_dir, '../'))
    copied_file = os.path.join(new_location, file_to_copy)

    # Copy the file
    success, failure = copy_files([original_file], new_location)
    assert success == [copied_file]
    assert os.path.isfile(copied_file)

    # Remove the copy
    os.remove(original_file)
    os.remove(copied_file)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_config():
    """Assert that the ``get_config`` function successfully creates a
    dictionary.
    """
    settings = get_config()
    assert isinstance(settings, dict)


@pytest.mark.parametrize('filename, solution', FILENAME_PARSER_TEST_DATA)
def test_filename_parser(filename, solution):
    """Generate a dictionary with parameters from a JWST filename.
    Assert that the dictionary matches what is expected.

    Parameters
    ----------
    filename : str
        The filename to test (e.g. ``jw00327001001_02101_00002_nrca1_rate.fits``)
    solution : dict
        A dictionary of the expected result
    """

    assert filename_parser(filename) == solution


def test_filename_parser_non_jwst():
    """Attempt to generate a file parameter dictionary from a file
    that is not formatted in the JWST naming convention. Ensure the
    appropriate error is raised.
    """
    filename = 'not_a_jwst_file.fits'
    filename_dict = filename_parser(filename)
    assert 'recognized_filename' in filename_dict
    assert filename_dict['recognized_filename'] is False


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_filesystem_path():
    """Test that a file's location in the filesystem is returned"""
    filename = 'jw02733001001_02101_00001_nrcb2_rateints.fits'
    check = filesystem_path(filename)
    location = os.path.join(get_config()['filesystem'], 'public', 'jw02733',
                            'jw02733001001', filename)

    assert check == location


def test_save_png():
    """Test that we can create a png file"""
    plot = figure(title='test', tools='')
    image = np.zeros((200, 200))
    image[100:105, 100:105] = 1
    ny, nx = image.shape
    mapper = LinearColorMapper(palette='Viridis256', low=0, high=1.1)
    imgplot = plot.image(image=[image], x=0, y=0, dw=nx, dh=ny, color_mapper=mapper, level="image")
    save_png(plot, filename='test.png')


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_validate_config():
    """Test that the config validator works."""
    # Make sure a bad config raises an error
    bad_config_dict = {"just": "one_key"}

    with pytest.raises(Exception) as excinfo:
        _validate_config(bad_config_dict)
    assert 'Provided config.json does not match the required JSON schema' \
           in str(excinfo.value), \
        'Failed to reject incorrect JSON dict.'

    # Make sure a good config does not!
    good_config_dict = {
        "admin_account": "",
        "auth_mast": "",
        "connection_string": "",
        "databases": {
            "engine": "",
            "name": "",
            "user": "",
            "password": "",
            "host": "",
            "port": ""
        },
        "django_databases": {
            "default": {
                "ENGINE": "",
                "NAME": "",
                "USER": "",
                "PASSWORD": "",
                "HOST": "",
                "PORT": ""
            },
            "monitors": {
                "ENGINE": "",
                "NAME": "",
                "USER": "",
                "PASSWORD": "",
                "HOST": "",
                "PORT": ""
            }
        },
        "django_debug": "",
        "jwql_dir": "",
        "jwql_version": "",
        "server_type": "",
        "log_dir": "",
        "mast_token": "",
        "outputs": "",
        "working": "",
        "preview_image_filesystem": "",
        "filesystem": "",
        "setup_file": "",
        "test_data": "",
        "test_dir": "",
        "thumbnail_filesystem": "",
        "cores": ""
    }

    is_valid = _validate_config(good_config_dict)
    assert is_valid is None, 'Failed to validate correct JSON dict'
