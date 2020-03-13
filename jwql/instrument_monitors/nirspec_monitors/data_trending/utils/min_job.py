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

    The file nirspec_database.db in the directory jwql/jwql/database/ must exist.

References
----------
    The code was developed in reference to the information provided in:
    ‘JWQL_NIRSpec_Inputs_V8.xlsx’

Notes
-----

    For further information please contact Brian O'Sullivan
"""
import statistics

import sys

import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.condition as cond
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.extract_data as extract_data
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.log_error_and_file as log_error_and_file
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.sql_interface as sql


def process_15min(conn, m_raw_data):
    '''Parse queried data, process data within and put to DB

    Parameters
    ----------
    conn : DBobject
        Connection object to auxiliary database
    path : str
        defines file to read
    '''

    # Define new log instance
    log = log_error_and_file.Log('PROCESS')
    log.info('process data 15 min')

    # Process and Filter the downloaded mnmemonics
    processed_data = once_a_day_routine(m_raw_data)

    # Sql save the mnemonics
    log.info('SQL data 15 min')

    for key, value in processed_data.items():
        try:
            m = m_raw_data[key]

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

    for identifier in mn.mnemSet_15min:

        m = m_raw_data[identifier]

        temp = []

        # look for all values that fit to the given conditions
        for element in m:
            temp.append(float(element['value']))

        # return None if no applicable data was found
        if len(temp) > 2:
            length = len(temp)
            mean = statistics.mean(temp)
            deviation = statistics.stdev(temp)

            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, identifier, dataset)
        elif len(temp) == 2:
            dataset = (float(element['time']), float(element['time']), 1, temp[0], 0)
            sql.add_data(conn, identifier, dataset)
        else:
            print('No data for {}'.format(identifier))
            print(temp)

        del temp

def once_a_day_routine(mnemonic_data):
    '''Routine for processing a 15min data file once a day
    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with correspining identifier as key
    Return
    ------
    return_data : dict
        Holds extracted data with applied conditions
    '''

    m = mnemonic_data
    return_data = dict()
    log = log_error_and_file.Log('PROCESS')

    # Define Condition Set 1
    # add filtered engineering values of mnemonics given in list mnemonic_cond_1
    con_set_1 = [ \
        cond.unequal(m['INRSD_EXP_STAT'], 'STARTED')]
    condition_1 = cond.condition(con_set_1)

    for identifier in mn.mnemonic_cond_1:
        data = extract_data.extract_data(condition_1, m[identifier])
        if data != None:
            return_data.update({identifier: data})
            log.log('Check condition 1 Succesful for ' + identifier)
        else:
            log.log('NO data in condition 1 for ' + identifier, 'Error')
    del condition_1

    # Define Condition Set 2
    # add filtered engineering values of mnemonics given in list mnemonic_cond_2
    con_set_2 = [ \
        cond.equal(m['INRSH_LAMP_SEL'], 'NO_LAMP')]
    condition_2 = cond.condition(con_set_2)

    for identifier in mn.mnemonic_cond_2:
        data = extract_data.extract_data(condition_2, m[identifier])
        if data != None:
            return_data.update({identifier: data})
            log.log('Check condition 2 Succesful for ' + identifier)
        else:
            log.log('NO data in condition 2 for ' + identifier, 'Error')
    del condition_2

    # Define Condition Set 3
    # add filtered engineering values of mnemonics given in list mnemonic_cond_3
    con_set_3 = [ \
        cond.unequal(m['INRSM_MOVE_STAT'], 'STARTED')]
    condition_3 = cond.condition(con_set_3)

    for identifier in mn.mnemonic_cond_3:
        data = extract_data.extract_data(condition_3, m[identifier])
        if data != None:
            return_data.update({identifier: data})
            log.log('Check condition 3 Succesful for ' + identifier)
        else:
            log.log('NO data in condition 3 for ' + identifier, 'Error')
    del condition_3

    return return_data

