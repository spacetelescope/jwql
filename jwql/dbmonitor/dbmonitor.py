"""This module is home to a suite of MAST queries that gather bulk properties
of available JWST data for JWQL

Authors
-------

    Joe Filippazzo

Use
---

    To get an inventory of all JWST files do:

    >>> from jwql.dbmonitor import dbmonitor
    >>> inventory, keywords = dbmonitor.jwst_inventory()

"""

from astroquery.mast import Mast
from bkcharts import Donut, show
import pandas as pd

from ..utils.utils import JWST_DATAPRODUCTS, JWST_INSTRUMENTS


def instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                         add_filters=None, add_requests=None,
                         return_data=False):
    """Get the counts for a given instrument and data product

    Parameters
    ----------
    instrument: str
        The instrument name, i.e. ['NIRISS','NIRCam','NIRSpec','MIRI','FGS']
    dataproduct: sequence, str
        The type of data product to search
    add_filters: dict
        The ('paramName':'values') pairs to include in the 'filters' argument
        of the request e.g. add_filters = {'filter':'GR150R'}
    add_requests: dict
        The ('request':'value') pairs to include in the request
        e.g. add_requests = {'pagesize':1, 'page':1}
    return_data: bool
        Return the actual data instead of counts only

    Returns
    -------
    int, dict
        The number of database records that satisfy the search criteria
        or a dictionary of the data if `return_data=True`
    """
    # Declare the service
    service = 'Mast.Jwst.Filtered.{}'.format(instrument.title())

    # Make sure the dataproduct is a list
    if isinstance(dataproduct, str):
        dataproduct = [dataproduct]

    # Make sure the instrument is a list
    if isinstance(instrument, str):
        instrument = [instrument]

    # Include filters
    if isinstance(add_filters, dict):
        filters = [{"paramName": name, "values": [val]}
                   for name, val in add_filters.items()]
    else:
        filters = []

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


def instrument_inventory_caom(instrument, dataproduct=JWST_DATAPRODUCTS,
                              add_filters=None, add_requests=None,
                              return_data=False):
    """Get the counts for a given instrument and data product in the
    CAOM service

    Parameters
    ----------
    instrument: str
        The instrument name, i.e. ['NIRISS','NIRCam','NIRSpec','MIRI','FGS']
    dataproduct: sequence, str
        The type of data product to search
    add_filters: dict
        The ('paramName':'values') pairs to include in the 'filters' argument
        of the request e.g. add_filters = {'target_classification':'moving'}
    add_requests: dict
        The ('request':'value') pairs to include in the request
        e.g. add_requests = {'pagesize':1, 'page':1}
    return_data: bool
        Return the actual data instead of counts only

    Returns
    -------
    int, dict
        The number of database records that satisfy the search criteria
        or a dictionary of the data if `return_data=True`
    """
    # Make sure the dataproduct is a list
    if isinstance(dataproduct, str):
        dataproduct = [dataproduct]

    # Make sure the instrument is a list
    if isinstance(instrument, str):
        instrument = [instrument]

    # Set default filters
    filters = [{'paramName': 'obs_collection', 'values': ['JWST']},
               {'paramName': 'instrument_name', 'values': instrument},
               {'paramName': 'dataproduct_type', 'values': dataproduct}]

    # Include additonal filters
    if isinstance(add_filters, dict):
        for param, value in add_filters.items():
            filters.append({'paramName': param, 'values': [value]
                            if isinstance(value, str) else value})

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

    response = Mast.service_request_async('Mast.Caom.Filtered', params)
    result = response[0].json()

    # Return all the data
    if return_data:
        return result

    # Or just the counts
    else:
        return result['data'][0]['Column1']


def instrument_keywords(instrument):
    """Get the keywords for a given instrument service

    Parameters
    ----------
    instrument: str
        The instrument name, i.e. ['NIRISS','NIRCam','NIRSpec','MIRI','FGS']

    Returns
    -------
    pd.DataFrame
        A DataFrame of the keywords
    """
    # Retrieve one dataset to get header keywords
    sample = instrument_inventory(instrument, return_data=True,
                                  add_requests={'pagesize': 1, 'page': 1})
    data = [[i['name'], i['type']] for i in sample['fields']]
    keywords = pd.DataFrame(data, columns=('keyword', 'dtype'))

    return keywords


def instrument_keywords_caom(instrument):
    """Get the keywords for a given instrument in the CAOM service

    Parameters
    ----------
    instrument: str
        The instrument name, i.e. ['NIRISS','NIRCam','NIRSpec','MIRI','FGS']

    Returns
    -------
    pd.DataFrame
        A DataFrame of the keywords
    """
    # Retrieve one dataset to get header keywords
    sample = instrument_inventory_caom(instrument, return_data=True,
                                       add_requests={'pagesize': 1, 'page': 1})
    data = [[i['name'], i['type']] for i in sample['fields']]
    keywords = pd.DataFrame(data, columns=('keyword', 'dtype'))

    return keywords


def jwst_inventory(instruments=JWST_INSTRUMENTS,
                   dataproducts=['image', 'spectrum', 'cube'],
                   plot=False):
    """Gather a full inventory of all JWST data in each instrument
    service by instrument/dtype

    Parameters
    ----------
    instruments: sequence
        The list of instruments to count
    dataproducts: sequence
        The types of dataproducts to count
    plot: bool
        Return a pie chart of the data

    Returns
    -------
    astropy.table.table.Table
        The table of record counts for each instrument and mode
    """
    # Iterate through instruments
    inventory, keywords = [], {}
    for instrument in instruments:
        ins = [instrument]
        for dp in dataproducts:
            count = instrument_inventory(instrument, dataproduct=dp)
            ins.append(count)

        # Get the total
        ins.append(sum(ins[-3:]))

        # Add it to the list
        inventory.append(ins)

        # Add the keywords to the dict
        keywords[instrument] = instrument_keywords(instrument)

    # Make the table
    all_cols = ['instrument']+dataproducts+['total']
    table = pd.DataFrame(inventory, columns=all_cols)

    # Melt the table
    table = pd.melt(table, id_vars=['instrument'],
                    value_vars=dataproducts,
                    value_name='files', var_name='dataproduct')

    # Plot it
    if plot:

        # Make the plot
        plt = Donut(table, label=['instrument', 'dataproduct'], values='files',
                    text_font_size='12pt', hover_text='files',
                    name="JWST Inventory", plot_width=600, plot_height=600)

        show(plt)

    return table, keywords


def jwst_inventory_caom(instruments=JWST_INSTRUMENTS,
                        dataproducts=['image', 'spectrum', 'cube'],
                        plot=False):
    """Gather a full inventory of all JWST data in the CAOM service
    by instrument/dtype

    Parameters
    ----------
    instruments: sequence
        The list of instruments to count
    dataproducts: sequence
        The types of dataproducts to count
    plot: bool
        Return a pie chart of the data

    Returns
    -------
    astropy.table.table.Table
        The table of record counts for each instrument and mode
    """
    # Iterate through instruments
    inventory, keywords = [], {}
    for instrument in instruments:
        ins = [instrument]
        for dp in dataproducts:
            count = instrument_inventory_caom(instrument, dataproduct=dp)
            ins.append(count)

        # Get the total
        ins.append(sum(ins[-3:]))

        # Add it to the list
        inventory.append(ins)

        # Add the keywords to the dict
        keywords[instrument] = instrument_keywords_caom(instrument)

    # Make the table
    all_cols = ['instrument']+dataproducts+['total']
    table = pd.DataFrame(inventory, columns=all_cols)

    # Melt the table
    table = pd.melt(table, id_vars=['instrument'],
                    value_vars=dataproducts,
                    value_name='files', var_name='dataproduct')

    # Plot it
    if plot:

        # Make the plot
        plt = Donut(table, label=['instrument', 'dataproduct'], values='files',
                    text_font_size='12pt', hover_text='files',
                    name="JWST Inventory", plot_width=600, plot_height=600)

        show(plt)

    return table, keywords
