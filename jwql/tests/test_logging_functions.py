#!/usr/bin/env python

"""Tests for the ``logging_functions`` module.

Authors
-------

    - Matthew Bourque

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_logging_functions.py
"""

import logging
import os
import pytest
import shutil

from jwql.utils import logging_functions
from jwql.utils.logging_functions import configure_logging, log_fail, log_info, make_log_file
from jwql.utils.utils import get_config

# Determine if tests are being run on jenkins
ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


@log_fail
@log_info
def perform_basic_logging():
    """Performs some basic logging to the test log file"""

    logging.info('This is some logging info')
    logging.warning('This is a normal warning')
    logging.critical('This is a critical warning')


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_configure_logging():
    """Assert that the ``configure_logging`` function successfully
    creates a log file"""

    log_file = logging_functions.configure_logging('test_logging_functions')
    assert os.path.exists(log_file)

    # Remove the log file
    shutil.rmtree(os.path.dirname(log_file), ignore_errors=True)


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_make_log_file():
    """Assert that ``make_log_file`` function returns the appropriate
    path for a log file"""

    module = 'test_logging_functions'
    log_file = make_log_file(module)

    correct_locations = [
        os.path.join(get_config()['log_dir'], 'dev', module, os.path.basename(log_file)),
        os.path.join(get_config()['log_dir'], 'test', module, os.path.basename(log_file)),
        os.path.join(get_config()['log_dir'], 'prod', module, os.path.basename(log_file))]

    assert log_file in correct_locations


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_logging_functions():
    """A generic end-to-end test that creates a log file, does some
    basic logging, then asserts that some logging content exists"""

    log_file = configure_logging('test_logging_functions')
    perform_basic_logging()

    # Open the log file and make some assertions
    with open(log_file, 'r') as f:
        data = f.readlines()
    data = str([line.strip() for line in data])
    testable_content = ['User:', 'System:', 'Python Executable Path:', 'INFO:',
                        'WARNING:', 'CRITICAL:', 'Elapsed Real Time:',
                        'Elapsed CPU Time:', 'Completed Successfully']
    for item in testable_content:
        assert item in data
