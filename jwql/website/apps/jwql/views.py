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
    - Bryan Hilbert


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

from collections import defaultdict
from copy import deepcopy
import csv
import json
import glob
import logging
import os
import operator

from bokeh.layouts import layout
from bokeh.embed import components
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
import numpy as np
import socket

from jwql.database.database_interface import load_connection
from jwql.utils import monitor_utils
from jwql.utils.interactive_preview_image import InteractivePreviewImg
from jwql.utils.constants import EXPOSURE_PAGE_SUFFIX_ORDER, JWST_INSTRUMENT_NAMES_MIXEDCASE, URL_DICT, THUMBNAIL_FILTER_LOOK, QUERY_CONFIG_TEMPLATE, QUERY_CONFIG_KEYS
from jwql.utils.utils import filename_parser, get_base_url, get_config, get_rootnames_for_instrument_proposal, query_unformat

from .data_containers import build_table
from .data_containers import get_acknowledgements
from .data_containers import get_anomaly_form
from .data_containers import get_dashboard_components
from .data_containers import get_edb_components
from .data_containers import get_explorer_extension_names
from .data_containers import get_header_info
from .data_containers import get_image_info
from .data_containers import get_thumbnails_all_instruments
from .data_containers import random_404_page
from .data_containers import text_scrape
from .data_containers import thumbnails_ajax
from .data_containers import thumbnails_query_ajax
from .data_containers import thumbnails_date_range_ajax
from .forms import JwqlQueryForm
from .forms import FileSearchForm
if not os.environ.get("READTHEDOCS"):
    from .models import Observation, Proposal, RootFileInfo
from astropy.io import fits
from astropy.time import Time
import astropy.units as u


def jwql_query(request):
    """The anomaly query form page"""

    form = JwqlQueryForm(request.POST or None)

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
                query_configs[instrument]['anomalies'] = [query_unformat(i) for i in form.cleaned_data['{}_anomalies'.format(instrument)]]

            all_filters, all_apers, all_detectors, all_exptypes, all_readpatts, all_gratings, all_anomalies = {}, {}, {}, {}, {}, {}, {}
            for instrument in query_configs:
                all_filters[instrument] = query_configs[instrument]['filters']
                all_apers[instrument] = query_configs[instrument]['apertures']
                all_detectors[instrument] = query_configs[instrument]['detectors']
                all_exptypes[instrument] = query_configs[instrument]['exptypes']
                all_readpatts[instrument] = query_configs[instrument]['readpatts']
                all_gratings[instrument] = query_configs[instrument]['gratings']
                all_anomalies[instrument] = query_configs[instrument]['anomalies']

            parameters = QUERY_CONFIG_TEMPLATE.copy()
            parameters[QUERY_CONFIG_KEYS.INSTRUMENTS] = form.cleaned_data['instrument']
            parameters[QUERY_CONFIG_KEYS.ANOMALIES] = all_anomalies
            parameters[QUERY_CONFIG_KEYS.APERTURES] = all_apers
            parameters[QUERY_CONFIG_KEYS.FILTERS] = all_filters
            parameters[QUERY_CONFIG_KEYS.DETECTORS] = all_detectors
            parameters[QUERY_CONFIG_KEYS.EXP_TYPES] = all_exptypes
            parameters[QUERY_CONFIG_KEYS.READ_PATTS] = all_readpatts
            parameters[QUERY_CONFIG_KEYS.GRATINGS] = all_gratings
            parameters[QUERY_CONFIG_KEYS.EXP_TIME_MIN] = str(form.cleaned_data['exp_time_min'])
            parameters[QUERY_CONFIG_KEYS.EXP_TIME_MAX] = str(form.cleaned_data['exp_time_max'])

            # save the query config settings to a session
            request.session['query_config'] = parameters
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
        rootname_expstarts = dict(item.split("=") for item in navigate_dict.split(","))
        request.session['navigation_data'] = rootname_expstarts
    context = {'item': request.session['navigation_data']}
    return JsonResponse(context, json_dumps_params={'indent': 2})


def archive_date_range(request, inst):
    """Generate the page for date range images

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

    template = 'archive_date_range.html'
    sort_type = request.session.get('image_sort', 'Recent')
    context = {'inst': inst,
               'base_url': get_base_url(),
               'sort': sort_type}

    return render(request, template, context)


def archive_date_range_ajax(request, inst, start_date, stop_date):
    """Generate the page listing all archived images within the inclusive date range for all proposals

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    start_date : str
        Start date for date range
    stop_date : str
        stop date for date range

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    # Calculate start date/time in MJD format to begin our range
    inclusive_start_time = Time(start_date)
    # Add a minute to the stop time and mark it 'exclusive' for code clarity, doing this to get all seconds selected minute
    exclusive_stop_time = Time(stop_date) + (1 * u.minute)

    # Get a queryset of all observations STARTING WITHIN our date range
    begin_after_start = Observation.objects.filter(proposal__archive__instrument=inst, obsstart__gte=inclusive_start_time.mjd)
    all_entries_beginning_in_range = begin_after_start.filter(obsstart__lt=exclusive_stop_time.mjd)

    # Get a queryset of all observations ENDING WITHIN our date range
    end_after_start = Observation.objects.filter(proposal__archive__instrument=inst, obsend__gte=inclusive_start_time.mjd)
    all_entries_ending_in_range = end_after_start.filter(obsend__lt=exclusive_stop_time.mjd)

    # Get a queryset of all observations SPANNING (starting before and ending after) our date range.  Bump our window out a few days to catch hypothetical
    # observations that last over 24 hours.  The larger the window the more time the query takes so keeping it tight.
    two_days_before_start_time = Time(start_date) - (2 * u.day)
    two_days_after_end_time = Time(stop_date) + (3 * u.day)
    end_after_stop = Observation.objects.filter(proposal__archive__instrument=inst, obsend__gte=two_days_after_end_time.mjd)
    all_entries_spanning_range = end_after_stop.filter(obsstart__lt=two_days_before_start_time.mjd)

    obs_beginning = [observation for observation in all_entries_beginning_in_range]
    obs_ending = [observation for observation in all_entries_ending_in_range]
    obs_spanning = [observation for observation in all_entries_spanning_range]

    # Create a single list of all pertinent observations
    all_observations = list(set(obs_beginning + obs_ending + obs_spanning))
    # Get all thumbnails that occurred within the time frame for these observations
    data = thumbnails_date_range_ajax(inst, all_observations, inclusive_start_time.mjd, exclusive_stop_time.mjd)
    data['thumbnail_sort'] = request.session.get("image_sort", "Recent")

    # Create Dictionary of Rootnames with expstart
    save_page_navigation_data(request, data)
    return JsonResponse(data, json_dumps_params={'indent': 2})


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
    # as use as the context
    output_dir = get_config()['outputs']
    context_file = os.path.join(output_dir, 'archive_page', f'{inst}_archive_context.json')

    with open(context_file, 'r') as obj:
        context = json.load(obj)

    return JsonResponse(context, json_dumps_params={'indent': 2})


def archive_thumbnails_ajax(request, inst, proposal, observation=None):
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
    JsonResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    data = thumbnails_ajax(inst, proposal, obs_num=observation)
    data['thumbnail_sort'] = request.session.get("image_sort", "Ascending")

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

    sort_type = request.session.get('image_sort', 'Ascending')
    template = 'thumbnails_per_obs.html'
    context = {'base_url': get_base_url(),
               'inst': inst,
               'obs': observation,
               'obs_list': obs_list,
               'prop': proposal,
               'prop_meta': proposal_meta,
               'sort': sort_type}

    return render(request, template, context)


def archive_thumbnails_query_ajax(request):
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

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """

    parameters = request.session.get("query_config", QUERY_CONFIG_TEMPLATE.copy())
    # Ensure the instrument is correctly capitalized
    instruments_list = []
    for instrument in parameters[QUERY_CONFIG_KEYS.INSTRUMENTS]:
        instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]
        instruments_list.append(instrument)

    # when parameters only contains nirspec as instrument, thumbnails still end up being all niriss data
    thumbnails = get_thumbnails_all_instruments(parameters)

    data = thumbnails_query_ajax(thumbnails)
    data['thumbnail_sort'] = request.session.get("image_sort", "Ascending")
    save_page_navigation_data(request, data)
    return JsonResponse(data, json_dumps_params={'indent': 2})


def dashboard(request):
    """Generate the dashbaord page

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
    filetype_bar = db.dashboard_filetype_bar_chart()
    table_columns, table_values = db.dashboard_monitor_tracking()
    grating_plot = db.dashboard_exposure_count_by_filter()
    anomaly_plot = db.dashboard_anomaly_per_instrument()

    plot = layout([[files_graph], [pie_graph, filetype_bar],
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
    all_jwql_tables = engine.table_names()

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
    sort_type = request.session.get('image_sort', 'Ascending')
    context = {'inst': '',
               'base_url': get_base_url(),
               'sort': sort_type
               }

    return render(request, template, context)


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


def explore_image(request, inst, file_root, filetype, rewrite=False):
    """Generate the header view page

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
    rewrite : bool, optional
        Regenerate if bokeh image already exists?

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
    image_info_list = get_image_info(file_root, rewrite)
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

    form = get_anomaly_form(request, inst, file_root)

    context = {'inst': inst,
               'file_root': file_root,
               'filetype': filetype,
               'extensions': extensions,
               'extension_groups': extension_groups,
               'extension_ints': extension_ints,
               'base_url': get_base_url(),
               'form': form}

    return render(request, template, context)


def explore_image_ajax(request, inst, file_root, filetype, scaling="log", low_lim=None, high_lim=None, ext_name="SCI", int1_nr=None, grp1_nr=None, int2_nr=None, grp2_nr=None, rewrite=False):
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
    scaling : str
        Scaling to implement in interactive preview image ("log" or "lin")
    low_lim : str
        Signal value to use as the lower limit of the displayed image. If "None", it will be calculated using the ZScale function
    high_lim : str
        Signal value to use as the upper limit of the displayed image. If "None", it will be calculated using the ZScale function
    ext_name : str
        Extension to implement in interactive preview image ("SCI", "DQ", "GROUPDQ", "PIXELDQ", "ERR"...)
    rewrite : bool, optional
        Regenerate if bokeh image already exists?

    Returns
    -------
    JsonResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    # Get image info containing all paths to fits files
    image_info_list = get_image_info(file_root, rewrite)

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

    int_preview_image = InteractivePreviewImg(full_fits_file, low_lim, high_lim, scaling, None, ext_name, group, integ)

    context = {'inst': "inst",
               'script': int_preview_image.script,
               'div': int_preview_image.div}

    return JsonResponse(context, json_dumps_params={'indent': 2})


def save_page_navigation_data(request, data):
    """
    It saves the data from the current page in the session so that the user can navigate to the next or
    previous page.  Our current sort options are Ascending/Descending, and Recent/Oldest so we need to
    preserve 'rootname' and 'expstart'.

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


def save_image_sort_ajax(request):

    # a string of the form " 'rootname1'='expstart1', 'rootname2'='expstart2', ..."
    image_sort = request.GET['sort_type']

    request.session['image_sort'] = image_sort
    context = {'item': request.session['image_sort']}
    return JsonResponse(context, json_dumps_params={'indent': 2})


def view_image(request, inst, file_root, rewrite=False):
    """Generate the image view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file_root : str
        FITS filename of selected image in filesystem
    rewrite : bool, optional
        Regenerate the jpg preview of `file` if it already exists?

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_image.html'
    image_info = get_image_info(file_root, rewrite)

    # Put suffixes in a consistent order. Check if any of the
    # suffixes are not in the list that specifies order.
    # Reorder the list of filenames to match the reordered list
    # of suffixes.
    suffixes = []
    all_files = []
    untracked_suffixes = deepcopy(image_info['suffixes'])
    untracked_files = deepcopy(image_info['all_files'])
    for poss_suffix in EXPOSURE_PAGE_SUFFIX_ORDER:
        if 'crf' not in poss_suffix:
            if poss_suffix in image_info['suffixes']:
                suffixes.append(poss_suffix)
                loc = image_info['suffixes'].index(poss_suffix)
                all_files.append(image_info['all_files'][loc])
                untracked_suffixes.remove(poss_suffix)
                untracked_files.remove(image_info['all_files'][loc])
        else:
            # EXPOSURE_PAGE_SUFFIX_ORDER contains crf and crfints, but the actual suffixes
            # in the data will be e.g. o001_crf, and there may be more than one crf file
            # in the list of suffixes. So in this case, we strip the e.g. o001 from the
            # suffixes and check which list elements match.
            suff_arr = np.array(image_info['suffixes'])
            files_arr = np.array(image_info['all_files'])
            splits = np.array([ele.split('_')[-1] for ele in image_info['suffixes']])
            if splits.size > 0:
                idxs = np.where(splits == poss_suffix)[0]
            else:
                idxs = []
            if len(idxs) > 0:
                suff_entries = list(suff_arr[idxs])
                file_entries = list(files_arr[idxs])
                suffixes.extend(suff_entries)
                all_files.extend(file_entries)

                untracked_splits = np.array([ele.split('_')[-1] for ele in untracked_suffixes])
                untracked_idxs = np.where(untracked_splits == poss_suffix)[0]
                untracked_suffixes = list(np.delete(untracked_suffixes, untracked_idxs))
                untracked_files = list(np.delete(untracked_files, untracked_idxs))

    # If the data contain any suffixes that are not in the list that specifies the order
    # to use, make a note in the log (so that they can be added to EXPOSURE_PAGE_SUFFIX_ORDER)
    # later. Then add them to the end of the suffixes list. Their order will be random since
    # they are not in EXPOSURE_PAGE_SUFFIX_ORDER.
    if len(untracked_suffixes) > 0:
        module = os.path.basename(__file__).strip('.py')
        start_time, log_file = monitor_utils.initialize_instrument_monitor(module)
        logging.warning((f'In view_image(), for {inst}, {file_root}, the following suffixes are present in the data, '
                         f'but not in EXPOSURE_PAGE_SUFFIX_ORDER in constants.py: {untracked_suffixes} '
                         'Please add them, so that they will appear in a consistent order on the webpage.'))
        suffixes.extend(untracked_suffixes)
        all_files.extend(untracked_files)

    form = get_anomaly_form(request, inst, file_root)

    prop_id = file_root[2:7]

    # if we get to this page without any navigation data (i.e. direct link), just use the file_root with no expstart time
    # navigate_data is dict of format rootname:expstart
    navigation_data = request.session.get('navigation_data', {file_root: 0})

    # For time based sorting options, sort to "Recent" first to create sorting consistency when times are the same.
    # This is consistent with how Tinysort is utilized in jwql.js->sort_by_thumbnails
    sort_type = request.session.get('image_sort', 'Ascending')
    if sort_type in ['Descending']:
        file_root_list = sorted(navigation_data, reverse=True)
    elif sort_type in ['Recent']:
        navigation_data = dict(sorted(navigation_data.items()))
        navigation_data = dict(sorted(navigation_data.items(), key=operator.itemgetter(1), reverse=True))
        file_root_list = list(navigation_data.keys())
    elif sort_type in ['Oldest']:
        navigation_data = dict(sorted(navigation_data.items()))
        navigation_data = dict(sorted(navigation_data.items(), key=operator.itemgetter(1)))
        file_root_list = list(navigation_data.keys())
    else:
        file_root_list = sorted(navigation_data)

    # Get our current views RootFileInfo model and send our "viewed/new" information
    root_file_info = RootFileInfo.objects.get(root_name=file_root)

    # Build the context
    context = {'base_url': get_base_url(),
               'file_root_list': file_root_list,
               'inst': inst,
               'prop_id': prop_id,
               'obsnum': file_root[7:10],
               'file_root': file_root,
               'jpg_files': image_info['all_jpegs'],
               'fits_files': all_files,
               'suffixes': suffixes,
               'num_ints': image_info['num_ints'],
               'available_ints': image_info['available_ints'],
               'total_ints': image_info['total_ints'],
               'form': form,
               'marked_viewed': root_file_info.viewed}

    return render(request, template, context)
