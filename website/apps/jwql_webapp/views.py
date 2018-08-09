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
    template = 'jwql_webapp/about.html'
    context = {'inst': '',
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
    template = 'jwql_webapp/archive.html'
    thumbnail_dir = os.path.join(get_config()['jwql_dir'], 'thumbnails')

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

    # Determine proposal ID, e.g. 00327
    proposals = list(set([f.split('/')[-1][2:7] for f in all_filepaths]))

    # For each proposal, get the first available thumbnail and determine
    # how many files there are
    thumbnails = []
    num_files = []
    for proposal in proposals:
        thumbnail_search_filepath = os.path.join(thumbnail_dir, 'jw{}'.format(proposal), 'jw{}*rate*.thumb'.format(proposal))
        thumbnail = glob.glob(thumbnail_search_filepath)
        if len(thumbnail) > 0:
            thumbnail = thumbnail[0]
            thumbnail = '/'.join(thumbnail.split('/')[-2:])
        thumbnails.append(thumbnail)

        fits_search_filepath = os.path.join(FILESYSTEM_DIR, 'jw{}'.format(proposal), 'jw{}*.fits'.format(proposal))
        num_files.append(len(glob.glob(fits_search_filepath)))

    return render(request, template,
        {'inst': inst,
         'all_filenames': [os.path.basename(f) for f in all_filepaths],
         'tools': MONITORS,
         'num_proposals': len(proposals),
         'zipped_thumbnails': zip(proposals, thumbnails, num_files)})


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
    template = 'jwql_webapp/thumbnails.html'
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
    template = 'jwql_webapp/dashboard.html'
    output_dir = get_config()['outputs']

    name_dict = {'': '',
                 'database_monitor': 'Database Monitor',
                 'filesystem_monitor': 'Filesystem Monitor',
                 'filecount_type': 'Total File Counts by Type',
                 'size_type': 'Total File Sizes by Type',
                 'filecount': 'Total File Counts',
                 'system_stats': 'System Statistics'}

    embed_components = {}
    for dir_name, subdir_list, file_list in os.walk(output_dir):
        monitor_name = os.path.basename(dir_name)
        embed_components[name_dict[monitor_name]] = {}
        for fname in file_list:
            if 'component' in fname:
                full_fname = '{}/{}'.format(monitor_name, fname)
                plot_name = fname.split('_component')[0]

                # Get the div
                html_file = full_fname.split('.')[0] + '.html'
                with open(os.path.join(output_dir, html_file)) as f:
                    div = f.read()

                # Get the script
                js_file = full_fname.split('.')[0] + '.js'
                with open(os.path.join(output_dir, js_file)) as f:
                    script = f.read()
                embed_components[name_dict[monitor_name]][name_dict[plot_name]] = [div, script]

    context = {'inst': '',
               'inst_list': JWST_INSTRUMENTS,
               'tools': MONITORS,
               'outputs': output_dir,
               'filesystem_html': os.path.join(output_dir, 'filesystem_monitor', 'filesystem_monitor.html'),
               'embed_components': embed_components}

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
    template = 'jwql_webapp/home.html'
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
    template = 'jwql_webapp/instrument.html'

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
    template = 'jwql_webapp/view_image.html'
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
    template = 'jwql_webapp/view_header.html'

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
    template = 'jwql_webapp/thumbnails.html'
    dict_to_render = thumbnails(inst)
    return render(request, template,
                  dict_to_render)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# HELPER FUNCTIONS
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def split_files(file_list, type):
    """JUST FOR USE DURING DEVELOPMENT WITH FILESYSTEM

    Splits the files in the filesystem into "unlooked" and "archived",
    with the "unlooked" images being the most recent 10% of files.
    """
    exp_times = []
    for file in file_list:
        hdr = fits.getheader(file, ext=0)
        exp_start = hdr['EXPSTART']
        exp_times.append(exp_start)

    exp_times_sorted = sorted(exp_times)
    i_cutoff = int(len(exp_times) * .1)
    t_cutoff = exp_times_sorted[i_cutoff]

    mask_unlooked = np.array([t < t_cutoff for t in exp_times])

    if type == 'unlooked':
        print('ONLY RETURNING {} "UNLOOKED" FILES OF {} ORIGINAL FILES'.format(len([m for m in mask_unlooked if m]), len(file_list)))
        return [f for i, f in enumerate(file_list) if mask_unlooked[i]]
    elif type == 'archive':
        print('ONLY RETURNING {} "ARCHIVED" FILES OF {} ORIGINAL FILES'.format(len([m for m in mask_unlooked if not m]), len(file_list)))
        return [f for i, f in enumerate(file_list) if not mask_unlooked[i]]


def thumbnails(inst, proposal=None):
    """Generate a page showing thumbnail images corresponding to
    activities, from a given ``proposal``

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    proposal : str (optional)
        Number of APT proposal to filter

    Returns
    -------
    dict_to_render : dict
        Dictionary of parameters for the thumbnails
    """

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

    # JUST FOR DEVELOPMENT
    # Split files into "archived" and "unlooked"
    if proposal is not None:
        page_type = 'archive'
    else:
        page_type = 'unlooked'
    all_filepaths = split_files(all_filepaths, page_type)

    # Determine file ID (everything except suffix)
    # e.g. jw00327001001_02101_00002_nrca1
    full_ids = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in all_filepaths])

    # If the proposal is specified (i.e. if the page being loaded is
    # an archive page), only collect data for given proposal
    if proposal is not None:
        full_ids = [f for f in full_ids if f[2:7] == proposal]

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
                try:
                    file_dict = filename_parser(file)
                except ValueError:
                    # Temporary workaround for noncompliant files in filesystem
                    file_dict = {'activity': file_id[17:19],
                                 'detector': file_id[26:],
                                 'exposure_id': file_id[20:25],
                                 'observation': file_id[7:10],
                                 'parallel_seq_id': file_id[16],
                                 'program_id': file_id[2:7],
                                 'suffix': file.split('/')[-1].split('.')[0].split('_')[-1],
                                 'visit': file_id[10:13],
                                 'visit_group': file_id[14:16]}

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
    # (Don't include the proposal as a sorting parameter if the
    # proposal has already been specified)
    if proposal is not None:
        dropdown_menus = {'detector': detectors}
    else:
        dropdown_menus = {'detector': detectors,
                          'proposal': proposals}

    dict_to_render = {'inst': inst,
                      'all_filenames': [os.path.basename(f) for f in all_filepaths],
                      'tools': MONITORS,
                      'thumbnail_zipped_list': zip(file_indices, file_data),
                      'dropdown_menus': dropdown_menus,
                      'n_fileids': len(file_data),
                      'prop': proposal}
    return dict_to_render

