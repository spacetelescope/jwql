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

import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.condition as cond
import warnings
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

    # look for all values that fit to the given conditions
    for element in mnemonic:
        if condition.state(float(element['time'])):
            temp.append(float(element['value']))

    # return temp is one ore more values fit to the condition
    # return None if no applicable data was found
    if len(temp) > 0:
        return temp
    else:
        return None


def extract_filterpos1(condition, nominals, ratio_mnem, pos_mnem):
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

    # initilize empty dict
    pos_values = defaultdict(list)

    # do for every position in mnemonic attribute
    for pos in pos_mnem:

        # raise warning if position is UNKNOWN
        if pos['value'] != "UNKNOWN":

            # request time interval where the current positon is in between
            interval = condition.get_interval(pos['time'])

            # get all ratio values in the interval

            # check if condition attribute for current positon is true
            if interval is not None:
                cur_pos_time = pos['time']

                for ratio in ratio_mnem:

                    # look for ratio values which are in the same time interval
                    # and differ a certain value (here 5mV) from the nominal
                    if (ratio['time'] >= cur_pos_time) and \
                        (abs(float(ratio['value']) - nominals.get(pos['value'])) < 5):

                        if (ratio['time'] > interval[0]) and (ratio['time'] < interval[1]):
                            pos_values[pos['value']].append((ratio['time'], ratio['value']))

        else:
            warnings.warn("UNKNOWN Position")
    return pos_values


def extract_filterpos(condition, nominals, ratio_mnem, pos_mnem):
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

    # initilize empty dict for assigned ratio values
    pos_values = defaultdict(list)

    for index, pos in enumerate(pos_mnem):

        # raise warning if position is UNKNOWN
        if pos['value'] != "UNKNOWN":

            # set up interval beween where the pos value was timed and the supply
            interval = condition.get_interval(pos['time'])

            if interval is None:
                continue
            else:
                interval[0] = pos['time']
                if pos_mnem[index+1]['time'] < interval[1]:
                    interval[1] = pos_mnem[index+1]['time']

            # empty list for pos values
            interval_ratios = []

            # get all ratio values in the interval
            for ratio in ratio_mnem:
                if (ratio['time'] >= interval[0]) and (ratio['time'] < interval[1]):
                    interval_ratios.append(ratio)
                elif ratio['time'] >= interval[1]:
                    break

            # check wheather pos values are in range of these checkvals
            window = 1
            found_value = False

            while found_value is False:
                for ratio in interval_ratios:
                    if (abs(float(ratio['value']) - nominals.get(pos['value'])) < window):
                        found_value = True
                        pos_values[pos['value']].append((ratio['time'], ratio['value']))
                        break

                window += 2

                if window > 10:
                    print('ratio error')
                    break

        else:
            warnings.warn("UNKNOWN Position")
    return pos_values


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
    data_cond_1 : dict
        holds extracted data with condition 2 applied
    '''

    # abbreviate attribute
    m = mnemonic_data
    returndata = dict()

    #########################################################################
    con_set_1 = [
    cond.equal(m.mnemonic('IMIR_HK_IMG_CAL_LOOP'), 'OFF'),
    cond.equal(m.mnemonic('IMIR_HK_IFU_CAL_LOOP'), 'OFF'),
    cond.equal(m.mnemonic('IMIR_HK_POM_LOOP'), 'OFF'),
    cond.smaller(m.mnemonic('IMIR_HK_ICE_SEC_VOLT1'), 1.0),
    cond.greater(m.mnemonic('SE_ZIMIRICEA'), 0.2)]
    # setup condition
    condition_1 = cond.condition(con_set_1)

    # add filtered engineering values of mnemonics given in list mnemonic_cond_1
    # to dictitonary
    for identifier in mn.mnemonic_cond_1:
        data = extract_data(condition_1, m.mnemonic(identifier))

        if data is not None:
            returndata.update({identifier: data})
        else:
            print("no data for {}".format(identifier))

    del condition_1

    ##########################################################################
    # under normal use following line should be added:
    # cond.equal(m.mnemonic('IGDP_IT_MIR_SW_STATUS'), 'DETECTOR_READY'),      \
    # SW was missing in the trainigs data so I could not use it for a condition.
    con_set_2 = [
    cond.greater(m.mnemonic('SE_ZIMIRFPEA'), 0.5),
    cond.equal(m.mnemonic('IGDP_IT_MIR_IC_STATUS'), 'DETECTOR_READY'),
    cond.equal(m.mnemonic('IGDP_IT_MIR_LW_STATUS'), 'DETECTOR_READY')]
    # setup condition
    condition_2 = cond.condition(con_set_2)

    # add filtered engineering values of mnemonics given in list mnemonic_cond_2
    # to dictitonary
    for identifier in mn.mnemonic_cond_2:
        data = extract_data(condition_2, m.mnemonic(identifier))

        if data is not None:
            returndata.update({identifier: data})
        else:
            print("no data for {}".format(identifier))

    del condition_2

    return returndata


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

    # abbreviate attribute
    m = mnemonic_data
    returndata = dict()

    #########################################################################
    con_set_3 = [
    cond.greater(m.mnemonic('IMIR_HK_ICE_SEC_VOLT1'), 25.0)]
    # setup condition
    condition_3 = cond.condition(con_set_3)

    # add filtered engineering values of mnemonics given in list mnemonic_cond_3
    # to dictitonary
    for identifier in mn.mnemonic_cond_3:
        data = extract_data(condition_3, m.mnemonic(identifier))

        if data is not None:
            returndata.update({identifier: data})
        else:
            print("no data for {}".format(identifier))

    del condition_3

    #########################################################################
    # extract data for IMIR_HK_FW_POS_VOLT under given condition
    con_set_FW = [
    cond.greater(m.mnemonic('IMIR_HK_FW_POS_VOLT'), 250.0)]
    # setup condition
    condition_FW = cond.condition(con_set_FW)
    FW_volt = extract_data(condition_FW, m.mnemonic('IMIR_HK_FW_POS_VOLT'))
    returndata.update({'IMIR_HK_FW_POS_VOLT':FW_volt})
    del condition_FW

    # extract data for IMIR_HK_GW14_POS_VOLT under given condition
    con_set_GW14 = [
    cond.greater(m.mnemonic('IMIR_HK_GW14_POS_VOLT'), 250.0)]
    # setup condition
    condition_GW14 = cond.condition(con_set_GW14)
    GW14_volt = extract_data(condition_GW14, m.mnemonic('IMIR_HK_GW14_POS_VOLT'))
    returndata.update({'IMIR_HK_GW14_POS_VOLT': GW14_volt})
    del condition_GW14

    # extract data for IMIR_HK_GW23_POS_VOLT under given condition
    con_set_GW23 = [
    cond.greater(m.mnemonic('IMIR_HK_GW23_POS_VOLT'), 250.0)]
    # setup condition
    condition_GW23 = cond.condition(con_set_GW23)
    GW23_volt = extract_data(condition_GW23, m.mnemonic('IMIR_HK_GW23_POS_VOLT'))
    returndata.update({'IMIR_HK_GW23_POS_VOLT': GW23_volt})
    del condition_GW23

    # extract data for IMIR_HK_CCC_POS_VOLT under given condition
    con_set_CCC = [
    cond.greater(m.mnemonic('IMIR_HK_CCC_POS_VOLT'), 250.0)]
    # setup condition
    condition_CCC = cond.condition(con_set_CCC)
    CCC_volt = extract_data(condition_CCC, m.mnemonic('IMIR_HK_CCC_POS_VOLT'))
    returndata.update({'IMIR_HK_CCC_POS_VOLT': CCC_volt})
    del condition_CCC

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

    # abbreviate attribute
    m = mnemonic_data

    con_set_FW = [
    cond.greater(m.mnemonic('IMIR_HK_FW_POS_VOLT'), 250.0)]
    # setup condition
    condition_FW = cond.condition(con_set_FW)
    FW = extract_filterpos(condition_FW, mn.fw_nominals,
        m.mnemonic('IMIR_HK_FW_POS_RATIO'), m.mnemonic('IMIR_HK_FW_CUR_POS'))

    del condition_FW

    con_set_GW14 = [
    cond.greater(m.mnemonic('IMIR_HK_GW14_POS_VOLT'), 250.0)]
    # setup condition
    condition_GW14 = cond.condition(con_set_GW14)
    GW14 = extract_filterpos(condition_GW14, mn.gw14_nominals,
        m.mnemonic('IMIR_HK_GW14_POS_RATIO'), m.mnemonic('IMIR_HK_GW14_CUR_POS'))

    del condition_GW14

    con_set_GW23 = [
    cond.greater(m.mnemonic('IMIR_HK_GW23_POS_VOLT'), 250.0)]
    # setup condition
    condition_GW23 = cond.condition(con_set_GW23)
    GW23 = extract_filterpos(condition_GW23, mn.gw23_nominals,
        m.mnemonic('IMIR_HK_GW23_POS_RATIO'), m.mnemonic('IMIR_HK_GW23_CUR_POS'))

    del condition_GW23

    con_set_CCC = [
    cond.greater(m.mnemonic('IMIR_HK_CCC_POS_VOLT'), 250.0)]
    # setup condition
    condition_CCC = cond.condition(con_set_CCC)
    CCC = extract_filterpos(condition_CCC, mn.ccc_nominals,
        m.mnemonic('IMIR_HK_CCC_POS_RATIO'), m.mnemonic('IMIR_HK_CCC_CUR_POS'))

    del condition_CCC

    return FW, GW14, GW23, CCC

if __name__ =='__main__':
    pass
