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
from scipy.stats import sigmaclip

def gaussian1d_fit(self, x_values, y_values):
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
    model_gauss = models.Gaussian1D()
    fitter_gauss = fitting.LevMarLSQFitter()
    best_fit = fitter_gauss(model_gauss, x_values, y_values)
    cov_diag = np.diag(fitter_gauss.fit_info['param_cov'])

    # Arrange each parameter into (best_fit_value, uncertainty) tuple
    amplitude = (best_fit.amplitude.value, np.sqrt(cov_diag[0]))
    peak = (best_fit.mean.value, np.sqrt(cov_diag[1]))
    width = (best_fit.stddev.value, np.sqrt(cov_diag[2]))
    return amplitude, peak, width

def mean_stdev(self, image, sigma_threshold=3):
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
