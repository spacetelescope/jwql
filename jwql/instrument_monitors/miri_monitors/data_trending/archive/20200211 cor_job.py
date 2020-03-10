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
import datetime
import netrc
import os
import statistics
import sys
from datetime import date
from datetime import datetime as DateTime
from multiprocessing import Process
from time import sleep

from astropy.time import Time

import jwql.edb.engineering_database as edb
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from jwql.utils.utils import get_config

host = 'mast'


class NullWriter(object):
    def write(self, arg):
        pass


def frange(start, stop, step):
    i = start
    while i < stop:
        yield i
        i += step


def querry_in_background(mnemonic_name, start_time, end_time, mast_token, conn):
    nullwrite = NullWriter()
    oldstdout = sys.stdout
    sys.stdout = nullwrite  # disable output

    try:
        # get data
        data, meta, info = edb.query_single_mnemonic(mnemonic_name, start_time, end_time, token=mast_token)
        data['time_iso'] = Time(data['MJD'], format='mjd').iso
        del data['theTime']

        # data.show_in_browser(jsviewer=True)
        value = data['euvalue']

        # process querried data
        length = len(value)
        mean = statistics.mean(value)
        deviation = statistics.stdev(value)
        dataset = (float(start_time.decimalyear), float(end_time.decimalyear), length, mean, deviation)
        sql.add_data(conn, mnemonic_name, dataset)

        # set text and color
        status = 'Succes'
        color = '\033[0m'  # color black (standard)

    except:
        # set text and color
        status = 'Failure'
        color = '\33[31m'  # color red

    print_string = 'dt_corn_job: ' + DateTime.now().isoformat() + '\t' + status + '\t' + mnemonic_name
    sys.stdout = oldstdout  # enable output
    print_string = color + print_string + '\033[0m'
    # sys.stdout.flush()
    # sys.stdout.write("\r%s" %print_string)
    print(print_string)


def main():
    max_time = 90
    step_time = 0.5

    # get date
    today = date.today()
    day = today - datetime.timedelta(days=10)
    day = day.strftime("%Y-%m-%d")

    # connect database
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'miri_database.db')
    conn = sql.create_connection(DATABASE_FILE)

    # define token
    secrets = netrc.netrc()
    mast_token = secrets.authenticators(host)[2]

    # define time
    start_time = Time(day + ' 12:00:00.000', format='iso')
    end_time = Time(day + ' 12:15:00.000', format='iso')

    # querry data 15 min STARTED
    print("*************************************************************")
    print("* querry data 15 min STARTED")
    print("*************************************************************")

    # go over all nmemonics
    for mnemonic_name in mn.mnemonic_set_15min:
        # define a new precess
        p = Process(target=querry_in_background, args=(mnemonic_name, start_time, end_time, mast_token, conn,))
        p.start()
        # sys.stdout.write("\n")

        # define max preccess time
        for i in frange(0, max_time, step_time):
            if i == (max_time - 1):
                output_s = '\33[31m' + 'dt_corn_job: ' + DateTime.now().isoformat() + '\t' + 'TimeOut' + '\t' + mnemonic_name + '\033[0m'
                # sys.stdout.write("\r%s" % output_s)
                print(output_s)
                break

            # display preccessed seconds
            if p.is_alive():
                # sys.stdout.flush()
                # output_s='\33[33m'+'dt_corn_job: Querry '+ mnemonic_name + ' for '+ str(i) + 's of ' + str(max_time) +'s' + '\033[0m'
                # sys.stdout.write("\r%s" % output_s)

                sleep(step_time)

            # if data querry was succesfull, break out of for
            else:
                break

        # if necessary close procces
        p.terminate()
        p.join()

    # finished
    sys.stdout.write("\n")
    print("*************************************************************")
    print("* querry data 15 min FINISHED")
    print("*************************************************************")

    # define time
    start_time = Time(day + ' 00:00:00.001', format='iso')
    end_time = Time(day + ' 23:59:59.000', format='iso')

    # querry data 15 min STARTED
    print("*************************************************************")
    print("* querry data day STARTED")
    print("*************************************************************")

    # go over all nmemonics
    for mnemonic_name in mn.mnemonic_set_15min:
        # define a new precess
        p = Process(target=querry_in_background, args=(mnemonic_name, start_time, end_time, mast_token, conn,))
        p.start()
        # sys.stdout.write("\n")

        # define max preccess time
        for i in frange(0, max_time, step_time):
            if i == (max_time - 1):
                output_s = '\33[31m' + 'dt_corn_job: ' + DateTime.now().isoformat() + '\t' + 'TimeOut' + '\t' + mnemonic_name + '\033[0m'
                # sys.stdout.write("\r%s" % output_s)
                print(output_s)
                break

            # display preccessed seconds
            if p.is_alive():
                # sys.stdout.flush()
                # output_s='\33[33m'+'dt_corn_job: Querry '+ mnemonic_name + ' for '+ str(i) + 's of ' + str(max_time) +'s' + '\033[0m'
                # sys.stdout.write("\r%s" % output_s)

                sleep(step_time)

            # if data querry was succesfull, break out of for
            else:
                break

        # if necessary close procces
        p.terminate()
        p.join()

    # finished
    sys.stdout.write("\n")
    print("*************************************************************")
    print("* querry data day FINISHED")
    print("*************************************************************")


main()
