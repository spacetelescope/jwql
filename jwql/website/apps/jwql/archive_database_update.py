"""Script that can be used to query MAST and return basic info
about all proposals. This information is used to help populate
the instrument archive pages

Authors
-------

    - Bryan Hilbert

Use
---

    This module is called as such:
    ::

        from jwql.websites.apps.jwql.archvie_database_update import get_updates
        instrument = 'nircam'
        get_updates(insturument)

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
from jwql.utils.utils import filename_parser, filesystem_path, get_base_url, get_config, get_rootnames_for_instrument_proposal, query_unformat

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
from .data_containers import get_thumbnails_all_instruments
from .data_containers import nirspec_trending
from .data_containers import random_404_page
from .data_containers import text_scrape
from .data_containers import thumbnails_ajax
from .data_containers import thumbnails_query_ajax
from .forms import AnomalyQueryForm
from .forms import FileSearchForm
from astropy.io import fits


def get_updates(inst):
    """Generate the page listing all archived proposals in the database

    Parameters
    ----------
    inst : str
        Name of JWST instrument

    Returns
    -------

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

    # Dictionary to hold summary observation of exp_types
    exp_types = {}

    # Get list of all files for the given instrument
    for proposal in all_proposals:
        # Get lists of all public and proprietary files for the program
        filenames_public, metadata_public, filenames_proprietary, metadata_proprietary = get_all_possible_filenames_for_proposal(inst, proposal)

        # Find the location in the filesystem for all files
        filepaths_public = files_in_filesystem(filenames_public, 'public')
        filepaths_proprietary = files_in_filesystem(filenames_proprietary, 'proprietary')
        filenames = filepaths_public + filepaths_proprietary

        # Get set of unique rootnames
        num_files = 0
        rootnames = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filenames])
        for rootname in rootnames:
            filename_dict = filename_parser(rootname)

            # Weed out file types that are not supported by generate_preview_images
            if 'stage_3' not in filename_dict['filename_type']:
                num_files += 1

        exp_types[str(proposal)] = {}
        if len(filenames) > 0:

            # Gather information about the proposals for the given instrument
            proposal_info = get_proposal_info(filenames)

            # Each observation number in each proposal will have a list of exp_types
            for obsnum in proposal_info['observation_nums']:
                match_pub = metadata_public['observtn'] == int(obsnum)
                exps_for_obs = list(set(metadata_public['observtn'][match_pub]))
                match_prop = metadata_proprietary['observtn'] == int(obsnum)
                exps_for_obs = list(set(exps_for_obs + metadata_proprietary['observtn'][match_prop]))
                exp_types[str(proposal)][obsnum] = exps_for_obs

                # Update the appropriate database table
                update_database_table(inst, proposal, obsnum, proposal_info['thumbnail_paths'][0], num_files, exp_types)


def get_all_possible_filenames_for_proposal(instrument, proposal_num):
    """
    """
    filename_query = mast_query_filenames_by_instrument(instrument, proposal_num, other_columns=['exp_type', 'observtn'])
    public, public_meta = get_filenames_by_instrument(instrument, proposal_num, restriction='public',
                                                      query_response=filename_query,  other_columns=['exp_type', 'observtn'])
    proprietary, proprietary_meta = get_filenames_by_instrument(instrument, proposal_num, restriction='proprietary',
                                                                query_response=filename_query,  other_columns=['exp_type', 'observtn'])
    return public, public_meta, proprietary, proprietary_meta


def files_in_filesystem(files, permission_type):
    """Determine locations in the filesystem for the input files

    Parameters
    ----------
    files : list
        List of filenames from MAST query

    permission_type : str
        Permission level of the input files: 'public' or 'proprietary'

    Return
    ------
    filenames : list
        List of full paths within the filesystem for the input files
    """
    if permission_type not in ['public', 'proprietary']:
        raise ValueError('permission type needs to be either "public" or "proprietary"')

    filenames = []
    for filename in files:
        try:
            relative_filepath = filesystem_path(filename, check_existence=False)
            full_filepath = os.path.join(filesystem, permission_type, relative_filepath)
            filenames.append(full_filepath)
        except ValueError:
            print('Unable to determine filepath for {}'.format(filename))
    return filenames


def update_database_table(instrument, prop, obs, thumbnail, files, types):
    """
    """
    logging.info('')
    inst_table = eval(f'{instrument}Archive')

    db_entries = session.query(inst_table) \
            .filter(inst_table.proposal == prop) \
            .filter(inst_table.obsnum == obs) \
            .all()

    num_found = len(db_entries)
    if num_found == 0:
        db_entries = None
    else:
        raise ValueError(f'Expecting a single database entry for proposal: {proposal}, obsnum {obsnum}, but found {len(db_entries)}')

    if db_entries is not None:
        db_entires.date = datetime.today()
        db_entries.thumbnail_path = thumbnail
        db_entries.num_files = files
        db_entries.exp_types = types
        session.commit()
    else:
        # If the proposal/obsnum combination is not in the database, add a
        # new entry
        entry = {'proposal': prop,
                 'obsnum': obs,
                 'thumbnail_path': thumbnail,
                 'num_files': files,
                 'exp_types': types
                 }
        inst_table.__table__.insert().execute(entry)

    session.close()


if __name__ == '__main__':
    instruments = ['nircam', 'miri', 'nirspec', 'niriss', 'fgs']
    for instrument in instruments:
        get_updates(instrument)
