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
    - Bryan Hilbert

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

from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.constants import FILESYSTEM_MONITOR_SUBDIRS, FILE_SUFFIX_TYPES, FILTERS_PER_INSTRUMENT, INSTRUMENT_SERVICE_MATCH
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.utils import filename_parser
from jwql.utils.utils import get_config
from jwql.utils.monitor_utils import initialize_instrument_monitor, update_monitor_table
from jwql.utils.protect_module import lock_module
from jwql.website.apps.jwql.data_containers import get_instrument_proposals

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # Need to set up django apps before we can access the models
    import django  # noqa: E402 (module level import not at top of file)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()

    # Import * is okay here because this module specifically only contains database models
    # for this monitor
    from jwql.website.apps.jwql.monitor_models.common import *  # noqa: E402 (module level import not at top of file)

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
            batches = [obs[i:i + batch_size] for i in range(0, len(obs), batch_size)]

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
                        filename_dict = filename_parser(filename)
                        if filename_dict['recognized_filename']:
                            filename_type = filename_dict['filename_type']
                        else:
                            logging.warning((f'While running gather_statistics() on the filesystem {filename}, '
                                             'caused filename_parser() to fail.'))
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
        Dictionary with instrument names as the top level keys, and lists of 2-tuples
        as values. Each tuple contains filter/pupil string and the number of
        observations that use that filter/pupil.
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
    update_central_store_database(central_storage_dict)


def update_central_store_database(central_storage_dict):
    """Updates the ``CentralStore`` database table with info on disk space

    Parameters
    ----------
    central_storage_dict : dict
        A dictionary for the ``central_storage`` database table
    """
    for area in FILESYSTEM_MONITOR_SUBDIRS:
        new_record = {}
        new_record['date'] = central_storage_dict['date']
        new_record['area'] = area
        new_record['size'] = central_storage_dict[area]['size']
        new_record['used'] = central_storage_dict[area]['used']
        new_record['available'] = central_storage_dict[area]['available']

        entry = CentralStorage(**new_record)
        entry.save()


def update_characteristics_database(char_info):
    """Updates the ``filesystem_characteristics`` database table.

    Parameters
    ----------
    char_info : dict
        A dictionary of characteristic information. Keys are
        instrument names, and values are lists of tuples. Each tuple is
        composed of a filter/pupil string and a count for the number of observations
        using that filter/pupil.
    """
    logging.info('\tUpdating the characteristics database')
    now = datetime.datetime.now()

    # Add data to filesystem_instrument table
    for instrument in ['nircam', 'niriss', 'nirspec', 'miri']:
        optics = [e[0] for e in char_info[instrument]]
        values = [e[1] for e in char_info[instrument]]
        new_record = {}
        new_record['date'] = now
        new_record['instrument'] = instrument
        new_record['filter_pupil'] = optics
        new_record['obs_per_filter_pupil'] = values

        entry = FilesystemCharacteristics(**new_record)
        entry.save()


def update_database(general_results_dict, instrument_results_dict, central_storage_dict):
    """Updates the ``filesystem_general`` and ``filesystem_instrument``
    database tables.

    Parameters
    ----------
    general_results_dict : dict
        A dictionary for the ``filesystem_general`` database table
    instrument_results_dict : dict
        A dictionary for the ``filesystem_instrument`` database table
    """
    logging.info('\tUpdating the database')

    fs_general_entry = FilesystemGeneral(**general_results_dict)
    fs_general_entry.save()

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
            fs_instrument_entry = FilesystemInstrument(**new_record)
            fs_instrument_entry.save()


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
