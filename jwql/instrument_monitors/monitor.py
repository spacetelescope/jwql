"""
"""

import datetime
import logging
import os

from jwql.database.database_interface import Monitor as MonitorTable
from jwql.database.database_interface import session
from jwql.utils.constants import INSTRUMENT_MONITOR_DATABASE_TABLES
from jwql.utils.logging_functions import configure_logging, get_log_status, log_info, log_fail
from jwql.utils.utils import get_config


class Monitor():
    """
    """

    def __init__(self, monitor_name):
        """
        """

        self.database_session = session
        self.monitor_name = monitor_name
        self.output_location = os.path.join(get_config()['outputs'], monitor_name)
        self._setup_logging()

    def add_database_entry(self, table, entry):
        """
        """

        table.__table__.insert().execute(entry)
        logging.info('Added entry to {} table'.format(table))


    def _setup_logging(self):
        """
        """

        self.start_time = datetime.datetime.now()
        self.log_file = configure_logging(self.monitor_name)
        logging.info('Begin logging for {}'.format(self.monitor_name))

    def query_database(self, query):
        """
        """

        results = self.database_session.query(query).all()
        return results


    @log_fail
    @log_info
    def run(self):
        """
        """

    def update_monitor_table(self):
        """
        """

        new_entry = {}
        new_entry['monitor_name'] = self.monitor_name
        new_entry['start_time'] = self.start_time
        new_entry['end_time'] = datetime.datetime.now()
        new_entry['status'] = get_log_status(self.log_file)
        new_entry['affected_tables'] = INSTRUMENT_MONITOR_DATABASE_TABLES[self.monitor_name]
        new_entry['log_file'] = os.path.basename(self.log_file)

        MonitorTable.__table__.insert().execute(new_entry)

        logging.info('Updated monitor table')
