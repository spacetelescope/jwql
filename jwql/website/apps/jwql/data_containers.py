"""Various functions to collect data to be used by the ``views`` of the
``jwql`` app.

This module contains several functions that assist in collecting and
producing various data to be rendered in ``views.py`` for use by the
``jwql`` app.

Authors
-------

    - Lauren Chambers
    - Matthew Bourque
    - Teagan King

Use
---

    The functions within this module are intended to be imported and
    used by ``views.py``, e.g.:

    ::
        from .data_containers import get_proposal_info
"""

import copy
from collections import OrderedDict
import glob
from operator import getitem
import os
import re
import tempfile

from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from bs4 import BeautifulSoup
from django.conf import settings
import numpy as np
from operator import itemgetter
import pandas as pd
import requests

from jwql.database import database_interface as di
from jwql.database.database_interface import load_connection
from jwql.edb.engineering_database import get_mnemonic, get_mnemonic_info
from jwql.instrument_monitors.miri_monitors.data_trending import dashboard as miri_dash
from jwql.instrument_monitors.nirspec_monitors.data_trending import dashboard as nirspec_dash
from jwql.utils.utils import check_config_for_key, ensure_dir_exists, filesystem_path, filename_parser, get_config
from jwql.utils.constants import MONITORS, PREVIEW_IMAGE_LISTFILE, THUMBNAIL_LISTFILE
from jwql.utils.constants import INSTRUMENT_SERVICE_MATCH, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_INSTRUMENT_NAMES_SHORTHAND
from jwql.utils.preview_image import PreviewImage
from jwql.utils.credentials import get_mast_token

# astroquery.mast import that depends on value of auth_mast
# this import has to be made before any other import of astroquery.mast
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

# Determine if the code is being run as part of a Readthedocs build
ON_READTHEDOCS = False
if 'READTHEDOCS' in os.environ:
    ON_READTHEDOCS = os.environ['READTHEDOCS']

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    from .forms import MnemonicSearchForm, MnemonicQueryForm, MnemonicExplorationForm
    check_config_for_key('auth_mast')
    configs = get_config()
    auth_mast = configs['auth_mast']
    mast_flavour = '.'.join(auth_mast.split('.')[1:])
    from astropy import config
    conf = config.get_config('astroquery')
    conf['mast'] = {'server': 'https://{}'.format(mast_flavour)}
from astroquery.mast import Mast
from jwedb.edb_interface import mnemonic_inventory

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    FILESYSTEM_DIR = configs['filesystem']
    PREVIEW_IMAGE_FILESYSTEM = configs['preview_image_filesystem']
    THUMBNAIL_FILESYSTEM = configs['thumbnail_filesystem']

PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]

# Temporary until JWST operations: switch to test string for MAST request URL
if not ON_GITHUB_ACTIONS:
    Mast._portal_api_connection.MAST_REQUEST_URL = get_config()['mast_request_url']


def build_table(tablename):
    """Create Pandas dataframe from JWQLDB table.

    Parameters
    ----------
    tablename : str
        Name of JWQL database table name.

    Returns
    -------
    table_meta_data : pandas.DataFrame
        Pandas data frame version of JWQL database table.
    """
    # Make dictionary of tablename : class object
    # This matches what the user selects in the select element
    # in the webform to the python object on the backend.
    tables_of_interest = {}
    for item in di.__dict__.keys():
        table = getattr(di, item)
        if hasattr(table, '__tablename__'):
            tables_of_interest[table.__tablename__] = table

    session, _, _, _ = load_connection(get_config()['connection_string'])
    table_object = tables_of_interest[tablename]  # Select table object

    result = session.query(table_object)

    # Turn query result into list of dicts
    result_dict = [row.__dict__ for row in result.all()]
    column_names = table_object.__table__.columns.keys()

    # Build list of column data based on column name.
    data = []
    for column in column_names:
        column_data = list(map(itemgetter(column), result_dict))
        data.append(column_data)

    data = dict(zip(column_names, data))

    # Build table.
    table_meta_data = pd.DataFrame(data)

    session.close()
    return table_meta_data


def data_trending():
    """Container for Miri datatrending dashboard and components

    Returns
    -------
    variables : int
        nonsense
    dashboard : list
        A list containing the JavaScript and HTML content for the
        dashboard
    """
    dashboard, variables = miri_dash.data_trending_dashboard()

    return variables, dashboard


def nirspec_trending():
    """Container for Miri datatrending dashboard and components

    Returns
    -------
    variables : int
        nonsense
    dashboard : list
        A list containing the JavaScript and HTML content for the
        dashboard
    """
    dashboard, variables = nirspec_dash.data_trending_dashboard()

    return variables, dashboard


def get_acknowledgements():
    """Returns a list of individuals who are acknowledged on the
    ``about`` page.

    The list is generated by reading in the contents of the ``jwql``
    ``README`` file.  In this way, the website will automatically
    update with updates to the ``README`` file.

    Returns
    -------
    acknowledgements : list
        A list of individuals to be acknowledged.
    """

    # Locate README file
    readme_file = os.path.join(REPO_DIR, 'README.md')

    # Get contents of the README file
    with open(readme_file, 'r') as f:
        data = f.readlines()

    # Find where the acknowledgements start
    for i, line in enumerate(data):
        if 'Acknowledgments' in line:
            index = i

    # Parse out the list of individuals
    acknowledgements = data[index + 1:]
    acknowledgements = [item.strip().replace('- ', '').split(' [@')[0].strip()
                        for item in acknowledgements]

    return acknowledgements


def get_all_proposals():
    """Return a list of all proposals that exist in the filesystem.

    Returns
    -------
    proposals : list
        A list of proposal numbers for all proposals that exist in the
        filesystem
    """

    proposals = glob.glob(os.path.join(FILESYSTEM_DIR, 'public', '*'))
    proposals.extend(glob.glob(os.path.join(FILESYSTEM_DIR, 'proprietary', '*')))
    proposals = sorted(list(set(proposals)))
    proposals = [proposal.split('jw')[-1] for proposal in proposals]
    proposals = [proposal for proposal in proposals if len(proposal) == 5]

    return proposals


def get_current_flagged_anomalies(rootname, instrument):
    """Return a list of currently flagged anomalies for the given
    ``rootname``

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00001_guider2/``)

    Returns
    -------
    current_anomalies : list
        A list of currently flagged anomalies for the given ``rootname``
        (e.g. ``['snowball', 'crosstalk']``)
    """

    table_dict = {}
    table_dict[instrument.lower()] = getattr(di, '{}Anomaly'.format(JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]))

    table = table_dict[instrument.lower()]
    query = di.session.query(table).filter(table.rootname == rootname).order_by(table.flag_date.desc()).limit(1)

    all_records = query.data_frame
    if not all_records.empty:
        current_anomalies = [col for col, val in np.sum(all_records, axis=0).items() if val]
    else:
        current_anomalies = []

    return current_anomalies


def get_dashboard_components(request):
    """Build and return dictionaries containing components and html
    needed for the dashboard.

    Returns
    -------
    dashboard_components : dict
        A dictionary containing components needed for the dashboard.
    dashboard_html : dict
        A dictionary containing full HTML needed for the dashboard.
    """

    from jwql.website.apps.jwql.bokeh_dashboard import GeneralDashboard

    if 'time_delta_value' in request.POST:
        time_delta_value = request.POST['timedelta']

        if time_delta_value == 'All Time':
            time_delta = None
        else:
            time_delta_options = {'All Time': None,
                                  '1 Day': pd.DateOffset(days=1),
                                  '1 Month': pd.DateOffset(months=1),
                                  '1 Week': pd.DateOffset(weeks=1),
                                  '1 Year': pd.DateOffset(years=1)}
            time_delta = time_delta_options[time_delta_value]

        dashboard = GeneralDashboard(delta_t=time_delta)

        return dashboard
    else:
        # When coming from home/monitor views
        dashboard = GeneralDashboard(delta_t=None)

        return dashboard


def get_edb_components(request):
    """Return dictionary with content needed for the EDB page.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    edb_components : dict
        Dictionary with the required components

    """
    mnemonic_name_search_result = {}
    mnemonic_query_result = {}
    mnemonic_query_result_plot = None
    mnemonic_exploration_result = None
    mnemonic_query_status = None
    mnemonic_table_result = None

    # If this is a POST request, we need to process the form data
    if request.method == 'POST':

        if 'mnemonic_name_search' in request.POST.keys():
            # authenticate with astroquery.mast if necessary
            logged_in = log_into_mast(request)

            mnemonic_name_search_form = MnemonicSearchForm(request.POST, logged_in=logged_in,
                                                           prefix='mnemonic_name_search')

            if mnemonic_name_search_form.is_valid():
                mnemonic_identifier = mnemonic_name_search_form['search'].value()
                if mnemonic_identifier is not None:
                    mnemonic_name_search_result = get_mnemonic_info(mnemonic_identifier)

            # create forms for search fields not clicked
            mnemonic_query_form = MnemonicQueryForm(prefix='mnemonic_query')
            mnemonic_exploration_form = MnemonicExplorationForm(prefix='mnemonic_exploration')

        elif 'mnemonic_query' in request.POST.keys():
            # authenticate with astroquery.mast if necessary
            logged_in = log_into_mast(request)

            mnemonic_query_form = MnemonicQueryForm(request.POST, logged_in=logged_in,
                                                    prefix='mnemonic_query')

            # proceed only if entries make sense
            if mnemonic_query_form.is_valid():
                mnemonic_identifier = mnemonic_query_form['search'].value()
                start_time = Time(mnemonic_query_form['start_time'].value(), format='iso')
                end_time = Time(mnemonic_query_form['end_time'].value(), format='iso')

                if mnemonic_identifier is not None:
                    mnemonic_query_result = get_mnemonic(mnemonic_identifier, start_time, end_time)

                    if len(mnemonic_query_result.data) == 0:
                        mnemonic_query_status = "QUERY RESULT RETURNED NO DATA FOR {} ON DATES {} - {}".format(mnemonic_identifier, start_time, end_time)
                    else:
                        mnemonic_query_status = 'SUCCESS'

                        # If else to determine data visualization.
                        if type(mnemonic_query_result.data['euvalues'][0]) == np.str_:
                            if len(np.unique(mnemonic_query_result.data['euvalues'])) > 4:
                                mnemonic_table_result = mnemonic_query_result.get_table_data()
                            else:
                                mnemonic_query_result_plot = mnemonic_query_result.bokeh_plot_text_data()
                        else:
                            mnemonic_query_result_plot = mnemonic_query_result.bokeh_plot()

                        # generate table download in web app
                        result_table = mnemonic_query_result.data

                        # save file locally to be available for download
                        static_dir = os.path.join(settings.BASE_DIR, 'static')
                        ensure_dir_exists(static_dir)
                        file_name_root = 'mnemonic_query_result_table'
                        file_for_download = '{}.csv'.format(file_name_root)
                        path_for_download = os.path.join(static_dir, file_for_download)

                        # add meta data to saved table
                        comments = []
                        comments.append('DMS EDB query of {}:'.format(mnemonic_identifier))
                        for key, value in mnemonic_query_result.info.items():
                            comments.append('{} = {}'.format(key, str(value)))
                        result_table.meta['comments'] = comments
                        comments.append(' ')
                        comments.append('Start time {}'.format(start_time.isot))
                        comments.append('End time   {}'.format(end_time.isot))
                        comments.append('Number of rows {}'.format(len(result_table)))
                        comments.append(' ')
                        result_table.write(path_for_download, format='ascii.fixed_width',
                                           overwrite=True, delimiter=',', bookend=False)
                        mnemonic_query_result.file_for_download = file_for_download

            # create forms for search fields not clicked
            mnemonic_name_search_form = MnemonicSearchForm(prefix='mnemonic_name_search')
            mnemonic_exploration_form = MnemonicExplorationForm(prefix='mnemonic_exploration')

        elif 'mnemonic_exploration' in request.POST.keys():
            mnemonic_exploration_form = MnemonicExplorationForm(request.POST,
                                                                prefix='mnemonic_exploration')
            if mnemonic_exploration_form.is_valid():
                mnemonic_exploration_result, meta = mnemonic_inventory()

                # loop over filled fields and implement simple AND logic
                for field in mnemonic_exploration_form.fields:
                    field_value = mnemonic_exploration_form[field].value()
                    if field_value != '':
                        column_name = mnemonic_exploration_form[field].label

                        # matching indices in table (case-insensitive)
                        index = [
                            i for i, item in enumerate(mnemonic_exploration_result[column_name]) if
                            re.search(field_value, item, re.IGNORECASE)
                        ]
                        mnemonic_exploration_result = mnemonic_exploration_result[index]

                mnemonic_exploration_result.n_rows = len(mnemonic_exploration_result)

                # generate tables for display and download in web app
                display_table = copy.deepcopy(mnemonic_exploration_result)

                # temporary html file,
                # see http://docs.astropy.org/en/stable/_modules/astropy/table/
                tmpdir = tempfile.mkdtemp()
                file_name_root = 'mnemonic_exploration_result_table'
                path_for_html = os.path.join(tmpdir, '{}.html'.format(file_name_root))
                with open(path_for_html, 'w') as tmp:
                    display_table.write(tmp, format='jsviewer')
                mnemonic_exploration_result.html_file_content = open(path_for_html, 'r').read()

                # pass on meta data to have access to total number of mnemonics
                mnemonic_exploration_result.meta = meta

                # save file locally to be available for download
                static_dir = os.path.join(settings.BASE_DIR, 'static')
                ensure_dir_exists(static_dir)
                file_for_download = '{}.csv'.format(file_name_root)
                path_for_download = os.path.join(static_dir, file_for_download)
                display_table.write(path_for_download, format='ascii.fixed_width',
                                    overwrite=True, delimiter=',', bookend=False)
                mnemonic_exploration_result.file_for_download = file_for_download

                if mnemonic_exploration_result.n_rows == 0:
                    mnemonic_exploration_result = 'empty'

            # create forms for search fields not clicked
            mnemonic_name_search_form = MnemonicSearchForm(prefix='mnemonic_name_search')
            mnemonic_query_form = MnemonicQueryForm(prefix='mnemonic_query')

    else:
        mnemonic_name_search_form = MnemonicSearchForm(prefix='mnemonic_name_search')
        mnemonic_query_form = MnemonicQueryForm(prefix='mnemonic_query')
        mnemonic_exploration_form = MnemonicExplorationForm(prefix='mnemonic_exploration')

    edb_components = {'mnemonic_query_form': mnemonic_query_form,
                      'mnemonic_query_result': mnemonic_query_result,
                      'mnemonic_query_result_plot': mnemonic_query_result_plot,
                      'mnemonic_query_status': mnemonic_query_status,
                      'mnemonic_name_search_form': mnemonic_name_search_form,
                      'mnemonic_name_search_result': mnemonic_name_search_result,
                      'mnemonic_exploration_form': mnemonic_exploration_form,
                      'mnemonic_exploration_result': mnemonic_exploration_result,
                      'mnemonic_table_result': mnemonic_table_result}

    return edb_components


def get_expstart(instrument, rootname):
    """Return the exposure start time (``expstart``) for the given
    ``rootname``.

    The ``expstart`` is gathered from a query to the
    ``astroquery.mast`` service.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    rootname : str
        The rootname of the observation of interest (e.g.
        ``jw86700006001_02101_00006_guider1``).

    Returns
    -------
    expstart : float
        The exposure start time of the observation (in MJD).
    """

    if '-seg' in rootname:
        file_set_name = rootname.split('-')[0]
    else:
        file_set_name = '_'.join(rootname.split('_')[:-1])

    service = INSTRUMENT_SERVICE_MATCH[instrument]
    params = {
        'columns': 'filename, expstart',
        'filters': [{'paramName': 'fileSetName', 'values': [file_set_name]}]}
    response = Mast.service_request_async(service, params)
    result = response[0].json()

    if result['data'] == []:
        expstart = 0
        print("WARNING: no data")
    else:
        expstart = min([item['expstart'] for item in result['data']])

    return expstart


def get_filenames_by_instrument(instrument, restriction='all', query_file=None, query_response=None):
    """Returns a list of filenames that match the given ``instrument``.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    restriction : str
        If ``all``, all filenames will be returned.  If ``public``,
        only publicly-available filenames will be returned.  If
        ``proprietary``, only proprietary filenames will be returned.
    query_file : str
        Name of a file containing a list of filenames. If provided, the
        filenames in this file will be used rather than calling mask_query_filenames_by_instrument.
        This can save a significant amount of time when the number of files is large.
    query_response : dict
        Dictionary with "data" key ontaining a list of filenames. This is assumed to
        essentially be the returned value from a call to mast_query_filenames_by_instrument.
        If this is provided, the call to that function is skipped, which can save a
        significant amount of time.

    Returns
    -------
    filenames : list
        A list of files that match the given instrument.
    """
    if not query_file and not query_response:
        result = mast_query_filenames_by_instrument(instrument)

    elif query_response:
        result = query_response
    elif query_file:
        with open(query_file) as fobj:
            result = fobj.readlines()

    # Determine filenames to return based on restriction parameter
    if restriction == 'all':
        filenames = [item['filename'] for item in result['data']]
    elif restriction == 'public':
        filenames = [item['filename'] for item in result['data'] if item['isRestricted'] is False]
    elif restriction == 'proprietary':
        filenames = [item['filename'] for item in result['data'] if item['isRestricted'] is True]
    else:
        raise KeyError('{} is not a valid restriction level.  Use "all", "public", or "proprietary".'.format(restriction))

    return filenames


def mast_query_filenames_by_instrument(instrument):
    """Query MAST for filenames for the given instrument. Return the json
    response from MAST.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    """
    service = INSTRUMENT_SERVICE_MATCH[instrument]
    params = {"columns": "filename, isRestricted", "filters": []}
    response = Mast.service_request_async(service, params)
    result = response[0].json()
    return result


def get_filenames_by_proposal(proposal):
    """Return a list of filenames that are available in the filesystem
    for the given ``proposal``.

    Parameters
    ----------
    proposal : str
        The one- to five-digit proposal number (e.g. ``88600``).

    Returns
    -------
    filenames : list
        A list of filenames associated with the given ``proposal``.
    """

    proposal_string = '{:05d}'.format(int(proposal))
    filenames = glob.glob(os.path.join(FILESYSTEM_DIR, 'public', 'jw{}'.format(proposal_string), '*/*'))
    filenames.extend(glob.glob(os.path.join(FILESYSTEM_DIR, 'proprietary', 'jw{}'.format(proposal_string), '*/*')))
    filenames = sorted([os.path.basename(filename) for filename in filenames])

    return filenames


def get_filenames_by_rootname(rootname):
    """Return a list of filenames that are part of the given
    ``rootname``.

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    filenames : list
        A list of filenames associated with the given ``rootname``.
    """

    proposal_dir = rootname[0:7]
    observation_dir = rootname.split('_')[0]

    filenames = glob.glob(os.path.join(FILESYSTEM_DIR, 'public', proposal_dir, observation_dir, '{}_[!o]*'.format(rootname)))
    filenames.extend(glob.glob(os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir, observation_dir, '{}_[!o]*'.format(rootname))))
    filenames = sorted([os.path.basename(filename) for filename in filenames])

    return filenames


def get_header_info(filename, filetype):
    """Return the header information for a given ``filename``.

    Parameters
    ----------
    filename : str
        The name of the file of interest, without the extension
        (e.g. ``'jw86600008001_02101_00007_guider2_uncal'``).
    filetype : str
        The type of the file of interest, (e.g. ``'uncal'``)

    Returns
    -------
    header_info : dict
        The FITS headers of the extensions in the given ``file``.
    """

    # Initialize dictionary to store header information
    header_info = {}

    # Open the file
    fits_filepath = filesystem_path(filename, search=f'*_{filetype}.fits')
    hdulist = fits.open(fits_filepath)

    # Extract header information from file
    for ext in range(0, len(hdulist)):

        # Initialize dictionary to store header information for particular extension
        header_info[ext] = {}

        # Get header
        header = hdulist[ext].header

        # Determine the extension name
        if ext == 0:
            header_info[ext]['EXTNAME'] = 'PRIMARY'
        else:
            header_info[ext]['EXTNAME'] = header['EXTNAME']

        # Get list of keywords and values
        exclude_list = ['', 'COMMENT']
        header_info[ext]['keywords'] = [item for item in list(header.keys()) if item not in exclude_list]
        header_info[ext]['values'] = []
        for key in header_info[ext]['keywords']:
            header_info[ext]['values'].append(hdulist[ext].header[key])

    # Close the file
    hdulist.close()

    # Build tables
    for ext in header_info:
        data_dict = {}
        data_dict['Keyword'] = header_info[ext]['keywords']
        data_dict['Value'] = header_info[ext]['values']
        header_info[ext]['table'] = pd.DataFrame(data_dict)
        header_info[ext]['table_rows'] = header_info[ext]['table'].values
        header_info[ext]['table_columns'] = header_info[ext]['table'].columns.values

    return header_info


def get_image_info(file_root, rewrite):
    """Build and return a dictionary containing information for a given
    ``file_root``.

    Parameters
    ----------
    file_root : str
        The rootname of the file of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).
    rewrite : bool
        ``True`` if the corresponding JPEG needs to be rewritten,
        ``False`` if not.

    Returns
    -------
    image_info : dict
        A dictionary containing various information for the given
        ``file_root``.
    """

    # Initialize dictionary to store information
    image_info = {}
    image_info['all_jpegs'] = []
    image_info['suffixes'] = []
    image_info['num_ints'] = {}
    image_info['available_ints'] = {}

    # Find all of the matching files
    proposal_dir = file_root[:7]
    observation_dir = file_root[:13]
    filenames = glob.glob(os.path.join(FILESYSTEM_DIR, 'public', proposal_dir, observation_dir, '{}*.fits'.format(file_root)))
    filenames.extend(glob.glob(os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir, observation_dir, '{}*.fits'.format(file_root))))
    image_info['all_files'] = filenames

    # Determine the jpg directory
    prev_img_filesys = configs['preview_image_filesystem']
    jpg_dir = os.path.join(prev_img_filesys, proposal_dir)

    for filename in image_info['all_files']:

        # Get suffix information
        suffix = os.path.basename(filename).split('_')[4].split('.')[0]
        image_info['suffixes'].append(suffix)

        # Determine JPEG file location
        jpg_filename = os.path.basename(os.path.splitext(filename)[0] + '_integ0.jpg')
        jpg_filepath = os.path.join(jpg_dir, jpg_filename)

        # Check that a jpg does not already exist. If it does (and rewrite=False),
        # just call the existing jpg file
        if os.path.exists(jpg_filepath) and not rewrite:
            pass

        # Record how many integrations there are per filetype
        jpgs = glob.glob(os.path.join(prev_img_filesys, observation_dir, '{}_{}_integ*.jpg'.format(file_root, suffix)))
        image_info['num_ints'][suffix] = len(jpgs)
        image_info['available_ints'][suffix] = sorted([int(jpg.split('_')[-1].replace('.jpg', '').replace('integ', '')) for jpg in jpgs])
        image_info['all_jpegs'].append(jpg_filepath)

    return image_info


def get_instrument_proposals(instrument):
    """Return a list of proposals for the given instrument

    Parameters
    ----------
    instrument : str
        Name of the JWST instrument, with first letter capitalized
        (e.g. ``Fgs``)

    Returns
    -------
    proposals : list
        List of proposals for the given instrument
    """

    service = "Mast.Jwst.Filtered.{}".format(instrument)
    params = {"columns": "program",
              "filters": []}
    response = Mast.service_request_async(service, params)
    results = response[0].json()['data']
    proposals = list(set(result['program'] for result in results))

    return proposals


def get_preview_images_by_instrument(inst):
    """Return a list of preview images available in the filesystem for
    the given instrument.

    Parameters
    ----------
    inst : str
        The instrument of interest (e.g. ``NIRCam``).

    Returns
    -------
    preview_images : list
        A list of preview images available in the filesystem for the
        given instrument.
    """

    # Make sure the instrument is of the proper format (e.g. "Nircam")
    instrument = inst[0].upper() + inst[1:].lower()

    # Query MAST for all rootnames for the instrument
    service = "Mast.Jwst.Filtered.{}".format(instrument)
    params = {"columns": "filename",
              "filters": []}
    response = Mast.service_request_async(service, params)
    results = response[0].json()['data']

    # Parse the results to get the rootnames
    filenames = [result['filename'].split('.')[0] for result in results]

    # Get list of all preview_images. Text file contains only preview
    # images for a single instrument.
    preview_list_file = f"{PREVIEW_IMAGE_LISTFILE}_{inst.lower()}.txt"
    preview_images = retrieve_filelist(os.path.join(PREVIEW_IMAGE_FILESYSTEM, preview_list_file))

    # DO WE NEED TO DO THIS??? I GUESS THIS GETS RID OF ANY PREVIEW IMAGES
    # THAT DON'T MATCH UP TO OBSERVATION FILES.
    # Get subset of preview images that match the filenames
    #preview_images = [os.path.basename(item) for item in preview_images if
    #                  os.path.basename(item).split('_integ')[0] in filenames]

    # Return only
    return preview_images


def get_preview_images_by_proposal(proposal):
    """Return a list of preview images available in the filesystem for
    the given ``proposal``.

    Parameters
    ----------
    proposal : str
        The one- to five-digit proposal number (e.g. ``88600``).

    Returns
    -------
    preview_images : list
        A list of preview images available in the filesystem for the
        given ``proposal``.
    """

    proposal_string = '{:05d}'.format(int(proposal))
    preview_images = glob.glob(os.path.join(PREVIEW_IMAGE_FILESYSTEM, 'jw{}'.format(proposal_string), '*'))
    preview_images = [os.path.basename(preview_image) for preview_image in preview_images]

    return preview_images


def get_preview_images_by_rootname(rootname):
    """Return a list of preview images available in the filesystem for
    the given ``rootname``.

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    preview_images : list
        A list of preview images available in the filesystem for the
        given ``rootname``.
    """

    proposal = rootname.split('_')[0].split('jw')[-1][0:5]
    preview_images = sorted(glob.glob(os.path.join(
        PREVIEW_IMAGE_FILESYSTEM,
        'jw{}'.format(proposal),
        '{}*'.format(rootname))))
    preview_images = [os.path.basename(preview_image) for preview_image in preview_images]

    return preview_images


def get_proposal_info(filepaths):
    """Builds and returns a dictionary containing various information
    about the proposal(s) that correspond to the given ``filepaths``.

    The information returned contains such things as the number of
    proposals, the paths to the corresponding thumbnails, and the total
    number of files.

    Parameters
    ----------
    filepaths : list
        A list of full paths to files of interest.

    Returns
    -------
    proposal_info : dict
        A dictionary containing various information about the
        proposal(s) and files corresponding to the given ``filepaths``.
    """

    # Initialize some containers
    thumbnail_paths = []
    num_files = []

    # Gather thumbnails and counts for proposals
    proposals, thumbnail_paths, num_files = [], [], []
    for filepath in filepaths:
        proposal = filepath.split('/')[-1][2:7]
        if proposal not in proposals:
            thumbnail_paths.append(os.path.join('jw{}'.format(proposal), 'jw{}.thumb'.format(proposal)))
            files_for_proposal = [item for item in filepaths if 'jw{}'.format(proposal) in item]
            num_files.append(len(files_for_proposal))
            proposals.append(proposal)

    # Put the various information into a dictionary of results
    proposal_info = {}
    proposal_info['num_proposals'] = len(proposals)
    proposal_info['proposals'] = proposals
    proposal_info['thumbnail_paths'] = thumbnail_paths
    proposal_info['num_files'] = num_files

    return proposal_info


def get_thumbnails_all_instruments(parameters):
    """Return a list of thumbnails available in the filesystem for all
    instruments given requested MAST parameters and queried anomalies.

    Parameters
    ----------
    parameters: dict
        A dictionary containing the following keys, some of which are dictionaries:
            instruments
            apertures
            filters
            detector
            effexptm_min
            effexptm_max
            anomalies

    Returns
    -------
    thumbnails : list
        A list of thumbnails available in the filesystem for the
        given instrument.
    """

    anomalies = parameters['anomalies']

    thumbnails_subset = []

    for inst in parameters['instruments']:
        # Make sure instruments are of the proper format (e.g. "Nircam")
        instrument = inst[0].upper() + inst[1:].lower()

        # Query MAST for all rootnames for the instrument
        service = "Mast.Jwst.Filtered.{}".format(instrument)

        if ((parameters['apertures'][inst.lower()] == [])
                and (parameters['detectors'][inst.lower()] == [])
                and (parameters['filters'][inst.lower()] == [])
                and (parameters['exposure_types'][inst.lower()] == [])
                and (parameters['read_patterns'][inst.lower()] == [])):
            params = {"columns": "*", "filters": []}
        else:
            query_filters = []
            if (parameters['apertures'][inst.lower()] != []):
                if instrument != "Nircam":
                    query_filters.append({"paramName": "pps_aper", "values": parameters['apertures'][inst.lower()]})
                if instrument == "Nircam":
                    query_filters.append({"paramName": "apername", "values": parameters['apertures'][inst.lower()]})
            if (parameters['detectors'][inst.lower()] != []):
                query_filters.append({"paramName": "detector", "values": parameters['detectors'][inst.lower()]})
            if (parameters['filters'][inst.lower()] != []):
                query_filters.append({"paramName": "filter", "values": parameters['filters'][inst.lower()]})
            if (parameters['exposure_types'][inst.lower()] != []):
                query_filters.append({"paramName": "exp_type", "values": parameters['exposure_types'][inst.lower()]})
            if (parameters['read_patterns'][inst.lower()] != []):
                query_filters.append({"paramName": "readpatt", "values": parameters['read_patterns'][inst.lower()]})
            params = {"columns": "*",
                      "filters": query_filters}

        response = Mast.service_request_async(service, params)
        results = response[0].json()['data']

        inst_filenames = [result['filename'].split('.')[0] for result in results]

        # Get list of all thumbnails
        thumbnail_list_file = f"{THUMBNAIL_LISTFILE}_{inst.lower()}.txt"
        thumbnail_inst_list = retrieve_filelist(os.path.join(THUMBNAIL_FILESYSTEM, THUMBNAIL_LISTFILE))

        # Get subset of thumbnail images that match the filenames
        thumbnails_inst_subset = [os.path.basename(item) for item in thumbnail_inst_list if
                                  os.path.basename(item).split('_integ')[0] in inst_filenames]

        # Eliminate any duplicates
        thumbnails_inst_subset = list(set(thumbnails_inst_subset))
        thumbnails_subset.extend(thumbnails_inst_subset)

    # Determine whether or not queried anomalies are flagged
    final_subset = []

    if anomalies != {'miri': [], 'nirspec': [], 'niriss': [], 'nircam': [], 'fgs': []}:
        for thumbnail in thumbnails_subset:
            components = thumbnail.split('_')
            rootname = ''.join((components[0], '_', components[1], '_', components[2], '_', components[3]))
            try:
                instrument = filename_parser(thumbnail)['instrument']
                thumbnail_anomalies = get_current_flagged_anomalies(rootname, instrument)
                if thumbnail_anomalies:
                    for anomaly in anomalies[instrument.lower()]:
                        if anomaly.lower() in thumbnail_anomalies:
                            # thumbnail contains an anomaly selected in the query
                            final_subset.append(thumbnail)
            except KeyError:
                print("Error with thumbnail: ", thumbnail)
    else:
        # if no anomalies are flagged, return all thumbnails from query
        final_subset = thumbnails_subset

    return list(set(final_subset))


def get_thumbnails_by_instrument(inst):
    """Return a list of thumbnails available in the filesystem for the
    given instrument.

    Parameters
    ----------
    inst : str
        The instrument of interest (e.g. ``NIRCam``).

    Returns
    -------
    preview_images : list
        A list of thumbnails available in the filesystem for the
        given instrument.
    """

    # Make sure the instrument is of the proper format (e.g. "Nircam")
    instrument = inst[0].upper() + inst[1:].lower()

    # Query MAST for all rootnames for the instrument
    service = "Mast.Jwst.Filtered.{}".format(instrument)
    params = {"columns": "filename",
              "filters": []}
    response = Mast.service_request_async(service, params)
    results = response[0].json()['data']

    # Parse the results to get the rootnames
    filenames = [result['filename'].split('.')[0] for result in results]

    # Get list of all thumbnails
    thumbnails = retrieve_filelist(os.path.join(THUMBNAIL_FILESYSTEM, THUMBNAIL_LISTFILE))

    # Get subset of preview images that match the filenames
    thumbnails = [os.path.basename(item) for item in thumbnails if
                  os.path.basename(item).split('_integ')[0] in filenames]

    return thumbnails


def get_thumbnails_by_proposal(proposal):
    """Return a list of thumbnails available in the filesystem for the
    given ``proposal``.

    Parameters
    ----------
    proposal : str
        The one- to five-digit proposal number (e.g. ``88600``).

    Returns
    -------
    thumbnails : list
        A list of thumbnails available in the filesystem for the given
        ``proposal``.
    """

    proposal_string = '{:05d}'.format(int(proposal))
    thumbnails = glob.glob(os.path.join(THUMBNAIL_FILESYSTEM, 'jw{}'.format(proposal_string), '*'))
    thumbnails = [os.path.basename(thumbnail) for thumbnail in thumbnails]

    return thumbnails


def get_thumbnails_by_rootname(rootname):
    """Return a list of preview images available in the filesystem for
    the given ``rootname``.

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    thumbnails : list
        A list of preview images available in the filesystem for the
        given ``rootname``.
    """

    proposal = rootname.split('_')[0].split('jw')[-1][0:5]
    thumbnails = sorted(glob.glob(os.path.join(
        THUMBNAIL_FILESYSTEM,
        'jw{}'.format(proposal),
        '{}*'.format(rootname))))

    thumbnails = [os.path.basename(thumbnail) for thumbnail in thumbnails]

    return thumbnails


def log_into_mast(request):
    """Login via astroquery.mast if user authenticated in web app.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    """
    if Mast.authenticated():
        return True

    # get the MAST access token if present
    access_token = str(get_mast_token(request))

    # authenticate with astroquery.mast if necessary
    # nosec comment added to ignore bandit security check
    if access_token != 'None':  # nosec
        Mast.login(token=access_token)
        return Mast.authenticated()
    else:
        return False


def random_404_page():
    """Randomly select one of the various 404 templates for JWQL

    Returns
    -------
    random_template : str
        Filename of the selected template
    """
    templates = ['404_space.html', '404_spacecat.html']
    choose_page = np.random.choice(len(templates))
    random_template = templates[choose_page]

    return random_template


def retrieve_filelist(filename):
    """Return a list of all thumbnail files in the filesystem from
    a list file.

    Parameters
    ----------
    filename : str
        Name of a text file containing a list of files
    """
    with open(filename) as fobj:
        file_list = fobj.read().splitlines()
    return file_list


def text_scrape(prop_id):
    """Scrapes the Proposal Information Page.

    Parameters
    ----------
    prop_id : int
        Proposal ID

    Returns
    -------
    program_meta : dict
        Dictionary containing information about program
    """

    # Generate url
    url = 'http://www.stsci.edu/cgi-bin/get-proposal-info?id=' + str(prop_id) + '&submit=Go&observatory=JWST'
    html = BeautifulSoup(requests.get(url).text, 'lxml')
    lines = html.findAll('p')
    lines = [str(line) for line in lines]

    program_meta = {}
    program_meta['prop_id'] = prop_id
    program_meta['phase_two'] = '<a href=https://www.stsci.edu/jwst/phase2-public/{}.pdf target="_blank"> Phase Two</a>'

    if prop_id[0] == '0':
        program_meta['phase_two'] = program_meta['phase_two'].format(prop_id[1:])
    else:
        program_meta['phase_two'] = program_meta['phase_two'].format(prop_id)

    program_meta['phase_two'] = BeautifulSoup(program_meta['phase_two'], 'html.parser')

    links = html.findAll('a')
    proposal_type = links[0].contents[0]

    program_meta['prop_type'] = proposal_type

    # Scrape for titles/names/contact persons
    for line in lines:
        if 'Title' in line:
            start = line.find('</b>') + 4
            end = line.find('<', start)
            title = line[start:end]
            program_meta['title'] = title

        if 'Principal Investigator:' in line:
            start = line.find('</b>') + 4
            end = line.find('<', start)
            pi = line[start:end]
            program_meta['pi'] = pi

        if 'Program Coordinator' in line:
            start = line.find('</b>') + 4
            mid = line.find('<', start)
            end = line.find('>', mid) + 1
            pc = line[mid:end] + line[start:mid] + '</a>'
            program_meta['pc'] = pc

        if 'Contact Scientist' in line:
            start = line.find('</b>') + 4
            mid = line.find('<', start)
            end = line.find('>', mid) + 1
            cs = line[mid:end] + line[start:mid] + '</a>'
            program_meta['cs'] = BeautifulSoup(cs, 'html.parser')

        if 'Program Status' in line:
            start = line.find('<a')
            end = line.find('</a>')
            ps = line[start:end]

            # beautiful soupify text to build absolute link
            ps = BeautifulSoup(ps, 'html.parser')
            ps_link = ps('a')[0]
            ps_link['href'] = 'https://www.stsci.edu' + ps_link['href']
            ps_link['target'] = '_blank'
            program_meta['ps'] = ps_link

    return program_meta


def thumbnails_ajax(inst, proposal=None):
    """Generate a page that provides data necessary to render the
    ``thumbnails`` template.

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    proposal : str (optional)
        Number of APT proposal to filter

    Returns
    -------
    data_dict : dict
        Dictionary of data needed for the ``thumbnails`` template
    """

    # Get the available files for the instrument
    filenames = get_filenames_by_instrument(inst)

    # Get set of unique rootnames
    rootnames = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filenames])

    # If the proposal is specified (i.e. if the page being loaded is
    # an archive page), only collect data for given proposal
    if proposal is not None:
        proposal_string = '{:05d}'.format(int(proposal))
        rootnames = [rootname for rootname in rootnames if rootname[2:7] == proposal_string]

    # Initialize dictionary that will contain all needed data
    data_dict = {}
    data_dict['inst'] = inst
    data_dict['file_data'] = {}

    # Gather data for each rootname
    for rootname in rootnames:

        # Parse filename
        try:
            filename_dict = filename_parser(rootname)

            # The detector keyword is expected in thumbnails_query_ajax() for generating filterable dropdown menus
            if 'detector' not in filename_dict.keys():
                filename_dict['detector'] = 'Unknown'

            # Weed out file types that are not supported by generate_preview_images
            if filename_dict['filename_type'] in ['stage_3_target_id']:
                continue

        except ValueError:
            # Temporary workaround for noncompliant files in filesystem
            filename_dict = {'activity': rootname[17:19],
                             'detector': rootname[26:],
                             'exposure_id': rootname[20:25],
                             'observation': rootname[7:10],
                             'parallel_seq_id': rootname[16],
                             'program_id': rootname[2:7],
                             'visit': rootname[10:13],
                             'visit_group': rootname[14:16]}

        # Get list of available filenames
        available_files = [item for item in filenames if rootname in item]

        # Add data to dictionary
        data_dict['file_data'][rootname] = {}
        data_dict['file_data'][rootname]['filename_dict'] = filename_dict
        data_dict['file_data'][rootname]['available_files'] = available_files
        data_dict['file_data'][rootname]['suffixes'] = [filename_parser(filename)['suffix'] for filename in available_files]
        try:
            data_dict['file_data'][rootname]['expstart'] = get_expstart(inst, rootname)
            data_dict['file_data'][rootname]['expstart_iso'] = Time(data_dict['file_data'][rootname]['expstart'], format='mjd').iso.split('.')[0]
        except:
            print("issue with get_expstart for {}".format(rootname))

    # Extract information for sorting with dropdown menus
    # (Don't include the proposal as a sorting parameter if the proposal has already been specified)
    detectors, proposals = [], []
    for rootname in list(data_dict['file_data'].keys()):
        proposals.append(data_dict['file_data'][rootname]['filename_dict']['program_id'])
        try:  # Some rootnames cannot parse out detectors
            detectors.append(data_dict['file_data'][rootname]['filename_dict']['detector'])
        except KeyError:
            pass

    if proposal is not None:
        dropdown_menus = {'detector': sorted(detectors)}
    else:
        dropdown_menus = {'detector': sorted(detectors),
                          'proposal': sorted(proposals)}

    data_dict['tools'] = MONITORS
    data_dict['dropdown_menus'] = dropdown_menus
    data_dict['prop'] = proposal

    # Order dictionary by descending expstart time.
    sorted_file_data = OrderedDict(sorted(data_dict['file_data'].items(),
                                   key=lambda x: getitem(x[1], 'expstart'), reverse=True))

    data_dict['file_data'] = sorted_file_data

    return data_dict


def thumbnails_query_ajax(rootnames):
    """Generate a page that provides data necessary to render the
    ``thumbnails`` template.

    Parameters
    ----------
    rootnames : list of strings (optional)
        Rootname of APT proposal to filter

    Returns
    -------
    data_dict : dict
        Dictionary of data needed for the ``thumbnails`` template
    """

    # Initialize dictionary that will contain all needed data
    data_dict = {}
    # dummy variable for view_image when thumbnail is selected
    data_dict['inst'] = "all"
    data_dict['file_data'] = {}
    # Gather data for each rootname
    for rootname in rootnames:
        # fit expected format for get_filenames_by_rootname()
        try:
            rootname = rootname.split("_")[0] + '_' + rootname.split("_")[1] + '_' + rootname.split("_")[2] + '_' + rootname.split("_")[3]
        except IndexError:
            continue

        # Parse filename
        try:
            filename_dict = filename_parser(rootname)
        except ValueError:
            # Temporary workaround for noncompliant files in filesystem
            filename_dict = {'activity': rootname[17:19],
                             'detector': rootname[26:],
                             'exposure_id': rootname[20:25],
                             'observation': rootname[7:10],
                             'parallel_seq_id': rootname[16],
                             'program_id': rootname[2:7],
                             'visit': rootname[10:13],
                             'visit_group': rootname[14:16]}

        # Get list of available filenames
        available_files = get_filenames_by_rootname(rootname)

        # Add data to dictionary
        data_dict['file_data'][rootname] = {}
        try:
            data_dict['file_data'][rootname]['inst'] = JWST_INSTRUMENT_NAMES_MIXEDCASE[filename_parser(rootname)['instrument']]
        except KeyError:
            data_dict['file_data'][rootname]['inst'] = "MIRI"
            print("Warning: assuming instrument is MIRI")
        data_dict['file_data'][rootname]['filename_dict'] = filename_dict
        data_dict['file_data'][rootname]['available_files'] = available_files
        data_dict['file_data'][rootname]['expstart'] = get_expstart(data_dict['file_data'][rootname]['inst'], rootname)
        data_dict['file_data'][rootname]['suffixes'] = [filename_parser(filename)['suffix'] for
                                                        filename in available_files]
        data_dict['file_data'][rootname]['prop'] = rootname[2:7]

    # Extract information for sorting with dropdown menus
    try:
        detectors = [data_dict['file_data'][rootname]['filename_dict']['detector'] for
                     rootname in list(data_dict['file_data'].keys())]
    except KeyError:
        detectors = []
        for rootname in list(data_dict['file_data'].keys()):
            try:
                detector = data_dict['file_data'][rootname]['filename_dict']['detector']
                detectors.append(detector) if detector not in detectors else detectors
            except KeyError:
                detector = 'Unknown'
                detectors.append(detector) if detector not in detectors else detectors

    instruments = [data_dict['file_data'][rootname]['inst'].lower() for
                   rootname in list(data_dict['file_data'].keys())]
    proposals = [data_dict['file_data'][rootname]['filename_dict']['program_id'] for
                 rootname in list(data_dict['file_data'].keys())]

    dropdown_menus = {'instrument': instruments,
                      'detector': detectors,
                      'proposal': proposals}

    data_dict['tools'] = MONITORS
    data_dict['dropdown_menus'] = dropdown_menus

    return data_dict
