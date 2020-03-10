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
import netrc
import statistics
import os
import sys
import datetime
import warnings

import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.edb.engineering_database as edb

from astropy.time import Time
from jwql.utils.utils import get_config
from time import sleep
from multiprocessing import Process
from datetime import datetime as DateTime
from datetime import date
from astropy.table import Table
from jwql.instrument_monitors.miri_monitors.data_trending.utils.process_data import once_a_day_routine

host = 'mast'


class NullWriter(object):
    def write(self, arg):
        pass

def frange(start, stop, step):
    i = start
    while i<stop:
        yield i
        i+= step

def process_15min(conn, m_raw_data):
    '''Parse CSV file, process data within and put to DB

    Parameters
    ----------
    conn : DBobject
        Connection object to auxiliary database
    path : str
        defines file to read
    '''

    #import mnemonic data and append dict to variable below
    #m_raw_data = mnemonic_dict

    #process raw data with once a day routine

    print("*************************************************************")
    print("* process data 15 min")
    print("*************************************************************")


    processed_data = once_a_day_routine(m_raw_data)

    print("*************************************************************")
    print("* SQL data 15 min")
    print("*************************************************************")

    #push extracted and filtered data to temporary database
    for key, value in processed_data.items():

        #abbreviate data table
        m = m_raw_data[key]

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

def querry_data(mnemonic_name, start_time, end_time, mast_token):
    try:
        # set text and color
        status = 'Succes'
        color = '\033[0m'  # color black (standard)

        # get data
        data, meta, info = edb.query_single_mnemonic(mnemonic_name, start_time, end_time, token=mast_token)

        if data == None:
            data = Table(names=('MJD', 'euvalue', 'sqldataType', 'theTime'), dtype=('f8', 'f8', 'U4', 'U21'))
            status = 'Failure No data'
            color = '\33[31m'  # color red
            # raise Exception('No data')

        data['time_iso'] = Time(data['MJD'], format='mjd').iso
        del data['theTime']

        # data.show_in_browser(jsviewer=True)
        value = data['euvalue']
        time = data['MJD']

        description = ('time', 'value')
        data = [time, value]

        # add some meta data
        if len(time) > 0:
            date_start = time[0]
            date_end = time[len(time) - 1]
            info = {'start': date_start, 'end': date_end}
        else:
            info = {"n": "n"}

        # add name of mnemonic to meta data of list
        info['mnemonic'] = mnemonic_name
        info['len'] = len(time)

        # table to return
        mnemonic_table = Table(data, names=description, dtype=('f8', 'str'), meta=info)

    except:
        # set text and color
        status = 'Failure ' + str(sys.exc_info()[1])
        color = '\33[31m'  # color red

    print_string = DateTime.now().isoformat() + ' Querry 15min: ' + mnemonic_name + '\t' + status
    print_string = color + print_string + '\033[0m'
    print(print_string)

    return mnemonic_name, mnemonic_table


def main():
    max_time=90
    step_time=0.5

    #get date
    today = date.today()
    day = today - datetime.timedelta(days=10)
    day = day.strftime("%Y-%m-%d")

    #connect database
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'miri_database.db')
    conn = sql.create_connection(DATABASE_FILE)

    #define token
    secrets = netrc.netrc()
    mast_token = secrets.authenticators(host)[2]

    day='2019-10-15'
    day='2019-12-10'

    #define time
    start_time = Time(day+' 12:00:00.000', format='iso')
    end_time =   Time(day+' 12:15:00.000', format='iso')

    #define time
    start_time = Time(day+' 00:00:00.001', format='iso')
    end_time =   Time(day+' 23:59:59.000', format='iso')


    #querry data 15 min STARTED
    print("*************************************************************")
    print("* querry data 15 min")
    print("*************************************************************")

    mnemonic_dict = {}

    # go over all nmemonics
    for mnemonic_name in mn.mnemonic_set_base:
        try:
            # set text and color
            status = 'Succes'
            color = '\033[0m'  # color black (standard)


            # get data
            data, meta, info = edb.query_single_mnemonic(mnemonic_name, start_time, end_time, token=mast_token)

            if data == None:
                data = Table(names=('MJD', 'euvalue', 'sqldataType', 'theTime'), dtype=('f8', 'f8', 'U4', 'U21'))
                status = 'Failure No data'
                color = '\33[31m'  # color red
                #raise Exception('No data')

            data['time_iso'] = Time(data['MJD'], format='mjd').iso
            del data['theTime']

            # data.show_in_browser(jsviewer=True)
            value = data['euvalue']
            time = data['MJD']

            description = ('time', 'value')
            data = [time, value]

            # add some meta data
            if len(time) > 0:
                date_start = time[0]
                date_end = time[len(time) - 1]
                info = {'start': date_start, 'end': date_end}
            else:
                info = {"n": "n"}

            # add name of mnemonic to meta data of list
            info['mnemonic'] = mnemonic_name
            info['len'] = len(time)

            # table to return
            mnemonic_table = Table(data, names=description, dtype=('f8', 'str'), meta=info)

            mnemonic_dict.update({mnemonic_name: mnemonic_table})



        except:
            # set text and color
            status = 'Failure '+ str(sys.exc_info()[1])
            color = '\33[31m'  # color red

        print_string = DateTime.now().isoformat() + ' Querry 15min: ' + mnemonic_name + '\t' + status
        print_string = color + print_string + '\033[0m'
        print(print_string)

    process_15min(conn, mnemonic_dict)


    print("*************************************************************")
    print("* querry data 15 min FINISHED")
    print("*************************************************************")

    #define time
    start_time = Time(day+' 00:00:00.001', format='iso')
    end_time =   Time(day+' 23:59:59.000', format='iso')



main()
