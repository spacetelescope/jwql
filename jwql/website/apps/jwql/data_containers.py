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
    - Bryan Hilbert
    - Maria Pena-Guerrero
    - Bradley Sappington
    - Melanie Clarke

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
import json
from operator import getitem
import os
import re
import tempfile
import logging

from astropy.io import fits
from astropy.time import Time
from bs4 import BeautifulSoup
from django import setup
from django.conf import settings
from django.contrib import messages
import numpy as np
from operator import itemgetter
import pandas as pd
import pyvo as vo
import requests

from jwql.database import database_interface as di
from jwql.database.database_interface import load_connection
from jwql.edb.engineering_database import get_mnemonic, get_mnemonic_info, mnemonic_inventory
from jwql.utils.utils import check_config_for_key, ensure_dir_exists, filesystem_path, filename_parser, get_config
from jwql.utils.constants import ANOMALIES_PER_INSTRUMENT, MAST_QUERY_LIMIT, MONITORS, THUMBNAIL_LISTFILE, THUMBNAIL_FILTER_LOOK
from jwql.utils.constants import EXPOSURE_PAGE_SUFFIX_ORDER, IGNORED_SUFFIXES, INSTRUMENT_SERVICE_MATCH
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_INSTRUMENT_NAMES
from jwql.utils.constants import REPORT_KEYS_PER_INSTRUMENT
from jwql.utils.constants import SUFFIXES_TO_ADD_ASSOCIATION, SUFFIXES_WITH_AVERAGED_INTS, QUERY_CONFIG_KEYS
from jwql.utils.credentials import get_mast_token
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import get_rootnames_for_instrument_proposal
from .forms import InstrumentAnomalySubmitForm
from astroquery.mast import Mast

# Increase the limit on the number of entries that can be returned by
# a MAST query.
Mast._portal_api_connection.PAGESIZE = MAST_QUERY_LIMIT

# astroquery.mast import that depends on value of auth_mast
# this import has to be made before any other import of astroquery.mast
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

# Determine if the code is being run as part of a Readthedocs build
ON_READTHEDOCS = False
if 'READTHEDOCS' in os.environ:  # pragma: no cover
    ON_READTHEDOCS = os.environ['READTHEDOCS']

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # These lines are needed in order to use the Django models in a standalone
    # script (as opposed to code run as a result of a webpage request). If these
    # lines are not run, the script will crash when attempting to import the
    # Django models in the line below.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    setup()

    from .forms import MnemonicSearchForm, MnemonicQueryForm, MnemonicExplorationForm
    from jwql.website.apps.jwql.models import Observation, Proposal, RootFileInfo
    check_config_for_key('auth_mast')
    configs = get_config()
    auth_mast = configs['auth_mast']
    mast_flavour = '.'.join(auth_mast.split('.')[1:])
    from astropy import config
    conf = config.get_config('astroquery')
    conf['mast'] = {'server': 'https://{}'.format(mast_flavour)}

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    FILESYSTEM_DIR = configs['filesystem']
    PREVIEW_IMAGE_FILESYSTEM = configs['preview_image_filesystem']
    THUMBNAIL_FILESYSTEM = configs['thumbnail_filesystem']
    OUTPUT_DIR = configs['outputs']

PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]

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


def filter_root_files(instrument=None, proposal=None, obsnum=None, sort_as=None,
                      look=None, exp_type=None, cat_type=None, detector=None):
    """Retrieve and filter root file table entries.

    Parameters
    ----------
    instrument : str, optional
        Name of the JWST instrument.
    proposal : str, optional
        Proposal to match. Used as a 'starts with' filter.
    obsnum : str, optional
        Observation number to match.
    sort_as : {'ascending', 'descending', 'recent', 'oldest'}, optional
        Sorting method for output table. Ascending and descending
        options refer to root file name; recent and oldest sort by exposure
        start time.
    look : {'new', 'viewed'}, optional
        If set to None, all viewed values are returned. If set to
        'viewed', only viewed data is returned. If set to 'new', only
        new data is returned.
    exp_type : str, optional
        Set to filter by exposure type.
    cat_type : str, optional
        Set to filter by proposal category.
    detector : str, optional
        Set to filter by detector name.

    Returns
    -------
    root_file_info : QuerySet
        List of RootFileInfo entries matching input criteria.
    """
    # standardize input

    # get desired filters
    filter_kwargs = dict()
    if instrument is not None and str(instrument).strip().lower() != 'all':
        inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]
        filter_kwargs['instrument'] = inst
    if proposal is not None and str(proposal).strip().lower() != 'all':
        filter_kwargs['proposal__startswith'] = proposal.lstrip('0')
    if obsnum is not None and str(obsnum).strip().lower() != 'all':
        filter_kwargs['obsnum__obsnum'] = obsnum
    if look is not None and str(look).strip().lower() != 'all':
        filter_kwargs['viewed'] = (str(look).lower() == 'viewed')
    if exp_type is not None and str(exp_type).strip().lower() != 'all':
        filter_kwargs['exp_type__iexact'] = exp_type
    if cat_type is not None and str(cat_type).strip().lower() != 'all':
        filter_kwargs['obsnum__proposal__category__iexact'] = cat_type
    if detector is not None and str(detector).strip().lower() != 'all':
        filter_kwargs['detector__iexact'] = detector

    # get file info by instrument from local model
    root_file_info = RootFileInfo.objects.filter(**filter_kwargs)

    # descending by root file is default;
    # for other options, sort as desired
    sort_as = str(sort_as).strip().lower()
    if sort_as == 'ascending':
        root_file_info = root_file_info.order_by('root_name')
    elif sort_as == 'recent':
        root_file_info = root_file_info.order_by('-expstart', 'root_name')
    elif sort_as == 'oldest':
        root_file_info = root_file_info.order_by('expstart', 'root_name')

    return root_file_info.values()


def create_archived_proposals_context(inst):
    """Generate and save a json file containing the information needed
    to create an instrument's archive page.

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    # Get a list of Observation entries for the given instrument
    all_entries = Observation.objects.filter(proposal__archive__instrument=inst)

    # Get a list of proposal numbers.
    prop_objects = Proposal.objects.filter(archive__instrument=inst)
    proposal_nums = [entry.prop_id for entry in prop_objects]

    # Put proposals into descending order
    proposal_nums.sort(reverse=True)

    # Total number of proposals for the instrument
    num_proposals = len(proposal_nums)

    thumbnail_paths = []
    min_obsnums = []
    total_files = []
    proposal_viewed = []
    proposal_exp_types = []
    thumb_exp_types = []
    proposal_obs_times = []
    thumb_obs_time = []
    cat_types = []

    # Get a set of all exposure types used in the observations associated with this proposal
    exp_types = [exposure_type for observation in all_entries for exposure_type in observation.exptypes.split(',')]
    exp_types = sorted(set(exp_types))

    # Get all proposals based on category type
    proposals_by_category = get_proposals_by_category(inst)
    unique_cat_types = sorted(set(proposals_by_category.values()))

    # The naming conventions for dropdown_menus are tightly coupled with the code, this should be changed down the line.
    dropdown_menus = {'look': THUMBNAIL_FILTER_LOOK,
                      'exp_type': exp_types,
                      'cat_type': unique_cat_types}
    thumbnails_dict = {}

    for proposal_num in proposal_nums:
        # For each proposal number, get all entries
        prop_entries = all_entries.filter(proposal__prop_id=proposal_num)

        # All entries will have the same thumbnail_path, so just grab the first
        thumbnail_paths.append(prop_entries[0].proposal.thumbnail_path)

        # Extract the observation numbers from each entry and find the minimum
        prop_obsnums = [entry.obsnum for entry in prop_entries]
        min_obsnums.append(min(prop_obsnums))

        # Sum the file count from all observations to get the total file count for
        # the proposal
        prop_filecount = [entry.number_of_files for entry in prop_entries]
        total_files.append(sum(prop_filecount))

        # In order to know if a proposal contains all observations that
        # are entirely viewed, check for at least one existing
        # viewed=False in RootFileInfo
        unviewed_root_file_infos = RootFileInfo.objects.filter(instrument=inst, proposal=proposal_num, viewed=False)
        proposal_viewed.append("Viewed" if unviewed_root_file_infos.count() == 0 else "New")

        # Store comma separated list of exp_types associated with each proposal
        proposal_exp_types = [exposure_type for observation in prop_entries for exposure_type in observation.exptypes.split(',')]
        proposal_exp_types = list(set(proposal_exp_types))
        thumb_exp_types.append(','.join(proposal_exp_types))

        # Get Most recent observation start time
        proposal_obs_times = [observation.obsstart for observation in prop_entries]
        thumb_obs_time.append(max(proposal_obs_times))

        # Add category type to list based on proposal number
        cat_types.append(proposals_by_category[int(proposal_num)])

    thumbnails_dict['proposals'] = proposal_nums
    thumbnails_dict['thumbnail_paths'] = thumbnail_paths
    thumbnails_dict['num_files'] = total_files
    thumbnails_dict['viewed'] = proposal_viewed
    thumbnails_dict['exp_types'] = thumb_exp_types
    thumbnails_dict['obs_time'] = thumb_obs_time
    thumbnails_dict['cat_types'] = cat_types

    context = {'inst': inst,
               'num_proposals': num_proposals,
               'min_obsnum': min_obsnums,
               'thumbnails': thumbnails_dict,
               'dropdown_menus': dropdown_menus}

    json_object = json.dumps(context, indent = 4)

    # Writing to json file
    outfilename = os.path.join(OUTPUT_DIR, 'archive_page', f'{inst}_archive_context.json')
    with open(outfilename, "w") as outfile:
        outfile.write(json_object)
    set_permissions(outfilename)


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
    proprietary_proposals = os.listdir(os.path.join(FILESYSTEM_DIR, 'proprietary'))
    public_proposals = os.listdir(os.path.join(FILESYSTEM_DIR, 'public'))
    all_proposals = [prop[2:] for prop in proprietary_proposals + public_proposals if 'jw' in prop]
    proposals = sorted(list(set(all_proposals)), reverse=True)
    return proposals


def get_available_suffixes(all_suffixes, return_untracked=True):
    """
    Put available suffixes in a consistent order.

    Any suffixes not recognized are returned at the end of the suffix
    list, in random order.

    Parameters
    ----------
    all_suffixes : list of str
        List of all data product suffixes found for a given file root.
    return_untracked : bool, optional
        If set, a set of untracked suffixes is also returned, for
        logging or diagnostic purposes.

    Returns
    -------
    suffixes : list of str
        All available unique suffixes in standard order.
    untracked_suffixes : set of str, optional
        Any suffixes that were not recognized.
    """
    #  Check if any of the
    # suffixes are not in the list that specifies order.
    suffixes = []
    untracked_suffixes = set(all_suffixes)
    for poss_suffix in EXPOSURE_PAGE_SUFFIX_ORDER:
        if 'crf' not in poss_suffix:
            if (poss_suffix in all_suffixes
                    and poss_suffix not in suffixes):
                suffixes.append(poss_suffix)
                untracked_suffixes.remove(poss_suffix)
        else:
            # EXPOSURE_PAGE_SUFFIX_ORDER contains crf and crfints,
            # but the actual suffixes in the data will be e.g. o001_crf,
            # and there may be more than one crf file in the list of suffixes.
            # So in this case, we strip the e.g. o001 from the
            # suffixes and check which list elements match.
            for image_suffix in all_suffixes:
                if (image_suffix.endswith(poss_suffix)
                        and image_suffix not in suffixes):
                    suffixes.append(image_suffix)
                    untracked_suffixes.remove(image_suffix)

    # If the data contain any suffixes that are not in the list
    # that specifies the order to use, add them to the end of the
    # suffixes list. Their order will be random since they are not in
    # EXPOSURE_PAGE_SUFFIX_ORDER.
    if len(untracked_suffixes) > 0:
        suffixes.extend(untracked_suffixes)

    if return_untracked:
        return suffixes, untracked_suffixes
    else:
        return suffixes


def get_current_flagged_anomalies(rootname, instrument, n_match=1):
    """Return a list of currently flagged anomalies for the given
    ``rootname``

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00001_guider2/``)

    Returns
    -------
    current_anomalies : list of str
        A list of currently flagged anomalies for the given ``rootname``
        (e.g. ``['snowball', 'crosstalk']``)
    """
    table = getattr(di, '{}Anomaly'.format(JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]))
    query = di.session.query(table).filter(table.rootname.startswith(rootname)).order_by(table.flag_date.desc())

    all_records = query.data_frame.groupby('rootname').first()
    current_anomalies = []
    if not all_records.empty:
        for col, val in all_records.sum(axis=0, numeric_only=True).items():
            # ignore rootname, flag_date, etc
            if val == n_match and col in ANOMALIES_PER_INSTRUMENT:
                current_anomalies.append(col)

    return current_anomalies


def get_anomaly_form(request, inst, file_root):
    """Generate form data for context

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file_root : str
        FITS filename of selected image in filesystem. May be a
        file or group root name.

    Returns
    -------
    InstrumentAnomalySubmitForm object
        form object to be sent with context to template
    """
    # Check for group root name
    file_root_info = RootFileInfo.objects.filter(root_name__startswith=file_root)
    file_roots = [rf.root_name for rf in file_root_info]

    # Determine current flagged anomalies
    current_anomalies = get_current_flagged_anomalies(file_root, inst, n_match=len(file_roots))

    # Create a form instance
    form = InstrumentAnomalySubmitForm(request.POST or None, instrument=inst.lower(), initial={'anomaly_choices': current_anomalies})

    # If this is a POST request and the form is filled out, process the form data
    if request.method == 'POST':
        anomaly_choices = dict(request.POST).get('anomaly_choices', [])
        if form.is_valid():
            for file_root in file_roots:
                # for a group form submit, add any individual anomalies
                # not in the original group set
                if len(file_roots) > 1:
                    file_current = get_current_flagged_anomalies(file_root, inst)
                    choices = anomaly_choices.copy()
                    for choice in file_current:
                        if choice not in current_anomalies:
                            choices.append(choice)
                else:
                    choices = anomaly_choices
                form.update_anomaly_table(file_root, 'unknown', choices)
            messages.success(request, "Anomaly submitted successfully")
        else:
            messages.error(request, "Failed to submit anomaly")

    return form


def get_dashboard_components(request):
    """Build and return a Dashboard class.

    Returns
    -------
    dashboard_components : GeneralDashboard
        The dashboard.
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
                        mnemonic_query_result.file_for_download = path_for_download

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
                mnemonic_exploration_result.file_for_download = path_for_download

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


def get_filenames_by_instrument(instrument, proposal, observation_id=None,
                                restriction='all', query_file=None,
                                query_response=None, other_columns=None):
    """Returns a list of filenames that match the given ``instrument``.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    proposal : str
        Proposal number to filter the results
    observation_id : str
        Observation number to filter the results
    restriction : str
        If ``all``, all filenames will be returned.  If ``public``,
        only publicly-available filenames will be returned.  If
        ``proprietary``, only proprietary filenames will be returned.
    query_file : str
        Name of a file containing a list of filenames. If provided, the
        filenames in this file will be used rather than calling mask_query_filenames_by_instrument.
        This can save a significant amount of time when the number of files is large.
    query_response : dict
        Dictionary with "data" key containing a list of filenames. This is assumed to
        essentially be the returned value from a call to mast_query_filenames_by_instrument.
        If this is provided, the call to that function is skipped, which can save a
        significant amount of time.
    other_columns : list
        List of other columns to retrieve from the MAST query

    Returns
    -------
    filenames : list
        A list of files that match the given instrument.
    col_data : dict
        Dictionary of other attributes returned from MAST. Keys are the attribute names
        e.g. 'exptime', and values are lists of the value for each filename. e.g. ['59867.6, 59867.601']
    """
    if not query_file and not query_response:
        result = mast_query_filenames_by_instrument(
            instrument, proposal, observation_id=observation_id,
            other_columns=other_columns)

    elif query_response:
        result = query_response
    elif query_file:
        with open(query_file) as fobj:
            result = fobj.readlines()

    if other_columns is not None:
        col_data = {}
        for element in other_columns:
            col_data[element] = []

    # Determine filenames to return based on restriction parameter
    if restriction == 'all':
        filenames = [item['filename'] for item in result['data']]
        if other_columns is not None:
            for keyword in other_columns:
                col_data[keyword] = [item[keyword] for item in result['data']]
    elif restriction == 'public':
        filenames = [item['filename'] for item in result['data'] if item['isRestricted'] is False]
        if other_columns is not None:
            for keyword in other_columns:
                col_data[keyword] = [item[keyword] for item in result['data'] if item['isRestricted'] is False]
    elif restriction == 'proprietary':
        filenames = [item['filename'] for item in result['data'] if item['isRestricted'] is True]
        if other_columns is not None:
            for keyword in other_columns:
                col_data[keyword] = [item[keyword] for item in result['data'] if item['isRestricted'] is True]
    else:
        raise KeyError('{} is not a valid restriction level.  Use "all", "public", or "proprietary".'.format(restriction))

    if other_columns is not None:
        return (filenames, col_data)

    return filenames


def mast_query_by_rootname(instrument, rootname):
    """Query MAST for all columns given an instrument and rootname. Return the dict of the 'data' column

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    rootname : str
        The Rootname of Interest

    Returns
    -------
    result : dict
        Dictionary of rootname data
    """

    query_filters = []
    if '-seg' in rootname:
        root_split = rootname.split('-')
        file_set_name = root_split[0]
        root_split = rootname.split('_')
        detector = root_split[-1]
    else:
        root_split = rootname.split('_')
        file_set_name = '_'.join(root_split[:-1])
        detector = root_split[-1]

    service = INSTRUMENT_SERVICE_MATCH[instrument]

    query_filters.append({'paramName': 'fileSetName', 'values': [file_set_name]})
    query_filters.append({'paramName': 'detector', 'values': [detector.upper()]})
    params = {'columns': '*',
              'filters': query_filters}
    try:
        response = Mast.service_request_async(service, params)
        result = response[0].json()
    except Exception as e:
        logging.error("Mast.service_request_async- {} - {}".format(file_set_name, e))
        result['data'] = []

    retval = {}
    if result['data'] == []:
        print("WARNING: no data for {}".format(rootname))
    else:
        retval = result['data'][0]
    return retval



def mast_query_filenames_by_instrument(instrument, proposal_id, observation_id=None, other_columns=None):
    """Query MAST for filenames for the given instrument. Return the json
    response from MAST.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    proposal_id : str
        Proposal ID number to use to filter the results
    observation_id : str
        Observation ID number to use to filter the results. If None, all files for the ``proposal_id`` are
        retrieved
    other_columns : list
        List of other columns to return from the MAST query

    Returns
    -------
    result : dict
        Dictionary of file information
    """
    # Be sure the instrument name is properly capitalized
    instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]

    if other_columns is None:
        columns = "filename, isRestricted"
    else:
        columns = "filename, isRestricted, " + ", ".join(other_columns)

    service = INSTRUMENT_SERVICE_MATCH[instrument]
    filters = [{'paramName': 'program', "values": [proposal_id]}]
    if observation_id is not None:
        filters.append({'paramName': 'observtn', 'values': [observation_id]})
    params = {"columns": columns, "filters": filters}
    response = Mast.service_request_async(service, params)
    result = response[0].json()
    return result


def get_filesystem_filenames(proposal=None, rootname=None,
                             file_types=None, full_path=False,
                             sort_names=True):
    """Return a list of filenames on the filesystem.

    One of proposal or rootname must be specified. If both are
    specified, only proposal is used.

    Parameters
    ----------
    proposal : str, optional
        The one- to five-digit proposal number (e.g. ``88600``).
    rootname : str, optional
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).
    file_types : list of str, optional
        If provided, only matching file extension types will be
        returned (e.g. ['fits', 'jpg']).
    full_path : bool, optional
        If set, the full path to the file will be returned instead
        of the basename.
    sort_names : bool, optional
        If set, the returned files are sorted.

    Returns
    -------
    filenames : list
        A list of filenames associated with the given ``rootname``.
    """
    if proposal is not None:
        proposal_string = '{:05d}'.format(int(proposal))
        filenames = glob.glob(
            os.path.join(FILESYSTEM_DIR, 'public',
                         'jw{}'.format(proposal_string), '*/*'))
        filenames.extend(glob.glob(
            os.path.join(FILESYSTEM_DIR, 'proprietary',
                         'jw{}'.format(proposal_string), '*/*')))
    elif rootname is not None:
        proposal_dir = rootname[0:7]
        observation_dir = rootname.split('_')[0]
        filenames = glob.glob(
            os.path.join(FILESYSTEM_DIR, 'public', proposal_dir,
                         observation_dir, '{}*'.format(rootname)))
        filenames.extend(glob.glob(
            os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir,
                         observation_dir, '{}*'.format(rootname))))
    else:
        logging.warning("Must provide either proposal or rootname; "
                        "no files returned.")
        filenames = []

    # check suffix and file type
    good_filenames = []
    for filename in filenames:
        split_file = os.path.splitext(filename)

        # certain suffixes are always ignored
        test_suffix = split_file[0].split('_')[-1]
        if test_suffix not in IGNORED_SUFFIXES:

            # check against additional file type requirement
            test_type = split_file[-1].lstrip('.')
            if file_types is None or test_type in file_types:
                if full_path:
                    good_filenames.append(filename)
                else:
                    good_filenames.append(os.path.basename(filename))

    if sort_names:
        good_filenames.sort()
    return good_filenames


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
    return get_filesystem_filenames(proposal=proposal)


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
    return get_filesystem_filenames(rootname=rootname)


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

        # Determine the extension name and type
        if ext == 0:
            header_info[ext]['EXTNAME'] = 'PRIMARY'
            header_info[ext]['XTENSION'] = 'PRIMARY'
        else:
            header_info[ext]['EXTNAME'] = header['EXTNAME']
            header_info[ext]['XTENSION'] = header['XTENSION']

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


def get_image_info(file_root):
    """Build and return a dictionary containing information for a given
    ``file_root``.

    Parameters
    ----------
    file_root : str
        The rootname of the file of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

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
    image_info['total_ints'] = {}
    image_info['detectors'] = set()

    # Find all the matching files
    proposal_dir = file_root[:7]
    observation_dir = file_root[:13]
    filenames = glob.glob(
        os.path.join(FILESYSTEM_DIR, 'public', proposal_dir,
                     observation_dir, '{}*.fits'.format(file_root)))
    filenames.extend(glob.glob(
        os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir,
                     observation_dir, '{}*.fits'.format(file_root))))

    # Certain suffixes are always ignored
    filenames = [filename for filename in filenames
                 if os.path.splitext(filename)[0].split('_')[-1]
                 not in IGNORED_SUFFIXES]
    image_info['all_files'] = filenames

    # Determine the jpg directory
    prev_img_filesys = configs['preview_image_filesystem']
    jpg_dir = os.path.join(prev_img_filesys, proposal_dir)

    for filename in image_info['all_files']:

        parsed_fn = filename_parser(filename)

        # Get suffix information
        suffix = parsed_fn['suffix']

        # For crf or crfints suffixes, we need to also include the association value
        # in the suffix, so that preview images can be found later.
        if suffix in SUFFIXES_TO_ADD_ASSOCIATION:
            assn = filename.split('_')[-2]
            suffix = f'{assn}_{suffix}'

        image_info['suffixes'].append(suffix)

        # Determine JPEG file location
        jpg_filename = os.path.basename(os.path.splitext(filename)[0] + '_integ0.jpg')
        jpg_filepath = os.path.join(jpg_dir, jpg_filename)

        # Record how many integrations have been saved as preview images per filetype
        jpgs = glob.glob(os.path.join(prev_img_filesys, proposal_dir, '{}*_{}_integ*.jpg'.format(file_root, suffix)))
        image_info['available_ints'][suffix] = sorted(set([int(jpg.split('_')[-1].replace('.jpg', '').replace('integ', '')) for jpg in jpgs]))
        image_info['num_ints'][suffix] = len(image_info['available_ints'][suffix])
        image_info['all_jpegs'].append(jpg_filepath)

        # Record how many integrations exist per filetype.
        if suffix not in SUFFIXES_WITH_AVERAGED_INTS:
            # time series segments need special handling
            header = fits.getheader(filename)
            nint = header['NINTS']
            if 'time_series' in parsed_fn['filename_type']:
                intstart = header.get('INTSTART', 1)
                intend = header.get('INTEND', nint)
                image_info['total_ints'][suffix] = intend - intstart + 1
            else:
                image_info['total_ints'][suffix] = nint
        else:
            image_info['total_ints'][suffix] = 1

        # Record the detector used
        image_info['detectors'].add(parsed_fn.get('detector', 'Unknown'))

    return image_info


def get_explorer_extension_names(fits_file, filetype):
    """ Return a list of Extensions that can be explored interactively

    Parameters
    ----------
    filename : str
        The name of the file of interest, without the extension
        (e.g. ``'jw86600008001_02101_00007_guider2_uncal'``).
    filetype : str
        The type of the file of interest, (e.g. ``'uncal'``)

    Returns
    -------
    extensions : list
        List of Extensions found in header and allowed to be Explored (extension type "IMAGE")
    """

    header_info = get_header_info(fits_file, filetype)

    extensions = [header_info[extension]['EXTNAME'] for extension in header_info if header_info[extension]['XTENSION'] == 'IMAGE']
    return extensions


def get_instrument_proposals(instrument):
    """Return a list of proposals for the given instrument

    Parameters
    ----------
    instrument : str
        Name of the JWST instrument, with first letter capitalized
        (e.g. ``Fgs``)

    Returns
    -------
    inst_proposals : list
        List of proposals for the given instrument
    """
    tap_service = vo.dal.TAPService("https://vao.stsci.edu/caomtap/tapservice.aspx")
    tap_results = tap_service.search(f"select distinct proposal_id from dbo.ObsPointing where obs_collection='JWST' and calib_level>0 and instrument_name like '{instrument.lower()}%'")
    prop_table = tap_results.to_table()
    proposals = prop_table['proposal_id'].data
    inst_proposals = sorted(proposals.compressed(), reverse=True)
    return inst_proposals


def get_instrument_looks(instrument, sort_as=None, proposal=None,
                         look=None, exp_type=None, cat_type=None,
                         additional_keys=None):
    """Return a table of looks information for the given instrument.

    Parameters
    ----------
    instrument : str
        Name of the JWST instrument.
    sort_as : {'ascending', 'descending', 'recent'}
        Sorting method for output table. Ascending and descending
        options refer to root file name; recent sorts by observation
        start.
    proposal : str, optional
        Proposal to match.  Used as a 'starts with' filter.
    look : {'new', 'viewed'}, optional
        If set to None, all viewed values are returned. If set to
        'viewed', only viewed data is returned. If set to 'new', only
        new data is returned.
    exp_type : str, optional
        Set to filter by exposure type.
    cat_type : str, optional
        Set to filter by proposal category.
    additional_keys : list of str, optional
        Additional model attribute names for information to return.

    Returns
    -------
    keys : list of str
        Report values returned for the given instrument.
    looks : list of dict
        List of looks information by root file for the given instrument.
    """
    # standardize input
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]

    # required keys
    keys = ['root_name']

    # optional keys by instrument
    keys += REPORT_KEYS_PER_INSTRUMENT[inst.lower()]

    # add any additional keys
    key_set = set(keys)
    if additional_keys is not None:
        for key in additional_keys:
            if key not in key_set:
                keys.append(key)

    # get filtered file info
    root_file_info = filter_root_files(
        instrument=instrument, sort_as=sort_as, look=look,
        exp_type=exp_type, cat_type=cat_type, proposal=proposal)

    looks = []
    for root_file in root_file_info:
        result = dict()
        for key in keys:
            try:
                # try the root file table
                value = root_file[key]
            except KeyError:
                value = ''

            # make sure value can be serialized
            if type(value) not in [str, float, int, bool]:
                value = str(value)

            result[key] = value
        looks.append(result)

    return keys, looks


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
    preview_images = [item for item in preview_images if os.path.splitext(item)[0].split('_')[-1] not in IGNORED_SUFFIXES]

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
    preview_images = [item for item in preview_images if os.path.splitext(item)[0].split('_')[-1] not in IGNORED_SUFFIXES]

    return preview_images


def get_proposals_by_category(instrument):
    """Return a dictionary of program numbers based on category type
    Parameters
    ----------
    instrument : str
        Name of the JWST instrument, with first letter capitalized
        (e.g. ``Fgs``)
    Returns
    -------
    category_sorted_dict : dict
        Dictionary with category as the key and a list of program id's as the value
    """

    service = "Mast.Jwst.Filtered.{}".format(instrument)
    params = {"columns": "program, category",
              "filters": []}
    response = Mast.service_request_async(service, params)
    results = response[0].json()['data']

    # Get all unique dictionaries
    unique_results = list(map(dict, set(tuple(sorted(sub.items())) for sub in results)))

    # Make a dictionary of {program: category} to pull from
    proposals_by_category = {d['program']:d['category'] for d in unique_results}

    return proposals_by_category


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
    proposals, thumbnail_paths, num_files, observations = [], [], [], []
    for filepath in filepaths:
        proposal = filepath.split('/')[-1][2:7]
        if proposal not in proposals:
            thumbnail_paths.append(os.path.join('jw{}'.format(proposal), 'jw{}.thumb'.format(proposal)))
            files_for_proposal = [item for item in filepaths if 'jw{}'.format(proposal) in item]

            obsnums = []
            for fname in files_for_proposal:
                try:
                    obs = filename_parser(fname)['observation']
                    obsnums.append(obs)
                except KeyError:
                    pass
            obsnums = sorted(obsnums)
            observations.extend(obsnums)
            num_files.append(len(files_for_proposal))
            proposals.append(proposal)

    # Put the various information into a dictionary of results
    proposal_info = {}
    proposal_info['num_proposals'] = len(proposals)
    proposal_info['proposals'] = proposals
    proposal_info['thumbnail_paths'] = thumbnail_paths
    proposal_info['num_files'] = num_files
    proposal_info['observation_nums'] = observations

    return proposal_info


def get_rootnames_for_proposal(proposal):
    """Return a list of rootnames for the given proposal (all instruments)

    Parameters
    ----------
    proposal : int or str
        Proposal ID number

    Returns
    -------
    rootnames : list
        List of rootnames for the given instrument and proposal number
    """
    tap_service = vo.dal.TAPService("https://vao.stsci.edu/caomtap/tapservice.aspx")
    tap_results = tap_service.search(f"select observationID from dbo.CaomObservation where collection='JWST' and maxLevel=2 and prpID='{int(proposal)}'")
    prop_table = tap_results.to_table()
    rootnames = prop_table['observationID'].data
    return rootnames.compressed()


def get_thumbnails_all_instruments(parameters):
    """Return a list of thumbnails available in the filesystem for all
    instruments given requested MAST parameters and queried anomalies.

    Parameters
    ----------
    parameters: dict
        A dictionary containing keys of QUERY_CONFIG_KEYS, some of which are dictionaries:


    Returns
    -------
    thumbnails : list
        A list of thumbnails available in the filesystem for the
        given instrument.
    """

    anomalies = parameters[QUERY_CONFIG_KEYS.ANOMALIES]

    thumbnails_subset = []

    for inst in parameters[QUERY_CONFIG_KEYS.INSTRUMENTS]:
        # Make sure instruments are of the proper format (e.g. "Nircam")
        instrument = inst[0].upper() + inst[1:].lower()

        # Query MAST for all rootnames for the instrument
        service = "Mast.Jwst.Filtered.{}".format(instrument)

        if ((parameters[QUERY_CONFIG_KEYS.APERTURES][inst.lower()] == [])
                and (parameters[QUERY_CONFIG_KEYS.DETECTORS][inst.lower()] == [])
                and (parameters[QUERY_CONFIG_KEYS.FILTERS][inst.lower()] == [])
                and (parameters[QUERY_CONFIG_KEYS.EXP_TYPES][inst.lower()] == [])
                and (parameters[QUERY_CONFIG_KEYS.READ_PATTS][inst.lower()] == [])):  # noqa: W503
            params = {"columns": "*", "filters": []}
        else:
            query_filters = []
            if (parameters[QUERY_CONFIG_KEYS.APERTURES][inst.lower()] != []):
                if instrument != "Nircam":
                    query_filters.append({"paramName": "pps_aper", "values": parameters[QUERY_CONFIG_KEYS.APERTURES][inst.lower()]})
                if instrument == "Nircam":
                    query_filters.append({"paramName": "apername", "values": parameters[QUERY_CONFIG_KEYS.APERTURES][inst.lower()]})
            if (parameters[QUERY_CONFIG_KEYS.DETECTORS][inst.lower()] != []):
                query_filters.append({"paramName": "detector", "values": parameters[QUERY_CONFIG_KEYS.DETECTORS][inst.lower()]})
            if (parameters[QUERY_CONFIG_KEYS.FILTERS][inst.lower()] != []):
                query_filters.append({"paramName": "filter", "values": parameters[QUERY_CONFIG_KEYS.FILTERS][inst.lower()]})
            if (parameters[QUERY_CONFIG_KEYS.EXP_TYPES][inst.lower()] != []):
                query_filters.append({"paramName": "exp_type", "values": parameters[QUERY_CONFIG_KEYS.EXP_TYPES][inst.lower()]})
            if (parameters[QUERY_CONFIG_KEYS.READ_PATTS][inst.lower()] != []):
                query_filters.append({"paramName": "readpatt", "values": parameters[QUERY_CONFIG_KEYS.READ_PATTS][inst.lower()]})
            params = {"columns": "*",
                      "filters": query_filters}

        response = Mast.service_request_async(service, params)
        results = response[0].json()['data']

        inst_filenames = [result['filename'].split('.')[0] for result in results]
        inst_filenames = [filename for filename in inst_filenames if filename.split('_')[-1] not in IGNORED_SUFFIXES]

        # Get list of all thumbnails
        thumb_inventory = os.path.join(f"{THUMBNAIL_FILESYSTEM}", f"{THUMBNAIL_LISTFILE}_{inst.lower()}.txt")
        thumbnail_inst_list = retrieve_filelist(thumb_inventory)

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
    # Get list of all thumbnails
    thumb_inventory = f'{THUMBNAIL_LISTFILE}_{inst.lower()}.txt'
    all_thumbnails = retrieve_filelist(os.path.join(THUMBNAIL_FILESYSTEM, thumb_inventory))

    thumbnails = []
    all_proposals = get_instrument_proposals(inst)
    for proposal in all_proposals:
        results = mast_query_filenames_by_instrument(inst, proposal)

        # Parse the results to get the rootnames
        filenames = [result['filename'].split('.')[0] for result in results]

        if len(filenames) > 0:
            # Get subset of preview images that match the filenames
            prop_thumbnails = [os.path.basename(item) for item in all_thumbnails if
                               os.path.basename(item).split('_integ')[0] in filenames]

            thumbnails.extend(prop_thumbnails)

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


def get_thumbnail_by_rootname(rootname):
    """Return the most appropriate existing thumbnail basename available in the filesystem for the given ``rootname``.
    We generate thumbnails only for 'rate' and 'dark' files.
    Check if these files exist in the thumbnail filesystem.
    In the case where neither rate nor dark thumbnails are present, revert to 'none'

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    thumbnail_basename : str
        A thumbnail_basename available in the filesystem for the given ``rootname``.
    """

    proposal = rootname.split('_')[0].split('jw')[-1][0:5]
    thumbnails = sorted(glob.glob(os.path.join(
        THUMBNAIL_FILESYSTEM,
        'jw{}'.format(proposal),
        '{}*'.format(rootname))))

    thumbnails = [os.path.basename(thumbnail) for thumbnail in thumbnails]
    thumbnail_basename = 'none'

    if len(thumbnails) > 0:
        preferred = [thumb for thumb in thumbnails if 'rate' in thumb]
        if len(preferred) == 0:
            preferred = [thumb for thumb in thumbnails if 'dark' in thumb]
        if len(preferred) > 0:
            thumbnail_basename = os.path.basename(preferred[0])

    return thumbnail_basename


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


def proposal_rootnames_by_instrument(proposal):
    """Retrieve the rootnames for a given proposal for all instruments and return
    as a dictionary with instrument names as keys. Instruments not used in the proposal
    will not be present in the dictionary.

    proposal : int or str
        Proposal ID number

    Returns
    -------
    rootnames : dict
        Dictionary of rootnames with instrument names as keys
    """
    rootnames = {}
    for instrument in JWST_INSTRUMENT_NAMES:
        names = get_rootnames_for_instrument_proposal(instrument, proposal)
        if len(names) > 0:
            rootnames[instrument] = names
    return rootnames


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
    not_available = "not available via this interface" in html.text
    not_available |= "temporarily unable" in html.text

    program_meta = {}
    program_meta['prop_id'] = prop_id
    if not not_available:
        lines = html.findAll('p')
        lines = [str(line) for line in lines]

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
    else:
        program_meta['phase_two'] = 'N/A'
        program_meta['prop_type'] = 'N/A'
        program_meta['title'] = 'Proposal not available or does not exist'
        program_meta['pi'] = 'N/A'
        program_meta['pc'] = 'N/A'
        program_meta['cs'] = 'N/A'
        program_meta['ps'] = 'N/A'

    return program_meta


def thumbnails_ajax(inst, proposal, obs_num=None):
    """Generate a page that provides data necessary to render the
    ``thumbnails`` template.

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    proposal : str (optional)
        Number of APT proposal to filter
    obs_num : str (optional)
        Observation number

    Returns
    -------
    data_dict : dict
        Dictionary of data needed for the ``thumbnails`` template
    """
    # generate the list of all obs of the proposal here, so that the list can be
    # properly packaged up and sent to the js scripts. but to do this, we need to call
    # get_rootnames_for_instrument_proposal, which is largely repeating the work done by
    # get_filenames_by_instrument above. can we use just get_rootnames? we would have to
    # filter results by obs_num after the call and after obs_list is created.
    # But we need the filename list below...hmmm...so maybe we need to do both
    all_rootnames = get_rootnames_for_instrument_proposal(inst, proposal)
    all_obs = []
    for root in all_rootnames:
        # Wrap in try/except because level 3 rootnames won't have an observation
        # number returned by the filename_parser. That's fine, we're not interested
        # in those files anyway.
        try:
            all_obs.append(filename_parser(root)['observation'])
        except KeyError:
            pass
    obs_list = sorted(list(set(all_obs)))

    # Get the available files for the instrument
    filenames, columns = get_filenames_by_instrument(inst, proposal, observation_id=obs_num, other_columns=['expstart', 'exp_type'])

    # Get set of unique rootnames
    rootnames = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filenames])

    # Initialize dictionary that will contain all needed data
    data_dict = {'inst': inst,
                 'file_data': dict()}
    exp_types = set()
    exp_groups = set()

    # Gather data for each rootname, and construct a list of all observations
    # in the proposal
    for rootname in rootnames:

        # Parse filename
        try:
            filename_dict = filename_parser(rootname)

            # Weed out file types that are not supported by generate_preview_images
            if 'stage_3' in filename_dict['filename_type']:
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
                             'visit_group': rootname[14:16],
                             'group_root': rootname[:26]}

        # Get list of available filenames and exposure start times. All files with a given
        # rootname will have the same exposure start time, so just keep the first.
        available_files = []
        exp_start = None
        exp_type = None
        for i, item in enumerate(filenames):
            if rootname in item:
                available_files.append(item)
                if exp_start is None:
                    exp_start = columns['expstart'][i]
                    exp_type = columns['exp_type'][i]
        exp_types.add(exp_type)

        # Viewed is stored by rootname in the Model db.  Save it with the data_dict
        # THUMBNAIL_FILTER_LOOK is boolean accessed according to a viewed flag
        try:
            root_file_info = RootFileInfo.objects.get(root_name=rootname)
            viewed = THUMBNAIL_FILTER_LOOK[root_file_info.viewed]
        except RootFileInfo.DoesNotExist:
            viewed = THUMBNAIL_FILTER_LOOK[0]

        # Add to list of all exposure groups
        exp_groups.add(filename_dict['group_root'])

        # Add data to dictionary
        data_dict['file_data'][rootname] = {}
        data_dict['file_data'][rootname]['filename_dict'] = filename_dict
        data_dict['file_data'][rootname]['available_files'] = available_files
        data_dict['file_data'][rootname]['viewed'] = viewed
        data_dict['file_data'][rootname]['exp_type'] = exp_type
        data_dict['file_data'][rootname]['thumbnail'] = get_thumbnail_by_rootname(rootname)

        try:
            data_dict['file_data'][rootname]['expstart'] = exp_start
            data_dict['file_data'][rootname]['expstart_iso'] = Time(exp_start, format='mjd').iso.split('.')[0]
        except (ValueError, TypeError) as e:
            logging.warning("Unable to populate exp_start info for {}".format(rootname))
            logging.warning(e)
        except KeyError:
            print("KeyError with get_expstart for {}".format(rootname))

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
        dropdown_menus = {'detector': sorted(detectors),
                          'look': THUMBNAIL_FILTER_LOOK,
                          'exp_type': sorted(exp_types)}
    else:
        dropdown_menus = {'detector': sorted(detectors),
                          'proposal': sorted(proposals),
                          'look': THUMBNAIL_FILTER_LOOK,
                          'exp_type': sorted(exp_types)}

    data_dict['tools'] = MONITORS
    data_dict['dropdown_menus'] = dropdown_menus
    data_dict['prop'] = proposal

    # Order dictionary by descending expstart time.
    sorted_file_data = OrderedDict(sorted(data_dict['file_data'].items(),
                                   key=lambda x: getitem(x[1], 'expstart'), reverse=True))

    data_dict['file_data'] = sorted_file_data

    # Add list of observation numbers and group roots
    data_dict['obs_list'] = obs_list
    data_dict['exp_groups'] = sorted(exp_groups)

    return data_dict


def thumbnails_date_range_ajax(inst, observations, inclusive_start_time_mjd, exclusive_stop_time_mjd):
    """Generate a page that provides data necessary to render thumbnails for
    ``archive_date_range`` template.

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    observations: list
        observation models to use to get filenames
    inclusive_start_time_mjd : float
        Start time in mjd format for date range
    exclusive_stop_time_mjd : float
        Stop time in mjd format for date range

    Returns
    -------
    data_dict : dict
        Dictionary of data needed for the ``thumbnails`` template
    """

    data_dict = {'inst': inst,
                 'file_data': dict()}
    exp_types = set()
    exp_groups = set()

    # Get the available files for the instrument
    for observation in observations:
        obs_num = observation.obsnum
        proposal = observation.proposal.prop_id
        filenames, columns = get_filenames_by_instrument(inst, proposal, observation_id=obs_num, other_columns=['expstart', 'exp_type'])
        # Get set of unique rootnames
        rootnames = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filenames])
        # Gather data for each rootname, and construct a list of all observations in the proposal
        for rootname in rootnames:
            # Parse filename
            try:
                filename_dict = filename_parser(rootname)

                # Weed out file types that are not supported by generate_preview_images
                if 'stage_3' in filename_dict['filename_type']:
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
                                 'visit_group': rootname[14:16],
                                 'group_root': rootname[:26]}

            # Get list of available filenames and exposure start times. All files with a given
            # rootname will have the same exposure start time, so just keep the first.
            available_files = []
            exp_start = None
            exp_type = None
            for i, item in enumerate(filenames):
                if rootname in item:
                    available_files.append(item)
                    if exp_start is None:
                        exp_start = columns['expstart'][i]
                        exp_type = columns['exp_type'][i]

            if exp_start >= inclusive_start_time_mjd and exp_start < exclusive_stop_time_mjd:
                exp_types.add(exp_type)
                # Viewed is stored by rootname in the Model db.  Save it with the data_dict
                # THUMBNAIL_FILTER_LOOK is boolean accessed according to a viewed flag
                try:
                    root_file_info = RootFileInfo.objects.get(root_name=rootname)
                    viewed = THUMBNAIL_FILTER_LOOK[root_file_info.viewed]
                except RootFileInfo.DoesNotExist:
                    viewed = THUMBNAIL_FILTER_LOOK[0]

                # Add to list of all exposure groups
                exp_groups.add(filename_dict['group_root'])

                # Add data to dictionary
                data_dict['file_data'][rootname] = {}
                data_dict['file_data'][rootname]['filename_dict'] = filename_dict
                data_dict['file_data'][rootname]['available_files'] = available_files
                data_dict['file_data'][rootname]["viewed"] = viewed
                data_dict['file_data'][rootname]["exp_type"] = exp_type
                data_dict['file_data'][rootname]['thumbnail'] = get_thumbnail_by_rootname(rootname)

                try:
                    data_dict['file_data'][rootname]['expstart'] = exp_start
                    data_dict['file_data'][rootname]['expstart_iso'] = Time(exp_start, format='mjd').iso.split('.')[0]
                except (ValueError, TypeError) as e:
                    logging.warning("Unable to populate exp_start info for {}".format(rootname))
                    logging.warning(e)
                except KeyError:
                    print("KeyError with get_expstart for {}".format(rootname))

    # Extract information for sorting with dropdown menus
    # (Don't include the proposal as a sorting parameter if the proposal has already been specified)
    detectors, proposals = [], []
    for rootname in list(data_dict['file_data'].keys()):
        proposals.append(data_dict['file_data'][rootname]['filename_dict']['program_id'])
        try:  # Some rootnames cannot parse out detectors
            detectors.append(data_dict['file_data'][rootname]['filename_dict']['detector'])
        except KeyError:
            pass

    dropdown_menus = {'detector': sorted(detectors),
                      'proposal': sorted(proposals),
                      'look': THUMBNAIL_FILTER_LOOK,
                      'exp_type': sorted(set(exp_types))}

    data_dict['tools'] = MONITORS
    data_dict['dropdown_menus'] = dropdown_menus

    # Order dictionary by descending expstart time.
    sorted_file_data = OrderedDict(sorted(data_dict['file_data'].items(),
                                   key=lambda x: getitem(x[1], 'expstart'), reverse=True))

    data_dict['file_data'] = sorted_file_data
    data_dict['exp_groups'] = sorted(exp_groups)

    return data_dict


def thumbnails_query_ajax(rootnames, expstarts=None):
    """Generate a page that provides data necessary to render the
    ``thumbnails`` template.

    Parameters
    ----------
    rootnames : list of strings
        Rootname of APT proposal to filter
    expstarts : list
        Exposure start times from MAST (mjd)

    Returns
    -------
    data_dict : dict
        Dictionary of data needed for the ``thumbnails`` template
    """
    # Initialize dictionary that will contain all needed data
    data_dict = {'inst': 'all',
                 'file_data': dict()}
    exp_groups = set()

    # Gather data for each rootname
    for rootname in rootnames:
        # fit expected format for get_filenames_by_rootname()
        split_name = rootname.split("_")
        try:
            rootname = split_name[0] + '_' + split_name[1] + '_' + split_name[2] + '_' + split_name[3]
        except IndexError:
            continue

        # Parse filename
        try:
            filename_dict = filename_parser(rootname)
        except ValueError:
            continue

        # Add to list of all exposure groups
        exp_groups.add(filename_dict['group_root'])

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
        data_dict['file_data'][rootname]['suffixes'] = []
        data_dict['file_data'][rootname]['prop'] = rootname[2:7]
        for filename in available_files:
            try:
                suffix = filename_parser(filename)['suffix']
                data_dict['file_data'][rootname]['suffixes'].append(suffix)
            except ValueError:
                continue
        data_dict['file_data'][rootname]['thumbnail'] = get_thumbnail_by_rootname(rootname)

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
    data_dict['exp_groups'] = sorted(exp_groups)

    return data_dict
