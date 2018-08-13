"""Defines the views for the ``jwql`` web app.

In Django, "a view function, or view for short, is simply a Python
function that takes a Web request and returns a Web response" (from
Django documentation). This module defines all of the views that are
used to generate the various webpages used for the Quicklook project.
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
        urlpatterns = [path('web/path/to/view/',
                             views.view_name, name='view_name')]

References
----------
For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/views/

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql/utils/`` directory.
"""

from collections import OrderedDict
import glob
import os
import time

from astropy.io import fits
from django.shortcuts import render
import numpy as np
# from django.views import generic # We ultimately might want to use generic views?

from .data_containers import get_acknowledgements
from .data_containers import get_dashboard_components
from .data_containers import get_filenames_by_instrument
from .data_containers import get_proposal_info
from .data_containers import thumbnails
from jwql.preview_image.preview_image import PreviewImage
from jwql.utils.utils import get_config, JWST_INSTRUMENTS, filename_parser, MONITORS


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

    return render(request, template,
        {'inst': inst,
         'all_filenames': all_filenames,
         'tools': MONITORS,
         'num_proposals': proposal_info['num_proposals'],
         'zipped_thumbnails': zip(proposal_info['proposals'],
                                  proposal_info['thumbnail_paths'],
                                  proposal_info['num_files'])})


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
    dict_to_render = thumbnails(inst, proposal)

    return render(request, template, dict_to_render)


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
    dashboard_components = get_dashboard_components()

    context = {'inst': '',
               'inst_list': JWST_INSTRUMENTS,
               'tools': MONITORS,
               'outputs': output_dir,
               'filesystem_html': os.path.join(output_dir, 'filesystem_monitor', 'filesystem_monitor.html'),
               'dashboard_components': dashboard_components}

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
    template = 'home.html'
    context = {'inst': '',
               'inst_list': JWST_INSTRUMENTS,
               'tools': MONITORS}

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

    return render(request, template,
                  {'inst': inst,
                   'tools': MONITORS})


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
    preview_dir = os.path.join(get_config()['jwql_dir'], 'preview_images')

    # Find all of the matching files
    dirname = file_root[:7]
    search_filepath = os.path.join(FILESYSTEM_DIR, dirname, file_root + '*.fits')
    all_files = glob.glob(search_filepath)

    # Generate the jpg filename
    all_jpgs = []
    suffixes = []
    n_ints = {}
    for file in all_files:
        suffix = os.path.basename(file).split('_')[4].split('.')[0]
        suffixes.append(suffix)

        jpg_dir = os.path.join(preview_dir, dirname)
        jpg_filename = os.path.basename(os.path.splitext(file)[0] + '_integ0.jpg')
        jpg_filepath = os.path.join(jpg_dir, jpg_filename)

        # Check that a jpg does not already exist. If it does (and rewrite=False),
        # just call the existing jpg file
        if os.path.exists(jpg_filepath) and not rewrite:
            pass

        # If it doesn't, make it using the preview_image module
        else:
            if not os.path.exists(jpg_dir):
                os.makedirs(jpg_dir)
            im = PreviewImage(file, 'SCI')
            im.output_directory = jpg_dir
            im.make_image()

        # Record how many integrations there are per filetype
        search_jpgs = os.path.join(preview_dir, dirname, file_root + '_{}_integ*.jpg'.format(suffix))
        n_jpgs = len(glob.glob(search_jpgs))
        n_ints[suffix] = n_jpgs

        all_jpgs.append(jpg_filepath)

    return render(request, template,
                  {'inst': inst,
                   'file_root': file_root,
                   'tools': MONITORS,
                   'jpg_files': all_jpgs,
                   'fits_files': all_files,
                   'suffixes': suffixes,
                   'n_ints': n_ints})


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

    dirname = file[:7]
    fits_filepath = os.path.join(FILESYSTEM_DIR, dirname, file)

    header = fits.getheader(fits_filepath, ext=0).tostring(sep='\n')

    file_root = '_'.join(file.split('_')[:-1])

    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': MONITORS,
                   'header': header,
                   'file_root': file_root})


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
    dict_to_render = thumbnails(inst)
    return render(request, template,
                  dict_to_render)
