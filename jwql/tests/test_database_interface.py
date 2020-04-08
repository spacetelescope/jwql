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
from jwql.utils.constants import ANOMALIES_PER_INSTRUMENT
from jwql.utils.utils import get_config

# Determine if tests are being run on jenkins
ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to development database server.')
def test_all_tables_exist():
    """Test that the table ORMs defined in ``database_interface``
    actually exist as tables in the database"""

    # Get list of table ORMs from database_interface
    table_orms = []
    database_interface_attributes = di.__dict__.keys()
    for attribute in database_interface_attributes:
        table_object = getattr(di, attribute)
        try:
            table_orms.append(table_object.__tablename__)
        except AttributeError:
            pass  # Not all attributes of database_interface are table ORMs

    # Get list of tables that are actually in the database
    existing_tables = di.engine.table_names()

    # Ensure that the ORMs defined in database_interface actually exist
    # as tables in the database
    for table in table_orms:
        assert table in existing_tables


def test_anomaly_orm_factory():
    """Test that the ``anomaly_orm_factory`` function successfully
    creates an ORM and contains the appropriate columns"""

    test_table_name = 'test_anomaly_table'
    TestAnomalyTable = di.anomaly_orm_factory(test_table_name)
    table_attributes = TestAnomalyTable.__dict__.keys()

    assert str(TestAnomalyTable) == "<class 'jwql.database.database_interface.{}'>"\
        .format(test_table_name)

    for item in ['id', 'rootname', 'flag_date', 'user']:
        assert item in table_attributes


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to development database server.')
def test_anomaly_records():
    """Test to see that new records can be entered"""

    # Add some data
    random_rootname = ''.join(random.SystemRandom().choice(string.ascii_lowercase + \
                                                           string.ascii_uppercase + \
                                                           string.digits) for _ in range(10))
    di.session.add(di.FGSAnomaly(rootname=random_rootname,
                              flag_date=datetime.datetime.today(),
                              user='test', ghost=True))
    di.session.commit()

    # Test the ghosts column
    ghosts = di.session.query(di.FGSAnomaly)\
        .filter(di.FGSAnomaly.rootname == random_rootname)\
        .filter(di.FGSAnomaly.ghost == "True")
    assert ghosts.data_frame.iloc[0]['ghost'] == True


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to development database server.')
def test_load_connections():
    """Test to see that a connection to the database can be
    established"""

    session, base, engine, meta = di.load_connection(get_config()['connection_string'])
    assert str(type(session)) == "<class 'sqlalchemy.orm.session.Session'>"
    assert str(type(base)) == "<class 'sqlalchemy.ext.declarative.api.DeclarativeMeta'>"
    assert str(type(engine)) == "<class 'sqlalchemy.engine.base.Engine'>"
    assert str(type(meta)) == "<class 'sqlalchemy.sql.schema.MetaData'>"


def test_monitor_orm_factory():
    """Test that the ``monitor_orm_factory`` function successfully
    creates an ORM and contains the appropriate columns"""

    test_table_name = 'instrument_test_monitor_table'

    # Create temporary table definitions file
    test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'database', 'monitor_table_definitions', 'instrument')
    test_filename = os.path.join(test_dir, '{}.txt'.format(test_table_name))
    if not os.path.isdir(test_dir):
        os.mkdir(test_dir)
    with open(test_filename, 'w') as f:
        f.write('TEST_COLUMN, string')

    # Create the test table ORM
    TestMonitorTable = di.monitor_orm_factory(test_table_name)
    table_attributes = TestMonitorTable.__dict__.keys()

    # Ensure the ORM exists and contains appropriate columns
    assert str(TestMonitorTable) == "<class 'jwql.database.database_interface.{}'>"\
        .format(test_table_name)
    for column in ['id', 'entry_date', 'test_column']:
        assert column in table_attributes

    # Remove test files and directories
    if os.path.isfile(test_filename):
        os.remove(test_filename)
    if os.path.isdir(test_dir):
        os.rmdir(test_dir)
