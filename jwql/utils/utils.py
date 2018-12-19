"""Various utility functions for the ``jwql`` project.

Authors
-------

    - Matthew Bourque
    - Lauren Chambers

Use
---

    This module can be imported as such:

    >>> import utils
    settings = get_config()

References
----------

    Filename parser modified from Joe Hunkeler:
    https://gist.github.com/jhunkeler/f08783ca2da7bfd1f8e9ee1d207da5ff
 """

import getpass
import json
import os
import re

from jwql.utils import permissions
from jwql.utils.constants import FILE_SUFFIX_TYPES

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def copy_from_filesystem(files, out_dir):
    """Copy a given file from the filesystem to a given directory.
    Short-term fix: if the file does not exist in the filesystem
    then try downloading from MAST
    """
    for input_file in files:
        success = []
        failed = []
        try:
            shutil.copy2(input_file, out_dir)
            success.append(input_file)
        except:
            filed.append(input_file)
    return success, failed


def download_mast_data(query_results, output_dir):
    """Example function for downloading MAST query results. From MAST website
    https://mast.stsci.edu/api/v0/pyex.html

    Parameters
    ----------
    query_results : list
        List of dictionaries returned by a MAST query.

    output_dir : str
        Directory into which the files will be downlaoded
    """
    # Set up the https connection
    server = 'mast.stsci.edu'
    conn = httplib.HTTPSConnection(server)

    # Dowload the products
    for i in range(len(query_results)):

        # Make full output file path
        output_file = os.path.join(output_dir, query_results[i]['filename'])

        # Download the data
        uri = query_results[i]['dataURI']
        conn.request("GET", "/api/v0/download/file?uri="+uri)
        resp = conn.getresponse()
        file_content = resp.read()

        # Save to file
        with open(output_file, 'wb') as file_obj:
            file_obj.write(file_content)

        # Check for file
        if not os.path.isfile(output_file):
            print("ERROR: " + output_file + " failed to download.")
        else:
            print("DOWNLOAD COMPLETE: ", output_file)
    conn.close()


def ensure_dir_exists(fullpath):
    """Creates dirs from ``fullpath`` if they do not already exist.
    """
    if not os.path.exists(fullpath):
        os.makedirs(fullpath)
        permissions.set_permissions(fullpath)


def filename_parser(filename):
    """Return a dictionary that contains the properties of a given
    JWST file (e.g. program ID, visit number, detector, etc.).

    Parameters
    ----------
    filename : str
        Path or name of JWST file to parse

    Returns
    -------
    filename_dict : dict
        Collection of file properties

    Raises
    ------
    ValueError
        When the provided file does not follow naming conventions
    """

    filename = os.path.basename(filename)
    file_root_name = (len(filename.split('.')) < 2)

    # Stage 1 and 2 filenames, e.g. "jw80500012009_01101_00012_nrcalong_uncal.fits"
    stage_1_and_2 = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"(?P<observation>\d{3})"\
        r"(?P<visit>\d{3})"\
        r"_(?P<visit_group>\d{2})"\
        r"(?P<parallel_seq_id>\d{1})"\
        r"(?P<activity>\w{2})"\
        r"_(?P<exposure_id>\d+)"\
        r"_(?P<detector>((?!_)[\w])+)"

    # Stage 3 filenames with target ID, e.g. "jw80600-o009_t001_miri_f1130w_i2d.fits"
    stage_3_target_id = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"-(?P<ac_id>(o|c|a|r)\d{3,4})"\
        r"_(?P<target_id>(t)\d{3})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with source ID, e.g. "jw80600-o009_s00001_miri_f1130w_i2d.fits"
    stage_3_source_id = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"-(?P<ac_id>(o|c|a|r)\d{3,4})"\
        r"_(?P<source_id>(s)\d{5})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with target ID and epoch, e.g. "jw80600-o009_t001-epoch1_miri_f1130w_i2d.fits"
    stage_3_target_id_epoch = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"-(?P<ac_id>(o|c|a|r)\d{3,4})"\
        r"_(?P<target_id>(t)\d{3})"\
        r"-epoch(?P<epoch>\d{1})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with source ID and epoch, e.g. "jw80600-o009_s00001-epoch1_miri_f1130w_i2d.fits"
    stage_3_source_id_epoch = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"-(?P<ac_id>(o|c|a|r)\d{3,4})"\
        r"_(?P<source_id>(s)\d{5})"\
        r"-epoch(?P<epoch>\d{1})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Time series filenames, e.g. "jw00733003001_02101_00002-seg001_nrs1_rate.fits"
    time_series = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"(?P<observation>\d{3})"\
        r"(?P<visit>\d{3})"\
        r"_(?P<visit_group>\d{2})"\
        r"(?P<parallel_seq_id>\d{1})"\
        r"(?P<activity>\w{2})"\
        r"_(?P<exposure_id>\d+)"\
        r"-seg(?P<segment>\d{3})"\
        r"_(?P<detector>\w+)"

    # Build list of filename types
    filename_types = [stage_1_and_2, stage_3_target_id, stage_3_source_id, stage_3_target_id_epoch, stage_3_source_id_epoch, time_series]

    # Try to parse the filename
    for filename_type in filename_types:

        # If full filename, try using suffix
        if not file_root_name:
            filename_type += r"_(?P<suffix>{}).*".format('|'.join(FILE_SUFFIX_TYPES))

        elements = re.compile(filename_type)
        jwst_file = elements.match(filename)
        if jwst_file is not None:
            break

    # Raise error if unable to parse the filename
    try:
        filename_dict = jwst_file.groupdict()
    except AttributeError:
        jdox_url = 'https://jwst-docs.stsci.edu/display/JDAT/File+Naming+Conventions+and+Data+Products'
        raise ValueError('Provided file {} does not follow JWST naming conventions.  See {} for further information.'.format(filename, jdox_url))

    return filename_dict


def get_base_url():
    """Return the beginning part of the URL to the ``jwql`` web app
    based on which user is running the software.

    If the admin account is running the code, the ``base_url`` is
    assumed to be the production URL.  If not, the ``base_url`` is
    assumed to be local.

    Returns
    -------
    base_url : str
        The beginning part of the URL to the ``jwql`` web app
    """

    username = getpass.getuser()
    if username == get_config()['admin_account']:
        base_url = 'https://dljwql.stsci.edu'
    else:
        base_url = 'http://127.0.0.1:8000'

    return base_url


def get_config():
    """Return a dictionary that holds the contents of the ``jwql``
    config file.

    Returns
    -------
    settings : dict
        A dictionary that holds the contents of the config file.
    """
    config_file_location = os.path.join(__location__, 'config.json')

    if not os.path.isfile(config_file_location):
        raise FileNotFoundError('The JWQL package requires a configuration file (config.json) '
                                'to be placed within the jwql/utils directory. '
                                'This file is missing. Please read the relevant wiki page '
                                '(https://github.com/spacetelescope/jwql/wiki/'
                                'Config-file) for more information.')

    with open(config_file_location, 'r') as config_file:
        settings = json.load(config_file)

    return settings


def filesystem_path(filename):
    """Return the full path to a given file in the filesystem

    Parameters
    ----------
    filename : str
        File to locate (e.g. jw86600006001_02101_00008_guider1_cal.fits)

    Returns
    -------
    full_path : str
        Full path to the given file, including filename
    """
    filesystem_base = get_config()["filesystem"]

    # Subdirectory name is based on the proposal ID
    subdir = filename[0:7]
    full_path = os.path.join(filesystem_base, subdir, filename)

    # Check to see if the file exists
    if os.path.isfile(full_path):
        return full_path
    else:
        raise FileNotFoundError('{} is not in the predicted location: {}'.format(filename, full_path))
