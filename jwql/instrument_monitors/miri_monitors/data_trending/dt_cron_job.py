#! /usr/bin/env python
''' Main module for miri datatrending -> fills database

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
import .utils.mnemonics as mn
import .utils.sql_interface as sql
from .utils.process_data import whole_day_routine, wheelpos_routine
from jwql.utils.engineering_database import query_single_mnemonic

import pandas as pd
import numpy as np
import statistics
import sqlite3

from astropy.time import Time

def add_day_to_db(conn, m_raw_data):
    '''Process 'one_day' data and add to miri_database
    Parameters
    ----------
    conn : DBobject
        connection object to specific database
    m_raw_data : dict
        holds astropy table of data with corresponding mnemonic as key
    '''

    #process data with predefined routines
    cond3, FW_volt, GW14_volt, GW23_volt, CCC_volt = whole_day_routine(m_raw_data)
    FW, GW14, GW23, CCC= wheelpos_routine(m_raw_data)

    #put data from con3 to database
    for key, value in cond3.items():

        #abbreviate astropy table of dict(key)
        m = m_raw_data.mnemonic(key)

        #Add data to database
        #######################################################################
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


    m = m_raw_data.mnemonic('IMIR_HK_FW_POS_VOLT')
    if FW_volt != None:
        if len(FW_volt) > 2:
            length = len(FW_volt)
            mean = statistics.mean(FW_volt)
            deviation = statistics.stdev(FW_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_FW_POS_VOLT", dataset)

    m = m_raw_data.mnemonic('IMIR_HK_GW14_POS_VOLT')
    if GW14_volt != None:
        if len(GW14_volt) > 2:
            length = len(GW14_volt)
            mean = statistics.mean(GW14_volt)
            deviation = statistics.stdev(GW14_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_GW14_POS_VOLT", dataset)

    m = m_raw_data.mnemonic('IMIR_HK_GW23_POS_VOLT')
    if GW23_volt != None:
        if len(GW23_volt) > 2:
            length = len(GW23_volt)
            mean = statistics.mean(GW23_volt)
            deviation = statistics.stdev(GW23_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_GW23_POS_VOLT", dataset)

    m = m_raw_data.mnemonic('IMIR_HK_CCC_POS_VOLT')
    if CCC_volt != None:
        if len(CCC_volt) > 2:
            length = len(CCC_volt)
            mean = statistics.mean(CCC_volt)
            deviation = statistics.stdev(CCC_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_CCC_POS_VOLT", dataset)

    #Add wheelposition data to database
    ###########################################################################
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
            data_GW23 = GW14[pos]

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


def add_15min_to_db(conn, m_raw_data):
    '''Process '15min' data and add to miri_database
    Parameters
    ----------
    conn : DBobject
        connection object to specific database
    m_raw_data : dict
        holds astropy table of data with corresponding mnemonic as key
    '''

    #process data
    cond1, cond2 = once_a_day_routine(m_raw_data)

    #Add data to database
    ############################################################################
    for key, value in cond1.items():

        #abbreviate astropy table of dict(key)
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

    for key, value in cond2.items():
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
        whole_day.update(mnemonic=query_single_mnemonic(mnemonic, start, end))


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
    db_file = "/home/daniel/STScI/jwql/jwql/database/miri_database_new.db"
    conn = sql.create_connection(db_file)

    add_day_to_db(conn, table_day)
    add_15min_to_db(conn, table_15min)

    sql.close_connection(conn)
