import statistics
import os
import glob
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.csv_to_AstropyTable as apt
from jwql.utils.utils import get_config, filename_parser

from astropy.table import Table, Column

from jwql.instrument_monitors.nirspec_monitors.data_trending.utils.process_data import wheelpos_routine

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

#point to the directory where your files are located!
directory = os.path.join(get_config()['outputs'], 'nirspec_data_trending', 'nirspec_wheels', '*.CSV')

#here some some files contain the same data but they are all incomplete
#in order to generate a full database we have to import all of them
filenames = glob.glob(directory)

def process_file(conn, path):

    #import mnemonic data and append dict to variable below
    m_raw_data = apt.mnemonics(path)

    #process raw data with once a day routine
    FW, GWX, GWY = wheelpos_routine(m_raw_data)

    for key, values in FW.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_FWA_POSITION_{}'.format(key), data)

    for key, values in GWX.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_GWA_X_POSITION_{}'.format(key), data)

    for key, values in GWY.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_GWA_Y_POSITION_{}'.format(key), data)

def main():
    #generate paths
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'nirspec_database.db')

    #connect to temporary database
    conn = sql.create_connection(DATABASE_FILE)

    '''
    path = directory + test
    process_file(conn, path)
    '''
    #do for every file in list above
    for path in filenames:
        process_file(conn, path)

    #close connection
    sql.close_connection(conn)
    print("done")

if __name__ == "__main__":
    main()
