"""min_job.py

    Process the data generated for a 15 min time frame around noon

    Processes all the data which is only generated as it is changed.
    Thes data will be processed to get the data needet for the display software.

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
import statistics

import sys

import jwql.instrument_monitors.miri_monitors.data_trending.utils.condition as cond
import jwql.instrument_monitors.miri_monitors.data_trending.utils.extract_data as extract_data
import jwql.instrument_monitors.miri_monitors.data_trending.utils.log_error_and_file as log_error_and_file
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql


def process_15min(conn, m_raw_data):
    """Parse CSV file, process data within and put to DB

    Parameters
    ----------
    m_raw_data
    conn : DBobject
        Connection object to auxiliary database
    """

    # Define new log section
    log = log_error_and_file.Log('PROCESS')
    log.info('process data 15 min')

    # Process and Filter the downloaded mnmemonics
    processed_data = once_a_day_routine(m_raw_data)

    # Sql save the mnemonics
    log.info('SQL data 15 min')

    for key, value in processed_data.items():
        m = m_raw_data[key]
        try:
            # Convert mnemonics name of specific mnemonics

            if key == "SE_ZIMIRICEA":
                key = "SE_ZIMIRICEA_IDLE"

            if key == "IMIR_HK_ICE_SEC_VOLT4":
                key = "IMIR_HK_ICE_SEC_VOLT4_IDLE"

            # Save in sql database
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, key, dataset)

        except:
            if 'variance requires at least two data points' == str(sys.exc_info()[1]):
                dataset = (float(m.meta['start']), float(m.meta['end']), float(1), value[0], float(0))
                sql.add_data(conn, key, dataset)
            else:
                log.log('Error: ' + str(sys.exc_info()[1]), 'Error')


def once_a_day_routine(mnemonic_data):
    """Proposed routine for processing a 15min data file once a day
    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with correspining identifier as key
    Return
    ------
    data_cond_1 : dict
        holds extracted data with condition 1 applied
    data_cond_1 : dict
        holds extracted data with condition 2 applied
    """

    log = log_error_and_file.Log('Process')
    m = mnemonic_data
    returndata = dict()

    # Define Condition Set 1
    # add filtered engineering values of mnemonics given in list mnemonic_cond_1
    con_set_1 = [
        cond.equal(m['IMIR_HK_IMG_CAL_LOOP'], 'OFF'),
        cond.equal(m['IMIR_HK_IFU_CAL_LOOP'], 'OFF'),
        cond.equal(m['IMIR_HK_POM_LOOP'], 'OFF'),
        cond.smaller(m['IMIR_HK_ICE_SEC_VOLT1'], 1.0),
        cond.greater(m['SE_ZIMIRICEA'], 0.2)]
    condition_1 = cond.condition(con_set_1)

    for identifier in mn.mnemonic_cond_1:
        data = extract_data.extract_data(condition_1, m[identifier])

        if data is not None:
            returndata.update({identifier: data})
            log.log('Check condition 1 Succesful for ' + identifier)
        else:
            log.log('NO data in condition 1 for ' + identifier, 'Error')

    del condition_1

    # Define Condition Set 2
    # add filtered engineering values of mnemonics given in list mnemonic_cond_2
    #
    # Pleas Note:
    # under normal use following line should be added:
    # cond.equal(m['IGDP_IT_MIR_SW_STATUS'), 'DETECTOR_READY'),      \
    # cond.greater(m['SE_ZIMIRFPEA'], 0.5), \

    con_set_2 = [
        cond.equal(m['IGDP_IT_MIR_IC_STATUS'], 'DETECTOR_READY'),
        cond.equal(m['IGDP_IT_MIR_IC_STATUS'], 'DETECTOR_READY')]
    condition_2 = cond.condition(con_set_2)

    for identifier in mn.mnemonic_cond_2:
        data = extract_data.extract_data(condition_2, m[identifier])

        if data is not None:
            returndata.update({identifier: data})
            log.log('Check condition 2 Succesful for ' + identifier)
        else:
            log.log('NO data in condition 2 for ' + identifier, 'Error')

    del condition_2

    return returndata
