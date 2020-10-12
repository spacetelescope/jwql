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

import os

from django.http import JsonResponse
from django.http import HttpRequest as request
from django.shortcuts import render
from django.shortcuts import redirect

from jwql.database.database_interface import load_connection
from jwql.utils.constants import MONITORS
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
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
from .forms import DynamicAnomalyForm
from .forms import FileSearchForm
from .oauth import auth_info, auth_required

from jwql.utils import anomaly_query_config

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


def dynamic_anomaly(request):
    """The anomaly query form page"""

    form = DynamicAnomalyForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            print("form.cleaned_data", form.cleaned_data)

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

            # all_apers = []
            # for instrument_apers in [miri_apers, nirspec_apers, niriss_apers, nircam_apers]:
            #     for aper in instrument_apers:
            #         all_apers.append(aper) if aper not in all_apers else all_apers

            # all_obsmodes = []
            # for instrument_obsmode in [miri_obsmode, nirspec_obsmode, niriss_obsmode, nircam_obsmode]:
            #     for obsmode in instrument_obsmode:
            #         all_obsmodes.append(obsmode) if obsmode not in all_obsmodes else all_obsmodes

            # all_anomalies = []
            # for instrument_anomalies in [miri_anomalies, nirspec_anomalies, niriss_anomalies, nircam_anomalies]:
            #     for anomaly in instrument_anomalies:
            #         all_anomalies.append(anomaly) if anomaly not in all_anomalies else all_anomalies

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
    template = 'dynamic_anomaly.html'

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


# @auth_required
def archived_proposals(request,       inst):  # user,
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


# @auth_required
def archived_proposals_ajax(request,      inst):   # user,
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


# @auth_required
def archive_thumbnails(request,      inst, proposal):  # user,
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


# @auth_required
def archive_thumbnails_ajax(request,       inst, proposal):  # user,
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


# @auth_required
def archive_thumbnails_query_ajax(request):  # ,       insts):  # user,
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
    insts_list = []
    for inst in anomaly_query_config.INSTRUMENTS_CHOSEN:
        inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]
        insts_list.append(inst)

    rootnames = anomaly_query_config.THUMBNAILS
    data = thumbnails_query_ajax(rootnames, insts_list)

    # return JsonResponse({'instrument_datasets': [nirspec_data, nircam_data]}, json_dumps_params={'indent': 2})
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
    url_dict = {'fgs': 'http://jwst-docs.stsci.edu/display/JTI/Fine+Guidance+Sensor%2C+FGS?q=fgs',
                'miri': 'http://jwst-docs.stsci.edu/display/JTI/Mid+Infrared+Instrument',
                'niriss': 'http://jwst-docs.stsci.edu/display/JTI/Near+Infrared+Imager+and+Slitless+Spectrograph',
                'nirspec': 'http://jwst-docs.stsci.edu/display/JTI/Near+Infrared+Spectrograph',
                'nircam': 'http://jwst-docs.stsci.edu/display/JTI/Near+Infrared+Camera'}

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

    table_view_components = get_jwqldb_table_view_components(request)

    session, base, engine, meta = load_connection(get_config()['connection_string'])
    all_jwql_tables = engine.table_names()

    template = 'jwqldb_table_viewer.html'
    context = {
        'inst': '',
        'all_jwql_tables': all_jwql_tables,
        'table_view_components': table_view_components}

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

    insts = anomaly_query_config.INSTRUMENTS_CHOSEN
    apers = anomaly_query_config.APERTURES_CHOSEN
    filts = anomaly_query_config.FILTERS_CHOSEN
    exptime_min = anomaly_query_config.EXPTIME_MIN
    exptime_max = anomaly_query_config.EXPTIME_MAX
    obs_modes = anomaly_query_config.OBSERVING_MODES_CHOSEN
    anomalies = anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES
    print("getting thumbnails")
    thumbnails = get_thumbnails_all_instruments(insts, apers, filts, 
                                                exptime_min, exptime_max, 
                                                obs_modes, anomalies)
    anomaly_query_config.THUMBNAILS = thumbnails

    # get information about thumbnails for thumbnail viewer
    proposal_info = get_proposal_info(thumbnails)

    context = {'inst': '',
               'anomalies_chosen_from_current_anomalies': 
                     anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES,
               'apertures_chosen': apers,
               'filters_chosen': filts,
               'inst_list_chosen': insts,
               'observing_modes_chosen': obs_modes,
               'thumbnails': thumbnails,
               'base_url': get_base_url(),
               'rootnames': thumbnails,
               'thumbnail_data':  {'inst': "Queried Anomalies",
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


# @auth_required
def view_image(request,       inst, file_root, rewrite=False):   # user,
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
            form.update_anomaly_table(file_root,          anomaly_choices)     #  user['ezid'],

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
