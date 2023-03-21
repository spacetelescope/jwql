#! /usr/bin/env python

"""This module monitors and gather statistics of the filesystem and
central storage area that hosts data for the ``jwql`` application.
This will answer questions such as the total number of files, how much
disk space is being used, and then plot these values over time.

Authors
-------

    - Misty Cracraft
    - Sara Ogaz
    - Matthew Bourque

Use
---

    This module is intended to be executed from the command line:
    ::

        python monitor_filesystem.py

    The user must have a ``config.json`` file in the ``jwql``
    directory with the following keys:
      - ``filesystem`` - The path to the filesystem
      - ``outputs`` - The path to where the output plots will be
                      written

Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``jwql`` directory.
"""

from collections import defaultdict
import datetime
import itertools
import logging
import os
import subprocess

from astroquery.mast import Mast, Observations
from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.palettes import Category20_20 as palette
from bokeh.plotting import figure, output_file, save
import numpy as np
from sqlalchemy.exc import DataError

from jwql.database.database_interface import engine
from jwql.database.database_interface import session
from jwql.database.database_interface import FilesystemGeneral
from jwql.database.database_interface import FilesystemInstrument
from jwql.database.database_interface import CentralStore
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.constants import FILESYSYEM_MONITOR_SUBDIRS, FILE_SUFFIX_TYPES, FILTERS_PER_INSTRUMENT, INSTRUMENT_SERVICE_MATCH
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import filename_parser
from jwql.utils.utils import get_config
from jwql.utils.monitor_utils import initialize_instrument_monitor, update_monitor_table
from jwql.utils.protect_module import lock_module
from jwql.website.apps.jwql.data_containers import get_instrument_proposals

SETTINGS = get_config()
FILESYSTEM = SETTINGS['filesystem']
PROPRIETARY_FILESYSTEM = os.path.join(FILESYSTEM, 'proprietary')
PUBLIC_FILESYSTEM = os.path.join(FILESYSTEM, 'public')
CENTRAL = SETTINGS['jwql_dir']
OUTPUTS = SETTINGS['outputs']
PREVIEW_IMAGES = SETTINGS['preview_image_filesystem']
THUMBNAILS = SETTINGS['thumbnail_filesystem']
LOGS = SETTINGS['log_dir']

def files_per_filter():
    """Querying MAST (rather than looping through the filesystem), determine how
    many files use each filter for each instrument. Note that thiw function takes
    a long time (~minutes per filter) to execute.

    Returns
    -------
    n_obs : dict
      Dictionary with filter names as keys, and values of the number of Observations that
      use that particular filter.
    """
    # Generate a list of filter/pupil pairs, to use as keys
    from astropy.table import unique, vstack
    n_files = {}
    for instrument in JWST_INSTRUMENT_NAMES:
        n_files[instrument] = {}
        for fname in FILTERS_PER_INSTRUMENT[instrument]:  # note that this does not include pupil wheel-based filters
            obs = Observations.query_criteria(filters=fname, instrument_name=JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument])
            batch_size = 5
            batches = [obs[i:i+batch_size] for i in range(0, len(obs), batch_size)]

            obs_table = [Observations.get_product_list(batch) for batch in batches]
            products = unique(vstack(obs_table), keys='productFilename')
            filtered_products = Observations.filter_products(products, productType=["SCIENCE"], productSubGroupDescription=['UNCAL'], extension="fits")

            n_files[instrument][fname] = obs
    return n_files


def gather_statistics(general_results_dict, instrument_results_dict):
    """Walks the filesytem to gather various statistics to eventually
    store in the database

    Parameters
    ----------
    general_results_dict : dict
        A dictionary for the ``filesystem_general`` database table
    instrument_results_dict : dict
        A dictionary for the ``filesystem_instrument`` database table

    Returns
    -------
    general_results_dict : dict
        A dictionary for the ``filesystem_general`` database table
    instrument_results_dict : dict
        A dictionary for the ``filesystem_instrument`` database table
    """

    logging.info('Gathering stats for filesystem')

    for filesystem_area in [PROPRIETARY_FILESYSTEM, PUBLIC_FILESYSTEM]:
        for dirpath, _, files in os.walk(filesystem_area):
            general_results_dict['total_file_count'] += len(files)
            for filename in files:

                file_path = os.path.join(dirpath, filename)
                if os.path.isfile(file_path):
                    general_results_dict['total_file_size'] += os.path.getsize(file_path)

                    if filename.endswith(".fits"):

                        # Parse out filename information
                        try:
                            filename_dict = filename_parser(filename)
                        except ValueError:
                            break

                        # For MSA files, which do not have traditional suffixes, set the
                        # suffix to "msa"
                        if 'suffix' not in filename_dict:
                            if filename_dict['filename_type'] == 'stage_2_msa':
                                filename_dict['suffix'] = 'msa'

                        try:
                            filetype = filename_dict['suffix']
                            instrument = filename_dict['instrument']
                        except KeyError:
                            logging.info(f'File {filename} skipped as it contains either no suffix or no instrument name from the filename parser.')
                            filetype = None
                            instrument = None

                        # Populate general stats
                        general_results_dict['fits_file_count'] += 1
                        general_results_dict['fits_file_size'] += os.path.getsize(file_path)

                        if filetype is not None:
                            # Populate instrument specific stats
                            if instrument not in instrument_results_dict:
                                instrument_results_dict[instrument] = {}
                            if filetype not in instrument_results_dict[instrument]:
                                instrument_results_dict[instrument][filetype] = {}
                                instrument_results_dict[instrument][filetype]['count'] = 0
                                instrument_results_dict[instrument][filetype]['size'] = 0
                            instrument_results_dict[instrument][filetype]['count'] += 1
                            instrument_results_dict[instrument][filetype]['size'] += os.path.getsize(file_path) / (2**40)

    # Convert file sizes to terabytes
    general_results_dict['total_file_size'] = general_results_dict['total_file_size'] / (2**40)
    general_results_dict['fits_file_size'] = general_results_dict['fits_file_size'] / (2**40)

    logging.info('\t{} fits files found in filesystem'.format(general_results_dict['fits_file_count']))

    return general_results_dict, instrument_results_dict


def get_global_filesystem_stats(general_results_dict):
    """Gathers ``used`` and ``available`` ``df``-style stats on the
    entire filesystem. (Not just directory titled filesystem.)

    Parameters
    ----------
    general_results_dict : dict
        A dictionary for the ``filesystem_general`` database table

    Returns
    -------
    general_results_dict : dict
        A dictionary for the ``filesystem_general`` database table
    """

    general_results_dict['used'] = 0.0
    general_results_dict['available'] = 0.0

    for filesystem_area in [PROPRIETARY_FILESYSTEM, PUBLIC_FILESYSTEM]:
        command = "df -k {}".format(filesystem_area)
        command += " | awk '{print $3, $4}' | tail -n 1"
        stats = subprocess.check_output(command, shell=True).split()
        general_results_dict['used'] += int(stats[0]) / (1024**3)
        general_results_dict['available'] += int(stats[1]) / (1024**3)

    return general_results_dict


def get_area_stats(central_storage_dict):
    """Gathers ``used`` and ``available`` ``df``-style stats on the
    selected area.

    Parameters
    ----------
    central_storage_dict : dict
        A dictionary for the ``central_storage`` database table

    Returns
    -------
    central_storage_dict : dict
        A dictionary for the ``central_storage`` database table
    """
    logging.info('Gathering stats for central storage area')

    areas = {'outputs': OUTPUTS,
             'logs': LOGS,
             'preview_images': PREVIEW_IMAGES,
             'thumbnails': THUMBNAILS,
             'all': CENTRAL}

    counteddirs = []

    sums = 0  # to be used to count 'all'
    for area in areas:

        used = 0
        # initialize area in dictionary
        if area not in central_storage_dict:
            central_storage_dict[area] = {}

        fullpath = areas[area]

        logging.info('\tSearching directory {}'.format(fullpath))
        counteddirs.append(fullpath)

        # to get df stats, use -k to get 1024 byte blocks
        command = "df -k {}".format(fullpath)
        command += " | awk '{print $2, $3, $4}' | tail -n 1"
        stats = subprocess.check_output(command, shell=True).split()
        # to put in TB, have to multiply values by 1024 to get in bytes, then
        # divide by 1024 ^ 4 to put in TB
        total = int(stats[0]) / (1024 ** 3)
        free = int(stats[2]) / (1024 ** 3)
        central_storage_dict[area]['size'] = total
        central_storage_dict[area]['available'] = free

        # do an os.walk on each directory to count up used space
        if area == 'all':
            # get listing of subdirectories
            subdirs = [f.path for f in os.scandir(fullpath) if f.is_dir()]
            for onedir in subdirs:
                if onedir not in counteddirs:
                    logging.info('\tSearching directory {}'.format(onedir))
                    for dirpath, _, files in os.walk(onedir):
                        for filename in files:
                            file_path = os.path.join(dirpath, filename)
                            # Check if file_path exists, if so, add to used space
                            exists = os.path.isfile(file_path)
                            if exists:
                                filesize = os.path.getsize(file_path)
                                sums += filesize
            use = sums / (1024 ** 4)
        else:
            for dirpath, _, files in os.walk(fullpath):
                for filename in files:
                    file_path = os.path.join(dirpath, filename)
                    # Check if file_path exists, if so, add to used space
                    exists = os.path.isfile(file_path)
                    if exists:
                        filesize = os.path.getsize(file_path)
                        used += filesize
                        sums += filesize
            use = used / (1024 ** 4)
        central_storage_dict[area]['used'] = use

    return central_storage_dict


def get_observation_characteristics():
    """Query MAST and count the number of observations that make use of each
    filter/pupil pair for each instrument.

    Returns
    -------
    n_obs : dict
        Nested dictionary with instrument names as the top level keys, and
        filter/pupil values as the second level keys. Values are the number of
        observations that use the filter/pupil value.
    """
    n_obs = {}
    for instrument in ['nircam', 'niriss', 'nirspec', 'miri']:  # Skip FGS here. It has no filters
        service = INSTRUMENT_SERVICE_MATCH[JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument]]
        n_obs[instrument] = {}

        # Get the list of proposal numbers for the given instrument
        proposal_list = get_instrument_proposals(instrument)

        # Different instruments hold the optical elements in different fields
        if instrument in ['nircam', 'niriss']:
            colval = "filter,pupil,observtn"
        elif instrument == 'nirspec':
            colval = "filter,grating,observtn"
        elif instrument == 'miri':
            colval = "filter,observtn"
        optics = colval.split(',')

        for proposal in proposal_list:
            filters = [{'paramName': 'program', "values": [proposal]}]
            columns = colval
            params = {"columns": columns, "filters": filters}
            response = Mast.service_request_async(service, params)
            result = response[0].json()
            result_array = np.array(result['data'])

            # Get a list of all the observation numbers within the proposal
            all_obs_nums = np.array([f'{entry["observtn"]}' for entry in result['data']])
            obs_nums = list(set(all_obs_nums))

            for obs_num in obs_nums:
                # Idenitfy which entries use the given obs_num
                match = np.where(all_obs_nums == obs_num)[0]

                # Generate a list of filter/pupil values used in the proposal. For MIRI,
                # just keep the filter name.
                if instrument != 'miri':
                    filter_pupils = sorted(list(set([f'{entry[optics[0]]}/{entry[optics[1]]}' for entry in result_array[match]])))
                else:
                    filter_pupils = sorted(list(set([f'{entry[optics[0]]}' for entry in result_array[match]])))

                # Increment dictionary values for the existing filter_pupil values
                for filter_pupil in filter_pupils:
                    if filter_pupil in n_obs[instrument]:
                        n_obs[instrument][filter_pupil] += 1
                    else:
                        n_obs[instrument][filter_pupil] = 1

        # Sort the filter/pupil list to make future plot more readable
        n_obs[instrument] = sorted(n_obs[instrument].items())
    return n_obs


def initialize_results_dicts():
    """Initializes dictionaries that will hold filesystem statistics

    Returns
    -------
    general_results_dict : dict
        A dictionary for the ``filesystem_general`` database table
    instrument_results_dict : dict
        A dictionary for the ``filesystem_instrument`` database table
    central_storage_dict : dict
        A dictionary for the ``central_storage`` database table
    """

    now = datetime.datetime.now()

    general_results_dict = {}
    general_results_dict['date'] = now
    general_results_dict['total_file_count'] = 0
    general_results_dict['fits_file_count'] = 0
    general_results_dict['total_file_size'] = 0
    general_results_dict['fits_file_size'] = 0

    instrument_results_dict = {}
    instrument_results_dict['date'] = now

    central_storage_dict = {}
    central_storage_dict['date'] = now

    return general_results_dict, instrument_results_dict, central_storage_dict


@log_fail
@log_info
def monitor_filesystem():
    """
    Tabulates the inventory of the JWST filesystem, saving statistics
    to database tables, and generates plots.
    """

    # Initialize dictionaries for database input
    general_results_dict, instrument_results_dict, central_storage_dict = initialize_results_dicts()

    # Walk through filesystem recursively to gather statistics
    general_results_dict, instrument_results_dict = gather_statistics(general_results_dict, instrument_results_dict)

    # Get df style stats on file system
    general_results_dict = get_global_filesystem_stats(general_results_dict)

    # Get stats on central storage areas
    central_storage_dict = get_area_stats(central_storage_dict)

    # Get stats on number of observations with particular characteristics
    characteristics = get_observation_characteristics()

    # Add data to database tables
    update_database(general_results_dict, instrument_results_dict, central_storage_dict)
    update_characteristics_database(characteristics)

    # Create the plots
    plot_filesystem_stats()


def plot_by_filetype(plot_type, instrument):
    """Plot ``count`` or ``size`` by filetype versus date for the given
    instrument, or all instruments.

    Parameters
    ----------
    plot_type : str
        Which data to plot.  Either ``count`` or ``size``.
    instrument : str
        The instrument to plot for.  Can be a valid JWST instrument or
        ``all`` to plot across all instruments.

    Returns
    -------
    plot : bokeh.plotting.figure.Figure object
        ``bokeh`` plot of total file counts versus date
    """

    # Determine plot title
    if instrument == 'all':
        title = 'Total File {} by Type'.format(plot_type.capitalize())
    else:
        instrument_title = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument]
        title = '{} Total File {} by Type'.format(instrument_title, plot_type.capitalize())

    if plot_type == 'count':
        ytitle = 'Counts'
    else:
        ytitle = 'Size (TB)'

    # Initialize plot
    plot = figure(
        tools='pan,box_zoom,wheel_zoom,reset,save',
        x_axis_type='datetime',
        title=title,
        x_axis_label='Date',
        y_axis_label=ytitle)
    colors = itertools.cycle(palette)

    for filetype, color in zip(FILE_SUFFIX_TYPES, colors):

        # Query for counts
        results = session.query(FilesystemInstrument.date, getattr(FilesystemInstrument, plot_type))\
            .filter(FilesystemInstrument.filetype == filetype)

        if instrument == 'all':
            results = results.all()
        else:
            results = results.filter(FilesystemInstrument.instrument == instrument).all()

        # Group by date
        if results:
            results_dict = defaultdict(int)
            for date, value in results:
                results_dict[date] += value

            # Parse results so they can be easily plotted
            dates = list(results_dict.keys())
            values = list(results_dict.values())

            # Plot the results
            plot.line(dates, values, legend='{} files'.format(filetype), line_color=color)
            plot.circle(dates, values, color=color)

    session.close()

    return plot


def plot_filesystem_size():
    """Plot filesystem sizes (size, used, available) versus date

    Returns
    -------
    plot : bokeh.plotting.figure.Figure object
        ``bokeh`` plot of total file counts versus date
    """

    # Plot system stats vs. date
    results = session.query(FilesystemGeneral.date, FilesystemGeneral.total_file_size,
                            FilesystemGeneral.used, FilesystemGeneral.available).all()
    dates, total_sizes, useds, availables = zip(*results)
    plot = figure(
        tools='pan,box_zoom,wheel_zoom,reset,save',
        x_axis_type='datetime',
        title='System stats',
        x_axis_label='Date',
        y_axis_label='Size TB')
    plot.line(dates, total_sizes, legend='Total size', line_color='red')
    plot.circle(dates, total_sizes, color='red')
    plot.line(dates, useds, legend='Used bytes', line_color='green')
    plot.circle(dates, useds, color='green')
    plot.line(dates, availables, legend='Free bytes', line_color='blue')
    plot.circle(dates, availables, color='blue')

    session.close()
    return plot


def plot_central_store_dirs():
    """Plot central store sizes (size, used, available) versus date

        Returns
        -------
        plot : bokeh.plotting.figure.Figure object
            ``bokeh`` plot of total directory size versus date
        """

    # Plot system stats vs. date
    results = session.query(CentralStore.date, CentralStore.size, CentralStore.available).all()

    # Initialize plot
    dates, total_sizes, availables = zip(*results)
    plot = figure(
        tools='pan,box_zoom,wheel_zoom,reset,save',
        x_axis_type='datetime',
        title='Central Store stats',
        x_axis_label='Date',
        y_axis_label='Size TB')
    colors = itertools.cycle(palette)

    plot.line(dates, total_sizes, legend='Total size', line_color='red')
    plot.circle(dates, total_sizes, color='red')
    plot.line(dates, availables, legend='Free', line_color='blue')
    plot.circle(dates, availables, color='blue')

    # This part of the plot should cycle through areas and plot area used values vs. date
    for area, color in zip(FILESYSYEM_MONITOR_SUBDIRS, colors):

        # Query for used sizes
        results = session.query(CentralStore.date, CentralStore.used).filter(CentralStore.area == area)

        # Group by date
        if results:
            results_dict = defaultdict(int)
            for date, value in results:
                results_dict[date] += value

            # Parse results so they can be easily plotted
            dates = list(results_dict.keys())
            values = list(results_dict.values())

            # Plot the results
            plot.line(dates, values, legend='{} files'.format(area), line_color=color)
            plot.circle(dates, values, color=color)

    session.close()

    return plot


def plot_filesystem_stats():
    """
    Plot various filesystem statistics using ``bokeh`` and save them to
    the output directory.
    """
    logging.info('Creating results plots')

    p1 = plot_total_file_counts()
    p2 = plot_filesystem_size()
    p3 = plot_by_filetype('count', 'all')
    p4 = plot_by_filetype('size', 'all')
    p5 = plot_central_store_dirs()
    plot_list = [p1, p2, p3, p4, p5]

    for instrument in JWST_INSTRUMENT_NAMES:
        plot_list.append(plot_by_filetype('count', instrument))
        plot_list.append(plot_by_filetype('size', instrument))

    # Create a layout with a grid pattern
    grid_chunks = [plot_list[i:i + 2] for i in range(0, len(plot_list), 2)]
    grid = gridplot(grid_chunks)

    # Save all of the plots in one file
    outputs_dir = os.path.join(OUTPUTS, 'monitor_filesystem')
    outfile = os.path.join(outputs_dir, 'filesystem_monitor.html')
    output_file(outfile)
    save(grid)
    set_permissions(outfile)
    logging.info('\tSaved plot of all statistics to {}'.format(outfile))

    # Save each plot's components
    for plot in plot_list:
        plot_name = plot.title.text.lower().replace(' ', '_')
        plot.sizing_mode = 'stretch_both'
        script, div = components(plot)

        div_outfile = os.path.join(outputs_dir, "{}_component.html".format(plot_name))
        with open(div_outfile, 'w') as f:
            f.write(div)
            f.close()
        set_permissions(div_outfile)

        script_outfile = os.path.join(outputs_dir, "{}_component.js".format(plot_name))
        with open(script_outfile, 'w') as f:
            f.write(script)
            f.close()
        set_permissions(script_outfile)

        logging.info('\tSaved components files: {}_component.html and {}_component.js'.format(plot_name, plot_name))


def plot_total_file_counts():
    """Plot total file counts versus date

    Returns
    -------
    plot : bokeh.plotting.figure.Figure object
        ``bokeh`` plot of total file counts versus date
    """

    # Total file counts vs. date
    results = session.query(FilesystemGeneral.date, FilesystemGeneral.total_file_count).all()
    dates, file_counts = zip(*results)
    plot = figure(
        tools='pan,box_zoom,reset,wheel_zoom,save',
        x_axis_type='datetime',
        title="Total File Counts",
        x_axis_label='Date',
        y_axis_label='Count')
    plot.line(dates, file_counts, line_width=2, line_color='blue')
    plot.circle(dates, file_counts, color='blue')

    session.close()

    return plot


def update_characteristics_database(char_info):
    """Updates the ``filesystem_characteristics`` database table.

    Parameters
    ----------
    char_info : dict
        A nested dictionary of characteristic information. Top level keys are
        instrument names, and second level keys are filter/pupil strings.
    """
    logging.info('\tUpdating the characteristics database')
    now = datetime.datetime.now()

    # Add data to filesystem_instrument table
    for instrument in ['nircam', 'niriss', 'nirspec', 'miri']:
        filter_list = [e[0] for e in char_info['nircam']]
        value_list= [e[1] for e in char_info['nircam']]
        new_record = {}
        new_record['date'] = now
        new_record['instrument'] = instrument
        new_record['filter_pupil'] = filter_list
        new_record['obs_per_filter_pupil'] = value_list
        engine.execute(FilesystemCharacteristics.__table__.insert(), new_record)
        session.commit()

    session.close()


def update_database(general_results_dict, instrument_results_dict, central_storage_dict):
    """Updates the ``filesystem_general`` and ``filesystem_instrument``
    database tables.

    Parameters
    ----------
    general_results_dict : dict
        A dictionary for the ``filesystem_general`` database table
    instrument_results_dict : dict
        A dictionary for the ``filesystem_instrument`` database table
    central_storage_dict : dict
        A dictionary for the ``central_storage`` database table

    """
    logging.info('\tUpdating the database')

    engine.execute(FilesystemGeneral.__table__.insert(), general_results_dict)
    session.commit()

    # Add data to filesystem_instrument table
    for instrument in JWST_INSTRUMENT_NAMES:
        for filetype in instrument_results_dict[instrument]:
            new_record = {}
            new_record['date'] = instrument_results_dict['date']
            new_record['instrument'] = instrument
            new_record['filetype'] = filetype
            new_record['count'] = instrument_results_dict[instrument][filetype]['count']
            new_record['size'] = instrument_results_dict[instrument][filetype]['size']

            # Protect against updated enum options that have not been propagated to
            # the table definition
            try:
                engine.execute(FilesystemInstrument.__table__.insert(), new_record)
                session.commit()
            except DataError as e:
                logging.error(e)

    # Add data to central_storage table
    for area in FILESYSYEM_MONITOR_SUBDIRS:
        new_record = {}
        new_record['date'] = central_storage_dict['date']
        new_record['area'] = area
        new_record['size'] = central_storage_dict[area]['size']
        new_record['used'] = central_storage_dict[area]['used']
        new_record['available'] = central_storage_dict[area]['available']
        engine.execute(CentralStore.__table__.insert(), new_record)
        session.commit()

    session.close()


@lock_module
def protected_code():
    """Protected code ensures only 1 instance of module will run at any given time"""

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor_filesystem()
    update_monitor_table(module, start_time, log_file)


if __name__ == '__main__':
    protected_code()
