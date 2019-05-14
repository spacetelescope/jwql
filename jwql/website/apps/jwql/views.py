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
from django.shortcuts import render

from .data_containers import get_acknowledgements, get_edb_components
from .data_containers import get_dashboard_components
from .data_containers import get_filenames_by_instrument
from .data_containers import get_header_info
from .data_containers import get_image_info
from .data_containers import get_proposal_info
from .data_containers import random_404_page
from .data_containers import thumbnails
from .data_containers import thumbnails_ajax
from .data_containers import data_trending
from .data_containers import nirspec_trending
from .forms import FileSearchForm
from .oauth import auth_info, auth_required
import jwql
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, MONITORS, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_base_url, get_config

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

    #append variables to context
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


def not_found(request):
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


def view_header(request, inst, file):
    """Generate the header view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file : str
        FITS filename of selected image in filesystem

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    template = 'view_header.html'
    header = get_header_info(file)
    file_root = '_'.join(file.split('_')[:-1])

    context = {'inst': inst,
               'file': file,
               'header': header,
               'file_root': file_root}

    return render(request, template, context)


@auth_required
def view_image(request, user, inst, file_root, rewrite=False):
    """Generate the image view page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file : str
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
    context = {'inst': inst,
               'file_root': file_root,
               'jpg_files': image_info['all_jpegs'],
               'fits_files': image_info['all_files'],
               'suffixes': image_info['suffixes'],
               'num_ints': image_info['num_ints']}

    return render(request, template, context)
