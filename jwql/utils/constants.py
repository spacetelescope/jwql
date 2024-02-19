"""Globally defined and used variables for the ``jwql`` project.

Authors
-------

    - Johannes Sahlmann
    - Matthew Bourque
    - Bryan Hilbert
    - Ben Sunnquist
    - Teagan King
    - Mike Engesser
    - Maria Pena-Guerrero
    - Rachel Cooper
    - Brad Sappington

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

import asdf
import inflection
import os

# Each amplifier is represented by 2 tuples, the first for x coordinates
# and the second for y coordinates. Within each tuple are value for
# starting, ending, and step size. Step size is needed for MIRI, where
# the pixels corresponding to the 4 amplifiers are interleaved.
AMPLIFIER_BOUNDARIES = {
    "nircam": {
        "1": [(0, 512, 1), (0, 2048, 1)],
        "2": [(512, 1024, 1), (0, 2048, 1)],
        "3": [(1024, 1536, 1), (0, 2048, 1)],
        "4": [(1536, 2048, 1), (0, 2048, 1)],
    },
    "niriss": {
        "1": [(0, 2048, 1), (0, 512, 1)],
        "2": [(0, 2048, 1), (512, 1024, 1)],
        "3": [(0, 2048, 1), (1024, 1536, 1)],
        "4": [(0, 2048, 1), (1536, 2048, 1)],
    },
    "fgs": {
        "1": [(0, 512, 1), (0, 2048, 1)],
        "2": [(512, 1024, 1), (0, 2048, 1)],
        "3": [(1024, 1536, 1), (0, 2048, 1)],
        "4": [(1536, 2048, 1), (0, 2048, 1)],
    },
    "nirspec": {
        "1": [(0, 2048, 1), (0, 512, 1)],
        "2": [(0, 2048, 1), (512, 1024, 1)],
        "3": [(0, 2048, 1), (1024, 1536, 1)],
        "4": [(0, 2048, 1), (1536, 2048, 1)],
    },
    "miri": {
        "1": [(0, 1032, 4), (0, 1024, 1)],
        "2": [(1, 1032, 4), (0, 1024, 1)],
        "3": [(2, 1032, 4), (0, 1024, 1)],
        "4": [(3, 1032, 4), (0, 1024, 1)],
    },
}

# Dictionary describing instruments to which anomalies apply
ANOMALIES_PER_INSTRUMENT = {
    # anomalies affecting all instruments:
    "diffraction_spike": ["fgs", "miri", "nircam", "niriss", "nirspec"],
    "excessive_saturation": ["fgs", "miri", "nircam", "niriss", "nirspec"],
    "persistence": ["fgs", "miri", "nircam", "niriss", "nirspec"],
    # anomalies affecting multiple instruments:
    "crosstalk": ["fgs", "nircam", "niriss"],
    "data_transfer_error": ["fgs", "nircam", "niriss"],
    "ghost": ["fgs", "nircam", "niriss"],
    "guidestar_failure": ["fgs", "miri", "nircam", "niriss"],
    "unusual_cosmic_rays": ["fgs", "nircam", "niriss", "nirspec"],
    "unusual_snowballs": ["fgs", "nircam", "niriss", "nirspec"],
    # instrument-specific anomalies:
    "cosmic_ray_shower": ["miri"],
    "column_pull_up": ["miri"],
    "column_pull_down": ["miri"],
    "noticeable_msa_leakage": ["nirspec"],
    "dragons_breath": ["nircam"],
    "mrs_glow": ["miri"],
    "mrs_zipper": ["miri"],
    "internal_reflection": ["miri"],
    "new_short": ["nirspec"],  # Only for MOS observations
    "row_pull_up": ["miri"],
    "row_pull_down": ["miri"],
    "lrs_contamination": ["miri"],
    "tree_rings": ["miri"],
    "scattered_light": ["niriss", "nircam", "nirspec"],
    "claws": ["nircam"],
    "wisps": ["nircam"],
    "tilt_event": ["nircam"],
    "light_saber": ["niriss"],
    "transient_short": ["nirspec"],
    "subsequently_masked_short": ["nirspec"],
    "monitored_short": ["nirspec"],
    "bright_object_not_a_short": ["nirspec"],
    # additional anomalies:
    "other": ["fgs", "miri", "nircam", "niriss", "nirspec"],
    "needs_discussion": ["fgs", "miri", "nircam", "niriss", "nirspec"],
}

# Defines the possible anomalies to flag through the web app
ANOMALY_CHOICES = [
    (anomaly, anomaly.replace("_", " ").upper())
    for anomaly in ANOMALIES_PER_INSTRUMENT
    for anomaly in ANOMALIES_PER_INSTRUMENT
]

ANOMALY_CHOICES_FGS = [
    (anomaly, inflection.titleize(anomaly).upper())
    for anomaly in ANOMALIES_PER_INSTRUMENT
    if "fgs" in ANOMALIES_PER_INSTRUMENT[anomaly]
]

ANOMALY_CHOICES_MIRI = [
    (anomaly, anomaly.replace("_", " ").upper())
    for anomaly in ANOMALIES_PER_INSTRUMENT
    if "miri" in ANOMALIES_PER_INSTRUMENT[anomaly]
]

ANOMALY_CHOICES_NIRCAM = [
    (anomaly, anomaly.replace("_", " ").upper())
    for anomaly in ANOMALIES_PER_INSTRUMENT
    if "nircam" in ANOMALIES_PER_INSTRUMENT[anomaly]
]

ANOMALY_CHOICES_NIRISS = [
    (anomaly, anomaly.replace("_", " ").upper())
    for anomaly in ANOMALIES_PER_INSTRUMENT
    if "niriss" in ANOMALIES_PER_INSTRUMENT[anomaly]
]

ANOMALY_CHOICES_NIRSPEC = [
    (anomaly, anomaly.replace("_", " ").upper())
    for anomaly in ANOMALIES_PER_INSTRUMENT
    if "nirspec" in ANOMALIES_PER_INSTRUMENT[anomaly]
]

ANOMALY_CHOICES_PER_INSTRUMENT = {
    "fgs": ANOMALY_CHOICES_FGS,
    "miri": ANOMALY_CHOICES_MIRI,
    "nircam": ANOMALY_CHOICES_NIRCAM,
    "niriss": ANOMALY_CHOICES_NIRISS,
    "nirspec": ANOMALY_CHOICES_NIRSPEC,
}

APERTURES_PER_INSTRUMENT = {
    "nircam": [],  # NIRCAM aperture redundant, can just use Subarray + Detector
    "niriss": [],  # NIRISS preferred subarray only
    "nirspec": [
        "NRS_FULL_MSA",
        "NRS_FULL_IFU",
        "NRS_S200A1_SLIT",
        "NRS_S200A2_SLIT",
        "NRS_S400A1_SLIT",
        "NRS_S1600A1_SLIT",
        "NRS_S200B1_SLIT",
    ],
    "miri": [],  # MIRI preferred subarray only
    "fgs": ["FGS1_FULL", "FGS2_FULL"],
}

# Observing templates used for ASIC tuning. MAST query results that
# have one of these templates will be ignored
ASIC_TEMPLATES = ["ISIM ASIC Tuning"]

# Bad pixel types by the type of data used to find them
BAD_PIXEL_TYPES = [
    "DEAD",
    "HOT",
    "LOW_QE",
    "RC",
    "OPEN",
    "ADJ_OPEN",
    "TELEGRAPH",
    "OTHER_BAD_PIXEL",
]
DARKS_BAD_PIXEL_TYPES = ["HOT", "RC", "OTHER_BAD_PIXEL", "TELEGRAPH"]
FLATS_BAD_PIXEL_TYPES = ["DEAD", "OPEN", "ADJ_OPEN", "LOW_QE"]

# The maximum number of bad pixels allowed on a bad pixel monitor plot. If there
# are more than this number of bad pixels identified for a particular type of
# bad pixel, then the figure is saved as a png rather than an interactive plot,
# in order to reduce the amount of data sent to the browser.
BAD_PIXEL_MONITOR_MAX_POINTS_TO_PLOT = 15000

# Possible exposure types for dark current data
DARK_EXP_TYPES = {
    "nircam": ["NRC_DARK"],
    "niriss": ["NIS_DARK"],
    "miri": ["MIR_DARKIMG", "MIR_DARKMRS", "MIR_DARKALL"],
    "nirspec": ["NRS_DARK"],
    "fgs": ["FGS_DARK"],
}

# Types of potential bad pixels identified by the dark current monitor
DARK_MONITOR_BADPIX_TYPES = ["hot", "dead", "noisy"]

# Maximum number of potential new bad pixels to overplot on the dark monitor
# mean dark image plot. Too many overplotted points starts to obscure the image
# itself, and are most likely not really new bad pixels
DARK_MONITOR_MAX_BADPOINTS_TO_PLOT = 1000

# Dictionary of observing modes available for each instrument
DETECTOR_PER_INSTRUMENT = {
    "miri": ["MIRIFULONG", "MIRIFUSHORT", "MIRIMAGE"],
    "nircam": [
        "NRCB4",
        "NRCA4",
        "NRCA2",
        "NRCALONG",
        "NRCBLONG",
        "NRCB2",
        "NRCB3",
        "NRCA1",
        "NRCA3",
        "NRCB1",
    ],
    "niriss": ["NIS"],
    "nirspec": ["NRS1", "NRS2"],
    "fgs": ["GUIDER1", "GUIDER2"],
}

# Default time range to use for EDB monitor telemetry plots. The plots will
# go from this starting time to the monitor run time, unless otherwise requested.
EDB_DEFAULT_PLOT_RANGE = 14  # days.

EXP_TYPE_PER_INSTRUMENT = {
    "fgs": ["FGS_FOCUS", "FGS_IMAGE", "FGS_INTFLAT", "FGS_SKYFLAT", "FGS_DARK"],
    "miri": [
        "MIR_FLATMRS",
        "MIR_MRS",
        "MIR_FLATIMAGE",
        "MIR_DARK",
        "MIR_LYOT",
        "MIR_IMAGE",
        "MIR_LRS-FIXEDSLIT",
        "MIR_LRS-SLITLESS",
        "MIR_CORONCAL",
        "MIR_4QPM",
        "MIR_FLATIMAGE-EXT",
        "MIR_TACQ",
        "MIR_DARKMRS",
        "MIR_DARKIMG",
        "MIR_FLATMRS-EXT",
        "MIR_TACONFIRM",
    ],
    "nircam": [
        "NRC_LED",
        "NRC_DARK",
        "NRC_CORON",
        "NRC_IMAGE",
        "NRC_FOCUS",
        "NRC_TSGRISM",
        "NRC_TSIMAGE",
        "NRC_WFSS",
        "NRC_TACQ",
        "NRC_TACONFIRM",
        "NRC_FLAT",
        "NRC_GRISM",
    ],
    "niriss": [
        "NIS_IMAGE",
        "NIS_FOCUS",
        "NIS_SOSS",
        "NIS_AMI",
        "NIS_LAMP",
        "NIS_WFSS",
        "NIS_DARK",
        "NIS_EXTCAL",
        "NIS_TACONFIRM",
        "NIS_TACQ",
    ],
    "nirspec": [
        "NRS_IFU",
        "NRS_MSASPEC",
        "NRS_BRIGHTOBJ",
        "NRS_DARK",
        "NRS_AUTOWAVE",
        "NRS_LAMP",
        "NRS_AUTOFLAT",
        "NRS_IMAGE",
        "NRS_CONFIRM",
        "NRS_FIXEDSLIT",
        "NRS_MIMF",
        "NRS_FOCUS",
        "NRS_TACONFIRM",
        "NRS_WATA",
        "NRS_MSATA",
    ],
}

EXPTYPES = {
    "nircam": {
        "imaging": "NRC_IMAGE",
        "ts_imaging": "NRC_TSIMAGE",
        "wfss": "NRC_WFSS",
        "ts_grism": "NRC_TSGRISM",
    },
    "niriss": {
        "imaging": "NIS_IMAGE",
        "ami": "NIS_IMAGE",
        "pom": "NIS_IMAGE",
        "wfss": "NIS_WFSS",
    },
    "fgs": {"imaging": "FGS_IMAGE"},
}

EXPOSURE_PAGE_SUFFIX_ORDER = [
    "uncal",
    "dark",
    "trapsfilled",
    "ramp",
    "rate",
    "rateints",
    "fitopt",
    "cal",
    "calints",
    "msa",
    "crf",
    "crfints",
    "bsub",
    "bsubints",
    "i2d",
    "s2d",
    "s3d",
    "x1d",
    "x1dints",
    "cat",
    "segm",
    "c1d",
    "psfstack",
    "psfalign",
    "psfsub",
    "amiavg",
    "aminorm",
    "ami",
    "psf-amiavg",
    "phot",
    "whtlt",
    "wfscmb",
]

# Filename Component Lengths
FILE_AC_CAR_ID_LEN = 4
FILE_AC_O_ID_LEN = 3
FILE_ACT_LEN = 2
FILE_DATETIME_LEN = 13
FILE_EPOCH_LEN = 1
FILE_GUIDESTAR_ATTMPT_LEN_MIN = 1
FILE_GUIDESTAR_ATTMPT_LEN_MAX = 3
FILE_OBS_LEN = 3
FILE_PARALLEL_SEQ_ID_LEN = 1
FILE_PROG_ID_LEN = 5
FILE_SEG_LEN = 3
FILE_SOURCE_ID_LEN = 5
FILE_TARG_ID_LEN = 3
FILE_VISIT_GRP_LEN = 2
FILE_VISIT_LEN = 3

# MSA metadata file do not have a standard suffix attached
FILETYPE_WO_STANDARD_SUFFIX = "msa.fits"

FLAT_EXP_TYPES = {
    "nircam": ["NRC_FLAT"],
    "niriss": ["NIS_LAMP"],
    "miri": ["MIR_FLATIMAGE", "MIR_FLATMRS"],
    "nirspec": ["NRS_AUTOFLAT", "NRS_LAMP"],
    "fgs": ["FGS_INTFLAT"],
}

# output subdirectories to keep track of via the filesytem monitor
FILESYSTEM_MONITOR_SUBDIRS = ['logs', 'outputs', 'working', 'preview_images', 'thumbnails', 'all']

FILTERS_PER_INSTRUMENT = {
    "fgs": [],
    "miri": [
        "F560W",
        "F770W",
        "F1000W",
        "F1065C",
        "F1130W",
        "F1140C",
        "F1280W",
        "F1500W",
        "F1550C",
        "F1800W",
        "F2100W",
        "F2300C",
        "F2550W",
        "F2550WR",
        "FLENS",
        "FND",
        "OPAQUE",
        "P750L",
    ],
    "nircam": [
        "F070W",
        "F090W",
        "F115W",
        "F140M",
        "F150W",
        "F150W2",
        "F182M",
        "F187N",
        "F200W",
        "F210M",
        "F212N",
        "WLP4",
        "F277W",
        "F356W",
        "F444W",
        "F300M",
        "F335M",
        "F360M",
        "F410M",
        "F430M",
        "F460M",
        "F480M",
        "F250M",
        "F322W2",
    ],
    "niriss": [
        "F090W",
        "F115W",
        "F140M",
        "F150W",
        "F200W",
        "F277W",
        "F356W",
        "F380M",
        "F430M",
        "F444W",
        "F480M",
        "GR150C",
        "GR150R",
    ],
    "nirspec": [
        "CLEAR",
        "F070LP",
        "F100LP",
        "F110W",
        "F140X",
        "F170LP",
        "F290LP",
        "OPAQUE",
        "P750L",
    ],
}

FOUR_AMP_SUBARRAYS = ["WFSS128R", "WFSS64R"]

# Names of full-frame apertures for all instruments
FULL_FRAME_APERTURES = {
    "NIRCAM": [
        "NRCA1_FULL",
        "NRCA2_FULL",
        "NRCA3_FULL",
        "NRCA4_FULL",
        "NRCA5_FULL",
        "NRCB1_FULL",
        "NRCB2_FULL",
        "NRCB3_FULL",
        "NRCB4_FULL",
        "NRCB5_FULL",
    ],
    "NIRISS": ["NIS_CEN"],
    "NIRSPEC": ["NRS1_FULL", "NRS2_FULL"],
    "MIRI": ["MIRIM_FULL"],
    "FGS": ["FGS1_FULL", "FGS2_FULL"],
}

# Possible suffix types for nominal files
GENERIC_SUFFIX_TYPES = [
    "uncal",
    "cal",
    "rateints",
    "rate",
    "trapsfilled",
    "i2d",
    "x1dints",
    "x1d",
    "s2d",
    "s3d",
    "dark",
    "crfints",
    "crf",
    "ramp",
    "fitopt",
    "bsubints",
    "bsub",
    "cat",
    "segm",
    "c1d",
]

# Gratings available for each instrument
GRATING_PER_INSTRUMENT = {
    "fgs": [],
    "miri": [],
    "nircam": [],
    "niriss": [],
    "nirspec": [
        "G140M",
        "G235M",
        "G395M",
        "G140H",
        "G235H",
        "G395H",
        "PRISM",
        "MIRROR",
    ],
}

# Filename extensions for guider data
GUIDER_FILENAME_TYPE = ["gs-fg", "gs-track", "gs-id", "gs-acq1", "gs-acq2"]

# Possible suffix types for guider exposures
GUIDER_SUFFIX_TYPES = [
    "stream",
    "stacked_uncal",
    "image_uncal",
    "stacked_cal",
    "image_cal",
]

# JWQL should ignore some filetypes in the filesystem.
IGNORED_SUFFIXES = ["original", "stream", "x1d", "x1dints", "c1d", "pre-image"]

# Instrument monitor database tables
INSTRUMENT_MONITOR_DATABASE_TABLES = {
    "dark_monitor": [
        "<instrument>_dark_dark_current",
        "<instrument>_dark_pixel_stats",
        "<instrument>_dark_query_history",
    ],
    "bad_pixel_monitor": [
        "<instrument>_bad_pixel_stats",
        "<instrument>_bad_pixel_query_history",
    ],
    "cosmic_ray_monitor": [
        "<instrument>_cosmic_ray_stats",
        "<instrument>_cosmic_ray_query_history",
    ],
    "msata_monitor": ["<instrument>_ta_stats", "<instrument>_ta_query_history"],
    "wata_monitor": ["<instrument>_ta_stats", "<instrument>_ta_query_history"],
}

INSTRUMENT_SERVICE_MATCH = {
    "FGS": "Mast.Jwst.Filtered.Fgs",
    "MIRI": "Mast.Jwst.Filtered.Miri",
    "NIRCam": "Mast.Jwst.Filtered.Nircam",
    "NIRISS": "Mast.Jwst.Filtered.Niriss",
    "NIRSpec": "Mast.Jwst.Filtered.Nirspec",
}

# JWST data products
JWST_DATAPRODUCTS = [
    "IMAGE",
    "SPECTRUM",
    "SED",
    "TIMESERIES",
    "VISIBILITY",
    "EVENTLIST",
    "CUBE",
    "CATALOG",
    "ENGINEERING",
    "NULL",
]

# Lowercase JWST instrument names
JWST_INSTRUMENT_NAMES = sorted(["niriss", "nircam", "nirspec", "miri", "fgs"])

# JWST instrument names with shorthand notation
JWST_INSTRUMENT_NAMES_SHORTHAND = {
    "gui": "fgs",
    "mir": "miri",
    "nis": "niriss",
    "nrc": "nircam",
    "nrs": "nirspec",
}

# Mixed case JWST instrument names
JWST_INSTRUMENT_NAMES_MIXEDCASE = {
    "fgs": "FGS",
    "miri": "MIRI",
    "nircam": "NIRCam",
    "niriss": "NIRISS",
    "nirspec": "NIRSpec",
}

# Upper case JWST instrument names
JWST_INSTRUMENT_NAMES_UPPERCASE = {
    key: value.upper() for key, value in JWST_INSTRUMENT_NAMES_MIXEDCASE.items()
}

# Astoquery service string for each JWST instrument
JWST_MAST_SERVICES = [
    "Mast.Jwst.Filtered.{}".format(value.title()) for value in JWST_INSTRUMENT_NAMES
]

# Possible values for look status filter
LOOK_OPTIONS = ["New", "Viewed"]

# Maximum number of records returned by MAST for a single query
MAST_QUERY_LIMIT = 550000

# Expected position sensor values for MIRI. Used by the EDB monitor
# to filter out bad values. Tuple values are the expected value and
# the standard deviation associated with the value
MIRI_POS_RATIO_VALUES = {
    "FW": {
        "FND": (-164.8728073, 0.204655346),
        "OPAQUE": (380.6122145, 0.078856646),
        "F1000W": (-24.15638797, 0.182865887),
        "F1130W": (137.8245397, 0.24910941),
        "F1280W": (-298.7062532, 0.229963508),
        "P750L": (12.39439777, 0.246932037),
        "F1500W": (-377.9888235, 0.263432415),
        "F1800W": (435.9046314, 0.27885876),
        "F2100W": (-126.5991201, 0.197193968),
        "F560W": (218.0010353, 0.282554884),
        "FLENS": (-212.7978283, 0.409300208),
        "F2300C": (306.0488778, 0.265448583),
        "F770W": (-62.48455213, 0.340861733),
        "F1550C": (188.7366748, 0.291288105),
        "F2550W": (-324.2364737, 0.176262309),
        "F1140C": (82.81057729, 0.169772457),
        "F2550WR": (-255.5816917, 0.251581688),
        "F1065C": (261.4486618, 0.16177981),
    },
    "CCC": {"CLOSED": (398.0376386, 0.173703628), "OPEN": (504.0482685, 0.328112274)},
    "GW14": {
        "SHORT": (626.9411005, 0.116034024),
        "MEDIUM": (342.8685233, 0.127123169),
        "LONG": (408.8339259, 0.117079193),
    },
    "GW23": {
        "SHORT": (619.7948107, 0.215417336),
        "MEDIUM": (373.1697309, 0.204314122),
        "LONG": (441.6632325, 0.349161169),
    },
}

# Suffix for msa files
MSA_SUFFIX = ["msa"]

# Available monitor names and their location for each JWST instrument
MONITORS = {
    'fgs': [('Bad Pixel Monitor', '/fgs/bad_pixel_monitor'),
            ('Cosmic Ray Monitor', '#'),
            ('Dark Current Monitor', '/fgs/dark_monitor'),
            ('EDB Telemetry Monitor', '/fgs/edb_monitor'),
            ('Readnoise Monitor', '/fgs/readnoise_monitor')],
    'miri': [('Bad Pixel Monitor', '/miri/bad_pixel_monitor'),
             ('Cosmic Ray Monitor', '#'),
             ('Dark Current Monitor', '/miri/dark_monitor'),
             ('EDB Telemetry Monitor', '/miri/edb_monitor'),
             ('Readnoise Monitor', '/miri/readnoise_monitor')],
    'nircam': [('Background Monitor', '/nircam/background_monitor'),
               ('Bad Pixel Monitor', '/nircam/bad_pixel_monitor'),
               ('Bias Monitor', '/nircam/bias_monitor'),
               ('Claw Monitor', '/nircam/claw_monitor'),
               ('Cosmic Ray Monitor', '#'),
               ('Dark Current Monitor', '/nircam/dark_monitor'),
               ('EDB Telemetry Monitor', '/nircam/edb_monitor'),
               ('Readnoise Monitor', '/nircam/readnoise_monitor')],
    'niriss': [('Bad Pixel Monitor', '/niriss/bad_pixel_monitor'),
               ('Bias Monitor', '/niriss/bias_monitor'),
               ('Cosmic Ray Monitor', '#'),
               ('Dark Current Monitor', '/niriss/dark_monitor'),
               ('EDB Telemetry Monitor', '/niriss/edb_monitor'),
               ('Readnoise Monitor', '/niriss/readnoise_monitor')],
    'nirspec': [('Bad Pixel Monitor', '/nirspec/bad_pixel_monitor'),
                ('Bias Monitor', '/nirspec/bias_monitor'),
                ('Dark Monitor', '/nirspec/dark_monitor'),
                ('Cosmic Ray Monitor', '#'),
                ('EDB Telemetry Monitor', '/nirspec/edb_monitor'),
                ('MSATA Monitor', '/nirspec/msata_monitor'),
                ('Readnoise Monitor', '/nirspec/readnoise_monitor'),
                ('WATA Monitor', '/nirspec/wata_monitor')
                ]}
# Possible suffix types for coronograph exposures
NIRCAM_CORONAGRAPHY_SUFFIX_TYPES = ["psfstack", "psfalign", "psfsub"]

# NIRCam subarrays that use four amps for readout
NIRCAM_FOUR_AMP_SUBARRAYS = ["WFSS128R", "WFSS64R"]

# NIRCam long wavelength detector names
NIRCAM_LONGWAVE_DETECTORS = ["NRCA5", "NRCB5"]

# NIRCam short wavelength detector names
NIRCAM_SHORTWAVE_DETECTORS = [
    "NRCA1",
    "NRCA2",
    "NRCA3",
    "NRCA4",
    "NRCB1",
    "NRCB2",
    "NRCB3",
    "NRCB4",
]

# NIRCam subarrays that use either one or four amps
NIRCAM_SUBARRAYS_ONE_OR_FOUR_AMPS = [
    "SUBGRISMSTRIPE64",
    "SUBGRISMSTRIPE128",
    "SUBGRISMSTRIPE256",
]

# Possible suffix types for AMI files
NIRISS_AMI_SUFFIX_TYPES = ["amiavg", "aminorm", "ami", "psf-amiavg"]

# Base name for the file listing the preview images for a given instrument.
# The complete name will have "_{instrument.lower}.txt" added to the end of this.
PREVIEW_IMAGE_LISTFILE = "preview_image_inventory"

# All possible proposal categories
PROPOSAL_CATEGORIES = ["AR", "CAL", "COM", "DD", "ENG", "GO", "GTO", "NASA", "SURVEY"]

PUPILS_PER_INSTRUMENT = {
    "nircam": [
        "CLEAR",
        "FLAT",
        "F162M",
        "F164N",
        "GDHS0",
        "GDHS60",
        "MASKBAR",
        "MASKIPR",
        "MASKRND",
        "PINHOLES",
        "WLM8",
        "WLP8",
        "F323N",
        "F405N",
        "F466N",
        "F470N",
        "GRISMC",
        "GRISMR",
        "GRISMV2",
        "GRISMV3",
    ],
    "niriss": [
        "CLEARP",
        "F090W",
        "F115W",
        "F140M",
        "F150W",
        "F158M",
        "F200W",
        "GR700XD",
        "NRM",
    ],
    "nirspec": [],
    "miri": [],
    "fgs": [],
}


# Keep keys defined via class as they are used many places with potential mispellings
# Keys are in sort order from general to instrument specific, then alphabetical
# within instrument specific fields.
class QueryConfigKeys:
    INSTRUMENTS = "INSTRUMENTS"
    PROPOSAL_CATEGORY = "PROPOSAL_CATEGORY"
    LOOK_STATUS = "LOOK_STATUS"
    DATE_RANGE = "DATE_RANGE"
    NUM_PER_PAGE = "NUM_PER_PAGE"
    SORT_TYPE = "SORT_TYPE"
    ANOMALIES = "ANOMALIES"
    APERTURES = "APERTURES"
    DETECTORS = "DETECTORS"
    EXP_TYPES = "EXP_TYPES"
    FILTERS = "FILTERS"
    GRATINGS = "GRATINGS"
    PUPILS = "PUPILS"
    READ_PATTS = "READ_PATTS"
    SUBARRAYS = "SUBARRAYS"


# Template for parameters to be stored in "query_config" session for query_page
QUERY_CONFIG_TEMPLATE = {
    QueryConfigKeys.INSTRUMENTS: [],
    QueryConfigKeys.PROPOSAL_CATEGORY: [],
    QueryConfigKeys.LOOK_STATUS: [],
    QueryConfigKeys.NUM_PER_PAGE: 100,
    QueryConfigKeys.SORT_TYPE: "Recent",
    QueryConfigKeys.DATE_RANGE: "",
    QueryConfigKeys.ANOMALIES: {},
    QueryConfigKeys.APERTURES: {},
    QueryConfigKeys.DETECTORS: {},
    QueryConfigKeys.EXP_TYPES: {},
    QueryConfigKeys.FILTERS: {},
    QueryConfigKeys.GRATINGS: {},
    QueryConfigKeys.PUPILS: {},
    QueryConfigKeys.READ_PATTS: {},
    QueryConfigKeys.SUBARRAYS: {},
}

# RAPID-style readout patterns for each instrument. Added so we can
# differentiate in MAST searches for e.g. the dark current monitor
RAPID_READPATTERNS = {
    "fgs": ["FGSRAPID"],
    "miri": [
        "FAST",
        "FASTR1",
        "SLOW",
        "SLOWR1",
        "FASTGRPAVG",
        "FASTGRPAVG8",
        "FASTGRPAVG16",
        "FASTGRPAVG32",
        "FASTGRPAVG64",
        "FASTR100",
    ],
    "nircam": ["RAPID"],
    "niriss": ["NISRAPID"],
    "nirspec": ["NRSRAPID", "NRSIRS2RAPID"],
}

READPATT_PER_INSTRUMENT = {
    "fgs": ["FGS", "FGSRAPID", "FGS60", "FGS840", "FGS8370"],
    "miri": [
        "FAST",
        "FASTR1",
        "SLOW",
        "SLOWR1",
        "FASTGRPAVG",
        "FASTGRPAVG8",
        "FASTGRPAVG16",
        "FASTGRPAVG32",
        "FASTGRPAVG64",
        "FASTR100",
    ],
    "nircam": [
        "RAPID",
        "SHALLOW2",
        "BRIGHT2",
        "MEDIUM2",
        "SHALLOW4",
        "MEDIUM8",
        "BRIGHT1",
        "DEEP2",
        "DEEP8",
    ],
    "niriss": ["NISRAPID", "NIS"],
    "nirspec": ["NRS", "NRSRAPID", "NRSIRS2RAPID", "NRSRAPIDD2", "NRSRAPIDD6"],
}


REPORT_KEYS_PER_INSTRUMENT = {
    "fgs": [
        "proposal",
        "exp_type",
        "expstart",
        "filter",
        "aperture",
        "detector",
        "subarray",
        "viewed",
    ],
    "miri": [
        "proposal",
        "exp_type",
        "expstart",
        "filter",
        "aperture",
        "detector",
        "subarray",
        "viewed",
    ],
    "nircam": [
        "proposal",
        "exp_type",
        "expstart",
        "filter",
        "pupil",
        "aperture",
        "detector",
        "subarray",
        "viewed",
    ],
    "niriss": [
        "proposal",
        "exp_type",
        "expstart",
        "filter",
        "pupil",
        "aperture",
        "detector",
        "subarray",
        "viewed",
    ],
    "nirspec": ["exp_type", "filter", "grating", "read_patt_num", "viewed"],
}

# Possible values for sort order
SORT_OPTIONS = ["Ascending", "Descending", "Recent", "Oldest"]

SUBARRAYS_ONE_OR_FOUR_AMPS = [
    "SUBGRISMSTRIPE64",
    "SUBGRISMSTRIPE128",
    "SUBGRISMSTRIPE256",
]

schema = asdf.schema.load_schema("http://stsci.edu/schemas/jwst_datamodel/subarray.schema")
SUBARRAYS_PER_INSTRUMENT = {
    "nircam": ['FULL'] + sorted(schema["properties"]["meta"]["properties"]["subarray"]["properties"]["name"]["anyOf"][2]['enum']),
    "niriss": ['FULL'] + sorted(schema["properties"]["meta"]["properties"]["subarray"]["properties"]["name"]["anyOf"][4]['enum']),
    "nirspec": ['FULL'] + sorted(schema["properties"]["meta"]["properties"]["subarray"]["properties"]["name"]["anyOf"][6]['enum']),
    "miri": ['FULL'] + sorted(schema["properties"]["meta"]["properties"]["subarray"]["properties"]["name"]["anyOf"][1]['enum']),
    "fgs": ['FULL'] + sorted(schema["properties"]["meta"]["properties"]["subarray"]["properties"]["name"]["anyOf"][0]['enum'])
    }

# Filename suffixes that need to include the association value in the suffix in
# order to identify the preview image file. This should only be crf and crfints,
# since those are essentially level 2 files that are output by the level 3 pipeline.
SUFFIXES_TO_ADD_ASSOCIATION = ["crf", "crfints"]

# Filename suffixes where data have been averaged over integrations
SUFFIXES_WITH_AVERAGED_INTS = ["rate", "cal", "crf", "i2d", "bsub"]

# boolean accessed according to a viewed flag
THUMBNAIL_FILTER_LOOK = ["New", "Viewed"]

# Base name for the file listing the thumbnail images for a given instrument.
# The complete name will have "_{instrument.lower}.txt" added to the end of this.
THUMBNAIL_LISTFILE = "thumbnail_inventory"

# Possible suffix types for time-series exposures
TIME_SERIES_SUFFIX_TYPES = ["phot", "whtlt"]

# Possible suffix types for WFS&C files
WFSC_SUFFIX_TYPES = ["wfscmb"]

# Concatenate all suffix types (ordered to ensure successful matching)
FILE_SUFFIX_TYPES = (
    GUIDER_SUFFIX_TYPES
    + GENERIC_SUFFIX_TYPES
    + TIME_SERIES_SUFFIX_TYPES
    + NIRCAM_CORONAGRAPHY_SUFFIX_TYPES
    + NIRISS_AMI_SUFFIX_TYPES
    + WFSC_SUFFIX_TYPES
    + MSA_SUFFIX
)

# Instrument Documentation Links
URL_DICT = {
    "fgs": "https://jwst-docs.stsci.edu/jwst-observatory-hardware/jwst-fine-guidance-sensor",
    "miri": "https://jwst-docs.stsci.edu/jwst-mid-infrared-instrument",
    "niriss": "https://jwst-docs.stsci.edu/jwst-near-infrared-imager-and-slitless-spectrograph",
    "nirspec": "https://jwst-docs.stsci.edu/jwst-near-infrared-spectrograph",
    "nircam": "https://jwst-docs.stsci.edu/jwst-near-infrared-camera",
}

# Determine if the code is being run as part of CI checking on github
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

# Determine if the code is being run as part of a Readthedocs build
ON_READTHEDOCS = False
if 'READTHEDOCS' in os.environ:  # pragma: no cover
    ON_READTHEDOCS = os.environ['READTHEDOCS']
