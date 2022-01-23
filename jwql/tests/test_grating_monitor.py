#! /usr/bin/env python

"""Tests for the ``grating_monitor`` module.

Authors
-------

    - Teagan King

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_grating_monitor.py
"""

from astropy.time import Time
import os
import pytest

from jwql.edb.engineering_database import get_mnemonics
from jwql.database.database_interface import NIRSpecGratingQueryHistory, NIRSpecGratingStats
from jwql.instrument_monitors.common_monitors import grating_monitor
from jwql.utils.constants import GRATING_TELEMETRY
from sqlalchemy.sql.sqltypes import TIME

ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')


def test_identify_tables():
    """Be sure the correct database tables are identified
    """
    grating = grating_monitor.Grating()
    grating.instrument = 'nirspec'
    grating.identify_tables()
    assert grating.query_table == eval('NIRSpecGratingQueryHistory')
    assert grating.pixel_table == eval('NIRSpecGratingStats')


def test_mnemonics_retrieval():
    start_telemetry_time = Time(Time(59013, format='mjd'), format='decimalyear')
    end_telemetry_time = Time(Time(55010, format='mjd'), format='decimalyear')
    # THIS IS A LONG TIME FRAME...
    mnemonics_list = ['INRSI_GWA_MECH_POS', 'INRSH_GWA_ADCMGAIN', 'INRSH_GWA_ADCMOFFSET', 'INRSH_GWA_MOTOR_VREF', 'INRSI_C_GWA_X_POSITION', 'INRSI_C_GWA_Y_POSITION']
    mnemonics = get_mnemonics(mnemonics_list, start_telemetry_time, end_telemetry_time)

    grating_val = mnemonics['INRSI_GWA_MECH_POS'].data[0]['euvalue']
    adcmgain = mnemonics['INRSH_GWA_ADCMGAIN'].data[0]['euvalue']
    adcmoffset = mnemonics['INRSH_GWA_ADCMOFFSET'].data[0]['euvalue']
    motor_vref = mnemonics['INRSH_GWA_MOTOR_VREF'].data[0]['euvalue']
    x_pos = mnemonics['INRSI_C_GWA_X_POSITION'].data[0]['euvalue']
    y_pos = mnemonics['INRSI_C_GWA_Y_POSITION'].data[0]['euvalue']

    assert grating_val == 'MIRROR'
    assert adcmgain == 2.5001527415
    assert adcmoffset == -0.0010681153
    assert motor_vref == -0.0009155273999999999
    assert x_pos == 173.1699688
    assert y_pos == 98.6046408
