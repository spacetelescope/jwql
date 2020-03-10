"""dt_corn_job.py

    This module holds functions to connect with the engineering database in order
    to grab and process data for the specific miri database. The scrips queries
    a daily 15 min chunk and a whole day dataset. These contain several mnemonics
    defined in ''mnemonics.py''. The queried data gets processed and stored in
    an auxiliary database.

Authors
-------

    - [AIRBUS] Daniel Kübacher
    - [AIRBUS] Leo Stumpf

Use
---
    -

Dependencies
------------

    The file miri_database.db in the directory jwql/jwql/database/ must exist.
    
References
----------
    The code was developed in reference to the information provided in:
    ‘MIRI trend requestsDRAFT1900301.docx’

Notes
-----

    For further information please contact Brian O'Sullivan
"""
import datetime
import netrc
import os
import sys
import time
from datetime import date

from astropy.table import Table
from astropy.time import Time

import jwql.edb.engineering_database as edb
import jwql.instrument_monitors.miri_monitors.data_trending.utils.log_error_and_file as log_error_and_file
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from jwql.instrument_monitors.miri_monitors.data_trending.day_job import process_day
from jwql.instrument_monitors.miri_monitors.data_trending.min_job import process_15min
from jwql.utils.utils import get_config

def querry_data(mnemonic_name, start_time, end_time, mast_token):
    """Download data from the mast database

    This function dowloads all datapoints of a given mnemonic in the set time frame.

    Parameters
    ----------
    mnemonic_name : str
        Name of the mnemonic to be downloaded.
    start_time : astrophy.time
        Start of timespan to be downloaded
    end_time : astrophy.time
        end of timespan to be downloaded
    mast_token : mast token

    Returns
    -------
    mnemonic_table : astrophy.table
        all downloaded data is presented in an astrophy table, with the format needed for the processing functions.
    """

    #Declare log region Querry
    log = log_error_and_file.Log('Querry')

    #Download data from the mast website and check weather there is anything wrong with the downloaded data
    try:
        data, meta, info = edb.query_single_mnemonic(mnemonic_name, start_time, end_time, token=mast_token)

        if data is None:
            data = Table(names=('MJD', 'euvalue', 'sqldataType', 'theTime'), dtype=('f8', 'f8', 'U4', 'U21'))
            log.log(mnemonic_name + ' Failed: No Data', 'Error')
        else:
            log.log(mnemonic_name + ' Succesful Downloaded ' + str(len(data)) + ' data points')

    except:
        # set text and color
        data = Table(names=('MJD', 'euvalue', 'sqldataType', 'theTime'), dtype=('f8', 'f8', 'U4', 'U21'))
        log.log(mnemonic_name + ' Failed: ' + str(sys.exc_info()[1]), 'Error')


    # Generate Info for the meta section
    time_column = data['MJD']
    if len(time_column) > 0:
        date_start = time_column[0]
        date_end = time_column[len(time_column) - 1]
        info = {'start': date_start, 'end': date_end}
    else:
        info = {"n": "n"}

    info['mnemonic'] = mnemonic_name
    info['len'] = len(time_column)

    #Format the table as it is needet for the processing unit
    description = ('time', 'value')
    data_return = [data['MJD'], data['euvalue']]

    return Table(data_return, names=description, dtype=('f8', 'str'), meta=info)

def get_data_day(day):
    """Download + Process + Save all mnemonics for one specific day

    Parameters
    ----------
    day : string
    string of date to be downloaded: Format = JJJJ-MM-DD

    Returns
    -------
    Saves directly in defined SQL database
    """

    #save the start time of the function to calculate the run time
    start_time_proc = time.time()

    #Connect to the miri database to save the variables
    database_location = os.path.join(get_config()['jwql_dir'], 'database')
    database_file = os.path.join(database_location, 'miri_database.db')
    conn = sql.create_connection(database_file)

    #Define Mast token
    host = 'mast'
    secrets = netrc.netrc()
    mast_token = secrets.authenticators(host)[2]

    #Generate a new log file
    log_error_and_file.define_log_file('log//LogFile_' + day + '.log')
    log = log_error_and_file.Log('MAIN')
    log.info('Process Startet for day ' + day)


    #Download data in the 15 min job
    log.info('querry data 15 min')
    mnemonic_dict = {}

    start_time = Time(day + ' 11:59:59.000', format='iso')
    end_time = Time(day + ' 12:15:01.000', format='iso')

    for mnemonic_name in mn.miri_mnemonic_min:
        mnemonic_table = querry_data(mnemonic_name, start_time, end_time, mast_token)
        mnemonic_dict.update({mnemonic_name: mnemonic_table})

    process_15min(conn, mnemonic_dict)


    # Download data in the day min job
    log.info('querry data day')
    mnemonic_dict = {}

    start_time = Time(day + ' 00:00:00.001', format='iso')
    end_time = Time(day + ' 23:59:59.000', format='iso')

    for mnemonic_name in mn.whould_day:
        mnemonic_table = querry_data(mnemonic_name, start_time, end_time, mast_token)
        mnemonic_dict.update({mnemonic_name: mnemonic_table})

    process_day(conn, mnemonic_dict)


    #Generate info end section
    end_time_proc = time.time()
    hours, rem = divmod(end_time_proc - start_time_proc, 3600)
    minutes, seconds = divmod(rem, 60)

    end_print = ['file:     dt_corn_job.py',
                 'version:  1.0',
                 'run time: {:0>2}:{:0>2}:{:05.2f}'.format(int(hours), int(minutes), seconds),
                 'status:   finished']
    log.info(end_print)

    log_error_and_file.delete_log_file()

def main_oneDay():
    #runs the software once for one specific date
    day = '2019-11-10'
    get_data_day(day)

def main_daily():
    #runs the software once for yesterday
    today = date.today()
    day = today - datetime.timedelta(days=1)
    day = day.strftime("%Y-%m-%d")

    get_data_day(day)

def main_multipleDays():
    #runs the software for mulatiple days
    today = date.today()
    for i in range(20):
        day = today - datetime.timedelta(days=(300 - i))
        day = day.strftime("%Y-%m-%d")
        get_data_day(day)

main_oneDay()
