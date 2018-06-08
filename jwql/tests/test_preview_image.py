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

from jwql.permissions import permissions
from jwql.preview_image.preview_image import PreviewImage

# from jwql.permissions.permissions import set_permissions, has_permissions, \
#     get_owner_string, get_group_string

# directory to be created and populated during tests running
TEST_DIRECTORY = os.path.join(os.environ['HOME'], 'preview_image_test')

# directory that contains sample images
TEST_DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_data')

@pytest.fixture(scope="module")
def test_directory(test_dir=TEST_DIRECTORY):
    """Create a test directory for permission management.

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
    permissions.set_permissions(test_dir, verbose=True)
    yield test_dir
    print("teardown test directory")
    if os.path.isdir(test_dir):
        os.remove(test_dir)








def test_make_image(test_directory):
    """Create a directory with the standard permissions
    ``('-rw-r--r--')``.

    Set the default permissions defined in ``permissions.py``. Assert
    that these were set correctly.

    Parameters
    ----------
    test_directory : str
        Path of directory used for testing
    """
    # Get owner and group on the current system.This allows to implement the tests
    # independently from the user.

    filenames = glob.glob(os.path.join(TEST_DATA_DIRECTORY, '*.fits'))
    print('\nGenerating preview images for {}.'.format(filenames))

    output_directory = test_directory
    thumbnail_output_directory = test_directory

    for filename in filenames:

        header = fits.getheader(filename)

        # Create and save the preview image and thumbnail
        try:
            im = PreviewImage(filename, "SCI")
            im.clip_percent = 0.01
            im.scaling = 'log'
            im.cmap = 'viridis'
            im.output_format = 'jpg'
            im.thumbnail = False
            im.output_directory = output_directory
            im.make_image()
        except ValueError as error:
            print(error)


        preview_image_filenames = glob.glob(os.path.join(test_directory, '*.jpg'))

        print(header)

    # owner = get_owner_string(test_directory)
    # group = get_group_string(test_directory)
    # print('\nCurrent owner={} group={}'.format(owner, group))
    #
    # set_permissions(test_directory, owner=owner, group=group)
    # assert has_permissions(test_directory, owner=owner, group=group)


# @pytest.fixture()
# def test_file(test_dir=TEST_DIRECTORY):
#     """Create a test file for permission management.
#
#     Parameters
#     ----------
#     test_dir : str
#         Path to directory used for testing
#
#     Yields
#     -------
#     filename : str
#         Path of file used for testing
#     """
#     if not os.path.isdir(test_dir):
#         os.mkdir(test_dir)
#
#     filename = os.path.join(test_dir, 'permission_test.txt')
#     with open(filename, 'w') as filestream:
#         filestream.write('jwql permission test')
#     yield filename
#     print("teardown test file and directory ")
#     if os.path.isfile(filename):
#         os.remove(filename)
#     if os.path.isdir(test_dir):
#         os.rmdir(test_dir)
#
#
# # @pytest.mark.xfail
# def test_file_group(test_file):
#     """Create a file with the standard permissions ``('-rw-r--r--')``
#     and default group.
#
#     Modify the group and set the default permissions defined in
#     ``permissions.py``.  Assert that both group and permissions were
#     set correctly.
#
#     Parameters
#     ----------
#     test_file : str
#         Path of file used for testing
#     """
#     # Get owner and group on the current system.
#     owner = get_owner_string(test_file)
#     group = get_group_string(test_file)
#
#     # attempt to retrieve a group name different from default
#     group_index = 0
#     test_group = grp.getgrgid(os.getgroups()[group_index]).gr_name
#
#     set_permissions(test_file, group=test_group, owner=owner)
#     assert has_permissions(test_file, group=test_group, owner=owner)
#
#     # return to default group
#     set_permissions(test_file, owner=owner, group=group)
#     assert has_permissions(test_file, owner=owner, group=group)
#
#
# def test_file_permissions(test_file):
#     """Create a file with the standard permissions ``('-rw-r--r--')``.
#
#     Set the default permissions defined in ``permissions.py``. Assert
#     that these were set correctly.
#
#     Parameters
#     ----------
#     test_file : str
#         Path of file used for testing
#     """
#     # Get owner and group on the current system.
#     owner = get_owner_string(test_file)
#     group = get_group_string(test_file)
#
#     set_permissions(test_file, owner=owner, group=group)
#     assert has_permissions(test_file, owner=owner, group=group)
