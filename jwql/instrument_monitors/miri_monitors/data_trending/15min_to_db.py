import statistics
import os
import glob
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.utils.csv_to_AstropyTable as apt
from jwql.utils.utils import get_config, filename_parser

from jwql.instrument_monitors.miri_monitors.data_trending.utils.process_data import once_a_day_routine

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

#point to the directory where your files are located!
directory = '/home/daniel/STScI/trainigData/set_15_min/'

paths = glob.glob(os.path.join(directory, '*.CSV'))

def process_file(conn, path):
    '''Parse CSV file, process data within and put to DB
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    #import mnemonic data and append dict to variable below
    m_raw_data = apt.mnemonics(path)

    #process raw data with once a day routine
    processed_data = once_a_day_routine(m_raw_data)

    #push extracted and filtered data to temporary database
    for key, value in processed_data.items():

        #abbreviate data table
        m = m_raw_data.mnemonic(key)

        if key == "SE_ZIMIRICEA":
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "SE_ZIMIRICEA_IDLE", dataset)

        elif key == "IMIR_HK_ICE_SEC_VOLT4":
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_IDLE", dataset)

        else:
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, key, dataset)

def main():
    #generate paths
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'miri_database.db')

    #connect to temporary database
    conn = sql.create_connection(DATABASE_FILE)

    #do for every file in list above
    for path in paths:
        process_file(conn, path)

    #close connection
    sql.close_connection(conn)
    print("done")

if __name__ == "__main__":
    main()
