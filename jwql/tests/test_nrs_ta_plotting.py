"""Test NRS TA (WATA & MSATA) plotting bokeh routines.

Author
______
    - Mees Fix
"""

import datetime
import pandas as pd


from jwql.instrument_monitors.nirspec_monitors.ta_monitors.msata_monitor import MSATA
from jwql.instrument_monitors.nirspec_monitors.ta_monitors.wata_monitor import WATA


def test_nrs_msata_bokeh():
    test_row = {
        "id": 1,
        "filename": "filename",
        "date_obs": datetime.datetime(
            1990, 11, 15, 20, 28, 59, 8000, tzinfo=datetime.timezone.utc
        ),
        "visit_id": "visit_id",
        "tafilter": "tafilter",
        "detector": "detector",
        "readout": "readout",
        "subarray": "subarray",
        "num_refstars": 1,
        "ta_status": "ta_status",
        "v2halffacet": 1.0,
        "v3halffacet": 1.0,
        "v2msactr": 1.0,
        "v3msactr": 1.0,
        "lsv2offset": 1.0,
        "lsv3offset": 1.0,
        "lsoffsetmag": 1.0,
        "lsrolloffset": 1.0,
        "lsv2sigma": 1.0,
        "lsv3sigma": 1.0,
        "lsiterations": 1,
        "guidestarid": 1,
        "guidestarx": 1.0,
        "guidestary": 1.0,
        "guidestarroll": 1.0,
        "samx": 1.0,
        "samy": 1.0,
        "samroll": 1.0,
        "box_peak_value": [
            1.0,
            1.0,
        ],
        "reference_star_mag": [
            1.0,
            1.0,
        ],
        "convergence_status": [
            "convergence_status",
            "convergence_status",
        ],
        "reference_star_number": [
            1,
            1,
        ],
        "lsf_removed_status": [
            "lsf_removed_status",
            "lsf_removed_status",
        ],
        "lsf_removed_reason": [
            "lsf_removed_reason",
            "lsf_removed_reason",
        ],
        "lsf_removed_x": [
            1.0,
            1.0,
        ],
        "lsf_removed_y": [
            1.0,
            1.0,
        ],
        "planned_v2": [
            1.0,
            1.0,
        ],
        "planned_v3": [
            1.0,
            1.0,
        ],
        "stars_in_fit": 1,
        "entry_date": datetime.datetime(
            1990, 11, 15, 20, 28, 59, 8000, tzinfo=datetime.timezone.utc
        ),
    }

    df = pd.DataFrame([test_row])
    monitor = MSATA()
    monitor.output_file_name = "msata_output.html"
    monitor.mk_plt_layout(df)


def test_nrs_wata_bokeh():
    test_row = {
        "id": 1,
        "filename": "filename",
        "date_obs": datetime.datetime(
            1990, 11, 15, 20, 28, 59, 8000, tzinfo=datetime.timezone.utc
        ),
        "visit_id": "visit_id",
        "tafilter": "tafilter",
        "readout": "readout",
        "ta_status": "ta_status",
        "star_name": 1,
        "star_ra": 1.0,
        "star_dec": 1.0,
        "star_mag": 1.0,
        "star_catalog": 1,
        "planned_v2": 1.0,
        "planned_v3": 1.0,
        "stamp_start_col": 1,
        "stamp_start_row": 1,
        "star_detector": "star_detector",
        "max_val_box": 1.0,
        "max_val_box_col": 1,
        "max_val_box_row": 1,
        "iterations": 1,
        "corr_col": 1,
        "corr_row": 1,
        "stamp_final_col": 1.0,
        "stamp_final_row": 1.0,
        "detector_final_col": 1.0,
        "detector_final_row": 1.0,
        "final_sci_x": 1.0,
        "final_sci_y": 1.0,
        "measured_v2": 1.0,
        "measured_v3": 1.0,
        "ref_v2": 1.0,
        "ref_v3": 1.0,
        "v2_offset": 1.0,
        "v3_offset": 1.0,
        "sam_x": 1.0,
        "sam_y": 1.0,
        "entry_date": datetime.datetime(
            1990, 11, 15, 20, 28, 59, 8000, tzinfo=datetime.timezone.utc
        ),
        "nrsrapid_f140x": [
            1.0
        ],  # Not in DB but added to column source data in algorithm, adding here
        "nrsrapid_f110w": [
            1.0
        ],  # Not in DB but added to column source data in algorithm, adding here
        "nrsrapid_clear": [
            1.0
        ],  # Not in DB but added to column source data in algorithm, adding here
        "nrsrapidd6_f140x": [
            1.0
        ],  # Not in DB but added to column source data in algorithm, adding here
        "nrsrapidd6_f110w": [
            1.0
        ],  # Not in DB but added to column source data in algorithm, adding here
        "nrsrapidd6_clear": [
            1.0
        ],  # Not in DB but added to column source data in algorithm, adding here
    }

    df = pd.DataFrame([test_row])
    monitor = WATA()
    monitor.output_file_name = "wata_output.html"
    monitor.mk_plt_layout(df)
