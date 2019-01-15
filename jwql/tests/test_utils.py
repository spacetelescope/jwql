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

import pytest

from jwql.utils.utils import get_config, filename_parser


FILENAME_PARSER_TEST_DATA = [

# Test full path
('/test/dir/to/the/file/jw90002/jw90002001001_02102_00001_nis_rateints.fits',
    {'activity': '02',
     'detector': 'nis',
     'exposure_id': '00001',
     'observation': '001',
     'parallel_seq_id': '1',
     'program_id': '90002',
     'suffix': 'rateints',
     'visit': '001',
     'visit_group': '02'}),

# Test full stage 1 and 2 filename
('jw00327001001_02101_00002_nrca1_rate.fits',
    {'activity': '01',
     'detector': 'nrca1',
     'exposure_id': '00002',
     'observation': '001',
     'parallel_seq_id': '1',
     'program_id': '00327',
     'suffix': 'rate',
     'visit': '001',
     'visit_group': '02'}),

# Test root stage 1 and 2 filename
('jw00327001001_02101_00002_nrca1',
    {'activity': '01',
     'detector': 'nrca1',
     'exposure_id': '00002',
     'observation': '001',
     'parallel_seq_id': '1',
     'program_id': '00327',
     'visit': '001',
     'visit_group': '02'}),

# Test full stage 3 filename
('jw80600-o009_t001_miri_f1130w_i2d.fits',
    {'ac_id': 'o009',
     'instrument': 'miri',
     'optical_elements': 'f1130w',
     'program_id': '80600',
     'suffix': 'i2d',
     'target_id': 't001'}),

# Test stage 3 filename with epoch
('jw80600-o009_t001-epoch1_miri_f1130w_i2d.fits',
    {'ac_id': 'o009',
     'instrument': 'miri',
     'epoch': '1',
     'optical_elements': 'f1130w',
     'program_id': '80600',
     'suffix': 'i2d',
     'target_id': 't001'}),

# Test root stage 3 filename
('jw80600-o009_t001_miri_f1130w',
    {'ac_id': 'o009',
     'instrument': 'miri',
     'optical_elements': 'f1130w',
     'program_id': '80600',
     'target_id': 't001'}),

# Test full time series filename
('jw00733003001_02101_00002-seg001_nrs1_rate.fits',
    {'activity': '01',
    'detector': 'nrs1',
    'exposure_id': '00002',
    'observation': '003',
    'parallel_seq_id': '1',
    'program_id': '00733',
    'segment': '001',
    'suffix': 'rate',
    'visit': '001',
    'visit_group': '02'}),

# Test root time series filename
('jw00733003001_02101_00002-seg001_nrs1',
    {'activity': '01',
    'detector': 'nrs1',
    'exposure_id': '00002',
    'observation': '003',
    'parallel_seq_id': '1',
    'program_id': '00733',
    'segment': '001',
    'visit': '001',
    'visit_group': '02'})
]


@pytest.mark.xfail
def test_get_config():
    """Assert that the ``get_config`` function successfuly creates a
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


def test_filename_parser_nonJWST():
    """Attempt to generate a file parameter dictionary from a file
    that is not formatted in the JWST naming convention. Ensure the
    appropriate error is raised.
    """
    with pytest.raises(ValueError,
                       match=r'Provided file .+ does not follow JWST naming conventions \(jw<PPPPP><OOO><VVV>_<GGSAA>_<EEEEE>_<detector>_<suffix>\.fits\)'):
        filename = 'not_a_jwst_file.fits'
        filename_parser(filename)
