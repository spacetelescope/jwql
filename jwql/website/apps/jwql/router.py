"""Defines the query routing for the monitor database tables.

In Django, database queries are assumed to go to the default database unless either the
`using` field/keyword is defined or a routing table sends it to a different database. In
this case, all monitor tables should be routed to the monitors database, and the router
should otherwise express no opinion (by returning None).

Authors
-------
    - Brian York

Use
---
    This module is not intended to be used outside of Django asking about it.

References
----------
    For more information please see:
        ```https://docs.djangoproject.com/en/2.0/topics/db/models/```
"""
from jwql.utils.constants import MONITOR_TABLE_NAMES


class MonitorRouter:
    """
    A router to control all database operations on models in the
    JWQLDB (monitors) database.
    """

    route_app_labels = {"monitors"}

    def db_for_read(self, model, **hints):
        """
        Attempts to read monitor models go to monitors db.
        """
        if model.__name__ in MONITOR_TABLE_NAMES:
            return "monitors"
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write  monitor models go to monitors db.
        """
        if model.__name__ in MONITOR_TABLE_NAMES:
            return "monitors"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between tables in the monitors DB.
        """
        if (
            obj1.__class__.__name__ in MONITOR_TABLE_NAMES
            and obj2.__class__.__name__ in MONITOR_TABLE_NAMES
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the monitors apps only appear in the 'monitors' database.
        """
        if app_label in self.route_app_labels or app_label == 'jwql':
            return db == "monitors"
        return None
