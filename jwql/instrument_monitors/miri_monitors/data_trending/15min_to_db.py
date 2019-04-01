#! /usr/bin/env python
''' Auxiliary module to populate database

    This module was used throughout development to populate the database. Since
    the EDB had no valid data during implementation we had to download data elsewhere.
    The downloaded data is in .CSV format and can easily be read by the program.
    After import and sorting the process_file function extracts the useful part and
    pushes it to the auxiliary database. This function can be implemented in the
    final cron job.

Authors
-------

    - Daniel Kühbacher

Use
---
    make sure "directory" points to a folder where useable 15min-samples are storedself.
    make sure you already ran .utils/sql_interface.py in order to create a empty database
    with prepared tables.
    Run the module form the command line.

Notes
-----
    For developement only
'''

import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.utils.csv_to_AstropyTable as apt
from jwql.instrument_monitors.miri_monitors.data_trending.utils.process_data import once_a_day_routine
from jwql.utils.utils import get_config, filename_parser

import statistics
import os
import glob

#set _location_ variable
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

#point to the directory where your files are located!
directory = os.path.join(get_config()['outputs'], 'miri_data_trending', 'trainings_data_15min', '*.CSV')
paths = glob.glob(directory)

def process_file(conn, path):
    '''Parse CSV file, process data within and put to DB

    Parameters
    ----------
    conn : DBobject
        Connection object to auxiliary database
    path : str
        defines file to read
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

    #process every csv file in directory folder
    for path in paths:
        process_file(conn, path)

    #close connection
    sql.close_connection(conn)
    print("done")

if __name__ == "__main__":
    main()
