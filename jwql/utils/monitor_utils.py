"""Various utility functions for instrument monitors

Authors
-------

    - Matthew Bourque
    - Bryan Hilbert

Use
---

    This module can be imported as such:

    >>> import monitor_utils
    settings = monitor_utils.update_monitor_table('dark_monitor')

 """
import datetime
import os


from jwql.utils.constants import INSTRUMENT_MONITOR_DATABASE_TABLES
from jwql.database.database_interface import Monitor
from jwql.utils.logging_functions import configure_logging, get_log_status


def initialize_instrument_monitor(module):
    """Configures a log file for the instrument monitor run and
    captures the start time of the monitor

    Parameters
    ----------
    module : str
        The module name (e.g. ``dark_monitor``)

    Returns
    -------
    start_time : datetime object
        The start time of the monitor
    log_file : str
        The path to where the log file is stored
    """
    start_time = datetime.datetime.now()
    log_file = configure_logging(module)

    return start_time, log_file


def update_monitor_table(module, start_time, log_file):
    """Update the ``monitor`` database table with information about
    the instrument monitor run

    Parameters
    ----------
    module : str
        The module name (e.g. ``dark_monitor``)
    start_time : datetime object
        The start time of the monitor
    log_file : str
        The path to where the log file is stored
    """
    new_entry = {}
    new_entry['monitor_name'] = module
    new_entry['start_time'] = start_time
    new_entry['end_time'] = datetime.datetime.now()
    new_entry['status'] = get_log_status(log_file)
    new_entry['affected_tables'] = INSTRUMENT_MONITOR_DATABASE_TABLES[module]
    new_entry['log_file'] = os.path.basename(log_file)

    Monitor.__table__.insert().execute(new_entry)
