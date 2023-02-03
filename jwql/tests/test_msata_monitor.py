#! /usr/bin/env python

"""Tests for the MSATA monitor module.

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
from random import randint
from datetime import datetime
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure

from jwql.instrument_monitors.nirspec_monitors.ta_monitors.msata_monitor import MSATA
from jwql.database.database_interface import NIRSpecTAQueryHistory
from jwql.utils.utils import get_config, ensure_dir_exists
from jwql.utils import monitor_utils



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
    msata_data : pandas dataframe
    """
    msata_dict = {
                    # info taken from main_hdr dict
                    'filename': ['jw09999001001_02101_00001_nrs1_uncal.fits'],
                    'date_obs': ['2022-06-22'],
                    'visit_id': ['V09999001001P0000000002101'],
                    'tafilter': ['F110W'],
                    'detector': ['NRS1'],
                    'readout': ['NRSRAPID'],
                    'subarray': ['FULL'],
                    # info taken from ta_hdr dict
                    'num_refstars': [12],
                    'ta_status': ['SUCCESSFUL'],
                    'status_rsn': ['-999'],
                    'v2halffacet': [-0.27568],
                    'v3halffacet': [0.10975],
                    'v2msactr': [378.523987],
                    'v3msactr': [-428.374481],
                    'lsv2offset': [-999.0],
                    'lsv3offset': [-999.0],
                    'lsoffsetmag': [-999.0],
                    'lsrolloffset': [-999.0],
                    'lsv2sigma': [-999.0],
                    'lsv3sigma': [-999.0],
                    'lsiterations': [-999],
                    'guidestarid': ['-999'],
                    'guidestarx': [-999.0],
                    'guidestary': [-999.0],
                    'guidestarroll': [-999.0],
                    'samx': [-999.0],
                    'samy': [-999.0],
                    'samroll': [-999.0],
                    'stars_in_fit': [-999]
                }
    # add info from ta_table
    num_refstars = msata_dict['num_refstars'][0]
    msata_dict['box_peak_value'] =  [[8000 for _ in range(num_refstars)]]
    msata_dict['reference_star_mag'] = [[-999 for _ in range(num_refstars)]]
    msata_dict['convergence_status'] = [['SUCCESS' for _ in range(num_refstars)]]
    msata_dict['reference_star_number'] = [[i for i in range(num_refstars)]]
    msata_dict['lsf_removed_status'] = [['-999' for i in range(num_refstars)]]
    msata_dict['lsf_removed_reason'] = [['-999' for i in range(num_refstars)]]
    msata_dict['lsf_removed_x'] = [[-999.0 for _ in range(num_refstars)]]
    msata_dict['lsf_removed_y'] = [[-999.0 for _ in range(num_refstars)]]
    msata_dict['planned_v2'] = [[-999.0 for _ in range(num_refstars)]]
    msata_dict['planned_v3'] = [[-999.0 for _ in range(num_refstars)]]
    # create the additional arrays
    number_status, time_arr, status_colors = [], [], []
    for tas, do_str in zip(msata_dict['ta_status'], msata_dict['date_obs']):
        if tas.lower() == 'unsuccessful':
            number_status.append(0.0)
            status_colors.append('red')
        elif 'progress' in tas.lower():
            number_status.append(0.5)
            status_colors.append('gray')
        else:
            number_status.append(1.0)
            status_colors.append('blue')
        # convert time string into an array of time (this is in UT with 0.0 milliseconds)
        t = datetime.fromisoformat(do_str)
        time_arr.append(t)
    # add these to the bokeh data structure
    msata_dict['time_arr'] = time_arr
    msata_dict['number_status'] = number_status
    msata_dict['status_colors'] = status_colors
    # crate the dataframe
    msata_data = pd.DataFrame(msata_dict)
    return msata_data


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_mast_query_ta():
    """Test the ``query_mast`` function"""

    query_start = 59833.0
    query_end = 59844.6

    result = monitor_utils.mast_query_ta('nirspec', 'NRS_FULL_MSA', query_start, query_end)

    assert len(result) == 4


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_most_recent_search():
    """Test the ``most_recent_search`` function"""

    ta = MSATA()
    ta.aperture = 'NRS_FULL_MSA'
    ta.query_table = NIRSpecTAQueryHistory

    result = ta.most_recent_search()

    assert isinstance(result, float)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_status():
    """Test the ``plt_status`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_status()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_residual_offsets():
    """Test the ``plt_residual_offsets`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_residual_offsets()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_v2offset_time():
    """Test the ``plt_v2offset_time`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_v2offset_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_v3offset_time():
    """Test the ``plt_v3offset_time`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_v3offset_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_lsv2v3offsetsigma():
    """Test the ``plt_lsv2v3offsetsigma`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_lsv2v3offsetsigma()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_res_offsets_corrected():
    """Test the ``plt_res_offsets_corrected`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_res_offsets_corrected()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_v2offsigma_time():
    """Test the ``plt_v2offsigma_time`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_v2offsigma_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_v3offsigma_time():
    """Test the ``plt_v3offsigma_time`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_v3offsigma_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_roll_offset():
    """Test the ``plt_roll_offset`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_roll_offset()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_lsoffsetmag():
    """Test the ``plt_lsoffsetmag`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_lsoffsetmag()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_tot_number_of_stars():
    """Test the ``plt_tot_number_of_stars`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_tot_number_of_stars()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_plt_mags_time():
    """Test the ``plt_mags_time`` function"""

    ta = MSATA()
    msata_data = define_testdata()
    # create the additional data
    colors_list, tot_number_of_stars = [], []
    color_dict, visit_id = {}, msata_data['visit_id']
    for i, _ in enumerate(visit_id):
        tot_stars = len(msata_data['reference_star_number'][i])
        tot_number_of_stars.append(tot_stars)
        ci = '#%06X' % randint(0, 0xFFFFFF)
        if visit_id[i] not in color_dict:
            color_dict[visit_id[i]] = ci
        colors_list.append(color_dict[visit_id[i]])
    # add these to the bokeh data structure
    msata_data['tot_number_of_stars'] = tot_number_of_stars
    msata_data['colors_list'] = colors_list
    ta.source = ColumnDataSource(data=msata_data)
    result = ta.plt_mags_time()

    assert bokeh_plot_type == type(result)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_mk_plt_layout(tmp_path):
    """Test the ``mk_plt_layout`` function"""

    truth_script, truth_div = components(figure())

    ta = MSATA()
    #ta.output_dir = os.path.join(get_config()['outputs'], 'msata_monitor/tests')
    ta.output_dir = str(tmp_path)
    ensure_dir_exists(ta.output_dir)
    ta.output_file_name = os.path.join(ta.output_dir, "msata_layout.html")
    ta.msata_data = define_testdata()
    script, div = ta.mk_plt_layout()

    assert type(truth_script) == type(script)
    assert type(truth_div) == type(div)
