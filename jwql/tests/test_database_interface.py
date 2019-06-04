#! /usr/bin/env python

"""Tests for the ``database_interface.py`` module.

Authors
-------

    - Joe Filippazzo
    - Matthew Bourque

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s database_interface.py
"""

import datetime
import os
import pytest
import random
import string

from jwql.database import database_interface as di

# Determine if tests are being run on jenkins
ON_JENKINS = os.path.expanduser('~') == '/home/jenkins'


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to development database server.')
def test_anomaly_table():
    """Test to see that the database has an anomalies table"""

    assert 'anomaly' in di.engine.table_names()


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to development database server.')
def test_anomaly_records():
    """Test to see that new records can be entered"""

    # Add some data
    random_string = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(10))
    di.session.add(di.Anomaly(rootname=random_string, flag_date=datetime.datetime.today(), user='test', ghost=True))
    di.session.commit()

    # Test the ghosts column
    ghosts = di.session.query(di.Anomaly).filter(di.Anomaly.ghost == "True")
    assert ghosts.data_frame.iloc[0]['ghost'] == True
