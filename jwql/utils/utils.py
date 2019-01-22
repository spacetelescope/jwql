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

    Filename parser modifed from Joe Hunkeler:
    https://gist.github.com/jhunkeler/f08783ca2da7bfd1f8e9ee1d207da5ff
 """

import json
import os
import re

from jwql.utils import permissions

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

FILE_SUFFIX_TYPES = ['uncal', 'cal', 'rateints', 'rate', 'trapsfilled',
                     'i2d', 'x1d', 's2d', 's3d', 'dark', 'ami', 'crf']
JWST_INSTRUMENTS = sorted(['NIRISS', 'NIRCam', 'NIRSpec', 'MIRI', 'FGS'])
JWST_DATAPRODUCTS = ['IMAGE', 'SPECTRUM', 'SED', 'TIMESERIES', 'VISIBILITY',
                     'EVENTLIST', 'CUBE', 'CATALOG', 'ENGINEERING', 'NULL']
MAST_SERVICES = ['Mast.Jwst.Filtered.Nircam', 'Mast.Jwst.Filtered.Nirspec',
                'Mast.Jwst.Filtered.Niriss', 'Mast.Jwst.Filtered.Miri',
                'Mast.Jwst.Filtered.Fgs']
MONITORS = {
    'FGS': ['Bad Pixel Monitor'],
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
NIRCAM_SHORTWAVE_DETECTORS = ['NRCA1', 'NRCA2', 'NRCA3', 'NRCA4',
                              'NRCB1', 'NRCB2', 'NRCB3', 'NRCB4']
NIRCAM_LONGWAVE_DETECTORS = ['NRCA5', 'NRCB5']
INSTRUMENTS_SHORTHAND = {'gui': 'FGS',
                         'mir': 'MIRI',
                         'nis': 'NIRISS',
                         'nrc': 'NIRCam',
                         'nrs': 'NIRSpec'}
INSTRUMENTS_CAPITALIZED = {'fgs': 'FGS',
                           'miri': 'MIRI',
                           'nircam': 'NIRCam',
                           'niriss': 'NIRISS',
                           'nirspec': 'NIRSpec'}


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
        r"-(?P<ac_id>(o|c|a|r)\d{3})"\
        r"_(?P<target_id>(t)\d{3})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with source ID, e.g. "jw80600-o009_s00001_miri_f1130w_i2d.fits"
    stage_3_source_id = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"-(?P<ac_id>(o|c|a|r)\d{3})"\
        r"_(?P<source_id>(s)\d{5})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with target ID and epoch, e.g. "jw80600-o009_t001-epoch1_miri_f1130w_i2d.fits"
    stage_3_target_id_epoch = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"-(?P<ac_id>(o|c|a|r)\d{3})"\
        r"_(?P<target_id>(t)\d{3})"\
        r"-epoch(?P<epoch>\d{1})"\
        r"_(?P<instrument>(nircam|niriss|nirspec|miri|fgs))"\
        r"_(?P<optical_elements>((?!_)[\w-])+)"

    # Stage 3 filenames with source ID and epoch, e.g. "jw80600-o009_s00001-epoch1_miri_f1130w_i2d.fits"
    stage_3_source_id_epoch = \
        r"jw" \
        r"(?P<program_id>\d{5})"\
        r"-(?P<ac_id>(o|c|a|r)\d{3})"\
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


def get_config():
    """Return a dictionary that holds the contents of the ``jwql``
    config file.

    Returns
    -------
    settings : dict
        A dictionary that holds the contents of the config file.
    """
    with open(os.path.join(__location__, 'config.json'), 'r') as config_file:
        settings = json.load(config_file)

    return settings
