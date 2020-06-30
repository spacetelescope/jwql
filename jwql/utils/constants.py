"""Globally defined and used variables for the ``jwql`` project.

Authors
-------

    - Johannes Sahlmann
    - Matthew Bourque
    - Bryan Hilbert
    - Ben Sunnquist
    - Teagan King

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

import inflection

# Each amplifier is represented by 2 tuples, the first for x coordinates
# and the second for y coordinates. Within each tuple are value for
# starting, ending, and step size. Step size is needed for MIRI, where
# the pixels corresponding to the 4 amplifiers are interleaved.
AMPLIFIER_BOUNDARIES = {'nircam': {'1': [(0, 512, 1), (0, 2048, 1)],
                                   '2': [(512, 1024, 1), (0, 2048, 1)],
                                   '3': [(1024, 1536, 1), (0, 2048, 1)],
                                   '4': [(1536, 2048, 1), (0, 2048, 1)]},
                        'niriss': {'1': [(0, 2048, 1), (0, 512, 1)],
                                   '2': [(0, 2048, 1), (512, 1024, 1)],
                                   '3': [(0, 2048, 1), (1024, 1536, 1)],
                                   '4': [(0, 2048, 1), (1536, 2048, 1)]},
                        'fgs': {'1': [(0, 512, 1), (0, 2048, 1)],
                                '2': [(512, 1024, 1), (0, 2048, 1)],
                                '3': [(1024, 1536, 1), (0, 2048, 1)],
                                '4': [(1536, 2048, 1), (0, 2048, 1)]},
                        'nirspec': {'1': [(0, 512, 1), (0, 2048, 1)],
                                    '2': [(512, 1024, 1), (0, 2048, 1)],
                                    '3': [(1024, 1536, 1), (0, 2048, 1)],
                                    '4': [(1536, 2048, 1), (0, 2048, 1)]},
                        'miri': {'1': [(0, 1032, 4), (0, 1024, 1)],
                                 '2': [(1, 1032, 4), (0, 1024, 1)],
                                 '3': [(2, 1032, 4), (0, 1024, 1)],
                                 '4': [(3, 1032, 4), (0, 1024, 1)]}}

# Dictionary describing instruments to which anomalies apply
ANOMALIES_PER_INSTRUMENT = {
    # anomalies affecting all instruments:
    'cosmic_ray_shower': ['fgs', 'miri', 'nircam', 'niriss', 'nirspec'],
    'diffraction_spike': ['fgs', 'miri', 'nircam', 'niriss', 'nirspec'],
    'excessive_saturation': ['fgs', 'miri', 'nircam', 'niriss', 'nirspec'],
    'guidestar_failure': ['fgs', 'miri', 'nircam', 'niriss', 'nirspec'],
    'persistence': ['fgs', 'miri', 'nircam', 'niriss', 'nirspec'],
    #anomalies affecting multiple instruments:
    'crosstalk': ['fgs', 'nircam', 'niriss', 'nirspec'],
    'data_transfer_error': ['fgs', 'nircam', 'niriss', 'nirspec'],
    'ghost': ['fgs', 'nircam', 'niriss', 'nirspec'],
    'snowball': ['fgs', 'nircam', 'niriss', 'nirspec'],
    # instrument-specific anomalies:
    'column_pull_up': ['miri'],
    'dominant_msa_leakage': ['nirspec'],
    'dragons_breath': ['nircam'],
    'glow': ['miri'],
    'internal_reflection': ['miri'],
    'optical_short': ['nirspec'],  # Only for MOS observations
    'row_pull_down': ['miri'],
    # additional anomalies:
    'other': ['fgs', 'miri', 'nircam', 'niriss', 'nirspec']}

# Defines the possible anomalies (with rendered name) to flag through the web app
ANOMALY_CHOICES = [(anomaly, inflection.titleize(anomaly)) for anomaly in ANOMALIES_PER_INSTRUMENT]

# Possible exposure types for dark current data
DARK_EXP_TYPES = {'nircam': ['NRC_DARK'],
                  'niriss': ['NIS_DARK'],
                  'miri': ['MIR_DARKIMG', 'MIR_DARKMRS', 'MIR_DARKALL'],
                  'nirspec': ['NRS_DARK'],
                  'fgs': ['FGS_DARK']}

EXPTYPES = {"nircam": {"imaging": "NRC_IMAGE", "ts_imaging": "NRC_TSIMAGE",
                       "wfss": "NRC_WFSS", "ts_grism": "NRC_TSGRISM"},
            "niriss": {"imaging": "NIS_IMAGE", "ami": "NIS_IMAGE", "pom": "NIS_IMAGE",
                       "wfss": "NIS_WFSS"},
            "fgs": {"imaging": "FGS_IMAGE"}}

FLAT_EXP_TYPES = {'nircam': ['NRC_FLAT'],
                  'niriss': ['NIS_LAMP'],
                  'miri': ['MIR_FLATIMAGE', 'MIR_FLATMRS'],
                  'nirspec': ['NRS_AUTOFLAT', 'NRS_LAMP'],
                  'fgs': ['FGS_INTFLAT']}

FILTERS_PER_INSTRUMENT = {'miri': ['F560W', 'F770W', 'F1000W', 'F1065C', 'F1130W', 'F1140C', 'F1280W',
                                   'F1500W', 'F1550C', 'F1800W', 'F2100W', 'F2300C', 'F2550W'],
                          'nircam': ['F070W', 'F090W', 'F115W', 'F140M', 'F150W', 'F150W2', 'F162M',
                                     'F164N', 'F182M', 'F187N', 'F200W', 'F210M', 'F212N', 'F250M',
                                     'F277W', 'F300M', 'F322W2', 'F323N', 'F335M', 'F356W', 'F360M',
                                     'F405N', 'F410M', 'F430M', 'F444W', 'F460M', 'F466N', 'F470N',
                                     'F480M'],
                          'niriss': ['F090W', 'F115W', 'F140M', 'F150W', 'F185M', 'F200W', 'F227W',
                                     'F356W', 'F380M', 'F430M', 'F444W', 'F480M'],
                          'nirspec': ['CLEAR', 'F070LP', 'F100LP', 'F170LP', 'F290LP']}

FOUR_AMP_SUBARRAYS = ['WFSS128R', 'WFSS64R', 'WFSS128C', 'WFSS64C']

# Names of full-frame apertures for all instruments
FULL_FRAME_APERTURES = {'NIRCAM': ['NRCA1_FULL', 'NRCA2_FULL', 'NRCA3_FULL', 'NRCA4_FULL',
                                   'NRCA5_FULL', 'NRCB1_FULL', 'NRCB2_FULL', 'NRCB3_FULL',
                                   'NRCB4_FULL', 'NRCB5_FULL'],
                        'NIRISS': ['NIS_CEN'],
                        'NIRSPEC': ['NRS1_FULL', 'NRS2_FULL'],
                        'MIRI': ['MIRIM_FULL']
                        }

# Possible suffix types for nominal files
GENERIC_SUFFIX_TYPES = ['uncal', 'cal', 'rateints', 'rate', 'trapsfilled', 'i2d',
                        'x1dints', 'x1d', 's2d', 's3d', 'dark', 'crfints',
                        'crf', 'ramp', 'fitopt', 'bsubints', 'bsub', 'cat']

# Possible suffix types for guider exposures
GUIDER_SUFFIX_TYPES = ['stream', 'stacked_uncal', 'image_uncal', 'stacked_cal', 'image_cal']

# Instrument monitor database tables
INSTRUMENT_MONITOR_DATABASE_TABLES = {
    'dark_monitor': ['<instrument>_dark_dark_current', '<instrument>_dark_pixel_stats', '<instrument>_dark_query_history'],
    'bad_pixel_monitor': ['<instrument>_bad_pixel_stats', '<instrument>_bad_pixel_query_history']}

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
               ('Mean Dark Current Rate Monitor', '/nircam/dark_monitor'),
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

# Dictionary of observing modes available for each instrument
OBSERVING_MODE_PER_INSTRUMENT = {'miri': ['Imaging', '4QPM Coronagraphic Imaging',
                                          'Lyot Coronagraphic Imaging', 'LRS', 'MRS'],
                                 'nircam': ['Imaging', 'Coronagraphic Imaging', 'WFSS',
                                            'Time-Series Imaging', 'Grism Time Series'],
                                 'niriss': ['WFSS', 'SOSS', 'AMI', 'Imaging'],
                                 'nirspec': ['Multi-Object Spectroscopy', 'IFU Spectroscopy',
                                             'Fixed Slit Spectroscopy', 'Bright Object Time Series']}

SUBARRAYS_ONE_OR_FOUR_AMPS = ['SUBGRISMSTRIPE64', 'SUBGRISMSTRIPE128', 'SUBGRISMSTRIPE256']

# Possible suffix types for time-series exposures
TIME_SERIES_SUFFIX_TYPES = ['phot', 'whtlt']

# Concatenate all suffix types (ordered to ensure successful matching)
FILE_SUFFIX_TYPES = GUIDER_SUFFIX_TYPES + GENERIC_SUFFIX_TYPES + \
                    TIME_SERIES_SUFFIX_TYPES + NIRCAM_CORONAGRAPHY_SUFFIX_TYPES + \
                    NIRISS_AMI_SUFFIX_TYPES
