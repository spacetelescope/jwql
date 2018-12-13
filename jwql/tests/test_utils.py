#!/usr/bin/env python
"""Tests for the ``utils`` module.

Authors
-------

    - Lauren Chambers

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_utils.py
"""

import pytest

from jwql.utils.utils import get_config, filename_parser

@pytest.mark.xfail
def test_get_config():
    '''Assert that the ``get_config`` function successfuly creates a
    dictionary.
    '''
    settings = get_config()
    assert isinstance(settings, dict)


def test_filename_parser_filename():
    '''Generate a dictionary with parameters from a JWST filename.
    Assert that the dictionary matches what is expected.
    '''
    filename = 'jw00327001001_02101_00002_nrca1_rate.fits'
    filename_dict = filename_parser(filename)

    correct_dict = {'activity': '01',
                    'detector': 'nrca1',
                    'exposure_id': '00002',
                    'observation': '001',
                    'parallel_seq_id': '1',
                    'program_id': '00327',
                    'suffix': 'rate',
                    'visit': '001',
                    'visit_group': '02'}

    assert filename_dict == correct_dict

def test_filename_parser_filename_root():
    '''Generate a dictionary with parameters from a JWST filename.
    Assert that the dictionary matches what is expected.
    '''
    filename = 'jw00327001001_02101_00002_nrca1'
    filename_dict = filename_parser(filename)

    correct_dict = {'activity': '01',
                    'detector': 'nrca1',
                    'exposure_id': '00002',
                    'observation': '001',
                    'parallel_seq_id': '1',
                    'program_id': '00327',
                    'visit': '001',
                    'visit_group': '02'}

    assert filename_dict == correct_dict


def test_filename_parser_filepath():
    '''Generate a dictionary with parameters from a JWST filepath
    (not just the basename). Assert that the dictionary matches what
    is expected.
    '''
    filepath = '/test/dir/to/the/file/jw90002/jw90002001001_02102_00001_nis_rateints.fits'
    filename_dict = filename_parser(filepath)

    correct_dict = {'activity': '02',
                    'detector': 'nis',
                    'exposure_id': '00001',
                    'observation': '001',
                    'parallel_seq_id': '1',
                    'program_id': '90002',
                    'suffix': 'rateints',
                    'visit': '001',
                    'visit_group': '02'}

    assert filename_dict == correct_dict


def test_filename_parser_nonJWST():
    '''Attempt to generate a file parameter dictionary from a file
    that is not formatted in the JWST naming convention. Ensure the
    appropriate error is raised.
    '''
    with pytest.raises(ValueError,
                       match=r'Provided file .+ does not follow JWST naming conventions \(jw<PPPPP><OOO><VVV>_<GGSAA>_<EEEEE>_<detector>_<suffix>\.fits\)'):
        filename = 'not_a_jwst_file.fits'
        filename_parser(filename)
