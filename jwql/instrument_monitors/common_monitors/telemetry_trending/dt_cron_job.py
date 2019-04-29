#! /usr/bin/env python
""" Populate the JWQL DB with engineering telemetry trending data for MIRI and NIRSpec.

This module holds functions to connect with the engineering database in order
to grab and process data for the specific miri database. The scrips queries
a daily 15 min chunk and a whole day dataset. These contain several mnemonics
defined in ``miri_telemetry.py``. The queried data gets processed and stored in
an auxiliary database.

Use
---

    This module can be used from the command line as such:

    ::

        python dark_monitor.py

Authors
-------
    - Daniel Kühbacher
    - Lauren Chambers

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

from .utils import miri_telemetry, process_miri_data, nirspec_telemetry, process_nirspec_data
from .utils import sql_interface as sql
from .utils import csv_to_AstropyTable as apt
from jwql.database.database_interface import session
from jwql.database.database_interface import MIRIEngineeringTelemetry, MIRIFilterWheelTelemetry, NIRSpecEngineeringTelemetry, NIRSpecFilterWheelTelemetry
from jwql.edb.edb_interface import is_valid_mnemonic
from jwql.edb.engineering_database import get_mnemonic
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
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
        completely implemented)

    write_to_jwqldb : boolean
        Should the telemetry data be written to the main JWQL database on
        central storage? If not, they will be written to local
        SQLite database files.
    """

    # for inst in ['miri', 'nirspec']:
    for inst in ['nirspec']:
        if not write_to_jwqldb:
            database_file = os.path.join(PACKAGE_DIR, 'database', '{}_database.db'.format(inst))
            conn = sql.create_connection(database_file)
        else:
            conn = None

        if use_csvs:
            populate_db_from_csv(conn, write_to_jwqldb)
        else:
            populate_db_from_edb(conn, write_to_jwqldb)

        if not write_to_jwqldb:
            sql.close_connection(conn)


def miri_process_day_sample(conn, mnemonic_data_dict, write_to_jwqldb):
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

    whole_day_dict = process_miri_data.whole_day_routine(mnemonic_data_dict)

    FW, GW14, GW23, CCC = process_miri_data.wheelpos_routine(mnemonic_data_dict)

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
                        _write_telemetry_to_jwqldb(MIRIEngineeringTelemetry, "SE_ZIMIRICEA_HV_ON", entry)

                elif mnemonic_id == "IMIR_HK_ICE_SEC_VOLT4":
                    if not write_to_jwqldb:
                        sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_HV_ON", dataset)
                    else:
                        _write_telemetry_to_jwqldb(MIRIEngineeringTelemetry, "IMIR_HK_ICE_SEC_VOLT4_HV_ON", entry)

                else:
                    if not write_to_jwqldb:
                        sql.add_data(conn, mnemonic_id, dataset)
                    else:
                        _write_telemetry_to_jwqldb(MIRIEngineeringTelemetry, mnemonic_id, entry)


    #########################################################################################
    for pos in miri_telemetry.fw_positions:
        try:
            data = FW[pos]
            for element in data:
                mnemonic_id = 'IMIR_HK_FW_POS_RATIO_{}'.format(pos)
                if not write_to_jwqldb:
                    sql.add_wheel_data(conn, mnemonic_id, element)
                else:
                    _write_filter_wheel_telemetry_to_jwqldb(MIRIFilterWheelTelemetry, mnemonic_id, element)

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
                    _write_filter_wheel_telemetry_to_jwqldb(MIRIFilterWheelTelemetry, mnemonic_id, element)

            for element in data_GW23:
                mnemonic_id = 'IMIR_HK_GW23_POS_RATIO_{}'.format(pos)
                if not write_to_jwqldb:
                    sql.add_wheel_data(conn, mnemonic_id, element)
                else:
                    _write_filter_wheel_telemetry_to_jwqldb(MIRIFilterWheelTelemetry, mnemonic_id, element)

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
                    _write_filter_wheel_telemetry_to_jwqldb(MIRIFilterWheelTelemetry, mnemonic_id, element)

        except KeyError:
            pass


def miri_process_15min_sample(conn, mnemonic_data_dict, write_to_jwqldb):
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
    processed_data = process_miri_data.once_a_day_routine(mnemonic_data_dict)

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
                _write_telemetry_to_jwqldb(MIRIEngineeringTelemetry, "SE_ZIMIRICEA_IDLE", entry)

        elif mnemonic_id == "IMIR_HK_ICE_SEC_VOLT4":
            if not write_to_jwqldb:
                sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_IDLE", dataset)
            else:
                _write_telemetry_to_jwqldb(MIRIEngineeringTelemetry, "IMIR_HK_ICE_SEC_VOLT4_IDLE", entry)


        else:
            if not write_to_jwqldb:
                sql.add_data(conn, mnemonic_id, dataset)
            else:
                _write_telemetry_to_jwqldb(MIRIEngineeringTelemetry, mnemonic_id, entry)


def nirspec_process_day_sample(conn, mnemonic_data_dict, write_to_jwqldb):
    '''Parse CSV file, process data within and put to DB
    
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    #process raw data with once a day routine
    whole_day_dict, lamp_data = process_nirspec_data.whole_day_routine(mnemonic_data_dict)
    FW, GWX, GWY = process_nirspec_data.wheelpos_routine(mnemonic_data_dict)

    #put all data to a database that uses a condition
    for mnemonic_id, mnemonic_table in whole_day_dict.items():
        m = mnemonic_data_dict[mnemonic_id]
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

        if not write_to_jwqldb:
            sql.add_data(conn, mnemonic_id, dataset)
        else:
            _write_telemetry_to_jwqldb(NIRSpecEngineeringTelemetry, "SE_ZIMIRICEA_HV_ON", entry)

    #add lamp data to database -> distiction over lamps
    for mnemonic_id, values in lamp_data.items():
        for data in values:
            start_time, end_time = data[:2]
            for data_type, inds in zip(['VOLT', 'CURR'], [[5, 6, 7], [2, 3, 4]]):
                id = 'LAMP_{}_{}'.format(mnemonic_id, data_type)
                n_data_points, average, deviation = data[inds]
                # Define new database entry
                if write_to_jwqldb:
                    entry = {'start_time_mjd': float(start_time),
                             'end_time_mjd': float(end_time),
                             'n_data_points': n_data_points,
                             'average': average,
                             'deviation': deviation}
                else:
                    dataset = (float(start_time), float(end_time), n_data_points, average, deviation)

                if not write_to_jwqldb:
                    sql.add_data(conn, id, dataset)
                else:
                    _write_telemetry_to_jwqldb(NIRSpecEngineeringTelemetry, id, entry)

    #add wheeldata to database]
    wheel_dicts = [FW, GWX, GWY]
    ids = ['INRSI_C_FWA_POSITION_{}', 'INRSI_C_GWA_X_POSITION_{}', 'INRSI_C_GWA_Y_POSITION_{}']
    for wheel_dict, id in zip(wheel_dicts, ids):
        for mnemonic_id, values in wheel_dict.items():
            for data in values:
                id = id.format(mnemonic_id)

                if not write_to_jwqldb:
                    sql.add_wheel_data(conn, id, data)
                else:
                    _write_filter_wheel_telemetry_to_jwqldb(NIRSpecFilterWheelTelemetry, id, data)


def nirspec_process_15min_sample(conn, mnemonic_data_dict, write_to_jwqldb):
    '''Parse CSV file, process data within and put to DB
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    #process raw data with once a day routine
    once_a_day_dict = process_nirspec_data.once_a_day_routine(mnemonic_data_dict)

    #put all data in a database that uses a condition
    for mnemonic_id, mnemonic_table in once_a_day_dict.items():
        m = mnemonic_data_dict[mnemonic_id]
        n_data_points = len(mnemonic_table)

        # return None if no applicable data was found
        if n_data_points > 2:
            mean = np.mean(mnemonic_table)
            deviation = np.std(mnemonic_table)
            start_time = m.meta['start']
            end_time = m.meta['end']

        elif n_data_points == 2:
            n_data_points = 1
            start_time = mnemonic_table['time']
            end_time = mnemonic_table['time']
            average = mnemonic_table[0]
            deviation = 0
            print('Trying to modify the database entry for N=2. Something weird going on here.')
            print((float(start_time), float(end_time), n_data_points, average, deviation))

        if write_to_jwqldb:
            entry = {'start_time_mjd': float(start_time),
                     'end_time_mjd': float(end_time),
                     'n_data_points': n_data_points,
                     'average': average,
                     'deviation': deviation}
        else:
            dataset = (float(start_time), float(end_time), n_data_points, average, deviation)

        if not write_to_jwqldb:
            sql.add_data(conn, mnemonic_id, dataset)
        else:
            _write_telemetry_to_jwqldb(NIRSpecEngineeringTelemetry, id, entry)


def populate_db_from_csv(conn, write_to_jwqldb):
    """Populate the MIRI telemetry database by parsing CSV files.
    (We don't have the CSV files for NIRSpec.)

    Parameters
    ----------
    conn : SQLite connection or None
        Connection to the local SQLite databases

    write_to_jwqldb : boolean
        Should the telemetry data be written to the main JWQL database on
        central storage? If not, they will be written to the local
        SQLite databases.
    """
    miri_csvs_day = glob.glob(
        os.path.join(get_config()['jwql_dir'], 'pending_outputs',
                     'miri_data_trending', 'trainings_data_day', '*.CSV')
    )
    miri_csvs_15min = glob.glob(
        os.path.join(get_config()['jwql_dir'], 'pending_outputs',
                     'miri_data_trending', 'trainings_data_15min', '*.CSV')
    )

    for csv in miri_csvs_day:
        # import mnemonic data and append dict to variable below
        m_raw_data = apt.mnemonics(csv)
        mnemonic_data_dict = m_raw_data.mnemonic_dict
        miri_process_day_sample(conn, mnemonic_data_dict, write_to_jwqldb)

    for csv in miri_csvs_15min:
        # import mnemonic data and append dict to variable below
        m_raw_data = apt.mnemonics(csv)
        mnemonic_data_dict = m_raw_data.mnemonic_dict
        miri_process_15min_sample(conn, mnemonic_data_dict, write_to_jwqldb)


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
    for inst in ['miri', 'nirspec']:
        # Check to see when the query was last performed
        if write_to_jwqldb:
            start_date = _get_latest_query(inst)
            print('Starting {} query on {}'.format(JWST_INSTRUMENT_NAMES_MIXEDCASE[inst], start_date.strftime('%D')))

        # Define default start and end dates
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
        for date in dates_to_query:

            if inst == 'miri':
                _daily_miri_queries(conn, write_to_jwqldb, date)
            elif inst == 'nirspec':
                _daily_nirspec_queries(conn, write_to_jwqldb, date)

            print('Added {} telemetry from {} to database.'.format(inst, date.strftime('%D')))


def _daily_miri_queries(conn, write_to_jwqldb, date):
    # Query the EDB for 15 minute chunks of data
    start_time = Time(date)
    end_time = Time(date + datetime.timedelta(minutes=15))

    mnemonic_15min_dict = {}
    for mnemonic_id in miri_telemetry.mnemonic_set_15min:
        if is_valid_mnemonic(mnemonic_id):
            query_results = get_mnemonic(
                mnemonic_id, start_time, end_time).data

            # Turn EDB queries into Astropy tables
            query_time = query_results['MJD']
            query_value = query_results['euvalue']
            mnemonic_15min_dict[mnemonic_id] = _create_mnemonic_table(
                mnemonic_id, query_time, query_value
            )

    # Process, evaluate, and save data to DB
    miri_process_15min_sample(conn, mnemonic_15min_dict, write_to_jwqldb)

    # Query the EDB for ~24 hour-long chunks of data
    end_time = Time(date + datetime.timedelta(days=1))

    mnemonic_day_dict = {}
    for mnemonic_id in miri_telemetry.mnemonic_set_day:
        if is_valid_mnemonic(mnemonic_id):
            query_results = get_mnemonic(
                mnemonic_id, start_time, end_time).data

            # Turn EDB queries into Astropy tables
            query_time = query_results['MJD']
            query_value = query_results['euvalue']
            mnemonic_day_dict[mnemonic_id] = _create_mnemonic_table(
                mnemonic_id, query_time, query_value
            )

    # Process, evaluate, and save data to DB
    miri_process_day_sample(conn, mnemonic_day_dict, write_to_jwqldb)


def _daily_nirspec_queries(conn, write_to_jwqldb, date):
    # Query the EDB for 15 minute chunks of data
    start_time = Time(date)
    end_time = Time(date + datetime.timedelta(minutes=15))

    mnemonic_15min_dict = {}
    for mnemonic_id in nirspec_telemetry.mnemonic_set_15min:
        if is_valid_mnemonic(mnemonic_id):
            query_results = get_mnemonic(
                mnemonic_id, start_time, end_time).data

            # Turn EDB queries into Astropy tables
            query_time = query_results['MJD']
            query_value = query_results['euvalue']
            mnemonic_15min_dict[mnemonic_id] = _create_mnemonic_table(
                mnemonic_id, query_time, query_value
            )

    # Process, evaluate, and save data to DB
    nirspec_process_15min_sample(conn, mnemonic_15min_dict, write_to_jwqldb)

    # Query the EDB for ~24 hour-long chunks of data
    end_time = Time(date + datetime.timedelta(days=1))

    mnemonic_day_dict = {}
    for mnemonic_id in nirspec_telemetry.mnemonic_set_day:
        if is_valid_mnemonic(mnemonic_id):
            query_results = get_mnemonic(
                mnemonic_id, start_time, end_time).data

            # Turn EDB queries into Astropy tables
            query_time = query_results['MJD']
            query_value = query_results['euvalue']
            mnemonic_day_dict[mnemonic_id] = _create_mnemonic_table(
                mnemonic_id, query_time, query_value
            )

    # Process, evaluate, and save data to DB
    nirspec_process_day_sample(conn, mnemonic_day_dict, write_to_jwqldb)

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


def _get_latest_query(inst):
    """Get the date of the most recent trending data added to the JWQL DB.

    Returns
    -------
    last_telem : Astropy.time.Time
        Date & time of most recent trending data entry in JWQL DB
    """
    inst_mixed_case = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]
    eng_telem_table = eval('{}EngineeringTelemetry'.format(inst_mixed_case))
    filter_wheel_table = eval('{}FilterWheelTelemetry'.format(inst_mixed_case))

    eng_entries = session.query(eng_telem_table).all()
    filter_wheel_entries = session.query(filter_wheel_table).all()

    if eng_entries == [] and filter_wheel_entries == []:
        return None

    last_eng_telem = np.max([e.start_time_mjd for e in eng_entries])
    last_filter_wheel_telem = np.max(
        [f.timestamp_mjd for f in filter_wheel_entries if f.timestamp_mjd is not None]
    )
    last_telem = max(last_eng_telem, last_filter_wheel_telem)

    return Time(last_telem, format='mjd').datetime


def _write_telemetry_to_jwqldb(table, mnemonic_id, entry):
    """Write the engineering telemetry information for a given
    mnemonic to the JWQL database.

    Parameters
    ----------
    table : SQLAlchemy Table
        The table to write the entry to

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

    existing_entries = session.query(table) \
        .filter(table.start_time_mjd == entry['start_time_mjd']) \
        .filter(table.mnemonic_id == mnemonic_id) \
        .all()
    if len(existing_entries) != 0:
        print('Entry already exists.')
        return

    entry['mnemonic_id'] = mnemonic_id
    entry['entry_date'] = datetime.datetime.now()
    table.__table__.insert().execute(entry)


def _write_filter_wheel_telemetry_to_jwqldb(table, mnemonic_id, element):
    """Write the filter wheel telemetry value and timestamp for a given
    mnemonic to the JWQL database.

    Parameters
    ----------
    table : SQLAlchemy Table
        The table to write the entry to

    mnemonic_id : str
        Mnemonic identifier

    element : tuple
        Data pair of the mnemonic value at the given timestamp
    """
    timestamp_mjd, value = element

    existing_entries = session.query(table) \
        .filter(table.timestamp_mjd == timestamp_mjd) \
        .filter(table.mnemonic_id == mnemonic_id) \
        .all()
    if len(existing_entries) != 0:
        print('Entry already exists.')
        return

    entry = {'mnemonic_id': mnemonic_id,
             'timestamp_mjd': timestamp_mjd,
             'value': float(value),
             'entry_date': datetime.datetime.now()}
    table.__table__.insert().execute(entry)


if __name__ == "__main__":
    telemetry_trending()
    print("dt_cron_job.py done")
