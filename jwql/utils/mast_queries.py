"""Various functions for using MAST to retrive file information

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be imported as such:

    >>> import mast_queries
    results = mast_queries.get_program_obs_nums('nircam', 1068)

 """

import logging
import os

from astroquery.mast import Mast

from jwql.utils.constants import MAST_QUERY_LIMIT

# Increase the limit on the number of entries that can be returned by
# a MAST query.
Mast._portal_api_connection.PAGESIZE = MAST_QUERY_LIMIT


def get_program_obs_nums(instrument, program):
    """For a given program number, return a list of the observations
    within that program

    Parameters
    ----------
    instrument : str
        Name of JWST instrument

    program : str or int
        Program number

    Returns
    -------
    obs : list
        List of observation number strings
    """
    server = "https://mast.stsci.edu"
    JwstObs = Mast()
    JwstObs._portal_api_connection.MAST_REQUEST_URL = server + "/portal_jwst/Mashup/Mashup.asmx/invoke"
    JwstObs._portal_api_connection.MAST_DOWNLOAD_URL = server + "/jwst/api/v0.1/download/file"
    JwstObs._portal_api_connection.COLUMNS_CONFIG_URL = server + "/portal_jwst/Mashup/Mashup.asmx/columnsconfig"
    JwstObs._portal_api_connection.MAST_BUNDLE_URL = server + "/jwst/api/v0.1/download/bundle"
    service = f'Mast.Jwst.Filtered.{instrument.title()}'
    FIELDS = ['program', 'observtn']
    params = {"columns":",".join(FIELDS),
              "filters":[
                         {"paramName":"program","values":[program]}
                         ]
              }
    t = JwstObs.service_request(service, params)
    obs = set(t['observtn'])
    obs = sorted([str(e).zfill(3) for e in obs])
    return obs


def get_file_obs_nums(instrument, filename):
    """Get the observation numbers associated with a given file. Handle a case where level
    3 files may have more than one observation associated with them

    Parameters
    ----------
    instrument : str
        Name of JWST instrument

    filename : str
        Name of file to query for

    Returns
    -------
    obs : list
        Observations associated with ``filename``
    """
    server = "https://mast.stsci.edu"
    JwstObs = Mast()
    JwstObs._portal_api_connection.MAST_REQUEST_URL = server + "/portal_jwst/Mashup/Mashup.asmx/invoke"
    JwstObs._portal_api_connection.MAST_DOWNLOAD_URL = server + "/jwst/api/v0.1/download/file"
    JwstObs._portal_api_connection.COLUMNS_CONFIG_URL = server + "/portal_jwst/Mashup/Mashup.asmx/columnsconfig"
    JwstObs._portal_api_connection.MAST_BUNDLE_URL = server + "/jwst/api/v0.1/download/bundle"
    service = f'Mast.Jwst.Filtered.{instrument.title()}'
    FIELDS = ['observtn']
    params = {"columns":",".join(FIELDS),
              "filters":[
                         {"paramName":"filename","values":[filename]}
                         ]
              }
    t = JwstObs.service_request(service, params)
    obs = set(t['observtn'])
    obs = sorted([str(e).zfill(3) for e in obs])
    return obs
