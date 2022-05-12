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
from pytest import fixture
from jwql.utils.protect_module import lock_module

@fixture
def module_lock():
    module = __file__
    module_lock = module.replace('.py', '.lock')
    print (f"module_lock fixture is: {module_lock}")
    return module_lock

@lock_module
def protected_code_verify_file_exists_true(module_lock):
    print("protected_code_verify_file_exists_true CODE ENTERED")
    #return True
    return os.path.exists(module_lock)

@lock_module
def protected_code_entered():
    print("protected_code_entered CODE ENTERED")
    return True

def test_lock_module_create_destroy_file(module_lock):
    """Test if that wrapper will create and destroy a lock file named by module """
    
    # Ensure lock file does not exist
    if os.path.exists(module_lock):
        os.remove(module_lock)
    print(f"test_lock_module_create_destroy_file - module_lock is: {module_lock}")
    file_created = protected_code_verify_file_exists_true(module_lock)
    file_exists = os.path.exists(module_lock)
    print(f"file_created == {file_created}")
    print(f"file_exists == {file_exists}")
    #Assert that lock file was created in wrapper, and removed upon exit
    assert (file_created and not file_exists) == True


def test_lock_module_wont_run_locked(module_lock):
    #create locked file in advance of calling protected code
    with open(module_lock, "w") as lock_file:
        entered_protected_code = protected_code_entered()
    os.remove(module_lock)
    # assert that we never entered protected code
    assert entered_protected_code == None
