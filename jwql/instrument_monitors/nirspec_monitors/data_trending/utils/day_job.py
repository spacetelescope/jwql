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
from collections import defaultdict

import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.condition as cond
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.extract_data as extract_data
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.log_error_and_file as log_error_and_file
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.sql_interface as sql


def process_day(conn, m_raw_data):
    '''Parse queried data, process data within and put to DB
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : list
        list containing querried data
    '''

    # Define new log instance
    log = log_error_and_file.Log('PROCESS')
    log.info('process data day')

    # Process and Filter Data
    # for all mnemonics
    # and for all wheel positions
    return_data, lamp_data = whole_day_routine(m_raw_data)
    FW, GWX, GWY = wheelpos_routine(m_raw_data)

    # put all data to a database that uses a condition
    for key, value in return_data.items():
        m = m_raw_data[key]
        length = len(value)
        mean = statistics.mean(value)
        deviation = statistics.stdev(value)
        dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
        sql.add_data(conn, key, dataset)

    # add rest of the data to database -> no conditions applied
    for identifier in mn.mnemSet_day:
        m = m_raw_data[identifier]
        temp = []
        # look for all values that fit to the given conditions
        for element in m:
            temp.append(float(element['value']))
        # return None if no applicable data was found
        if len(temp) >= 2:
            length = len(temp)
            mean = statistics.mean(temp)
            deviation = statistics.stdev(temp)

        elif len(temp) == 1:
            length =1
            mean = temp[0]
            deviation = 0

        else:
            log.log('No data for {}'.format(identifier), 'error')
        del temp

    # add lamp data to database -> distiction over lamps
    for key, values in lamp_data.items():
        for data in values:
            dataset_volt = (data[0], data[1], data[5], data[6], data[7])
            dataset_curr = (data[0], data[1], data[2], data[3], data[4])
            sql.add_data(conn, 'LAMP_{}_VOLT'.format(key), dataset_volt)
            sql.add_data(conn, 'LAMP_{}_CURR'.format(key), dataset_curr)

    # add wheeldata to database
    for key, values in FW.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_FWA_POSITION_{}'.format(key), data)

    for key, values in GWX.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_GWA_X_POSITION_{}'.format(key), data)

    for key, values in GWY.items():
        for data in values:
            sql.add_wheel_data(conn, 'INRSI_C_GWA_Y_POSITION_{}'.format(key), data)



def whole_day_routine(mnemonic_data):
    '''Proposed routine for processing a 15min data file once a day

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
    '''

    log = log_error_and_file.Log('Process')

    # abbreviate attribute
    m = mnemonic_data
    return_data = dict()

    # Define Condition Set ft_10
    # add filtered engineering values of mnemonics given in list mnemonic_cond_ft10
    con_set_ft_10 = [
        cond.equal(m['ICTM_RT_FILTER'], 10, stringval=False)]
    condition_ft_10 = cond.condition(con_set_ft_10)

    for identifier in mn.mnemonic_ft10:
        data = extract_data.extract_data(condition_ft_10, m[identifier])
        if data != None:
            return_data.update({identifier: data})
            log.log('Check condition ft10 Succesful for ' + identifier)
        else:
            log.log('NO data in condition ft10 for ' + identifier, 'Error')
    del condition_ft_10

    # Define Condition Set caa
    # add filtered engineering values of mnemonics given in list mnemonic_cond_caa
    con_set_caa = [ \
        cond.equal(m['INRSH_CAA_PWRF_ST'], 'ON')]
    condition_caa = cond.condition(con_set_caa)

    for identifier in mn.mnemonic_caa:
        data = extract_data.extract_data(condition_caa, m[identifier])

        if data != None:
            return_data.update({identifier: data})
            log.log('Check condition caa Succesful for ' + identifier)
        else:
            log.log('NO data in condition ft10 for ' + identifier, 'Error')

    del condition_caa

    # Define Labs data
    data_lamps = lamp_distinction(m['INRSI_CAA_ON_FLAG'],
                                  m['INRSH_LAMP_SEL'],
                                  m['INRSI_C_CAA_CURRENT'],
                                  m['INRSI_C_CAA_VOLTAGE'])

    return return_data, data_lamps


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


    # abbreviate attribute
    m = mnemonic_data

    FW = extract_filterpos(m['INRSI_FWA_MOVE_ST'],
                           m['INRSI_FWA_MECH_POS'],
                           m['INRSI_C_FWA_POSITION'])

    GWX = extract_filterpos(m['INRSI_GWA_MOVE_ST'],
                            m['INRSI_GWA_MECH_POS'],
                            m['INRSI_C_GWA_X_POSITION'])

    GWY = extract_filterpos(m['INRSI_GWA_MOVE_ST'],
                            m['INRSI_GWA_MECH_POS'],
                            m['INRSI_C_GWA_Y_POSITION'])

    return FW, GWX, GWY

def lamp_distinction(caa_flag, lamp_sel, lamp_curr, lamp_volt):
    """Distincts over all calibration lamps and returns representative current means
        each
    Parameters
    ----------
    """

    # initilize empty dict
    lamp_values = defaultdict(list)

    for index, flag in enumerate(caa_flag):

        if flag['value'] == 'ON':

            # initialize lamp value to default
            current_lamp = "default"

            # find current lamp value
            for lamp in lamp_sel:
                if lamp['time'] <= flag['time']:
                    current_lamp = lamp['value']

            # go to next Value if dummy lamps are activated
            if (current_lamp == 'NO_LAMP') or (current_lamp == 'DUMMY'):
                continue

            # define on_time of current lamp
            try:
                start_time = flag['time']

                i = 1
                if caa_flag[index + i]['value'] == 'OFF':
                    end_time = caa_flag[index + 1]['time']
                else:
                    i += 1

            except IndexError:
                break

            # append and evaluate current and voltage values
            temp_curr = []
            temp_volt = []

            # append current values to list
            for curr in lamp_curr:
                if curr['time'] >= start_time:
                    if curr['time'] < end_time:
                        temp_curr.append(float(curr['value']))
                    else:
                        break
            # append voltage values to list
            for volt in lamp_volt:
                if volt['time'] >= start_time:
                    if volt['time'] < end_time:
                        temp_volt.append(float(volt['value']))
                    else:
                        break

            lamp_data = []
            # append current values
            lamp_data.append(start_time)
            lamp_data.append(end_time)
            lamp_data.append(len(temp_curr))
            lamp_data.append(statistics.mean(temp_curr))
            lamp_data.append(statistics.stdev(temp_curr))
            # append voltage values
            lamp_data.append(len(temp_volt))
            lamp_data.append(statistics.mean(temp_volt))
            lamp_data.append(statistics.stdev(temp_volt))
            lamp_values[current_lamp].append((lamp_data))

    return lamp_values

def extract_filterpos(move_stat, wheel_pos, wheel_val):
    '''Extracts ratio values which correspond to given position values and their
       proposed nominals
    Parameters
    ----------
    condition : object
        conditon object that holds one or more subconditions
    nominals : dict
        holds nominal values for all wheel positions
    ratio_mem : AstropyTable
        holds ratio values of one specific mnemonic
    pos_mem : AstropyTable
        holds pos values of one specific mnemonic
    Return
    ------
    pos_values : dict
        holds ratio values and times with corresponding positionlabel as key
    '''
    log = log_error_and_file.Log('PROCESS')

    # initilize empty dict for assigned ratio values
    pos_values = defaultdict(list)

    for index, stat in enumerate(move_stat):

        # raise warning if position is UNKNOWN
        if stat['value'] == "SUCCESS":

            # initialize lamp value to default
            current_pos = "default"
            pos_val = 0
            pos_time = 0

            # Evaluate current position
            for pos in wheel_pos:
                if pos['time'] <= stat['time']:
                    current_pos = pos['value']
                if pos['time'] > stat['time']:
                    break

            # Evaluate corresponding value
            for val in wheel_val:
                if val['time'] <= stat['time']:
                    pos_val = val['value']
                    pos_time = val['time']
                if val['time'] > stat['time']:
                    break

            log.log('Position ' + str(current_pos) +' value: '+ str(pos_val) + ' at ' + str(pos_time))

            if current_pos != 'default':
                pos_values[current_pos].append((pos_time, pos_val))
        else:
            continue

    return pos_values