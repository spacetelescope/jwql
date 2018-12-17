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

Use
---

    This module is called in ``urls.py`` as such:
    ::

        from django.urls import path
        from . import views
        urlpatterns = [path('web/path/to/view/', views.view_name, name='view_name')]

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

from django.shortcuts import render

from .data_containers import get_acknowledgements
from .data_containers import get_dashboard_components
from .data_containers import get_filenames_by_instrument
from .data_containers import get_header_info
from .data_containers import get_image_info
from .data_containers import get_proposal_info
from .data_containers import thumbnails
from .forms import FileSearchForm
from jwql.utils.utils import get_config, JWST_INSTRUMENTS, MONITORS


FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


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
               'inst': '',
               'inst_list': JWST_INSTRUMENTS,
               'tools': MONITORS}

    return render(request, template, context)


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

    template = 'archive.html'

    # For each proposal, get the first available thumbnail and determine
    # how many files there are
    filepaths = get_filenames_by_instrument(inst)
    all_filenames = [os.path.basename(f) for f in filepaths]
    proposal_info = get_proposal_info(filepaths)

    context = {'inst': inst,
               'all_filenames': all_filenames,
               'tools': MONITORS,
               'num_proposals': proposal_info['num_proposals'],
               'zipped_thumbnails': zip(proposal_info['proposals'],
                                        proposal_info['thumbnail_paths'],
                                        proposal_info['num_files'])}

    return render(request, template, context)


def archive_thumbnails(request, inst, proposal):
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
    template = 'thumbnails.html'
    context = thumbnails(inst, proposal)

    return render(request, template, context)


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
               'inst_list': JWST_INSTRUMENTS,
               'tools': MONITORS,
               'outputs': output_dir,
               'filesystem_html': os.path.join(output_dir, 'monitor_filesystem', 'filesystem_monitor.html'),
               'dashboard_components': dashboard_components,
               'dashboard_html': dashboard_html}

    return render(request, template, context)


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
               'inst_list': JWST_INSTRUMENTS,
               'tools': MONITORS,
               'form': form}

    return render(request, template, context)


def instrument(request, inst):
    """Generate the instrument tool index page

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
    template = 'instrument.html'
    url_dict = {'FGS': 'http://jwst-docs.stsci.edu/display/JTI/Fine+Guidance+Sensor%2C+FGS?q=fgs',
                'MIRI': 'http://jwst-docs.stsci.edu/display/JTI/Mid-Infrared+Instrument%2C+MIRI',
                'NIRISS': 'http://jwst-docs.stsci.edu/display/JTI/Near+Infrared+Imager+and+Slitless+Spectrograph',
                'NIRSpec': 'http://jwst-docs.stsci.edu/display/JTI/Near+Infrared+Spectrograph',
                'NIRCam': 'http://jwst-docs.stsci.edu/display/JTI/Near+Infrared+Camera'}

    doc_url = url_dict[inst]

    context = {'inst': inst,
                'tools': MONITORS,
                'doc_url': doc_url}

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
    template = 'thumbnails.html'
    context = thumbnails(inst)

    return render(request, template, context)


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
    template = 'view_header.html'
    header = get_header_info(file)
    file_root = '_'.join(file.split('_')[:-1])

    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': MONITORS,
                   'header': header,
                   'file_root': file_root})


def view_image(request, inst, file_root, rewrite=False):
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
    template = 'view_image.html'
    image_info = get_image_info(file_root, rewrite)
    context = {'inst': inst,
               'file_root': file_root,
               'tools': MONITORS,
               'jpg_files': image_info['all_jpegs'],
               'fits_files': image_info['all_files'],
               'suffixes': image_info['suffixes'],
               'num_ints': image_info['num_ints']}

    return render(request, template, context)
