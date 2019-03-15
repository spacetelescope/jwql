


def lamp_distinction(lamp_sel, lamp_curr):
    """Distincts over all calibration lamps and returns representative current means
        each
    Parameters
    ----------
    """

    #initilize empty dict
    lamp_currents = defaultdict(list)

    #do for every position in mnemonic attribute
    for index, lamp in enumerate(lamp_sel):

        #raise warning if position is UNKNOWN
        if lamp['value'] != "DUMMY":

            #request time interval with applicable current values.
            start_time = lamp['time']

            if index < len(lamp_sel):
                end_time = lamp_sel[index+1]['time']
            else:
                break



            for curr in lamp_curr:
                if (curr['time'] > start_time):
                    if (curr['time'] < end_time):




                for ratio in ratio_mnem:

                    #look for ratio values which are in the same time interval
                    #and differ a certain value (here 5mV) from the nominal
                    if (ratio['time'] >= cur_pos_time) and \
                        (abs(float(ratio['value']) - nominals.get(pos['value'])) < 5):

                        if (ratio['time'] > interval[0]) and (ratio['time'] < interval[1]):
                            pos_values[pos['value']].append(( ratio['time'], ratio['value']))

        else:
            warnings.warn("DUMMY Lamp")
    return lamp_currents
