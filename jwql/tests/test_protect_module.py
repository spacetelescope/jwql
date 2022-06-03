#!/usr/bin/env python

"""Tests protect_module.py module

Authors
-------

    - Bradley Sappington

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_protect_module.py
"""
import os
from pytest import fixture, mark
from jwql.utils.protect_module import lock_module

# Determine if tests are being run on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


@fixture
def module_lock():
    module = __file__
    module_lock = module.replace('.py', '.lock')
    return module_lock


@lock_module
def protected_code_verify_file_exists_true(module_lock):
    return os.path.exists(module_lock)


@lock_module
def protected_code_entered():
    return True


@mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_lock_module_create_destroy_file(module_lock):
    """Test if that wrapper will create and destroy a lock file named by module """

    # Ensure lock file does not exist
    if os.path.exists(module_lock):
        os.remove(module_lock)
    file_created = protected_code_verify_file_exists_true(module_lock)
    file_exists = os.path.exists(module_lock)
    # Assert that lock file was created in wrapper, and removed upon exit
    assert (file_created and not file_exists) is True


@mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_lock_module_wont_run_locked(module_lock):
    """Test if that wrapper will create and destroy a lock file named by module """
    # create locked file in advance of calling protected code
    with open(module_lock, "w"):
        entered_protected_code = protected_code_entered()
    os.remove(module_lock)
    # assert that we never entered protected code
    assert entered_protected_code is None
