"""Various utility functions for interacting with MAST

Authors
-------

    - Bryan Hilbert
    - Dick Shaw
    - Teagan King

Use
---

    This module can be imported as such:

    >>> import mast_utils
    results = mast_utils.mast_query('nircam', 'NRCA1_FULL', 'NRC_DARK', 53005.1, 53005.2)

 """
from astroquery.mast import Mast
from astropy import table
import numpy as np
import os

from jwql.jwql_monitors import monitor_mast
from jwql.utils.constants import JWST_DATAPRODUCTS, JWST_INSTRUMENT_NAMES_MIXEDCASE


def download_mast_data(query_results, output_dir):
    """Example function for downloading MAST query results. From MAST
    website (``https://mast.stsci.edu/api/v0/pyex.html``)

    Parameters
    ----------
    query_results : list
        List of dictionaries returned by a MAST query.

    output_dir : str
        Directory into which the files will be downlaoded
    """

    # Set up the https connection
    server = 'mast.stsci.edu'
    conn = httplib.HTTPSConnection(server)

    # Dowload the products
    print('Number of query results: {}'.format(len(query_results)))

    for i in range(len(query_results)):

        # Make full output file path
        output_file = os.path.join(output_dir, query_results[i]['filename'])

        print('Output file is {}'.format(output_file))

        # Download the data
        uri = query_results[i]['dataURI']

        print('uri is {}'.format(uri))

        conn.request("GET", "/api/v0/download/file?uri=" + uri)
        resp = conn.getresponse()
        file_content = resp.read()

        # Save to file
        with open(output_file, 'wb') as file_obj:
            file_obj.write(file_content)

        # Check for file
        if not os.path.isfile(output_file):
            print("ERROR: {} failed to download.".format(output_file))
        else:
            statinfo = os.stat(output_file)
            if statinfo.st_size > 0:
                print("DOWNLOAD COMPLETE: ", output_file)
            else:
                print("ERROR: {} file is empty.".format(output_file))
    conn.close()


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

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
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

    # monitor_mast.instrument_inventory does not allow list inputs to
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

        query = monitor_mast.instrument_inventory(instrument, dataproduct=JWST_DATAPRODUCTS,
                                                  add_filters=parameters, return_data=True, caom=False)
        if len(query['data']) > 0:
            query_results.extend(query['data'])

    return query_results


def mast_retrieve_level_1b(instrument, gs_omit, aperture=None, detector=None,
                           filter_name=None, pupil=None, grating=None,
                           readpattern=None, lamp=None, fileSetName=None):
    """Retrieve MAST data that includes level-1b products
    if level-3 data is already processed. This can be used
    as an alternative to Mast.service_request_async.

    The steps to query for and retrieve data files are:
    1. Set the configuration for the web service calls
    2. Make an Observation query that matches your criteria
       (Mast.Caom.Filtered.JwstOps), filtering by instrument
    3. Use the table of results to form a Product query to
       return all the files that are connected to each
       Observation (Mast.Caom.Products.JwstOps)
    4. Filter the returned table of files to select the type you want
       (match a substring in the filename: “_uncal”)

    Parameters
    ----------
    instrument : str
        Name of JWST instrument used to obtain data
    gs_omit : bool
        Omit associated guide-star data files?
    """

    # ret_columns = ['proposal_id', 'dataURL', 'obsid', 'obs_id']

    # set server endpoints --- ISN'T THIS ALREADY SET IN JWQL?
    server = 'https://mast.stsci.edu'
    JwstObs = Mast()
    JwstObs._portal_api_connection.MAST_REQUEST_URL = server + "/portal_jwst/Mashup/Mashup.asmx/invoke"
    JwstObs._portal_api_connection.MAST_DOWNLOAD_URL = server + "/jwst/api/v0.1/download/file"
    JwstObs._portal_api_connection.COLUMNS_CONFIG_URL = server + "/portal_jwst/Mashup/Mashup.asmx/columnsconfig"
    JwstObs._portal_api_connection.MAST_BUNDLE_URL = server + "/jwst/api/v0.1/download/bundle"

    # Perform query for observations matching JWST instrument
    # columns = ','.join(ret_columns)
    # Must use fields available in CAOM: https://mast.stsci.edu/api/v0/_c_a_o_mfields.html
    caom_service = 'Mast.Caom.Filtered.JwstOps'
    filters = [{"paramName": "obs_collection", "values": ["JWST"]},
               {"paramName": "instrument_name", "values": [instrument]}]
    # if detector is not None:
    #     filters.append({"paramName": "detector", "values": [detector]})
    # if aperture is not None:
    #     filters.append({"paramName": "apername", "values": [aperture]})
    if filter_name is not None:  # USE KEYWORD FILTERS IF CAOM, FILTER IF JWST NIRSPEC QUERY
        filters.append({"paramName": "filters", "values": [filter_name]})
    # if pupil is not None:
    #     filters.append({"paramName": "pupil", "values": [pupil]})
    # if grating is not None:
    #     filters.append({"paramName": "grating", "values": [grating]})
    # if readpattern is not None:
    #     filters.append({"paramName": "readpatt", "values": [readpattern]})
    # if lamp is not None:
    #     filters.append({"paramName": "lamp", "values": [lamp]})
    # if fileSetName is not None:
    #     filters.append({"paramName": "fileSetName", "values": [fileSetName]})
    caom_params = {"columns": "*",  # can replace with columns if want specific columns returned
                   "filters": filters}

    obsTable = JwstObs.service_request(caom_service, caom_params)

    if len(obsTable) > 0:
        # Perform query for data products based on obs_id's in observation table
        obs_ids = ','.join(obsTable['obsid'])
        products_service = 'Mast.Caom.Products.JwstOps'
        products_params = {"obsid": obs_ids,
                           "format": "json"}

        products = JwstObs.service_request(products_service, products_params)
        mask = product_filter(products, ['_uncal.fits'], gs_omit)
        selected_products = table.unique(products[mask], ['productFilename'])
        selected_products['productFilename'].pprint(max_lines=-1, show_name=False)
        print('{} L-1b products'.format(len(selected_products)))
    else:
        print("No matching observations")

    response = selected_products  # May need to change format

    return response


def product_filter(table, prodList, gs_omit=True):
    '''
    Filter the list of products based on product semantic type

    Parameters
    ----------
    table : object
        astropy table of products associated with observations
    prodList : list of str
        list of product type extensions to select
    gs_omit
        Omit associated guide-star products?
    '''
    mask = np.full(len(table), False)
    gs_text = '_gs-'
    for r in table:
        mk = False
        fileName = r['productFilename']
        if all(x in fileName for x in prodList):
            mk = mk | True
            if gs_text in fileName:
                mk = not gs_omit

        mask[r.index] = mk

    return mask


# instrument = 'Nirspec'
# gs_omit = True
# mast_retrieve_level_1b(instrument, gs_omit, filter_name='F290LP', grating='G140M',
#                        aperture='NRS_FULL_IFU', detector='NRS1_FULL', readpattern='NRSRAPID')
