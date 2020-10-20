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
    placed in the ``jwql/utils/`` directory.
"""

import csv
import os

from django.http import JsonResponse
from django.http import HttpRequest as request
from django.shortcuts import render
from django.shortcuts import redirect

from jwql.database.database_interface import load_connection
from jwql.utils.constants import MONITORS
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_SHORTHAND
from jwql.utils.utils import get_base_url
from jwql.utils.utils import get_config
from jwql.utils.utils import query_unformat

from .data_containers import data_trending
from .data_containers import get_acknowledgements
from .data_containers import get_current_flagged_anomalies
from .data_containers import get_dashboard_components
from .data_containers import get_edb_components
from .data_containers import get_filenames_by_instrument
from .data_containers import get_header_info
from .data_containers import get_image_info
from .data_containers import get_proposal_info
from .data_containers import get_thumbnails_all_instruments
from .data_containers import nirspec_trending
from .data_containers import random_404_page
from .data_containers import get_jwqldb_table_view_components
from .data_containers import thumbnails_ajax
from .data_containers import thumbnails_query_ajax
from .forms import FGSAnomalySubmitForm
from .forms import MIRIAnomalySubmitForm
from .forms import NIRCamAnomalySubmitForm
from .forms import NIRISSAnomalySubmitForm
from .forms import NIRSpecAnomalySubmitForm
from .forms import AnomalyQueryForm
from .data_containers import build_table
from .forms import AnomalyForm
from .forms import FileSearchForm
from .oauth import auth_info, auth_required

from jwql.utils import anomaly_query_config

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


def anomaly_query(request):
    """The anomaly query form page"""

    form = AnomalyQueryForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            miri_filters = [query_unformat(i) for i in form.cleaned_data['miri_filt']]
            miri_apers = [query_unformat(i) for i in form.cleaned_data['miri_aper']]
            miri_obsmode = [query_unformat(i) for i in form.cleaned_data['miri_obsmode']]
            miri_anomalies = [query_unformat(i) for i in form.cleaned_data['miri_anomalies']]

            nirspec_filters = [query_unformat(i) for i in form.cleaned_data['nirspec_filt']]
            nirspec_apers = [query_unformat(i) for i in form.cleaned_data['nirspec_aper']]
            nirspec_obsmode = [query_unformat(i) for i in form.cleaned_data['nirspec_obsmode']]
            nirspec_anomalies = [query_unformat(i) for i in form.cleaned_data['nirspec_anomalies']]

            niriss_filters = [query_unformat(i) for i in form.cleaned_data['niriss_filt']]
            niriss_apers = [query_unformat(i) for i in form.cleaned_data['niriss_aper']]
            niriss_obsmode = [query_unformat(i) for i in form.cleaned_data['niriss_obsmode']]
            niriss_anomalies = [query_unformat(i) for i in form.cleaned_data['niriss_anomalies']]

            nircam_filters = [query_unformat(i) for i in form.cleaned_data['nircam_filt']]
            nircam_apers = [query_unformat(i) for i in form.cleaned_data['nircam_aper']]
            nircam_obsmode = [query_unformat(i) for i in form.cleaned_data['nircam_obsmode']]
            nircam_anomalies = [query_unformat(i) for i in form.cleaned_data['nircam_anomalies']]

            all_filters = {}
            all_filters['miri'] = miri_filters
            all_filters['nirspec'] = nirspec_filters
            all_filters['niriss'] = niriss_filters
            all_filters['nircam'] = nircam_filters

            all_apers = {}
            all_apers['miri'] = miri_apers
            all_apers['nirspec'] = nirspec_apers
            all_apers['niriss'] = niriss_apers
            all_apers['nircam'] = nircam_apers

            all_obsmodes = {}
            all_obsmodes['miri'] = miri_obsmode
            all_obsmodes['nirspec'] = nirspec_obsmode
            all_obsmodes['niriss'] = niriss_obsmode
            all_obsmodes['nircam'] = nircam_obsmode

            all_anomalies = {}
            all_anomalies['miri'] = miri_anomalies
            all_anomalies['nirspec'] = nirspec_anomalies
            all_anomalies['niriss'] = niriss_anomalies
            all_anomalies['nircam'] = nircam_anomalies

            anomaly_query_config.INSTRUMENTS_CHOSEN = form.cleaned_data['instrument']
            anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES = all_anomalies
            anomaly_query_config.APERTURES_CHOSEN = all_apers
            anomaly_query_config.FILTERS_CHOSEN = all_filters
            anomaly_query_config.EXPTIME_MIN = str(form.cleaned_data['exp_time_min'])
            anomaly_query_config.EXPTIME_MAX = str(form.cleaned_data['exp_time_max'])
            anomaly_query_config.OBSERVING_MODES_CHOSEN = all_obsmodes

            return redirect('/query_submit')

    context = {'form': form,
               'inst': ''}
    template = 'anomaly_query.html'

    return render(request, template, context)


def miri_data_trending(request):
    """Generate the ``MIRI DATA-TRENDING`` page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = "miri_data_trending.html"
    variables, dash = data_trending()

    context = {
        'dashboard': dash,
        'inst': '',  # Leave as empty string or instrument name; Required for navigation bar
        'inst_list': JWST_INSTRUMENT_NAMES_MIXEDCASE,  # Do not edit; Required for navigation bar
        'tools': MONITORS,  # Do not edit; Required for navigation bar
        'user': None  # Do not edit; Required for authentication
    }

    # append variables to context
    context.update(variables)

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


def nirspec_data_trending(request):
    """Generate the ``MIRI DATA-TRENDING`` page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    template = "nirspec_data_trending.html"
    variables, dash = nirspec_trending()

    context = {
        'dashboard': dash,
        'inst': '',  # Leave as empty string or instrument name; Required for navigation bar
        'inst_list': JWST_INSTRUMENT_NAMES_MIXEDCASE,  # Do not edit; Required for navigation bar
        'tools': MONITORS,  # Do not edit; Required for navigation bar
        'user': None  # Do not edit; Required for authentication
    }

    # append variables to context
    context.update(variables)

    # Return a HTTP response with the template and dictionary of variables
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


@auth_required
def archived_proposals(request, user, inst):
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


@auth_required
def archived_proposals_ajax(request, user, inst):
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

    # For each proposal, get the first available thumbnail and determine
    # how many files there are
    filepaths = get_filenames_by_instrument(inst)
    all_filenames = [os.path.basename(f) for f in filepaths]
    proposal_info = get_proposal_info(filepaths)

    context = {'inst': inst,
               'all_filenames': all_filenames,
               'num_proposals': proposal_info['num_proposals'],
               'thumbnails': {'proposals': proposal_info['proposals'],
                              'thumbnail_paths': proposal_info['thumbnail_paths'],
                              'num_files': proposal_info['num_files']}}

    return JsonResponse(context, json_dumps_params={'indent': 2})


@auth_required
def archive_thumbnails(request, user, inst, proposal):
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
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'thumbnails.html'
    context = {'inst': inst,
               'prop': proposal,
               'base_url': get_base_url()}

    return render(request, template, context)


@auth_required
def archive_thumbnails_ajax(request, user, inst, proposal):
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
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    data = thumbnails_ajax(inst, proposal)

    return JsonResponse(data, json_dumps_params={'indent': 2})


@auth_required
def archive_thumbnails_query_ajax(request, user):
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
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    instruments_list = []
    for instrument in anomaly_query_config.INSTRUMENTS_CHOSEN:
        instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]
        instruments_list.append(instrument)

    rootnames = anomaly_query_config.THUMBNAILS
    data = thumbnails_query_ajax(rootnames, instruments_list)

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
    output_dir = get_config()['outputs']
    dashboard_components, dashboard_html = get_dashboard_components()

    context = {'inst': '',
               'outputs': output_dir,
               'filesystem_html': os.path.join(output_dir, 'monitor_filesystem',
                                               'filesystem_monitor.html'),
               'dashboard_components': dashboard_components,
               'dashboard_html': dashboard_html}

    return render(request, template, context)


@auth_info
def engineering_database(request, user):
    """Generate the EDB page.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    user : dict
        A dictionary of user credentials.

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


def home(request):
    """Generate the home page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    user : dict
        A dictionary of user credentials.

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
    url_dict = {'fgs': 'https://jwst-docs.stsci.edu/jwst-observatory-hardware/fine-guidance-sensor',
                'miri': 'https://jwst-docs.stsci.edu/mid-infrared-instrument',
                'niriss': 'https://jwst-docs.stsci.edu/near-infrared-imager-and-slitless-spectrograph',
                'nirspec': 'https://jwst-docs.stsci.edu/near-infrared-spectrograph',
                'nircam': 'https://jwst-docs.stsci.edu/near-infrared-camera'}

    doc_url = url_dict[inst.lower()]

    context = {'inst': inst,
               'doc_url': doc_url}

    return render(request, template, context)


def jwqldb_table_viewer(request):
    """Generate the JWQL Table Viewer view.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    user : dict
        A dictionary of user credentials.

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    table_meta, tablename = get_jwqldb_table_view_components(request)
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


def export(request, tablename):
    import pandas as pd
    import csv
    from jwql.website.apps.jwql.data_containers import get_jwqldb_table_view_components

    table_meta = build_table(tablename)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(tablename)

    writer = csv.writer(response)
    writer.writerow(table_meta.columns.values)
    for _, row in table_meta.iterrows():
        writer.writerow(row.values)

    return response


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

    instruments = anomaly_query_config.INSTRUMENTS_CHOSEN
    apertures = anomaly_query_config.APERTURES_CHOSEN
    filters = anomaly_query_config.FILTERS_CHOSEN
    exposure_time_min = anomaly_query_config.EXPTIME_MIN
    exposure_time_max = anomaly_query_config.EXPTIME_MAX
    observing_modes = anomaly_query_config.OBSERVING_MODES_CHOSEN
    anomalies = anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES
    parameters = {}
    parameters['instruments'] = instruments
    parameters['apertures'] = apertures
    parameters['filters'] = filters
    parameters['observing_modes'] = observing_modes
    parameters['exposure_time_min'] = exposure_time_min
    parameters['exposure_time_max'] = exposure_time_max
    parameters['anomalies'] = anomalies
    thumbnails = get_thumbnails_all_instruments(parameters)
    anomaly_query_config.THUMBNAILS = thumbnails

    # get information about thumbnails for thumbnail viewer
    proposal_info = get_proposal_info(thumbnails)

    context = {'inst': '',
               'anomalies_chosen_from_current_anomalies':
                     anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES,
               'apertures_chosen': apertures,
               'filters_chosen': filters,
               'inst_list_chosen': instruments,
               'observing_modes_chosen': observing_modes,
               'thumbnails': thumbnails,
               'base_url': get_base_url(),
               'rootnames': thumbnails,
               'thumbnail_data': {'inst': "Queried Anomalies",
                                  'all_filenames': thumbnails,
                                  'num_proposals': proposal_info['num_proposals'],
                                  'thumbnails': {'proposals': proposal_info['proposals'],
                                                  'thumbnail_paths': proposal_info['thumbnail_paths'],
                                                  'num_files': proposal_info['num_files']}}
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


def view_header(request, inst, filename):
    """Generate the header view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    filename : str
        FITS filename of selected image in filesystem

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_header.html'
    file_root = '_'.join(filename.split('_')[:-1])

    context = {'inst': inst,
               'filename': filename,
               'file_root': file_root,
               'header_info': get_header_info(filename)}

    return render(request, template, context)


@auth_required
def view_image(request, user, inst, file_root, rewrite=False):
    """Generate the image view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    user : dict
        A dictionary of user credentials.
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

    # Determine current flagged anomalies
    current_anomalies = get_current_flagged_anomalies(file_root, inst)

    # Create a form instance
    if inst == 'FGS':
        form = FGSAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'MIRI':
        form = MIRIAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'NIRCam':
        form = NIRCamAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'NIRISS':
        form = NIRISSAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'NIRSpec':
        form = NIRSpecAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    # If this is a POST request, process the form data
    if request.method == 'POST':
        anomaly_choices = dict(request.POST)['anomaly_choices']
        if form.is_valid():
            form.update_anomaly_table(file_root, user['ezid'], anomaly_choices)

    # Build the context
    context = {'inst': inst,
               'prop_id': file_root[2:7],
               'file_root': file_root,
               'jpg_files': image_info['all_jpegs'],
               'fits_files': image_info['all_files'],
               'suffixes': image_info['suffixes'],
               'num_ints': image_info['num_ints'],
               'form': form}

    return render(request, template, context)


@auth_required
def view_all_images(request, user, file_root, rewrite=False):
    """Generate the image view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    user : dict
        A dictionary of user credentials.
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

    inst = JWST_INSTRUMENT_NAMES_SHORTHAND[file_root.split("_")[-1][:3]]

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_image.html'
    image_info = get_image_info(file_root, rewrite)

    # Determine current flagged anomalies
    current_anomalies = get_current_flagged_anomalies(file_root, inst)

    # Create a form instance
    if inst == 'FGS':
        form = FGSAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'MIRI':
        form = MIRIAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'NIRCam':
        form = NIRCamAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'NIRISS':
        form = NIRISSAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    if inst == 'NIRSpec':
        form = NIRSpecAnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})
    # If this is a POST request, process the form data
    if request.method == 'POST':
        anomaly_choices = dict(request.POST)['anomaly_choices']
        if form.is_valid():
            form.update_anomaly_table(file_root, user['ezid'], anomaly_choices)

    # Build the context
    context = {'inst': inst,
               'prop_id': file_root[2:7],
               'file_root': file_root,
               'jpg_files': image_info['all_jpegs'],
               'fits_files': image_info['all_files'],
               'suffixes': image_info['suffixes'],
               'num_ints': image_info['num_ints'],
               'form': form}

    return render(request, template, context)
