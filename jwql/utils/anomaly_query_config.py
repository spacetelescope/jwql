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
APERTURES_CHOSEN = ["No apertures selected"]

# Anomalies available to select after instruments are selected in query_anomaly
# Default is all anomalies common to all instruments
CURRENT_ANOMALIES = ['cosmic_ray_shower', 'diffraction_spike', 'excessive_saturation',
                     'guidestar_failure', 'persistence', 'other']

# Instruments selected by user in query_anomaly
INSTRUMENTS_CHOSEN = ["No instruments selected"]

print("INSTRUMENTS_CHOSEN", INSTRUMENTS_CHOSEN)

# Observing modes selected by user
OBSERVING_MODES_CHOSEN = ["No observing modes selected"]

# Anomalies selected by user in query_anomaly_3
ANOMALIES_CHOSEN_FROM_CURRENT_ANOMALIES = ["No anomalies selected"]

# Filters selected by user in query_anomaly_2
FILTERS_CHOSEN = ["No filters selected"]
