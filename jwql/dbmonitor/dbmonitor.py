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

import http.client as httplib
import json
import sys
from urllib.parse import quote as urlencode

from astroquery.mast import Mast
import astropy.table as at

from ..utils.utils import JWST_DATAPRODUCTS, JWST_INSTRUMENTS


def instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                         add_filters={}, add_requests={}, return_data=False):
    """Get the counts for a given instrument and data product

    Parameters
    ----------
    instrument: sequence, str
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
    # Declare the service
    service = 'Mast.Jwst.Filtered.{}'.format(instrument.title())
                         
    # Make sure the dataproduct is a list
    if isinstance(dataproduct, str):
        dataproduct = [dataproduct]

    # Make sure the instrument is a list
    if isinstance(instrument, str):
        instrument = [instrument]

    # Set default filters
    filters = []

    # Assemble the request
    params = {'columns': 'COUNT_BIG(*)', 
              'filters': filters, 
              'removenullcolumns':True,}

    # Just get the counts
    if return_data:
        params['columns'] = '*'

    # Add requests
    if add_requests:
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
                         add_filters={}, add_requests={}, return_data=False):
    """Get the counts for a given instrument and data product

    Parameters
    ----------
    instrument: sequence, str
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
    for param, value in add_filters.items():
        filters.append({'paramName': param, 'values': [value]
                        if isinstance(value, str) else value})

    # Assemble the request
    params = {'columns': 'COUNT_BIG(*)', 'filters': filters,}

    # Just get the counts
    if return_data:
        params['columns'] = '*'

    # Add requests
    if add_requests:
        params.update(add_requests)
    
    response = Mast.service_request_async('Mast.Caom.Filtered', params)
    result = response[0].json()

    # Return all the data
    if return_data:
        return result

    # Or just the counts
    else:
        return result['data'][0]['Column1']


def jwst_inventory(instruments=JWST_INSTRUMENTS,
                   dataproducts=['image', 'spectrum', 'cube']):
    """Gather a full inventory of all JWST data on MAST by instrument/dtype

    Parameters
    ----------
    instruments: sequence
        The list of instruments to count
    dataproducts: sequence
        The types of dataproducts to count

    Returns
    -------
    astropy.table.table.Table
        The table of record counts for each instrument and mode
    """
    # Make master table
    inventory = at.Table(names=('instrument', 'dataproduct', 'count'),
                         dtype=('S8', 'S12', int))

    # Iterate through instruments
    for instrument in instruments:
        for dataproduct in dataproducts:
            count = instrument_inventory_caom(instrument, dataproduct=dataproduct)
            inventory.add_row([instrument, dataproduct, count])

        # Get number of files for all datatypes for this instrument
        count = instrument_inventory_caom(instrument, dataproduct=dataproducts)
        inventory.add_row([instrument, '*', count])

    # Get total number of files
    count = instrument_inventory_caom(instruments, dataproduct=dataproducts)
    inventory.add_row(['*', '*', count])

    # Retrieve one dataset to get header keywords
    sample = instrument_inventory_caom(instruments, dataproduct=dataproducts,
                                  add_requests={'pagesize': 1, 'page': 1},
                                  return_data=True)
    names = [i['name'] for i in sample['fields']]
    types = [i['type'] for i in sample['fields']]
    keywords = at.Table([names, types], names=('keyword', 'dtype'))

    return inventory, keywords


def jwst_inventory_caom(instruments=JWST_INSTRUMENTS,
                   dataproducts=['image', 'spectrum', 'cube']):
    """Gather a full inventory of all JWST data on MAST by instrument/dtype

    Parameters
    ----------
    instruments: sequence
        The list of instruments to count
    dataproducts: sequence
        The types of dataproducts to count

    Returns
    -------
    astropy.table.table.Table
        The table of record counts for each instrument and mode
    """
    # Make master table
    inventory = at.Table(names=('instrument', 'dataproduct', 'count'),
                         dtype=('S8', 'S12', int))

    # Iterate through instruments
    for instrument in instruments:
        for dataproduct in dataproducts:
            count = instrument_inventory_caom(instrument, dataproduct=dataproduct)
            inventory.add_row([instrument, dataproduct, count])

        # Get number of files for all datatypes for this instrument
        count = instrument_inventory_caom(instrument, dataproduct=dataproducts)
        inventory.add_row([instrument, '*', count])

    # Get total number of files
    count = instrument_inventory_caom(instruments, dataproduct=dataproducts)
    inventory.add_row(['*', '*', count])

    # Retrieve one dataset to get header keywords
    sample = instrument_inventory_caom(instruments, dataproduct=dataproducts,
                                  add_requests={'pagesize': 1, 'page': 1},
                                  return_data=True)
    names = [i['name'] for i in sample['fields']]
    types = [i['type'] for i in sample['fields']]
    keywords = at.Table([names, types], names=('keyword', 'dtype'))

    return inventory, keywords


def listMissions():
    """Small function to test sevice_request and make sure JWST is
    in the list of services

    Returns
    -------
    astropy.table.table.Table
        The table of all supported services
    """
    service = 'Mast.Missions.List'
    params = {}
    request = Mast.service_request(service, params)

    return request


def mastQuery(request):
    """A small MAST API wrapper

    Parameters
    ----------
    request: dict
        The dictionary of 'service', 'format' and 'params' for the request

    Returns
    -------
    dict
        A dictionary of the 'data', 'fields', 'paging', and 'status'
        of the request
    """
    # Define the server
    server = 'mast.stsci.edu'

    # Grab Python Version
    version = ".".join(map(str, sys.version_info[:3]))

    # Create Http Header Variables
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain",
               "User-agent": "python-requests/"+version}

    # Encoding the request as a json string
    requestString = json.dumps(request)
    requestString = urlencode(requestString)

    # opening the https connection
    conn = httplib.HTTPSConnection(server)

    # Making the query
    conn.request("POST", "/api/v0/invoke", "request="+requestString, headers)

    # Getting the response
    resp = conn.getresponse()
    head = resp.getheaders()
    content = resp.read().decode('utf-8')

    # Close the https connection
    conn.close()

    return head, content
