#! /usr/bin/env python
''' Main module for nirspec datatrending -> fills database

    This module holds functions to connect with the engineering database in order
    to grab and process data for the specific miri database. The scrips queries
    a daily 15 min chunk and a whole day dataset. These contain several mnemonics
    defined in ''mnemonics.py''. The queried data gets processed and stored in
    a prepared database.

Authors
-------

    - Daniel Kühbacher

Use
---

Dependencies
------------

References
----------

Notes
-----
'''
import utils.mnemonics as mn
import utils.sql_interface as sql
from utils.process_data import whole_day_routine, wheelpos_routine
from jwql.utils.engineering_database import query_single_mnemonic

import pandas as pd
import numpy as np
import statistics
import sqlite3

from astropy.time import Time


def process_daysample(conn, m_raw_data):
    '''Parse CSV file, process data within and put to DB
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    #process raw data with once a day routine
    return_data, lamp_data = whole_day_routine(m_raw_data)
    FW, GWX, GWY = wheelpos_routine(m_raw_data)

    #put all data to a database that uses a condition
    for key, value in return_data.items():
        m = m_raw_data.mnemonic(key)
        length = len(value)
        mean = statistics.mean(value)
        deviation = statistics.stdev(value)
        dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
        sql.add_data(conn, key, dataset)


    #add rest of the data to database -> no conditions applied
    for identifier in mn.mnemSet_day:
        m = m_raw_data.mnemonic(identifier)
        temp = []
        #look for all values that fit to the given conditions
        for element in m:
            temp.append(float(element['value']))
        #return None if no applicable data was found
        if len(temp) > 2:
            length = len(temp)
            mean = statistics.mean(temp)
            deviation = statistics.stdev(temp)
        else:
            print('No data for {}'.format(identifier))
        del temp

    #add lamp data to database -> distiction over lamps
    for key, values in lamp_data.items():
        for data in values:
            dataset_volt = (data[0], data[1], data[5], data[6], data[7])
            dataset_curr = (data[0], data[1], data[2], data[3], data[4])
            sql.add_data(conn, 'LAMP_{}_VOLT'.format(key), dataset_volt)
            sql.add_data(conn, 'LAMP_{}_CURR'.format(key), dataset_curr)


    #add wheeldata to database
    for key, values in FW.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_FWA_POSITION_{}'.format(key), data)

    for key, values in GWX.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_GWA_X_POSITION_{}'.format(key), data)

    for key, values in GWY.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_GWA_Y_POSITION_{}'.format(key), data)


def process_15minsample(conn, m_raw_data):
    '''Parse CSV file, process data within and put to DB
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    #process raw data with once a day routine
    returndata = once_a_day_routine(m_raw_data)

    #put all data in a database that uses a condition
    for key, value in returndata.items():
        m = m_raw_data.mnemonic(key)
        length = len(value)
        mean = statistics.mean(value)
        deviation = statistics.stdev(value)
        dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
        sql.add_data(conn, key, dataset)

    #add rest of the data to database
    for identifier in mn.mnemSet_15min:

        m = m_raw_data.mnemonic(identifier)

        temp = []

        #look for all values that fit to the given conditions
        for element in m:
            temp.append(float(element['value']))

        #return None if no applicable data was found
        if len(temp) > 2:
            length = len(temp)
            mean = statistics.mean(temp)
            deviation = statistics.stdev(temp)

            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, identifier, dataset)
        elif len(temp) == 2:
            dataset = (float(element['time']), float(element['time']), 1, temp[0], 0)
            sql.add_data(conn, identifier, dataset)
        else:
            print('No data for {}'.format(identifier))
            print(temp)

        del temp

def main():

    '''
    from ..utils.engineering_database import query_single_mnemonic

    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')


    mnemonic = query_single_mnemonic(mnemonic_identifier, start_time, end_time)
    assert len(mnemonic.data) == mnemonic.meta['paging']['rows']
    '''


    for mnemonic in mn.mnemonic_set_15min:
        whole_day.update(mnemonic = query_single_mnemonic(mnemonic, start, end))


    #configure start and end time for query
    #
    #
    #
    #

    #query table start and end from engineering_database
    #
    #
    #
    #
    #return table_day, table_15min
    #generate paths
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'nirspec_database.db')

    #connect to temporary database
    conn = sql.create_connection(DATABASE_FILE)

    process_daysample(conn, table_day)
    process_15minsample(conn, table_15min)

    #close connection
    sql.close_connection(conn)
    print("done")
