"""Resources for unit tests.

Authors
-------

    - Melanie Clarke

Use
---

    These structures can be imported in unit tests and used to
    mock various software functionality.
"""

import pandas as pd


class MockAnomalyQuery(object):
    """Mock a SQLAlchemy query on an anomaly table."""
    def __init__(self, group_record=False):
        records = [{'rootname': 'jw02589006001_04101_00001-seg001_nrs1',
                    'persistence': True, 'crosstalk': True,
                    'ghost': False}]
        if group_record:
            records.append(
                {'rootname': 'jw02589006001_04101_00001-seg001_nrs2',
                 'persistence': True, 'crosstalk': False, 'ghost': False})
        self.data_frame = pd.DataFrame(records)

    def filter(self, filter_val):
        return self

    def order_by(self, sort_val):
        return self


class MockSessionGroupAnomaly(object):
    """Mock a SQLAlchemy session for an anomaly query on a group."""
    def query(self, table):
        return MockAnomalyQuery(group_record=True)


class MockSessionFileAnomaly(object):
    """Mock a SQLAlchemy session for an anomaly query on a file."""
    def query(self, table):
        return MockAnomalyQuery(group_record=False)
