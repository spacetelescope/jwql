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
    make sure "directory" points to a folder where useable day-samples are stored.
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
from jwql.instrument_monitors.miri_monitors.data_trending.utils.process_data import whole_day_routine, wheelpos_routine
from jwql.utils.utils import get_config, filename_parser

import os
import glob
import statistics
import sqlite3

#set _location_ variable
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

#files with data to initially fill the database
directory = os.path.join(get_config()['outputs'], 'miri_data_trending', 'trainings_data_day', '*.CSV')
paths = glob.glob(directory)


def process_file(conn, path):
    '''Parse CSV file, process data within and put to DB

    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines file to read
    '''

    m_raw_data = apt.mnemonics(path)

    cond3, FW_volt, GW14_volt, GW23_volt, CCC_volt = whole_day_routine(m_raw_data)
    FW, GW14, GW23, CCC= wheelpos_routine(m_raw_data)

    #put data from con3 to database
    for key, value in cond3.items():

        m = m_raw_data.mnemonic(key)

        if value != None:
            if len(value) > 2:
                if key == "SE_ZIMIRICEA":
                    length = len(value)
                    mean = statistics.mean(value)
                    deviation = statistics.stdev(value)
                    dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
                    sql.add_data(conn, "SE_ZIMIRICEA_HV_ON", dataset)

                elif key == "IMIR_HK_ICE_SEC_VOLT4":
                    length = len(value)
                    mean = statistics.mean(value)
                    deviation = statistics.stdev(value)
                    dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
                    sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_HV_ON", dataset)

                else:
                    length = len(value)
                    mean = statistics.mean(value)
                    deviation = statistics.stdev(value)
                    dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
                    sql.add_data(conn, key, dataset)


    #########################################################################################
    for pos in mn.fw_positions:
        try:
            data = FW[pos]
            for element in data:
                sql.add_wheel_data(conn, 'IMIR_HK_FW_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass

    for pos in mn.gw_positions:
        try:
            data_GW14 = GW14[pos]
            data_GW23 = GW23[pos]

            for element in data_GW14:
                sql.add_wheel_data(conn, 'IMIR_HK_GW14_POS_RATIO_{}'.format(pos), element)
            for element in data_GW23:
                sql.add_wheel_data(conn, 'IMIR_HK_GW23_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass

    for pos in mn.ccc_positions:
        try:
            data = CCC[pos]
            for element in data:
                sql.add_wheel_data(conn, 'IMIR_HK_CCC_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass


def main():
    #point to database
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'miri_database.db')

    #connect to temporary database
    conn = sql.create_connection(DATABASE_FILE)

    #process all files found ind folder "directory"
    for path in paths:
        process_file(conn, path)

    sql.close_connection(conn)
    print("done")

if __name__ == "__main__":
    main()
