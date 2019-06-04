"""Globally defined and used variables for the ``jwql`` project.

Authors
-------

    - Johannes Sahlmann

Use
---
    This variables within this module are intended to be directly
    imported, e.g.:
    ::

        from jwql.utils.constants import JWST_INSTRUMENT_NAMES

References
----------

    Many variables were transferred from an earlier version of
    ``utils.py``
"""

# Defines the x and y coordinates of amplifier boundaries
AMPLIFIER_BOUNDARIES = {'nircam': {'1': [(0, 0), (512, 2048)], '2': [(512, 0), (1024, 2048)],
                                   '3': [(1024, 0), (1536, 2048)], '4': [(1536, 0), (2048, 2048)]}
                        }

# Possible suffix types for nominal files
GENERIC_SUFFIX_TYPES = ['uncal', 'cal', 'rateints', 'rate', 'trapsfilled', 'i2d',
                        'x1dints', 'x1d', 's2d', 's3d', 'dark', 'crfints',
                        'crf', 'ramp', 'fitopt', 'bsubints', 'bsub', 'cat']

# Possible suffix types for guider exposures
GUIDER_SUFFIX_TYPES = ['stream', 'stacked_uncal', 'image_uncal', 'stacked_cal', 'image_cal']

# JWST data products
JWST_DATAPRODUCTS = ['IMAGE', 'SPECTRUM', 'SED', 'TIMESERIES', 'VISIBILITY',
                     'EVENTLIST', 'CUBE', 'CATALOG', 'ENGINEERING', 'NULL']

# Lowercase JWST instrument names
JWST_INSTRUMENT_NAMES = sorted(['niriss', 'nircam', 'nirspec', 'miri', 'fgs'])

# JWST instrument names with shorthand notation
JWST_INSTRUMENT_NAMES_SHORTHAND = {'gui': 'fgs',
                                   'mir': 'miri',
                                   'nis': 'niriss',
                                   'nrc': 'nircam',
                                   'nrs': 'nirspec'}

# Mixed case JWST instrument names
JWST_INSTRUMENT_NAMES_MIXEDCASE = {'fgs': 'FGS',
                                   'miri': 'MIRI',
                                   'nircam': 'NIRCam',
                                   'niriss': 'NIRISS',
                                   'nirspec': 'NIRSpec'}

# Upper case JWST instrument names
JWST_INSTRUMENT_NAMES_UPPERCASE = {key: value.upper() for key, value in
                                   JWST_INSTRUMENT_NAMES_MIXEDCASE.items()}

# Astoquery service string for each JWST instrument
JWST_MAST_SERVICES = ['Mast.Jwst.Filtered.{}'.format(value.title()) for value in
                      JWST_INSTRUMENT_NAMES]

# Available monitor names and their location for each JWST instrument
MONITORS = {
    'fgs': [('Bad Pixel Monitor', '#')],
    'miri': [('Dark Current Monitor', '#'),
             ('Data Trending', '/miri/miri_data_trending'),
             ('Bad Pixel Monitor', '#'),
             ('Cosmic Ray Monitor', '#'),
             ('Photometry Monitor', '#'),
             ('TA Failure Monitor', '#'),
             ('Blind Pointing Accuracy Monitor', '#'),
             ('Filter and Calibration Lamp Monitor', '#'),
             ('Thermal Emission Monitor', '#')],
    'nircam': [('Bias Monitor', '#'),
               ('Readnoise Monitor', '#'),
               ('Gain Level Monitor', '#'),
               ('Mean Dark Current Rate Monitor', '#'),
               ('Photometric Stability Monitor', '#')],
    'niriss': [('Bad Pixel Monitor', '#'),
               ('Readnoise Monitor', '#'),
               ('AMI Calibrator Monitor', '#'),
               ('TSO RMS Monitor', '#')],
    'nirspec': [('Optical Short Monitor', '#'),
                ('Target Acquisition Monitor', '#'),
                ('Data Trending', '/nirspec/nirspec_data_trending'),
                ('Detector Health Monitor', '#'),
                ('Ref Pix Monitor', '#'),
                ('Internal Lamp Monitor', '#'),
                ('Instrument Model Updates', '#'),
                ('Failed-open Shutter Monitor', '#')]}

# Possible suffix types for coronograph exposures
NIRCAM_CORONAGRAPHY_SUFFIX_TYPES = ['psfstack', 'psfalign', 'psfsub']

# NIRCam subarrays that use four amps for readout
NIRCAM_FOUR_AMP_SUBARRAYS = ['WFSS128R', 'WFSS64R']

# NIRCam long wavelength detector names
NIRCAM_LONGWAVE_DETECTORS = ['NRCA5', 'NRCB5']

# NIRCam short wavelength detector names
NIRCAM_SHORTWAVE_DETECTORS = ['NRCA1', 'NRCA2', 'NRCA3', 'NRCA4',
                              'NRCB1', 'NRCB2', 'NRCB3', 'NRCB4']

# NIRCam subarrays that use either one or four amps
NIRCAM_SUBARRAYS_ONE_OR_FOUR_AMPS = ['SUBGRISMSTRIPE64', 'SUBGRISMSTRIPE128', 'SUBGRISMSTRIPE256']

# Possible suffix types for AMI files
NIRISS_AMI_SUFFIX_TYPES = ['amiavg', 'aminorm', 'ami']

# Possible suffix types for time-series exposures
TIME_SERIES_SUFFIX_TYPES = ['phot', 'whtlt']

# Concatenate all suffix types (ordered to ensure successful matching)
FILE_SUFFIX_TYPES = GUIDER_SUFFIX_TYPES + GENERIC_SUFFIX_TYPES + \
                    TIME_SERIES_SUFFIX_TYPES + NIRCAM_CORONAGRAPHY_SUFFIX_TYPES + \
                    NIRISS_AMI_SUFFIX_TYPES
