#! /usr/bin/env python

"""Tests for the ``instrument_properties`` module.

Authors
-------

    - Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_instrument_properties.py
"""

import os
import pytest

import numpy as np

from jwql.utils import instrument_properties

ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

if not ON_GITHUB_ACTIONS:
    from jwql.utils.utils import get_config


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_amplifier_info():
    """Test that the correct number of amplifiers are found for a given
    file
    """

    data_dir = os.path.join(get_config()['test_dir'], 'dark_monitor')

    fullframe = instrument_properties.amplifier_info(os.path.join(data_dir, 'test_image_ff.fits'))
    fullframe_truth = (4, {'1': [(4, 512, 1), (4, 2044, 1)],
                           '2': [(512, 1024, 1), (4, 2044, 1)],
                           '3': [(1024, 1536, 1), (4, 2044, 1)],
                           '4': [(1536, 2044, 1), (4, 2044, 1)]})

    assert fullframe == fullframe_truth

    fullframe = instrument_properties.amplifier_info(os.path.join(data_dir, 'test_image_ff.fits'), omit_reference_pixels=False)
    fullframe_truth = (4, {'1': [(0, 512, 1), (0, 2048, 1)],
                           '2': [(512, 1024, 1), (0, 2048, 1)],
                           '3': [(1024, 1536, 1), (0, 2048, 1)],
                           '4': [(1536, 2048, 1), (0, 2048, 1)]})

    assert fullframe == fullframe_truth

    subarray = instrument_properties.amplifier_info(os.path.join(data_dir, 'test_image_1.fits'))
    subarray_truth = (1, {'1': [(0, 10, 1), (0, 10, 1)]})
    assert subarray == subarray_truth

    subarray_one = instrument_properties.amplifier_info(os.path.join(data_dir, 'test_image_grismstripe_one_amp.fits'))
    subarray_one_truth = (1, {'1': [(4, 2044, 1), (4, 64, 1)]})
    assert subarray_one == subarray_one_truth

    subarray_four = instrument_properties.amplifier_info(os.path.join(data_dir, 'test_image_grismstripe_four_amp.fits'))
    subarray_four_truth = (4, {'1': [(4, 512, 1), (4, 64, 1)],
                               '2': [(512, 1024, 1), (4, 64, 1)],
                               '3': [(1024, 1536, 1), (4, 64, 1)],
                               '4': [(1536, 2044, 1), (4, 64, 1)]})
    assert subarray_four == subarray_four_truth


def test_calc_frame_time():
    """Test calcuation of frametime for a given instrument/aperture"""

    nearir_fullframe = 10.73677
    nircam_160 = 0.27864
    nrc_fullframe = instrument_properties.calc_frame_time('nircam', 'NRCA1_FULL', 2048, 2048, 4)
    nrc_160 = instrument_properties.calc_frame_time('nircam', 'NRCA1_SUB160', 160, 160, 1)
    nrs_fullframe = instrument_properties.calc_frame_time('niriss', 'NIS_CEN', 2048, 2048, 4)
    # nrs_some_subarra = instrument_properies.calc_frame_time('niriss', '????', ??, ??, ?)

    print('STILL NEED TO ADD FRAMETIME CALCS FOR MIRI AND NIRSPEC TO THE CALC_FRAME_TIME_FUNCTION')
    print('CONFIRM NIRCAMSUB160 TIME ON JDOX')

    assert np.isclose(nrc_fullframe, nearir_fullframe, atol=0.001, rtol=0)
    assert np.isclose(nrc_160, nircam_160, atol=0.001, rtol=0)
    assert np.isclose(nrs_fullframe, nearir_fullframe, atol=0.001, rtol=0)
