"""Functions that are used to extract data


-------
    - Daniel Kühbacher

Use
---


Dependencies
------------
    no external files needed

References
----------

Notes
-----

"""

import mnemonics as mn
import condition as cond
import statistics
import sqlite3
import warnings
from collections import defaultdict



def extract_data(condition, mnemonic):
    '''Function extracts data from given mnemmonic that applies to the given condition
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
            #developement purpose:
            #print("condition true: value= {}, time= {}".format(element['value'],element['time']))
            temp.append(float(element['value']))

    if len(temp) > 0:
        return temp
    else:
        return None

def extract_filterpos(condition, nominals, ratio_mnem, pos_mnem):
    '''Extracts to filterpositions corresponding ratio values
    Parameters
    ----------
    condition : object
        conditon object that holds one or more subconditions
    ratio_mem : AstropyTable
        holds ratio values of one specific mnemonic
    pos_mem : AstropyTable
        holds pos values of one specific mnemonic
    Return
    ------
    pos_values : dict
        holds ratio values and times with corresponding pos label
    '''

    pos_values = defaultdict(list)

    #do for every position in mnemonic
    for pos in pos_mnem:

        if pos['value'] != "UNKNOWN":

            interval = condition.get_interval(pos['time'])

            if interval is not None:
                cur_pos_time = pos['time']
                filtername = pos['value']

                for ratio in ratio_mnem:

                    if (ratio['time'] >= cur_pos_time) and \
                        (abs(float(ratio['value']) - nominals.get(pos['value'])) < 10):

                        if (ratio['time'] > interval[0]) and (ratio['time'] < interval[1]):
                            pos_values[pos['value']].append(( ratio['time'], ratio['value']))
                        break
        else:
            warnings.warn("Position for {} is UNKNOWN".format(pos['value']))
    return pos_values


def once_a_day_routine(mnemonic_data):

    #abbreviate attribute
    m = mnemonic_data

    #########################################################################
    con_set_1 = [                                               \
    cond.equal(m.mnemonic('IMIR_HK_IMG_CAL_LOOP'),'OFF'),       \
    cond.equal(m.mnemonic('IMIR_HK_IFU_CAL_LOOP'),'OFF'),       \
    cond.equal(m.mnemonic('IMIR_HK_POM_LOOP'),'OFF'),           \
    cond.smaller(m.mnemonic('IMIR_HK_ICE_SEC_VOLT1'),1.0),      \
    cond.greater(m.mnemonic('SE_ZIMIRICEA'),0.2)]
    #setup condition
    condition_1 = cond.condition(con_set_1)

    data_cond_1 = dict()

    for identifier in mn.mnemonic_cond_1:
        data = extract_data(condition_1, m.mnemonic(identifier))

        if data != None:
            data_cond_1.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))

    del condition_1

    ##########################################################################
    con_set_2 = [                                                           \
    cond.greater(m.mnemonic('SE_ZIMIRFPEA'), 0.5),                           \
    cond.equal(m.mnemonic('IGDP_IT_MIR_IC_STATUS'), 'DETECTOR_READY'),       \
    cond.equal(m.mnemonic('IGDP_IT_MIR_LW_STATUS'), 'DETECTOR_READY')]
    #setup condition
    condition_2 = cond.condition(con_set_2)


    data_cond_2 = dict()

    for identifier in mn.mnemonic_cond_2:
        data = extract_data(condition_2, m.mnemonic(identifier))

        if data != None:
            data_cond_2.update( {identifier:data} )
        else:
            print("no data for {}".format(identifier))

    del condition_2

    return data_cond_1, data_cond_2

#in developement
def whole_day_routine(mnemonic_data):

    #abbreviate attribute
    m = mnemonic_data

    #########################################################################
    con_set_3 = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_ICE_SEC_VOLT1'), 25.0)]
    #setup condition
    condition_3 = cond.condition(con_set_3)

    data_cond_3 = dict()

    for identifier in mn.mnemonic_cond_3:
        data = extract_data(condition_3, m.mnemonic(identifier))

        if data != None:
            data_cond_3.update({identifier:data})
        else:
            print("no data for {}".format(identifier))

    del condition_3

    #########################################################################
    con_set_FW = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_FW_POS_VOLT'),250.0)]
    #setup condition
    condition_FW = cond.condition(con_set_FW)
    FW_volt = extract_data(condition_FW, m.mnemonic('IMIR_HK_FW_POS_VOLT'))

    del condition_FW

    con_set_GW14 = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_GW14_POS_VOLT'),250.0)]
    #setup condition
    condition_GW14 = cond.condition(con_set_GW14)
    GW14_volt = extract_data(condition_GW14, m.mnemonic('IMIR_HK_GW14_POS_VOLT'))

    del condition_GW14

    con_set_GW23 = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_GW23_POS_VOLT'),250.0)]
    #setup condition
    condition_GW23 = cond.condition(con_set_GW23)
    GW23_volt = extract_data(condition_GW23, m.mnemonic('IMIR_HK_GW23_POS_VOLT'))

    del condition_GW23

    con_set_CCC = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_CCC_POS_VOLT'),250.0)]
    #setup condition
    condition_CCC = cond.condition(con_set_CCC)
    CCC_volt = extract_data(condition_CCC, m.mnemonic('IMIR_HK_CCC_POS_VOLT'))

    del condition_CCC

    return data_cond_3, FW_volt , GW14_volt, GW23_volt, CCC_volt



def wheelpos_routine(mnemonic_data):

    #abbreviate attribute
    m = mnemonic_data

    con_set_FW = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_FW_POS_VOLT'),250.0)]
    #setup condition
    condition_FW = cond.condition(con_set_FW)
    FW = extract_filterpos(condition_FW, mn.fw_nominals, \
        m.mnemonic('IMIR_HK_FW_POS_RATIO'), m.mnemonic('IMIR_HK_FW_CUR_POS'))

    del condition_FW

    con_set_GW14 = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_GW14_POS_VOLT'),250.0)]
    #setup condition
    condition_GW14 = cond.condition(con_set_GW14)
    GW14 = extract_filterpos(condition_GW14, mn.gw14_nominals, \
        m.mnemonic('IMIR_HK_GW14_POS_RATIO'), m.mnemonic('IMIR_HK_GW14_CUR_POS'))

    del condition_GW14

    con_set_GW23 = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_FW_POS_VOLT'),250.0)]
    #setup condition
    condition_GW23 = cond.condition(con_set_GW23)
    GW23 = extract_filterpos(condition_GW23, mn.gw23_nominals, \
        m.mnemonic('IMIR_HK_GW23_POS_RATIO'), m.mnemonic('IMIR_HK_GW23_CUR_POS'))

    del condition_GW23

    con_set_CCC = [                                               \
    cond.greater(m.mnemonic('IMIR_HK_CCC_POS_VOLT'),250.0)]
    #setup condition
    condition_CCC = cond.condition(con_set_CCC)
    CCC = extract_filterpos(condition_CCC, mn.ccc_nominals, \
        m.mnemonic('IMIR_HK_CCC_POS_RATIO'), m.mnemonic('IMIR_HK_CCC_CUR_POS'))

    del condition_CCC

    return FW, GW14, GW23, CCC

def extract_filterpos_obsolete(condition, ratio_mnem, pos_mnem):
    '''Extracts to filterpositions corresponding ratio values
    Parameters
    ----------
    condition : object
        conditon object that holds one or more subconditions
    ratio_mem : AstropyTable
        holds ratio values of one specific mnemonic
    pos_mem : AstropyTable
        holds pos values of one specific mnemonic
    Return
    ------
    pos_values : dict
        holds ratio values and times with corresponding pos label
    '''

    pos_values = defaultdict(list)

    #do for every position in mnemonic
    for pos in pos_mnem:

        interval = condition.get_interval(pos['time'])

        if interval is not None:
            cur_pos_time = pos['time']
            filtername = pos['value']

            for ratio in ratio_mnem:

                if (ratio['time'] == cur_pos_time) and (abs(float(ratio['value'])) > 0.1):
                    if (ratio['time'] > interval[0]) and (ratio['time'] < interval[1]):
                        pos_values[pos['value']].append( ( ratio['time'], ratio['value']) )
                        break
    return pos_values


if __name__ =='__main__':
    pass
