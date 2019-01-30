"""This module contains classes to monitor the bias of all JWST instruments

Authors
-------

    Joe Filippazzo

Use
---

"""

import os
import random

from astropy.io import fits
import numpy as np

from jwql.jwql_monitors import monitor_mast as mast
from jwql.utils.constants import JWST_INSTRUMENT_NAMES


DIMS = {'niriss': (2048, 2048)}

def fetch_data(instrument, test=10):
    """Fetch the masked data for this instrument from MAST or generate
    a test dataset with the appropriate dimensions

    Parameters
    ----------
    instrument: str
        The instrument name ['fgs', 'niriss', 'nircam', 'nirspec', 'miri']
    test: bool
        Generate fake data for testing

    Returns
    -------
    np.ndarray
        The data cube
    """
    # Placeholder for bad pixel map
    badpixmap = np.zeros(DIMS[instrument])

    # Get the detector dimensions
    dims = DIMS[instrument]

    # Generate fake data if it's a test
    if isinstance(test, int):

        # Make fake data
        data = np.ones((test, *dims))

        # Simulate 1% bad pixels randomly
        idx = random.sample(range(np.prod(dims)), int(np.prod(dims)*0.01))
        flatmap = badpixmap.flatten()
        flatmap[idx] = 1
        badpixmap = flatmap.reshape(*dims)

    else:

        # Or get it from MAST
        data = mast.instrument_inventory(instrument, dataproduct='IMAGE',
                                         add_filters=None, add_requests=None,
                                         caom=False, return_data=True)

        # And get the bad pixel map from... somewhere
        badpixmap = np.zeros(dims)

    # Apply the bad pixel map
    badpix = np.broadcast_to(badpixmap, data.shape)
    masked_data = np.ma.masked_where(badpix > 0, data)

    return masked_data


def measure_bias(instrument, start_date, end_date, test=None):
    """Measure the bias over a time interval for a given instrument

    Parameters
    ----------
    instrument: str
        The instrument name ['fgs', 'niriss', 'nircam', 'nirspec', 'miri']
    start_date: ?
        The starting date
    end_date: ?
        The ending date
    """
    # Make sure the instrument is valid
    instrument = instrument.lower()
    if instrument not in JWST_INSTRUMENT_NAMES:
        raise ValueError("{}: Instrument must be in {}".format(instrument, JWST_INSTRUMENT_NAMES))

    # Get the dark frames
    masked_data = fetch_data(instrument, test=test)

    # Calculations

    return masked_data