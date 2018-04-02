"""This module is home to a suite of MAST queries that gather bulk properties of available JWST data for JWQL

Authors
-------

    Joe Filippazzo

Use
---

    This module can be imported as such:

    >>> from jwql.dbmonitor import dbmonitor
"""
import sys
import os
import time
import re
import json
from urllib.parse import quote as urlencode
from urllib.request import urlretrieve
import http.client as httplib 
from astroquery.mast import Mast, Observations

JWST_INSTRUMENTS = ['NIRISS','NIRCam','NIRSpec','MIRI','FGS']
JWST_DATAPRODUCTS = ['IMAGE', 'SPECTRUM', 'SED', 'TIMESERIES', 'VISIBILITY', 'EVENTLIST', 'CUBE', 'CATALOG', 'ENGINEERING', 'NULL']

def listMissions():
    """Small function to test sevice_request and make sure JWST is in the list of services
    
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
        A dictionary of the 'data', 'fields', 'paging', and 'status' of the request
    """
    # Define the server
    server='mast.stsci.edu'
    
    # Grab Python Version 
    version = ".".join(map(str, sys.version_info[:3]))
    
    # Create Http Header Variables
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain",
               "User-agent":"python-requests/"+version}
               
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
    
    return head,content
    
def instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS, return_data=False):
    """Get the counts for a given instrument and data product
    
    Parameters
    ----------
    instrument: str
        The instrument name, i.e. ['NIRISS','NIRCam','NIRSpec','MIRI','FGS']
    dataproduct: sequence, str
        The type of data product to search
    return_data: bool
        Return the actual data instead of counts only
    
    Returns
    -------
    int
        The number of database records that satisfy the search criteria
    """
    # Make sure the dataproduct is a list
    if isinstance(dataproduct,str):
        dataproduct = [dataproduct]
        
    # Assemble the request
    request = {'service':'Mast.Caom.Filtered',
               'format':'json',
               'params':{
                   'columns':'COUNT_BIG(*)',
                   'filters':[
                       {'paramName':'obs_collection', 'values':['JWST']},
                       {'paramName':'instrument_name', 'values':[instrument]},
                       {'paramName':'dataproduct_type', 'values':dataproduct}
                   ]}}
                   
    # Just get the counts
    if return_data:
        request['params']['columns'] = '*'
                   
    # Perform the query
    headers, outString = mastQuery(request)
    result = json.loads(outString)
    
    # REturn all the data
    if return_data:
        return result
    
    # Or just the counts
    else:
        return result['data'][0]['Column1']
    
def jwst_inventory():
    """Gather a full inventory of all JWST data on MAST binned by instrument and mode
    
    Returns
    -------
    astropy.table.table.Table
        The table of record counts for each instrument and mode
    """
    # Make master table
    inventory = at.Table(names=('instrument','dataproduct','count'))
    
    # Iterate through instruments
    for instrument in JWST_INSTRUMENTS:
        for dataproduct in ['cube','image','spectrum']:
            count = instrument_inventory(instrument, dataproduct=dataproduct)
            