#! /usr/bin/env python
"""Combines plots to tabs and prepares dashboard

The module imports all prepared plot functions from .plots and combines
prebuilt tabs to a dashboard. Furthermore it defines the timerange for
the visualisation. Default ``time_range`` should be set to about 4
months (120 days)

Authors
-------

    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``data_container.py``, e.g.:

    ::
        from jwql.instrument_monitors.miri_monitors.data_trending.dashboard as dash
        dashboard, variables = dash.data_trending_dashboard(start_time, end_time)

Dependencies
------------
    User must provide ``miri_database.db`` in folder ``jwql/database/``

"""

import datetime
import os

from bokeh.embed import components
from bokeh.models.widgets import Tabs

import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from jwql.utils.utils import get_config

from .plots.power_tab import power_plots
from .plots.ice_voltage_tab import volt_plots
from .plots.fpe_voltage_tab import fpe_plots
from .plots.temperature_tab import temperature_plots
from .plots.bias_tab import bias_plots
from .plots.wheel_ratio_tab import wheel_ratios

# Configure actual datetime in order to implement range function
NOW = datetime.datetime.now()
DEFAULT_START = datetime.date(2017, 8, 15).isoformat()

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
PACKAGE_DIR = __location__.split('instrument_monitors')[0]


def data_trending_dashboard(start=DEFAULT_START, end=NOW):
    """Build the MIRI data tending dashboard

    Parameters
    ----------
    start : string
        The start time for query and visualisation
    end : string
        The end time for query and visualisation

    Returns
    -------
    dashboard_components : list
        A list containing the JavaScript and HTML content for the dashboard
    """

    # Connect to database
    database_location = os.path.join(PACKAGE_DIR, 'database')
    database_file = os.path.join(database_location, 'miri_database.db')

    conn = sql.create_connection(database_file)

    # Add tabs to dashboard
    tab1 = power_plots(conn, start, end)
    tab2 = volt_plots(conn, start, end)
    tab3 = fpe_plots(conn, start, end)
    tab4 = temperature_plots(conn, start, end)
    tab5 = bias_plots(conn, start, end)
    tab6 = wheel_ratios(conn, start, end)

    # Build dashboard
    tabs = Tabs(tabs=[tab1, tab2, tab3, tab5, tab4, tab6])

    # Return dashboard to web app
    script, div = components(tabs)
    dashboard_components = [div, script]

    # Close sql connection
    sql.close_connection(conn)

    return dashboard_components
