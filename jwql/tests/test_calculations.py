#! /usr/bin/env python

"""Tests for the ``calculations`` module.

Authors
-------

    - Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_calculations.py
"""

import numpy as np

from jwql.utils import calculations


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
    input_values = calculations.double_gaussian(bin_centers, *input_params)

    initial_params = [np.max(input_values), 0.55, 0.1, np.max(input_values), 0.5, 0.05]
    params, sigma = calculations.double_gaussian_fit(bin_centers, input_values, initial_params)

    assert np.allclose(np.array(params[0:3]), np.array([amplitude2, mean_value2, sigma_value2]),
                       atol=0, rtol=0.000001)
    assert np.allclose(np.array(params[3:]), np.array([amplitude1, mean_value1, sigma_value1]),
                       atol=0, rtol=0.000001)


def test_gaussian1d_fit():
    """Test histogram fitting function"""

    mean_value = 0.5
    sigma_value = 0.05
    image = np.random.normal(loc=mean_value, scale=sigma_value, size=(100, 100))
    hist, bin_edges = np.histogram(image, bins='auto')
    bin_centers = (bin_edges[1:] + bin_edges[0: -1]) / 2.
    initial_params = [np.max(hist), 0.55, 0.1]
    amplitude, peak, width = calculations.gaussian1d_fit(bin_centers, hist, initial_params)

    assert np.isclose(peak[0], mean_value, atol=0.0035, rtol=0.)
    assert np.isclose(width[0], sigma_value, atol=0.0035, rtol=0.)
    assert ((mean_value <= peak[0]+7*peak[1]) & (mean_value >= peak[0]-7*peak[1]))
    assert ((sigma_value <= width[0]+7*width[1]) & (sigma_value >= width[0]-7*width[1]))


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
    mean_img, dev_img = calculations.mean_image(cube, sigma_threshold=3)

    assert np.all(mean_img == 4.5)
    assert np.all(dev_img == 0.5)


def test_mean_stdev():
    """Test calcualtion of the sigma-clipped mean from an image"""

    image = np.zeros((50, 50)) + 1.
    badx = [1, 4, 10, 14, 16, 20, 22, 25, 29, 30]
    bady = [13, 27, 43, 21, 1, 32, 25, 21, 9, 14]
    for x, y in zip(badx, bady):
        image[y, x] = 100.

    meanval, stdval = calculations.mean_stdev(image, sigma_threshold=3)
    assert meanval == 1.
    assert stdval == 0.
