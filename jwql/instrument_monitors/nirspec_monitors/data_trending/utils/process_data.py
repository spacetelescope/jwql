"""This module holds functions for miri data trending

All functions in this module are tailored for the miri datatrending application.
Detailed descriptions are given for every function individually.

-------
    - Daniel Kühbacher

Use
---

Dependencies
------------
MIRI_trend_requestsDRAFT1900201.docx

References
----------

Notes
-----

"""

import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.condition as cond
import statistics
import sqlite3
import warnings
import numpy as np
from collections import defaultdict


def extract_data(condition, mnemonic):
    '''Function extracts data from given mnemmonic at a given condition
    Parameters
    ----------
    condition : object
        conditon object that holds one or more subconditions
    mnemonic : AstropyTable
        holds single table with mnemonic data
    Return
    ------
    temp : list  or None
        holds data that applies to given condition
    '''
    temp = []

    #look for all values that fit to the given conditions
    for element in mnemonic:
        if condition.state(float(element['time'])):
            temp.append(float(element['value']))

    #return temp is one ore more values fit to the condition
    #return None if no applicable data was found
    if len(temp) > 0:
        return temp
    else:
        return None

def lamp_distinction(caa_flag, lamp_sel, lamp_curr, lamp_volt):
    """Distincts over all calibration lamps and returns representative current means
        each
    Parameters
    ----------
    """

    #initilize empty dict
    lamp_values = defaultdict(list)

    for index, flag in enumerate(caa_flag):

        if flag['value'] == 'ON':

            #initialize lamp value to default
            current_lamp = "default"

            #find current lamp value
            for lamp in lamp_sel:
                if lamp['time'] <= flag['time']:
                    current_lamp = lamp['value']

            if (current_lamp == 'NO_LAMP') or (current_lamp == 'DUMMY'):
                continue

            #define interval of retrieval:
            try:
                start_time = flag['time']

                i = 1
                if caa_flag[index+i]['value'] == 'OFF':
                    end_time = caa_flag[index+1]['time']
                else:
                    i += 1

            except IndexError:
                break

            #append and evaluate current and voltage values
            temp_curr = []
            temp_volt = []

            for curr in lamp_curr:
                if curr['time'] >= start_time:
                    if curr['time'] < end_time:
                        temp_curr.append(float(curr['value']))
                    else:
                        break

            for volt in lamp_volt:
                if volt['time'] >= start_time :
                    if volt['time'] < end_time:
                        temp_volt.append(float(volt['value']))
                    else:
                        break

            lamp_data = []
            #append current values
            lamp_data.append(start_time)
            lamp_data.append(end_time)
            lamp_data.append(len(temp_curr))
            lamp_data.append(statistics.mean(temp_curr))
            lamp_data.append(statistics.stdev(temp_curr))
            #append voltage values
            lamp_data.append(len(temp_volt))
            lamp_data.append(statistics.mean(temp_volt))
            lamp_data.append(statistics.stdev(temp_volt))

            lamp_values[current_lamp].append(( lamp_data ))

    return lamp_values

def once_a_day_routine(mnemonic_data):
    '''Proposed routine for processing a 15min data file once a day
    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with correspining identifier as key
    Return
    ------
    data_cond_1 : dict
        holds extracted data with condition 1 applied
    data_cond_2 : dict
        holds extracted data with condition 1 applied
    data_cond_3 : dict
        holds extracted data with condition 1 applied
    '''

    #abbreviate attribute
    m = mnemonic_data
    return_data = dict()

    ###########################################################################
    con_set_1 = [                                                           \
    cond.unequal(m.mnemonic('INRSD_EXP_STAT'),'STARTED')]
    #setup condition
    condition_1 = cond.condition(con_set_1)
    data_cond_1 = dict()

    #add filtered engineering values of mnemonics given in list mnemonic_cond_2
    #to dictitonary
    for identifier in mn.mnemonic_cond_1:
        data = extract_data(condition_1, m.mnemonic(identifier))
        if data != None:
            return_data.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))
    del condition_1

    ###########################################################################
    con_set_2 = [                                                           \
    cond.equal(m.mnemonic('INRSH_LAMP_SEL'), 'NO_LAMP')]
    #setup condition
    condition_2 = cond.condition(con_set_2)
    data_cond_2 = dict()

    #add filtered engineering values of mnemonics given in list mnemonic_cond_2
    #to dictitonary
    for identifier in mn.mnemonic_cond_2:
        data = extract_data(condition_2, m.mnemonic(identifier))
        if data != None:
            return_data.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))
    del condition_2

    ###########################################################################
    con_set_3 = [                                                           \
    cond.unequal(m.mnemonic('INRSM_MOVE_STAT'), 'STARTED')]
    #setup condition
    condition_3 = cond.condition(con_set_3)
    data_cond_3 = dict()

    #add filtered engineering values of mnemonics given in list mnemonic_cond_2
    #to dictitonary
    for identifier in mn.mnemonic_cond_3:
        data = extract_data(condition_3, m.mnemonic(identifier))
        if data != None:
            return_data.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))
    del condition_3

    return return_data


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

    #abbreviate attribute
    m = mnemonic_data

    ###########################################################################
    con_set_ft_10 = [
    cond.equal(m.mnemonic('ICTM_RT_FILTER'), 10, stringval=False)]
    #setup condition
    condition_ft_10 = cond.condition(con_set_ft_10)
    data_cond_ft_10 = dict()

    #add filtered engineering values of mnemonics given in list mnemonic_cond_1
    #to dictitonary
    for identifier in mn.mnemonic_ft10:
        data = extract_data(condition_ft_10, m.mnemonic(identifier))
        if data != None:
            data_cond_ft_10.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))
    del condition_ft_10

    ##########################################################################
    con_set_caa = [                                                           \
    cond.equal(m.mnemonic('INRSH_CAA_PWRF_ST'), 'ON')]
    #setup condition
    condition_caa = cond.condition(con_set_caa)

    data_cond_caa = dict()

    #add filtered engineering values of mnemonics given in list mnemonic_cond_2
    #to dictitonary
    for identifier in mn.mnemonic_caa:
        data = extract_data(condition_caa, m.mnemonic(identifier))

        if data != None:
            data_cond_caa.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))

    del condition_caa

    ##########################################################################
    '''
    data_cond_5 = defaultdict(list)

    con_manualrpt = [
    cond.equal(m.mnemonic('INRSI_MANUALRPT_ST'), 'STARTED')]
    #setup condition
    condition_manualrpt = cond.condition(con_manualrpt)

    for identifier in mn.mnemonic_cond_5:
        data = extract_data(condition_manualrpt, m.mnemonic(identifier))

        if data != None:
            data_cond_5[identifier].append(data)
        else:
            print("no data for {}, MANUALRPT".format(identifier))
    del condition_manualrpt

    con_move = [
    cond.equal(m.mnemonic('INRSI_FWA_MOVE_ST'), 'STARTED')]
    #setup condition
    condition_move = cond.condition(con_move)

    for identifier in mn.mnemonic_cond_5:
        data = extract_data(condition_move, m.mnemonic(identifier))

        if data != None:
            data_cond_5[identifier].append(data)
        else:
            print("no data for {}, FWA/GWA MOVE".format(identifier))

    print(data_cond_5)
    del condition_move
    '''
    ###########################################################################
    data_lamps = lamp_distinction(  m.mnemonic('INRSI_CAA_ON_FLAG'),
                                    m.mnemonic('INRSH_LAMP_SEL'),
                                    m.mnemonic('INRSI_C_CAA_CURRENT'),
                                    m.mnemonic('INRSI_C_CAA_VOLTAGE') )
    print(data_lamps)

    return data_cond_ft_10, data_cond_caa, data_cond_5, data_lamps

if __name__ =='__main__':
    pass
