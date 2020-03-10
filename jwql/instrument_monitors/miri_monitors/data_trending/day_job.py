"""day_job.py

    Process the data generated for a whoul day

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

import jwql.instrument_monitors.miri_monitors.data_trending.utils.condition as cond
import jwql.instrument_monitors.miri_monitors.data_trending.utils.extract_data as extract_data
import jwql.instrument_monitors.miri_monitors.data_trending.utils.log_error_and_file as log_error_and_file
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql


def process_day(conn, m_raw_data):
    '''Parse CSV file, process data within and put to DB

    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines file to read
    '''

    log = log_error_and_file.Log('PROCESS')
    log.info('process data day')

    cond3 = whole_day_routine(m_raw_data)
    FW, GW14, GW23, CCC = wheelpos_routine(m_raw_data)

    log.info('SQL data day')

    # put data from con3 to database
    for key, value in cond3.items():

        m = m_raw_data[key]

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

    #########################################################################################

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
            data_GW23 = GW23[pos]

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


def whole_day_routine(mnemonic_data):
    '''Proposed routine for processing data representing a whole day
    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with correspining identifier as key
    Return
    ------
    data_cond_3 : dict
        holds extracted data with condition 3 applied
    FW_volt : list
        extracted data for IMIR_HK_FW_POS_VOLT
    GW14_volt : list
        extracted data for IMIR_HK_GW14_POS_VOLT
    GW23_volt : list
        extracted data for IMIR_HK_GW23_POS_VOLT
    CCC_volt : list
        extracted data for IMIR_HK_CCC_POS_VOLT
    '''
    log = log_error_and_file.Log('Process')

    # abbreviate attribute
    m = mnemonic_data
    returndata = dict()

    #########################################################################
    con_set_3 = [ \
        cond.greater(m['IMIR_HK_ICE_SEC_VOLT1'], 25.0)]
    # setup condition
    condition_3 = cond.condition(con_set_3)

    # add filtered engineering values of mnemonics given in list mnemonic_cond_3
    # to dictitonary
    for identifier in mn.mnemonic_cond_3:
        data = extract_data.extract_data(condition_3, m[identifier])

        if data != None:
            returndata.update({identifier: data})
            log.log('Check condition 3 Succesful for ' + identifier)
        else:
            log.log('NO data in condition 3 for ' + identifier, 'Error')

    del condition_3

    #########################################################################
    # extract data for IMIR_HK_FW_POS_VOLT under given condition
    con_set_FW = [ \
        cond.greater(m['IMIR_HK_FW_POS_VOLT'], 250.0)]
    # setup condition
    condition_FW = cond.condition(con_set_FW)
    FW_volt = extract_data.extract_data(condition_FW, m['IMIR_HK_FW_POS_VOLT'])
    returndata.update({'IMIR_HK_FW_POS_VOLT': FW_volt})
    del condition_FW
    log.log('Check condition IMIR_HK_FW_POS_VOLT > 250')

    # extract data for IMIR_HK_GW14_POS_VOLT under given condition
    con_set_GW14 = [ \
        cond.greater(m['IMIR_HK_GW14_POS_VOLT'], 250.0)]
    # setup condition
    condition_GW14 = cond.condition(con_set_GW14)
    GW14_volt = extract_data.extract_data(condition_GW14, m['IMIR_HK_GW14_POS_VOLT'])
    returndata.update({'IMIR_HK_GW14_POS_VOLT': GW14_volt})
    del condition_GW14
    log.log('Check condition IMIR_HK_GW14_POS_VOLT > 250')

    # extract data for IMIR_HK_GW23_POS_VOLT under given condition
    con_set_GW23 = [ \
        cond.greater(m['IMIR_HK_GW23_POS_VOLT'], 250.0)]
    # setup condition
    condition_GW23 = cond.condition(con_set_GW23)
    GW23_volt = extract_data.extract_data(condition_GW23, m['IMIR_HK_GW23_POS_VOLT'])
    returndata.update({'IMIR_HK_GW23_POS_VOLT': GW23_volt})
    del condition_GW23
    log.log('Check condition IMIR_HK_GW23_POS_VOLT > 250')

    # extract data for IMIR_HK_CCC_POS_VOLT under given condition
    con_set_CCC = [ \
        cond.greater(m['IMIR_HK_CCC_POS_VOLT'], 250.0)]
    # setup condition
    condition_CCC = cond.condition(con_set_CCC)
    CCC_volt = extract_data.extract_data(condition_CCC, m['IMIR_HK_CCC_POS_VOLT'])
    returndata.update({'IMIR_HK_CCC_POS_VOLT': CCC_volt})
    del condition_CCC
    log.log('Check condition IMIR_HK_CCC_POS_VOLT > 250')

    return returndata


def wheelpos_routine(mnemonic_data):
    '''Proposed routine for positionsensors each day
    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with correspining identifier as key
    Return
    ------
    FW : dict
        holds FW ratio values and times with corresponding positionlabel as key
    GW14 : dict
        holds GW14 ratio values and times with corresponding positionlabel as key
    GW23 : dict
        holds GW23 ratio values and times with corresponding positionlabel as key
    CCC : dict
        holds CCC ratio values and times with corresponding positionlabel as key
    '''

    log = log_error_and_file.Log('PROCESS')

    # abbreviate attribute
    m = mnemonic_data

    log.log('extract IMIR_HK_FW filterpositions')
    FW = extract_data.extract_filterpos(mn.fw_nominals, \
                                        m['IMIR_HK_FW_POS_RATIO'], m['IMIR_HK_FW_CUR_POS'])

    log.log('extract IMIR_HK_GW14 filterpositions')
    GW14 = extract_data.extract_filterpos(mn.gw14_nominals, \
                                          m['IMIR_HK_GW14_POS_RATIO'], m['IMIR_HK_GW14_CUR_POS'])

    log.log('extract IMIR_HK_GW23 filterpositions')
    GW23 = extract_data.extract_filterpos(mn.gw23_nominals, \
                                          m['IMIR_HK_GW23_POS_RATIO'], m['IMIR_HK_GW23_CUR_POS'])

    log.log('extract IMIR_HK_CCC filterpositions')
    CCC = extract_data.extract_filterpos(mn.ccc_nominals, \
                                         m['IMIR_HK_CCC_POS_RATIO'], m['IMIR_HK_CCC_CUR_POS'])

    return FW, GW14, GW23, CCC
