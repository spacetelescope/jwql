#!/usr/bin/env python
"""Tests for the permissions module


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
    """Create a test directory for permission management

    :return:
    """

    os.mkdir(test_dir) # default mode=511

    yield test_dir
    print("teardown test directory")
    if os.path.isdir(test_dir):
        os.remove(test_dir)

@pytest.fixture(scope="module")
def test_file(test_dir=TEST_DIRECTORY):
    """Create a test file for permission management

    :param directory:
    :return:
    """
    # test_dir = test_directory()
    # print(test_dir)
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
    """Create a file with the standard permissions ('-rw-r--r--'), then set
    the default permissions defined in permissions.py
    Assert that these were set correctly.

    :param test_file:
    :return:
    """
    # filename = test_file
    set_permissions(test_file)
    assert has_permissions(test_file)
