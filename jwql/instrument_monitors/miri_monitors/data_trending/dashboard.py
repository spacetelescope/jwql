#! /usr/bin/env python
"""Combines plots to tabs and prepares dashboard

The module imports all prepares plot functions from .plots and combines
prebuilt tabs to a dashboard. Furthermore it defines the timerange for
the visualisation. Default time_range should be set to about 4 Month (120days)

Authors
-------
    - Daniel Kühbacher

Use
---
    The functions within this module are intended to be imported and
    used by ``data_container.py``, e.g.:

    ::
        import jwql.instrument_monitors.miri_monitors.data_trending.dashboard as dash
        dashboard, variables = dash.data_trending_dashboard(start_time, end_time)

Dependencies
------------
    User must provide "miri_database.db" in folder jwql/database

"""
import datetime
import os

from bokeh.embed import components
from bokeh.models.widgets import Tabs

#import plot functions
from .plots.power_tab import power_plots
from .plots.ice_voltage_tab import volt_plots
from .plots.fpe_voltage_tab import fpe_plots
from .plots.temperature_tab import temperature_plots
from .plots.bias_tab import bias_plots
from .plots.wheel_ratio_tab import wheel_ratios
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from jwql.utils.utils import get_config


#configure actual datetime in order to implement range function
now = datetime.datetime.now()
#default_start = now - datetime.timedelta(1000)
default_start = datetime.date(2017, 8, 15).isoformat()

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
PACKAGE_DIR = __location__.split('instrument_monitors')[0]

def data_trending_dashboard(start = default_start, end = now):
    """Builds dashboard
    Parameters
    ----------
    start : time
        configures start time for query and visualisation
    end : time
        configures end time for query and visualisation
    Return
    ------
    plot_data : list
        A list containing the JavaScript and HTML content for the dashboard
    variables : dict
        no use
    """

    #connect to database
    # DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_LOCATION = os.path.join(PACKAGE_DIR, 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'miri_database.db')

    conn = sql.create_connection(DATABASE_FILE)

    #some variables can be passed to the template via following
    variables = dict(init = 1)

    #some variables can be passed to the template via following
    variables = dict(init = 1)

    #add tabs to dashboard
    tab1 = power_plots(conn, start, end)
    tab2 = volt_plots(conn, start, end)
    tab3 = fpe_plots(conn, start, end)
    tab4 = temperature_plots(conn, start, end)
    tab5 = bias_plots(conn, start, end)
    tab6 = wheel_ratios(conn, start, end)

    #build dashboard
    tabs = Tabs( tabs=[ tab1, tab2, tab3, tab5, tab4, tab6 ] )

    #return dashboard to web app
    script, div = components(tabs)
    plot_data = [div, script]

    #close sql connection
    sql.close_connection(conn)

    return plot_data, variables
