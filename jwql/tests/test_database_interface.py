#! /usr/bin/env python

"""Tests for the ``database_interface.py`` module.

Authors
-------

    - Joe Filippazzo

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s database_interface.py
"""

import datetime

from jwql.database import database_interface as di


def test_anomaly_table():
    """Test to see that the database has an anomalies table"""

    assert 'anomaly' in di.engine.table_names()


def test_anomaly_records():
    """Test to see that new records can be entered"""

    # Add some data
    di.session.add(di.Anomaly(rootname='foo1', flag_date=datetime.datetime.today(), user='test', ghost=True))
    di.session.commit()

    # Test the ghosts column
    ghosts = di.session.query(di.Anomaly).filter(di.Anomaly.ghost == "True")
    assert ghosts.data_frame.iloc[0]['ghost'] == True
