import sql_interface as sql
from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation
import plot_functions as pf

import numpy as np

from astropy.time import Time

def plot_volt1_3(conn, filename):

    #query data from database
    columns = ('start_time, average, deviation')
    volt1 = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT1', columns)
    volt2 = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT2', columns)
    volt3 = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT3', columns)

    #append data from query to numpy arrays
    volt1_time, volt1_val = pf.split_data(volt1)
    volt2_time, volt2_val = pf.split_data(volt2)
    volt3_time, volt3_val = pf.split_data(volt3)

    volt1_reg = pf.pol_regression(volt1_time, volt1_val, 3)
    volt2_reg = pf.pol_regression(volt2_time, volt2_val, 3)
    volt3_reg = pf.pol_regression(volt3_time, volt3_val, 3)

    # output to static HTML file
    output_file("volt1-3.html")

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,box_zoom,reset,save",                  \
                title = "IMIR_HK_ICE_SEC_VOLT 1 - 3",               \
                x_axis_label = 'DOY (mjd)', y_axis_label='Power (W)')

    p.background_fill_color = "#efefef"
    p.xgrid.grid_line_color = None

    # add a line renderer with legend and line thickness
    p.scatter(volt1_time, volt1_val, color = 'red', legend = "Volt 1")
    p.scatter(volt2_time, volt2_val, color = 'orange', legend = "Volt 2")
    p.scatter(volt3_time, volt3_val, color = 'purple', legend = "Volt 3")

    p.line(volt1_time, volt1_reg, color = 'green')
    p.line(volt2_time, volt2_reg, color = 'green')
    p.line(volt3_time, volt3_reg, color = 'green')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    show(p)

def main():

    db_file = "miri_database.db"
    conn = sql.create_connection(db_file)

    plot_volt1_3(conn, "power_ice.html")

    sql.close_connection(conn)
    print('end')

#run main programm
if __name__ == "__main__":
    main()
