"""extract_data.py

    This module contains all function to extract the needed data using conditions,
    from the downloaded nmemonics.

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

def extract_filterpos(nominals, ratio_mnem, pos_mnem):
    '''Extracts ratio values which correspond to given position values and their
       proposed nominals
    Parameters
    ----------
    condition : object
        conditon object that holds one or more subconditions
    nominals : dict
        holds nominal values for all wheel positions
    ratio_mnem : AstropyTable
        holds ratio values of one specific mnemonic
    pos_mnem : AstropyTable
        holds pos values of one specific mnemonic
    Return
    ------
    pos_values : dict
        holds ratio values and times with corresponding positionlabel as key
    '''

    # initilize empty dict for assigned ratio values
    pos_values = defaultdict(list)

    # get time range of each position
    pos_ranges = []
    pos_bevore = "NUL"

    for index, pos in enumerate(pos_mnem):
        # calculate latest possible time in that date
        max_time = max(pos_mnem['time']) + 1

        if pos['value'] != pos_bevore:
            pos_new = []
            pos_new.append(pos['value'])  # value
            pos_new.append(pos['time'])  # start time
            pos_new.append(max_time)  # end time
            pos_ranges.append(pos_new)

            pos_bevore = pos['value']

            try:
                pos_ranges[-2][2] = pos['time']
            except:
                continue

        else:
            continue

    for pos, start_time, end_time in pos_ranges:
        value_list = []
        times_list = []
        nominal_value = nominals.get(pos)

        for mnemonic in ratio_mnem:

            if mnemonic['time'] < start_time or mnemonic['time'] > end_time:
                continue
            else:
                value_list.append(float(mnemonic['value']))
                times_list.append(float(mnemonic['time']))

        try:
            min_value = min(value_list, key=lambda x: abs(x - nominal_value))
            min_index = value_list.index(min_value)
            data_to_save = [times_list[min_index], min_value]
            pos_values[pos].append(data_to_save)


        except:
            continue

    return pos_values

