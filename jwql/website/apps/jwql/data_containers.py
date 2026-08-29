"""Various functions to collect data to be used by the ``views`` of the
``jwql`` app.

This module contains several functions that assist in collecting and
producing various data to be rendered in ``views.py`` for use by the
``jwql`` app.

Authors
-------

    - Lauren Chambers
    - Matthew Bourque
    - Teagan King
    - Bryan Hilbert
    - Maria Pena-Guerrero
    - Bradley Sappington
    - Melanie Clarke

Use
---

    The functions within this module are intended to be imported and
    used by ``views.py``, e.g.:

    ::
        from .data_containers import get_proposal_info
"""

import copy
import glob
import json
import logging
import os
import re
import tempfile
from collections import defaultdict, OrderedDict
from datetime import datetime
from operator import getitem, itemgetter
from pathlib import Path

import numpy as np
import pandas as pd
import pyvo as vo
import requests
from astropy.io import fits
from astropy.time import Time
from astroquery.mast import Mast
from bs4 import BeautifulSoup
from django import forms, setup
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet

from jwql.edb.engineering_database import get_mnemonic, get_mnemonic_info, mnemonic_inventory
from jwql.utils.constants import (
    DEFAULT_MODEL_COMMENT,
    EXPOSURE_PAGE_SUFFIX_ORDER,
    IGNORED_SUFFIXES,
    INSTRUMENT_SERVICE_MATCH,
    JWST_INSTRUMENT_NAMES,
    JWST_INSTRUMENT_NAMES_MIXEDCASE,
    MAST_QUERY_LIMIT,
    MONITORS,
    ON_GITHUB_ACTIONS,
    ON_READTHEDOCS,
    REPORT_KEYS_PER_INSTRUMENT,
    SUFFIXES_TO_ADD_ASSOCIATION,
    SUFFIXES_WITH_AVERAGED_INTS,
    THUMBNAIL_FILTER_LOOK,
    QueryConfigKeys,
    STSCI_VO_URL
)
from jwql.utils.credentials import get_mast_token
from jwql.utils.logging_functions import configure_logging
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import (
    check_config_for_key,
    ensure_dir_exists,
    filename_parser,
    filesystem_path,
    get_config,
    get_rootnames_for_instrument_proposal,
)


# Increase the limit on the number of entries that can be returned by
# a MAST query.
Mast._portal_api_connection.PAGESIZE = MAST_QUERY_LIMIT


if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # These lines are needed in order to use the Django models in a standalone
    # script (as opposed to code run as a result of a webpage request). If these
    # lines are not run, the script will crash when attempting to import the
    # Django models in the line below.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    setup()

    from jwql.website.apps.jwql.models import Anomalies, get_model_column_names, Observation, Proposal, RootFileInfo

    from .forms import (
        InstrumentAnomalySubmitForm,
        MnemonicExplorationForm,
        MnemonicQueryForm,
        MnemonicSearchForm,
        RootFileInfoCommentSubmitForm,
        RootFileInfoExposureCommentSubmitForm,
    )
    check_config_for_key('auth_mast')
    configs = get_config()
    auth_mast = configs['auth_mast']
    mast_flavour = '.'.join(auth_mast.split('.')[1:])
    from astropy import config
    conf = config.get_config('astroquery')
    conf['mast'] = {'server': 'https://{}'.format(mast_flavour)}
    FILESYSTEM_DIR = configs['filesystem']
    PREVIEW_IMAGE_FILESYSTEM = configs['preview_image_filesystem']
    THUMBNAIL_FILESYSTEM = configs['thumbnail_filesystem']
    OUTPUT_DIR = configs['outputs']

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]

if not ON_GITHUB_ACTIONS:
    Mast._portal_api_connection.MAST_REQUEST_URL = get_config()['mast_request_url']


def build_table(tablename):
    """Create Pandas dataframe from JWQLDB table.

    Parameters
    ----------
    tablename : str
        Name of JWQL database table name.

    Returns
    -------
    table_meta_data : pandas.DataFrame
        Pandas data frame version of JWQL database table.
    """
    all_models = import_all_models()
    table_object = all_models.get(tablename)

    result = table_object.objects.all()
    column_names = get_model_column_names(table_object)

    # Convert the QuerySet into a dictionary
    rows = result.values()
    data = defaultdict(list)

    for row in rows:
        for key, value in row.items():
            data[key].append(value)

    # Build table.
    table_meta_data = pd.DataFrame(data)

    return table_meta_data


def filter_root_files(instrument=None, proposal=None, obsnum=None, sort_as=None,
                      look=None, exp_type=None, cat_type=None, detector=None):
    """Retrieve and filter root file table entries.

    Parameters
    ----------
    instrument : str, optional
        Name of the JWST instrument.
    proposal : str, optional
        Proposal to match. Used as a 'starts with' filter.
    obsnum : str, optional
        Observation number to match.
    sort_as : {'ascending', 'descending', 'recent', 'oldest'}, optional
        Sorting method for output table. Ascending and descending
        options refer to root file name; recent and oldest sort by exposure
        start time.
    look : {'new', 'viewed'}, optional
        If set to None, all viewed values are returned. If set to
        'viewed', only viewed data is returned. If set to 'new', only
        new data is returned.
    exp_type : str, optional
        Set to filter by exposure type.
    cat_type : str, optional
        Set to filter by proposal category.
    detector : str, optional
        Set to filter by detector name.

    Returns
    -------
    root_file_info : QuerySet
        List of RootFileInfo entries matching input criteria.
    """
    # standardize input

    # get desired filters
    filter_kwargs = dict()
    if instrument is not None and str(instrument).strip().lower() != 'all':
        inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]
        filter_kwargs['instrument'] = inst
    if proposal is not None and str(proposal).strip().lower() != 'all':
        filter_kwargs['proposal__startswith'] = proposal.lstrip('0')
    if obsnum is not None and str(obsnum).strip().lower() != 'all':
        filter_kwargs['obsnum__obsnum'] = obsnum
    if look is not None and str(look).strip().lower() != 'all':
        filter_kwargs['viewed'] = (str(look).lower() == 'viewed')
    if exp_type is not None and str(exp_type).strip().lower() != 'all':
        filter_kwargs['exp_type__iexact'] = exp_type
    if cat_type is not None and str(cat_type).strip().lower() != 'all':
        filter_kwargs['obsnum__proposal__category__iexact'] = cat_type
    if detector is not None and str(detector).strip().lower() != 'all':
        filter_kwargs['detector__iexact'] = detector

    # get file info by instrument from local model
    root_file_info = RootFileInfo.objects.filter(**filter_kwargs)

    # descending by root file is default;
    # for other options, sort as desired
    sort_as = str(sort_as).strip().lower()
    if sort_as == 'ascending':
        root_file_info = root_file_info.order_by('root_name')
    elif sort_as == 'recent':
        root_file_info = root_file_info.order_by('-expstart', 'root_name')
    elif sort_as == 'oldest':
        root_file_info = root_file_info.order_by('expstart', 'root_name')

    return root_file_info.values()


def create_archived_proposals_context(inst):
    """Generate and save a json file containing the information needed
    to create an instrument's archive page.

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    """
    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    # Get a list of Observation entries for the given instrument
    all_entries = Observation.objects.filter(proposal__archive__instrument=inst)

    # Get a list of proposal numbers.
    prop_objects = Proposal.objects.filter(archive__instrument=inst)
    proposal_nums = [entry.prop_id for entry in prop_objects]

    # Put proposals into descending order
    proposal_nums.sort(key=int, reverse=True)

    # Total number of proposals for the instrument
    num_proposals = len(proposal_nums)

    thumbnail_paths = []
    min_obsnums = []
    total_files = []
    proposal_viewed = []
    proposal_exp_types = []
    thumb_exp_types = []
    proposal_obs_times = []
    thumb_obs_time = []
    cat_types = []

    # Get a set of all exposure types used in the observations associated with this proposal
    exp_types = [exposure_type for observation in all_entries for exposure_type in observation.exptypes.split(',')]
    exp_types = sorted(set(exp_types))

    # Get all proposals based on category type
    proposals_by_category = get_proposals_by_category(inst)
    unique_cat_types = sorted(set(proposals_by_category.values()))

    # The naming conventions for dropdown_menus are tightly coupled with the code, this should be changed down the line.
    dropdown_menus = {'look': THUMBNAIL_FILTER_LOOK,
                      'exp_type': exp_types,
                      'cat_type': unique_cat_types}
    thumbnails_dict = {}

    for proposal_num in proposal_nums:
        # For each proposal number, get all entries
        prop_entries = all_entries.filter(proposal__prop_id=proposal_num)

        # All entries will have the same thumbnail_path, so just grab the first
        thumbnail_paths.append(prop_entries[0].proposal.thumbnail_path)

        # Extract the observation numbers from each entry and find the minimum
        prop_obsnums = [entry.obsnum for entry in prop_entries]
        min_obsnums.append(min(prop_obsnums))

        # Sum the file count from all observations to get the total file count for
        # the proposal
        prop_filecount = [entry.number_of_files for entry in prop_entries]
        total_files.append(sum(prop_filecount))

        # In order to know if a proposal contains all observations that
        # are entirely viewed, check for at least one existing
        # viewed=False in RootFileInfo
        unviewed_root_file_infos = RootFileInfo.objects.filter(instrument=inst, proposal=proposal_num, viewed=False)
        proposal_viewed.append("Viewed" if unviewed_root_file_infos.count() == 0 else "New")

        # Store comma separated list of exp_types associated with each proposal
        proposal_exp_types = [exposure_type for observation in prop_entries for exposure_type in observation.exptypes.split(',')]
        proposal_exp_types = list(set(proposal_exp_types))
        thumb_exp_types.append(','.join(proposal_exp_types))

        # Get Most recent observation start time
        proposal_obs_times = [observation.obsstart for observation in prop_entries]
        thumb_obs_time.append(max(proposal_obs_times))

        try:
            # Add category type to list based on proposal number
            cat_types.append(proposals_by_category[int(proposal_num)])
        except KeyError:
            cat_types.append("MISSING")
            logging.error(f"""Unable to populate proposals by category in MAST for proposal number {proposal_num}
                          Proposal number {proposal_num} will have 'MISSING' category type associated with it
                          """)

    thumbnails_dict['proposals'] = proposal_nums
    thumbnails_dict['thumbnail_paths'] = thumbnail_paths
    thumbnails_dict['num_files'] = total_files
    thumbnails_dict['viewed'] = proposal_viewed
    thumbnails_dict['exp_types'] = thumb_exp_types
    thumbnails_dict['obs_time'] = thumb_obs_time
    thumbnails_dict['cat_types'] = cat_types

    context = {'inst': inst,
               'num_proposals': num_proposals,
               'min_obsnum': min_obsnums,
               'thumbnails': thumbnails_dict,
               'dropdown_menus': dropdown_menus}

    json_object = json.dumps(context, indent=4)

    # Writing to json file
    outfilename = os.path.join(OUTPUT_DIR, 'archive_page', f'{inst}_archive_context.json')
    with open(outfilename, "w") as outfile:
        outfile.write(json_object)
    set_permissions(outfilename)


def get_acknowledgements():
    """Returns a list of individuals who are acknowledged on the
    ``about`` page.

    The list is generated by reading in the contents of the ``jwql``
    ``README`` file.  In this way, the website will automatically
    update with updates to the ``README`` file.

    Returns
    -------
    acknowledgements : list
        A list of individuals to be acknowledged.
    """

    # Locate README file
    readme_file = os.path.join(REPO_DIR, 'README.md')

    # Get contents of the README file
    with open(readme_file, 'r') as f:
        data = f.readlines()

    # Find where the acknowledgements start
    for i, line in enumerate(data):
        if 'Acknowledgments' in line:
            index = i

    # Parse out the list of individuals
    acknowledgements = data[index + 1:]
    acknowledgements = [item.strip().replace('- ', '').split(' [@')[0].strip()
                        for item in acknowledgements]

    return acknowledgements


def get_additional_exposure_info(root_file_infos, image_info):
    """Create dictionaries of basic exposure information from an exposure's
    RootFileInfo entry, as well as header information. Originally designed to
    be used in jwql.website.apps.jwql.views.view_image()

    Parameters
    ----------
    root_file_infos : jwql.website.apps.jwql.models.RootFileInfo or django.db.models.query.QuerySet
        RootFileInfo for a particular file base name, or a QuerySet of RootFileInfos for
        an exposure base name.

    image_info : : dict
        A dictionary containing various information for the given
        ``file_root``.

    Returns
    -------
    basic_info : dict
        Dictionary of information about the file/exposure

    additional_info : dict
        Dictionary of extra information about the file/exposure
    """
    # Get headers from the file so we can pass along info that is common to all
    # suffixes. The order of possible_suffixes_to_use is itentional, because the
    # uncal file will not have info on the pipeline version used, and so we would
    # rather grab information from the rate or cal files.
    #possible_suffixes_to_use = np.array(['rate', 'rateints', 'cal', 'calints', 'uncal', 'i2d', 's3d', 's2d', 'x1d', 'crf'])
    suffixes_to_ignore = set(['trapsfilled', 'msa', 'cat', 'segm', 'phot', 'whtlt'])
    possible_suffixes_to_use = np.array([item for item in EXPOSURE_PAGE_SUFFIX_ORDER if item not in suffixes_to_ignore])
    existing_suffixes = np.array([suffix in image_info['suffixes'] for suffix in possible_suffixes_to_use])

    if isinstance(root_file_infos, QuerySet):
        root_file_info = root_file_infos[0]
        filter_value = '/'.join(set([e.filter for e in root_file_infos]))
        pupil_value = '/'.join(set([e.pupil for e in root_file_infos]))
        grating_value = '/'.join(set([e.grating for e in root_file_infos]))
        exp_comment = root_file_infos.first().exp_comment
    elif isinstance(root_file_infos, RootFileInfo):
        root_file_info = root_file_infos
        filter_value = root_file_info.filter
        pupil_value = root_file_info.pupil
        grating_value = root_file_info.grating
        exp_comment = root_file_info.exp_comment

    # Print N/A if no exposure comment is used
    exp_comment = exp_comment if exp_comment != DEFAULT_MODEL_COMMENT else "N/A"

    # Initialize dictionary of file info to show at the top of the page, along
    # with another for info that will be in the collapsible text box.
    basic_info = {'exp_type': root_file_info.exp_type,
                  'category': 'N/A',
                  'visit_status': 'N/A',
                  'subarray': root_file_info.subarray,
                  'filter': filter_value
                  }

    # The order of the elements is important here, in that the webpage displays
    # them in the order they are here, and we've set this order to try and group
    # together related keywords.
    if isinstance(root_file_infos, QuerySet):
        additional_info = {'READPATT': root_file_info.read_patt,
                           'TITLE': 'N/A',
                           'NGROUPS': 'N/A',
                           'PI_NAME': 'N/A',
                           'NINTS': 'N/A',
                           'TARGNAME': 'N/A',
                           'EXPTIME': 'N/A',
                           'TARG_RA': 'N/A',
                           'CAL_VER': 'N/A',
                           'TARG_DEC': 'N/A',
                           'CRDS context': 'N/A',
                           'PA_V3': 'N/A',
                           'EXPSTART': root_file_info.expstart,
                           'EXP_COMMENT': exp_comment
                           }
    elif isinstance(root_file_infos, RootFileInfo):
        additional_info = {'READPATT': root_file_info.read_patt,
                           'TITLE': 'N/A',
                           'NGROUPS': 'N/A',
                           'PI_NAME': 'N/A',
                           'NINTS': 'N/A',
                           'TARGNAME': 'N/A',
                           'EXPTIME': 'N/A',
                           'RA_REF': 'N/A',
                           'CAL_VER': 'N/A',
                           'DEC_REF': 'N/A',
                           'CRDS context': 'N/A',
                           'ROLL_REF': 'N/A',
                           'EXPSTART': root_file_info.expstart,
                           'EXP_COMMENT': exp_comment
                           }

    # Deal with instrument-specific parameters
    if root_file_info.instrument == 'NIRSpec':
        basic_info['grating'] = grating_value

    if root_file_info.instrument in ['NIRCam', 'NIRISS']:
        basic_info['pupil'] = pupil_value

    # If any of the desired files are present, get the headers and populate the header
    # info dictionary
    if any(existing_suffixes):
        suffix = possible_suffixes_to_use[existing_suffixes][0]
        filename = f'{root_file_info.root_name}_{suffix}.fits'

        # get_image_info() has already globbed over the directory with the files and
        # returned the list of existing suffixes, so we shouldn't need to check for
        # file existence here.
        try:
            file_path = filesystem_path(filename, check_existence=True)
        except FileNotFoundError as e:
            raise e

        header = fits.getheader(file_path)
        header_sci = fits.getheader(file_path, 1)

        # Dont assume headers exist, some are omitted in parallel observations
        basic_info['category'] = header.get('CATEGORY', 'N/A')
        basic_info['visit_status'] = header.get('VISITSTA', 'N/A')
        additional_info['NGROUPS'] = header.get('NGROUPS', 'N/A')
        additional_info['NINTS'] = header.get('NINTS', 'N/A')
        additional_info['EXPTIME'] = header.get('EFFEXPTM', 'N/A')
        additional_info['TITLE'] = header.get('TITLE', 'N/A')
        additional_info['PI_NAME'] = header.get('PI_NAME', 'N/A')
        additional_info['TARGNAME'] = header.get('TARGPROP', 'N/A')

        # For the exposure level (i.e. multiple files) present the target
        # RA and Dec. For the image level, give RA_REF, DEC_REF, since those
        # are specific to the detector. Similarly, for the exposure level, show
        # PA_V3, which applies to all detectors. At the image level, show
        # ROLL_REF, which is detector-specific.
        if isinstance(root_file_infos, QuerySet):
            additional_info['TARG_RA'] = header.get('TARG_RA', 'N/A')
            additional_info['TARG_DEC'] = header.get('TARG_DEC', 'N/A')
            additional_info['PA_V3'] = header_sci.get('PA_V3', 'N/A')
        elif isinstance(root_file_infos, RootFileInfo):
            additional_info['RA_REF'] = header_sci.get('RA_REF', 'N/A')
            additional_info['DEC_REF'] = header_sci.get('DEC_REF', 'N/A')
            additional_info['ROLL_REF'] = header_sci.get('ROLL_REF', 'N/A')

        additional_info['CAL_VER'] = 'N/A'
        additional_info['CRDS context'] = 'N/A'

        # Pipeline version and CRDS context info are not in uncal files
        if suffix != 'uncal':
            additional_info['CAL_VER'] = header.get('CAL_VER', 'N/A')
            additional_info['CRDS context'] = header.get('CRDS_CTX', 'N/A')

    return basic_info, additional_info


def get_all_proposals():
    """Return a list of all proposals that exist in the filesystem.

    Returns
    -------
    proposals : list
        A list of proposal numbers for all proposals that exist in the
        filesystem
    """
    proprietary_proposals = os.listdir(os.path.join(FILESYSTEM_DIR, 'proprietary'))
    public_proposals = os.listdir(os.path.join(FILESYSTEM_DIR, 'public'))
    all_proposals = [prop[2:] for prop in proprietary_proposals + public_proposals if 'jw' in prop]
    proposals = sorted(list(set(all_proposals)), reverse=True)
    return proposals


def get_available_suffixes(all_suffixes, return_untracked=True):
    """
    Put available suffixes in a consistent order.

    Any suffixes not recognized are returned at the end of the suffix
    list, in random order.

    Parameters
    ----------
    all_suffixes : list of str
        List of all data product suffixes found for a given file root.
    return_untracked : bool, optional
        If set, a set of untracked suffixes is also returned, for
        logging or diagnostic purposes.

    Returns
    -------
    suffixes : list of str
        All available unique suffixes in standard order.
    untracked_suffixes : set of str, optional
        Any suffixes that were not recognized.
    """
    #  Check if any of the
    # suffixes are not in the list that specifies order.
    suffixes = []
    untracked_suffixes = set(all_suffixes)
    for poss_suffix in EXPOSURE_PAGE_SUFFIX_ORDER:
        if 'crf' not in poss_suffix:
            if (poss_suffix in all_suffixes and poss_suffix not in suffixes):
                suffixes.append(poss_suffix)
                untracked_suffixes.remove(poss_suffix)
        else:
            # EXPOSURE_PAGE_SUFFIX_ORDER contains crf and crfints,
            # but the actual suffixes in the data will be e.g. o001_crf,
            # and there may be more than one crf file in the list of suffixes.
            # So in this case, we strip the e.g. o001 from the
            # suffixes and check which list elements match.
            for image_suffix in all_suffixes:
                if (image_suffix.endswith(poss_suffix) and image_suffix not in suffixes):
                    suffixes.append(image_suffix)
                    untracked_suffixes.remove(image_suffix)

    # If the data contain any suffixes that are not in the list
    # that specifies the order to use, add them to the end of the
    # suffixes list. Their order will be random since they are not in
    # EXPOSURE_PAGE_SUFFIX_ORDER.
    for suffix in untracked_suffixes:
        if suffix not in IGNORED_SUFFIXES:
            suffixes.append(suffix)

    if return_untracked:
        return suffixes, untracked_suffixes
    else:
        return suffixes


def get_current_flagged_anomalies(rootfileinfo_set):
    """Return a list of currently flagged anomalies for the given
    ``rootname``

    This function may be used to retrieve the current anomalies
    for single rootfileinfo or sets of rootfileinfos in an exposure group. Group
    anomalies are returned if they are true in every rootfileinfo in the set.
    For single files,  any anomaly present for the file is a current anomaly.


    Parameters
    ----------
    rootfileinfo_set : RootFileInfo Queryset
        A query set of 1 or more RootFileInfos of interest
        Must be iterable, even if only one RootFileInfo.

    Returns
    -------
    current_anomalies : list of str
        A list of currently flagged anomalies for the given rootfileinfo_set
        (e.g. ``['snowball', 'crosstalk']``)
    """
    all_anomalies = Anomalies.get_all_anomalies()
    anomalies_set = []
    current_anomalies = []
    empty_anomaly_found = False
    for rootfileinfo in rootfileinfo_set:
        try:
            anomalies_set.append(rootfileinfo.anomalies.get_marked_anomalies())
        except (ObjectDoesNotExist, AttributeError):
            empty_anomaly_found = True
            break

    if not empty_anomaly_found:
        # If all RootFileInfos have anomalies, calculate which anomalies exist in every RootFileInfo
        flat_list = [anomaly for sublist in anomalies_set for anomaly in sublist]
        for anomaly in all_anomalies:
            if flat_list.count(anomaly) == len(rootfileinfo_set):
                current_anomalies.append(anomaly)

    return current_anomalies


def get_anomaly_form(request, inst, file_root):
    """Generate form data for context

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument
    file_root : str
        FITS filename of selected image in filesystem. May be a
        file or group root name.

    Returns
    -------
    InstrumentAnomalySubmitForm object
        form object to be sent with context to template
    """
    # Check for group root name
    rootfileinfo_set = RootFileInfo.objects.filter(root_name__startswith=file_root)
    # Determine current flagged anomalies
    current_anomalies = get_current_flagged_anomalies(rootfileinfo_set)
    # Create a form instance
    form = InstrumentAnomalySubmitForm(request.POST or None, instrument=inst.lower(), initial={'anomaly_choices': current_anomalies})

    # If this is a POST request and the form is filled out, process the form data
    if request.method == 'POST':
        anomaly_choices = dict(request.POST).get('anomaly_choices', [])
        if form.is_valid():
            for rootfileinfo in rootfileinfo_set:
                # for a group form submit, add any individual anomalies
                # not in the original group set
                if len(rootfileinfo_set) > 1:
                    file_current = get_current_flagged_anomalies([rootfileinfo])
                    choices = anomaly_choices.copy()
                    for choice in file_current:
                        if choice not in current_anomalies:
                            choices.append(choice)
                else:
                    choices = anomaly_choices
                form.update_anomaly_table(rootfileinfo, 'unknown', choices)  # TODO do we actually want usernames?
            messages.success(request, "Anomaly submitted successfully")
        else:
            messages.error(request, "Failed to submit anomaly")

    return form


def get_comment_form(request, file_root):
    """Generate form data for comment form

    Parameters
    ----------
    request : HttpRequest object
        Incoming request
    file_root : str
        FITS filename of selected image in filesystem. May be a
        file or group root name.

    Returns
    -------
    RootFileInfoCommentSubmitForm object
        form object to be sent with context to template
    """

    root_file_info = RootFileInfo.objects.get(root_name=file_root)

    if request.method == 'POST':
        comment_form = RootFileInfoCommentSubmitForm(request.POST, instance=root_file_info)
        if comment_form.is_valid():
            comment_form.save()
        else:
            messages.error(request, "Failed to update comment form")
    else:
        comment_form = RootFileInfoCommentSubmitForm(instance=root_file_info)

    return comment_form


def get_exp_comment_form(request, file_root):
    """Generate form data for exposure comment
        This form updates all exposure level comments in each related rootfileimage model.
        Each model related to this exposure will have the same exposure_comment associated with it.
        When getting the default comment for this form, just use the first of the set.  When updating
        the comment, update for every rootfileinfo in the query set.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request
    file_root : str
        Partial FITS filename substring of exposure root name.

    Returns
    -------
    RootFileInfoExposureCommentSubmitForm object
        form object to be sent with context to template
    """

    rootfileinfo_set = RootFileInfo.objects.filter(root_name__startswith=file_root)

    if request.method == 'POST':
        exp_comment_form = RootFileInfoExposureCommentSubmitForm(request.POST, instance=rootfileinfo_set.first())
        if exp_comment_form.is_valid():
            # Update the for all images in exposure
            for rootfileinfo in rootfileinfo_set:
                rootfileinfo.exp_comment = exp_comment_form.cleaned_data['exp_comment']
                rootfileinfo.save()
        else:
            messages.error(request, "Failed to update exposure comment form")
    else:
        exp_comment_form = RootFileInfoExposureCommentSubmitForm(instance=rootfileinfo_set.first())

    return exp_comment_form


def get_group_anomalies(file_root):
    """Generate form data for context

    Parameters
    ----------
    file_root : str
        FITS filename of selected image in filesystem. May be a
        file or group root name.

    Returns
    -------
    group_anomaly_dict dict
        root file name key with string of anomalies followed by anomaly comment
    """
    # Check for group root name
    rootfileinfo_set = RootFileInfo.objects.filter(root_name__startswith=file_root).order_by("root_name")
    group_anomaly_dict = {}
    for rootfileinfo in rootfileinfo_set:
        anomalies_list = get_current_flagged_anomalies([rootfileinfo])
        anomalies_string = ', '.join(anomalies_list)
        group_anomaly_dict[rootfileinfo.root_name] = anomalies_string
        if rootfileinfo.comment != DEFAULT_MODEL_COMMENT:
            anomalies_string += f" -- Comments: {rootfileinfo.comment}"
        group_anomaly_dict[rootfileinfo.root_name] = anomalies_string

    return group_anomaly_dict


def get_dashboard_components(request):
    """Build and return a Dashboard class.

    Returns
    -------
    dashboard_components : GeneralDashboard
        The dashboard.
    """

    from jwql.website.apps.jwql.bokeh_dashboard import GeneralDashboard

    if 'time_delta_value' in request.POST:
        time_delta_value = request.POST['timedelta']

        if time_delta_value == 'All Time':
            time_delta = None
        else:
            time_delta_options = {'All Time': None,
                                  '1 Day': pd.DateOffset(days=1),
                                  '1 Month': pd.DateOffset(months=1),
                                  '1 Week': pd.DateOffset(weeks=1),
                                  '1 Year': pd.DateOffset(years=1)}
            time_delta = time_delta_options[time_delta_value]

        dashboard = GeneralDashboard(delta_t=time_delta)

        return dashboard
    else:
        # When coming from home/monitor views
        dashboard = GeneralDashboard(delta_t=None)

        return dashboard


def get_edb_components(request):
    """Return dictionary with content needed for the EDB page.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    edb_components : dict
        Dictionary with the required components

    """
    mnemonic_name_search_result = {}
    mnemonic_query_result = {}
    mnemonic_query_result_plot = None
    mnemonic_exploration_result = None
    mnemonic_query_status = None
    mnemonic_table_result = None

    # If this is a POST request, we need to process the form data
    if request.method == 'POST':

        if 'mnemonic_name_search' in request.POST.keys():
            # authenticate with astroquery.mast if necessary
            logged_in = log_into_mast(request)

            mnemonic_name_search_form = MnemonicSearchForm(request.POST, logged_in=logged_in,
                                                           prefix='mnemonic_name_search')

            if mnemonic_name_search_form.is_valid():
                mnemonic_identifier = mnemonic_name_search_form['search'].value()
                if mnemonic_identifier is not None:
                    mnemonic_name_search_result = get_mnemonic_info(mnemonic_identifier)

            # create forms for search fields not clicked
            mnemonic_query_form = MnemonicQueryForm(prefix='mnemonic_query')
            mnemonic_exploration_form = MnemonicExplorationForm(prefix='mnemonic_exploration')

        elif 'mnemonic_query' in request.POST.keys():
            # authenticate with astroquery.mast if necessary
            logged_in = log_into_mast(request)

            mnemonic_query_form = MnemonicQueryForm(request.POST, logged_in=logged_in,
                                                    prefix='mnemonic_query')

            # proceed only if entries make sense
            if mnemonic_query_form.is_valid():
                mnemonic_identifier = mnemonic_query_form['search'].value()
                start_time = Time(mnemonic_query_form['start_time'].value(), format='iso')
                end_time = Time(mnemonic_query_form['end_time'].value(), format='iso')

                if mnemonic_identifier is not None:
                    mnemonic_query_result = get_mnemonic(mnemonic_identifier, start_time, end_time)

                    if len(mnemonic_query_result.data) == 0:
                        mnemonic_query_status = "QUERY RESULT RETURNED NO DATA FOR {} ON DATES {} - {}".format(mnemonic_identifier,
                                                                                                               start_time, end_time)
                    else:
                        mnemonic_query_status = 'SUCCESS'

                        # If else to determine data visualization.
                        if type(mnemonic_query_result.data['euvalues'][0]) == np.str_:
                            if len(np.unique(mnemonic_query_result.data['euvalues'])) > 4:
                                mnemonic_table_result = mnemonic_query_result.get_table_data()
                            else:
                                mnemonic_query_result_plot = mnemonic_query_result.bokeh_plot_text_data()
                        else:
                            mnemonic_query_result_plot = mnemonic_query_result.bokeh_plot()

                        # generate table download in web app
                        result_table = mnemonic_query_result.data

                        # save file locally to be available for download
                        static_dir = os.path.join(settings.BASE_DIR, 'static')
                        ensure_dir_exists(static_dir)
                        file_name_root = f"{mnemonic_identifier}_{start_time.iso.split(' ')[0]}_{end_time.iso.split(' ')[0]}"
                        file_for_download = '{}.csv'.format(file_name_root)
                        path_to_save = os.path.join(static_dir, file_for_download)

                        # add meta data to saved table
                        comments = []
                        comments.append('DMS EDB query of {}:'.format(mnemonic_identifier))
                        for key, value in mnemonic_query_result.info.items():
                            comments.append('{} = {}'.format(key, str(value)))
                        result_table.meta['comments'] = comments
                        comments.append(' ')
                        comments.append('Start time {}'.format(start_time.isot))
                        comments.append('End time   {}'.format(end_time.isot))
                        comments.append('Number of rows {}'.format(len(result_table)))
                        comments.append(' ')
                        result_table.write(path_to_save, format='ascii.fixed_width',
                                           overwrite=True, delimiter=',', bookend=False)
                        mnemonic_query_result.file_for_download = path_for_download

            # create forms for search fields not clicked
            mnemonic_name_search_form = MnemonicSearchForm(prefix='mnemonic_name_search')
            mnemonic_exploration_form = MnemonicExplorationForm(prefix='mnemonic_exploration')

        elif 'mnemonic_exploration' in request.POST.keys():
            mnemonic_exploration_form = MnemonicExplorationForm(request.POST,
                                                                prefix='mnemonic_exploration')
            if mnemonic_exploration_form.is_valid():
                mnemonic_exploration_result, meta = mnemonic_inventory()

                # loop over filled fields and implement simple AND logic
                for field in mnemonic_exploration_form.fields:
                    field_value = mnemonic_exploration_form[field].value()
                    if field_value != '':
                        column_name = mnemonic_exploration_form[field].label

                        # matching indices in table (case-insensitive)
                        index = [
                            i for i, item in enumerate(mnemonic_exploration_result[column_name]) if
                            re.search(field_value, item, re.IGNORECASE)
                        ]
                        mnemonic_exploration_result = mnemonic_exploration_result[index]

                mnemonic_exploration_result.n_rows = len(mnemonic_exploration_result)

                # generate tables for display and download in web app
                display_table = copy.deepcopy(mnemonic_exploration_result)

                # temporary html file,
                # see http://docs.astropy.org/en/stable/_modules/astropy/table/
                tmpdir = tempfile.mkdtemp()
                file_name_root = 'mnemonic_exploration_result_table'
                path_for_html = os.path.join(tmpdir, '{}.html'.format(file_name_root))
                with open(path_for_html, 'w') as tmp:
                    display_table.write(tmp, format='jsviewer')
                mnemonic_exploration_result.html_file_content = open(path_for_html, 'r').read()

                # pass on meta data to have access to total number of mnemonics
                mnemonic_exploration_result.meta = meta

                # save file locally to be available for download
                static_dir = os.path.join(settings.BASE_DIR, 'static')
                ensure_dir_exists(static_dir)
                file_for_download = '{}.csv'.format(file_name_root)
                path_for_download = os.path.join(static_dir, file_for_download)
                display_table.write(path_for_download, format='ascii.fixed_width',
                                    overwrite=True, delimiter=',', bookend=False)
                mnemonic_exploration_result.file_for_download = path_for_download

                if mnemonic_exploration_result.n_rows == 0:
                    mnemonic_exploration_result = 'empty'

            # create forms for search fields not clicked
            mnemonic_name_search_form = MnemonicSearchForm(prefix='mnemonic_name_search')
            mnemonic_query_form = MnemonicQueryForm(prefix='mnemonic_query')

    else:
        mnemonic_name_search_form = MnemonicSearchForm(prefix='mnemonic_name_search')
        mnemonic_query_form = MnemonicQueryForm(prefix='mnemonic_query')
        mnemonic_exploration_form = MnemonicExplorationForm(prefix='mnemonic_exploration')

    edb_components = {'mnemonic_query_form': mnemonic_query_form,
                      'mnemonic_query_result': mnemonic_query_result,
                      'mnemonic_query_result_plot': mnemonic_query_result_plot,
                      'mnemonic_query_status': mnemonic_query_status,
                      'mnemonic_name_search_form': mnemonic_name_search_form,
                      'mnemonic_name_search_result': mnemonic_name_search_result,
                      'mnemonic_exploration_form': mnemonic_exploration_form,
                      'mnemonic_exploration_result': mnemonic_exploration_result,
                      'mnemonic_table_result': mnemonic_table_result}

    return edb_components


def get_expstart(instrument, rootname):
    """Return the exposure start time (``expstart``) for the given
    ``rootname``.

    The ``expstart`` is gathered from a query to the
    ``astroquery.mast`` service.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    rootname : str
        The rootname of the observation of interest (e.g.
        ``jw86700006001_02101_00006_guider1``).

    Returns
    -------
    expstart : float
        The exposure start time of the observation (in MJD).
    """

    if '-seg' in rootname:
        file_set_name = rootname.split('-')[0]
    else:
        file_set_name = '_'.join(rootname.split('_')[:-1])

    service = INSTRUMENT_SERVICE_MATCH[instrument]
    params = {
        'columns': 'filename, expstart',
        'filters': [{'paramName': 'fileSetName', 'values': [file_set_name]}]}
    response = Mast.service_request_async(service, params)
    result = response[0].json()

    if result['data'] == []:
        expstart = 0
        logging.warning(f"get_expstart() finds no data for {file_set_name} from {rootname}")
    else:
        expstart = min([item['expstart'] for item in result['data']])

    return expstart


def get_filenames_by_instrument(instrument, proposal, observation_id=None,
                                restriction='all', query_file=None,
                                query_response=None, other_columns=None):
    """Returns a list of filenames that match the given ``instrument``.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    proposal : str
        Proposal number to filter the results
    observation_id : str
        Observation number to filter the results
    restriction : str
        If ``all``, all filenames will be returned.  If ``public``,
        only publicly-available filenames will be returned.  If
        ``proprietary``, only proprietary filenames will be returned.
    query_file : str
        Name of a file containing a list of filenames. If provided, the
        filenames in this file will be used rather than calling mask_query_filenames_by_instrument.
        This can save a significant amount of time when the number of files is large.
    query_response : dict
        Dictionary with "data" key containing a list of filenames. This is assumed to
        essentially be the returned value from a call to mast_query_filenames_by_instrument.
        If this is provided, the call to that function is skipped, which can save a
        significant amount of time.
    other_columns : list
        List of other columns to retrieve from the MAST query

    Returns
    -------
    filenames : list
        A list of files that match the given instrument.
    col_data : dict
        Dictionary of other attributes returned from MAST. Keys are the attribute names
        e.g. 'exptime', and values are lists of the value for each filename. e.g. ['59867.6, 59867.601']
    """
    if not query_file and not query_response:
        result = mast_query_filenames_by_instrument(
            instrument, proposal, observation_id=observation_id,
            other_columns=other_columns)

    elif query_response:
        result = query_response
    elif query_file:
        with open(query_file) as fobj:
            result = fobj.readlines()

    if other_columns is not None:
        col_data = {}
        for element in other_columns:
            col_data[element] = []

    # Determine filenames to return based on restriction parameter
    if restriction == 'all':
        filenames = [item['filename'] for item in result['data']]
        if other_columns is not None:
            for keyword in other_columns:
                col_data[keyword] = [item[keyword] for item in result['data']]
    elif restriction == 'public':
        filenames = [item['filename'] for item in result['data'] if item['isRestricted'] is False]
        if other_columns is not None:
            for keyword in other_columns:
                col_data[keyword] = [item[keyword] for item in result['data'] if item['isRestricted'] is False]
    elif restriction == 'proprietary':
        filenames = [item['filename'] for item in result['data'] if item['isRestricted'] is True]
        if other_columns is not None:
            for keyword in other_columns:
                col_data[keyword] = [item[keyword] for item in result['data'] if item['isRestricted'] is True]
    else:
        raise KeyError('{} is not a valid restriction level.  Use "all", "public", or "proprietary".'.format(restriction))

    if other_columns is not None:
        return (filenames, col_data)

    return filenames


def mast_query_by_filename(instrument, filename):
    """Query MAST for all columns given an instrument and filename. Return the dict of the 'data' column

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    filename : str
        The Rootname of Interest (e.g. 'jw01068-o001_t005_nircam_clear-f356w-sub160_i2d.fits')

    Returns
    -------
    result : dict
        Dictionary of rootname data
    """
    query_filters = []
    service = INSTRUMENT_SERVICE_MATCH[instrument]

    query_filters.append({'paramName': 'filename', 'values': [filename]})
    params = {'columns': '*',
              'filters': query_filters}
    try:
        response = Mast.service_request_async(service, params)
        result = response[0].json()
    except Exception as e:
        logging.error("Mast.service_request_async- {} - {}".format(filename, e))
        result = {'data': []}

    retval = {}
    if result['data'] == []:
        logging.warning("mast_query_by_filename() returned no data for {}".format(filename))
    else:
        retval = result['data'][0]
    return retval


def mast_query_by_rootname(instrument, rootname):
    """Query MAST for all columns given an instrument and rootname. Return the dict of the 'data' column

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    rootname : str
        The Rootname of Interest (e.g. 'jw01068001001_02101_00001_nrcb2')

    Returns
    -------
    result : dict
        Dictionary of rootname data
    """
    service = INSTRUMENT_SERVICE_MATCH[instrument]

    query_filters = []

    # This query still returns nothing for the "b" and "v" stage 3 source-based filenames. I'm not sure why.
    # e.g. jw04735-o005_v000000001_nirspec_f100lp-g140h_cal.fits, jw04735-o005_b000000030_nirspec_f100lp-g140h_cal.fits
    info = filename_parser(rootname)
    if 'stage_3' not in info['filename_type']:

        if '-seg' in rootname:
            root_split = rootname.split('-')
            file_set_name = root_split[0]
            root_split = rootname.split('_')
            detector = root_split[-1]
        else:
            root_split = rootname.split('_')
            file_set_name = '_'.join(root_split[:-1])
            detector = root_split[-1]

        query_filters.append({'paramName': 'fileSetName', 'values': [file_set_name]})
        query_filters.append({'paramName': 'detector', 'values': [detector.upper()]})

    else:
        # For stage 3 files the general rule of thumb is that we want to strip off
        # everything from the rootname that comes after the name of the instrument
        index = [rootname.find(e) for e in JWST_INSTRUMENT_NAMES if rootname.find(e) != -1][0]
        name_end = index + len(instrument)
        subroot = rootname[0:name_end]
        query_filters.append({'paramName': 'fileSetName', 'values': [subroot]})

    params = {'columns': '*',
              'filters': query_filters}
    try:
        response = Mast.service_request_async(service, params)
        result = response[0].json()
    except Exception as e:
        logging.error("Mast.service_request_async- {} - {}".format(file_set_name, e))
        result = {'data': []}

    retval = {}
    if result['data'] == []:
        logging.warning("mast_query_by_rootname() returns no data for {}".format(rootname))
    else:
        retval = result['data'][0]
    return retval


def mast_query_filenames_by_instrument(instrument, proposal_id, observation_id=None, other_columns=None):
    """Query MAST for filenames for the given instrument. Return the json
    response from MAST.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).
    proposal_id : str
        Proposal ID number to use to filter the results
    observation_id : str
        Observation ID number to use to filter the results. If None, all files for the ``proposal_id`` are
        retrieved
    other_columns : list
        List of other columns to return from the MAST query

    Returns
    -------
    result : dict
        Dictionary of file information
    """
    # Be sure the instrument name is properly capitalized
    instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]

    if other_columns is None:
        columns = "filename, isRestricted"
    else:
        columns = "filename, isRestricted, " + ", ".join(other_columns)

    service = INSTRUMENT_SERVICE_MATCH[instrument]
    filters = [{'paramName': 'program', "values": [proposal_id]}]
    if observation_id is not None:
        filters.append({'paramName': 'observtn', 'values': [observation_id]})
    params = {"columns": columns, "filters": filters}
    response = Mast.service_request_async(service, params)
    result = response[0].json()
    return result


def get_filesystem_filenames(proposal=None, rootname=None,
                             file_types=None, full_path=False,
                             sort_names=True):
    """Return a list of filenames on the filesystem.

    One of proposal or rootname must be specified. If both are
    specified, only proposal is used.

    Parameters
    ----------
    proposal : str, optional
        The one- to five-digit proposal number (e.g. ``88600``).
    rootname : str, optional
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).
    file_types : list of str, optional
        If provided, only matching file extension types will be
        returned (e.g. ['fits', 'jpg']).
    full_path : bool, optional
        If set, the full path to the file will be returned instead
        of the basename.
    sort_names : bool, optional
        If set, the returned files are sorted.

    Returns
    -------
    filenames : list
        A list of filenames associated with the given ``rootname``.
    """
    if proposal is not None:
        proposal_string = '{:05d}'.format(int(proposal))

        # Level 2 only. This "proposal" block is not currently used anywhere.
        filenames = glob.glob(
            os.path.join(FILESYSTEM_DIR, 'public',
                         'jw{}'.format(proposal_string), '*/*.fits'))
        filenames.extend(glob.glob(
            os.path.join(FILESYSTEM_DIR, 'proprietary',
                         'jw{}'.format(proposal_string), '*/*.fits')))

    elif rootname is not None:
        proposal_dir = rootname[0:7]

        # Level 2 files
        observation_dir = rootname.split('_')[0]
        filenames = glob.glob(
            os.path.join(FILESYSTEM_DIR, 'public', proposal_dir,
                         observation_dir, f'{rootname}*.fits'))
        filenames.extend(glob.glob(
            os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir,
                         observation_dir, f'{rootname}*.fits')))

        # Level 3 files
        if len(filenames) == 0:
            ostr = rootname.split('-')[1].split('_')[0]
            filenames = glob.glob(
                os.path.join(FILESYSTEM_DIR, 'public', proposal_dir,
                             'L3', f'*/{ostr}/', f'{rootname}*'))
            filenames.extend(glob.glob(
                os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir,
                             'L3', f'*/{ostr}/', f'{rootname}*')))

    else:
        logging.warning("Must provide either proposal or rootname; "
                        "no files returned.")
        filenames = []

    # check suffix and file type
    good_filenames = []
    for filename in filenames:
        split_file = os.path.splitext(filename)

        # certain suffixes are always ignored
        test_suffix = split_file[0].split('_')[-1]
        if test_suffix not in IGNORED_SUFFIXES:

            # check against additional file type requirement
            test_type = split_file[-1].lstrip('.')
            if file_types is None or test_type in file_types:
                if full_path:
                    good_filenames.append(filename)
                else:
                    good_filenames.append(os.path.basename(filename))

    if sort_names:
        good_filenames.sort()
    return good_filenames


def get_filenames_by_proposal(proposal):
    """Return a list of filenames that are available in the filesystem
    for the given ``proposal``.

    Parameters
    ----------
    proposal : str
        The one- to five-digit proposal number (e.g. ``88600``).

    Returns
    -------
    filenames : list
        A list of filenames associated with the given ``proposal``.
    """
    return get_filesystem_filenames(proposal=proposal)


def get_filenames_by_rootname(rootname):
    """Return a list of filenames that are part of the given
    ``rootname``.

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    filenames : list
        A list of filenames associated with the given ``rootname``.
    """
    return get_filesystem_filenames(rootname=rootname)


def get_header_info(filename, filetype):
    """Return the header information for a given ``filename``.

    Parameters
    ----------
    filename : str
        The name of the file of interest, without the extension
        (e.g. ``'jw86600008001_02101_00007_guider2_uncal'``).
    filetype : str
        The type of the file of interest, (e.g. ``'uncal'``)

    Returns
    -------
    header_info : dict
        The FITS headers of the extensions in the given ``file``.
    """

    # Initialize dictionary to store header information
    header_info = {}

    # Open the file
    try:
        fits_filepath = filesystem_path(filename, search=f'*_{filetype}.fits')
    except FileNotFoundError as e:
        #raise e
        header_info = {}
        return header_info

    hdulist = fits.open(fits_filepath)

    # Extract header information from file
    for ext in range(0, len(hdulist)):

        # Initialize dictionary to store header information for particular extension
        header_info[ext] = {}

        # Get header
        header = hdulist[ext].header

        # Determine the extension name and type
        if ext == 0:
            header_info[ext]['EXTNAME'] = 'PRIMARY'
            header_info[ext]['XTENSION'] = 'PRIMARY'
        else:
            header_info[ext]['EXTNAME'] = header['EXTNAME']
            header_info[ext]['XTENSION'] = header['XTENSION']

        # Get list of keywords and values
        exclude_list = ['', 'COMMENT']
        header_info[ext]['keywords'] = [item for item in list(header.keys()) if item not in exclude_list]
        header_info[ext]['values'] = []
        for key in header_info[ext]['keywords']:
            header_info[ext]['values'].append(hdulist[ext].header[key])

    # Close the file
    hdulist.close()

    # Build tables
    for ext in header_info:
        data_dict = {}
        data_dict['Keyword'] = header_info[ext]['keywords']
        data_dict['Value'] = header_info[ext]['values']
        header_info[ext]['table'] = pd.DataFrame(data_dict)
        header_info[ext]['table_rows'] = header_info[ext]['table'].values
        header_info[ext]['table_columns'] = header_info[ext]['table'].columns.values

    return header_info


def get_header_info_ecsv(filename, filetype):
    """Return the header information for a given ecsv ``filename``.

    Parameters
    ----------
    filename : str
        The name of the file of interest, without the extension
        (e.g. ``'jw86600008001_02101_00007_guider2_uncal'``).
    filetype : str
        The type of the file of interest, (e.g. ``'uncal'``)

    Returns
    -------
    header_info : dict
        The FITS headers of the extensions in the given ``file``.
    """

    # Initialize dictionary to store header information
    header_info = {0: {'EXTNAME': 'PRIMARY',
                       'XTENSION': 'PRIMARY'
                       }
                   }

    # Open the file
    try:
        fits_filepath = filesystem_path(filename, search=f'*_{filetype}.ecsv')
    except FileNotFoundError as e:
        #raise e
        header_info = {}
        return header_info

    metadata = parse_meta_section_of_ecsv(fits_filepath)

    header_info[0]['keywords'] = [item for item in list(metadata.keys())]
    header_info[0]['values'] = []
    for key in header_info[0]['keywords']:
        header_info[0]['values'].append(metadata[key])

    # Populate info needed for the webpage
    data_dict = {}
    data_dict['Keyword'] = header_info[0]['keywords']
    data_dict['Value'] = header_info[0]['values']
    header_info[0]['table'] = pd.DataFrame(data_dict)
    header_info[0]['table_rows'] = header_info[0]['table'].values
    header_info[0]['table_columns'] = header_info[0]['table'].columns.values
    return header_info


def get_image_info(file_root):
    """Build and return a dictionary containing information for a given
    ``file_root``. Supports level 2 or level 3 file_root values.

    Parameters
    ----------
    file_root : str
        The rootname of the file of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    image_info : dict
        A dictionary containing various information for the given
        ``file_root``.
    """
    log_file = configure_logging("django", include_time=False)
    logging.debug(f"Getting image info for {file_root}")

    # Initialize dictionary to store information
    image_info = {}
    image_info['all_jpegs'] = []
    image_info['suffixes'] = []
    image_info['num_ints'] = {}
    image_info['available_ints'] = {}
    image_info['total_ints'] = {}
    image_info['detectors'] = set()
    image_info['level'] = 2

    # Find all the matching files
    proposal_dir = file_root[:7]
    observation_dir = file_root[:13]
    filenames = glob.glob(
        os.path.join(FILESYSTEM_DIR, 'public', proposal_dir,
                     observation_dir, f'{file_root}*.fits'))
    filenames.extend(glob.glob(
        os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir,
                     observation_dir, f'{file_root}*.fits')))

    # If the search above does not find any filenames, then we are looking
    # for a level 3 file. In that case, we need to check different directories

    # L3/ then either s/ or t/ (or others?) and then e.g. o001
    if len(filenames) == 0:
        ostr = file_root.split('-')[1].split('_')[0]
        filenames.extend(glob.glob(
            os.path.join(FILESYSTEM_DIR, 'public', proposal_dir,
                    'L3', f'*/{ostr}/', f'{file_root}*.fits')))
        filenames.extend(glob.glob(
            os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir,
                    'L3', f'*/{ostr}/', f'{file_root}*.fits')))

        # Second search, for whtlt and phot files, which are ecsv rather
        # than fits. Can't search for *.escv though, because we don't want
        # the source catalog files, which are *_cat.ecsv
        ecsv_suffixes = ['whtlt', 'phot']
        for ecsv_suffix in ecsv_suffixes:
            filenames.extend(glob.glob(
                os.path.join(FILESYSTEM_DIR, 'public', proposal_dir,
                        'L3', f'*/{ostr}/', f'{file_root}*{ecsv_suffix}.ecsv')))
            filenames.extend(glob.glob(
                os.path.join(FILESYSTEM_DIR, 'proprietary', proposal_dir,
                        'L3', f'*/{ostr}/', f'{file_root}*{ecsv_suffix}.ecsv')))
        image_info['level'] = 3

    logging.debug(f"Files before filtering: {filenames}")
    # Certain suffixes are always ignored
    filenames = [filename for filename in filenames
                 if os.path.splitext(filename)[0].split('_')[-1]
                 not in IGNORED_SUFFIXES]
    logging.debug(f"Files after filtering: {filenames}")
    image_info['all_files'] = filenames

    try:
        image_info['obsnum'] = fits.getheader(image_info['all_files'][0])['OBSERVTN']
    except (KeyError, OSError):
        image_info['obsnum'] = 'N/A'

    # Determine the jpg directory
    prev_img_filesys = configs['preview_image_filesystem']
    jpg_dir = os.path.join(prev_img_filesys, proposal_dir)

    for filename in image_info['all_files']:
        logging.debug(f"Checking file {filename}")

        parsed_fn = filename_parser(filename)

        # Get suffix information
        if parsed_fn['recognized_filename']:
            suffix = parsed_fn['suffix']
        else:
            # If the filename parser does not recognize the file, skip it
            logging.warning((f'While running get_image_info() on {filename}, the '
                             'filename_parser() failed to recognize the file pattern.'))
            continue
        logging.debug(f"\tGot suffix {suffix}")

        # For crf or crfints suffixes, we need to also include the association value
        # in the suffix, so that preview images can be found later.
        if ((image_info['level'] == 2) & (suffix in SUFFIXES_TO_ADD_ASSOCIATION)):
            assn = filename.split('_')[-2]
            suffix = f'{assn}_{suffix}'

        image_info['suffixes'].append(suffix)

        # Determine JPEG file location
        # Level 2 files will end with "integ?.jpg", but level 3 files typically will not
        jpg_filename = os.path.basename(os.path.splitext(filename)[0] + '_integ0.jpg')
        jpg_filepath = os.path.join(jpg_dir, jpg_filename)

        if os.path.isfile(jpg_filepath):
            # Level 2 files
            jpgs = glob.glob(os.path.join(prev_img_filesys, proposal_dir, f'{file_root}*_{suffix}_integ*.jpg'))

            # Record how many integrations have been saved as preview images per filetype
            image_info['available_ints'][suffix] = sorted(set([int(jpg.split('_')[-1].replace('.jpg', '').replace('integ', '')) for jpg in jpgs]))
            image_info['num_ints'][suffix] = len(image_info['available_ints'][suffix])
            image_info['all_jpegs'].append(jpg_filepath)
        else:
            # Level 3 files
            jpg_filename = os.path.basename(os.path.splitext(filename)[0] + '.jpg')
            jpg_filepath = os.path.join(jpg_dir, jpg_filename)

            # Will there ever be more than one jpg for a level 3 file/suffix?
            jpgs = glob.glob(os.path.join(prev_img_filesys, proposal_dir, f'{file_root}*_{suffix}*jpg'))

            image_info['available_ints'][suffix] = ['N/A']
            image_info['num_ints'][suffix] = len(image_info['available_ints'][suffix])
            image_info['all_jpegs'].append(jpg_filepath)

        # Record how many integrations exist per filetype.
        if ((suffix not in SUFFIXES_WITH_AVERAGED_INTS) and (image_info['available_ints'][suffix] != ['N/A'])):
            header = fits.getheader(filename)
            nint = header['NINTS']
            if 'time_series' in parsed_fn['filename_type']:
                # time series segments need special handling
                intstart = header.get('INTSTART', 1)
                intend = header.get('INTEND', nint)
                image_info['total_ints'][suffix] = intend - intstart + 1
            elif image_info['num_ints'][suffix] > nint:
                # so do data cubes:
                # get max ints from data shape in first extension
                sci_header = fits.getheader(filename, ext=1)
                n_frame = sci_header.get('NAXIS3', nint)

                # for groups with multiple cubes (e.g. miri with ifu
                # short and long), make sure we keep the highest total
                if 'suffix' in image_info['total_ints']:
                    if n_frame > image_info['total_ints'][suffix]:
                        image_info['total_ints'][suffix] = n_frame
                else:
                    image_info['total_ints'][suffix] = n_frame
            else:
                image_info['total_ints'][suffix] = nint
        else:
            image_info['total_ints'][suffix] = 1

        # Record the detector used
        image_info['detectors'].add(parsed_fn.get('detector', 'Unknown'))

    return image_info


def get_explorer_extension_names(fits_file, filetype):
    """ Return a list of Extensions that can be explored interactively

    Parameters
    ----------
    filename : str
        The name of the file of interest, without the extension
        (e.g. ``'jw86600008001_02101_00007_guider2_uncal'``).
    filetype : str
        The type of the file of interest, (e.g. ``'uncal'``)

    Returns
    -------
    extensions : list
        List of Extensions found in header and allowed to be Explored (extension type "IMAGE")
    """

    header_info = get_header_info(fits_file, filetype)

    extensions = [header_info[extension]['EXTNAME'] for extension in header_info if header_info[extension]['XTENSION'] == 'IMAGE']
    return extensions


def get_instrument_proposals(instrument):
    """Return a list of proposals for the given instrument

    Parameters
    ----------
    instrument : str
        Name of the JWST instrument, with first letter capitalized
        (e.g. ``Fgs``)

    Returns
    -------
    inst_proposals : list
        List of proposals for the given instrument
    """
    tap_service = vo.dal.TAPService(STSCI_VO_URL)
    tap_results = tap_service.search(f"""select distinct prpID from CaomObservation where collection='JWST'
                                     and maxLevel>0 and insName like '{instrument.lower()}%'""")
    prop_table = tap_results.to_table()
    if 'prpID' in prop_table.columns:
        proposals = prop_table['prpID'].data
    elif 'prpid' in prop_table.columns:
        proposals = prop_table['prpid'].data
    else:
        proposals = []
    inst_proposals = sorted(proposals.compressed(), reverse=True)
    return inst_proposals


def get_instrument_looks(instrument, sort_as=None, proposal=None,
                         look=None, exp_type=None, cat_type=None,
                         additional_keys=None):
    """Return a table of looks information for the given instrument.

    Parameters
    ----------
    instrument : str
        Name of the JWST instrument.
    sort_as : {'ascending', 'descending', 'recent'}
        Sorting method for output table. Ascending and descending
        options refer to root file name; recent sorts by observation
        start.
    proposal : str, optional
        Proposal to match.  Used as a 'starts with' filter.
    look : {'new', 'viewed'}, optional
        If set to None, all viewed values are returned. If set to
        'viewed', only viewed data is returned. If set to 'new', only
        new data is returned.
    exp_type : str, optional
        Set to filter by exposure type.
    cat_type : str, optional
        Set to filter by proposal category.
    additional_keys : list of str, optional
        Additional model attribute names for information to return.

    Returns
    -------
    keys : list of str
        Report values returned for the given instrument.
    looks : list of dict
        List of looks information by root file for the given instrument.
    """
    # standardize input
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]

    # required keys
    keys = ['root_name']

    # optional keys by instrument
    keys += REPORT_KEYS_PER_INSTRUMENT[inst.lower()]

    # add any additional keys
    key_set = set(keys)
    if additional_keys is not None:
        for key in additional_keys:
            if key not in key_set:
                keys.append(key)

    # get filtered file info
    root_file_info = filter_root_files(
        instrument=instrument, sort_as=sort_as, look=look,
        exp_type=exp_type, cat_type=cat_type, proposal=proposal)

    looks = []
    for root_file in root_file_info:
        result = dict()
        for key in keys:
            try:
                # try the root file table
                value = root_file[key]
            except KeyError:
                value = ''

            # make sure value can be serialized
            if type(value) not in [str, float, int, bool]:
                value = str(value)

            result[key] = value
        looks.append(result)

    return keys, looks


def get_preview_images_by_proposal(proposal):
    """Return a list of preview images available in the filesystem for
    the given ``proposal``.

    Parameters
    ----------
    proposal : str
        The one- to five-digit proposal number (e.g. ``88600``).

    Returns
    -------
    preview_images : list
        A list of preview images available in the filesystem for the
        given ``proposal``.
    """

    proposal_string = '{:05d}'.format(int(proposal))
    preview_images = glob.glob(os.path.join(PREVIEW_IMAGE_FILESYSTEM, 'jw{}'.format(proposal_string), '*'))
    preview_images = [os.path.basename(preview_image) for preview_image in preview_images]
    preview_images = [item for item in preview_images if os.path.splitext(item)[0].split('_')[-1] not in IGNORED_SUFFIXES]

    return preview_images


def get_preview_images_by_rootname(rootname):
    """Return a list of preview images available in the filesystem for
    the given ``rootname``.

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    preview_images : list
        A list of preview images available in the filesystem for the
        given ``rootname``.
    """

    proposal = rootname.split('_')[0].split('jw')[-1][0:5]
    preview_images = sorted(glob.glob(os.path.join(
        PREVIEW_IMAGE_FILESYSTEM,
        'jw{}'.format(proposal),
        '{}*'.format(rootname))))
    preview_images = [os.path.basename(preview_image) for preview_image in preview_images]
    preview_images = [item for item in preview_images if os.path.splitext(item)[0].split('_')[-1] not in IGNORED_SUFFIXES]

    return preview_images


def get_detectors_by_rootname(rootname):
    """
    Return a list of exposures with the same rootname as the provided rootname, but
    including all available detectors.

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    detector_list : list
        A list of images that are part of the same exposure but with all detectors.
        e.g. ['jw01068001001_02101_00001_nrca1', 'jw01068001001_02101_00001_nrca2']
    """
    detector_list = []
    search_rootname = rootname[:25]
    filenames = get_filenames_by_rootname(search_rootname)
    for filename in filenames:
        bare_name = Path(filename).name
        name_items = bare_name.split("_")
        detector_name = "_".join(name_items[:4])
        if detector_name not in detector_list:
            detector_list.append(detector_name)
    return detector_list


def get_proposals_by_category(instrument):
    """Return a dictionary of program numbers and category type
    Parameters
    ----------
    instrument : str
        Name of the JWST instrument, with first letter capitalized
        (e.g. ``Fgs``)
    Returns
    -------
    category_sorted_dict : dict
        Dictionary with program number as the key and program category as the value
    """
    tap_service = vo.dal.TAPService(STSCI_VO_URL)
    tap_results = tap_service.search(f"""select distinct prpID,prpProject from CaomObservation where collection='JWST'
                                     and maxLevel>0 and insName like '{instrument.lower()}%'""")
    # Put the results into an astropy Table
    prop_table = tap_results.to_table()

    # Convert to a dictionary
    try:
        proposals_by_category = {int(d['prpID']): d['prpProject'] for d in prop_table}
    except KeyError as k:
        proposals_by_category = {int(d['prpid']): d['prpproject'] for d in prop_table}
    return proposals_by_category


def get_proposal_info(filepaths):
    """Builds and returns a dictionary containing various information
    about the proposal(s) that correspond to the given ``filepaths``.

    The information returned contains such things as the number of
    proposals, the paths to the corresponding thumbnails, and the total
    number of files.

    Parameters
    ----------
    filepaths : list
        A list of full paths to files of interest.

    Returns
    -------
    proposal_info : dict
        A dictionary containing various information about the
        proposal(s) and files corresponding to the given ``filepaths``.
    """

    # Gather thumbnails and counts for proposals
    proposals, thumbnail_paths, num_files, observations = [], [], [], []
    for filepath in filepaths:
        proposal = filepath.split('/')[-1][2:7]
        if proposal not in proposals:
            thumbnail_paths.append(os.path.join('jw{}'.format(proposal), 'jw{}.thumb'.format(proposal)))
            files_for_proposal = [item for item in filepaths if 'jw{}'.format(proposal) in item]

            obsnums = []
            for fname in files_for_proposal:
                file_info = filename_parser(fname)
                if file_info['recognized_filename']:
                    # Wrap in a try/except because level 3 files do not have an 'observation' key.
                    # That's ok. We will ignore those files.
                    try:
                        obs = file_info['observation']
                        obsnums.append(obs)
                    except KeyError:
                        logging.info(f'\n\nFile {fname} has no observation info from the filename_parser')
                else:
                    logging.warning((f'While running get_proposal_info() for a program {proposal}, {fname} '
                                     'was not recognized by the filename_parser().'))

            obsnums = sorted(obsnums)
            observations.extend(obsnums)
            num_files.append(len(files_for_proposal))
            proposals.append(proposal)

    # Put the various information into a dictionary of results
    proposal_info = {}
    proposal_info['num_proposals'] = len(proposals)
    proposal_info['proposals'] = proposals
    proposal_info['thumbnail_paths'] = thumbnail_paths
    proposal_info['num_files'] = num_files
    proposal_info['observation_nums'] = observations

    return proposal_info


def get_rootnames_for_proposal(proposal):
    """Return a list of rootnames for the given proposal (all instruments)

    Parameters
    ----------
    proposal : int or str
        Proposal ID number

    Returns
    -------
    rootnames : list
        List of rootnames for the given instrument and proposal number
    """
    tap_service = vo.dal.TAPService(STSCI_VO_URL)
    tap_results = tap_service.search(f"""select observationID from dbo.CaomObservation where
                                     collection='JWST' and prpID='{int(proposal)}'""", maxrec=100000)
    prop_table = tap_results.to_table()
    if 'observationID' in prop_table.columns:
        rootnames = prop_table['observationID'].data
    elif 'observationid' in prop_table.columns:
        rootnames = prop_table['observationid'].data
    else:
        rootnames = []
    return rootnames.compressed()


def get_rootnames_from_query(parameters):
    """Return a query_set of RootFileInfo given requested filter parameters.

    Parameters
    ----------
    parameters: dict
        A dictionary containing keys of QUERY_CONFIG_KEYS, some of which are dictionaries:


    Returns
    -------
    filtered_rootnames : list
        A list of all root filenames filtered from the given parameters
    """

    filtered_rootnames = []
    DATE_FORMAT = "%Y/%m/%d %I:%M%p"  # noqa n806

    # Parse DATE_RANGE string into correct format
    date_range = parameters[QueryConfigKeys.DATE_RANGE]
    start_date_range, stop_date_range = date_range.split(" to ")
    # Parse the strings into datetime objects
    start_datetime = datetime.strptime(start_date_range, DATE_FORMAT)
    stop_datetime = datetime.strptime(stop_date_range, DATE_FORMAT)
    # store as astroquery Time objects in isot format to be used in filter (with mjd format)
    start_time = Time(start_datetime.isoformat(), format="isot")
    stop_time = Time(stop_datetime.isoformat(), format="isot")

    # Each Query Selection is Instrument specific
    for inst in parameters[QueryConfigKeys.INSTRUMENTS]:
        # Make sure instruments are of the proper format for the archive query
        inst = inst.lower()
        current_ins_rootfileinfos = RootFileInfo.objects.filter(instrument=JWST_INSTRUMENT_NAMES_MIXEDCASE[inst])

        # General fields
        sort_type = parameters[QueryConfigKeys.SORT_TYPE]
        look_status = parameters[QueryConfigKeys.LOOK_STATUS]

        # Get a queryset of all observations STARTING within our date range
        current_ins_rootfileinfos = current_ins_rootfileinfos.filter(
            expstart__gte=start_time.mjd)
        current_ins_rootfileinfos = current_ins_rootfileinfos.filter(
            expstart__lte=stop_time.mjd)

        if len(look_status) == 1:
            viewed = (look_status[0] == 'VIEWED')
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(viewed=viewed)
        proposal_category = parameters[QueryConfigKeys.PROPOSAL_CATEGORY]
        if len(proposal_category) > 0:
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(obsnum__proposal__category__in=proposal_category)

        # Instrument fields
        inst_anomalies = parameters[QueryConfigKeys.ANOMALIES][inst]
        inst_aperture = parameters[QueryConfigKeys.APERTURES][inst]
        inst_detector = parameters[QueryConfigKeys.DETECTORS][inst]
        inst_exp_type = parameters[QueryConfigKeys.EXP_TYPES][inst]
        inst_filter = parameters[QueryConfigKeys.FILTERS][inst]
        inst_grating = parameters[QueryConfigKeys.GRATINGS][inst]
        inst_pupil = parameters[QueryConfigKeys.PUPILS][inst]
        inst_read_patt = parameters[QueryConfigKeys.READ_PATTS][inst]
        inst_subarray = parameters[QueryConfigKeys.SUBARRAYS][inst]

        if (inst_aperture != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(aperture__in=inst_aperture)
        if (inst_detector != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(detector__in=inst_detector)
        if (inst_exp_type != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(exp_type__in=inst_exp_type)
        if (inst_filter != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(filter__in=inst_filter)
        if (inst_grating != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(grating__in=inst_grating)
        if (inst_pupil != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(pupil__in=inst_pupil)
        if (inst_read_patt != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(read_patt__in=inst_read_patt)
        if (inst_subarray != []):
            current_ins_rootfileinfos = current_ins_rootfileinfos.filter(subarray__in=inst_subarray)
        if (inst_anomalies != []):
            anomaly_rootfileinfos = RootFileInfo.objects.none()
            for anomaly in inst_anomalies:
                # If the rootfile info has any of the marked anomalies we want it
                anomaly_filter = "anomalies__" + str(anomaly).lower()
                anomaly_rootfileinfos = anomaly_rootfileinfos.union(current_ins_rootfileinfos.filter(**{anomaly_filter: True}))
            current_ins_rootfileinfos = current_ins_rootfileinfos.intersection(anomaly_rootfileinfos)

        # sort as desired
        if sort_type.upper() == 'ASCENDING':
            current_ins_rootfileinfos = current_ins_rootfileinfos.order_by('root_name')
        elif sort_type.upper() == 'RECENT':
            current_ins_rootfileinfos = current_ins_rootfileinfos.order_by('-expstart', 'root_name')
        elif sort_type.upper() == 'OLDEST':
            current_ins_rootfileinfos = current_ins_rootfileinfos.order_by('expstart', 'root_name')
        else:
            current_ins_rootfileinfos = current_ins_rootfileinfos.order_by('-root_name')

        # Django is doing something wonky here.  I can't call values_list with a single parameter, even with 'flat=True' as per Django Docs.
        # TODO: This is hacky and should be fixed.
        filtered_list = list(current_ins_rootfileinfos.values_list('root_name', 'expstart'))
        rootnames = [name[0] for name in filtered_list]
        filtered_rootnames.extend(rootnames)

    return filtered_rootnames


def get_thumbnails_by_proposal(proposal):
    """Return a list of thumbnails available in the filesystem for the
    given ``proposal``.

    Parameters
    ----------
    proposal : str
        The one- to five-digit proposal number (e.g. ``88600``).

    Returns
    -------
    thumbnails : list
        A list of thumbnails available in the filesystem for the given
        ``proposal``.
    """

    proposal_string = '{:05d}'.format(int(proposal))
    thumbnails = glob.glob(os.path.join(THUMBNAIL_FILESYSTEM, 'jw{}'.format(proposal_string), '*'))
    thumbnails = [os.path.basename(thumbnail) for thumbnail in thumbnails]

    return thumbnails


def get_thumbnail_by_rootname(rootname):
    """Return the most appropriate existing thumbnail basename available in the filesystem for the given ``rootname``.
    We generate thumbnails only for 'rate' and 'dark' files.
    Check if these files exist in the thumbnail filesystem.
    In the case where neither rate nor dark thumbnails are present, revert to 'none'

    Parameters
    ----------
    rootname : str
        The rootname of interest (e.g.
        ``jw86600008001_02101_00007_guider2``).

    Returns
    -------
    thumbnail_basename : str
        A thumbnail_basename available in the filesystem for the given ``rootname``.
    """
    log_file = configure_logging("django", include_time=False)
    logging.debug(f"Getting thumbnails for {rootname}")

    proposal = rootname.split('_')[0].split('jw')[-1][0:5]
    thumbnails = sorted(glob.glob(os.path.join(
        THUMBNAIL_FILESYSTEM,
        'jw{}'.format(proposal),
        '{}*'.format(rootname))))

    thumbnails = [os.path.basename(thumbnail) for thumbnail in thumbnails]
    thumbnail_basename = 'none'

    if len(thumbnails) > 0:
        preferred = [thumb for thumb in thumbnails if 'rate' in thumb]
        if len(preferred) == 0:
            preferred = [thumb for thumb in thumbnails if 'dark' in thumb]
        if len(preferred) == 0:
            level3_suffixes = ['x1d', 'x1dints', 'phot', 'whtlt', 's2d', 's3d',
                               'i2d', 'crf', 'cal', 'psfsub', 'psfstack', 'ami-oi',
                               'amimulti-oi', 'aminorm-oi']
            for suffix in level3_suffixes:
                preferred = [thumb for thumb in thumbnails if suffix in thumb]
                if len(preferred) > 0:
                    break
        if len(preferred) > 0:
            thumbnail_basename = os.path.basename(preferred[0])
    return thumbnail_basename


def import_all_models():
    """
    Dynamically import and return all Django models as a dictionary.
    Keys are model names (as strings), and values are model classes.

    Returns
    -------
    models : dict
        Keys are model names, values are model classes
    """
    models = {}
    for model in apps.get_app_config('jwql').get_models():
        models[model.__name__] = model
    return models


def log_into_mast(request):
    """Login via astroquery.mast if user authenticated in web app.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    """
    if Mast.authenticated():
        return True

    # get the MAST access token if present
    access_token = str(get_mast_token(request))

    # authenticate with astroquery.mast if necessary
    # nosec comment added to ignore bandit security check
    if access_token != 'None':  # nosec
        Mast.login(token=access_token)
        return Mast.authenticated()
    else:
        return False


def parse_meta_section_of_ecsv(filepath):
    """Extract the meta section from a level 3 ecsv file (i.e. whtlt or phot)

    Parameters
    ----------
    filepath : str
        Name of the ecsv file to read in

    Returns
    -------
    result : dict
        Dictionary of metadata
    """
    result = {}
    in_meta = False
    pattern = r'\{(\w+):\s*([^}]+)\}'

    with open(filepath, 'r') as f:
        for line in f:
            # Detect start of meta section
            if line.strip() == '# meta: !!omap':
                in_meta = True
                continue

            # Stop when we hit another top-level section or non-comment line
            if in_meta:
                if not line.startswith('#'):
                    break
                if re.match(r'^# \w+:', line) and 'meta' not in line:
                    break

            if in_meta:
                match = re.search(pattern, line)
                if match:
                    key = match.group(1)
                    value = match.group(2).strip()
                    if value == 'null':
                        value = None
                    result[key] = value

    return result


def proposal_rootnames_by_instrument(proposal):
    """Retrieve the rootnames for a given proposal for all instruments and return
    as a dictionary with instrument names as keys. Instruments not used in the proposal
    will not be present in the dictionary.

    proposal : int or str
        Proposal ID number

    Returns
    -------
    rootnames : dict
        Dictionary of rootnames with instrument names as keys
    """
    rootnames = {}
    for instrument in JWST_INSTRUMENT_NAMES:
        names = get_rootnames_for_instrument_proposal(instrument, proposal)
        if len(names) > 0:
            rootnames[instrument] = names
    return rootnames


def random_404_page():
    """Randomly select one of the various 404 templates for JWQL

    Returns
    -------
    random_template : str
        Filename of the selected template
    """
    templates = ['404_space.html', '404_spacecat.html']
    choose_page = np.random.choice(len(templates))
    random_template = templates[choose_page]

    return random_template


def retrieve_filelist(filename):
    """Return a list of all thumbnail files in the filesystem from
    a list file.

    Parameters
    ----------
    filename : str
        Name of a text file containing a list of files
    """
    with open(filename) as fobj:
        file_list = fobj.read().splitlines()
    return file_list


def text_scrape(prop_id):
    """Scrapes the Proposal Information Page.

    Parameters
    ----------
    prop_id : int
        Proposal ID

    Returns
    -------
    program_meta : dict
        Dictionary containing information about program
    """
    # Ensure prop_id is a 5-digit string
    prop_id = str(prop_id).zfill(5)

    # Generate url
    url = f'https://www.stsci.edu/jwst-program-info/program/?program={prop_id}'
    html = BeautifulSoup(requests.get(url).text, 'lxml')
    not_available = "not available via this interface" in html.text
    not_available |= "temporarily unable" in html.text
    not_available |= "internal error" in html.text

    program_meta = {}
    program_meta['prop_id'] = prop_id
    if not not_available:
        lines = html.findAll('p')
        lines = [str(line) for line in lines]

        program_meta['phase_two'] = '<a href=https://www.stsci.edu/jwst/phase2-public/{}.pdf target="_blank"> Phase Two</a>'

        if prop_id[0] == '0':
            program_meta['phase_two'] = program_meta['phase_two'].format(prop_id[1:])
        else:
            program_meta['phase_two'] = program_meta['phase_two'].format(prop_id)

        program_meta['phase_two'] = BeautifulSoup(program_meta['phase_two'], 'html.parser')

        links = html.findAll('a')

        proposal_type = links[3].contents[0]

        program_meta['prop_type'] = proposal_type

        # Scrape for titles/names/contact persons
        for line in lines:
            if 'Title' in line:
                start = line.find('</b>') + 4
                end = line.find('<', start)
                title = line[start:end]
                program_meta['title'] = title

            if 'Principal Investigator:' in line:
                start = line.find('</b>') + 4
                end = line.find('<', start)
                pi = line[start:end]
                program_meta['pi'] = pi

            if 'Program Coordinator' in line:
                start = line.find('</b>') + 4
                mid = line.find('<', start)
                end = line.find('>', mid) + 1
                pc = line[mid:end] + line[start:mid] + '</a>'
                program_meta['pc'] = pc

            if 'Contact Scientist' in line:
                start = line.find('</b>') + 4
                mid = line.find('<', start)
                end = line.find('>', mid) + 1
                cs = line[mid:end] + line[start:mid] + '</a>'
                program_meta['cs'] = BeautifulSoup(cs, 'html.parser')

            if 'Program Status' in line:
                start = line.find('<a')
                end = line.find('</a>')
                ps = line[start:end]

                # beautiful soupify text to build absolute link
                ps = BeautifulSoup(ps, 'html.parser')
                ps_link = ps('a')[0]
                ps_link['href'] = 'https://www.stsci.edu' + ps_link['href']
                ps_link['target'] = '_blank'
                program_meta['ps'] = ps_link
    else:
        program_meta['phase_two'] = 'N/A'
        program_meta['prop_type'] = 'N/A'
        program_meta['title'] = 'Proposal not available or does not exist'
        program_meta['pi'] = 'N/A'
        program_meta['pc'] = 'N/A'
        program_meta['cs'] = 'N/A'
        program_meta['ps'] = 'N/A'

    return program_meta


def thumbnails_ajax(inst, proposal, obs_num=None):
    """Generate a page that provides data necessary to render the
    ``thumbnails`` template.

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    proposal : str
        Number of APT proposal to filter

    Returns
    -------
    data_dict : dict
        Dictionary of data needed for the ``thumbnails`` template
    """
    log_file = configure_logging("django", include_time=False)
    logging.debug(f"Collecting thumbnails for {inst} {proposal} {obs_num}")
    # generate the list of all obs of the proposal here, so that the list can be
    # properly packaged up and sent to the js scripts. but to do this, we need to call
    # get_rootnames_for_instrument_proposal, which is largely repeating the work done by
    # get_filenames_by_instrument above. can we use just get_rootnames? we would have to
    # filter results by obs_num after the call and after obs_list is created.
    # But we need the filename list below...hmmm...so maybe we need to do both
    all_rootnames = get_rootnames_for_instrument_proposal(inst, proposal)
    logging.debug(f"Associated roots are {all_rootnames}")
    all_obs = []
    for root in all_rootnames:
        logging.debug(f"Collecting info for {root}")
        try:
            # Wrap in try/except because level 3 rootnames won't have an observation
            # number returned by the filename_parser. That's fine, we're not interested
            # in those files anyway.
            file_info = filename_parser(root)
            if file_info['recognized_filename']:
                try:
                    all_obs.append(file_info['observation'])
                except KeyError:
                    pass
            else:
                logging.warning((f'While running thumbnails_ajax() on root {root}, '
                                 'filename_parser() failed to recognize the file pattern.'))
        except Exception as e:
            logging.warning(f"{root} failed filename parser with {e}")

    obs_list = sorted(list(set(all_obs)))

    # Get the available files for the instrument
    filenames, columns = get_filenames_by_instrument(
        inst, proposal, observation_id=obs_num, other_columns=['expstart', 'exp_type']
    )
    logging.debug(f"filenames are {filenames}")

    # Get set of unique rootnames
    rootnames = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filenames])
    logging.debug(f"rootnames are {rootnames}")

    # Initialize dictionary that will contain all needed data
    data_dict = {'inst': inst,
                 'file_data': dict()}

    # Create keys to organize data by observation number
    if obs_num is None:
        obs_loop_list = obs_list
    else:
        obs_loop_list = [str(obs_num).zfill(3)]

    for obsnum in obs_loop_list:
        data_dict['file_data'][obsnum] = {}
        data_dict['file_data'][obsnum]['stage_2'] = {}
        data_dict['file_data'][obsnum]['stage_3'] = {}
        data_dict['file_data'][obsnum]['stage_2']['files'] = {}
        data_dict['file_data'][obsnum]['stage_3']['files'] = {}

    exp_types = set()
    exp_groups = set()

    # Gather data for each rootname, and construct a list of all observations
    # in the proposal
    for rootname in rootnames:
        logging.debug(f"Gathering data for {rootname}")

        # Parse filename
        filename_dict = filename_parser(rootname)
        if filename_dict['recognized_filename']:
            # Weed out file types that are not supported by generate_preview_images.
            # Source-based WFSS filenames are no longer supported, but the files are still in MAST.
            # Skip these. e.g. jw02279-o001_s000000123
            if 'stage_3_wfss_source_id' in filename_dict['filename_type']:
                continue
        else:
            # Skip over files not recognized by the filename_parser
            continue

        # Get the stage of the rootname so that we can add it to the right place
        # in the nested dictionary
        if 'stage_3' not in filename_dict['filename_type']:
            stage = 'stage_2'
        else:
            stage = 'stage_3'

        # Get list of available filenames and exposure start times. All files with a given
        # rootname will have the same exposure start time, so just keep the first.
        available_files = []
        exp_start = None
        exp_type = None
        for i, item in enumerate(filenames):
            if rootname in item:
                available_files.append(item)
                if exp_start is None:
                    exp_start = columns['expstart'][i]
                    exp_type = columns['exp_type'][i]
        exp_types.add(exp_type)

        # These attributes are stored by rootname in the Model db.  Save them with the data_dict
        # THUMBNAIL_FILTER_LOOK is boolean accessed according to a viewed flag
        try:
            root_file_info = RootFileInfo.objects.get(root_name=rootname)
            viewed = THUMBNAIL_FILTER_LOOK[root_file_info.viewed]
            filter_type = root_file_info.filter
            pupil_type = root_file_info.pupil
            grating_type = root_file_info.grating
        except RootFileInfo.DoesNotExist:
            viewed = THUMBNAIL_FILTER_LOOK[0]
            filter_type = ""
            pupil_type = ""
            grating_type = ""

        # Add to list of all exposure groups
        exp_groups.add(filename_dict['group_root'])

        # Add data to dictionary
        # Work around for stage 3 files where different suffixes can be from different observations,
        # but RootFileInfo forces all suffixes to have the same observation number. If we're loading
        # an "all obs" page then all of the proper obsnum keys will be in the dict. If we are loading
        # a page for a single observation, just use that observation number. No need to retrieve it
        # from the filename_parser info.
        if obs_num is None:
            obsnum = filename_dict['observation']
        else:
            obsnum = obs_num
        data_dict['file_data'][obsnum][stage]['files'][rootname] = {}
        data_dict['file_data'][obsnum][stage]['files'][rootname]['filename_dict'] = filename_dict
        data_dict['file_data'][obsnum][stage]['files'][rootname]['available_files'] = available_files
        data_dict['file_data'][obsnum][stage]['files'][rootname]['viewed'] = viewed
        data_dict['file_data'][obsnum][stage]['files'][rootname]['exp_type'] = exp_type
        data_dict['file_data'][obsnum][stage]['files'][rootname]['thumbnail'] = get_thumbnail_by_rootname(rootname)
        data_dict['file_data'][obsnum][stage]['files'][rootname]['filter'] = filter_type
        data_dict['file_data'][obsnum][stage]['files'][rootname]['pupil'] = pupil_type
        data_dict['file_data'][obsnum][stage]['files'][rootname]['grating'] = grating_type

        try:
            data_dict['file_data'][obsnum][stage]['files'][rootname]['expstart'] = exp_start
            data_dict['file_data'][obsnum][stage]['files'][rootname]['expstart_iso'] = Time(exp_start, format='mjd').iso.split('.')[0]
        except (ValueError, TypeError) as e:
            logging.warning("Unable to populate exp_start info for {}".format(rootname))
            logging.warning(e)
        except KeyError:
            logging.warning("KeyError with get_expstart for {}".format(rootname))

    # Extract information for sorting with dropdown menus
    # (Don't include the proposal as a sorting parameter if the proposal has already been specified)
    detectors, proposals, visits, filters, pupils, gratings = [], [], [], [], [], []
    for obsnum in list(data_dict['file_data'].keys()):
        obstime_set = False
        for stage in ['stage_2', 'stage_3']:
            for i, rootname in enumerate(list(data_dict['file_data'][obsnum][stage]['files'].keys())):
                proposals.append(data_dict['file_data'][obsnum][stage]['files'][rootname]['filename_dict']['program_id'])
                try:  # Some rootnames cannot parse out detectors
                    detectors.append(data_dict['file_data'][obsnum][stage]['files'][rootname]['filename_dict']['detector'])
                except KeyError:
                    pass
                try:  # Some rootnames cannot parse out visit
                    visits.append(data_dict['file_data'][obsnum][stage]['files'][rootname]['filename_dict']['visit'])
                except KeyError:
                    pass
                try:
                    filters.append(data_dict['file_data'][obsnum][stage]['files'][rootname]['filter'])
                except KeyError:
                    pass
                try:
                    pupils.append(data_dict['file_data'][obsnum][stage]['files'][rootname]['pupil'])
                except KeyError:
                    pass
                try:
                    gratings.append(data_dict['file_data'][obsnum][stage]['files'][rootname]['grating'])
                except KeyError:
                    pass

                # Set a representative exp_time for each observation. To be used for
                # sorting later. It doesn't matter which exposure's exp_time we use,
                # since all exposures for a given observation are taken together. There's
                # no mixing of observations.
                if ((i == 0) and (not obstime_set)):
                    data_dict['file_data'][obsnum]['obs_exp_time'] = data_dict['file_data'][obsnum][stage]['files'][rootname]['expstart']
                    obstime_set = True

    if proposal is not None:
        dropdown_menus = {'detector': sorted(detectors),
                          'look': THUMBNAIL_FILTER_LOOK,
                          'exp_type': sorted(exp_types),
                          'visit': sorted(visits),
                          'stage': ['Stage 2', 'Stage 3']}
    else:
        dropdown_menus = {'detector': sorted(detectors),
                          'proposal': sorted(proposals),
                          'look': THUMBNAIL_FILTER_LOOK,
                          'exp_type': sorted(exp_types),
                          'visit': sorted(visits),
                          'stage': ['Stage 2', 'Stage 3']}
    if filters is not None:
        dropdown_menus['filter'] = sorted(filters)
    if pupils is not None:
        dropdown_menus['pupil'] = sorted(pupils)
    if gratings is not None:
        dropdown_menus['grating'] = sorted(gratings)

    data_dict['tools'] = MONITORS
    data_dict['dropdown_menus'] = dropdown_menus
    data_dict['prop'] = proposal

    # Order dictionary by descending expstart time. Start by ordering the observations, using
    # the representative obs_exp_time. Then order the entries within each observation.
    sorted_file_data = {k: v for k, v in sorted(data_dict['file_data'].items(), key=lambda item: item[1]['obs_exp_time'], reverse=True)}

    # Sort separately for stage_2 and stage_3 files
    for key in sorted_file_data:
        for stage_key in ['stage_2', 'stage_3']:
            value = sorted_file_data[key][stage_key]
            files = value['files']
            sorted_file_data[key][stage_key]['files'] = {k: v for k, v in sorted(files.items(), key=lambda item: item[1]['expstart'], reverse=True)}

    data_dict['file_data'] = sorted_file_data

    # Add list of observation numbers and group roots
    data_dict['obs_list'] = obs_list
    data_dict['exp_groups'] = sorted(exp_groups)

    return data_dict


def thumbnails_query_ajax(rootnames):
    """Generate a page that provides data necessary to render the
    ``thumbnails`` template.

    Parameters
    ----------
    rootnames : list of strings

    Returns
    -------
    data_dict : dict
        Dictionary of data needed for the ``thumbnails`` template
    """
    # Initialize dictionary that will contain all needed data
    data_dict = {'inst': 'all',
                 'file_data': dict()}
    exp_groups = set()

    # Gather data for each rootname
    for rootname in rootnames:
        # fit expected format for get_filenames_by_rootname()
        split_name = rootname.split("_")
        try:
            rootname = split_name[0] + '_' + split_name[1] + '_' + split_name[2] + '_' + split_name[3]
        except IndexError:
            continue

        # Parse filename
        filename_dict = filename_parser(rootname)

        if filename_dict['recognized_filename']:
            # Add to list of all exposure groups
            exp_groups.add(filename_dict['group_root'])
        else:
            logging.warning((f'While running thumbnails_query_ajax() on rootname {rootname}, '
                             'filename_parser() failed to recognize the file pattern.'))
            continue

        try:
            root_file_info = RootFileInfo.objects.get(root_name=rootname)
            filter_type = root_file_info.filter
            pupil_type = root_file_info.pupil
            grating_type = root_file_info.grating
        except RootFileInfo.DoesNotExist:
            filter_type = ""
            pupil_type = ""
            grating_type = ""

        # Get list of available filenames
        available_files = get_filenames_by_rootname(rootname)

        # Add data to dictionary
        data_dict['file_data'][rootname] = {}
        data_dict['file_data'][rootname]['inst'] = JWST_INSTRUMENT_NAMES_MIXEDCASE[filename_dict['instrument']]
        data_dict['file_data'][rootname]['filename_dict'] = filename_dict
        data_dict['file_data'][rootname]['available_files'] = available_files
        root_file_info = RootFileInfo.objects.get(root_name=rootname)
        exp_start = root_file_info.expstart
        data_dict['file_data'][rootname]['expstart'] = exp_start
        data_dict['file_data'][rootname]['expstart_iso'] = Time(exp_start, format='mjd').iso.split('.')[0]
        data_dict['file_data'][rootname]['suffixes'] = []
        data_dict['file_data'][rootname]['prop'] = rootname[2:7]
        data_dict['file_data'][rootname]['filter'] = filter_type
        data_dict['file_data'][rootname]['pupil'] = pupil_type
        data_dict['file_data'][rootname]['grating'] = grating_type

        if 'stage_3' not in filename_dict['filename_type']:
            data_dict['file_data'][rootname]['stage'] = 'stage_2'
        else:
            data_dict['file_data'][rootname]['stage'] = 'stage_3'

        for filename in available_files:
            file_info = filename_parser(filename)
            if file_info['recognized_filename']:
                suffix = file_info['suffix']
                data_dict['file_data'][rootname]['suffixes'].append(suffix)
            else:
                logging.warning((f'While running thumbnails_query_ajax() on filename {filename}, '
                                 'filename_parser() failed to recognize the file pattern.'))
                continue

        data_dict['file_data'][rootname]['thumbnail'] = get_thumbnail_by_rootname(rootname)

    # Extract information for sorting with dropdown menus
    try:
        detectors = [data_dict['file_data'][rootname]['filename_dict']['detector'] for
                     rootname in list(data_dict['file_data'].keys())]
    except KeyError:
        detectors = []
        for rootname in list(data_dict['file_data'].keys()):
            try:
                detector = data_dict['file_data'][rootname]['filename_dict']['detector']
                detectors.append(detector) if detector not in detectors else detectors
            except KeyError:
                detector = 'Unknown'
                detectors.append(detector) if detector not in detectors else detectors

    instruments = [data_dict['file_data'][rootname]['inst'].lower() for
                   rootname in list(data_dict['file_data'].keys())]
    proposals = [data_dict['file_data'][rootname]['filename_dict']['program_id'] for
                 rootname in list(data_dict['file_data'].keys())]
    try:
        visits = [data_dict['file_data'][rootname]['filename_dict']['visit'] for
                  rootname in list(data_dict['file_data'].keys())]
    except KeyError:
        visits = []
    filters = [data_dict['file_data'][rootname]['filter'] for
               rootname in list(data_dict['file_data'].keys())]
    pupils = [data_dict['file_data'][rootname]['pupil'] for
              rootname in list(data_dict['file_data'].keys())]
    gratings = [data_dict['file_data'][rootname]['grating'] for
                rootname in list(data_dict['file_data'].keys())]

    dropdown_menus = {'instrument': instruments,
                      'detector': sorted(detectors),
                      'proposal': sorted(proposals),
                      'visit': sorted(visits),
                      'stage': ['Stage 2', 'Stage 3']}
    if filters is not None:
        dropdown_menus['filter'] = sorted(filters)
    if pupils is not None:
        dropdown_menus['pupil'] = sorted(pupils)
    if gratings is not None:
        dropdown_menus['grating'] = sorted(gratings)

    data_dict['tools'] = MONITORS
    data_dict['dropdown_menus'] = dropdown_menus
    data_dict['exp_groups'] = sorted(exp_groups)

    return data_dict
