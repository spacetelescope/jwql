#! /usr/bin/env python

"""Tests for the ``dark_monitor`` module.

Authors
-------

    Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_dark_monitor.py
"""

from collections import OrderedDict
import os
import pytest

from astropy.time import Time
import numpy as np

from jwql.instrument_monitors import pipeline_tools
from jwql.instrument_monitors.common_monitors import dark_monitor as dm
from jwql.utils import instrument_properties, maths
from jwql.utils.utils import copy_files, download_mast_data, ensure_dir_exists, filesystem_path, get_config


def completed_steps_check(filename):
    """Test that the list of completed pipeline steps for a file is correct

    Parameters
    ----------
    filename : str
        File to be checked

    Returns
    -------
    completed_steps : OrderedDict
        True = step has been done. False = step has not been done
    """
    completed_steps = pipeline_tools.completed_pipeline_steps(filename)

    true_completed = OrderedDict([('group_scale', False),
                                  ('dq_init', True),
                                  ('saturation', True),
                                  ('ipc', False),
                                  ('refpix', True),
                                  ('superbias', True),
                                  ('persistence', False),
                                  ('dark_current', False),
                                  ('linearity', True),
                                  ('firstframe', False),
                                  ('lastframe', False),
                                  ('rscd', False),
                                  ('jump', False),
                                  ('rate', False)])
    assert completed_steps == true_completed
    return completed_steps


def required_steps_to_do_check(filename, required, already_done):
    """Test that the dictionaries for steps required and steps completed
    are correctly combined to create a dictionary of pipeline steps to
    be done

    Parameters
    ----------
    filename : str
        File to be checked

    required : OrderedDict
        Dict of all pipeline steps to be run on filename

    alraedy_done : OrderedDict
        Dict of pipeline steps already run on filename
    """
    steps_to_run = pipeline_tools.steps_to_run(filename, required, already_done)

    true_steps_to_run = OrderedDict([('group_scale', True),
                                     ('dq_init', False),
                                     ('saturation', False),
                                     ('ipc', False),
                                     ('refpix', False),
                                     ('superbias', False),
                                     ('persistence', True),
                                     ('dark_current', True),
                                     ('linearity', False),
                                     ('firstframe', False),
                                     ('lastframe', False),
                                     ('rscd', False),
                                     ('jump', True),
                                     ('rate', True)])
    assert steps_to_run == true_steps_to_run


def test_amplifier_info():
    """Test that the correct number of amplifiers are found for a
    given file"""
    pass


def test_calc_frame_time():
    """Test calcuation of frametime for a given instrument/aperture"""
    nearir_fullframe = 10.73677
    nircam_160 = 0.27864
    nrc_fullframe = instrument_properties.calc_frame_time('nircam', 'NRCA1_FULL', 2048, 2048, 4)
    nrc_160 = instrument_properties.calc_frame_time('nircam', 'NRCA1_SUB160', 160, 160, 1)
    nrs_fullframe = instrument_properties.calc_frame_time('niriss', 'NIS_CEN', 2048, 2048, 4)
    #nrs_some_subarra = instrument_properies.calc_frame_time('niriss', '????', ??, ??, ?)

    print('STILL NEED TO ADD FRAMETIME CALCS FOR MIRI AND NIRSPEC TO THE CALC_FRAME_TIME_FUNCTION')
    print('CONFIRM NIRCAMSUB160 TIME ON JDOX')

    assert np.isclose(nrc_fullframe, nearir_fullframe, atol=0.001, rtol=0)
    assert np.isclose(nrc_160, nircam_160, atol=0.001, rtol=0)
    assert np.isclose(nrs_fullframe, nearir_fullframe, atol=0.001, rtol=0)


def test_copy_files():
    """Test basic function to copy file from one place to another"""
    file_to_copy = [os.path.join(os.path.dirname(__file__), 'test_data/dark_monitor/test_image_2.fits')]

    # Create temporary directory
    destination = os.path.join(os.path.dirname(__file__), 'temp')
    ensure_dir_exists(destination)

    copy_files(file_to_copy, destination)

    copied_file = os.path.join(destination, os.path.basename(file_to_copy[0]))
    assert os.path.isfile(copied_file)

    # Remove copied file
    os.remove(copied_file)
    os.rmdir(destination)


def test_double_gaussian_fit():
    """Test the double Gaussian fitting function"""
    amplitude1 = 500
    mean_value1 = 0.5
    sigma_value1 = 0.05
    amplitude2 = 300
    mean_value2 = 0.4
    sigma_value2 = 0.03

    bin_centers = np.arange(0., 1.1, 0.007)
    input_params = [amplitude1, mean_value1, sigma_value1, amplitude2, mean_value2, sigma_value2]
    input_values = maths.double_gaussian(bin_centers, *input_params)

    initial_params = [np.max(input_values), 0.55, 0.1, np.max(input_values), 0.5, 0.05]
    params, sigma = maths.double_gaussian_fit(bin_centers, input_values, initial_params)

    double_gauss_fit = maths.double_gaussian(bin_centers, *params)

    assert np.allclose(np.array(params[0:3]), np.array([amplitude2, mean_value2, sigma_value2]),
                       atol=0, rtol=0.000001)
    assert np.allclose(np.array(params[3:]), np.array([amplitude1, mean_value1, sigma_value1]),
                       atol=0, rtol=0.000001)


def test_download_mast_data():
    """Test that fits files are downloaded from MAST"""
    # Create temporary directory
    destination = os.path.join(os.path.dirname(__file__), 'temp')
    ensure_dir_exists(destination)

    # Small query. Should return only one filename
    instrument = 'NIRCAM'
    aperture = 'NRCA1_FULL'
    query = dm.mast_query_darks(instrument, aperture, 57410.917, 57410.919)

    download_mast_data(query, destination)

    downloaded_file = os.path.join(destination, query[0]['filename'])
    assert os.path.isfile(downloaded_file)

    required_steps = pipeline_tools.get_pipeline_steps(instrument)
    print('DOWNLOADED FILE:', downloaded_file)
    finished_steps = completed_steps_check(downloaded_file)
    required_steps_to_do_check(downloaded_file, required_steps, finished_steps)

    # Remove downloaded file
    print('REMOVE: {}'.format(downloaded_file))
    print('REMOVE: {}'.format(destination))
    #os.remove(downloaded_file)
    #os.rmdir(destination)


@pytest.mark.xfail
def test_filesystem_path():
    """Test  that a file's location in the filesystem is returned"""
    filename = 'jw96003001001_02201_00001_nrca1_dark.fits'
    check = filesystem_path(filename)

    filesystem_base = get_config()["filesystem"]
    assert check == os.path.join(filesystem_base, 'jw96003/{}'.format(filename))


def test_gaussian1d_fit():
    """Test histogram fitting function"""
    mean_value = 0.5
    sigma_value = 0.05
    image = np.random.normal(loc=mean_value, scale=sigma_value, size=(100, 100))
    hist, bin_edges = np.histogram(image, bins='auto')
    bin_centers = (bin_edges[1:] + bin_edges[0: -1]) / 2.
    initial_params = [np.max(hist), 0.55, 0.1]
    amplitude, peak, width = maths.gaussian1d_fit(bin_centers, hist, initial_params)

    assert (((peak[0] - peak[1]) <= mean_value) and ((peak[0] + peak[1]) >= mean_value))
    assert (((width[0] - width[1]) <= sigma_value) and ((width[0] + width[1]) >= sigma_value))


def test_get_metadata():
    """Test retrieval of metadata from input file"""
    monitor = dm.Dark(testing=True)
    filename = os.path.join(os.path.dirname(__file__), 'test_data/dark_monitor/test_image_1.fits')
    monitor.get_metadata(filename)
    assert monitor.instrument == 'NIRCAM'
    assert monitor.x0 == 0
    assert monitor.y0 == 0
    assert monitor.xsize == 10
    assert monitor.ysize == 10
    assert monitor.sample_time == 10
    assert monitor.frame_time == 10.5


def test_get_pipeline_steps():
    """Test that the proper pipeline steps are returned for an instrument"""
    nrc_req_steps = pipeline_tools.get_pipeline_steps('nircam')
    nrc_steps = ['group_scale', 'dq_init', 'saturation', 'superbias', 'refpix', 'linearity',
                 'persistence', 'dark_current', 'jump', 'rate']
    not_required = ['ipc', 'firstframe', 'lastframe', 'rscd']
    nrc_dict = OrderedDict({})
    for step in nrc_steps:
        nrc_dict[step] = True
    for step in not_required:
        nrc_dict[step] = False
    assert nrc_req_steps == nrc_dict

    nrs_req_steps = pipeline_tools.get_pipeline_steps('nirspec')
    nrs_steps = ['group_scale', 'dq_init', 'saturation', 'superbias', 'refpix', 'linearity',
                 'dark_current', 'jump', 'rate']
    not_required = ['ipc', 'persistence', 'firstframe', 'lastframe', 'rscd']
    nrs_dict = OrderedDict({})
    for step in nrs_steps:
        nrs_dict[step] = True
    for step in not_required:
        nrs_dict[step] = False
    assert nrs_req_steps == nrs_dict

    miri_req_steps = pipeline_tools.get_pipeline_steps('miri')
    miri_steps = ['group_scale', 'dq_init', 'saturation', 'firstframe', 'lastframe',
                  'linearity', 'rscd', 'dark_current', 'refpix', 'jump', 'rate']
    not_required = ['ipc', 'superbias', 'persistence']
    miri_dict = OrderedDict({})
    for step in miri_steps:
        miri_dict[step] = True
    for step in not_required:
        miri_dict[step] = False
    assert miri_req_steps == miri_dict


def test_hot_dead_pixel_check():
    """Test hot and dead pixel searches"""
    monitor = dm.Dark(testing=True)

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

    hot, dead = monitor.hot_dead_pixel_check(mean_image, comparison_image, hot_threshold=2.,
                                             dead_threshold=0.1)
    assert len(hot) == 2
    assert np.all(hot[0] == np.array([1, 7]))
    assert np.all(hot[1] == np.array([1, 7]))
    assert len(dead) == 2
    assert np.all(dead[0] == np.array([6, 7]))
    assert np.all(dead[1] == np.array([6, 3]))


def test_image_stack():
    """Test stacking of slope images"""
    directory = os.path.join(os.path.dirname(__file__), 'test_data/dark_monitor')
    files = [os.path.join(directory, 'test_image_{}.fits'.format(str(i+1))) for i in range(3)]

    image_stack = pipeline_tools.image_stack(files)
    truth = np.zeros((3, 10, 10))
    truth[0, :, :] = 5.
    truth[1, :, :] = 10.
    truth[2, :, :] = 15.

    print(image_stack)
    print('')
    print(truth)

    assert np.all(image_stack == truth)


def test_mast_query_darks():
    """Test that the MAST query for darks is functional"""
    instrument = 'NIRCAM'
    aperture = 'NRCA1_FULL'
    start_date = Time("2016-01-01T00:00:00").mjd
    end_date = Time("2018-01-01T00:00:00").mjd
    query = dm.mast_query_darks(instrument, aperture, start_date, end_date)
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


def test_mean_image():
    """Test the sigma-clipped mean and stdev image calculator"""
    # Create a stack of 50 5x5 pixel images
    nstack = 50
    cube = np.zeros((nstack, 5, 5))

    # Set alternating frames equal to 4 and 5
    for i in range(nstack):
        if i % 2 == 0:
            cube[i, :, :] = 4.
        else:
            cube[i, :, :] = 5.

    # Insert a few signal values that will be removed by sigma clipping.
    # Make sure you "remove" and equal number of 4's and 5's from each
    # pixel in order to keep the mean at 4.5 and dev at 0.5
    cube[0, 0, 0] = 55.
    cube[1, 0, 0] = -78.
    cube[3, 3, 3] = 150.
    cube[2, 3, 3] = 32.
    cube[1, 4, 4] = -96.
    cube[4, 4, 4] = -25.
    mean_img, dev_img = maths.mean_image(cube, sigma_threshold=3)

    assert np.all(mean_img == 4.5)
    assert np.all(dev_img == 0.5)


def test_mean_stdev():
    """Test calcualtion of the sigma-clipped mean from an image"""
    image = np.zeros((50, 50)) + 1.
    badx = [1, 4, 10, 14, 16, 20, 22, 25, 29, 30]
    bady = [13, 27, 43, 21, 1, 32, 25, 21, 9, 14]
    for x, y in zip(badx, bady):
        image[y, x] = 100.

    meanval, stdval = maths.mean_stdev(image, sigma_threshold=3)
    assert meanval == 1.
    assert stdval == 0.


def test_noise_check():
    """Test the search for noisier than average pixels"""
    noise_image = np.zeros((10, 10)) + 0.5
    baseline = np.zeros((10, 10)) + 0.5

    noise_image[3, 3] = 0.8
    noise_image[6, 6] = 0.6
    noise_image[9, 9] = 1.0

    baseline[5, 5] = 1.0
    noise_image[5, 5] = 1.25

    monitor = dm.Dark(testing=True)
    noisy = monitor.noise_check(noise_image, baseline, threshold=1.5)

    assert len(noisy[0]) == 2
    assert np.all(noisy[0] == np.array([3, 9]))
    assert np.all(noisy[1] == np.array([3, 9]))


def test_shift_to_full_frame():
    """Test pixel coordinate shifting to be in full frame coords

    Parameters
    ----------
    instance : jwql.instrument_monitor.common_monitor.dark_monitor.Dark
        Dark monitor class instance

    coords : tup
        List of pixel coordinates to shift (e.g. output of
        hot_dead_pixel_search
    """
    monitor = dm.Dark(testing=True)
    monitor.x0 = 512
    monitor.y0 = 512

    coordinates = (np.array([6, 7]), np.array([6, 3]))
    new_coords = monitor.shift_to_full_frame(coordinates)

    assert np.all(new_coords[0] == np.array([518, 519]))
    assert np.all(new_coords[1] == np.array([518, 515]))








