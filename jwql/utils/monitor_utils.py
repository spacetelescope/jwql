"""Various utility functions for instrument monitors

Authors
-------

    - Matthew Bourque
    - Bryan Hilbert
    - Maria Pena-Guerrero

Use
---

    This module can be imported as such:

    >>> import monitor_utils
    settings = monitor_utils.update_monitor_table('dark_monitor')

 """
import datetime
import os
from astroquery.mast import Mast, Observations


from jwql.database.database_interface import Monitor
from jwql.jwql_monitors import monitor_mast
from jwql.utils.constants import ASIC_TEMPLATES, JWST_DATAPRODUCTS, MAST_QUERY_LIMIT
from jwql.utils.logging_functions import configure_logging, get_log_status
from jwql.utils.utils import filename_parser


# Increase the limit on the number of entries that can be returned by
# a MAST query.
Mast._portal_api_connection.PAGESIZE = MAST_QUERY_LIMIT


def exclude_asic_tuning(mast_results):
    """Given a list of file information from a MAST query, filter out
    files taken during ASIC tuning, which will have bad data in terms
    of results for the instrument monitors.

    Parameters
    ----------
    mast_results : list
        List of dictionaries containing a MAST query result

    Returns
    -------
    filtered_results : list
        Modified list with ASIC tuning entries removed
    """
    filtered_results = []
    for mast_result in mast_results:
        if mast_result['template'] not in ASIC_TEMPLATES:
            filtered_results.append(mast_result)
    return filtered_results


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


def mast_query_darks(instrument, aperture, start_date, end_date, readpatt=None):
    """Use ``astroquery`` to search MAST for dark current data

    Parameters
    ----------
    instrument : str
        Instrument name (e.g. ``nircam``)

    aperture : str
        Detector aperture to search for (e.g. ``NRCA1_FULL``)

    start_date : float
        Starting date for the search in MJD

    end_date : float
        Ending date for the search in MJD

    readpatt : str
        Readout pattern to search for (e.g. ``RAPID``). If None,
        readout pattern will not be added to the query parameters.

    Returns
    -------
    query_results : list
        List of dictionaries containing the query results
    """

    # Make sure instrument is correct case
    if instrument.lower() == 'nircam':
        instrument = 'NIRCam'
        dark_template = ['NRC_DARK']
    elif instrument.lower() == 'niriss':
        instrument = 'NIRISS'
        dark_template = ['NIS_DARK']
    elif instrument.lower() == 'nirspec':
        instrument = 'NIRSpec'
        dark_template = ['NRS_DARK']
    elif instrument.lower() == 'fgs':
        instrument = 'FGS'
        dark_template = ['FGS_DARK']
    elif instrument.lower() == 'miri':
        instrument = 'MIRI'
        dark_template = ['MIR_DARKALL', 'MIR_DARKIMG', 'MIR_DARKMRS']

    # monitor_mast.instrument_inventory does not allow list inputs to
    # the added_filters input (or at least if you do provide a list, then
    # it becomes a nested list when it sends the query to MAST. The
    # nested list is subsequently ignored by MAST.)
    # So query once for each dark template, and combine outputs into a
    # single list.
    query_results = []
    for template_name in dark_template:

        # Create dictionary of parameters to add
        parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                      "apername": aperture, "exp_type": template_name, }

        if readpatt is not None:
            parameters["readpatt"] = readpatt

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                  add_filters=parameters, return_data=True, caom=False)
        if 'data' in query.keys():
            if len(query['data']) > 0:
                query_results.extend(query['data'])

    return query_results


def mast_query_ta(instrument, aperture, start_date, end_date, readpatt=None):
    """Use ``astroquery`` to search MAST for TA current data

    Parameters
    ----------
    instrument : str
        Instrument name (e.g. ``nirspec``)

    aperture : str
        Detector aperture to search for (e.g. ``NRS_S1600A1_SLIT``)

    start_date : float
        Starting date for the search in MJD

    end_date : float
        Ending date for the search in MJD

    readpatt : str
        Readout pattern to search for (e.g. ``RAPID``). If None,
        readout pattern will not be added to the query parameters.

    Returns
    -------
    query_results : list
        List of dictionaries containing the query results
    """

    # Make sure instrument is correct case
    if instrument.lower() == 'nirspec':
        instrument = 'Nirspec'
        if aperture == 'NRS_S1600A1_SLIT':
            exp_types = ['NRS_TASLIT', 'NRS_BOTA', 'NRS_WATA']
        else:
            exp_types = ['NRS_TACQ', 'NRS_MSATA']

    # monitor_mast.instrument_inventory does not allow list inputs to
    # the added_filters input (or at least if you do provide a list, then
    # it becomes a nested list when it sends the query to MAST. The
    # nested list is subsequently ignored by MAST.)
    # So query once for each exp_type, and combine outputs into a
    # single list.
    query_results = []
    for template_name in exp_types:

        # Create dictionary of parameters to add
        parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                      "apername": aperture, "exp_type": template_name }

        if readpatt is not None:
            parameters["readpatt"] = readpatt

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                  add_filters=parameters, return_data=True, caom=False)
        if 'data' in query.keys():
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
    new_entry['log_file'] = os.path.basename(log_file)

    Monitor.__table__.insert().execute(new_entry)
