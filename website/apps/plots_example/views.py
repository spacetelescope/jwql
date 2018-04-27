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
import glob

from astropy.io import fits
from django.shortcuts import render
import numpy as np
# from django.views import generic # We ultimately might want to use generic views?

from jwql.preview_image.preview_image import PreviewImage
from jwql.utils.utils import get_config, filename_parser

from .db import DatabaseConnection

FILESYSTEM_DIR = get_config()['filesystem']
PREVIEW_DIR = get_config()['preview_image_dir']
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
    context = {'inst': '',
               'inst_list': INST_LIST,
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
    template = 'plots_example/view_image.html'

    # Find all of the matching files
    dirname = file_root[:7]
    search_filepath = os.path.join(FILESYSTEM_DIR, dirname, file_root + '*.fits')
    all_files = glob.glob(search_filepath)

    # Generate the jpg filename
    all_jpgs = []
    suffixes = []
    for file in all_files:
        suffix = os.path.basename(file).split('_')[4].split('.')[0]
        suffixes.append(suffix)

        jpg_dir = os.path.join(PREVIEW_DIR, dirname)
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

        all_jpgs.append(jpg_filepath)

    return render(request, template,
                  {'inst': inst,
                   'file_root': file_root,
                   'tools': TOOLS,
                   'jpg_files': all_jpgs,
                   'fits_files': all_files,
                   'suffixes': suffixes})

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

    file_root = '_'.join(file.split('_')[:-1])

    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': TOOLS,
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
    template = 'plots_example/unlooked.html'

    # Query files from MAST database
    # filepaths, filenames = DatabaseConnection('MAST', instrument=inst).\
    #     get_files_for_instrument(inst)

    # Find all of the matching files in filesytem
    # (TEMPORARY WHILE THE MAST STUFF IS BEING WORKED OUT)
    instrument_match = {'FGS': 'guider',
                        'MIRI': 'mir',
                        'NIRCam': 'nrc',
                        'NIRISS': 'nis',
                        'NIRSpec': 'nrs'}
    search_filepath = os.path.join(FILESYSTEM_DIR, '*', '*.fits')
    all_filepaths = [f for f in glob.glob(search_filepath) if instrument_match[inst] in f]

    # Determine file ID (everything except suffix)
    full_ids = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in all_filepaths])

    # Group files by ID
    file_data = []
    detectors = []
    proposals = []
    for i, file_id in enumerate(full_ids):
        suffixes = []
        count = 0
        for file in all_filepaths:
            if '_'.join(file.split('/')[-1].split('_')[:-1]) == file_id:
                count += 1

                # Parse filename
                file_dict = filename_parser(file)

                # Determine suffix
                suffix = file_dict['suffix']
                suffixes.append(suffix)

                hdr = fits.getheader(file, ext=0)
                exp_start = hdr['EXPSTART']

        suffixes = list(set(suffixes))

        # Add parameters to sort by
        if file_dict['detector'] not in detectors and \
           not file_dict['detector'].startswith('f'):
            detectors.append(file_dict['detector'])
        if file_dict['program_id'] not in proposals:
            proposals.append(file_dict['program_id'])

        file_dict['exp_start'] = exp_start
        file_dict['suffixes'] = suffixes
        file_dict['file_count'] = count
        file_dict['file_root'] = file_id

        file_data.append(file_dict)
    file_indices = np.arange(len(file_data))

    # Extract information for sorting with dropdown menus
    dropdown_menus = {'detector': detectors,
                      'proposal': proposals}

    return render(request, template,
                  {'inst': inst,
                   'all_filenames': [os.path.basename(f) for f in all_filepaths],
                   'tools': TOOLS,
                   'thumbnail_zipped_list': zip(file_indices, file_data),
                   'dropdown_menus': dropdown_menus,
                   'n_fileids': len(file_data)})
