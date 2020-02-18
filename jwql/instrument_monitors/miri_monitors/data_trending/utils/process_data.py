"""This module holds various utility functions for MIRI data trending

All functions in this module are tailored for the MIRI data trending
application.  Detailed descriptions are given for every function
individually.

Authors
-------

    - Daniel Kühbacher

Use
---

    This module is intended to be imported and used by MIRI data
    trending software, e.g.:

    ::
        from .utils.process_data import whole_day_routine
        whole_day_routine(raw_daya)`
"""

from collections import defaultdict
import warnings

from jwql.instrument_monitors.miri_monitors.data_trending.utils import condition
from jwql.instrument_monitors.miri_monitors.data_trending.utils import mnemonics


def _extract_data(condition, mnemonic):
    """Extract data for given mnemmonic and a given condition

    Parameters
    ----------
    condition : obj
        Conditon object that holds one or more subconditions
    mnemonic : obj
        ``AstropyTable`` object that holds single table with mnemonic
        data

    Returns
    -------
    data : list or None
        Contains data that applies to given condition
    """

    data = []

    # Look for all values that fit to the given conditions
    for element in mnemonic:
        if condition.state(float(element['time'])):
            data.append(float(element['value']))

    # Returned data is one or more values fit to the condition
    # Return None if no applicable data was found
    if len(data) > 0:
        return data
    else:
        return None


def _extract_filterpos(condition, nominals, ratio_mnemonic, position_mnemonic):
    """Extracts ratio values which correspond to given position values
    and their proposed nominals

    Parameters
    ----------
    condition : obj
        Conditon object that holds one or more subconditions
    nominals : dict
        Holds nominal values for all wheel positions
    ratio_mnemonic : AstropyTable
        Holds ratio values of one specific mnemonic
    position_mnemonic : AstropyTable
        Holds position values of one specific mnemonic

    Returns
    -------
    position_values : dict
        Holds ratio values and times with corresponding position label
        as key
    """

    # Initilize empty dict for assigned ratio values
    position_values = defaultdict(list)

    for index, position in enumerate(position_mnemonic):

        if position['value'] != 'UNKNOWN':

            # Set up interval beween where the position value was timed and the supply
            interval = condition.get_interval(position['time'])
            if interval is None:
                continue
            else:
                interval[0] = position['time']
                if position_mnemonic[index + 1]['time'] < interval[1]:
                    interval[1] = position_mnemonic[index + 1]['time']

            # Empty list for position values
            interval_ratios = []

            # Get all ratio values in the interval
            for ratio in ratio_mnemonic:
                if (ratio['time'] >= interval[0]) and (ratio['time'] < interval[1]):
                    interval_ratios.append(ratio)
                elif ratio['time'] >= interval[1]:
                    break

            # Check whether position values are in range of these checkvals
            window = 1
            found_value = False
            while found_value is False:
                for ratio in interval_ratios:
                    if (abs(float(ratio['value']) - nominals.get(position['value'])) < window):
                        found_value = True
                        position_values[position['value']].append((ratio['time'], ratio['value']))
                        break
                window += 2
                if window > 10:
                    print('ratio error')
                    break
        else:
            warnings.warn('UNKNOWN Position')

    return position_values


def _extract_filterpos1(condition, nominals, ratio_mnemonic, position_mnemonic):
    """Extracts ratio values which correspond to given position values
    and their proposed nominals

    Parameters
    ----------
    condition : obj
        Conditon object that holds one or more subconditions
    nominals : dict
        Holds nominal values for all wheel positions
    ratio_mnemonic : AstropyTable
        Holds ratio values of one specific mnemonic
    position_mnemonic : AstropyTable
        Holds position values of one specific mnemonic

    Returns
    -------
    position_values : dict
        Holds ratio values and times with corresponding position label
        as key
    """

    position_values = defaultdict(list)

    for position in position_mnemonic:

        if position['value'] != 'UNKNOWN':

            # Request time interval where the current positon is in between
            interval = condition.get_interval(position['time'])

            # Check if condition attribute for current positon is true
            if interval is not None:
                current_position_time = position['time']

                for ratio in ratio_mnemonic:

                    # Look for ratio values which are in the same time interval
                    # and differ a certain value (here 5mV) from the nominal
                    if (ratio['time'] >= current_position_time) and \
                       (abs(float(ratio['value']) - nominals.get(position['value'])) < 5):

                        if (ratio['time'] > interval[0]) and (ratio['time'] < interval[1]):
                            position_values[position['value']].append((ratio['time'], ratio['value']))

        else:
            warnings.warn('UNKNOWN Position')

    return position_values


def once_a_day_routine(mnemonic_data):
    """Routine for processing a 15 min data file once a day

    Parameters
    ----------
    mnemonic_data : dict
        Holds time and value in a astropy table with correspining
        identifier as key

    Returns
    -------
    data_cond_1 : dict
        Holds extracted data with condition 1 applied
    data_cond_2 : dict
        Holds extracted data with condition 2 applied
    """

    # Initialize dictionary to hold data
    data_dict = dict()

    condition_set_1 = [
        condition.equal(mnemonic_data.mnemonic('IMIR_HK_IMG_CAL_LOOP'), 'OFF'),
        condition.equal(mnemonic_data.mnemonic('IMIR_HK_IFU_CAL_LOOP'), 'OFF'),
        condition.equal(mnemonic_data.mnemonic('IMIR_HK_POM_LOOP'), 'OFF'),
        condition.smaller(mnemonic_data.mnemonic('IMIR_HK_ICE_SEC_VOLT1'), 1.0),
        condition.greater(mnemonic_data.mnemonic('SE_ZIMIRICEA'), 0.2)]
    condition_1 = condition.condition(condition_set_1)

    # Add filtered engineering values of mnemonics given in list mnemonic_cond_1
    # to dictitonary
    for identifier in mnemonics.mnemonic_cond_1:
        data = _extract_data(condition_1, mnemonic_data.mnemonic(identifier))
        if data is not None:
            data_dict.update({identifier: data})
        else:
            print('no data for {}'.format(identifier))

    # Under normal use, the following line should be added:
    # condition.equal(mnemonic_data.mnemonic('IGDP_IT_MIR_SW_STATUS'), 'DETECTOR_READY'),
    # SW was missing in the trainigs data so I could not use it for a condition.
    condition_set_2 = [
        condition.greater(mnemonic_data.mnemonic('SE_ZIMIRFPEA'), 0.5),
        condition.equal(mnemonic_data.mnemonic('IGDP_IT_MIR_IC_STATUS'), 'DETECTOR_READY'),
        condition.equal(mnemonic_data.mnemonic('IGDP_IT_MIR_LW_STATUS'), 'DETECTOR_READY')]
    condition_2 = condition.condition(condition_set_2)

    # Add filtered engineering values of mnemonics given in list mnemonic_cond_2
    # to dictitonary
    for identifier in mnemonics.mnemonic_cond_2:
        data = _extract_data(condition_2, mnemonic_data.mnemonic(identifier))
        if data is not None:
            data_dict.update({identifier: data})
        else:
            print('no data for {}'.format(identifier))

    return data_dict


def wheelpos_routine(mnemonic_data):
    """Routine for position sensors each day

    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with correspining
        identifier as key

    Returns
    -------
    FW : dict
        Holds FW ratio values and times with corresponding
        positionlabel as key
    GW14 : dict
        Holds GW14 ratio values and times with corresponding
        positionlabel as key
    GW23 : dict
        Holds GW23 ratio values and times with corresponding
        positionlabel as key
    CCC : dict
        Holds CCC ratio values and times with corresponding
        positionlabel as key
    """

    condition_FW = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_FW_POS_VOLT'), 250.0)])
    fw = _extract_filterpos(
        condition_FW,
        mnemonics.fw_nominals,
        mnemonic_data.mnemonic('IMIR_HK_FW_POS_RATIO'),
        mnemonic_data.mnemonic('IMIR_HK_FW_CUR_POS'))

    condition_GW14 = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_GW14_POS_VOLT'), 250.0)])
    gw14 = _extract_filterpos(
        condition_GW14,
        mnemonics.gw14_nominals,
        mnemonic_data.mnemonic('IMIR_HK_GW14_POS_RATIO'),
        mnemonic_data.mnemonic('IMIR_HK_GW14_CUR_POS'))

    condition_GW23 = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_GW23_POS_VOLT'), 250.0)])
    gw23 = _extract_filterpos(
        condition_GW23,
        mnemonics.gw23_nominals,
        mnemonic_data.mnemonic('IMIR_HK_GW23_POS_RATIO'),
        mnemonic_data.mnemonic('IMIR_HK_GW23_CUR_POS'))

    condition_CCC = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_CCC_POS_VOLT'), 250.0)])
    ccc = _extract_filterpos(
        condition_CCC,
        mnemonics.ccc_nominals,
        mnemonic_data.mnemonic('IMIR_HK_CCC_POS_RATIO'),
        mnemonic_data.mnemonic('IMIR_HK_CCC_CUR_POS'))

    return fw, gw14, gw23, ccc


def whole_day_routine(mnemonic_data):
    """Routine for processing data representing a whole day

    Parameters
    ----------
    mnemonic_data : dict
        dict holds time and value in a astropy table with corresponding
        identifier as key

    Returns
    -------
    data_cond_3 : dict
        Holds extracted data with condition 3 applied
    FW_volt : list
        extracted data for ``IMIR_HK_FW_POS_VOLT```
    GW14_volt : list
        extracted data for ``IMIR_HK_GW14_POS_VOLT``
    GW23_volt : list
        extracted data for ``IMIR_HK_GW23_POS_VOLT``
    CCC_volt : list
        extracted data for ``IMIR_HK_CCC_POS_VOLT``
    """

    data_dict = dict()

    condition_3 = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_ICE_SEC_VOLT1'), 25.0)])

    # add filtered engineering values of mnemonics given in list mnemonic_cond_3
    # to dictitonary
    for identifier in mnemonics.mnemonic_cond_3:
        data = _extract_data(condition_3, mnemonic_data.mnemonic(identifier))
        if data is not None:
            data_dict.update({identifier: data})
        else:
            print('no data for {}'.format(identifier))

    # Extract data for IMIR_HK_FW_POS_VOLT under given condition
    condition_FW = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_FW_POS_VOLT'), 250.0)])
    FW_volt = _extract_data(condition_FW, mnemonic_data.mnemonic('IMIR_HK_FW_POS_VOLT'))
    data_dict.update({'IMIR_HK_FW_POS_VOLT': FW_volt})

    # Extract data for IMIR_HK_GW14_POS_VOLT under given condition
    condition_GW14 = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_GW14_POS_VOLT'), 250.0)])
    GW14_volt = _extract_data(condition_GW14, mnemonic_data.mnemonic('IMIR_HK_GW14_POS_VOLT'))
    data_dict.update({'IMIR_HK_GW14_POS_VOLT': GW14_volt})

    # Extract data for IMIR_HK_GW23_POS_VOLT under given condition
    condition_GW23 = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_GW23_POS_VOLT'), 250.0)])
    GW23_volt = _extract_data(condition_GW23, mnemonic_data.mnemonic('IMIR_HK_GW23_POS_VOLT'))
    data_dict.update({'IMIR_HK_GW23_POS_VOLT': GW23_volt})

    # Extract data for IMIR_HK_CCC_POS_VOLT under given condition
    condition_CCC = condition.condition([condition.greater(mnemonic_data.mnemonic('IMIR_HK_CCC_POS_VOLT'), 250.0)])
    CCC_volt = _extract_data(condition_CCC, mnemonic_data.mnemonic('IMIR_HK_CCC_POS_VOLT'))
    data_dict.update({'IMIR_HK_CCC_POS_VOLT': CCC_volt})

    return data_dict
