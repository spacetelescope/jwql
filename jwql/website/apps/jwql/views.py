"""Defines the views for the ``jwql`` web app.

In Django, "a view function, or view for short, is simply a Python
function that takes a Web request and returns a Web response" (from
Django documentation). This module defines all of the views that are
used to generate the various webpages used for the JWQL application.
For example, these views can list the tools available to users, query
the ``jwql`` database, and display images and headers.

Authors
-------

    - Lauren Chambers
    - Johannes Sahlmann
    - Teagan King
    - Mees Fix
    - Bryan Hilbert
    - Maria Pena-Guerrero
    - Bradley Sappington
    - Melanie Clarke


Use
---

    This module is called in ``urls.py`` as such:
    ::

        from django.urls import path
        from . import views
        urlpatterns = [path('web/path/to/view/', views.view_name,
        name='view_name')]

References
----------
    For more information please see:
        ``https://docs.djangoproject.com/en/2.0/topics/http/views/``

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql`` directory.
"""

import csv
import datetime
import glob
import json
import logging
import operator
import os
from pathlib import Path
import socket

from astropy.time import Time
from bokeh.embed import components
from bokeh.layouts import layout
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
import numpy as np
from sqlalchemy import inspect

from jwql.utils import monitor_utils
from jwql.utils.constants import JWQLDB_EXCLUDED, JWST_INSTRUMENT_NAMES_MIXEDCASE, QUERY_CONFIG_TEMPLATE, SUFFIXES_OF_ECSV_FILES, URL_DICT, QueryConfigKeys
from jwql.utils.interactive_preview_image import InteractivePreviewImg
from jwql.utils.logging_functions import configure_logging
from jwql.utils.utils import filename_parser, get_base_url, get_config, get_rootnames_for_instrument_proposal, query_unformat

from .data_containers import (
    build_table,
    get_acknowledgements,
    get_additional_exposure_info,
    get_anomaly_form,
    get_available_suffixes,
    get_comment_form,
    get_detectors_by_rootname,
    get_exp_comment_form,
    get_dashboard_components,
    get_edb_components,
    get_explorer_extension_names,
    get_group_anomalies,
    get_header_info,
    get_header_info_ecsv,
    get_image_info,
    get_instrument_looks,
    get_rootnames_from_query,
    import_all_models,
    random_404_page,
    text_scrape,
    thumbnails_ajax,
    thumbnails_query_ajax,
)
from .forms import FileSearchForm, JwqlQueryForm

if not os.environ.get("READTHEDOCS"):
    from .models import RootFileInfo
from astropy.io import fits


def jwql_query(request):
    """The anomaly query form page"""

    form = JwqlQueryForm(request.POST or None)
    form.fields['sort_type'].initial = request.session.get('image_sort', 'Recent')

    if request.method == 'POST':
        if form.is_valid():
            query_configs = {}
            for instrument in ['miri', 'nirspec', 'niriss', 'nircam', 'fgs']:
                query_configs[instrument] = {}
                query_configs[instrument]['filters'] = [query_unformat(i) for i in form.cleaned_data['{}_filt'.format(instrument)]]
                query_configs[instrument]['apertures'] = [query_unformat(i) for i in form.cleaned_data['{}_aper'.format(instrument)]]
                query_configs[instrument]['detectors'] = [query_unformat(i) for i in form.cleaned_data['{}_detector'.format(instrument)]]
                query_configs[instrument]['exptypes'] = [query_unformat(i) for i in form.cleaned_data['{}_exptype'.format(instrument)]]
                query_configs[instrument]['readpatts'] = [query_unformat(i) for i in form.cleaned_data['{}_readpatt'.format(instrument)]]
                query_configs[instrument]['gratings'] = [query_unformat(i) for i in form.cleaned_data['{}_grating'.format(instrument)]]
                query_configs[instrument]['subarrays'] = [query_unformat(i) for i in form.cleaned_data['{}_subarray'.format(instrument)]]
                query_configs[instrument]['pupils'] = [query_unformat(i) for i in form.cleaned_data['{}_pupil'.format(instrument)]]
                query_configs[instrument]['anomalies'] = [query_unformat(i) for i in form.cleaned_data['{}_anomalies'.format(instrument)]]

            all_filters, all_apers, all_detectors, all_exptypes = {}, {}, {}, {}
            all_readpatts, all_gratings, all_subarrays, all_pupils, all_anomalies = {}, {}, {}, {}, {}
            for instrument in query_configs:
                all_filters[instrument] = query_configs[instrument]['filters']
                all_apers[instrument] = query_configs[instrument]['apertures']
                all_detectors[instrument] = query_configs[instrument]['detectors']
                all_exptypes[instrument] = query_configs[instrument]['exptypes']
                all_readpatts[instrument] = query_configs[instrument]['readpatts']
                all_gratings[instrument] = query_configs[instrument]['gratings']
                all_subarrays[instrument] = query_configs[instrument]['subarrays']
                all_pupils[instrument] = query_configs[instrument]['pupils']
                all_anomalies[instrument] = query_configs[instrument]['anomalies']

            parameters = QUERY_CONFIG_TEMPLATE.copy()
            parameters[QueryConfigKeys.INSTRUMENTS] = form.cleaned_data['instrument']
            parameters[QueryConfigKeys.LOOK_STATUS] = form.cleaned_data['look_status']
            parameters[QueryConfigKeys.DATE_RANGE] = form.cleaned_data['date_range']
            parameters[QueryConfigKeys.PROPOSAL_CATEGORY] = form.cleaned_data['proposal_category']
            parameters[QueryConfigKeys.SORT_TYPE] = form.cleaned_data['sort_type']
            parameters[QueryConfigKeys.NUM_PER_PAGE] = form.cleaned_data['num_per_page']
            parameters[QueryConfigKeys.ANOMALIES] = all_anomalies
            parameters[QueryConfigKeys.APERTURES] = all_apers
            parameters[QueryConfigKeys.FILTERS] = all_filters
            parameters[QueryConfigKeys.DETECTORS] = all_detectors
            parameters[QueryConfigKeys.EXP_TYPES] = all_exptypes
            parameters[QueryConfigKeys.READ_PATTS] = all_readpatts
            parameters[QueryConfigKeys.GRATINGS] = all_gratings
            parameters[QueryConfigKeys.SUBARRAYS] = all_subarrays
            parameters[QueryConfigKeys.PUPILS] = all_pupils

            # save the query config settings to a session
            request.session['query_config'] = parameters
            # Check if the download button value exists in the POST message (meaning Download was pressed)
            download_button_value = request.POST.get('download_jwstqueryform', None)
            if(download_button_value):
                return redirect('/query_download')
            else:
                # submit was pressed go to the query_submit page
                return redirect('/query_submit')

    context = {'form': form,
               'inst': ''}
    template = 'jwql_query.html'

    return render(request, template, context)


def about(request):
    """Generate the ``about`` page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = 'about.html'
    acknowledgements = get_acknowledgements()
    context = {'acknowledgements': acknowledgements,
               'inst': ''}

    return render(request, template, context)


def api_landing(request):
    """Generate the ``api`` page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = 'api_landing.html'
    context = {'inst': ''}

    return render(request, template, context)


def save_page_navigation_data_ajax(request):
    """
    Takes a bracketless string of rootnames and expstarts, and saves it as a session dictionary

    Parameters
    ----------
    request: HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # navigation_dict will be a single string e.g. "obs1:stage1:rootname1=expstart2,obs2:stage2:rootname2=expstart2"
    if request.method == 'POST':
        navigate_dict = request.POST.get('navigate_dict')
        navigate_dict_type = request.POST.get('navigate_dict_type')
        rootname_expstarts = dict()
        if navigate_dict_type == 'nested':
            # navigation_data will created be in the form of {obs:{stage:{rootname:expstart}}}
            for item in navigate_dict.split(','):
                obs, stage, roottime = item.split(':')
                rootname, expstart = roottime.split('=')
                if obs not in rootname_expstarts:
                    rootname_expstarts[obs] = {}
                if stage not in rootname_expstarts[obs]:
                    rootname_expstarts[obs][stage] = {}
                rootname_expstarts[obs][stage][rootname] = float(expstart)
        else:
            # navigation_data will created be in the form of {rootname:expstart}}}
            for item in navigate_dict.split(','):
                obs, stage, roottime = item.split(':')
                rootname, expstart = roottime.split('=')
                rootname_expstarts[rootname] = float(expstart)

        request.session['navigation_data'] = rootname_expstarts
        logging.debug(f'In save_page_navigation_data_ajax, navigation_data saved as: {navigation_data}')

    context = {'item': request.session['navigation_data']}
    return JsonResponse(context, json_dumps_params={'indent': 2})


def archived_proposals(request, inst):
    """Generate the page listing all archived proposals in the database

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'archive.html'
    context = {'inst': inst,
               'base_url': get_base_url()}

    return render(request, template, context)


def archived_proposals_ajax(request, inst):
    """Generate the page listing all archived proposals in the database

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """
    # Read in the json file created by data_containers.create_archived_proposals_context
    # and use as the context
    output_dir = get_config()['outputs']
    context_file = os.path.join(output_dir, 'archive_page', f'{inst}_archive_context.json')

    with open(context_file, 'r') as obj:
        context = json.load(obj)

    return JsonResponse(context, json_dumps_params={'indent': 2})


def archive_thumbnails_ajax(request, inst, proposal, observation=None):
    """Generate the page listing archived images by proposal.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    proposal : str
        Number of observing proposal
    observation : str
        Observation number within the proposal

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """
    log_file = configure_logging("django", include_time=False)
    logging.debug(f"Generating thumbnails for {inst} {proposal} {observation}")
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    # Create nested dictionary of information needed for the page
    data = thumbnails_ajax(inst, proposal, obs_num=observation)
    request.session['navigate_dict_type'] = 'nested'
    logging.debug(f"Ajax returned: {data}")
    data['thumbnail_sort'] = request.session.get("image_sort", "Recent")
    data['thumbnail_group'] = request.session.get("image_group", "Exposure")

    save_page_navigation_data(request, data, style='nested')
    return JsonResponse(data, json_dumps_params={'indent': 2})


def archive_thumbnails_per_observation(request, inst, proposal, observation=None):
    """Generate the page listing all archived images in the database
    for a certain proposal

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    proposal : str
        Number of observing proposal
    observation : str
    Observation number within the proposal

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]
    proposal_meta = text_scrape(proposal)

    # Get a list of all observation numbers for the proposal
    # This will be used to create buttons for observation-specific
    # pages
    rootnames = get_rootnames_for_instrument_proposal(inst, proposal)
    all_obs = []
    for root in rootnames:
        try:
            all_obs.append(filename_parser(root)['observation'])
        except KeyError:
            pass

    obs_list = sorted(list(set(all_obs)))

    sort_type = request.session.get('image_sort', 'Recent')
    group_type = request.session.get('image_group', 'Exposure')

    # Different templates for the single observation versus all observation cases
    template = 'thumbnails_per_obs.html'
    if observation is None:
        template = 'thumbnails_all_obs.html'
        observation = 'none'

    context = {'base_url': get_base_url(),
               'inst': inst,
               'obs': observation,
               'obs_list': obs_list,
               'prop': proposal,
               'prop_meta': proposal_meta,
               'sort': sort_type,
               'group': group_type}

    return render(request, template, context)


def archive_thumbnails_query_ajax(request):
    """Generate the page listing archived images by query parameters.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    proposal : str
        Number of observing proposal

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """

    parameters = request.session.get("query_config", QUERY_CONFIG_TEMPLATE.copy())
    filtered_rootnames = get_rootnames_from_query(parameters)

    paginator = Paginator(filtered_rootnames,
                          parameters[QueryConfigKeys.NUM_PER_PAGE])
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    data = thumbnails_query_ajax(page_obj.object_list)
    data['thumbnail_sort'] = parameters[QueryConfigKeys.SORT_TYPE]
    data['thumbnail_group'] = request.session.get("image_group", "Exposure")

    # Navigation data will be a flat, rather than nested dictionary. This will allow
    # stage 2 and 3 files to mix on the results page
    request.session['navigate_dict_type'] = 'flat'

    # add top level parameters for summarizing
    data['query_config'] = {}
    for key in parameters:
        value = parameters[key]
        if isinstance(value, dict):
            for subkey in value:
                subvalue = value[subkey]
                if subvalue:
                    data['query_config'][f'{key}_{subkey}'] = subvalue
        elif value:
            data['query_config'][key] = value

    # pass pagination info
    if page_obj.has_previous():
        data['previous_page'] = page_obj.previous_page_number()
    data['current_page'] = page_obj.number
    if page_obj.has_next():
        data['next_page'] = page_obj.next_page_number()
    data['total_pages'] = paginator.num_pages
    data['total_files'] = paginator.count

    request.session['image_sort'] = parameters[QueryConfigKeys.SORT_TYPE]
    save_page_navigation_data(request, data, style='flat')
    return JsonResponse(data, json_dumps_params={'indent': 2})


def dashboard(request):
    """Generate the dashboard page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = 'dashboard.html'

    db = get_dashboard_components(request)
    pie_graph = db.dashboard_instrument_pie_chart()
    files_graph = db.dashboard_files_per_day()
    useage_graph = db.dashboard_disk_usage()
    directories_usage_graph, central_store_usage_graph = db.dashboard_central_store_data_volume()
    filetype_bar = db.dashboard_filetype_bar_chart()
    table_columns, table_values = db.dashboard_monitor_tracking()
    grating_plot = db.dashboard_exposure_count_by_filter()
    anomaly_plot = db.dashboard_anomaly_per_instrument()

    plot = layout([[files_graph, useage_graph],
                   [directories_usage_graph, central_store_usage_graph],
                   [pie_graph, filetype_bar],
                   [grating_plot, anomaly_plot]], sizing_mode='stretch_width')
    script, div = components(plot)

    time_deltas = ['All Time', '1 Day', '1 Week', '1 Month', '1 Year']

    context = {'inst': '',
               'script': script,
               'div': div,
               'table_columns': table_columns,
               'table_rows': table_values,
               'time_deltas': time_deltas}

    return render(request, template, context)


def download_edb_data(request, mnemonic_result):
    """
    """
    mnemonic_identifier = mnemonic_result.mnemonic_identifier
    start_time = mnemonic_result.start_time
    end_time = mnemonic_result.end_time

    result_table = mnemonic_result.data

    # add meta data to saved table
    comments = []
    comments.append('DMS EDB query of {}:'.format(mnemonic_identifier))
    for key, value in mnemonic_query_result.info.items():
        comments.append('{} = {}'.format(key, str(value)))
    comments.append(' ')
    comments.append('Start time {}'.format(start_time.isot))
    comments.append('End time   {}'.format(end_time.isot))
    comments.append('Number of rows {}'.format(len(result_table)))
    comments.append(' ')
    result_table.meta['comments'] = comments

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{mnemonic_query_result.file_for_download}"'

    writer = csv.writer(response)

    for comment in result_table.meta['comments']:
        writer.writerow(comment)
    for i in range(len(result_table)):
        writer.writerow([result_table['dates'][i], result_table['euvalues'][i]])

    now do we need a new html file that this sends the response to? probably.

    return response


def download_report(request, inst):
    """Download data report by look status.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage.
    inst : str
        The JWST instrument of interest.

    Returns
    -------
    response : HttpResponse object
        Outgoing response sent to the webpage
    """
    # check for filter criteria passed in request
    kwargs = dict()
    for filter_name in ['look', 'exp_type', 'cat_type', 'proposal', 'sort_as']:
        kwargs[filter_name] = request.GET.get(filter_name)

    # get all observation looks from file info model
    # and join with observation descriptors
    keys, looks = get_instrument_looks(inst, **kwargs)

    today = datetime.datetime.now().strftime('%Y%m%d')
    filename = f'{inst.lower()}_report_{today}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(keys)
    for row in looks:
        writer.writerow(row.values())

    return response


def engineering_database(request):
    """Generate the EDB page.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage

    """

    edb_components = get_edb_components(request)

    template = 'engineering_database.html'
    context = {'inst': '',
               'edb_components': edb_components}

    return render(request, template, context)


def export(request, tablename):
    """Function to export and download data from JWQLDB Table Viewer

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    tablename : str
        Name of table to download

    Returns
    -------
    response : HttpResponse object
        Outgoing response sent to the webpage
    """
    table_meta = build_table(tablename)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(tablename)

    writer = csv.writer(response)
    writer.writerow(table_meta.columns.values)
    for _, row in table_meta.iterrows():
        writer.writerow(row.values)

    return response


def home(request):
    """Generate the home page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Create a form instance and populate it with data from the request
    form = FileSearchForm(request.POST or None)

    # If this is a POST request, we need to process the form data
    if request.method == 'POST':
        if form.is_valid():
            return form.redirect_to_files()

    template = 'home.html'
    context = {'inst': '',
               'form': form}

    return render(request, template, context)


def instrument(request, inst):
    """Generate the instrument tool index page.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'instrument.html'

    doc_url = URL_DICT[inst.lower()]

    context = {'inst': inst,
               'doc_url': doc_url}

    return render(request, template, context)


def jwqldb_table_viewer(request, tablename_param=None):
    """Generate the JWQL Table Viewer view.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    tablename_param : str
        Table name parameter from URL

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    try:
        tablename = request.POST['db_table_select']
    except KeyError:
        if tablename_param:
            tablename = tablename_param
        else:
            tablename = None

    if tablename is None:
        table_meta = None
    else:
        table_meta = build_table(tablename)

    all_jwql_tables = import_all_models()

    jwql_tables_by_instrument = {}
    instruments = ['nircam', 'nirspec', 'niriss', 'miri', 'fgs']

    #  Sort tables by instrument
    for instrument in instruments:
        jwql_tables_by_instrument[instrument] = [tablename for tablename in all_jwql_tables if instrument in tablename.lower() and tablename not in JWQLDB_EXCLUDED]

    # Wisp finder DB doesn't follow the naming convention. Add it here.
    jwql_tables_by_instrument['nircam'].append('WispFinderB4QueryHistory')

    # Don't forget tables that dont contain instrument specific instrument information.
    jwql_tables_by_instrument['general'] = [table for table in all_jwql_tables if not any(instrument in table.lower() for instrument in instruments) and table not in JWQLDB_EXCLUDED]
    jwql_tables_by_instrument['general'].remove('WispFinderB4QueryHistory')

    template = 'jwqldb_table_viewer.html'

    # If value of table_meta is None (when coming from home page)
    if table_meta is None:
        context = {
            'inst': '',
            'all_jwql_tables': jwql_tables_by_instrument}
    # If table_meta is empty, just render table with no data.
    elif table_meta.empty:
        context = {
            'inst': '',
            'all_jwql_tables': jwql_tables_by_instrument,
            'table_columns': table_meta.columns.values,
            'table_name': tablename}
    # Else, everything is good to go, render the table.
    else:
        context = {
            'inst': '',
            'all_jwql_tables': jwql_tables_by_instrument,
            'table_columns': table_meta.columns.values,
            'table_rows': table_meta.values,
            'table_name': tablename}

    return render(request, template, context)


def log_view(request):
    """Access JWQL monitoring logs from the web app.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = 'log_view.html'
    log_path = get_config()['log_dir']
    log_name = request.POST.get('log_submit', None)

    hostname = socket.gethostname()

    if 'dljwql' in hostname:
        server = 'dev'
    elif 'tljwql' in hostname:
        server = 'test'
    else:
        server = 'ops'

    full_log_paths = sorted(glob.glob(os.path.join(log_path, server, '*', '*')), reverse=True)
    full_log_paths = [log for log in full_log_paths if not os.path.basename(log).startswith('.')]
    log_dictionary = {os.path.basename(path): path for path in full_log_paths}

    if log_name:
        with open(log_dictionary[log_name]) as f:
            log_text = f.read()
    else:
        log_text = None

    context = {'inst': '',
               'all_logs': log_dictionary,
               'log_text': log_text,
               'log_name': log_name}

    return render(request, template, context)


def not_found(request, *kwargs):
    """Generate a ``not_found`` page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = random_404_page()
    status_code = 404  # Note that this will show 400, 403, 404, and 500 as 404 status
    context = {'inst': ''}

    return render(request, template, context, status=status_code)


def query_submit(request):
    """Generate the page listing all archived images in the database
    for a certain proposal

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = 'query_submit.html'
    sort_type = request.session.get('image_sort', 'Recent')
    group_type = request.session.get('image_group', 'Exposure')
    page_number = request.GET.get("page", 1)
    context = {'inst': '',
               'base_url': get_base_url(),
               'sort': sort_type,
               'group': group_type,
               'page': page_number}

    return render(request, template, context)


def query_download(request):
    """Download query results in csv format

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage.

    Returns
    -------
    response : HttpResponse object
        Outgoing response sent to the webpage (csv file to be downloaded)
    """
    parameters = request.session.get("query_config", QUERY_CONFIG_TEMPLATE.copy())
    filtered_rootnames = get_rootnames_from_query(parameters)

    today = datetime.datetime.now().strftime('%Y%m%d_%H:%M')
    filename = f'jwql_query_{today}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    header_row = ["Index", "Name"]
    writer = csv.writer(response)
    writer.writerow(header_row)
    for index, rootname in enumerate(filtered_rootnames):
        writer.writerow([index, rootname])

    return response


def unlooked_images(request, inst):
    """Generate the page listing all unlooked images in the database

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    pass


def view_header(request, inst, filename, filetype):
    """Generate the header view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    filename : str
        FITS filename of selected image in filesystem
    filetype : str
        Type of file (e.g. ``uncal``)

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_header.html'
    file_root = '_'.join(filename.split('_'))

    if filetype not in SUFFIXES_OF_ECSV_FILES:
        header_info = get_header_info(filename, filetype)
    else:
        header_info = get_header_info_ecsv(filename, filetype)

    # For level 3 files, we need the obsnum, which cannot be
    # reliably found by parsing the filename.
    if header_info:
        obsidx = np.where(np.array(header_info[0]['keywords']) == 'OBSERVTN')[0]
        if len(obsidx) > 0:
            obsnum = header_info[0]['values'][obsidx[0]]
        else:
            # Observation number not in the header in this case.
            # Query for RootFileInfo instances for similar files, and try to
            # extract the keyword from one of those.
            file_base = '_'.join(filename.split('_')[0:-1])
            root_file_info = RootFileInfo.objects.filter(root_name__startswith=file_base)
            if root_file_info:
                obsnum = root_file_info[0].obsnum.obsnum
            else:
                obsnum = 'N/A'

    else:
        # header_info is an empty dict here.
        # Add an entry that will make it clear to the user that there is no header available.
        # Try to get the obsnum from the RootFileInfo instance
        header_info[0] = {'No header available': ''}
        file_base = '_'.join(filename.split('_')[0:-1])
        root_file_info = RootFileInfo.objects.filter(root_name__startswith=file_base)
        if root_file_info:
            obsnum = root_file_info[0].obsnum.obsnum
        else:
            obsnum = 'N/A'

    context = {'inst': inst,
               'filename': filename,
               'file_root': file_root,
               'file_type': filetype,
               'extended_root': f"{file_root}_suffix_{filetype}",
               'header_info': header_info,
               'obsnum': obsnum}

    return render(request, template, context)


def explore_image(request, inst, file_root, filetype):
    """Generate the explore image page.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file_root : str
        FITS file_root of selected image in filesystem
    filetype : str
        Type of file (e.g. ``uncal``)

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]
    template = 'explore_image.html'

    # get explorable extensions from header
    extensions = get_explorer_extension_names(file_root, filetype)

    fits_file = file_root + '_' + filetype + '.fits'
    # Get image info containing all paths to fits files
    image_info_list = get_image_info(file_root)
    # Find index of our fits file
    fits_index = next(ix for ix, fits_path in enumerate(image_info_list['all_files']) if fits_file in fits_path)
    # get full path of fits file to open and extract extension info
    full_fits_file = image_info_list['all_files'][fits_index]
    extension_ints = {}
    extension_groups = {}

    # gather extension group/integration information to send
    if os.path.isfile(full_fits_file):
        with fits.open(full_fits_file) as hdulist:
            for exten in extensions:
                dims = hdulist[exten].shape
                if len(dims) == 4:
                    extension_ints[exten], extension_groups[exten], ny, nx = dims
                elif len(dims) == 3:
                    extension_groups[exten] = 0
                    extension_ints[exten], ny, nx = dims
                else:
                    extension_ints[exten] = 0
                    extension_groups[exten] = 0
    else:
        raise FileNotFoundError(f'WARNING: {full_fits_file} does not exist!')

    anomaly_form = get_anomaly_form(request, inst, file_root)
    comment_form = get_comment_form(request, file_root)

    context = {'inst': inst,
               'file_root': file_root,
               'filetype': filetype,
               'file_path': full_fits_file,
               'extensions': extensions,
               'extension_groups': extension_groups,
               'extension_ints': extension_ints,
               'base_url': get_base_url(),
               'jdaviz_host': get_config()["jdaviz"]["host"],
               'jdaviz_port': get_config()["jdaviz"]["port"],
               'anomaly_form': anomaly_form,
               'comment_form': comment_form}

    return render(request, template, context)


def explore_image_ajax(request, inst, file_root, filetype, line_plots='false', low_lim=None, high_lim=None,
                       ext_name="SCI", int1_nr=None, grp1_nr=None, int2_nr=None, grp2_nr=None):
    """Generate the page listing all archived images in the database
    for a certain proposal

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file_root : str
        FITS file_root of selected image in filesystem
    filetype : str
        Type of file (e.g. ``uncal``)
    line_plots : str
        If 'true', column and row plots will be computed and shown with the image.
    low_lim : str
        Signal value to use as the lower limit of the displayed image. If "None", it will be calculated using the ZScale function
    high_lim : str
        Signal value to use as the upper limit of the displayed image. If "None", it will be calculated using the ZScale function
    ext_name : str
        Extension to implement in interactive preview image ("SCI", "DQ", "GROUPDQ", "PIXELDQ", "ERR"...)

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    # Get image info containing all paths to fits files
    image_info_list = get_image_info(file_root)

    # Save fits file name to use for bokeh image
    fits_file = file_root + '_' + filetype + '.fits'
    # Find index of our fits file
    fits_index = next(ix for ix, fits_path in enumerate(image_info_list['all_files']) if fits_file in fits_path)

    # get full path of fits file to send to InteractivePreviewImg
    full_fits_file = image_info_list['all_files'][fits_index]
    # sent floats not strings to init
    if low_lim == "None":
        low_lim = None
    if high_lim == "None":
        high_lim = None
    if int1_nr == "None":
        int1_nr = None
    if grp1_nr == "None":
        grp1_nr = None
    if int2_nr == "None":
        int2_nr = None
    if grp2_nr == "None":
        grp2_nr = None

    if low_lim is not None:
        low_lim = float(low_lim)
    if high_lim is not None:
        high_lim = float(high_lim)

    group = None
    integ = None
    if (grp1_nr):
        if (grp2_nr):
            group = [int(grp1_nr), int(grp2_nr)]
        else:
            group = int(grp1_nr)
    if (int1_nr):
        if (int2_nr):
            integ = [int(int1_nr), int(int2_nr)]
        else:
            integ = int(int1_nr)

    if str(line_plots).strip().lower() == 'true':
        line_plots = True
    else:
        line_plots = False

    int_preview_image = InteractivePreviewImg(
        full_fits_file, low_lim=low_lim, high_lim=high_lim, extname=ext_name,
        group=group, integ=integ, line_plots=line_plots)

    context = {'inst': "inst",
               'script': int_preview_image.script,
               'div': int_preview_image.div}

    return JsonResponse(context, json_dumps_params={'indent': 2})


def save_image_group_ajax(request):
    """Save the latest selected group type in the session.

    Parameters
    ----------
    request : HttpRequest
        The incoming request.

    Returns
    -------
    JsonResponse
        Object containing the group value as set in the session (key: 'item').
    """
    image_group = request.GET['group_type']
    request.session['image_group'] = image_group
    context = {'item': request.session['image_group']}
    return JsonResponse(context, json_dumps_params={'indent': 2})


def save_image_sort_ajax(request):
    """Save the latest selected sort type in the session.

    Parameters
    ----------
    request : HttpRequest
        The incoming request.

    Returns
    -------
    JsonResponse
        Object containing the sort value as set in the session (key: 'item').
    """
    # a string of the form " 'rootname1'='expstart1', 'rootname2'='expstart2', ..."
    image_sort = request.GET['sort_type']

    request.session['image_sort'] = image_sort
    context = {'item': request.session['image_sort']}
    return JsonResponse(context, json_dumps_params={'indent': 2})


def save_page_navigation_data(request, data, style='nested'):
    """
    Save the data from the current page in the session.

    Enables navigating to the next or previous page.  Current sort options
    are Ascending/Descending, and Recent/Oldest.

    Parameters
    ----------
    request: HttpRequest object
    data: dictionary
        the data dictionary to be returned from the calling view function
    style: str
        'nested' when coming from observation level page. 'flat' when coming from query results page
    nav_by_date_range: boolean
        when viewing an image, will the next/previous buttons be sorted by date? (the other option is rootname)
    """
    navigate_data = {}
    try:
        for rootname in data['file_data']:
            navigate_data[rootname] = data['file_data'][rootname]['expstart']
    except:
        if style == 'nested':
            for obs in data['file_data']:
                navigate_data[obs] = {}
                for stage in ['stage_2', 'stage_3']:
                    navigate_data[obs][stage] = {}
                    for rootname in data['file_data'][obs][stage]['files']:
                        navigate_data[obs][stage][rootname] = data['file_data'][obs][stage]['files'][rootname]['expstart']
        elif style == 'flat':
            for obs in data['file_data']:
                for stage in ['stage_2', 'stage_3']:
                    for rootname in data['file_data'][obs][stage]['files']:
                        navigate_data[rootname] = data['file_data'][obs][stage]['files'][rootname]['expstart']
        else:
            raise ValueError(f'Unrecognized style keyword value: {style}. Must be either "flat" or "nested"')

    request.session['navigation_data'] = navigate_data
    return


def set_viewed_ajax(request, group_root, status):
    """Update the model's "viewed" field for a group of files

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    group_root : str
        Group root name, matching filename roots up to
        but not including the detector.
    status : {'new', 'viewed'}
        Value to set: 'new' for viewed=False, 'viewed' for viewed=True.

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """
    viewed = (str(status).strip().lower() == 'viewed')

    root_file_info = RootFileInfo.objects.filter(
        root_name__startswith=group_root)
    for root_file in root_file_info:
        root_file.viewed = viewed
        root_file.save()

    #  check actual status as set
    marked_viewed = all([rf.viewed for rf in root_file_info])

    # Build the context
    context = {'marked_viewed': marked_viewed}
    return JsonResponse(context, json_dumps_params={'indent': 2})


def get_leaf_values(d):
    """Recursively collect all bottom-level values from a nested dict."""
    values = []
    for v in d.values():
        if isinstance(v, dict):
            values.extend(get_leaf_values(v))
        else:
            values.append(v)
    return values


def get_leaf_keys(d):
    """Recursively collect all bottom-level keys from a nested dict."""
    keys = []
    for v in d.values():
        if isinstance(v, dict):
            keys.extend(get_leaf_keys(v))
        else:
            keys.append(v)  # bottom-level: the key is what we want
    # Fix: we need the keys, not values, at the leaf level
    keys = []
    for k, v in d.items():
        if isinstance(v, dict):
            keys.extend(get_leaf_keys(v))
        else:
            keys.append(k)
    return keys


def sort_leaf_dict(d, mode):
    """Sort a bottom-level dict by the given mode."""
    if mode in ('Recent', 'Oldest'):
        reverse = (mode == 'Recent')
        return dict(sorted(d.items(), key=lambda x: x[1], reverse=reverse))
    elif mode in ('Ascending', 'Descending'):
        reverse = (mode == 'Descending')
        return dict(sorted(d.items(), key=lambda x: x[0], reverse=reverse))


def sort_nested_navigation_data(sorting_type, nav_data):
    """
    Sort nav_data in one of four modes:
      'Recent'     - chronological by MJD values (smallest first)
      'Oldest'     - reverse chronological by MJD values (largest first)
      'Ascending'  - alphabetical by bottom-level keys
      'Descending' - reverse alphabetical by bottom-level keys

    Top-level keys are sorted by the same criterion applied to their contents.
    Stage keys are always ordered stage_2 before stage_3.
    """
    STAGE_ORDER = ['stage_2', 'stage_3']

    # --- Determine the sort key for top-level entries ---
    if sorting_type in ('Recent', 'Oldest'):
        # Use the minimum leaf value across all stages as the representative date
        def top_key(item):
            return min(get_leaf_values(item[1]))
        reverse = (sorting_type == 'Recent')
    elif sorting_type in ('Ascending', 'Descending'):
        # Use the first (alphabetically smallest) leaf key as the representative
        def top_key(item):
            return min(get_leaf_keys(item[1]))
        reverse = (sorting_type == 'Descending')

    # --- Sort top-level entries ---
    sorted_top = sorted(nav_data.items(), key=top_key, reverse=reverse)

    # --- Rebuild dict with sorted stages and sorted leaf dicts ---
    result = {}
    for obs_k, obs_v in sorted_top:
        sorted_stages = {}
        for stage in STAGE_ORDER:
            if stage in obs_v:
                sorted_stages[stage] = sort_leaf_dict(obs_v[stage], sorting_type)
        result[obs_k] = sorted_stages

    # Now create a list of file root names in order
    matching_rootfiles = []
    for obs in result.values():
        for stage in obs.values():
            matching_rootfiles.extend(stage.keys())

    return matching_rootfiles


def sort_flat_navigation_data(sorting_type, nav_data):
    """Sort navigation data stored in a flat dictionary (e.g. navigation data coming from a
    query results page.)

    Parameters
    ----------
    sorting_type : str
        Sorting criterium to use ('Descending', 'Recent', 'Oldest')
    nav_data : dict
        Navigataion data. Dictionary with format nav_data[rootname] = exptime.

    Returns
    -------
    group_root_list : list
        List of sorted rootnames
    """
    # For time based sorting options, sort to "Recent" first to create sorting consistency when times are the same.
    # This is consistent with how Tinysort is utilized in jwql.js->sort_by_thumbnails
    if sorting_type in ['Descending']:
        matching_rootfiles = sorted(nav_data.keys(), reverse=True)
    elif sorting_type in ['Recent']:
        # First sort by the exposure start time, and then by filename,
        # in order to guarantee consistency (since there are multiple files with matching exposure start times)
        matching_rootfiles = sorted(nav_data,
            key=lambda k: (-nav_data[k], k)
            )
    elif sorting_type in ['Oldest']:
        # First sort by the exposure start time, and then by filename,
        # in order to guarantee consistency (since there are multiple files with matching exposure start times)
        matching_rootfiles = sorted(nav_data,
            key=lambda k: (nav_data[k], k)
            )
    else:
        matching_rootfiles = sorted(nav_data.keys())

    return matching_rootfiles


def toggle_viewed_ajax(request, file_root):
    """Update the model's "mark_viewed" field and save in the database

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    file_root : str
        FITS file_root of selected image in filesystem

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """
    root_file_info = RootFileInfo.objects.get(root_name=file_root)
    root_file_info.viewed = not root_file_info.viewed
    root_file_info.save()

    # Build the context
    context = {'marked_viewed': root_file_info.viewed}
    return JsonResponse(context, json_dumps_params={'indent': 2})


def view_exposure(request, inst, group_root):
    """Generate the exposure view page.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage.
    inst : str
        Name of JWST instrument.
    group_root : str
        Exposure group, matching file root names up to but not
        including the detector.

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_exposure.html'
    image_info = get_image_info(group_root)

    # Get available suffixes in a consistent order.
    suffixes = get_available_suffixes(image_info['suffixes'],
                                      return_untracked=False)

    # Determine which suffix to show upon page load
    default_suffix = ''
    if "suffix" in request.GET:
        default_suffix = request.GET["suffix"]
    else:
        preferred_suffixes = ["rate", "dark", "uncal", "i2d", "c1d", "x1d", "s3d",
                              "s2d", "whtlt", "phot", "psfsub", "psfstack", "ami",
                              "aminorm", "cal"]
        for suffix in preferred_suffixes:
            if suffix in suffixes:
                default_suffix = suffix
                break

    # Get the anomaly submission form
    form = get_anomaly_form(request, inst, group_root)
    group_anomalies = get_group_anomalies(group_root)
    exposure_comment_form = get_exp_comment_form(request, group_root)

    # if we get to this page without any navigation data,
    # previous/next buttons will be hidden
    navigation_data = request.session.get('navigation_data')

    # For time based sorting options, sort to "Recent" first to create sorting consistency when times are the same.
    # This is consistent with how Tinysort is utilized in jwql.js->sort_by_thumbnails
    if navigation_data:
        sort_type = request.session.get('image_sort', 'Recent')

        # Sort the navigation data. Use separate functions for nested (coming from an observation
        # level page) vs flat (coming from a query results page) navigation_data
        first_key = next(iter(navigation_data))
        if not isinstance(navigation_data[first_key], dict):
            matching_rootfiles = sort_flat_navigation_data(sort_type, navigation_data)
        else:
            matching_rootfiles = sort_nested_navigation_data(sort_type, navigation_data)

        # pick out group names from the matching root files
        group_root_list = []
        for rootname in matching_rootfiles:
            try:
                other_group_root = filename_parser(rootname)['group_root']
            except ValueError:
                continue
            if other_group_root not in group_root_list:
                group_root_list.append(other_group_root)
    else:
        # If there is no navigation_data, just use the current files
        group_root_list = []
        for file in image_info['all_files']: #do something smarter here. find obslist, loop over obs/stage
            name = Path(file).name           #need to match the initial Recent sort done on the thumbnails!
            obs = name.split("_")[0]
            if obs not in group_root_list:
                group_root_list.append(obs)

    # Get our current views RootFileInfo model and send our "viewed/new" information
    root_file_info = RootFileInfo.objects.filter(root_name__startswith=group_root)
    if len(root_file_info) == 0:
        return generate_error_view(request, inst, f"No groups starting with {group_root} currently in JWQL database.")
    viewed = all([rf.viewed for rf in root_file_info])

    # Get the program ID and the obsnum
    prop_id = root_file_info[0].proposal.zfill(5)
    obsnum = root_file_info[0].obsnum.obsnum

    # Convert expstart from MJD to a date
    expstart_str = Time(root_file_info[0].expstart, format='mjd').to_datetime().strftime('%d %b %Y %H:%M')

    # Create one dict of info to show at the top of the page, and another dict of info
    # to show in the collapsible text box.
    try:
        basic_info, additional_info = get_additional_exposure_info(root_file_info, image_info)
    except FileNotFoundError as e:
        return generate_error_view(request, inst,
                                   "Looks like at least one of your files has not yet been ingested into the JWQL database.  \
                                   If this is a newer observation, please wait a few hours and try again.  \
                                   If this observation is over a day old please contact JWQL support.",
                                   exception_message=f"Received Error: '{e}'")

    logging.info(f"Group Root is {group_root}")
    logging.info(f"Group Root List is {group_root_list}")
    logging.info(f"Group Root in List: {group_root in group_root_list}")
    logging.info(f"prop_id is : {prop_id}")
    logging.info(f"obsnum is: {obsnum}")

    # Build the context
    context = {'base_url': get_base_url(),
               'group_root_list': group_root_list,
               'inst': inst,
               'prop_id': prop_id,
               'obsnum': obsnum,
               'group_root': group_root,
               'suffixes': suffixes,
               'initial_suffix': default_suffix,
               'num_ints': image_info['num_ints'],
               'available_ints': image_info['available_ints'],
               'total_ints': image_info['total_ints'],
               'detectors': sorted(image_info['detectors']),
               'form': form,
               'marked_viewed': viewed,
               'expstart_str': expstart_str,
               'basic_info': basic_info,
               'additional_info': additional_info,
               'group_anomalies': group_anomalies,
               'exposure_comment_form': exposure_comment_form}

    return render(request, template, context)


def view_image(request, inst, file_root, initial_suffix=None):
    """Generate the image view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file_root : str
        FITS filename of selected image in filesystem
    initial_suffix : str, default ""
        Suffix to start by loading (supplied from view_exposure)

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_image.html'
    image_info = get_image_info(file_root)
    logging.debug(f"image_info: {image_info}")

    # Put suffixes in a consistent order. Check if any of the
    # suffixes are not in the list that specifies order.
    logging.debug(f"Initial set of suffixes: {image_info['suffixes']}")
    suffixes, untracked_suffixes = get_available_suffixes(
        image_info['suffixes'], return_untracked=True)
    logging.debug(f"Final suffixes: {suffixes}")

    if len(untracked_suffixes) > 0:
        logging.warning((f'In view_image(), for {inst}, {file_root}, '
                         f'the following suffixes are present in the data, '
                         f'but not in EXPOSURE_PAGE_SUFFIX_ORDER in '
                         f'constants.py: {untracked_suffixes} '
                         'Please add them, so that they will appear in a '
                         'consistent order on the webpage.'))

    url_suffix = None
    if "_suffix_" in file_root:
        file_bits = file_root.split("_")
        file_root = "_".join(file_bits[:-2])
        url_suffix = file_bits[-1]
    log_file = configure_logging("django", include_time=False)
    logging.debug(f"Running through view_image() for {inst} {file_root}")

    request_suffix = None
    if "suffix" in request.GET:
        request_suffix = request.GET["suffix"]

    if initial_suffix is not None:
        logging.debug(f"Setting suffix via initial suffix to {initial_suffix}")
        default_suffix = initial_suffix
    elif request_suffix is not None:
        logging.debug(f"Setting suffix via request object to {request_suffix}")
        default_suffix = request_suffix
    elif url_suffix is not None:
        logging.debug(f"Setting suffix via URL apped to {url_suffix}")
        default_suffix = url_suffix
    elif 'rate' in suffixes:
        # Default to rate files for level 2 rootnames
        default_suffix = 'rate'
    elif 'x1d' in suffixes:
        # Default to x1d files for the level 3 rootnames
        default_suffix = 'x1d'
    else:
        # In this case, the html template will fall back to the first suffix
        # in the list.
        default_suffix = ""

    default_preview = ""
    preview_cookie = request.COOKIES.get('preview')
    if preview_cookie:
        logging.debug(f"Found cookie value {preview_cookie}")
        default_preview = preview_cookie
    elif "preview" in request.GET:
        default_preview = request.GET["preview"]

    file_paths = {}
    for file_path in image_info['all_files']:
        logging.debug(f"Checking input file {file_path}")
        source_path = Path(file_path).parent
        for suffix in suffixes:
            logging.debug(f"\tChecking suffix {suffix}")
            file_type = 'fits'
            if suffix in SUFFIXES_OF_ECSV_FILES:
                file_type = 'ecsv'
            file_search = list(source_path.rglob(f"{file_root}*_{suffix}.{file_type}"))
            if len(file_search) > 0:
                if suffix not in file_paths:
                    logging.debug(f"\tAdding {suffix} to file paths")
                    file_paths[suffix] = file_search[0].as_posix()

    anomaly_form = get_anomaly_form(request, inst, file_root)
    comment_form = get_comment_form(request, file_root)

    prop_id = file_root[2:7]

    # if we get to this page without any navigation data (i.e. direct link),
    # just use the file_root with no expstart time
    # navigate_data is dict of format rootname:expstart
    navigation_data = request.session.get('navigation_data')

    # For time based sorting options, sort to "Recent" first to create
    # sorting consistency when times are the same.
    # This is consistent with how Tinysort is utilized in
    # jwql.js->sort_by_thumbnails
    if navigation_data:
        sort_type = request.session.get('image_sort', 'Recent')

        # Sort the navigation data. Use separate functions for nested (coming from an observation
        # level page) vs flat (coming from a query results page) navigation_data
        first_key = next(iter(navigation_data))
        if not isinstance(navigation_data[first_key], dict):
            file_root_list = sort_flat_navigation_data(sort_type, navigation_data)
        else:
            file_root_list = sort_nested_navigation_data(sort_type, navigation_data)

    else:
        if image_info['level'] == 2:
            file_root_list = sorted(get_detectors_by_rootname(file_root))
        elif image_info['level'] == 3:
            # In most (all?) cases with level 3 rootnames, I think we should end up
            # with a single element list that's essentially equal to file_root
            #file_list = get_filenames_by_rootname(file_root)
            #file_root_list = [filestr.rsplit('_', 1)[0] for filestr in file_list if 'jpg' not in filestr]
            #file_root_list = sorted(set(file_root_list))
            file_root_list = [file_root]

    # Get our current views RootFileInfo model and send our "viewed/new" information
    root_file_info = RootFileInfo.objects.get(root_name=file_root)

    # Convert expstart from MJD to a date
    expstart_str = Time(root_file_info.expstart, format='mjd').to_datetime().strftime('%d %b %Y %H:%M')

    # Create one dict of info to show at the top of the page, and another dict of info
    # to show in the collapsible text box.
    basic_info, additional_info = get_additional_exposure_info(root_file_info, image_info)

    try:
        file_root_index = file_root_list.index(file_root)
    except Exception as e:
        file_root_index = 0

    logging.info(f"File root is {file_root}")
    logging.info(f"File root list is {file_root_list}")
    logging.info(f"File root in file_root_list: {file_root in file_root_list}")
    logging.info(f"file_paths should be a dict: {file_paths}")

    # Build the context
    context = {'base_url': get_base_url(),
               'initial_suffix': default_suffix,
               'initial_preview': default_preview,
               'file_path': source_path,
               'file_root_list': file_root_list,
               'file_paths': file_paths,
               'inst': inst,
               'prop_id': prop_id,
               'obsnum': image_info['obsnum'],
               'file_root': file_root,
               'suffixes': suffixes,
               'num_ints': image_info['num_ints'],
               'available_ints': image_info['available_ints'],
               'total_ints': image_info['total_ints'],
               'anomaly_form': anomaly_form,
               'comment_form': comment_form,
               'marked_viewed': root_file_info.viewed,
               'expstart_str': expstart_str,
               'basic_info': basic_info,
               'additional_info': additional_info,
               'index': file_root_index}

    return render(request, template, context)


def generate_error_view(request, inst, error_message, exception_message=""):
    """Generate the error view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    error_message : str
        Custom Error Message to be seen in error_view.html
    exception_message: str
        if an exception caused this to be generated, pass the exception message along for display

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    template = 'error_view.html'
    context = {'base_url': get_base_url(), 'inst': inst, 'error_message': error_message, 'exception_message': exception_message}
    return render(request, template, context)
