#! /usr/bin/env python

"""Tests for the ``monitor_utils`` module.

Authors
-------

    - Melanie Clarke

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_monitor_utils.py
"""
import datetime

import pytest

from jwql.database.database_interface import session, Monitor
from jwql.tests.resources import has_test_db
from jwql.utils import monitor_utils


@pytest.mark.skipif(not has_test_db(), reason='Modifies test database.')
def test_update_monitor_table(tmp_path):
    module = 'test'
    start_time = datetime.datetime.now()
    log_file = tmp_path / 'test_log.txt'
    log_file.write_text('Completed Successfully')

    try:
        monitor_utils.update_monitor_table(module, start_time, log_file)
        query = session.query(Monitor).filter(Monitor.monitor_name == module)
        assert query.count() == 1
        assert query.first().status == 'SUCCESS'
    finally:
        # clean up
        query = session.query(Monitor).filter(Monitor.monitor_name == module)
        query.delete()
        session.commit()

        assert session.query(Monitor).filter(
            Monitor.monitor_name == module).count() == 0
