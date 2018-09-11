#! /usr/bin/env python

"""Tests for the ``preview_image`` module.

Authors
-------

    - Johannes Sahlmann


Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_preview_image.py
"""

import glob
import os
import pytest

from astropy.io import fits

from jwql.utils.preview_image import PreviewImage

# directory to be created and populated during tests running
TEST_DIRECTORY = os.path.join(os.environ['HOME'], 'preview_image_test')

# directory that contains sample images
TEST_DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_data')


@pytest.fixture(scope="module")
def test_directory(test_dir=TEST_DIRECTORY):
    """Create a test directory for preview image.

    Parameters
    ----------
    test_dir : str
        Path to directory used for testing

    Yields
    -------
    test_dir : str
        Path to directory used for testing

    """
    os.mkdir(test_dir)  # creates directory
    yield test_dir
    print("teardown test directory")
    if os.path.isdir(test_dir):
        os.rmdir(test_dir)


def test_make_image(test_directory):
    """Use PreviewImage.make_image to create preview images of a sample JWST exposure.

    Assert that the number of JPGs created corresponds to the number of integrations.

    Parameters
    ----------
    test_directory : str
        Path of directory used for testing

    """
    filenames = glob.glob(os.path.join(TEST_DATA_DIRECTORY, '*.fits'))
    print('\nGenerating preview images for {}.'.format(filenames))

    output_directory = test_directory

    for filename in filenames:

        header = fits.getheader(filename)

        # Create and save the preview image or thumbnail
        for create_thumbnail in [False, True]:
            try:
                image = PreviewImage(filename, "SCI")
                image.clip_percent = 0.01
                image.scaling = 'log'
                image.cmap = 'viridis'
                image.output_format = 'jpg'
                image.thumbnail = create_thumbnail
                image.output_directory = output_directory
                image.make_image()
            except ValueError as error:
                print(error)

            if create_thumbnail:
                extension = 'thumb'
            else:
                extension = 'jpg'

            # list of preview images
            preview_image_filenames = glob.glob(os.path.join(test_directory, '*.{}'.format(
                extension)))

            assert len(preview_image_filenames) == header['NINTS']

            # clean up: delete preview images
            for file in preview_image_filenames:
                os.remove(file)
