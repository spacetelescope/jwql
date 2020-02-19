#! /usr/bin/env python

"""Cron Job for MIRI data trending

This module holds functions to connect with the engineering database in
order to grab and process data for MIRI data trending. The script
queries a daily 15-minute chunk and a whole-day dataset. These contain
several mnemonics defined in ``mnemonics.py``. The queried data gets
processed and stored in an auxiliary database.

Authors
-------

    - Daniel Kühbacher

Dependencies
------------

    - ``jwedb``

References
----------

    For further information please contact Brian O'Sullivan
"""

import os
import statistics

from jwedb.edb_interface import query_single_mnemonic

from .utils import csv_to_astropy_table, mnemonics, sql_interface
from .utils.process_data import wheelpos_routine, whole_day_routine


PACKAGE_DIR = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))).split('instrument_monitors')[0]


def main():
    """Main function of the ``dt_cron_job`` module.  See module
    docstring for further details"""

    for mnemonic in mnemonics.mnemonic_set_15min:
        whole_day.update(mnemonic=query_single_mnemonic(mnemonic, start, end))

    # Open temporary database and write data
    database_file = os.path.join(PACKAGE_DIR, 'database', 'miri_database.db')
    conn = sql_interface.create_connection(database_file)
    process_day_sample(conn, table_day)
    process_15process_15min_sample(conn, table_15min)
    sql_interface.close_connection(conn)


def process_15min_sample(conn, path):
    """Parse CSV file, process data within and put into auxillary
    database

    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        Defines path to the files
    """

    # Import mnemonic data and append dict to variable below
    mnemonics_raw_data = csv_to_astropy_table.mnemonics(path)

    # Process raw data with once a day routine
    processed_data = once_a_day_routine(mnemonics_raw_data)

    # Push extracted and filtered data to auxillary database
    for key, value in processed_data.items():

        # Abbreviate data table
        mnemonics_data_table = mnemonics_raw_data.mnemonic(key)

        length = len(value)
        mean = statistics.mean(value)
        deviation = statistics.stdev(value)
        dataset = (
            float(mnemonics_data_table.meta['start']),
            float(mnemonics_data_table.meta['end']),
            length,
            mean,
            deviation)

        if key == "SE_ZIMIRICEA":
            sql_interface.add_data(conn, 'SE_ZIMIRICEA_IDLE', dataset)
        elif key == 'IMIR_HK_ICE_SEC_VOLT4':
            sql_interface.add_data(conn, 'IMIR_HK_ICE_SEC_VOLT4_IDLE', dataset)
        else:
            sql_interface.add_data(conn, key, dataset)


def process_day_sample(conn, path):
    """Parse CSV file, process data within and put into auxillary
    database

    Parameters
    ----------
    conn : obj
        Connection object to auxillary database
    path : str
        Defines path to the files
    """

    raw_data = csv_to_astropy_table.mnemonics(path)

    cond3, FW_volt, GW14_volt, GW23_volt, CCC_volt = whole_day_routine(raw_data)
    FW, GW14, GW23, CCC = wheelpos_routine(raw_data)

    # Put data from con3 to database
    for key, value in cond3.items():

        mnemonics_data_table = raw_data.mnemonic(key)

        if value is not None:
            if len(value) > 2:

                length = len(value)
                mean = statistics.mean(value)
                deviation = statistics.stdev(value)
                dataset = (
                    float(mnemonics_data_table.meta['start']),
                    float(mnemonics_data_table.meta['end']),
                    length,
                    mean,
                    deviation)

                if key == 'SE_ZIMIRICEA':
                    sql_interface.add_data(conn, 'SE_ZIMIRICEA_HV_ON', dataset)
                elif key == 'IMIR_HK_ICE_SEC_VOLT4':
                    sql_interface.add_data(conn, 'IMIR_HK_ICE_SEC_VOLT4_HV_ON', dataset)
                else:
                    sql_interface.add_data(conn, key, dataset)

    for position in mnemonics.fw_positions:
        try:
            data = FW[position]
            for element in data:
                sql_interface.add_wheel_data(conn, 'IMIR_HK_FW_POS_RATIO_{}'.format(position), element)
        except KeyError:
            pass

    for position in mnemonics.gw_positions:
        try:
            data_GW14 = GW14[position]
            data_GW23 = GW23[position]
            for element in data_GW14:
                sql_interface.add_wheel_data(conn, 'IMIR_HK_GW14_POS_RATIO_{}'.format(position), element)
            for element in data_GW23:
                sql_interface.add_wheel_data(conn, 'IMIR_HK_GW23_POS_RATIO_{}'.format(position), element)
        except KeyError:
            pass

    for position in mnemonics.ccc_positions:
        try:
            data = CCC[position]
            for element in data:
                sql_interface.add_wheel_data(conn, 'IMIR_HK_CCC_POS_RATIO_{}'.format(position), element)
        except KeyError:
            pass
