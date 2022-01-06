#! /usr/bin/env python

"""Tests for the EDB telemetry

Authors
-------

    - Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_edb_telemetry_monitor.py
"""
import numpy as np
import os
import pytest

from astropy.table import Table
from astropy.table.column import Column
from astropy.time import Time, TimeDelta
import astropy.units as u

from jwql.edb.engineering_database import EdbMnemonic
from jwql.instrument_monitors.common_monitors import edb_telemetry_monitor as etm
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import condition as cond
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import utils as etm_utils

# Determine if tests are being run on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')



def test_conditions():
    """Test the extraction of data using the ```equal``` class.
    """
    # Create data for mnemonic of interest
    start_time = Time('2022-02-02')
    end_time = Time('2022-02-03')
    temp_data = Table()
    temp_data["euvalues"] = np.array([35., 35.1, 35.2, 36., 36.1, 36.2, 37.1, 37., 36., 36.])
    temp_data["dates"] = np.array([Time('2022-02-02') + TimeDelta(0.1*i, format='jd') for i in range(10)])
    meta = {}
    info = {}
    temperature = EdbMnemonic("TEMPERATURE", start_time, end_time, temp_data, meta, info)

    # Create conditional data
    current_data = {}
    current_data["euvalues"] = np.array([1., 1., 1., 2.5, 2.5, 2.5, 5.5, 5.5, 2.5, 2.5])
    #current_data["dates"] = np.arange(10)*0.1001 + 59612.
    current_data["dates"] = np.array([Time('2022-02-02') + TimeDelta(0.1001*i, format='jd') for i in range(10)])


    ##############################################################
    # Set up condition
    # Using separate classes for each of =, <, >
    #eq25 = cond.equal(current_data, 2.5)
    #condition_list = [eq25]
    #condition_1 = cond.condition(condition_list)


    # pick one of above or below....


    # Or using a single relation class
    eq25 = cond.relation_test(current_data, '==', 2.5)
    condition_list = [eq25]
    condition_1 = cond.condition(condition_list)
    ##########################################################

    # Extract the good data
    condition_1.extract_data(temperature.data)

    # Expected results
    expected_table = Table()
    #expected_table["dates"] = [59612.4, 59612.5, 59612.9]
    frac_days = [0.4, 0.5, 0.9]
    expected_table["dates"] = [Time('2022-02-02') + TimeDelta(frac, format='jd') for frac in frac_days]
    expected_table["euvalues"] = [36.1, 36.2, 36.0]

    assert np.all(condition_1.extracted_data == expected_table)
    assert condition_1.block_indexes == [0, 2]

    grt0 = cond.relation_test(current_data, '>', 0)
    condition_list.append(grt0)
    condition_2 = cond.condition(condition_list)
    condition_2.extract_data(temperature.data)
    assert np.all(condition_2.extracted_data == expected_table)
    assert condition_2.block_indexes == [0, 2]

    less10 = cond.relation_test(current_data, '<', 10)
    condition_list.append(less10)
    condition_3 = cond.condition(condition_list)
    condition_3.extract_data(temperature.data)
    assert np.all(condition_3.extracted_data == expected_table)
    assert condition_3.block_indexes == [0, 2]


def test_find_all_changes():
    """
    """
    inst = etm.EdbMnemonicMonitor()

    # Create test data
    start_time = Time('2022-02-02')
    end_time = Time('2022-02-03')
    temp_data = Table()
    temp_data["euvalues"] = [350., 350.1, 350.2, 360., 360.1, 360.2, 370.1, 370., 360., 360.]
    #temp_data["dates"] = np.arange(10)*0.1 + 59612.
    temp_data["dates"] = np.array([Time('2022-02-02') + TimeDelta(0.1 * i, format='jd') for i in range(10)])
    meta = {}
    info = {}
    temperature = EdbMnemonic("TEMPERATURE", start_time, end_time, temp_data, meta, info)

    # Create dictionary of dependency info
    dependency = [{"name": "CURRENT", "relation": "none", "threshold": 0}]

    # Create dependency data
    current_data = Table()
    current_data["euvalues"] = [1., 1., 1., 25., 25., 25., 55., 55., 25., 25.]
    #current_data["dates"] = np.arange(10)*0.1001 + 59612.
    current_data["dates"] = np.array([Time('2022-02-02') + TimeDelta(0.1001 * i, format='jd') for i in range(10)])
    inst.query_results[dependency[0]["name"]] = EdbMnemonic("CURRENT", start_time, end_time, current_data, meta, info)


    vals = inst.find_all_changes(temperature, dependency)
    means, meds, devs, times, dep_means, dep_meds, dep_devs, dep_times = vals
    assert means == [35.1, 36.1, 37.05, 36.]
    assert meds == [35.1, 36.1, 37.05, 36.]
    assert devs == []
    assert dep_means = [1., 2., 3., 2.]
    assert dep_meds = [1., 2., 3., 2.]
    assert dep_devs = [0., 0., 0., 0.]
    This is not working well. Strategy for how to find different values in the condition may need to change.


def test_multiple_conditions():
    """Test that filtering using multiple conditions is working as expected.
    """
    # Create data for mnemonic of interest
    start_time = Time('2022-02-02')
    end_time = Time('2022-02-03')
    temp_data = Table()
    temp_data["euvalues"] = Column(np.array([35., 35.1, 35.2, 36., 36.1, 36.2, 37.1, 37., 36., 36.]))
    temp_data["dates"] = Column(np.array([Time('2022-02-02') + TimeDelta(0.1*i, format='jd') for i in range(10)]))
    meta = {}
    info = {}
    temperature = EdbMnemonic("TEMPERATURE", start_time, end_time, temp_data, meta, info)

    # Create conditional data
    current_data = {}
    current_data["euvalues"] = Column(np.array([1., 2.5, 2.5, 2.5, 2.5, 2.5, 5.5, 5.5, 2.5, 2.5]))
    current_data["dates"] = Column(np.array([Time('2022-02-02') + TimeDelta(0.1001*i, format='jd') for i in range(10)]))

    element_data = {}
    element_data["euvalues"] = Column(np.repeat("OFF", 20))
    element_data["euvalues"][13:] = "ON"
    element_data["dates"] = Column(np.array([Time('2022-02-02') + TimeDelta(0.06*i, format='jd') for i in range(20)]))

    grt35 = cond.relation_test(temp_data, '>', 35.11)
    eq25 = cond.relation_test(current_data, '==', 2.5)
    off = cond.relation_test(element_data, '=', 'OFF')
    condition_list = [grt35, eq25, off]
    condition = cond.condition(condition_list)
    condition.extract_data(temperature.data)

    # Compare to expectations
    expected_table = temp_data[2:6]
    assert np.all(condition.extracted_data == expected_table)
    assert condition.block_indexes == [0, 4]


def test_remove_outer_points():
    """
    """
    data = Table()
    #data["dates"] = [56999.5, 57000., 57000.5, 57001., 57001.5]
    data["dates"] = [Time('2014-12-08') + TimeDelta(0.5 * (i+1), format='jd') for i in range(5)]
    data["euvalues"] = [1, 2, 3, 4, 5]
    mnem = EdbMnemonic('TEST', Time('2022-12-09'), Time('2022-12-10'), data, {}, {})
    etm_utils.remove_outer_points(mnem)
    assert all(mnem.data['MJD'][1:-1] == new.data['dates'])
    assert all(mnem.data['data'][1:-1] == new.data['euvalues'])


def test_get_averaging_time_duration():
    """
    """
    in_strings = ["5_minute", "45_second", "10_day", "2_hour"]
    expected_vals = [5 * u.minute, 45 * u.second, 10 * u.day, 2 * u.hour]

    for inval, outval in zip(in_strings, expected_vals):
        output = etm_utils.get_averaging_time_duration(inval)
        assert output == outval

    bad_strings = ["7_years", "nonsense"]
    for inval in bad_strings:
        with pytest.raises(ValueError) as e_info:
            output = etm_utils.get_averaging_time_duration(inval)


def test_get_query_duration():
    """
    """
    in_strings = ['daily_means', "every_change", "block_means", "time_interval", "none"]
    expected_vals = [15 * u.minute, 1 * u.day, 1 * u.day, 1 * u.day, 1 * u.day,]
    for inval, outval in zip(in_strings, expected_vals):
        output = etm_utils.get_query_duration(inval)
        assert output == outval

    with pytest.raises(ValueError) as e_info:
        output = etm_utils.get_query_duration("bad_string")


def test_key_check():
    """
    """
    d = {'key1': [1,2,3], 'key4': 'a'}
    assert etm_utils.check_key(d, 'key1') == d['key1']
    assert etm_utils.check_key(d, 'key2') == None




@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
