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

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

JWST_INSTRUMENTS = sorted(['NIRISS', 'NIRCam', 'NIRSpec', 'MIRI', 'FGS'])
JWST_DATAPRODUCTS = ['IMAGE', 'SPECTRUM', 'SED', 'TIMESERIES', 'VISIBILITY',
                     'EVENTLIST', 'CUBE', 'CATALOG', 'ENGINEERING', 'NULL']
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


def filename_parser(filename):
    """Return a dictionary that contains the properties of a given
    JWST file (e.g. program ID, visit number, detector, etc.)

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

    elements = \
        re.compile(r"[a-z]+"
                   "(?P<program_id>\d{5})"
                   "(?P<observation>\d{3})"
                   "(?P<visit>\d{3})"
                   "_(?P<visit_group>\d{2})"
                   "(?P<parallel_seq_id>\d{1})"
                   "(?P<activity>\w{2})"
                   "_(?P<exposure_id>\d+)"
                   "_(?P<detector>\w+)"
                   "_(?P<suffix>\w+).*")

    jwst_file = elements.match(filename)

    if jwst_file is not None:
        filename_dict = jwst_file.groupdict()
    else:
        raise ValueError('Provided file {} does not follow JWST naming conventions (jw<PPPPP><OOO><VVV>_<GGSAA>_<EEEEE>_<detector>_<suffix>.fits)'.format(filename))

    return filename_dict
