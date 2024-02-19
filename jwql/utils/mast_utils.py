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

import logging
import os

from astroquery.mast import Mast
from bokeh.embed import components
from bokeh.io import save, output_file
import pandas as pd

from jwql.utils.constants import JWST_DATAPRODUCTS, JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, MAST_QUERY_LIMIT
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import ensure_dir_exists, get_config
from jwql.utils.plotting import bar_chart


if not ON_GITHUB_ACTIONS:
    Mast._portal_api_connection.MAST_REQUEST_URL = get_config()['mast_request_url']

# Increase the limit on the number of entries that can be returned by
# a MAST query.
Mast._portal_api_connection.PAGESIZE = MAST_QUERY_LIMIT


def instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                         add_filters=None, add_requests=None,
                         caom=False, return_data=False):
    """Get the counts for a given instrument and data product

    Parameters
    ----------
    instrument: str
        The instrument name, i.e. one of ['niriss','nircam','nirspec',
        'miri','fgs']
    dataproduct: sequence, str
        The type of data product to search
    add_filters: dict
        The ('paramName':'values') pairs to include in the 'filters'
        argument of the request e.g. add_filters = {'filter':'GR150R'}
    add_requests: dict
        The ('request':'value') pairs to include in the request
        e.g. add_requests = {'pagesize':1, 'page':1}
    caom: bool
        Query CAOM service
    return_data: bool
        Return the actual data instead of counts only

    Returns
    -------
    int, dict
        The number of database records that satisfy the search criteria
        or a dictionary of the data if `return_data=True`
    """
    filters = []

    # Make sure the dataproduct is a list
    if isinstance(dataproduct, str):
        dataproduct = [dataproduct]

    # Make sure the instrument is supported
    if instrument.lower() not in [ins.lower() for ins in JWST_INSTRUMENT_NAMES]:
        raise TypeError('Supported instruments include:', JWST_INSTRUMENT_NAMES)

    # CAOM service
    if caom:

        # Declare the service
        service = 'Mast.Caom.Filtered'

        # Set the filters
        filters += [{'paramName': 'obs_collection', 'values': ['JWST']},
                    {'paramName': 'instrument_name', 'values': [instrument]},
                    {'paramName': 'dataproduct_type', 'values': dataproduct}]

    # Instruent filtered service
    else:

        # Declare the service
        service = 'Mast.Jwst.Filtered.{}'.format(instrument.title())

    # Include additonal filters
    if isinstance(add_filters, dict):
        filters += [{"paramName": name, "values": [val]}
                    for name, val in add_filters.items()]

    # Assemble the request
    params = {'columns': 'COUNT_BIG(*)',
              'filters': filters,
              'removenullcolumns': True}

    # Just get the counts
    if return_data:
        params['columns'] = '*'

    # Add requests
    if isinstance(add_requests, dict):
        params.update(add_requests)

    response = Mast.service_request_async(service, params)
    result = response[0].json()

    # Return all the data
    if return_data:
        return result

    # Or just the counts
    else:
        return result['data'][0]['Column1']


def instrument_keywords(instrument, caom=False):
    """Get the keywords for a given instrument service

    Parameters
    ----------
    instrument: str
        The instrument name, i.e. one of ['niriss','nircam','nirspec',
        'miri','fgs']
    caom: bool
        Query CAOM service

    Returns
    -------
    pd.DataFrame
        A DataFrame of the keywords
    """
    # Retrieve one dataset to get header keywords
    if not caom:
        filter_to_add = {'program': '01440'}
    else:
        filter_to_add = {'proposal_id': '01440'}
    sample = instrument_inventory(instrument, return_data=True, caom=caom,
                                  add_requests={'pagesize': 1, 'page': 1},
                                  add_filters=filter_to_add)
    data = [[i['name'], i['type']] for i in sample['fields']]
    keywords = pd.DataFrame(data, columns=('keyword', 'dtype'))

    return keywords


def jwst_inventory(instruments=JWST_INSTRUMENT_NAMES,
                   dataproducts=['image', 'spectrum', 'cube'],
                   caom=False, plot=False, output_dir=None):
    """Gather a full inventory of all JWST data in each instrument
    service by instrument/dtype

    Parameters
    ----------
    instruments: sequence
        The list of instruments to count
    dataproducts: sequence
        The types of dataproducts to count
    caom: bool
        Query CAOM service
    plot: bool
        Return a pie chart of the data
    output_dir: str
        Directory into which plots are saved

    Returns
    -------
    astropy.table.table.Table
        The table of record counts for each instrument and mode
    """
    if output_dir is None:
        output_dir = os.path.join(get_config()['outputs'], 'mast_utils')
    ensure_dir_exists(output_dir)

    logging.info('Searching database...')
    # Iterate through instruments
    inventory, keywords = [], {}
    for instrument in instruments:
        ins = [instrument]
        for dp in dataproducts:
            count = instrument_inventory(instrument, dataproduct=dp, caom=caom)
            ins.append(count)

        # Get the total
        ins.append(sum(ins[-3:]))

        # Add it to the list
        inventory.append(ins)

        # Add the keywords to the dict
        keywords[instrument] = instrument_keywords(instrument, caom=caom)

    logging.info('Completed database search for {} instruments and {} data products.'.
                 format(instruments, dataproducts))

    # Make the table
    all_cols = ['instrument'] + dataproducts + ['total']
    table = pd.DataFrame(inventory, columns=all_cols)

    # Plot it
    if plot:
        if caom:
            output_filename = 'database_monitor_caom'
        else:
            output_filename = 'database_monitor_jwst'

        # Make the plot
        plt = bar_chart(table, 'instrument', dataproducts,
                        title="JWST Inventory")

        # Save the plot as full html
        html_filename = output_filename + '.html'
        outfile = os.path.join(output_dir, html_filename)
        output_file(outfile)
        save(plt)
        set_permissions(outfile)

        logging.info('Saved Bokeh plots as HTML file: {}'.format(html_filename))

        # Save the plot as components
        plt.sizing_mode = 'stretch_both'
        script, div = components(plt)

        div_outfile = os.path.join(output_dir, output_filename + "_component.html")
        with open(div_outfile, 'w') as f:
            f.write(div)
            f.close()
        set_permissions(div_outfile)

        script_outfile = os.path.join(output_dir, output_filename + "_component.js")
        with open(script_outfile, 'w') as f:
            f.write(script)
            f.close()
        set_permissions(script_outfile)

        logging.info('Saved Bokeh components files: {}_component.html and {}_component.js'.format(
            output_filename, output_filename))

    # Melt the table
    table = pd.melt(table, id_vars=['instrument'],
                    value_vars=dataproducts,
                    value_name='files', var_name='dataproduct')

    return table, keywords


def mast_query(instrument, templates, start_date, end_date, aperture=None, detector=None, filter_name=None,
               pupil=None, grating=None, readpattern=None, lamp=None):
    """Use ``astroquery`` to search MAST for data for given observation
    templates over a given time range

    Parameters
    ----------
    instrument : str
        Instrument name (e.g. ``nircam``)

    templates : str or list
        Single, or list of, templates for the query (e.g. ``NRC_DARK``,
        ``MIR_FLATMRS``)

    start_date : float
        Starting date for the search in MJD

    end_date : float
        Ending date for the search in MJD

    aperture : str
        Detector aperture to search for (e.g. ``NRCA1_FULL``)

    detector : str
        Detector name (e.g. ``MIRIMAGE``)

    filter_name : str
        Fitler element (e.g. ``F200W``)

    pupil : str
        Pupil element (e.g. ``F323N``)

    grating : str
        Grating element (e.g. ``MIRROR``)

    readpattern : str
        Detector read out pattern (e.g. ``NISRAPID``)

    lamp : str
        Lamp name (e.g. ``LINE2``)

    Returns
    -------
    query_results : list
        List of dictionaries containing the query results
    """

    # If a single template name is input as a string, put it in a list
    if isinstance(templates, str):
        templates = [templates]

    # Make sure instrument is correct case
    instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]

    # instrument_inventory does not allow list inputs to
    # the added_filters input (or at least if you do provide a list, then
    # it becomes a nested list when it sends the query to MAST. The
    # nested list is subsequently ignored by MAST.)
    # So query once for each flat template, and combine outputs into a
    # single list.
    query_results = []
    for template_name in templates:

        # Create dictionary of parameters to add
        parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                      "exp_type": template_name}

        if detector is not None:
            parameters["detector"] = detector
        if aperture is not None:
            parameters["apername"] = aperture
        if filter_name is not None:
            parameters["filter"] = filter_name
        if pupil is not None:
            parameters["pupil"] = pupil
        if grating is not None:
            parameters["grating"] = grating
        if readpattern is not None:
            parameters["readpatt"] = readpattern
        if lamp is not None:
            parameters["lamp"] = lamp

        query = instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                     add_filters=parameters, return_data=True, caom=False)
        if len(query['data']) > 0:
            query_results.extend(query['data'])

    return query_results


def mast_query_miri(detector, aperture, templates, start_date, end_date):
    """Use ``astroquery`` to search MAST for data for given observation
    templates over a given time range for MIRI. MIRI is different than
    the other instruments in that (to find full frame flats and darks at
    least) you need to use the detector name rather than the aperture
    name. There is no full frame aperture name for the MRS detectors.

    Parameters
    ----------
    detector : str
        Name of the detector to search for. One of ``MIRIMAGE``,
        ``MIRIFULONG``, ``MIRIFUSHORT``.

    aperture : str
        Aperture name on the detector (e.g. ``MIRIM_FULL``)

    templates : str or list
        Single, or list of, templates for the query (e.g. ``NRC_DARK``,
        ``MIR_FLATMRS``)

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

    instrument = 'MIRI'

    # instrument_inventory does not allow list inputs to
    # the added_filters input (or at least if you do provide a list, then
    # it becomes a nested list when it sends the query to MAST. The
    # nested list is subsequently ignored by MAST.)
    # So query once for each flat template, and combine outputs into a
    # single list.
    query_results = []
    for template_name in templates:

        # Create dictionary of parameters to add
        if aperture.lower() != 'none':
            parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                          "detector": detector, "apername": aperture, "exp_type": template_name}
        else:
            parameters = {"date_obs_mjd": {"min": start_date, "max": end_date},
                          "detector": detector, "exp_type": template_name}

        query = instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                     add_filters=parameters, return_data=True, caom=False)
        if len(query['data']) > 0:
            query_results.extend(query['data'])

    return query_results
