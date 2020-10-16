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
# Anomalies selected by user in dynamic_anomaly
ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES = {}

# Apertures selected by user in dynamic_anomaly
APERTURES_CHOSEN = {}

# Anomalies available to select after instruments are selected in dynamic_anomaly
# Default is all anomalies common to all instruments
CURRENT_ANOMALIES = {}

# Maximum exposure time selected by user in dynamic_anomaly. Corresponds to EFFEXPTM in MAST.
EXPTIME_MAX = ['999999999999999']   # select all as default

# Minimum exposure time selected by user in dynamic_anomaly. Corresponds to EFFEXPTM in MAST.
EXPTIME_MIN = ['0']  # select all as default

# Filters selected by user in dynamic_anomaly
FILTERS_CHOSEN = {}

# Instruments selected by user in dynamic_anomaly
INSTRUMENTS_CHOSEN = []

# Observing modes selected by user in dynamic_anomaly
OBSERVING_MODES_CHOSEN = {}

# Thumbnails selected by user in dynamic_anomaly
THUMBNAILS = []
