#!/usr/bin/env python
"""Tests for the permissions module.

Authors
-------

    - Johannes Sahlmann


Use
---

    These tests can be run via the command line:

    ::
        pytest -s test_permissions.py

"""

import os
import pytest

from .permissions import set_permissions, has_permissions

# directory to be created and populated during tests running
TEST_DIRECTORY = os.path.join(os.environ['HOME'], 'permission_test')

@pytest.fixture(scope="module")
def test_directory(test_dir=TEST_DIRECTORY):
    """Create a test directory for permission management.

    Parameters
    ----------
    test_dir : str
        Path to directory used for testing

    Returns
    -------
    test_dir : str
        Path to directory used for testing

    """
    os.mkdir(test_dir) # default mode=511

    yield test_dir
    print("teardown test directory")
    if os.path.isdir(test_dir):
        os.remove(test_dir)

@pytest.fixture(scope="module")
def test_file(test_dir=TEST_DIRECTORY):
    """Create a test file for permission management.

    Parameters
    ----------
    test_dir : str
        Path to directory used for testing

    Returns
    -------
    filename : str
        Path of file used for testing

    """
    if not os.path.isdir(test_dir):
        os.mkdir(test_dir)

    filename = os.path.join(test_dir, 'permission_test.txt')
    file = open(filename, 'w')
    file.write('jwql permission test')
    file.close()
    yield filename
    print("teardown test file and directory ")
    if os.path.isfile(filename):
        os.remove(filename)
    if os.path.isdir(test_dir):
        os.rmdir(test_dir)

def test_file_permissions(test_file):
    """Create a file with the standard permissions ('-rw-r--r--').
    Set the default permissions defined in permissions.py. Assert that these were set correctly.

    Parameters
    ----------
    test_file : str
        Path of file used for testing

    """
    set_permissions(test_file)
    assert has_permissions(test_file)
