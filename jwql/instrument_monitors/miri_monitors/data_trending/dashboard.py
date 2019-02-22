'''module holds and delivers all plots contibuted to data_trending

'''
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql

from bokeh.embed import components
from bokeh.models.widgets import Tabs

import datetime
from astropy.time import Time
from datetime import date

#import plot functions
from .plots.power_tab import power_plots
from .plots.ice_voltage_tab import volt_plots
from .plots.fpe_voltage_tab import fpe_plots
from .plots.temperature_tab import temperature_plots
from .plots.bias_tab import bias_plots
#from .plots.overview_tab import overview_settings
from .plots.wheel_ratio_tab import wheel_ratios

#configure actual datetime in order to implement range function
now = datetime.datetime.now()
#default_start = now - datetime.timedelta(1000)
default_start = datetime.date(2017, 8, 25).isoformat()

def data_trending_dashboard(start = default_start, end = now):

    #connect to database
    db_file = "/home/daniel/STScI/jwql/jwql/database/miri_database.db"
    conn = sql.create_connection(db_file)

    #some variables can be passed to the template via following
    variables = dict(init=10)

    #add tabs to dashboard
    #tab0 = overview_settings(conn)
    tab1 = power_plots(conn, start, end)
    tab2 = volt_plots(conn, start, end)
    tab3 = fpe_plots(conn, start, end)
    tab4 = temperature_plots(conn, start, end)
    tab5 = bias_plots(conn, start, end)
    tab6 = wheel_ratios(conn, start, end)

    #build dashboard
    tabs = Tabs( tabs=[ tab1, tab2, tab3, tab5, tab4, tab6 ] )

    #return dasboard to webapp
    script, div = components(tabs)
    plot_data = [div, script]

    #close sql connection
    sql.close_connection(conn)

    return plot_data, variables
