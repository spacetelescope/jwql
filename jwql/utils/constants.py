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
                        'nirspec': {'1': [(0, 2048, 1), (0, 512, 1)],
                                    '2': [(0, 2048, 1), (512, 1024, 1)],
                                    '3': [(0, 2048, 1), (1024, 1536, 1)],
                                    '4': [(0, 2048, 1), (1536, 2048, 1)]},
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
    # anomalies affecting multiple instruments:
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

# Defines the possible anomalies to flag through the web app
ANOMALY_CHOICES = [(anomaly, inflection.titleize(anomaly)) if anomaly != "dominant_msa_leakage"
                   else (anomaly, "Dominant MSA Leakage")
                   for anomaly in ANOMALIES_PER_INSTRUMENT]

ANOMALY_CHOICES_FGS = [(anomaly, inflection.titleize(anomaly)) for anomaly in ANOMALIES_PER_INSTRUMENT
                       if 'fgs' in ANOMALIES_PER_INSTRUMENT[anomaly]]

ANOMALY_CHOICES_MIRI = [(anomaly, inflection.titleize(anomaly)) for anomaly in ANOMALIES_PER_INSTRUMENT
                        if 'miri' in ANOMALIES_PER_INSTRUMENT[anomaly]]

ANOMALY_CHOICES_NIRCAM = [(anomaly, inflection.titleize(anomaly)) for anomaly in ANOMALIES_PER_INSTRUMENT
                          if 'nircam' in ANOMALIES_PER_INSTRUMENT[anomaly]]

ANOMALY_CHOICES_NIRISS = [(anomaly, inflection.titleize(anomaly)) for anomaly in ANOMALIES_PER_INSTRUMENT
                          if 'niriss' in ANOMALIES_PER_INSTRUMENT[anomaly]]

ANOMALY_CHOICES_NIRSPEC = [(anomaly, inflection.titleize(anomaly)) if anomaly != "dominant_msa_leakage"
                           else (anomaly, "Dominant MSA Leakage")
                           for anomaly in ANOMALIES_PER_INSTRUMENT
                           if 'nirspec' in ANOMALIES_PER_INSTRUMENT[anomaly]]

ANOMALY_CHOICES_PER_INSTRUMENT = {'fgs': ANOMALY_CHOICES_FGS,
                                  'miri': ANOMALY_CHOICES_MIRI,
                                  'nircam': ANOMALY_CHOICES_NIRCAM,
                                  'niriss': ANOMALY_CHOICES_NIRISS,
                                  'nirspec': ANOMALY_CHOICES_NIRSPEC
                                  }

APERTURES_PER_INSTRUMENT = {'NIRCAM': ['NRCA1_FULL', 'NRCA2_FULL', 'NRCA3_FULL', 'NRCA4_FULL',
                                       'NRCA5_FULL', 'NRCB1_FULL', 'NRCB2_FULL', 'NRCB3_FULL',
                                       'NRCB4_FULL', 'NRCB5_FULL'],
                            'NIRISS': ['NIS_CEN', 'NIS_SOSSFULL', 'NIS_AMIFULL', 'NIS_AMI1',
                                       'NIS_SUBSTRIP256', 'NIS_SUBSTRIP96',
                                       'NIS_SUB64', 'NIS_SUB128', 'NIS_SUB256'],
                            'NIRSPEC': ['NRS_FULL_MSA', 'NRS_FULL_IFU', 'NRS_S200A1_SLIT', 'NRS_S200A2_SLIT',
                                        'NRS_S400A1_SLIT', 'NRS_S1600A1_SLIT', 'NRS_S200B1_SLIT'],
                            'MIRI': ['MIRIM_SUB64', 'MIRIM_SUB128', 'MIRIM_SUB256', 'MIRIM_MASK1140',
                                     'MIRIM_MASK1065', 'MIRIM_MASK1550', 'MIRIM_MASKLYOT',
                                     'MIRIM_BRIGHTSKY', 'MIRIM_SLITLESSPRISM'],
                            'FGS': ['FGS1_FULL', 'FGS2_FULL']}

# Observing templates used for ASIC tuning. MAST query results that
# have one of these templates will be ignored
ASIC_TEMPLATES = ['ISIM ASIC Tuning']

# Bad pixel types by the type of data used to find them
BAD_PIXEL_TYPES = ['DEAD', 'HOT', 'LOW_QE', 'RC', 'OPEN', 'ADJ_OPEN', 'TELEGRAPH', 'OTHER_BAD_PIXEL']
DARKS_BAD_PIXEL_TYPES = ['HOT', 'RC', 'OTHER_BAD_PIXEL', 'TELEGRAPH']
FLATS_BAD_PIXEL_TYPES = ['DEAD', 'OPEN', 'ADJ_OPEN', 'LOW_QE']

# Possible exposure types for dark current data
DARK_EXP_TYPES = {'nircam': ['NRC_DARK'],
                  'niriss': ['NIS_DARK'],
                  'miri': ['MIR_DARKIMG', 'MIR_DARKMRS', 'MIR_DARKALL'],
                  'nirspec': ['NRS_DARK'],
                  'fgs': ['FGS_DARK']}

# Dictionary of observing modes available for each instrument
DETECTOR_PER_INSTRUMENT = {'miri': ['MIRIFULONG', 'MIRIFUSHORT', 'MIRIMAGE'],
                           'nircam': ['NRCB4', 'NRCA4', 'NRCA2', 'NRCALONG',
                                      'NRCBLONG', 'NRCB2', 'NRCB3', 'NRCA1',
                                      'NRCA3', 'NRCB1'],
                           'niriss': ['NIS'],
                           'nirspec': ['NRS1', 'NRS2'],
                           'fgs': ['GUIDER1', 'GUIDER2']}

EXP_TYPE_PER_INSTRUMENT = {'fgs': ['FGS_FOCUS', 'FGS_IMAGE', 'FGS_INTFLAT',
                                   'FGS_SKYFLAT', 'FGS_DARK'],
                           'miri': ['MIR_FLATMRS', 'MIR_MRS', 'MIR_FLATIMAGE',
                                    'MIR_DARK', 'MIR_LYOT', 'MIR_IMAGE',
                                    'MIR_LRS-FIXEDSLIT', 'MIR_LRS-SLITLESS',
                                    'MIR_CORONCAL', 'MIR_4QPM', 'MIR_FLATIMAGE-EXT',
                                    'MIR_TACQ', 'MIR_DARKMRS',
                                    'MIR_DARKIMG', 'MIR_FLATMRS-EXT', 'MIR_TACONFIRM'],
                           'nircam': ['NRC_LED', 'NRC_DARK', 'NRC_CORON',
                                      'NRC_IMAGE', 'NRC_FOCUS', 'NRC_TSGRISM',
                                      'NRC_TSIMAGE', 'NRC_WFSS', 'NRC_TACQ',
                                      'NRC_TACONFIRM', 'NRC_FLAT', 'NRC_GRISM'],
                           'niriss': ['NIS_IMAGE', 'NIS_FOCUS', 'NIS_SOSS',
                                      'NIS_AMI', 'NIS_LAMP', 'NIS_WFSS', 'NIS_DARK',
                                      'NIS_EXTCAL', 'NIS_TACONFIRM', 'NIS_TACQ'],
                           'nirspec': ['NRS_IFU', 'NRS_MSASPEC', 'NRS_BRIGHTOBJ', 'NRS_DARK',
                                       'NRS_AUTOWAVE', 'NRS_LAMP', 'NRS_AUTOFLAT', 'NRS_IMAGE',
                                       'NRS_CONFIRM', 'NRS_FIXEDSLIT', 'NRS_MIMF', 'NRS_FOCUS',
                                       'NRS_TACONFIRM', 'NRS_WATA', 'NRS_MSATA']}

EXPTYPES = {"nircam": {"imaging": "NRC_IMAGE", "ts_imaging": "NRC_TSIMAGE",
                       "wfss": "NRC_WFSS", "ts_grism": "NRC_TSGRISM"},
            "niriss": {"imaging": "NIS_IMAGE", "ami": "NIS_IMAGE",
                       "pom": "NIS_IMAGE", "wfss": "NIS_WFSS"},
            "fgs": {"imaging": "FGS_IMAGE"}}

# Filename Component Lengths
FILE_AC_CAR_ID_LEN = 4
FILE_AC_O_ID_LEN = 3
FILE_ACT_LEN = 2
FILE_DATETIME_LEN = 13
FILE_EPOCH_LEN = 1
FILE_GUIDESTAR_ATTMPT_LEN = 1
FILE_OBS_LEN = 3
FILE_PARALLEL_SEQ_ID_LEN = 1
FILE_PROG_ID_LEN = 5
FILE_SEG_LEN = 3
FILE_SOURCE_ID_LEN = 5
FILE_TARG_ID_LEN = 3
FILE_VISIT_GRP_LEN = 2
FILE_VISIT_LEN = 3

# MSA metadata file do not have a standard suffix attached
FILETYPE_WO_STANDARD_SUFFIX = 'msa.fits'

FLAT_EXP_TYPES = {'nircam': ['NRC_FLAT'],
                  'niriss': ['NIS_LAMP'],
                  'miri': ['MIR_FLATIMAGE', 'MIR_FLATMRS'],
                  'nirspec': ['NRS_AUTOFLAT', 'NRS_LAMP'],
                  'fgs': ['FGS_INTFLAT']}

FILTERS_PER_INSTRUMENT = {'fgs': [],
                          'miri': ['F1000W', 'F1130W', 'F1280W', 'OPAQUE', 'F2300C', 'F560W', 'P750L',
                                   'F1500W', 'F2550W', 'F770W', 'FLENS', 'FND', 'F2100W', 'F1800W',
                                   'F1550C', 'F1140C', 'F2550WR', 'F1065C'],
                          'nircam': ['F070W', 'F090W', 'F115W', 'F140M', 'F150W', 'F150W2', 'F182M',
                                     'F187N', 'F200W', 'F210M', 'F212N', 'F250M', 'F277W', 'F300M',
                                     'F322W2', 'F335M', 'F356W', 'F360M', 'F410M', 'F430M', 'F444W',
                                     'F460M', 'F480M'],
                          'niriss': ['CLEAR', 'F380M', 'F480M', 'GR150R', 'F430M', 'GR150C', 'F444W',
                                     'F356W', 'F277W'],
                          'nirspec': ['F290LP', 'F170LP', 'OPAQUE', 'F100LP', 'F070LP', 'F140X', 'CLEAR', 'F110W']}

FOUR_AMP_SUBARRAYS = ['WFSS128R', 'WFSS64R']

# Names of full-frame apertures for all instruments
FULL_FRAME_APERTURES = {'NIRCAM': ['NRCA1_FULL', 'NRCA2_FULL', 'NRCA3_FULL', 'NRCA4_FULL',
                                   'NRCA5_FULL', 'NRCB1_FULL', 'NRCB2_FULL', 'NRCB3_FULL',
                                   'NRCB4_FULL', 'NRCB5_FULL'],
                        'NIRISS': ['NIS_CEN'],
                        'NIRSPEC': ['NRS1_FULL', 'NRS2_FULL'],
                        'MIRI': ['MIRIM_FULL'],
                        'FGS': ['FGS1_FULL', 'FGS2_FULL']
                        }

# Possible suffix types for nominal files
GENERIC_SUFFIX_TYPES = ['uncal', 'cal', 'rateints', 'rate', 'trapsfilled', 'i2d',
                        'x1dints', 'x1d', 's2d', 's3d', 'dark', 'crfints',
                        'crf', 'ramp', 'fitopt', 'bsubints', 'bsub', 'cat', 'segm', 'c1d']

# Gratings available for each instrument
GRATING_PER_INSTRUMENT = {'fgs': [],
                          'miri': [],
                          'nircam': [],
                          'niriss': [],
                          'nirspec': ['G140M', 'G235M', 'G395M', 'G140H',
                                      'G235H', 'G395H', 'PRISM']
                          }

# Possible suffix types for guider exposures
GUIDER_SUFFIX_TYPES = ['stream', 'stacked_uncal', 'image_uncal', 'stacked_cal', 'image_cal']

# JWQL should ignore some filetypes in the filesystem.
IGNORED_SUFFIXES = ['original', 'stream', 'x1d', 'x1dints', 'c1d']

# Instrument monitor database tables
INSTRUMENT_MONITOR_DATABASE_TABLES = {
    'dark_monitor': ['<instrument>_dark_dark_current', '<instrument>_dark_pixel_stats', '<instrument>_dark_query_history'],
    'bad_pixel_monitor': ['<instrument>_bad_pixel_stats', '<instrument>_bad_pixel_query_history']}

INSTRUMENT_SERVICE_MATCH = {
    'FGS': 'Mast.Jwst.Filtered.Fgs',
    'MIRI': 'Mast.Jwst.Filtered.Miri',
    'NIRCam': 'Mast.Jwst.Filtered.Nircam',
    'NIRISS': 'Mast.Jwst.Filtered.Niriss',
    'NIRSpec': 'Mast.Jwst.Filtered.Nirspec'}

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
    'fgs': [('Bad Pixel Monitor', '/fgs/bad_pixel_monitor'),
            ('Readnoise Monitor', '/fgs/readnoise_monitor'),
            ('Dark Current Monitor', '/fgs/dark_monitor')],
    'miri': [('Dark Current Monitor', '/miri/dark_monitor'),
             ('Data Trending', '#'),
             ('Bad Pixel Monitor', '/miri/bad_pixel_monitor'),
             ('Readnoise Monitor', '/miri/readnoise_monitor'),
             ('Cosmic Ray Monitor', '#'),
             ('Photometry Monitor', '#'),
             ('TA Failure Monitor', '#'),
             ('Blind Pointing Accuracy Monitor', '#'),
             ('Filter and Calibration Lamp Monitor', '#'),
             ('Thermal Emission Monitor', '#')],
    'nircam': [('Bias Monitor', '/nircam/bias_monitor'),
               ('Readnoise Monitor', '/nircam/readnoise_monitor'),
               ('Gain Level Monitor', '#'),
               ('Dark Current Monitor', '/nircam/dark_monitor'),
               ('Bad Pixel Monitor', '/nircam/bad_pixel_monitor'),
               ('Photometric Stability Monitor', '#')],
    'niriss': [('Bad Pixel Monitor', '/niriss/bad_pixel_monitor'),
               ('Readnoise Monitor', '/niriss/readnoise_monitor'),
               ('AMI Calibrator Monitor', '#'),
               ('TSO RMS Monitor', '#'),
               ('Bias Monitor', '/niriss/bias_monitor'),
               ('Dark Current Monitor', '/niriss/dark_monitor')],
    'nirspec': [('Optical Short Monitor', '#'),
                ('Bad Pixel Monitor', '/nirspec/bad_pixel_monitor'),
                ('Readnoise Monitor', '/nirspec/readnoise_monitor'),
                ('Target Acquisition Monitor', '#'),
                ('Data Trending', '#'),
                ('Detector Health Monitor', '#'),
                ('Ref Pix Monitor', '#'),
                ('Internal Lamp Monitor', '#'),
                ('Instrument Model Updates', '#'),
                ('Failed-open Shutter Monitor', '#'),
                ('Bias Monitor', '/nirspec/bias_monitor'),
                ('Dark Monitor', '/nirspec/dark_monitor')]}

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
NIRISS_AMI_SUFFIX_TYPES = ['amiavg', 'aminorm', 'ami', 'psf-amiavg']

# Base name for the file listing the preview images for a given instrument.
# The complete name will have "_{instrument.lower}.txt" added to the end of this.
PREVIEW_IMAGE_LISTFILE = 'preview_image_inventory'

# RAPID-style readout patterns for each instrument. Added so we can
# differentiate in MAST searches for e.g. the dark current monitor
RAPID_READPATTERNS = {'fgs': ['FGSRAPID'],
                      'miri': ['FAST', 'FASTR1', 'SLOW', 'SLOWR1', 'FASTGRPAVG',
                               'FASTGRPAVG8', 'FASTGRPAVG16', 'FASTGRPAVG32',
                               'FASTGRPAVG64', 'FASTR100'],
                      'nircam': ['RAPID'],
                      'niriss': ['NISRAPID'],
                      'nirspec': ['NRSRAPID', 'NRSIRS2RAPID']}

READPATT_PER_INSTRUMENT = {'fgs': ['FGS', 'FGSRAPID', 'FGS60', 'FGS840', 'FGS8370'],
                           'miri': ['FAST', 'FASTR1', 'SLOW', 'SLOWR1', 'FASTGRPAVG',
                                    'FASTGRPAVG8', 'FASTGRPAVG16', 'FASTGRPAVG32',
                                    'FASTGRPAVG64', 'FASTR100'],
                           'nircam': ['RAPID', 'SHALLOW2', 'BRIGHT2', 'MEDIUM2', 'SHALLOW4',
                                      'MEDIUM8', 'BRIGHT1', 'DEEP2', 'DEEP8'],
                           'niriss': ['NISRAPID', 'NIS'],
                           'nirspec': ['NRS', 'NRSRAPID', 'NRSIRS2RAPID',
                                       'NRSRAPIDD2', 'NRSRAPIDD6']}

SUBARRAYS_ONE_OR_FOUR_AMPS = ['SUBGRISMSTRIPE64', 'SUBGRISMSTRIPE128', 'SUBGRISMSTRIPE256']

# Filename suffixes that need to include the association value in the suffix in
# order to identify the preview image file. This should only be crf and crfints,
# since those are essentially level 2 files that are output by the level 3 pipeline.
SUFFIXES_TO_ADD_ASSOCIATION = ['crf', 'crfints']

# Filename suffixes where data have been averaged over integrations
SUFFIXES_WITH_AVERAGED_INTS = ['rate', 'cal', 'crf', 'i2d', 'bsub']

# Base name for the file listing the thumbnail images for a given instrument.
# The complete name will have "_{instrument.lower}.txt" added to the end of this.
THUMBNAIL_LISTFILE = 'thumbnail_inventory'

# Possible suffix types for time-series exposures
TIME_SERIES_SUFFIX_TYPES = ['phot', 'whtlt']

# Possible suffix types for WFS&C files
WFSC_SUFFIX_TYPES = ['wfscmb']

# Concatenate all suffix types (ordered to ensure successful matching)
FILE_SUFFIX_TYPES = GUIDER_SUFFIX_TYPES + GENERIC_SUFFIX_TYPES + \
    TIME_SERIES_SUFFIX_TYPES + NIRCAM_CORONAGRAPHY_SUFFIX_TYPES + \
    NIRISS_AMI_SUFFIX_TYPES + WFSC_SUFFIX_TYPES

# Instrument Documentation Links
URL_DICT = {'fgs': 'https://jwst-docs.stsci.edu/jwst-observatory-hardware/jwst-fine-guidance-sensor',
            'miri': 'https://jwst-docs.stsci.edu/jwst-mid-infrared-instrument',
            'niriss': 'https://jwst-docs.stsci.edu/jwst-near-infrared-imager-and-slitless-spectrograph',
            'nirspec': 'https://jwst-docs.stsci.edu/jwst-near-infrared-spectrograph',
            'nircam': 'https://jwst-docs.stsci.edu/jwst-near-infrared-camera'}
