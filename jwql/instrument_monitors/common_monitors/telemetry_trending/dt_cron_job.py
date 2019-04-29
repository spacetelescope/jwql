#! /usr/bin/env python
""" Cron Job for miri datatrending -> populates database

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

"""
import datetime
import glob
import os

from astropy.table import Table
from astropy.time import Time
import numpy as np

from .utils import miri_telemetry
from .utils import sql_interface as sql
from .utils import csv_to_AstropyTable as apt
from .utils.process_data import whole_day_routine, wheelpos_routine, once_a_day_routine
from jwql.database.database_interface import session
from jwql.database.database_interface import MIRIEngineeringTelemetry, MIRIFilterWheelTelemetry
from jwql.edb import engineering_database
from jwql.utils.utils import get_config

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
PACKAGE_DIR = __location__.split('instrument_monitors')[0]

def telemetry_trending(use_csvs=True, write_to_jwqldb=True):
    """Update the database with engineering telemetry trends

    Parameters
    ----------
    use_csvs : boolean
        Should the telemetry data be loaded from the CSV files on central
        storage? If not, they will be loaded via an EDB query (not yet
        implemented)

    write_to_jwqldb : boolean
        Should the telemetry data be written to the main JWQL database on
        central storage? If not, they will be written to the local
        SQLite databases.
    """
    if not write_to_jwqldb:
        database_file = os.path.join(PACKAGE_DIR, 'database', 'miri_database.db')
        conn = sql.create_connection(database_file)
    else:
        conn = None

    if use_csvs:
        populate_db_from_csv(conn, write_to_jwqldb)
    else:
        populate_db_from_edb(conn, write_to_jwqldb)

    if not write_to_jwqldb:
        sql.close_connection(conn)


def process_day_sample(conn, mnemonic_data_dict, write_to_jwqldb):
    """Process ~24 hour chunks of telemetry data and write to DB

    Parameters
    ----------
    conn : SQLite connection or None
        Connection to the local SQLite databases

    mnemonic_data_dict : dict
        Dictionary containing an Astropy table for each mnemonic identifier

    write_to_jwqldb : boolean
        Should the telemetry data be written to the main JWQL database on
        central storage? If not, they will be written to the local
        SQLite databases.
    """

    whole_day_dict = whole_day_routine(mnemonic_data_dict)

    FW, GW14, GW23, CCC = wheelpos_routine(mnemonic_data_dict)

    #put data from con3 to database
    for mnemonic_id, mnemonic_table in whole_day_dict.items():

        m = mnemonic_data_dict[mnemonic_id] # Can this just be the mnemonic_table from the whole_day_dict?

        if mnemonic_table != None:
            if len(mnemonic_table) > 2:
                length = len(mnemonic_table)
                mean = np.mean(mnemonic_table)
                deviation = np.std(mnemonic_table)

                # Define new database entry
                if write_to_jwqldb:
                    entry = {'start_time_mjd': float(m.meta['start']),
                             'end_time_mjd': float(m.meta['end']),
                             'n_data_points': length,
                             'average': mean,
                             'deviation': deviation}
                else:
                    dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)

                # Add entries to database
                if mnemonic_id == "SE_ZIMIRICEA":
                    if not write_to_jwqldb:
                        sql.add_data(conn, "SE_ZIMIRICEA_HV_ON", dataset)
                    else:
                        _write_telemetry_to_jwqldb("SE_ZIMIRICEA_HV_ON", entry)

                elif mnemonic_id == "IMIR_HK_ICE_SEC_VOLT4":
                    if not write_to_jwqldb:
                        sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_HV_ON", dataset)
                    else:
                        _write_telemetry_to_jwqldb("IMIR_HK_ICE_SEC_VOLT4_HV_ON", entry)

                else:
                    if not write_to_jwqldb:
                        sql.add_data(conn, mnemonic_id, dataset)
                    else:
                        _write_telemetry_to_jwqldb(mnemonic_id, entry)


    #########################################################################################
    for pos in miri_telemetry.fw_positions:
        try:
            data = FW[pos]
            for element in data:
                mnemonic_id = 'IMIR_HK_FW_POS_RATIO_{}'.format(pos)
                if not write_to_jwqldb:
                    sql.add_wheel_data(conn, mnemonic_id, element)
                else:
                    _write_filter_wheel_telemetry_to_jwqldb(mnemonic_id, element)

        except KeyError:
            pass

    for pos in miri_telemetry.gw_positions:
        try:
            data_GW14 = GW14[pos]
            data_GW23 = GW23[pos]

            for element in data_GW14:
                mnemonic_id = 'IMIR_HK_GW14_POS_RATIO_{}'.format(pos)
                if not write_to_jwqldb:
                    sql.add_wheel_data(conn, mnemonic_id, element)
                else:
                    _write_filter_wheel_telemetry_to_jwqldb(mnemonic_id, element)

            for element in data_GW23:
                mnemonic_id = 'IMIR_HK_GW23_POS_RATIO_{}'.format(pos)
                if not write_to_jwqldb:
                    sql.add_wheel_data(conn, mnemonic_id, element)
                else:
                    _write_filter_wheel_telemetry_to_jwqldb(mnemonic_id, element)

        except KeyError:
            pass

    for pos in miri_telemetry.ccc_positions:
        try:
            data = CCC[pos]
            for element in data:
                mnemonic_id = 'IMIR_HK_CCC_POS_RATIO_{}'.format(pos)
                if not write_to_jwqldb:
                    sql.add_wheel_data(conn, mnemonic_id, element)
                else:
                    _write_filter_wheel_telemetry_to_jwqldb(mnemonic_id, element)

        except KeyError:
            pass


def process_15min_sample(conn, mnemonic_data_dict, write_to_jwqldb):
    """Process 15 minute chunks of telemetry data and write to DB

    Parameters
    ----------
    conn : SQLite connection or None
        Connection to the local SQLite databases

    mnemonic_data_dict : dict
        Dictionary containing an Astropy table for each mnemonic identifier

    write_to_jwqldb : boolean
        Should the telemetry data be written to the main JWQL database on
        central storage? If not, they will be written to the local
        SQLite databases.
    """

    #process raw data with once a day routine
    processed_data = once_a_day_routine(mnemonic_data_dict)

    #push extracted and filtered data to temporary database
    for mnemonic_id, value in processed_data.items():

        mnemonic_table = mnemonic_data_dict[mnemonic_id]
        length = len(value)
        mean = np.mean(value)
        deviation = np.std(value)

        # Define new database entry
        if write_to_jwqldb:
            entry = {'start_time_mjd': float(mnemonic_table.meta['start']),
                     'end_time_mjd': float(mnemonic_table.meta['end']),
                     'n_data_points': length,
                     'average': mean,
                     'deviation': deviation}
        else:
            dataset = (float(mnemonic_table.meta['start']), float(mnemonic_table.meta['end']), length, mean, deviation)

        if mnemonic_id == "SE_ZIMIRICEA":
            if not write_to_jwqldb:
                sql.add_data(conn, "SE_ZIMIRICEA_IDLE", dataset)
            else:
                _write_telemetry_to_jwqldb("SE_ZIMIRICEA_IDLE", entry)

        elif mnemonic_id == "IMIR_HK_ICE_SEC_VOLT4":
            if not write_to_jwqldb:
                sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_IDLE", dataset)
            else:
                _write_telemetry_to_jwqldb("IMIR_HK_ICE_SEC_VOLT4_IDLE", entry)


        else:
            if not write_to_jwqldb:
                sql.add_data(conn, mnemonic_id, dataset)
            else:
                _write_telemetry_to_jwqldb(mnemonic_id, entry)


def populate_db_from_csv(conn, write_to_jwqldb):
    """Populate the MIRI telemetry database by parsing CSV files.

    Parameters
    ----------
    conn : SQLite connection or None
        Connection to the local SQLite databases

    write_to_jwqldb : boolean
        Should the telemetry data be written to the main JWQL database on
        central storage? If not, they will be written to the local
        SQLite databases.
    """
    csvs_day = glob.glob(
        os.path.join(get_config()['jwql_dir'], 'pending_outputs',
                     'miri_data_trending', 'trainings_data_day', '*.CSV')
    )
    csvs_15min = glob.glob(
        os.path.join(get_config()['jwql_dir'], 'pending_outputs',
                     'miri_data_trending', 'trainings_data_15min', '*.CSV')
    )

    for csv in csvs_day:
        # import mnemonic data and append dict to variable below
        m_raw_data = apt.mnemonics(csv)
        mnemonic_data_dict = m_raw_data.mnemonic_dict
        process_day_sample(conn, mnemonic_data_dict, write_to_jwqldb)

    for csv in csvs_15min:
        # import mnemonic data and append dict to variable below
        m_raw_data = apt.mnemonics(csv)
        mnemonic_data_dict = m_raw_data.mnemonic_dict
        process_15min_sample(conn, mnemonic_data_dict, write_to_jwqldb)


def populate_db_from_edb(conn, write_to_jwqldb, start_date=None, end_date=None):
    """Populate the MIRI telemetry database by querying the EDB

    Parameters
    ----------
    conn : SQLite connection or None
        Connection to the local SQLite databases

    write_to_jwqldb : boolean
        Should the telemetry data be written to the main JWQL database on
        central storage? If not, they will be written to the local
        SQLite databases.

    start_date : datetime.datetime object
        The first date to query telemetry from the EDB

    end_date : datetime.datetime object
        The last date to query telemetry from the EDB
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
                mnemonic_dict[mnemonic_id] = _create_mnemonic_table(
                    mnemonic_id, query_time, query_value
                )

        # Process, evaluate, and save data to DB
        process_15min_sample(conn, mnemonic_dict, write_to_jwqldb)

        # Query the EDB for day-long batches of data
        end_time = Time(date + datetime.timedelta(days=1))

        for mnemonic_id in miri_telemetry.mnemonic_set_day:
            if mnemonic_id not in miri_telemetry.not_in_edb:
                query_results = engineering_database.get_mnemonic(
                    mnemonic_id, start_time, end_time).data

                # Turn EDB queries into Astropy tables
                query_time = query_results['MJD']
                query_value = query_results['euvalue']
                mnemonic_dict[mnemonic_id] = _create_mnemonic_table(
                    mnemonic_id, query_time, query_value
                )

        # Process, evaluate, and save data to DB
        process_day_sample(conn, mnemonic_dict, write_to_jwqldb)

        print('Added telemetry from {} to database.'.format(date.strftime('%D')))


def _create_mnemonic_table(mnemonic, query_time, query_value):
    """Create an Astropy table with the times, values, and some metadata
    for a given mnemonic identifier.

    Parameters
    ----------
    mnemonic : str
        Mnemonic identifier

    query_time : list
        List of timestamps for mnemonic data

    query_value : list
        List of values for mnemonic data
    """
    # Include metadata
    if len(query_time) > 0:
        date_start = query_time[0]
        date_end = query_time[len(query_time) - 1]
        info = {'start': date_start, 'end': date_end}
    else:
        info = {"n": "n"}

    # add name of mnemonic to metadata of list
    info['mnemonic'] = mnemonic
    info['len'] = len(query_time)

    # table to return
    mnemonic_table = Table([query_time, query_value], names=('time','value'),
                           dtype=('f8', 'str'), meta=info)

    return mnemonic_table


def _write_telemetry_to_jwqldb(mnemonic_id, entry):
    """Write the engineering telemetry information for a given
    mnemonic to the JWQL database.

    Parameters
    ----------
    mnemonic_id : str
        Mnemonic identifier

    entry : dict
        Dictionary containing the following keys to be written to the DB:
            'start_time_mjd'
            'end_time_mjd'
            'n_data_points'
            'average'
            'deviation'
    """

    existing_entries = session.query(MIRIEngineeringTelemetry) \
        .filter(MIRIEngineeringTelemetry.start_time_mjd == entry['start_time_mjd']) \
        .filter(MIRIEngineeringTelemetry.mnemonic_id == mnemonic_id) \
        .all()
    if len(existing_entries) != 0:
        print('Entry already exists.')
        return

    entry['mnemonic_id'] = mnemonic_id
    entry['entry_date'] = datetime.datetime.now()
    MIRIEngineeringTelemetry.__table__.insert().execute(entry)


def _write_filter_wheel_telemetry_to_jwqldb(mnemonic_id, element):
    """Write the filter wheel telemetry value and timestamp for a given
    mnemonic to the JWQL database.

    Parameters
    ----------
    mnemonic_id : str
        Mnemonic identifier

    element : tuple
        Data pair of the mnemonic value at the given timestamp
    """
    timestamp_mjd, value = element

    existing_entries = session.query(MIRIFilterWheelTelemetry) \
        .filter(MIRIFilterWheelTelemetry.timestamp_mjd == timestamp_mjd) \
        .filter(MIRIFilterWheelTelemetry.mnemonic_id == mnemonic_id) \
        .all()
    if len(existing_entries) != 0:
        print('Entry already exists.')
        return

    entry = {'mnemonic_id': mnemonic_id,
             'timestamp_mjd': timestamp_mjd,
             'value': float(value),
             'entry_date': datetime.datetime.now()}
    MIRIFilterWheelTelemetry.__table__.insert().execute(entry)


if __name__ == "__main__":
    telemetry_trending()
    print("dt_cron_job.py done")
