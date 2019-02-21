'''module holds and delivers all plots contibuted to data_trending

'''
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql

from sklearn.linear_model import LinearRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.utils import check_random_state
from sklearn import metrics

from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation
from bokeh.embed import components
from bokeh.layouts import column, row, WidgetBox
from bokeh.models import Panel
from bokeh.models.widgets import Tabs

from astropy.time import Time

#import plot functionsS



def data_trending_dashboard():

    from .plots.power_tab import power_plots
    from .plots.voltage_tab import volt_plots
    from .plots.temperature_tab import temperature_plots

    #connect to database
    db_file = "/home/daniel/STScI/jwql/jwql/database/miri_database.db"
    conn = sql.create_connection(db_file)

    #add tabs to dashboard
    tab1 = power_plots(conn)
    tab2 = volt_plots(conn)
    tab3 = temperature_plots(conn)

    #connect tabs
    tabs = Tabs( tabs=[ tab1, tab2, tab3 ] )

    #return dasboard to webapp
    script, div = components(tabs)
    plot_data = [div, script]
    sql.close_connection(conn)
    return plot_data
