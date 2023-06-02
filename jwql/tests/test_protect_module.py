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
from jwql.utils import protect_module as pm

from pytest import fixture, mark
from jwql.utils.protect_module import lock_module, _PID_LOCKFILE_KEY

# Determine if tests are being run on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


@fixture
def module_lock():
    module = __file__
    module_lock = module.replace('.py', '.lock')
    return module_lock


@fixture
def do_not_email():
    pm.ALERT_EMAIL = False
    return pm.ALERT_EMAIL


@lock_module
def protected_code_verify_file_exists_true(module_lock):
    return os.path.exists(module_lock)


@lock_module
def protected_code_entered():
    return True


@mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_lock_module_create_destroy_file(module_lock, do_not_email):
    """Test wrapper will create and destroy a lock file named by module if no other lock exists """

    # Ensure lock file does not exist
    if os.path.exists(module_lock):
        os.remove(module_lock)
    file_created = protected_code_verify_file_exists_true(module_lock)
    file_exists = os.path.exists(module_lock)
    # Assert that lock file was created in wrapper, and removed upon exit
    assert (file_created and not file_exists) is True


@mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_already_locked_module_wont_run_with_bad_lock_file(module_lock, do_not_email):
    """Test when wrapper encounters poorly formatted lock file,
       it will not run, not delete lock file, and will send warn email """
    # create locked file in advance of calling protected code
    with open(module_lock, "w"):
        entered_protected_code = protected_code_entered()
    # assert the invalid lock file was never deleted
    assert os.path.exists(module_lock)
    # assert that we never entered protected code
    assert entered_protected_code is None
    # clean the test
    os.remove(module_lock)


@mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_already_locked_module_wont_run_with_legit_lock_file(module_lock, do_not_email):
    """Test wrapper will not run if it encounters a correclty formatted lock_file """
    # create locked file with running PID in advance of calling protected code
    with open(module_lock, "w") as lock_file:
        lock_file.write(f"{_PID_LOCKFILE_KEY}{os.getpid()}\n")
    entered_protected_code = protected_code_entered()
    # assert that we never entered protected code because the PID is currently running
    assert entered_protected_code is None
    # clean the test
    os.remove(module_lock)


@mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_lock_module_handles_stale_lock_files(module_lock, do_not_email):
    """Test wrapper will correctly identify stale lock file,
       delete it, and continue to run successfully """
    # create locked file with not running PID in advance of calling protected code
    with open(module_lock, "w") as lock_file:
        lock_file.write(f"{_PID_LOCKFILE_KEY}12345\n")
    file_created = protected_code_verify_file_exists_true(module_lock)
    file_exists = os.path.exists(module_lock)
    # Assert that lock file was created in wrapper, and removed upon exit
    assert (file_created and not file_exists) is True
