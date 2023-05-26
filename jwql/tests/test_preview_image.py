#! /usr/bin/env python

"""Tests for the ``preview_image`` module.

Authors
-------

    - Johannes Sahlmann
    - Lauren Chambers


Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_preview_image.py
"""

import glob
import numpy as np
import os
import pytest

from astropy.io import fits
from jwst.datamodels import dqflags

from jwql.utils.preview_image import PreviewImage, crop_to_subarray
from jwql.utils.utils import get_config

# Determine if tests are being run on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

# Determine if the code is being run as part of a Readthedocs build
ON_READTHEDOCS = False
if 'READTHEDOCS' in os.environ:
    ON_READTHEDOCS = os.environ['READTHEDOCS']


def test_crop_to_subarray():
    """Test that the code correctly crops larger arrays down to
    the requested subarray
    """
    # Set up a small DQ array that shows the location of reference pixels on 2 sides
    dq = np.ones((10, 10), dtype=int)
    dq[0:3, :] = 0
    dq[:, 0:3] = 0

    # Set up a fits header
    h = fits.ImageHDU([0])
    h.header['FILENAME'] = 'myfile_uncal.fits'

    # Specify that we are cropping the DQ array down to a 5x5 subarray
    xdim = 5
    ydim = 5

    # First test the case where the header has no info on subarray location
    c = crop_to_subarray(dq, h.header, xdim, ydim)
    expected = np.ones((ydim, xdim), dtype=int)
    assert np.all(c == expected)

    # Next test the case where the header does include subarray location info
    h.header['SUBSTRT1'] = 2
    h.header['SUBSTRT2'] = 4
    h.header['SUBSIZE1'] = 5
    h.header['SUBSIZE2'] = 5
    c = crop_to_subarray(dq, h.header, xdim, ydim)
    expected = np.ones((5, 5), dtype=int)
    expected[:, 0:2] = 0
    assert np.all(c == expected)

    # Tweak the y location and try again
    h.header['SUBSTRT2'] = 1
    c = crop_to_subarray(dq, h.header, xdim, ydim)
    expected = np.zeros((5, 5), dtype=int)
    expected[3:, 2:] = 1
    assert np.all(c == expected)


def get_test_fits_files():
    """Get a list of the FITS files on central storage to make preview images.

    Returns
    -------
    filenames : list
        List of filepaths to FITS files
    """
    # Get the files from central store
    if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
        filenames = glob.glob(os.path.join(get_config()['test_dir'], '*.fits'))
        assert len(filenames) > 0
        return filenames

    # Or return an empty list
    else:
        return []


def test_get_nonsci_map():
    """Test the retrieval of the dq data from an HDUList
    """
    # Create HDUList. Start with the case where there is no DQ extension
    h0 = fits.PrimaryHDU([0])
    h1 = fits.ImageHDU(np.zeros((10, 10), dtype=int))
    hdulist = fits.HDUList([h0, h1])
    extensions = ['PRIMARY', 'ERR']
    xd = 10
    yd = 10
    dq = PreviewImage.get_nonsci_map(0, hdulist, extensions, xd, yd)
    expected = np.ones((10, 10), dtype=bool)
    assert np.all(dq == expected)

    # Now test the case where there is a DQ extension. And insert some
    # NON_SCIENCE and REFERENCE_PIXEL flags
    h1.header['EXTNAME'] = 'DQ'
    extensions[1] = 'DQ'
    hdulist['DQ'].data[1, 1] = dqflags.pixel['REFERENCE_PIXEL']
    hdulist['DQ'].data[3, 3] = dqflags.pixel['NON_SCIENCE']
    hdulist['DQ'].data[5, 5] = dqflags.pixel['HOT']
    hdulist['DQ'].data[7, 7] = dqflags.pixel['REFERENCE_PIXEL'] + dqflags.pixel['NON_SCIENCE']
    hdulist['DQ'].data[9, 9] = dqflags.pixel['REFERENCE_PIXEL'] + dqflags.pixel['DEAD']
    dq = PreviewImage.get_nonsci_map(0, hdulist, extensions, xd, yd)
    expected = np.ones((10, 10), dtype=bool)
    expected[1, 1] = expected[3, 3] = expected[7, 7] = expected[9, 9] = 0
    assert np.all(dq == expected)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
@pytest.mark.parametrize('filename', get_test_fits_files())
def test_make_image(tmp_path, filename):
    """Use PreviewImage.make_image to create preview images of a sample
    JWST exposure.

    Assert that the number of JPGs created corresponds to the number of
    integrations.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory to write to
    filename : str
        Path of FITS image to generate preview of
    """
    test_directory = str(tmp_path)
    header = fits.getheader(filename)

    # Create and save the preview image or thumbnail
    for create_thumbnail in [False, True]:
        try:
            image = PreviewImage(filename, "SCI")
            image.clip_percent = 0.01
            image.scaling = 'log'
            image.cmap = 'viridis'
            image.output_format = 'jpg'
            image.thumbnail_output_directory = test_directory
            image.preview_output_directory = test_directory
            image.make_image(create_thumbnail=create_thumbnail)
        except ValueError as error:
            print(error)

        if create_thumbnail:
            extension = 'thumb'
            n_img = 1
        else:
            extension = 'jpg'
            n_img = header['NINTS']

        # list of preview images
        preview_image_filenames = glob.glob(
            os.path.join(test_directory, '*.{}'.format(extension)))
        assert len(preview_image_filenames) == n_img

        # clean up: delete preview images
        for file in preview_image_filenames:
            os.remove(file)
