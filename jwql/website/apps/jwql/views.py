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
    placed in the ``jwql`` directory.
"""

import csv
import os

from bokeh.layouts import layout
from bokeh.embed import components
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from jwql.database.database_interface import load_connection
from jwql.utils import anomaly_query_config
from jwql.utils.interactive_preview_image import InteractivePreviewImg
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, MONITORS, URL_DICT
from jwql.utils.utils import filename_parser, filesystem_path, get_base_url, get_config, query_unformat

from .data_containers import build_table
from .data_containers import data_trending
from .data_containers import get_acknowledgements, get_instrument_proposals
from .data_containers import get_anomaly_form
from .data_containers import get_dashboard_components
from .data_containers import get_edb_components
from .data_containers import get_explorer_extension_names
from .data_containers import get_filenames_by_instrument, mast_query_filenames_by_instrument
from .data_containers import get_header_info
from .data_containers import get_image_info
from .data_containers import get_proposal_info
from .data_containers import get_rootnames_for_instrument_proposal
from .data_containers import get_thumbnails_all_instruments
from .data_containers import nirspec_trending
from .data_containers import random_404_page
from .data_containers import text_scrape
from .data_containers import thumbnails_ajax
from .data_containers import thumbnails_query_ajax
from .forms import AnomalyQueryForm
from .forms import FileSearchForm


def anomaly_query(request):
    """The anomaly query form page"""

    form = AnomalyQueryForm(request.POST or None)

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

            anomaly_query_config.INSTRUMENTS_CHOSEN = form.cleaned_data['instrument']
            anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES = all_anomalies
            anomaly_query_config.APERTURES_CHOSEN = all_apers
            anomaly_query_config.FILTERS_CHOSEN = all_filters
            anomaly_query_config.EXPTIME_MIN = str(form.cleaned_data['exp_time_min'])
            anomaly_query_config.EXPTIME_MAX = str(form.cleaned_data['exp_time_max'])
            anomaly_query_config.DETECTORS_CHOSEN = all_detectors
            anomaly_query_config.EXPTYPES_CHOSEN = all_exptypes
            anomaly_query_config.READPATTS_CHOSEN = all_readpatts
            anomaly_query_config.GRATINGS_CHOSEN = all_gratings

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
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]
    filesystem = get_config()['filesystem']

    # Dictionary to hold summary information for all proposals
    all_proposals = get_instrument_proposals(inst)
    all_proposal_info = {'num_proposals': 0,
                         'proposals': [],
                         'min_obsnum': [],
                         'thumbnail_paths': [],
                         'num_files': []}

    # Get list of all files for the given instrument
    for proposal in all_proposals:
        filename_query = mast_query_filenames_by_instrument(inst, proposal)
        filenames_public = get_filenames_by_instrument(inst, proposal, restriction='public', query_response=filename_query)
        filenames_proprietary = get_filenames_by_instrument(inst, proposal, restriction='proprietary', query_response=filename_query)

        # Determine locations to the files
        filenames = []
        for filename in filenames_public:
            try:
                relative_filepath = filesystem_path(filename, check_existence=False)
                full_filepath = os.path.join(filesystem, 'public', relative_filepath)
                filenames.append(full_filepath)
            except ValueError:
                print('Unable to determine filepath for {}'.format(filename))
        for filename in filenames_proprietary:
            try:
                relative_filepath = filesystem_path(filename, check_existence=False)
                full_filepath = os.path.join(filesystem, 'proprietary', relative_filepath)
                filenames.append(full_filepath)
            except ValueError:
                print('Unable to determine filepath for {}'.format(filename))

        # Get set of unique rootnames
        num_files = 0
        rootnames = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filenames])
        for rootname in rootnames:
            filename_dict = filename_parser(rootname)

            # Weed out file types that are not supported by generate_preview_images
            if 'stage_3' not in filename_dict['filename_type']:
                num_files += 1

        if len(filenames) > 0:
            # Gather information about the proposals for the given instrument
            proposal_info = get_proposal_info(filenames)
            all_proposal_info['num_proposals'] = all_proposal_info['num_proposals'] + 1
            all_proposal_info['proposals'].append(proposal)
            all_proposal_info['min_obsnum'].append(proposal_info['observation_nums'][0])
            all_proposal_info['thumbnail_paths'].append(proposal_info['thumbnail_paths'][0])
            all_proposal_info['num_files'].append(num_files)

    context = {'inst': inst,
               'num_proposals': all_proposal_info['num_proposals'],
               'min_obsnum': all_proposal_info['min_obsnum'],
               'thumbnails': {'proposals': all_proposal_info['proposals'],
                              'thumbnail_paths': all_proposal_info['thumbnail_paths'],
                              'num_files': all_proposal_info['num_files']}}

    print('in archived_proposals_ajax')
    print(all_proposal_info['min_obsnum'])

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

    template = 'thumbnails_per_obs.html'
    context = {'inst': inst,
               'prop': proposal,
               'obs': observation,
               'obs_list': obs_list,
               'prop_meta': proposal_meta,
               'base_url': get_base_url()}

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

    # Ensure the instrument is correctly capitalized
    instruments_list = []
    for instrument in anomaly_query_config.INSTRUMENTS_CHOSEN:
        instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]
        instruments_list.append(instrument)

    parameters = anomaly_query_config.PARAMETERS

    # when parameters only contains nirspec as instrument, thumbnails still end up being all niriss data
    thumbnails = get_thumbnails_all_instruments(parameters)

    anomaly_query_config.THUMBNAILS = thumbnails

    data = thumbnails_query_ajax(thumbnails)

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


def jwqldb_table_viewer(request):
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

    parameters = {}
    parameters['instruments'] = anomaly_query_config.INSTRUMENTS_CHOSEN
    parameters['apertures'] = anomaly_query_config.APERTURES_CHOSEN
    parameters['filters'] = anomaly_query_config.FILTERS_CHOSEN
    parameters['detectors'] = anomaly_query_config.DETECTORS_CHOSEN
    parameters['exposure_types'] = anomaly_query_config.EXPTYPES_CHOSEN
    parameters['read_patterns'] = anomaly_query_config.READPATTS_CHOSEN
    parameters['gratings'] = anomaly_query_config.GRATINGS_CHOSEN
    parameters['anomalies'] = anomaly_query_config.ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES

    anomaly_query_config.PARAMETERS = parameters

    context = {'inst': '',
               'base_url': get_base_url()
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

    # Get image info containing all paths to fits files
    image_info_list = get_image_info(file_root, rewrite)

    # get explorable extensions from header
    extensions = get_explorer_extension_names(file_root, filetype)

    # Save fits file name to use for bokeh image
    fits_file = file_root + '_' + filetype + '.fits'

    # Find index of our fits file
    fits_index = next(ix for ix, fits_path in enumerate(image_info_list['all_files']) if fits_file in fits_path)

    # TODO verify and create appropriate error handling

    form = get_anomaly_form(request, inst, file_root)

    context = {'inst': inst,
               'prop_id': file_root[2:7],
               'file_root': file_root,
               'filetype': filetype,
               'index': fits_index,
               'suffix': image_info_list['suffixes'][fits_index],
               'num_ints': image_info_list['num_ints'],
               'available_ints': image_info_list['available_ints'],
               'extensions': extensions,
               'base_url': get_base_url(),
               'form': form}

    return render(request, template, context)


def explore_image_ajax(request, inst, file_root, filetype, scaling="log", low_lim=None, high_lim=None, ext_name="SCI", rewrite=False):
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

    if low_lim is not None:
        low_lim = float(low_lim)
    if high_lim is not None:
        high_lim = float(high_lim)

    int_preview_image = InteractivePreviewImg(full_fits_file, low_lim, high_lim, scaling, None, ext_name)

    context = {'inst': "inst",
               'script': int_preview_image.script,
               'div': int_preview_image.div}

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

    form = get_anomaly_form(request, inst, file_root)

    # Build the context
    context = {'inst': inst,
               'prop_id': file_root[2:7],
               'obsnum': file_root[7:10],
               'file_root': file_root,
               'jpg_files': image_info['all_jpegs'],
               'fits_files': image_info['all_files'],
               'suffixes': image_info['suffixes'],
               'num_ints': image_info['num_ints'],
               'available_ints': image_info['available_ints'],
               'form': form}

    return render(request, template, context)
