"""Globally defined and used variables for the JWQL query anomaly
feature. Variables will be re-defined when anomaly query forms are
submitted.

Authors
-------

    - Teagan King


Use
---
    This variables within this module are intended to be directly
    imported, e.g.:
    ::

        from jwql.utils.query_config import CHOSEN_INSTRUMENTS
"""
# Anomalies selected by user in anomaly_query
ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES = {}

# Apertures selected by user in anomaly_query
APERTURES_CHOSEN = {}

# Anomalies available to select after instruments are selected in anomaly_query
# Default is all anomalies common to all instruments
CURRENT_ANOMALIES = {}

# Observing modes selected by user in anomaly_query
DETECTORS_CHOSEN = {}

# Maximum exposure time selected by user in anomaly_query.
# Corresponds to EFFEXPTM in MAST.
EXPTIME_MAX = ['999999999999999']   # select all as default

# Minimum exposure time selected by user in anomaly_query.
# Corresponds to EFFEXPTM in MAST.
EXPTIME_MIN = ['0']  # select all as default

# Exposure types selected by user in anomaly_query
EXPTYPES_CHOSEN = {}

# Filters selected by user in anomaly_query
FILTERS_CHOSEN = {}

# Gratings selected by user in anomaly_query
GRATINGS_CHOSEN = {}

# Instruments selected by user in anomaly_query
INSTRUMENTS_CHOSEN = []

# Read patterns selected by user in anomaly_query
READPATTS_CHOSEN = {}

# Thumbnails selected by user in anomaly_query
THUMBNAILS = []
