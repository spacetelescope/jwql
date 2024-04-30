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

    Various documentation related to JWST filename conventions:
    - https://innerspace.stsci.edu/pages/viewpage.action?pageId=94092600
    - https://innerspace.stsci.edu/pages/viewpage.action?spaceKey=SCSB&title=JWST+Science+Data+Products
    - https://jwst-pipeline.readthedocs.io/en/stable/jwst/introduction.html#pipeline-step-suffix-definitions
    - JWST TR JWST-STScI-004800, SM-12
 """

import getpass
import glob
import itertools
import json
import pyvo as vo
import os
import re
import shutil
import http
import jsonschema

from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from bokeh.io import export_png
from bokeh.models import LinearColorMapper, LogColorMapper
from bokeh.plotting import figure
import numpy as np
from PIL import Image
from selenium import webdriver

from jwql.utils import permissions
from jwql.utils.constants import FILE_AC_CAR_ID_LEN, FILE_AC_O_ID_LEN, FILE_ACT_LEN, \
    FILE_DATETIME_LEN, FILE_EPOCH_LEN, FILE_GUIDESTAR_ATTMPT_LEN_MIN, \
    FILE_GUIDESTAR_ATTMPT_LEN_MAX, FILE_OBS_LEN, FILE_PARALLEL_SEQ_ID_LEN, \
    FILE_PROG_ID_LEN, FILE_SEG_LEN, FILE_SOURCE_ID_LEN, FILE_SUFFIX_TYPES, \
    FILE_TARG_ID_LEN, FILE_VISIT_GRP_LEN, FILE_VISIT_LEN, FILETYPE_WO_STANDARD_SUFFIX, \
    JWST_INSTRUMENT_NAMES_SHORTHAND, ON_GITHUB_ACTIONS
__location__ = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _validate_config(config_file_dict):
    """Check that the config.json file contains all the needed entries with
    expected data types

    Parameters
    ----------
    config_file_dict : dict
        The configuration JSON file loaded as a dictionary

    Notes
    -----
    See here for more information on JSON schemas:
        https://json-schema.org/learn/getting-started-step-by-step.html
    """
    # Define the schema for config.json
    schema = {
        "type": "object",  # Must be a JSON object
        "properties": {  # List all the possible entries and their types
            "admin_account": {"type": "string"},
            "auth_mast": {"type": "string"},
            "connection_string": {"type": "string"},
            "databases": {
                "type": "object",
                "properties": {
                    "engine": {"type": "string"},
                    "name": {"type": "string"},
                    "user": {"type": "string"},
                    "password": {"type": "string"},
                    "host": {"type": "string"},
                    "port": {"type": "string"}
                },
                "required": ['engine', 'name', 'user', 'password', 'host', 'port']
            },
            "django_databases": {
                "type": "object",
                "properties": {
                    "default": {
                        "type": "object",
                        "properties": {
                            "ENGINE": {"type": "string"},
                            "NAME": {"type": "string"},
                            "USER": {"type": "string"},
                            "PASSWORD": {"type": "string"},
                            "HOST": {"type": "string"},
                            "PORT": {"type": "string"}
                        },
                        "required": ['ENGINE', 'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT']
                    },
                    "monitors": {
                        "type": "object",
                        "properties": {
                            "ENGINE": {"type": "string"},
                            "NAME": {"type": "string"},
                            "USER": {"type": "string"},
                            "PASSWORD": {"type": "string"},
                            "HOST": {"type": "string"},
                            "PORT": {"type": "string"}
                        },
                        "required": ['ENGINE', 'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT']
                    }
                },
                "required": ["default", "monitors"]
            },
            "jwql_dir": {"type": "string"},
            "jwql_version": {"type": "string"},
            "server_type": {"type": "string"},
            "log_dir": {"type": "string"},
            "mast_token": {"type": "string"},
            "working": {"type": "string"},
            "outputs": {"type": "string"},
            "preview_image_filesystem": {"type": "string"},
            "filesystem": {"type": "string"},
            "setup_file": {"type": "string"},
            "test_data": {"type": "string"},
            "test_dir": {"type": "string"},
            "thumbnail_filesystem": {"type": "string"},
            "cores": {"type": "string"}
        },
        # List which entries are needed (all of them)
        "required": ["connection_string", "databases", "django_databases",
                     "filesystem", "preview_image_filesystem",
                     "thumbnail_filesystem", "outputs", "jwql_dir",
                     "admin_account", "log_dir", "test_dir", "test_data",
                     "setup_file", "auth_mast", "mast_token", "working"]
    }

    # Test that the provided config file dict matches the schema
    try:
        jsonschema.validate(instance=config_file_dict, schema=schema)
    except jsonschema.ValidationError as e:
        raise jsonschema.ValidationError(
            'Provided config.json does not match the '
            'required JSON schema: {}'.format(e.message)
        )


def create_png_from_fits(filename, outdir):
    """Create and save a png file of the provided file. The file
    will be saved with the same filename as the input file, but
    with fits replaced by png

    Parameters
    ----------
    filename : str
        Fits file to be opened and saved as a png

    outdir : str
        Output directory to save the png file to

    Returns
    -------
    png_file : str
        Name of the saved png file
    """
    if os.path.isfile(filename):
        image = fits.getdata(filename)

        # If the input file is a rateints/calints file, it will have 3 dimensions.
        # If it is a file containing all groups, prior to ramp-fitting, it will have
        # 4 dimensions. In this case, grab the appropriate 2D image to work with. For
        # a 3D case, get the first integration. For a 4D case, get the last group
        # (which will have the highest SNR).
        ndim = len(image.shape)
        if ndim == 2:
            pass
        elif ndim == 3:
            image = image[0, :, :]
        elif ndim == 4:
            image = image[0, -1, :, :]
        else:
            raise ValueError(f'File {filename} has an unsupported number of dimensions: {ndim}.')

        ny, nx = image.shape
        img_mn, img_med, img_dev = sigma_clipped_stats(image[4: ny - 4, 4: nx - 4])

        plot = figure(tools='')
        plot.x_range.range_padding = plot.y_range.range_padding = 0
        plot.toolbar.logo = None
        plot.toolbar_location = None
        plot.min_border = 0
        plot.xgrid.visible = False
        plot.ygrid.visible = False

        # Create the color mapper that will be used to scale the image
        mapper = LogColorMapper(palette='Greys256', low=(img_med - (5 * img_dev)), high=(img_med + (5 * img_dev)))

        # Plot image
        imgplot = plot.image(image=[image], x=0, y=0, dw=nx, dh=ny,
                             color_mapper=mapper, level="image")

        # Turn off the axes, in order to make embedding in another figure easier
        plot.xaxis.visible = False
        plot.yaxis.visible = False

        # Save the plot in a png
        output_filename = os.path.join(outdir, os.path.basename(filename).replace('fits', 'png'))
        save_png(plot, filename=output_filename)
        permissions.set_permissions(output_filename)
        return output_filename
    else:
        return None


def get_config():
    """Return a dictionary that holds the contents of the ``jwql``
    config file.

    Returns
    -------
    settings : dict
        A dictionary that holds the contents of the config file.
    """
    if os.environ.get('READTHEDOCS') == 'True':
        # ReadTheDocs should use the example configuration file rather than the complete configuration file
        config_file_location = os.path.join(__location__, 'jwql', 'example_config.json')
    else:
        # Users should complete their own configuration file and store it in the main jwql directory
        config_file_location = os.path.join(__location__, 'jwql', 'config.json')

    # Make sure the file exists
    if not os.path.isfile(config_file_location):
        base_config = os.path.basename(config_file_location)
        raise FileNotFoundError('The JWQL package requires a configuration file ({}) '
                                'to be placed within the main jwql directory. '
                                'This file is missing. Please read the relevant wiki page '
                                '(https://github.com/spacetelescope/jwql/wiki/'
                                'Config-file) for more information.'.format(base_config))

    with open(config_file_location, 'r') as config_file_object:
        try:
            # Load it with JSON
            settings = json.load(config_file_object)
        except json.JSONDecodeError as e:
            # Raise a more helpful error if there is a formatting problem
            raise ValueError('Incorrectly formatted config.json file. '
                             'Please fix JSON formatting: {}'.format(e))

    # Ensure the file has all the needed entries with expected data types
    _validate_config(settings)

    return settings


if not ON_GITHUB_ACTIONS:
    FILESYSTEM = get_config()['filesystem']


def copy_files(files, out_dir):
    """Copy a given file to a given directory. Only try to copy the file
    if it is not already present in the output directory.

    Parameters
    ----------
    files : list
        List of files to be copied

    out_dir : str
        Destination directory

    Returns
    -------
    success : list
        Files successfully copied (or that already existed in out_dir)

    failed : list
        Files that were not copied
    """

    # Copy files if they do not already exist
    success = []
    failed = []
    for input_file in files:
        input_new_path = os.path.join(out_dir, os.path.basename(input_file))
        if os.path.isfile(input_new_path):
            success.append(input_new_path)
        else:
            try:
                shutil.copy2(input_file, out_dir)
                success.append(input_new_path)
                permissions.set_permissions(input_new_path)
            except Exception:
                failed.append(input_file)
    return success, failed


def download_mast_data(query_results, output_dir):
    """Example function for downloading MAST query results. From MAST
    website (``https://mast.stsci.edu/api/v0/pyex.html``)

    Parameters
    ----------
    query_results : list
        List of dictionaries returned by a MAST query.

    output_dir : str
        Directory into which the files will be downlaoded
    """

    # Set up the https connection
    server = 'mast.stsci.edu'
    conn = http.client.HTTPSConnection(server)

    # Dowload the products
    print('Number of query results: {}'.format(len(query_results)))

    for i in range(len(query_results)):

        # Make full output file path
        output_file = os.path.join(output_dir, query_results[i]['filename'])

        print('Output file is {}'.format(output_file))

        # Download the data
        uri = query_results[i]['dataURI']

        print('uri is {}'.format(uri))

        conn.request("GET", "/api/v0/download/file?uri=" + uri)
        resp = conn.getresponse()
        file_content = resp.read()

        # Save to file
        with open(output_file, 'wb') as file_obj:
            file_obj.write(file_content)

        # Check for file
        if not os.path.isfile(output_file):
            print("ERROR: {} failed to download.".format(output_file))
        else:
            statinfo = os.stat(output_file)
            if statinfo.st_size > 0:
                print("DOWNLOAD COMPLETE: ", output_file)
            else:
                print("ERROR: {} file is empty.".format(output_file))
    conn.close()


def ensure_dir_exists(fullpath):
    """Creates dirs from ``fullpath`` if they do not already exist."""
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
    split_filename = filename.split('.')
    file_root_name = (len(split_filename) < 2)
    if file_root_name:
        root_name = filename
    else:
        root_name = split_filename[0]

    # Stage 1 and 2 filenames
    # e.g. "jw80500012009_01101_00012_nrcalong_uncal.fits"
    stage_1_and_2 = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"(?P<observation>\d{" + f"{FILE_OBS_LEN}" + "})"\
        r"(?P<visit>\d{" + f"{FILE_VISIT_LEN}" + "})"\
        r"_(?P<visit_group>\d{" + f"{FILE_VISIT_GRP_LEN}" + "})"\
        r"(?P<parallel_seq_id>\d{" + f"{FILE_PARALLEL_SEQ_ID_LEN}" + "})"\
        r"(?P<activity>\w{" f"{FILE_ACT_LEN}" + "})"\
        r"_(?P<exposure_id>\d+)"\
        r"_(?P<detector>((?!_)[\w])+)"

    # Stage 2c outlier detection filenames
    # e.g. "jw94015002002_02108_00001_mirimage_o002_crf.fits"
    stage_2c = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})" \
        r"(?P<observation>\d{" + f"{FILE_OBS_LEN}" + "})" \
        r"(?P<visit>\d{" + f"{FILE_VISIT_LEN}" + "})" \
        r"_(?P<visit_group>\d{" + f"{FILE_VISIT_GRP_LEN}" + "})" \
        r"(?P<parallel_seq_id>\d{" + f"{FILE_PARALLEL_SEQ_ID_LEN}" + "})" \
        r"(?P<activity>\w{" + f"{FILE_ACT_LEN}" + "})" \
        r"_(?P<exposure_id>\d+)" \
        r"_(?P<detector>((?!_)[\w])+)"\
        r"_(?P<ac_id>(o\d{" + f"{FILE_AC_O_ID_LEN}" + r"}|(c|a|r)\d{" + f"{FILE_AC_CAR_ID_LEN}" + "}))"

    # Stage 2 MSA metadata file. Created by APT and loaded in
    # assign_wcs. e.g. "jw01118008001_01_msa.fits"
    stage_2_msa = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"(?P<observation>\d{" + f"{FILE_OBS_LEN}" + "})"\
        r"(?P<visit>\d{" + f"{FILE_VISIT_LEN}" + "})"\
        r"(_.._msa.fits)"

    # Stage 3 filenames with target ID
    # e.g. "jw80600-o009_t001_miri_f1130w_i2d.fits"
    stage_3_target_id = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"-(?P<ac_id>(o\d{" + f"{FILE_AC_O_ID_LEN}" + r"}|(c|a|r)\d{" + f"{FILE_AC_CAR_ID_LEN}" + "}))"\
        r"_(?P<target_id>(t)\d{" + f"{FILE_TARG_ID_LEN}" + "})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with source ID
    # e.g. "jw80600-o009_s00001_miri_f1130w_i2d.fits"
    stage_3_source_id = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"-(?P<ac_id>(o\d{" + f"{FILE_AC_O_ID_LEN}" + r"}|(c|a|r)\d{" + f"{FILE_AC_CAR_ID_LEN}" + "}))"\
        r"_(?P<source_id>(s)\d{" + f"{FILE_SOURCE_ID_LEN}" + "})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with target ID and epoch
    # e.g. "jw80600-o009_t001-epoch1_miri_f1130w_i2d.fits"
    stage_3_target_id_epoch = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"-(?P<ac_id>(o\d{" + f"{FILE_AC_O_ID_LEN}" + r"}|(c|a|r)\d{" + f"{FILE_AC_CAR_ID_LEN}" + "}))"\
        r"_(?P<target_id>(t)\d{" + f"{FILE_TARG_ID_LEN}" + "})"\
        r"-epoch(?P<epoch>\d{" + f"{FILE_EPOCH_LEN}" + "})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with source ID and epoch
    # e.g. "jw80600-o009_s00001-epoch1_miri_f1130w_i2d.fits"
    stage_3_source_id_epoch = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"-(?P<ac_id>(o\d{" + f"{FILE_AC_O_ID_LEN}" + r"}|(c|a|r)\d{" + f"{FILE_AC_CAR_ID_LEN}" + "}))"\
        r"_(?P<source_id>(s)\d{" + f"{FILE_SOURCE_ID_LEN}" + "})"\
        r"-epoch(?P<epoch>\d{" + f"{FILE_EPOCH_LEN}" + "})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Time series filenames
    # e.g. "jw00733003001_02101_00002-seg001_nrs1_rate.fits"
    time_series = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"(?P<observation>\d{" + f"{FILE_OBS_LEN}" + "})"\
        r"(?P<visit>\d{" + f"{FILE_VISIT_LEN}" + "})"\
        r"_(?P<visit_group>\d{" + f"{FILE_VISIT_GRP_LEN}" + "})"\
        r"(?P<parallel_seq_id>\d{" + f"{FILE_PARALLEL_SEQ_ID_LEN}" + "})"\
        r"(?P<activity>\w{" + f"{FILE_ACT_LEN}" + "})"\
        r"_(?P<exposure_id>\d+)"\
        r"-seg(?P<segment>\d{" + f"{FILE_SEG_LEN}" + "})"\
        r"_(?P<detector>((?!_)[\w])+)"

    # Time series filenames for stage 2c
    # e.g. "jw00733003001_02101_00002-seg001_nrs1_o001_crfints.fits"
    time_series_2c = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})"\
        r"(?P<observation>\d{" + f"{FILE_OBS_LEN}" + "})"\
        r"(?P<visit>\d{" + f"{FILE_VISIT_LEN}" + "})"\
        r"_(?P<visit_group>\d{" + f"{FILE_VISIT_GRP_LEN}" + "})"\
        r"(?P<parallel_seq_id>\d{" + f"{FILE_PARALLEL_SEQ_ID_LEN}" + "})"\
        r"(?P<activity>\w{" + f"{FILE_ACT_LEN}" + "})"\
        r"_(?P<exposure_id>\d+)"\
        r"-seg(?P<segment>\d{" + f"{FILE_SEG_LEN}" + "})"\
        r"_(?P<detector>((?!_)[\w])+)"\
        r"_(?P<ac_id>(o\d{" + f"{FILE_AC_O_ID_LEN}" + r"}|(c|a|r)\d{" + f"{FILE_AC_CAR_ID_LEN}" + "}))"

    # Guider filenames
    # e.g. "jw00729011001_gs-id_1_image_cal.fits" or
    # "jw00799003001_gs-acq1_2019154181705_stream.fits"
    guider = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})" \
        r"(?P<observation>\d{" + f"{FILE_OBS_LEN}" + "})" \
        r"(?P<visit>\d{" + f"{FILE_VISIT_LEN}" + "})" \
        r"_gs-(?P<guider_mode>(id|acq1|acq2|track|fg))" \
        r"_((?P<date_time>\d{" + f"{FILE_DATETIME_LEN}" + r"})|(?P<guide_star_attempt_id>\d{" + f"{FILE_GUIDESTAR_ATTMPT_LEN_MIN},{FILE_GUIDESTAR_ATTMPT_LEN_MAX}" + "}))"

    # Segment guider filenames
    # e.g. "jw01118005001_gs-fg_2022150070312-seg002_uncal.fits"
    guider_segment = \
        r"jw" \
        r"(?P<program_id>\d{" + f"{FILE_PROG_ID_LEN}" + "})" \
        r"(?P<observation>\d{" + f"{FILE_OBS_LEN}" + "})" \
        r"(?P<visit>\d{" + f"{FILE_VISIT_LEN}" + "})" \
        r"_gs-(?P<guider_mode>(id|acq1|acq2|track|fg))" \
        r"_((?P<date_time>\d{" + f"{FILE_DATETIME_LEN}" + r"})|(?P<guide_star_attempt_id>\d{" + f"{FILE_GUIDESTAR_ATTMPT_LEN_MIN},{FILE_GUIDESTAR_ATTMPT_LEN_MAX}" + "}))" \
        r"-seg(?P<segment>\d{" + f"{FILE_SEG_LEN}" + "})"

    # Build list of filename types
    filename_types = [
        stage_1_and_2,
        stage_2c,
        stage_2_msa,
        stage_3_target_id,
        stage_3_source_id,
        stage_3_target_id_epoch,
        stage_3_source_id_epoch,
        time_series,
        time_series_2c,
        guider,
        guider_segment]

    filename_type_names = [
        'stage_1_and_2',
        'stage_2c',
        'stage_2_msa',
        'stage_3_target_id',
        'stage_3_source_id',
        'stage_3_target_id_epoch',
        'stage_3_source_id_epoch',
        'time_series',
        'time_series_2c',
        'guider',
        'guider_segment'
    ]

    # Try to parse the filename
    for filename_type, filename_type_name in zip(filename_types, filename_type_names):

        # If full filename, try using suffix, except for *msa.fits files
        if not file_root_name and FILETYPE_WO_STANDARD_SUFFIX not in filename:
            filename_type += r"_(?P<suffix>{}).*".format('|'.join(FILE_SUFFIX_TYPES))
        # If not, make sure the provided regex matches the entire filename root
        else:
            filename_type += r"$"

        elements = re.compile(filename_type)
        jwst_file = elements.match(filename)

        # Stop when you find a format that matches
        if jwst_file is not None:
            name_match = filename_type_name
            break

    try:
        # Convert the regex match to a dictionary
        filename_dict = jwst_file.groupdict()

        # Add the filename type to that dict
        filename_dict['filename_type'] = name_match

        # Also, add the instrument if not already there
        if 'instrument' not in filename_dict.keys():
            if name_match in ['guider', 'guider_segment']:
                filename_dict['instrument'] = 'fgs'
            elif 'detector' in filename_dict.keys():
                filename_dict['instrument'] = JWST_INSTRUMENT_NAMES_SHORTHAND[
                    filename_dict['detector'][:3].lower()
                ]
            elif name_match == 'stage_2_msa':
                filename_dict['instrument'] = 'nirspec'

        # Also add detector, root name, and group root name
        root_name = re.sub(rf"_{filename_dict.get('suffix', '')}$", '', root_name)
        root_name = re.sub(rf"_{filename_dict.get('ac_id', '')}$", '', root_name)
        filename_dict['file_root'] = root_name
        if 'detector' not in filename_dict.keys():
            filename_dict['detector'] = 'Unknown'
            filename_dict['group_root'] = root_name
        else:
            group_root = re.sub(rf"_{filename_dict['detector']}$", '', root_name)
            filename_dict['group_root'] = group_root

    # Raise error if unable to parse the filename
    except AttributeError:
        jdox_url = 'https://jwst-docs.stsci.edu/understanding-jwst-data-files/jwst-data-file-naming-conventions'
        raise ValueError(
            'Provided file {} does not follow JWST naming conventions.  '
            'See {} for further information.'.format(filename, jdox_url)
        )

    return filename_dict


def filesystem_path(filename, check_existence=True, search=None):
    """Return the path to a given file in the filesystem.

    The full path is returned if ``check_existence`` is True, otherwise
    only the path relative to the ``filesystem`` key in the ``config.json``
    file is returned.

    Parameters
    ----------
    filename : str
        File to locate (e.g. ``jw86600006001_02101_00008_guider1_cal.fits``)
    check_existence : boolean
        Check to see if the file exists in the expected lcoation
    search : str
        A search term to use in a ``glob.glob`` statement if the full
        filename is unkown (e.g. ``*rate.fits``).  In this case, the first
        element of the list of returned values is chosen as the filename.

    Returns
    -------
    full_path : str
        Full path to the given file, including filename
    """

    # Subdirectory name is based on the proposal ID
    subdir1 = 'jw{}'.format(filename[2:7])
    subdir2 = 'jw{}'.format(filename[2:13])

    if search:
        full_subdir = os.path.join(subdir1, subdir2, '{}{}'.format(filename, search))
        filenames_found = glob.glob(os.path.join(FILESYSTEM, 'public', full_subdir))
        filenames_found.extend(glob.glob(os.path.join(FILESYSTEM, 'proprietary', full_subdir)))
        if len(filenames_found) > 0:
            filename = os.path.basename(filenames_found[0])
        else:
            raise FileNotFoundError('{} did not yield any files in predicted location {}'.format(search, full_subdir))

    full_path = os.path.join(subdir1, subdir2, filename)

    # Check to see if the file exists
    if check_existence:
        full_path_public = os.path.join(FILESYSTEM, 'public', full_path)
        full_path_proprietary = os.path.join(FILESYSTEM, 'proprietary', full_path)
        if os.path.isfile(full_path_public):
            full_path = full_path_public
        elif os.path.isfile(full_path_proprietary):
            full_path = full_path_proprietary
        else:
            raise FileNotFoundError('{} is not in the expected location: {}'.format(filename, full_path))

    return full_path


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
        base_url = 'https://{}.stsci.edu'.format(get_config()['server_name'])
    else:
        base_url = 'http://127.0.0.1:8000'

    return base_url


def get_rootnames_for_instrument_proposal(instrument, proposal):
    """Return a list of rootnames for the given instrument and proposal

    Parameters
    ----------
    instrument : str
        Name of the JWST instrument, with first letter capitalized
        (e.g. ``Fgs``)

    proposal : int or str
        Proposal ID number

    Returns
    -------
    rootnames : list
        List of rootnames for the given instrument and proposal number
    """
    tap_service = vo.dal.TAPService("https://vao.stsci.edu/caomtap/tapservice.aspx")
    tap_results = tap_service.search(f"select observationID from dbo.CaomObservation where collection='JWST' and maxLevel=2 and insName like '{instrument.lower()}%' and prpID='{int(proposal)}'")
    prop_table = tap_results.to_table()
    rootnames = prop_table['observationID'].data
    return rootnames.compressed()


def check_config_for_key(key):
    """Check that the config.json file contains the specified key
    and that the entry is not empty

    Parameters
    ----------
    key : str
        The configuration file key to verify
    """
    try:
        get_config()[key]
    except KeyError:
        msg = 'The key `{}` is not present in config.json. Please add it.'.format(key)
        msg += ' See the relevant wiki page (https://github.com/spacetelescope/'
        msg += 'jwql/wiki/Config-file) for more information.'
        raise KeyError(msg)

    if get_config()[key] == "":
        msg = 'Please complete the `{}` field in your config.json. '.format(key)
        msg += ' See the relevant wiki page (https://github.com/spacetelescope/'
        msg += 'jwql/wiki/Config-file) for more information.'
        raise ValueError(msg)


def delete_non_rate_thumbnails(extensions=['_rate_', '_dark']):
    """This script will go through all the thumbnail directories and delete all
    thumbnails that do not contain the given extensions. We currently create thumbnails
    using only rate.fits and dark.fits files, so the default is to keep only those.

    Parameters
    ----------
    extension : list
        If a thumbnail filename contains any of these strings, it will not be deleted
    """
    base_dir = get_config()["thumbnail_filesystem"]
    dir_list = sorted(glob.glob(os.path.join(base_dir, 'jw*')))

    for dirname in dir_list:
        files = glob.glob(os.path.join(dirname, '*.thumb'))
        for file in files:
            if not any([x in file for x in extensions]):
                os.remove(file)


def query_format(string):
    """Take a string of format lower_case and change it to UPPER CASE"""
    upper_case = string.upper()
    split_string = upper_case.replace("_", " ")

    return split_string


def query_unformat(string):
    """Take a string of format UPPER CASE and change it to UPPER_CASE"""
    unsplit_string = string.replace(" ", "_")

    return unsplit_string


def read_png(filename):
    """Open the given png file and return as a 3D numpy array

    Parameters
    ----------
    filename : str
        png file to be opened

    Returns
    -------
    data : numpy.ndarray
        3D array representation of the data in the png file
    """
    if os.path.isfile(filename):
        rgba_img = Image.open(filename).convert('RGBA')
        xdim, ydim = rgba_img.size

        # Create an array representation for the image, filled with
        # dummy data to begin with
        img = np.empty((ydim, xdim), dtype=np.uint32)

        # Create a layer/RGBA" version with a set of 4, 8-bit layers.
        # We will work with the data using 'view', and our changes
        # will propagate back into the 2D 'img' version, which is
        # what we will end up returning.
        view = img.view(dtype=np.uint8).reshape((ydim, xdim, 4))

        # Copy the RGBA image into view, flipping it so it comes right-side up
        # with a lower-left origin
        view[:, :, :] = np.flipud(np.asarray(rgba_img))
    else:
        view = None
    # Return the 2D version
    return img


def save_png(fig, filename=''):
    """Starting with selenium version 4.10.0, our testing has shown that on the JWQL
    servers, we need to specify an instance of a web driver when exporting a Bokeh
    figure as a png. This is a wrapper function that creates the web driver instance
    and calls Bokeh's export_png function.

    Parameters
    ----------
    fig : bokeh.plotting.figure
        Bokeh figure to be saved as a png

    filename : str
        Filename to use for the png file
    """
    options = webdriver.FirefoxOptions()
    options.add_argument('-headless')
    driver = webdriver.Firefox(options=options)
    export_png(fig, filename=filename, webdriver=driver)
    driver.quit()


def grouper(iterable, chunksize):
    """
    Take a list of items (iterable), and group it into chunks of chunksize, with the
    last chunk being any remaining items. This allows you to batch-iterate through a
    potentially very long list without missing any items, and where each individual
    iteration can involve a much smaller number of files. Particularly useful for
    operations that you want to execute in batches, but don't want the batches to be too
    long.

    Examples
    --------

    grouper([1, 2, 3, 4, 5], 2)
    produces
    (1, 2), (3, 4), (5, )

    grouper([1, 2, 3, 4, 5], 6)
    produces
    (1, 2, 3, 4, 5)
    """
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, chunksize))
        if not chunk:
            return
        yield chunk
