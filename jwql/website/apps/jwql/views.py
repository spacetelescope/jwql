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
import socket

from astropy.time import Time
from bokeh.embed import components
from bokeh.layouts import layout
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from sqlalchemy import inspect

from jwql.database.database_interface import load_connection
from jwql.utils import monitor_utils
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, QUERY_CONFIG_TEMPLATE, URL_DICT, QueryConfigKeys
from jwql.utils.interactive_preview_image import InteractivePreviewImg
from jwql.utils.utils import filename_parser, get_base_url, get_config, get_rootnames_for_instrument_proposal, query_unformat

from .data_containers import (
    build_table,
    get_acknowledgements,
    get_additional_exposure_info,
    get_anomaly_form,
    get_available_suffixes,
    get_dashboard_components,
    get_edb_components,
    get_explorer_extension_names,
    get_group_anomalies,
    get_header_info,
    get_image_info,
    get_instrument_looks,
    get_rootnames_from_query,
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

    # a string of the form " 'rootname1'='expstart1', 'rootname2'='expstart2', ..."
    if request.method == 'POST':
        navigate_dict = request.POST.get('navigate_dict')
        # Save session in form {rootname:expstart}
        rootname_expstarts = dict()
        for item in navigate_dict.split(','):
            rootname, expstart = item.split("=")
            rootname_expstarts[rootname] = float(expstart)
        request.session['navigation_data'] = rootname_expstarts

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
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    data = thumbnails_ajax(inst, proposal, obs_num=observation)
    data['thumbnail_sort'] = request.session.get("image_sort", "Recent")
    data['thumbnail_group'] = request.session.get("image_group", "Exposure")

    save_page_navigation_data(request, data)
    return JsonResponse(data, json_dumps_params={'indent': 2})


def archive_thumbnails_per_observation(request, inst, proposal, observation):
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
    template = 'thumbnails_per_obs.html'
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
    save_page_navigation_data(request, data)
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

    _, _, engine, _ = load_connection(get_config()['connection_string'])
    all_jwql_tables = inspect(engine).get_table_names()

    if 'django_migrations' in all_jwql_tables:
        all_jwql_tables.remove('django_migrations')  # No necessary information.

    jwql_tables_by_instrument = {}
    instruments = ['nircam', 'nirspec', 'niriss', 'miri', 'fgs']

    #  Sort tables by instrument
    for instrument in instruments:
        jwql_tables_by_instrument[instrument] = [tablename for tablename in all_jwql_tables if instrument in tablename]

    # Don't forget tables that dont contain instrument specific instrument information.
    jwql_tables_by_instrument['general'] = [table for table in all_jwql_tables if not any(instrument in table for instrument in instruments)]

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

    context = {'inst': inst,
               'filename': filename,
               'file_root': file_root,
               'file_type': filetype,
               'header_info': get_header_info(filename, filetype)}

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

    context = {'inst': inst,
               'file_root': file_root,
               'filetype': filetype,
               'extensions': extensions,
               'extension_groups': extension_groups,
               'extension_ints': extension_ints,
               'base_url': get_base_url(),
               'anomaly_form': anomaly_form}

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


def save_page_navigation_data(request, data):
    """
    Save the data from the current page in the session.

    Enables navigating to the next or previous page.  Current sort options
    are Ascending/Descending, and Recent/Oldest.

    Parameters
    ----------
    request: HttpRequest object
    data: dictionary
        the data dictionary to be returned from the calling view function
    nav_by_date_range: boolean
        when viewing an image, will the next/previous buttons be sorted by date? (the other option is rootname)
    """
    navigate_data = {}
    for rootname in data['file_data']:
        navigate_data[rootname] = data['file_data'][rootname]['expstart']

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

    # Get the proposal id and obsnum from the group root name
    prop_id = group_root[2:7]
    obsnum = group_root[7:10]

    # Get available suffixes in a consistent order.
    suffixes = get_available_suffixes(image_info['suffixes'],
                                      return_untracked=False)

    # Get the anomaly submission form
    form = get_anomaly_form(request, inst, group_root)
    group_anomalies = get_group_anomalies(group_root)

    # if we get to this page without any navigation data,
    # previous/next buttons will be hidden
    navigation_data = request.session.get('navigation_data', {})

    # For time based sorting options, sort to "Recent" first to create sorting consistency when times are the same.
    # This is consistent with how Tinysort is utilized in jwql.js->sort_by_thumbnails
    sort_type = request.session.get('image_sort', 'Recent')
    if sort_type in ['Descending']:
        matching_rootfiles = sorted(navigation_data, reverse=True)
    elif sort_type in ['Recent']:
        navigation_data = dict(sorted(navigation_data.items()))
        navigation_data = dict(sorted(navigation_data.items(), key=operator.itemgetter(1), reverse=True))
        matching_rootfiles = list(navigation_data.keys())
    elif sort_type in ['Oldest']:
        navigation_data = dict(sorted(navigation_data.items()))
        navigation_data = dict(sorted(navigation_data.items(), key=operator.itemgetter(1)))
        matching_rootfiles = list(navigation_data.keys())
    else:
        matching_rootfiles = sorted(navigation_data)

    # pick out group names from matching root files
    group_root_list = []
    for rootname in matching_rootfiles:
        try:
            other_group_root = filename_parser(rootname)['group_root']
        except ValueError:
            continue
        if other_group_root not in group_root_list:
            group_root_list.append(other_group_root)

    # Get our current views RootFileInfo model and send our "viewed/new" information
    root_file_info = RootFileInfo.objects.filter(root_name__startswith=group_root)
    if len(root_file_info) == 0:
        return generate_error_view(request, inst, f"No groups starting with {group_root} currently in JWQL database.")
    viewed = all([rf.viewed for rf in root_file_info])

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

    # Build the context
    context = {'base_url': get_base_url(),
               'group_root_list': group_root_list,
               'inst': inst,
               'prop_id': prop_id,
               'obsnum': obsnum,
               'group_root': group_root,
               'suffixes': suffixes,
               'num_ints': image_info['num_ints'],
               'available_ints': image_info['available_ints'],
               'total_ints': image_info['total_ints'],
               'detectors': sorted(image_info['detectors']),
               'form': form,
               'marked_viewed': viewed,
               'expstart_str': expstart_str,
               'basic_info': basic_info,
               'additional_info': additional_info,
               'group_anomalies': group_anomalies}

    return render(request, template, context)


def view_image(request, inst, file_root):
    """Generate the image view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file_root : str
        FITS filename of selected image in filesystem

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_image.html'
    image_info = get_image_info(file_root)

    # Put suffixes in a consistent order. Check if any of the
    # suffixes are not in the list that specifies order.
    suffixes, untracked_suffixes = get_available_suffixes(
        image_info['suffixes'], return_untracked=True)

    if len(untracked_suffixes) > 0:
        module = os.path.basename(__file__).strip('.py')
        monitor_utils.initialize_instrument_monitor(module)
        logging.warning((f'In view_image(), for {inst}, {file_root}, '
                         f'the following suffixes are present in the data, '
                         f'but not in EXPOSURE_PAGE_SUFFIX_ORDER in '
                         f'constants.py: {untracked_suffixes} '
                         'Please add them, so that they will appear in a '
                         'consistent order on the webpage.'))

    anomaly_form = get_anomaly_form(request, inst, file_root)

    prop_id = file_root[2:7]

    # if we get to this page without any navigation data (i.e. direct link),
    # just use the file_root with no expstart time
    # navigate_data is dict of format rootname:expstart
    navigation_data = request.session.get('navigation_data', {file_root: 0})

    # For time based sorting options, sort to "Recent" first to create
    # sorting consistency when times are the same.
    # This is consistent with how Tinysort is utilized in
    # jwql.js->sort_by_thumbnails
    sort_type = request.session.get('image_sort', 'Recent')
    if sort_type in ['Descending']:
        file_root_list = sorted(navigation_data, reverse=True)
    elif sort_type in ['Recent']:
        navigation_data = dict(sorted(navigation_data.items()))
        navigation_data = dict(sorted(navigation_data.items(),
                                      key=operator.itemgetter(1), reverse=True))
        file_root_list = list(navigation_data.keys())
    elif sort_type in ['Oldest']:
        navigation_data = dict(sorted(navigation_data.items()))
        navigation_data = dict(sorted(navigation_data.items(),
                                      key=operator.itemgetter(1)))
        file_root_list = list(navigation_data.keys())
    else:
        file_root_list = sorted(navigation_data)

    # Get our current views RootFileInfo model and send our "viewed/new" information
    root_file_info = RootFileInfo.objects.get(root_name=file_root)

    # Convert expstart from MJD to a date
    expstart_str = Time(root_file_info.expstart, format='mjd').to_datetime().strftime('%d %b %Y %H:%M')

    # Create one dict of info to show at the top of the page, and another dict of info
    # to show in the collapsible text box.
    basic_info, additional_info = get_additional_exposure_info(root_file_info, image_info)

    # Build the context
    context = {'base_url': get_base_url(),
               'file_root_list': file_root_list,
               'inst': inst,
               'prop_id': prop_id,
               'obsnum': file_root[7:10],
               'file_root': file_root,
               'suffixes': suffixes,
               'num_ints': image_info['num_ints'],
               'available_ints': image_info['available_ints'],
               'total_ints': image_info['total_ints'],
               'anomaly_form': anomaly_form,
               'marked_viewed': root_file_info.viewed,
               'expstart_str': expstart_str,
               'basic_info': basic_info,
               'additional_info': additional_info}

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
