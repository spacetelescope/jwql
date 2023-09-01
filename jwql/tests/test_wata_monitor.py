#! /usr/bin/env python

"""Tests for the WATA monitor module.

    Authors
    -------

    - Maria Pena-Guerrero

    Use
    ---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_msata_monitor.py
    """

import os
import pandas as pd
import numpy as np
import pytest
from datetime import datetime
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure

from jwql.instrument_monitors.nirspec_monitors.ta_monitors.wata_monitor import WATA
from jwql.database.database_interface import NIRSpecTAQueryHistory
from jwql.utils.utils import get_config, ensure_dir_exists
from jwql.utils import monitor_utils, permissions

ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

# define the type of a Bokeh plot type
bokeh_plot_type = type(figure())


def define_testdata():
    """Define the data to test with.

    Parameters
    ----------
    nints : int
        The number of integrations

    Returns
    -------
    wata_data : pandas dataframe
    """
    wata_dict = {
                    # info taken from main_hdr dict
                    'filename': ['jw09999001001_02101_00001_nrs1_uncal.fits'],
                    'date_obs': ['2022-06-22'],
                    'visit_id': ['V09999001001P0000000002101'],
                    'tafilter': ['F110W'],
                    'detector': ['NRS1'],
                    'readout': ['NRSRAPID'],
                    'subarray': ['FULL'],
                    # info taken from ta_hdr dict
                    'ta_status': ['SUCCESSFUL'],
                    'status_reason': ['-999'],
                    'star_name': ['-999'],
                    'star_ra': [-999.0],
                    'star_dec': [-999.0],
                    'star_mag': [-999.0],
                    'star_catalog': [-999],
                    'planned_v2': [-999.0],
                    'planned_v3': [-999.0],
                    'stamp_start_col': [-999],
                    'stamp_start_row': [-999],
                    'star_detector': ['-999'],
                    'max_val_box': [-999.0],
                    'max_val_box_col': [-999.0],
                    'max_val_box_row': [-999.0],
                    'iterations': [-999],
                    'corr_col': [-999.0],
                    'corr_row': [-999.0],
                    'stamp_final_col': [-999.0],
                    'stamp_final_row': [-999.0],
                    'detector_final_col': [-999.0],
                    'detector_final_row': [-999.0],
                    'final_sci_x': [-999.0],
                    'final_sci_y': [-999.0],
                    'measured_v2': [-999.0],
                    'measured_v3': [-999.0],
                    'ref_v2': [-999.0],
                    'ref_v3': [-999.0],
                    'v2_offset': [-999.0],
                    'v3_offset': [-999.0],
                    'sam_x': [-999.0],
                    'sam_y': [-999.0],
                }
    # create the additional arrays
    bool_status, status_colors = [], []
    for tas, do_str in zip(wata_dict['ta_status'], wata_dict['date_obs']):
        if 'unsuccessful' not in tas.lower():
            bool_status.append(1)
            status_colors.append('blue')
        else:
            bool_status.append(0)
            status_colors.append('red')

    # add these to the bokeh data structure
    wata_dict['ta_status_bool'] = bool_status
    wata_dict['status_colors'] = status_colors

    # create the dataframe
    wata_data = pd.DataFrame(wata_dict)
    return wata_data


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_query_ta():
    """Test the ``query_mast`` function"""

    query_start = 59833.0
    query_end = 59844.6

    # query mast
    result = monitor_utils.mast_query_ta('nirspec', 'NRS_S1600A1_SLIT', query_start, query_end)

    # eliminate duplicates (sometimes rate files are returned with cal files)
    result = [r for r in result if r['productLevel'] == '2b']
    assert len(result) == 16

    # query local model
    alternate = monitor_utils.model_query_ta('nirspec', 'NRS_S1600A1_SLIT', query_start, query_end)
    assert len(alternate) == len(result)

    # check that filenames match up - model returns rootfiles, mast returns filenames
    result = sorted(result, key=lambda x: x['filename'])
    alternate = sorted(alternate, key=lambda x: x['root_name'])
    for i, rootfile in enumerate(alternate):
        assert rootfile['root_name'] in result[i]['filename']


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_most_recent_search():
    """Test the ``most_recent_search`` function"""

    ta = WATA()
    ta.aperture = 'NRS_S1600A1_SLIT'
    ta.query_table = NIRSpecTAQueryHistory

    result = ta.most_recent_search()

    assert isinstance(result, float)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_status():
    """Test the ``plt_status`` function"""

    ta = WATA()
    wata_data = define_testdata()
    ta.source = ColumnDataSource(data=wata_data)
    ta.add_time_column()
    ta.setup_date_range()
    result = ta.plt_status()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_residual_offsets():
    """Test the ``plt_residual_offsets`` function"""

    ta = WATA()
    wata_data = define_testdata()
    ta.source = ColumnDataSource(data=wata_data)
    ta.add_time_column()
    ta.setup_date_range()
    result = ta.plt_residual_offsets()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_v2offset_time():
    """Test the ``plt_v2offset_time`` function"""

    ta = WATA()
    wata_data = define_testdata()
    ta.source = ColumnDataSource(data=wata_data)
    ta.add_time_column()
    ta.setup_date_range()
    result = ta.plt_v2offset_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_v3offset_time():
    """Test the ``plt_v3offset_time`` function"""

    ta = WATA()
    wata_data = define_testdata()
    ta.source = ColumnDataSource(data=wata_data)
    ta.add_time_column()
    ta.setup_date_range()
    result = ta.plt_v3offset_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_mag_time():
    """Test the ``plt_mag_time`` function"""

    ta = WATA()
    wata_data = define_testdata()
    ta.source = ColumnDataSource(data=wata_data)
    ta.add_time_column()
    ta.setup_date_range()

    # create the arrays per filter and readout pattern
    nrsrapid_f140x, nrsrapid_f110w, nrsrapid_clear = [], [], []
    nrsrapidd6_f140x, nrsrapidd6_f110w, nrsrapidd6_clear = [], [], []
    filter_used, readout = ta.source.data['tafilter'], ta.source.data['readout']
    max_val_box, _ = ta.source.data['max_val_box'], ta.source.data['time_arr']
    for i, val in enumerate(max_val_box):
        if '140' in filter_used[i]:
            if readout[i].lower() == 'nrsrapid':
                nrsrapid_f140x.append(val)
                nrsrapid_f110w.append(np.NaN)
                nrsrapid_clear.append(np.NaN)
                nrsrapidd6_f140x.append(np.NaN)
                nrsrapidd6_f110w.append(np.NaN)
                nrsrapidd6_clear.append(np.NaN)
            elif readout[i].lower() == 'nrsrapidd6':
                nrsrapid_f140x.append(np.NaN)
                nrsrapid_f110w.append(np.NaN)
                nrsrapid_clear.append(np.NaN)
                nrsrapidd6_f140x.append(val)
                nrsrapidd6_f110w.append(np.NaN)
                nrsrapidd6_clear.append(np.NaN)
        elif '110' in filter_used[i]:
            if readout[i].lower() == 'nrsrapid':
                nrsrapid_f140x.append(np.NaN)
                nrsrapid_f110w.append(val)
                nrsrapid_clear.append(np.NaN)
                nrsrapidd6_f140x.append(np.NaN)
                nrsrapidd6_f110w.append(np.NaN)
                nrsrapidd6_clear.append(np.NaN)
            elif readout[i].lower() == 'nrsrapidd6':
                nrsrapid_f140x.append(np.NaN)
                nrsrapid_f110w.append(np.NaN)
                nrsrapid_clear.append(np.NaN)
                nrsrapidd6_f140x.append(np.NaN)
                nrsrapidd6_f110w.append(val)
                nrsrapidd6_clear.append(np.NaN)
        else:
            if readout[i].lower() == 'nrsrapid':
                nrsrapid_f140x.append(np.NaN)
                nrsrapid_f110w.append(np.NaN)
                nrsrapid_clear.append(val)
                nrsrapidd6_f140x.append(np.NaN)
                nrsrapidd6_f110w.append(np.NaN)
                nrsrapidd6_clear.append(np.NaN)
            elif readout[i].lower() == 'nrsrapidd6':
                nrsrapid_f140x.append(np.NaN)
                nrsrapid_f110w.append(np.NaN)
                nrsrapid_clear.append(np.NaN)
                nrsrapidd6_f140x.append(np.NaN)
                nrsrapidd6_f110w.append(np.NaN)
                nrsrapidd6_clear.append(val)
    # add to the bokeh data structure
    ta.source.data["nrsrapid_f140x"] = nrsrapid_f140x
    ta.source.data["nrsrapid_f110w"] = nrsrapid_f110w
    ta.source.data["nrsrapid_clear"] = nrsrapid_clear
    ta.source.data["nrsrapidd6_f140x"] = nrsrapidd6_f140x
    ta.source.data["nrsrapidd6_f110w"] = nrsrapidd6_f110w
    ta.source.data["nrsrapidd6_clear"] = nrsrapidd6_clear
    result = ta.plt_mag_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_unsuccessful_ta():
    """Test the ``get_unsuccessful_ta`` function"""

    ta = WATA()
    wata_data = define_testdata()
    ta.source = ColumnDataSource(data=wata_data)
    ta.add_time_column()
    ta.setup_date_range()

    list_failed, list_else = ta.get_unsuccessful_ta('ta_status_bool')

    assert list_else[0] == ta.source.data['ta_status_bool'][0]
    assert np.isnan(list_failed[0])


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_mk_plt_layout():
    """Test the ``mk_plt_layout`` function"""

    truth_script, truth_div = components(figure())

    ta = WATA()
    ta.output_dir = os.path.join(get_config()['outputs'], 'wata_monitor/tests')
    ensure_dir_exists(ta.output_dir)
    ta.output_file_name = os.path.join(ta.output_dir, "wata_layout.html")
    ta.wata_data = define_testdata()
    script, div = ta.mk_plt_layout()

    # set group write permission for the test file
    # to make sure others can overwrite it
    permissions.set_permissions(ta.output_file_name)

    assert type(script) == type(truth_script)
    assert type(div) == type(truth_div)
