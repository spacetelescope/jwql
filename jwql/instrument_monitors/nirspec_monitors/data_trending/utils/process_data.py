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

    ##########################################################################
    con_set_4 = [                                                           \
    cond.equal(m.mnemonic('INRSI_CAA_ON_FLAG'), 'ON'),                      \
    cond.unequal(m.mnemonic('INRSH_LAMP_SEL'), 'NO_LAMP')]
    #setup condition
    condition_4 = cond.condition(con_set_4)
    data_cond_4 = dict()

    #add filtered engineering values of mnemonics given in list mnemonic_cond_2
    #to dictitonary
    for identifier in mn.mnemonic_cond_4:
        data = extract_data(condition_4, m.mnemonic(identifier))
        if data != None:
            data_cond_4.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))

    del condition_4

    ###########################################################################
    con_set_ft_10 = [
    cond.equal(m.mnemonic('ICTM_RT_FILTER'),'10')]
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
    cond.equal(m.mnemonic('INRS_CAA_PWRF_ST'), 'ON')]
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
    con_manualrpt = [
    cond.equal(m.mnemonic('INRSI_MANUALRPT_ST'), 'STARTED')]
    #setup condition
    condition_manualrpt = cond.condition(con_manualrpt)

    con_move = [
    cond.equal(m.mnemonic('INRSI_FWA_MOVE_ST'), 'STARTED')]
    #setup condition
    condition_move = cond.condition(con_move)

    data_cond_5 = dict()

    #add filtered engineering values of mnemonics given in list mnemonic_cond_2
    #to dictitonary
    for identifier in mn.mnemonic_cond_5:
        data1 = extract_data(condition_manualrpt, m.mnemonic(identifier))
        data2 = extract_data(condition_move, m.mnemonic(identifier))

        if data1 != None:
            data_cond_5.update( {identifier:data1} )
        elif data2 != None:
            data_cond_5.update( {identifier:data2} )
        else:
            print("no data for {}".format(identifier))

    del condition_manualrpt
    del condition_move

    return data_cond_4, data_cond_ft_10, data_cond_caa, data_cond_5

if __name__ =='__main__':
    pass
