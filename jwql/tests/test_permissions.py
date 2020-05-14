#! /usr/bin/env python

"""Tests for the ``permissions`` module.

Authors
-------

    - Johannes Sahlmann


Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_permissions.py
"""

import grp
import os
import pytest

from jwql.utils.permissions import set_permissions, has_permissions, \
    get_owner_string, get_group_string

# directory to be created and populated during tests running
TEST_DIRECTORY = os.path.join(os.environ['HOME'], 'permission_test')

# Determine if tests are being run on jenkins
ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


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
    os.mkdir(test_dir)  # creates directory with default mode=511

    yield test_dir
    if os.path.isdir(test_dir):
        os.remove(test_dir)


def test_directory_permissions(test_directory):
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
    owner = get_owner_string(test_directory)
    group = get_group_string(test_directory)

    set_permissions(test_directory, owner=owner, group=group)
    assert has_permissions(test_directory, owner=owner, group=group)


@pytest.fixture()
def test_file(test_dir=TEST_DIRECTORY):
    """Create a test file for permission management.

    Parameters
    ----------
    test_dir : str
        Path to directory used for testing

    Yields
    -------
    filename : str
        Path of file used for testing
    """
    if not os.path.isdir(test_dir):
        os.mkdir(test_dir)

    filename = os.path.join(test_dir, 'permission_test.txt')
    with open(filename, 'w') as filestream:
        filestream.write('jwql permission test')
    yield filename
    if os.path.isfile(filename):
        os.remove(filename)
    if os.path.isdir(test_dir):
        os.rmdir(test_dir)


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_file_group(test_file):
    """Create a file with the standard permissions ``('-rw-r--r--')``
    and default group.

    Modify the group and set the default permissions defined in
    ``permissions.py``.  Assert that both group and permissions were
    set correctly.

    Parameters
    ----------
    test_file : str
        Path of file used for testing
    """
    # Get owner and group on the current system.
    owner = get_owner_string(test_file)
    group = get_group_string(test_file)

    # attempt to retrieve a group name different from default
    group_index = 0
    test_group = grp.getgrgid(os.getgroups()[group_index]).gr_name

    set_permissions(test_file, group=test_group, owner=owner)
    assert has_permissions(test_file, group=test_group, owner=owner)

    # return to default group
    set_permissions(test_file, owner=owner, group=group)
    assert has_permissions(test_file, owner=owner, group=group)


def test_file_permissions(test_file):
    """Create a file with the standard permissions ``('-rw-r--r--')``.

    Set the default permissions defined in ``permissions.py``. Assert
    that these were set correctly.

    Parameters
    ----------
    test_file : str
        Path of file used for testing
    """
    # Get owner and group on the current system.
    owner = get_owner_string(test_file)
    group = get_group_string(test_file)

    set_permissions(test_file, owner=owner, group=group)
    assert has_permissions(test_file, owner=owner, group=group)
