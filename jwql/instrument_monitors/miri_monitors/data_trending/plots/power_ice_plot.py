import sql_interface as sql
from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation
import plot_functions

import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.utils import check_random_state
from sklearn import metrics

from astropy.time import Time



def plot_power_ice(conn, filename):

    #query data from database
    columns = ('start_time, average, deviation')
    curr_idle = sql.query_data(conn, 'SE_ZIMIRICEA_IDLE', columns)
    curr_hv = sql.query_data(conn, 'SE_ZIMIRICEA_HV_ON', columns)

    voltage = 30

    #append data from query to numpy arrays
    curr_idle_time, curr_idle_val = split_data(curr_idle)
    power_idle = curr_idle_val * voltage

    curr_hv_time, curr_hv_val = split_data(curr_hv)
    power_hv = curr_hv_val * voltage

    power_hv_reg = pol_regression(curr_hv_time, power_hv, 3)
    power_idle_reg = pol_regression(curr_idle_time, power_idle, 3)

    # output to static HTML file
    output_file("lines.html")

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,box_zoom,reset,save",                  \
                title = "POWER ICE",                                \
                y_range = [0,16],                                   \
                x_axis_label = 'DOY (mjd)', y_axis_label='Power (W)')

    p.background_fill_color = "#efefef"
    p.xgrid.grid_line_color = None

    # add a line renderer with legend and line thickness
    p.scatter(curr_idle_time, power_idle, color = 'red', legend = "Power idle")
    p.scatter(curr_hv_time, power_hv, color = 'orange', legend = "Power HV on ")

    p.line(curr_hv_time, power_hv_reg , color = 'green')
    p.line(curr_idle_time, power_idle_reg, color = 'blue')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    show(p)

def main():

    db_file = "miri_database.db"
    conn = sql.create_connection(db_file)

    plot_power_ice(conn, "power_ice.html")

    sql.close_connection(conn)
    print('end')

#run main programm
if __name__ == "__main__":
    main()
