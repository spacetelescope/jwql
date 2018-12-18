#! /usr/bin/env python

"""Tests for the ``database_interface.py`` module.

Authors
-------

    Joe Filippazzo

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s database_interface.py
"""

from jwql.database import database_interface as di


def test_anomaly_table():
    """Test to see that the database has an anomalies table"""
    assert 'anomalies' in di.engine.table_names()


def test_anomaly_records():
    """Test to see that new records can be entered"""
    # Add some data
    di.session.add(di.Anomaly(filename='foo1', bowtie="True"))
    di.session.commit()

    # Test the bowties column
    bowties = di.session.query(di.Anomaly).filter(di.Anomaly.bowtie == "True")
    assert bowties.data_frame.iloc[0]['bowtie'] == "True"

    # Test the other columns
    non_bowties = [col for col in di.Anomaly().colnames if col != 'bowtie']
    assert all([i == "False" for i in bowties.data_frame.iloc[0][non_bowties]])


def test_names_colnames():
    """Test that the column names are correct"""
    # Make sure we get non-empty lists
    anom = di.Anomaly()
    assert isinstance(anom.colnames, list) and len(anom.colnames) > 0
    assert isinstance(anom.names, list) and len(anom.names) == len(anom.colnames)
    assert all([i == j.replace('_', ' ') for i, j in zip(anom.names, anom.colnames)])
