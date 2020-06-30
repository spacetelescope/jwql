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
# from django import forms
from django.shortcuts import render

from jwql.database.database_interface import load_connection
from jwql.utils.constants import ANOMALIES_PER_INSTRUMENT
from jwql.utils.constants import FILTERS_PER_INSTRUMENT
from jwql.utils.constants import FULL_FRAME_APERTURES
from jwql.utils.constants import JWST_INSTRUMENT_NAMES
from jwql.utils.constants import MONITORS
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.constants import OBSERVING_MODE_PER_INSTRUMENT
from jwql.utils.utils import get_base_url
from jwql.utils.utils import get_config

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
from .forms import AnomalyForm
from .forms import AnomalySubmitForm
from .forms import ApertureForm
from .forms import EarlyDateForm
from .forms import ExptimeMaxForm
from .forms import ExptimeMinForm
from .forms import FileSearchForm
from .forms import FiletypeForm
from .forms import FilterForm
from .forms import InstrumentForm
from .forms import LateDateForm
from .forms import ObservingModeForm
from .oauth import auth_info, auth_required

# from jwql.utils.anomaly_query_config import APERTURES_CHOSEN, CURRENT_ANOMALIES
# from jwql.utils.anomaly_query_config import INSTRUMENTS_CHOSEN, OBSERVING_MODES_CHOSEN
# from jwql.utils.anomaly_query_config import ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES
from jwql.utils import anomaly_query_config

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


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


def query_anomaly(request):
    """Generate the anomaly query form page.

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

    exposure_min_form = ExptimeMinForm(request.POST or None)
    exposure_max_form = ExptimeMaxForm(request.POST or None)
    instrument_form = InstrumentForm(request.POST or None)
    early_date_form = EarlyDateForm(request.POST or None)
    late_date_form = LateDateForm(request.POST or None)

    # global current_anomalies
    current_anomalies = ['cosmic_ray_shower', 'diffraction_spike', 'excessive_saturation',
                         'guidestar_failure', 'persistence', 'other']

    # global instruments_chosen
    instruments_chosen = "No instruments chosen"
    if request.method == 'POST':
        if instrument_form.is_valid():
            instruments_chosen = instrument_form.clean_instruments()

            for anomaly in ANOMALIES_PER_INSTRUMENT:
                for inst in instruments_chosen:
                    if inst in ANOMALIES_PER_INSTRUMENT[anomaly]:
                        current_anomalies.append(anomaly) if anomaly not in current_anomalies else current_anomalies

    anomaly_query_config.INSTRUMENTS_CHOSEN = instruments_chosen
    anomaly_query_config.CURRENT_ANOMALIES = current_anomalies

    template = 'query_anomaly.html'
    context = {'inst': '',
               'exposure_min_form': exposure_min_form,
               'exposure_max_form': exposure_max_form,
               'instrument_form': instrument_form,
               'early_date_form': early_date_form,
               'late_date_form': late_date_form,
               'requested_insts': anomaly_query_config.INSTRUMENTS_CHOSEN,
               'current_anomalies': anomaly_query_config.CURRENT_ANOMALIES,
               'None': "No instruments chosen"}

    return render(request, template, context)


def query_anomaly_2(request):
    """Generate the second page of the anomaly query form.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    initial_aperture_list = []
    for instrument in FULL_FRAME_APERTURES.keys():
        if instrument.lower() in anomaly_query_config.INSTRUMENTS_CHOSEN:
            for aperture in FULL_FRAME_APERTURES[instrument]:
                initial_aperture_list.append(aperture)

    initial_mode_list = []
    for instrument in OBSERVING_MODE_PER_INSTRUMENT.keys():
        if instrument in anomaly_query_config.INSTRUMENTS_CHOSEN:
            for mode in OBSERVING_MODE_PER_INSTRUMENT[instrument]:
                initial_mode_list.append(mode)

    initial_filter_list = []
    for instrument in FILTERS_PER_INSTRUMENT.keys():
        if instrument in anomaly_query_config.INSTRUMENTS_CHOSEN:
            for filter in FILTERS_PER_INSTRUMENT[instrument]:
                initial_filter_list.append(filter)

    aperture_form = ApertureForm(request.POST or None, initial={'aperture': initial_aperture_list})
    filter_form = FilterForm(request.POST or None, initial={'filter': initial_filter_list})
    filetype_form = FiletypeForm(request.POST or None)
    observing_mode_form = ObservingModeForm(request.POST or None, initial={'mode': initial_mode_list})

    # Saving one form currently removes initial choices of other forms on the page
    # global apertures_chosen
    apertures_chosen = "No apertures chosen"
    if request.method == 'POST':
        if aperture_form.is_valid():
            apertures_chosen = aperture_form.clean_apertures()
            initial_aperture_list = apertures_chosen
    anomaly_query_config.APERTURES_CHOSEN = apertures_chosen

    # global filters_chosen
    filters_chosen = "No filters chosen"
    if request.method == 'POST':
        if filter_form.is_valid():
            filters_chosen = filter_form.clean_filters()
            initial_filter_list = filters_chosen
    anomaly_query_config.FILTERS_CHOSEN = filters_chosen

    # global observing_modes_chosen
    observing_modes_chosen = "No observing modes chosen"
    if request.method == 'POST':
        if observing_mode_form.is_valid():
            observing_modes_chosen = observing_mode_form.clean_modes()
            initial_mode_list = observing_modes_chosen
    anomaly_query_config.OBSERVING_MODES_CHOSEN = observing_modes_chosen

    # if current_anomalies == None:
    #     print("PLEASE START AT THE FIRST PAGE IN THE FORMS! (eg, <SERVER ADDRESS>/query_anomaly/ ")

    template = 'query_anomaly_2.html'
    context = {'inst': '',
               'aperture_form': aperture_form,
               'filter_form': filter_form,
               'filetype_form': filetype_form,
               'observing_mode_form': observing_mode_form,
               'apertures_chosen': anomaly_query_config.APERTURES_CHOSEN,
               'current_anomalies': anomaly_query_config.CURRENT_ANOMALIES,
               'filters_chosen': anomaly_query_config.FILTERS_CHOSEN,
               'instruments_chosen_cfg': anomaly_query_config.INSTRUMENTS_CHOSEN,
               'observing_modes_chosen': anomaly_query_config.OBSERVING_MODES_CHOSEN
               }

    return render(request, template, context)


def query_anomaly_3(request):
    """Generate the second page of the anomaly query form.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    anomaly_form = AnomalyForm(request.POST or None, initial={'query': anomaly_query_config.CURRENT_ANOMALIES})

    # if current_anomalies == None:
    #     print("PLEASE START AT THE FIRST PAGE IN THE FORMS! (eg, <SERVER ADDRESS>/query_anomaly/ ")
    # global anomalies_chosen_from_current_anomalies
    anomalies_chosen_from_current_anomalies = anomaly_query_config.CURRENT_ANOMALIES
    if request.method == 'POST':
        if anomaly_form.is_valid():
            anomalies_chosen_from_current_anomalies = anomaly_form.clean_anomalies()
    anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES = anomalies_chosen_from_current_anomalies

    template = 'query_anomaly_3.html'
    context = {'inst': '',
               'anomaly_form': anomaly_form,
               'chosen_current_anomalies': anomalies_chosen_from_current_anomalies
               }

    return render(request, template, context)


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

    # if current_anomalies == None:
    #     print("PLEASE START AT THE FIRST PAGE IN THE FORMS! (eg, <SERVER ADDRESS>/query_anomaly/ ")

    template = 'query_submit.html'
    # inst_list_chosen = ["NIRSpec", "NIRCam"]

    # print(get_thumbnails_all_instruments(inst_list_chosen))

    context = {'inst': '',
               'anomalies_chosen_from_current_anomalies': anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES,
               'apertures_chosen': anomaly_query_config.APERTURES_CHOSEN,
               'current_anomalies': anomaly_query_config.CURRENT_ANOMALIES,
               'filters_chosen': anomaly_query_config.FILTERS_CHOSEN,
               'inst_list_chosen': anomaly_query_config.INSTRUMENTS_CHOSEN,
               'observing_modes_chosen': anomaly_query_config.OBSERVING_MODES_CHOSEN
               # 'thumbnails': get_thumbnails_all_instruments(inst_list_chosen)
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
    form = AnomalySubmitForm(request.POST or None, initial={'anomaly_choices': current_anomalies})

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
