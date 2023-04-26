#! /usr/bin/env python

"""Script that can be used to query MAST and return basic info
about all proposals. This information is used to help populate
the instrument archive pages

Authors
-------

    - Bryan Hilbert
    - Bradley Sappington

Use
---

    This module is called as follows:
    ::

        from jwql.websites.apps.jwql.archvie_database_update import get_updates
        instrument = 'nircam'
        get_updates(insturument)

        can be run from command line to add new elements to the django database
        $ python archive_database_update.py

        Use the '--fill_empty' argument to provide a model and field.  Updates ALL fields for any model with empty/null/0 specified field
        $ python archive_database_update.py --fill_empty rootfileinfo expstart
        WARNING: Not all fields will be populated by all model objects. This will result in updates that may not be necessary.
                 While this will not disturb the data, it has the potential to increase run time.  
                 Select the field that is most pertient to the models you need updated minimize run time

        Use the 'update' argument to update every rootfileinfo data model with the most complete information from MAST
        $ python archive_database_update.py --update
        WARNING: THIS WILL TAKE A LONG TIME


Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql`` directory.
"""

import logging
import os
import argparse

import numpy as np
import django

from django.apps import apps
from jwql.utils.protect_module import lock_module

# These lines are needed in order to use the Django models in a standalone
# script (as opposed to code run as a result of a webpage request). If these
# lines are not run, the script will crash when attempting to import the
# Django models in the line below.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
django.setup()

from jwql.website.apps.jwql.models import Archive, Observation, Proposal, RootFileInfo  # noqa
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE  # noqa
from jwql.utils.logging_functions import log_info, log_fail  # noqa
from jwql.utils.monitor_utils import initialize_instrument_monitor  # noqa
from jwql.utils.constants import MAST_QUERY_LIMIT  # noqa
from jwql.utils.utils import filename_parser, filesystem_path, get_config  # noqa
from jwql.website.apps.jwql.data_containers import create_archived_proposals_context  # noqa
from jwql.website.apps.jwql.data_containers import get_instrument_proposals, get_filenames_by_instrument  # noqa
from jwql.website.apps.jwql.data_containers import get_proposal_info, mast_query_filenames_by_instrument, mast_query_by_rootname  # noqa

FILESYSTEM = get_config()['filesystem']


@log_info
@log_fail
def get_updates(update_database):
    """Generate the page listing all archived proposals in the database

    Parameters
    ----------
    update_database : bool
        true: run updates on existing rootfilename entries
        false: only create new entries

    inst : str
        Name of JWST instrument
    """
    instruments = ['nircam', 'miri', 'nirspec', 'niriss', 'fgs']
    for inst in instruments:
        logging.info(f'Updating database for {inst} archive page.')

        # Ensure the instrument is correctly capitalized
        inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

        # Dictionary to hold summary information for all proposals
        all_proposals = get_instrument_proposals(inst)

        # Get list of all files for the given instrument
        for proposal in all_proposals:
            # Get lists of all public and proprietary files for the program
            filenames_public, metadata_public, filenames_proprietary, metadata_proprietary = get_all_possible_filenames_for_proposal(inst, proposal)
            # Find the location in the filesystem for all files
            filepaths_public = files_in_filesystem(filenames_public, 'public')
            filepaths_proprietary = files_in_filesystem(filenames_proprietary, 'proprietary')
            filenames = filepaths_public + filepaths_proprietary

            # There is one and only one category for the proposal, so just take the first.
            proposal_category = ''
            if len(metadata_public['category']):
                proposal_category = metadata_public['category'][0]
            elif len(metadata_proprietary['category']):
                proposal_category = metadata_proprietary['category'][0]

            # Get set of unique rootnames
            all_rootnames = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filenames])
            rootnames = []
            for rootname in all_rootnames:
                filename_dict = filename_parser(rootname)

                # Weed out file types that are not supported by generate_preview_images
                if 'stage_3' not in filename_dict['filename_type']:
                    rootnames.append(rootname)

            if len(filenames) > 0:

                # Gather information about the proposals for the given instrument
                proposal_info = get_proposal_info(filenames)

                # Each observation number in each proposal can have a list of exp_types (e.g. NRC_TACQ, NRC_IMAGE)
                for obsnum in set(proposal_info['observation_nums']):
                    # Find the public entries for the observation and get the associated exp_types
                    public_obs = np.array(metadata_public['observtn'])
                    match_pub = public_obs == int(obsnum)
                    public_exptypes = np.array(metadata_public['exp_type'])
                    exp_types = list(set(public_exptypes[match_pub]))

                    # Find the proprietary entries for the observation, get the associated exp_types, and
                    # combine with the public values
                    prop_obs = np.array(metadata_proprietary['observtn'])
                    match_prop = prop_obs == int(obsnum)
                    prop_exptypes = np.array(metadata_proprietary['exp_type'])
                    exp_types = list(set(exp_types + list(set(prop_exptypes[match_prop]))))

                    # Find the starting and ending dates for the observation
                    all_start_dates = np.array(metadata_public['expstart'])[match_pub]
                    all_start_dates = np.append(all_start_dates, np.array(metadata_proprietary['expstart'])[match_prop])

                    starting_date = np.min(all_start_dates)
                    all_end_dates = np.array(metadata_public['expend'])[match_pub]
                    all_end_dates = np.append(all_end_dates, np.array(metadata_proprietary['expend'])[match_prop])
                    latest_date = np.max(all_end_dates)

                    # Get the number of files in the observation
                    propobs = f'jw{int(proposal):05}{obsnum}'
                    obsfiles = [f for f in rootnames if propobs in f]

                    # Update the appropriate database table
                    update_database_table(update_database, inst, proposal, obsnum, proposal_info['thumbnail_paths'][0], obsfiles,
                                          exp_types, starting_date, latest_date, proposal_category)

        create_archived_proposals_context(inst)


def get_all_possible_filenames_for_proposal(instrument, proposal_num):
    """Wrapper around a MAST query for filenames from a given instrument/proposal

    Parameters
    ----------
    instrument : str
        JWST instrument, mixed-case e.g. NIRCam

    proposal_num : str
        Proposal number to search for

    Returns
    -------
    public: list
        A list of publicly-available filenames

    public_meta : dict
        Dictionary of other attributes returned from MAST for public data. Keys are the attribute names
        e.g. 'exptime', and values are lists of the value for each filename. e.g. ['59867.6, 59867.601']

    proprietary list
        A list of filenames from proprietary programs

    proprietary_meta : dict
        Dictionary of other attributes returned from MAST for proporietary programs. Keys are the attribute names
        e.g. 'exptime', and values are lists of the value for each filename. e.g. ['59867.6, 59867.601']
    """
    filename_query = mast_query_filenames_by_instrument(instrument, proposal_num,
                                                        other_columns=['exp_type', 'observtn', 'expstart', 'expend', 'category'])

    # Check the number of files returned by the MAST query. MAST has a limit of 50,000 rows in
    # the returned result. If we hit that limit, then we are most likely not getting back all of
    # the files. In such a case, we will have to start querying by observation or some other property.
    if len(filename_query['data']) >= MAST_QUERY_LIMIT:
        raise ValueError((f'WARNING! MAST query limit of {MAST_QUERY_LIMIT} entries has been reached for {instrument} PID {proposal_num}. '
                          'This means we are not getting a complete list of files. The query must be broken up into multuple queries.'))

    public, public_meta = get_filenames_by_instrument(instrument, proposal_num, restriction='public',
                                                      query_response=filename_query,
                                                      other_columns=['exp_type', 'observtn', 'expstart', 'expend', 'category'])
    proprietary, proprietary_meta = get_filenames_by_instrument(instrument, proposal_num, restriction='proprietary',
                                                                query_response=filename_query,
                                                                other_columns=['exp_type', 'observtn', 'expstart', 'expend', 'category'])
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
            full_filepath = os.path.join(FILESYSTEM, permission_type, relative_filepath)
            filenames.append(full_filepath)
        except ValueError:
            print('Unable to determine filepath for {}'.format(filename))
    return filenames


def update_database_table(update, instrument, prop, obs, thumbnail, obsfiles, types, startdate, enddate, proposal_category):
    """Update the database tables that contain info about proposals and observations, via Django models.

    Parameters
    ----------
    update : bool
        true: run updates on existing rootfilename entries
        false: only create new entries

    instrument : str
        Instrument name

    prop : str
        Proposal ID. 5-digit string

    obs : str
        Observation number. 3-digit string

    thumbnail : str
        Full path to the thumbnail image for the proposal

    obsfiles : list
        list of file rootnames in the observation

    types : list
        List of exposure types of the data in the observation

    startdate : float
        Date of the beginning of the observation in MJD

    enddate : float
        Date of the ending of the observation in MJD

    proposal_category : str
        category name
    """

    # Check to see if the required Archive entry exists, and create it if it doesn't
    archive_instance, archive_created = Archive.objects.get_or_create(instrument=instrument)
    if archive_created:
        logging.info(f'No existing entries for Archive: {instrument}. Creating.')

    # Check to see if the required Proposal entry exists, and create it if it doesn't
    prop_instance, prop_created = Proposal.objects.get_or_create(prop_id=prop, archive=archive_instance)
    if prop_created:
        logging.info(f'No existing entries for Proposal: {prop}. Creating.')

    # Update the proposal instance with the thumbnail path
    prop_instance.thumbnail_path = thumbnail
    prop_instance.category = proposal_category
    prop_instance.save(update_fields=['thumbnail_path', 'category'])

    # Now that the Archive and Proposal instances are sorted, get or create the
    # Observation instance
    obs_instance, obs_created = Observation.objects.get_or_create(obsnum=obs,
                                                                  proposal=prop_instance,
                                                                  proposal__archive=archive_instance)

    # Update the Observation info. Note that in this case, if the Observation entry
    # already existed we are overwriting the old values for number of files and dates.
    # This is done in case new files have appeared in MAST since the last run of
    # this script (i.e. the pipeline wasn't finished at the time of the last run)
    obs_instance.number_of_files = len(obsfiles)
    obs_instance.obsstart = startdate
    obs_instance.obsend = enddate

    # If the Observation instance was just created, then set the exptype list with
    # the input list. If the Observation instance already existed, then update the
    # exptype list by adding the new entries to the existing ones.
    if obs_created:
        logging.info((f'No existing entries for Observation: {instrument}, PID {prop}, Obs {obs} found. Creating. '
                      'Updating number of files, start/end dates, and exp_type list'))
        obs_instance.exptypes = ','.join(types)
    else:
        if obs_instance.exptypes == '':
            obs_instance.exptypes = ','.join(types)
        else:
            existing_exps = obs_instance.exptypes.split(',')
            existing_exps.extend(types)
            existing_exps = sorted(list(set(existing_exps)))
            new_exp_list = ','.join(existing_exps)
            obs_instance.exptypes = new_exp_list
    obs_instance.save(update_fields=['number_of_files', 'obsstart', 'obsend', 'exptypes'])

    # Get all unsaved root names in the Observation to store in the database
    nr_files_created = 0
    for file in obsfiles:
        try:
            root_file_info_instance, rfi_created = RootFileInfo.objects.get_or_create(root_name=file,
                                                                                      instrument=instrument,
                                                                                      obsnum=obs_instance,
                                                                                      proposal=prop)
            if update or rfi_created:
                # Updating defaults only on update or creation to prevent call to mast_query_by_rootname on every file name.
                defaults_dict = mast_query_by_rootname(instrument, file)

                defaults = dict(filter=defaults_dict.get('filter', ''),
                                detector=defaults_dict.get('detector', ''),
                                exp_type=defaults_dict.get('exp_type', ''),
                                read_patt=defaults_dict.get('readpatt', ''),
                                grating=defaults_dict.get('grating', ''),
                                read_patt_num=defaults_dict.get('patt_num', 0),
                                aperture=defaults_dict.get('apername', ''),
                                subarray=defaults_dict.get('subarray', ''),
                                pupil=defaults_dict.get('pupil', ''),
                                expstart=defaults_dict.get('expstart', 0.0))

                for key, value in defaults.items():
                    setattr(root_file_info_instance, key, value)
                root_file_info_instance.save()
            if rfi_created:
                nr_files_created += 1
        except Exception as e:
            logging.warning(f'\tError {e} was raised')
            logging.warning(f'\tError with root_name: {file} inst: {instrument} obsnum: {obs_instance} proposal: {prop}')
    if nr_files_created > 0:
        logging.info(f'Created {nr_files_created} rootfileinfo entries for: {instrument} - proposal:{prop} - obs:{obs}')


@log_fail
def fill_empty_model(model_name, model_field):
    '''`fill_empty_model` takes a model name and a model field as input, and then updates all the models in
    the database that have a null, empty, or zero value for that field.

    Parameters
    ----------
    model_name
        the name of the model to be updated
    model_field
        the name of the field in the model that is empty

    '''

    model_field_null = model_field + "__isnull"
    model_field_empty = model_field + "__exact"

    model = apps.get_model('jwql', model_name)
    null_models = empty_models = zero_models = model.objects.none()

    # filter(field__isnull=True)
    try:
        null_models = model.objects.filter(**{model_field_null: True})
    except ValueError:
        pass

    # filter(field__exact='')
    try:
        empty_models = model.objects.filter(**{model_field_empty: ''})
    except ValueError:
        pass

    # filter(field=0)
    try:
        zero_models = model.objects.filter(**{model_field: 0})
    except ValueError:
        pass

    model_set = null_models | empty_models | zero_models
    if model_set.exists():
        logging.info(f'{model_set.count()} models to be updated')
        if model_name == 'proposal':
            fill_empty_proposals(model_set)
        elif model_name == 'rootfileinfo':
            fill_empty_rootfileinfo(model_set)
        else:
            logging.warning(f'Filling {model_name} model is not currently implemented')
            print(f'Filling {model_name} model is not currently implemented')


def fill_empty_proposals(proposal_set):
    '''It takes a list of proposal querysets, finds the thumbnail and category for each proposal, and saves
    the proposal

    Parameters
    ----------
    proposal_set : a queryset of Proposal objects

    '''

    saved_proposals = 0
    for proposal_mod in proposal_set:

        filenames_public, metadata_public, filenames_proprietary, metadata_proprietary = get_all_possible_filenames_for_proposal(proposal_mod.archive.instrument, proposal_mod.prop_id)
        # Find the location in the filesystem for all files
        filepaths_public = files_in_filesystem(filenames_public, 'public')
        filepaths_proprietary = files_in_filesystem(filenames_proprietary, 'proprietary')
        filenames = filepaths_public + filepaths_proprietary
        proposal_info = get_proposal_info(filenames)

        # There is one and only one category for the proposal, so just take the first.
        proposal_category = ''
        if len(metadata_public['category']):
            proposal_category = metadata_public['category'][0]
        elif len(metadata_proprietary['category']):
            proposal_category = metadata_proprietary['category'][0]

        proposal_mod.thumbnail_path = proposal_info['thumbnail_paths'][0]
        proposal_mod.category = proposal_category
        try:
            proposal_mod.save(update_fields=['thumbnail_path', 'category'])
            saved_proposals += 1
        except Exception as e:
            logging.warning(f'\tCould not save proposal {proposal_mod.prop_id}')
            logging.warning(f'\tError {e} was raised')

    logging.info(f'\tSaved {saved_proposals} proposals')


def fill_empty_rootfileinfo(rootfileinfo_set):
    '''Takes a queryset of RootFileInfo objects and fills in the empty fields with values
    from the MAST database

    Parameters
    ----------
    rootfileinfo_set : a queryset of RootFileInfo objects

    '''

    saved_rootfileinfos = 0
    for rootfileinfo_mod in rootfileinfo_set:
        defaults_dict = mast_query_by_rootname(rootfileinfo_mod.instrument, rootfileinfo_mod.root_name)

        defaults = dict(filter=defaults_dict.get('filter', ''),
                        detector=defaults_dict.get('detector', ''),
                        exp_type=defaults_dict.get('exp_type', ''),
                        read_patt=defaults_dict.get('readpatt', ''),
                        grating=defaults_dict.get('grating', ''),
                        read_patt_num=defaults_dict.get('patt_num', 0),
                        aperture=defaults_dict.get('apername', ''),
                        subarray=defaults_dict.get('subarray', ''),
                        pupil=defaults_dict.get('pupil', ''),
                        expstart=defaults_dict.get('expstart', 0.0))

        for key, value in defaults.items():
            setattr(rootfileinfo_mod, key, value)
        try:
            rootfileinfo_mod.save()
            saved_rootfileinfos += 1
        except Exception as e:
            logging.warning(f'\tCould not save rootfileinfo {rootfileinfo_mod.root_name}')
            logging.warning(f'\tError {e} was raised')
    logging.info(f'\tSaved {saved_rootfileinfos} Root File Infos')


@lock_module
def protected_code(update_database, fill_empty_list):
    """Protected code ensures only 1 instance of module will run at any given time

    Parameters
    ----------
    update_database : bool
        If True, any existing rootfileinfo models are overwritten
    """
    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    if fill_empty_list:
        fill_empty_model(fill_empty_list[0], fill_empty_list[1])
    else:
        get_updates(update_database)


if __name__ == '__main__':

    models_list = ['archive', 'observation', 'proposal', 'rootfileinfo']
    proposal_fields = ['category']
    # Initialize parser
    msg = "Used to update Django Model Database from header information"
    parser = argparse.ArgumentParser(description=msg)

    # Adding optional argument
    parser.add_argument("--update", action='store_true', help="Update Entire Model Database")
    parser.add_argument("--fill_empty", nargs=2, help="enter 2 arguments-> model_name, model_field")

    args = parser.parse_args()
    continue_script = True
    if args.fill_empty:
        continue_script = False
        args.fill_empty = list(map(lambda x: x.lower(), args.fill_empty))
        if args.fill_empty[0] not in models_list:
            print('model_name incorrect, try: {}'.format(models_list))
        else:
            model = apps.get_model('jwql', args.fill_empty[0])
            fields = [field.name for field in model._meta.get_fields()]
            if args.fill_empty[1] not in fields:
                print('Invalid field entered for model type {}, try one of the following: {}'.format(args.fill_empty[0], fields))
            else:
                continue_script = True

    if continue_script:
        protected_code(args.update, args.fill_empty)
