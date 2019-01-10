"""Various math-related functions used by the ``jwql`` instrument monitors.

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be imported as such:

    >>> import math
    mean_val, stdev_val = math.mean_stdev(image, sigma_threshold=4)
 """

import numpy as np

from astropy.modeling import fitting, models
from scipy.optimize import curve_fit
from scipy.stats import sigmaclip


def double_gaussian(x, amp1, peak1, sigma1, amp2, peak2, sigma2):
    """Equation two Gaussians

    Parameters
    ----------
    x : numpy.ndarray
        1D array of x values to be fit

    params : list
        Gaussian coefficients
        [amplitude1, peak1, stdev1, amplitude2, peak2, stdev2]
    """
    y_values = amp1 * np.exp(-(x - peak1)**2.0 / (2.0 * sigma1**2.0)) \
        + amp2 * np.exp(-(x - peak2)**2.0 / (2.0 * sigma2**2.0))
    return y_values


def double_gaussian_fit(x_values, y_values, input_params):
    """Fit two Gaussians to the given array

    Parameters
    ----------
    x_values : numpy.ndarray
        1D array of x values to be fit

    y_values : numpy.ndarray
        1D array of y values to be fit

    params : list
        Initial guesses for Gaussian coefficients
        [amplitude1, peak1, stdev1, amplitude2, peak2, stdev2]
    """
    params, cov = curve_fit(double_gaussian, x_values, y_values, input_params)
    sigma = np.sqrt(diag(cov))
    return params, sigma


def gaussian1d_fit(x_values, y_values, params):
    """Fit 1D Gaussian to an array. Designed around fitting to
    histogram of pixel values.

    Parameters
    ----------
    x_values : numpy.ndarray
        1D array of x values to be fit

    y_values : numpy.ndarray
        1D array of y values to be fit

    Returns
    -------
    amplitude : tup
        Tuple of the best fit Gaussian amplitude and uncertainty

    peak : tup
        Tuple of the best fit Gaussian peak position and uncertainty

    width : tup
        Tuple of the best fit Gaussian width and uncertainty
    """
    model_gauss = models.Gaussian1D(amplitude=params[0], mean=params[1], stddev=params[2])
    fitter_gauss = fitting.LevMarLSQFitter()
    best_fit = fitter_gauss(model_gauss, x_values, y_values)
    cov_diag = np.diag(fitter_gauss.fit_info['param_cov'])

    # Arrange each parameter into (best_fit_value, uncertainty) tuple
    amplitude = (best_fit.amplitude.value, np.sqrt(cov_diag[0]))
    peak = (best_fit.mean.value, np.sqrt(cov_diag[1]))
    width = (best_fit.stddev.value, np.sqrt(cov_diag[2]))
    return amplitude, peak, width


def mean_image(file_list, sigma_threshold=3):
    """Combine a list of images into a mean slope image,
    using sigma-clipping

    Parameters
    ----------
    file_list : list
        List of filenames to be included in the mean calculations

    sigma_threshold : int
        Number of sigma to use when sigma-clipping values in each
        pixel

    Returns
    -------
    mean_image : numpy.ndarray
        2D sigma-clipped mean image

    stdev_image : numpy.ndarray
        2D sigma-clipped standard deviation image
    """
    for i, input_file in enumerate(file_list):
        model = datamodels.open(input_file)
        image = model.data

        # Stack all inputs together into a single 3D image cube
        if i == 0:
            ndim_base = image.shape
            if len(ndim_base) == 3:
                cube = copy.deepcopy(image)
            elif len(ndim_base) == 2:
                cube = np.expand_dims(image, 0)

        ndim = image.shape
        if ndim_base[-2:] == ndim[-2:]:
            if len(ndim) == 2:
                image = np.expand_dims(image, 0)
            elif len(ndim) > 3:
                raise ValueError("4-dimensional input images not supported.")
            cube = np.vstack((cube, image))
        else:
            raise ValueError("Input images are of inconsistent size in x/y dimension.")

    # Create mean and standard deviation images, using sigma-
    # clipping on a pixel-by-pixel basis
    clipped_cube = sigma_clip(cube, sigma=sigma_threshold, axis=0, masked=False)
    mean_image = np.mean(clipped_cube, axis=0)
    std_image = np.nanstd(clipped_cube, axis=0)
    return mean_image, std_image


def mean_stdev(image, sigma_threshold=3):
    """Calculate the sigma-clipped mean and stdev of an input array

    Parameters
    ----------
    image : numpy.ndarray
        Array of which to calculate statistics

    sigma_threshold : float
        Number of sigma to use when sigma-clipping

    Returns
    -------
    mean_value : float
        Sigma-clipped mean of image

    stdev_value : float
        Sigma-clipped standard deviation of image
    """
    clipped, lower, upper = sigmaclip(image, low=sigma_threshold, high=sigma_threshold)
    mean_value = np.mean(clipped)
    stdev_value = np.std(clipped)
    return mean_value, stdev_value
