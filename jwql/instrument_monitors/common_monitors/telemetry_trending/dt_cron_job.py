#! /usr/bin/env python
''' Cron Job for miri datatrending -> populates database

    This module holds functions to connect with the engineering database in order
    to grab and process data for the specific miri database. The scrips queries
    a daily 15 min chunk and a whole day dataset. These contain several mnemonics
    defined in ''miri_telemetry.py''. The queried data gets processed and stored in
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
import glob
import os

from astropy.time import Time
import numpy as np

from .utils import miri_telemetry
from .utils import sql_interface as sql
from .utils import csv_to_AstropyTable as apt
from .utils.process_data import whole_day_routine, wheelpos_routine, once_a_day_routine
from jwql.edb import engineering_database
from jwql.utils.utils import get_config

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
PACKAGE_DIR = __location__.split('instrument_monitors')[0]


def process_day_sample(conn, mnemonic_data_dict):
    '''Parse CSV file, process data within and put to DB

    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    # m_raw_data = apt.mnemonics(path)

    whole_day_dict = whole_day_routine(mnemonic_data_dict)

    FW, GW14, GW23, CCC = wheelpos_routine(mnemonic_data_dict)

    #put data from con3 to database
    for mnemonic_id, mnemonic_table in whole_day_dict.items():

        m = mnemonic_data_dict[mnemonic_id] # Can this just be the mnemonic_table from the whole_day_dict?

        if mnemonic_table != None:
            if len(mnemonic_table) > 2:
                length = len(mnemonic_table)
                mean = np.mean(mnemonic_table)
                deviation = np.stdev(mnemonic_table)
                dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)

                if mnemonic_id == "SE_ZIMIRICEA":
                    sql.add_data(conn, "SE_ZIMIRICEA_HV_ON", dataset)

                elif mnemonic_id == "IMIR_HK_ICE_SEC_VOLT4":
                    sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_HV_ON", dataset)

                else:
                    sql.add_data(conn, mnemonic_id, dataset)


    #########################################################################################
    for pos in miri_telemetry.fw_positions:
        try:
            data = FW[pos]
            for element in data:
                sql.add_wheel_data(conn, 'IMIR_HK_FW_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass

    for pos in miri_telemetry.gw_positions:
        try:
            data_GW14 = GW14[pos]
            data_GW23 = GW23[pos]

            for element in data_GW14:
                sql.add_wheel_data(conn, 'IMIR_HK_GW14_POS_RATIO_{}'.format(pos), element)
            for element in data_GW23:
                sql.add_wheel_data(conn, 'IMIR_HK_GW23_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass

    for pos in miri_telemetry.ccc_positions:
        try:
            data = CCC[pos]
            for element in data:
                sql.add_wheel_data(conn, 'IMIR_HK_CCC_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass


def process_15min_sample(conn, mnemonic_data_dict):
    '''Parse CSV file, process data within and put to DB

    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    #import mnemonic data and append dict to variable below
    # m_raw_data = apt.mnemonics(path)

    #process raw data with once a day routine
    processed_data = once_a_day_routine(mnemonic_data_dict)

    #push extracted and filtered data to temporary database
    for key, value in processed_data.items():

        #abbreviate data table
        m = mnemonic_data_dict[key]

        if key == "SE_ZIMIRICEA":
            length = len(value)
            mean = np.mean(value)
            deviation = np.stdev(value)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "SE_ZIMIRICEA_IDLE", dataset)

        elif key == "IMIR_HK_ICE_SEC_VOLT4":
            length = len(value)
            mean = np.mean(value)
            deviation = np.stdev(value)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_IDLE", dataset)

        else:
            length = len(value)
            mean = np.mean(value)
            deviation = np.stdev(value)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, key, dataset)


def populate_db_from_csv(conn):
    """Populate the miri_database.db by parsing CSV files.
    """
    csvs_day = glob.glob(
        os.path.join(get_config()['jwql_dir'], 'pending_outputs', 'miri_data_trending', 'trainings_data_day', '*.CSV'))
    csvs_15min = glob.glob(
        os.path.join(get_config()['jwql_dir'], 'pending_outputs', 'miri_data_trending', 'trainings_data_15min',
                     '*.CSV'))

    for csv in csvs_day:
        # import mnemonic data and append dict to variable below
        m_raw_data = apt.mnemonics(csv)
        mnemonic_data_dict = m_raw_data.__mnemonic_dict
        process_day_sample(conn, mnemonic_data_dict)

    for csv in csvs_15min:
        # import mnemonic data and append dict to variable below
        m_raw_data = apt.mnemonics(csv)
        mnemonic_data_dict = m_raw_data.__mnemonic_dict
        process_15min_sample(conn, mnemonic_data_dict)


def populate_db_from_edb(conn, start_date=None, end_date=None):
    """Populate the miri_database.db by querying the EDB
    """

    # TODO: Check to see when the query was last performed

    # Define start and end dates
    if start_date is None:
        start_date = datetime.datetime(2017, 8, 15)
    if end_date is None:
        end_date = datetime.datetime.now()
    # Determine how many days need to be queried
    if isinstance(start_date, datetime.datetime) and isinstance(end_date, datetime.datetime):
        dates_to_query = [
            start_date + datetime.timedelta(days=x) for x in range((end_date - start_date).days + 1)
        ]
    else:
        raise TypeError("Please provide start_date and end_date as datetime.datetime objects.")

    # Perform the queries for each day and update the database
    mnemonic_dict = {}
    for date in dates_to_query:

        # Query the EDB for 15 minute batches of data
        start_time = Time(date)
        end_time = Time(date + datetime.timedelta(minutes=15))

        for mnemonic_id in miri_telemetry.mnemonic_set_15min:
            if mnemonic_id not in miri_telemetry.not_in_edb:
                query_results = engineering_database.get_mnemonic(
                    mnemonic_id, start_time, end_time).data

                # Turn EDB queries into Astropy tables
                query_time = query_results['MJD']
                query_value = query_results['euvalue']
                mnemonic_dict[mnemonic_id] = apt.mnemonic_table(
                    mnemonic_id, query_time, query_value
                )

        # Process, evaluate, and save data to DB
        process_15min_sample(conn, mnemonic_dict)

        # Query the EDB for day-long batches of data
        end_time = Time(date + datetime.timedelta(days=1))

        for mnemonic_id in miri_telemetry.mnemonic_set_day:
            if mnemonic_id not in miri_telemetry.not_in_edb:
                query_results = engineering_database.get_mnemonic(
                    mnemonic_id, start_time, end_time).data

                # Turn EDB queries into Astropy tables
                query_time = query_results['MJD']
                query_value = query_results['euvalue']
                mnemonic_dict[mnemonic_id] = apt.mnemonic_table(
                    mnemonic_id, query_time, query_value
                )

        # Process, evaluate, and save data to DB
        process_day_sample(conn, mnemonic_dict)

        print('Added telemetry from {} to database.'.format(date.strftime('%D')))


def telemetry_trending(use_csvs=True):
    """Update the database with engineering telemetry trends

    Parameters
    ----------
    use_csvs : boolean
        Should the telemetry data be loaded from the CSV files on central
        storage? If not, they will be loaded via an EDB query (not yet
        implemented)
    """

    DATABASE_LOCATION = os.path.join(PACKAGE_DIR, 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'miri_database.db')

    conn = sql.create_connection(DATABASE_FILE)

    if use_csvs:
        populate_db_from_csv(conn)
    else:
        populate_db_from_edb(conn)

    sql.close_connection(conn)


if __name__ == "__main__":
    telemetry_trending()
    print("dt_cron_job.py done")
