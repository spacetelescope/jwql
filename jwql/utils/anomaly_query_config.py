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

# Apertures selected by user in query_anomaly_2
APERTURES_CHOSEN = {}

# Anomalies available to select after instruments are selected in query_anomaly
# Default is all anomalies common to all instruments
CURRENT_ANOMALIES = {}

# Instruments selected by user in query_anomaly
INSTRUMENTS_CHOSEN = []

# Observing modes selected by user in query_anomaly
OBSERVING_MODES_CHOSEN = {}

# Anomalies selected by user in query_anomaly
ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES = {}

# Filters selected by user in query_anomaly
FILTERS_CHOSEN = {}

# Minimum exposure time selected by user in query_anomaly. Corresponds to EFFEXPTM in MAST.
EXPTIME_MIN = ['0']  # select all as default

# Maximum exposure time selected by user in query_anomaly. Corresponds to EFFEXPTM in MAST.
EXPTIME_MAX = ['999999999999999']   # select all as default

THUMBNAILS = []
