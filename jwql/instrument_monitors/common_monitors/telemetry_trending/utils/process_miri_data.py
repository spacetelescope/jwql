"""This module holds functions for miri data trending

All functions in this module are tailored for the miri datatrending application.
Detailed descriptions are given for every function individually.

-------
    - Daniel Kühbacher
    - Lauren Chambers

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

from collections import defaultdict
import warnings

from . import miri_telemetry
from . import condition as cond


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
                elif ratio['time']>= interval[1]:
                        break

            # check wheather pos values are in range of these checkvals
            window = 1
            found_value = False

            while found_value == False:
                for ratio in interval_ratios:
                    if (abs(float(ratio['value']) - nominals.get(pos['value'])) < window):
                        found_value = True
                        pos_values[pos['value']].append(( ratio['time'], ratio['value']))
                        break

                window +=2

                if window > 10:
                    # Ratio error (don't know what this means)
                    break

        else:
            warnings.warn("UNKNOWN Position")
    return pos_values

def once_a_day_routine(mnemonic_data_dict):
    '''Proposed routine for processing a 15min data file once a day

    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with corresponding identifier as key
    Return
    ------
    data_cond_1 : dict
        holds extracted data with condition 1 applied
    data_cond_1 : dict
        holds extracted data with condition 2 applied
    '''

    # abbreviate attribute
    returndata = dict()

    ######################################################################### 
    con_set_1 = [
        cond.equal(mnemonic_data_dict['IMIR_HK_IMG_CAL_LOOP'], 'OFF'),
        cond.equal(mnemonic_data_dict['IMIR_HK_IFU_CAL_LOOP'], 'OFF'),
        cond.equal(mnemonic_data_dict['IMIR_HK_POM_LOOP'], 'OFF'),
        cond.smaller(mnemonic_data_dict['IMIR_HK_ICE_SEC_VOLT1'], 1.0),
        cond.greater(mnemonic_data_dict['SE_ZIMIRICEA'], 0.2)
    ]
    # setup condition
    condition_1 = cond.condition(con_set_1)


    # add filtered engineering values of mnemonics given in list mnemonic_cond_1
    # to dictionary
    for mnemonic_id in miri_telemetry.mnemonic_cond_1:
        if mnemonic_id not in miri_telemetry.not_in_edb:
            data = _extract_data(condition_1, mnemonic_data_dict[mnemonic_id])
    
            if data != None:
                returndata.update( {mnemonic_id:data} )
                print('{} data points for {}'.format(len(data), mnemonic_id))
            else:
                print("no data for {}".format(mnemonic_id))

    ##########################################################################
    # under normal use following line should be added:
    # cond.equal(mnemonic_data_dict['IGDP_IT_MIR_SW_STATUS'), 'DETECTOR_READY'),      \
    # SW was missing in the training data so I could not use it for a condition.
    con_set_2 = [
        cond.greater(mnemonic_data_dict['SE_ZIMIRFPEA'], 0.5),
        cond.equal(mnemonic_data_dict['IGDP_IT_MIR_IC_STATUS'], 'DETECTOR_READY'),
        cond.equal(mnemonic_data_dict['IGDP_IT_MIR_LW_STATUS'], 'DETECTOR_READY')
    ]
    # setup condition
    condition_2 = cond.condition(con_set_2)

    # add filtered engineering values of mnemonics given in list mnemonic_cond_2
    # to dictionary
    for mnemonic_id in miri_telemetry.mnemonic_cond_2:
        if mnemonic_id not in miri_telemetry.not_in_edb:
            data = _extract_data(condition_2, mnemonic_data_dict[mnemonic_id])
    
            if data != None:
                returndata.update( {mnemonic_id:data} )
                print('{} data points for {}'.format(len(data), mnemonic_id))
            else:
                print("no data for {}".format(mnemonic_id))

    return returndata


def whole_day_routine(mnemonic_data_dict):
    '''Proposed routine for processing data representing a whole day

    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with corresponding identifier as key
    Return
    ------
    whole_day_data_dict : dict
    '''

    whole_day_data_dict = {}

    ######################################################################### 
    # Require ICE Voltage to be over 25.0 volts
    con_set_3 = [
        cond.greater(mnemonic_data_dict['IMIR_HK_ICE_SEC_VOLT1'], 25.0)
    ]

    # setup condition
    condition_3 = cond.condition(con_set_3)

    # For the mnemonics that re subject to this condition, only pull out the
    # values that have ICE voltage above 25 V
    for mnemonic_id in miri_telemetry.mnemonic_cond_3:
        if mnemonic_id not in miri_telemetry.not_in_edb:
            data_matching_cond3 = _extract_data(
                condition_3, mnemonic_data_dict[mnemonic_id]
            )

            if data_matching_cond3 != None:
                whole_day_data_dict[mnemonic_id] = data_matching_cond3
                print('{} data points for {}'.format(len(data_matching_cond3), mnemonic_id))
            else:
                print("no data for {}".format(mnemonic_id))

    ######################################################################### 
    for mnemonic_id in miri_telemetry.mnemonic_pos_volt:
        if mnemonic_id not in miri_telemetry.not_in_edb:
            # extract data for ID under given condition
            try:
                con_set = [
                    cond.greater(mnemonic_data_dict[mnemonic_id], 250.0)
                ]
            except Exception as e:
                print('Could not apply > 250.0 condition for', mnemonic_id)
                raise(e)

            # setup condition
            condition = cond.condition(con_set)
            data_matching_pos_volt = _extract_data(condition, mnemonic_data_dict[mnemonic_id])
            whole_day_data_dict.update({mnemonic_id: data_matching_pos_volt})


    return whole_day_data_dict


def wheelpos_routine(mnemonic_data_dict):
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

    con_set_FW = [
        cond.greater(mnemonic_data_dict['IMIR_HK_FW_POS_VOLT'],250.0)
    ]
    # setup condition
    condition_FW = cond.condition(con_set_FW)
    FW = extract_filterpos(
        condition_FW, miri_telemetry.fw_nominals, mnemonic_data_dict['IMIR_HK_FW_POS_RATIO'],
        mnemonic_data_dict['IMIR_HK_FW_CUR_POS']
    )

    con_set_GW14 = [
        cond.greater(mnemonic_data_dict['IMIR_HK_GW14_POS_VOLT'],250.0)
    ]
    # setup condition
    condition_GW14 = cond.condition(con_set_GW14)
    GW14 = extract_filterpos(
        condition_GW14, miri_telemetry.gw14_nominals, mnemonic_data_dict['IMIR_HK_GW14_POS_RATIO'],
        mnemonic_data_dict['IMIR_HK_GW14_CUR_POS']
    )

    con_set_GW23 = [
        cond.greater(mnemonic_data_dict['IMIR_HK_GW23_POS_VOLT'], 250.0)
    ]
    # setup condition
    condition_GW23 = cond.condition(con_set_GW23)
    GW23 = extract_filterpos(
        condition_GW23, miri_telemetry.gw23_nominals, mnemonic_data_dict['IMIR_HK_GW23_POS_RATIO'],
        mnemonic_data_dict['IMIR_HK_GW23_CUR_POS']
    )

    con_set_CCC = [
        cond.greater(mnemonic_data_dict['IMIR_HK_CCC_POS_VOLT'], 250.0)
    ]
    # setup condition
    condition_CCC = cond.condition(con_set_CCC)
    CCC = extract_filterpos(
        condition_CCC, miri_telemetry.ccc_nominals, mnemonic_data_dict['IMIR_HK_CCC_POS_RATIO'],
        mnemonic_data_dict['IMIR_HK_CCC_CUR_POS']
    )

    return FW, GW14, GW23, CCC


def _extract_data(condition, mnemonic_table):
    '''Function extracts data from given mnemmonic at a given condition
    Parameters
    ----------
    condition : object
        conditon object that holds one or more subconditions
    mnemonic_table : AstropyTable
        holds single table with mnemonic data
    Return
    ------
    temp : list  or None
        holds data that applies to given condition
    '''
    mnemonic_values_for_cond = []

    # look for all values that fit to the given conditions
    for row in mnemonic_table:
        if condition.state(float(row['time'])):
            mnemonic_values_for_cond.append(float(row['value']))

    # return temp is one ore more values fit to the condition
    # return None if no applicable data was found
    if len(mnemonic_values_for_cond) > 0:
        return mnemonic_values_for_cond
    else:
        return None


if __name__ =='__main__':
    pass
