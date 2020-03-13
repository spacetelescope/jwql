"""dashboard.py

    The module imports all prepares plot functions from .plots and combines
    prebuilt tabs to a dashboard. Furthermore it defines the timerange for
    the visualisation. Default time_range should be set to about 4 Month (120days)

Authors
-------

    - [AIRBUS] Daniel Kübacher
    - [AIRBUS] Leo Stumpf

Use
---
    -

Dependencies
------------

    The file miri_database.db in the directory jwql/jwql/database/ must be populated.

References
----------
    The code was developed in reference to the information provided in:
    ‘MIRI trend requestsDRAFT1900301.docx’

Notes
-----

    For further information please contact Brian O'Sullivan
"""
import os

import datetime
from bokeh.embed import components
from bokeh.models.widgets import Tabs

import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from .plots.bias_tab import bias_plots
from .plots.fpe_voltage_tab import fpe_plots
from .plots.ice_voltage_tab import volt_plots
from .plots.power_tab import power_plots
from .plots.temperature_tab import temperature_plots
from .plots.wheel_ratio_tab import wheel_ratios


def data_trending_dashboard(start=datetime.date(2017, 8, 15).isoformat(), end=datetime.datetime.now()):
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

    # Connect to database
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    package_dir = __location__.split('instrument_monitors')[0]
    database_location = os.path.join(package_dir, 'database')
    database_file = os.path.join(database_location, 'miri_database.db')
    conn = sql.create_connection(database_file)

    # add tabs to dashboard
    tab1 = power_plots(conn, start, end)
    tab2 = volt_plots(conn, start, end)
    tab3 = fpe_plots(conn, start, end)
    tab4 = temperature_plots(conn, start, end)
    tab5 = bias_plots(conn, start, end)
    tab6 = wheel_ratios(conn, start, end)

    # build dashboard
    tabs = Tabs(tabs=[tab1, tab2, tab3, tab5, tab4, tab6])

    # return dashboard to web app
    script, div = components(tabs)
    plot_data = [div, script]

    # close sql connection
    sql.close_connection(conn)

    return plot_data
