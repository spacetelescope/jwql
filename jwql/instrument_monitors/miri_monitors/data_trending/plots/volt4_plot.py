
import jwql.instrument_monitors.miri_monitors.data_trending.sql_interface as sql
from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation

import plot_functions as pf
import numpy as np

from astropy.time import Time


def plot_volt4(conn, filename):

    #query data from database
    columns = ('start_time, average, deviation')
    volt4_idle = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT4_IDLE', columns)
    volt4_hv = sql.query_data(conn, 'IMIR_HK_ICE_SEC_VOLT4_HV_ON', columns)
    voltage = 30
    #append data from query to numpy arrays

    volt4_idle_time, volt4_idle_val = pf.split_data(volt4_idle)
    volt4_hv_time, volt4_hv_val = pf.split_data(volt4_hv)

    volt4_hv_reg = pf.pol_regression(volt4_hv_time, volt4_hv_val, 3)
    volt4_idle_reg = pf.pol_regression(volt4_idle_time, volt4_idle_val, 3)

    # output to static HTML file
    output_file(filename)

    # create a new plot with a title and axis labels
    p = figure( tools = "pan,box_zoom,reset,save",                  \
                title = "IMIR_HK_ICE_SEC_VOLT4",                                   \
                y_range = [4,5],
                x_axis_label = 'DOY (mjd)', y_axis_label= 'Voltage (V)')

    p.background_fill_color = "#efefef"
    p.xgrid.grid_line_color = None

    # add a line renderer with legend and line thickness
    p.scatter(volt4_idle_time, volt4_idle_val, color = 'red', legend = "Power idle")
    p.scatter(volt4_hv_time, volt4_hv_val, color = 'orange', legend = "Power HV on ")

    p.line(volt4_hv_time, volt4_hv_reg , color = 'green')
    p.line(volt4_idle_time, volt4_idle_reg, color = 'blue')

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"

    show(p)

def main():

    db_file = "miri_database.db"
    conn = sql.create_connection(db_file)

    plot_volt4(conn, "output/volt4.html")

    sql.close_connection(conn)
    print('end')

#run main programm
if __name__ == "__main__":
    main()
