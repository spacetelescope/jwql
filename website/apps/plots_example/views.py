"""Defines the views for the JWQL web app.

In Django, "a view function, or view for short, is simply a Python
function that takes a Web request and returns a Web response" (from
Django documentation). This module defines all of the views that are
used to generate the various webpages used for the Quicklook project.
For example, these views can list the tools available to users, query
the JWQL database, and display images and headers.

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
    placed in jwql/utils/ directory.

"""

import os

from astropy.io import fits
from django.shortcuts import render
# from django.views import generic # We ultimately might want to use generic views?

from jwql.preview_image.preview_image import PreviewImage
from jwql.utils.utils import get_config

from .db import DatabaseConnection

FILESYSTEM_DIR = get_config()['filesystem']
INST_LIST = ['FGS', 'MIRI', 'NIRCam', 'NIRISS', 'NIRSpec']
TOOLS = {'FGS': ['Bad Pixel Monitor'],
         'MIRI': ['Dark Current Monitor',
                  'Bad Pixel Monitor', 'Cosmic Ray Monitor', 'Photometry Monitor',
                  'TA Failure Monitor', 'Blind Pointing Accuracy Monitor',
                  'Filter and Calibration Lamp Monitor', 'Thermal Emission Monitor'],
         'NIRCam': ['Bias Monitor',
                    'Readnoise Monitor', 'Gain Level Monitor',
                    'Mean Dark Current Rate Monitor', 'Photometric Stability Monitor'],
         'NIRISS': ['Bad Pixel Monitor',
                    'Readnoise Monitor', 'AMI Calibrator Monitor', 'TSO RMS Monitor'],
         'NIRSpec': ['Optical Short Monitor', 'Target Acquisition Monitor',
                     'Detector Health Monitor', 'Ref Pix Monitor',
                     'Internal Lamp Monitor', 'Instrument Model Updates',
                     'Failed-open Shutter Monitor']}

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
    template = 'plots_example/home.html'
    context = {'inst_list': INST_LIST,
               'tools': TOOLS}

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
    template = 'plots_example/instrument.html'

    return render(request, template,
                  {'inst': inst,
                   'tools': TOOLS})

def view_image(request, inst, file, rewrite=False):
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
    template = 'plots_example/view_image.html'

    # Generate the jpg filename
    dirname = file[:7]
    jpg_filename = os.path.splitext(file)[0] + '_integ0.jpg'
    jpg_filepath = os.path.join(FILESYSTEM_DIR, dirname, jpg_filename)

    # Check that a jpg does not already exist. If it does (and rewrite=False),
    # just call the existing jpg file
    if os.path.exists(jpg_filepath) and not rewrite:
        pass

    # If it doesn't, make it using the preview_image module
    else:
        fits_filepath = os.path.join(FILESYSTEM_DIR, dirname, file)

        # Only process FITS files that are 3D+ (preview_image can't handle 2D)
        # if any([end in fits_filepath for end in ['rate.fits', 'cal.fits', 'i2d.fits']]):
        #     jpg_filename = 'Cannot currently create JPEG preview for 2-dimensional FITS files.'
        # else:
        im = PreviewImage(fits_filepath, 'SCI')
        im.make_image()

    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': TOOLS,
                   'jpg': jpg_filename})

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
    template = 'plots_example/view_header.html'

    dirname = file[:7]
    fits_filepath = os.path.join(FILESYSTEM_DIR, dirname, file)

    header = fits.getheader(fits_filepath, ext=0).tostring(sep='\n')

    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': TOOLS,
                   'header': header})

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
    template = 'plots_example/unlooked.html'
    filepaths, filenames = DatabaseConnection('MAST', instrument=inst).\
        get_files_for_instrument(inst)

    return render(request, template,
                  {'inst': inst,
                   'imdat': filenames,
                   'tools': TOOLS})
