"""Various utility functions for interacting with MAST

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be imported as such:

    >>> import mast_utils
    results = mast_utils.mast_query('nircam', 'NRCA1_FULL', 'NRC_DARK', 53005.1, 53005.2)

 """
import datetime
import os

from jwql.database.database_interface import Monitor
from jwql.jwql_monitors import monitor_mast
from jwql.utils.constants import INSTRUMENT_MONITOR_DATABASE_TABLES, JWST_DATAPRODUCTS
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


def mast_query(instrument, aperture, templates, start_date, end_date):
    """Use ``astroquery`` to search MAST for data for given observation
    templates over a given time range

    Parameters
    ----------
    instrument : str
        Instrument name (e.g. ``nircam``)

    aperture : str
        Detector aperture to search for (e.g. ``NRCA1_FULL``)

    templates : str or list
        Single, or list of, templates for the query (e.g. ``NRC_DARK``, ``MIR_FLATMRS``)

    start_date : float
        Starting date for the search in MJD

    end_date : float
        Ending date for the search in MJD

    Returns
    -------
    query_results : list
        List of dictionaries containing the query results
    """
    # If a single template name is input as a string, put it in a list
    if isinstance(templates, str):
        templates = [templates]

    # Make sure instrument is correct case
    if instrument.lower() == 'nircam':
        instrument = 'NIRCam'
    elif instrument.lower() == 'niriss':
        instrument = 'NIRISS'
    elif instrument.lower() == 'nirspec':
        instrument = 'NIRSpec'
    elif instrument.lower() == 'fgs':
        instrument = 'FGS'
    elif instrument.lower() == 'miri':
        instrument = 'MIRI'

    # monitor_mast.instrument_inventory does not allow list inputs to
    # the added_filters input (or at least if you do provide a list, then
    # it becomes a nested list when it sends the query to MAST. The
    # nested list is subsequently ignored by MAST.)
    # So query once for each flat template, and combine outputs into a
    # single list.
    query_results = []
    for template_name in templates:

        # Create dictionary of parameters to add
        parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                      "apername": aperture, "exp_type": template_name}

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                  add_filters=parameters, return_data=True, caom=False)
        if len(query['data']) > 0:
            query_results.extend(query['data'])

    return query_results


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
