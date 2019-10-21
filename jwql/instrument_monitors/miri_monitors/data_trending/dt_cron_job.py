#! /usr/bin/env python
''' Cron Job for miri datatrending -> populates database

    This module holds functions to connect with the engineering database in order
    to grab and process data for the specific miri database. The scrips queries
    a daily 15 min chunk and a whole day dataset. These contain several mnemonics
    defined in ''mnemonics.py''. The queried data gets processed and stored in
    an auxiliary database.

Authors
-------
    - Daniel Kühbacher

Dependencies
------------
    For further information please contact Brian O'Sullivan

References
----------

'''
import utils.mnemonics as mn
import utils.sql_interface as sql
from utils.process_data import whole_day_routine, wheelpos_routine
from jwql.utils.engineering_database import query_single_mnemonic

import pandas as pd
import numpy as np
import statistics
import sqlite3
import os

from astropy.time import Time

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
PACKAGE_DIR = __location__.split('instrument_monitors')[0]


def process_day_sample(conn, m_raw_data):
    '''Parse CSV file, process data within and put to DB
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
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


def process_15min_sample(conn, m_raw_data):
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

    from ..utils.engineering_database import query_single_mnemonic

    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')


    mnemonic = query_single_mnemonic(mnemonic_identifier, start_time, end_time)
    assert len(mnemonic.data) == mnemonic.meta['paging']['rows']



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

    #open temporary database and write data!
    DATABASE_LOCATION = os.path.join(PACKAGE_DIR, 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'miri_database.db')

    conn = sql.create_connection(DATABASE_FILE)

    process_day_sample(conn, table_day)
    process_15process_15min_sample(conn, table_15min)

    sql.close_connection(conn)
