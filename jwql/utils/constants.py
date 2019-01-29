"""Globally defined and used variables for the ``jwql`` project.

Authors
-------

    - Johannes Sahlmann

Use
---
    To print the JWST instrument names do:
    ::

        from jwql.utils import constants
        print(constants.JWST_INSTRUMENT_NAMES)
        inventory, keywords = monitor_mast.jwst_inventory()

References
----------
    Many variables were transferred from an earlier version of utils.py

"""
JWST_INSTRUMENT_NAMES = sorted(['niriss', 'nircam', 'nirspec', 'miri', 'fgs'])

JWST_DATAPRODUCTS = ['IMAGE', 'SPECTRUM', 'SED', 'TIMESERIES', 'VISIBILITY',
                     'EVENTLIST', 'CUBE', 'CATALOG', 'ENGINEERING', 'NULL']

JWST_INSTRUMENT_NAMES_SHORTHAND = {'gui': 'fgs',
                                   'mir': 'miri',
                                   'nis': 'niriss',
                                   'nrc': 'nircam',
                                   'nrs': 'nirspec'}

JWST_INSTRUMENT_NAMES_MIXEDCASE = {'fgs': 'FGS',
                                   'miri': 'MIRI',
                                   'nircam': 'NIRCam',
                                   'niriss': 'NIRISS',
                                   'nirspec': 'NIRSpec'}

JWST_INSTRUMENT_NAMES_UPPERCASE = {key: value.upper() for key, value in
                                   JWST_INSTRUMENT_NAMES_MIXEDCASE.items()}

JWST_MAST_SERVICES = ['Mast.Jwst.Filtered.{}'.format(value.title()) for value in
                      JWST_INSTRUMENT_NAMES]

FILE_SUFFIX_TYPES = ['uncal', 'cal', 'rateints', 'rate', 'trapsfilled',
                     'i2d', 'x1d', 's2d', 's3d', 'dark', 'ami', 'crf']

MONITORS = {
    'fgs': ['Bad Pixel Monitor'],
    'miri': ['Dark Current Monitor',
             'Bad Pixel Monitor', 'Cosmic Ray Monitor', 'Photometry Monitor',
             'TA Failure Monitor', 'Blind Pointing Accuracy Monitor',
             'Filter and Calibration Lamp Monitor', 'Thermal Emission Monitor'],
    'nircam': ['Bias Monitor',
               'Readnoise Monitor', 'Gain Level Monitor',
               'Mean Dark Current Rate Monitor', 'Photometric Stability Monitor'],
    'niriss': ['Bad Pixel Monitor',
               'Readnoise Monitor', 'AMI Calibrator Monitor', 'TSO RMS Monitor'],
    'nirspec': ['Optical Short Monitor', 'Target Acquisition Monitor',
                'Detector Health Monitor', 'Ref Pix Monitor',
                'Internal Lamp Monitor', 'Instrument Model Updates',
                'Failed-open Shutter Monitor']}

NIRCAM_SHORTWAVE_DETECTORS = ['NRCA1', 'NRCA2', 'NRCA3', 'NRCA4',
                              'NRCB1', 'NRCB2', 'NRCB3', 'NRCB4']

NIRCAM_LONGWAVE_DETECTORS = ['NRCA5', 'NRCB5']
