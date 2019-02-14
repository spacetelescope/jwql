

import csv_to_AstropyTable as apt
import statistics
import sqlite3

import mnemonics as mn
import sql_interface as sql
import condition as cond

from collections import defaultdict



#create filename string
directory='/home/daniel/STScI/trainigData/set_1_day/'

filename= 'imir_190204_DoY2292017FOFTLM2019035182609402.CSV'

filterpositions = [
'FND',
'OPAQUE',
'F1000W',
'F1130W',
'F1280W',
'P750L',
'F1500W',
'F1800W',
'F2100W',
'F560W',
'FLENS',
'F2300C',
'F770W',
'F1550C',
'F2550W',
'F1140C',
'F2550WR',
'F1065C']

def extract_filterpos(cond, ratio_mnem, pos_mnem):

    pos_values = defaultdict(list)

    #do for every position in file
    for pos in pos_mnem:

        interval = cond.get_interval(pos['time'])

        if interval is not None:
            cur_pos_time = pos['time']
            filtername = pos['value']

            for ratio in ratio_mnem: 

                if (ratio['time'] > cur_pos_time) and (abs(float(ratio['value'])) > 0.1): 
                    if (ratio['time'] > interval[0]) and (ratio['time'] < interval[1]): 
                        pos_values[pos['value']].append( ( ratio['time'], ratio['value']) )
                        break
    return pos_values



def day_routine(path): 

    #read data in file "path"  and return dictionary with mnemonic and astropy table 
    m = apt.mnemonics(path)


    #prepare condition for data retrieval 
    con_set_3 = [ 
    cond.greater(m.mnemonic('IMIR_HK_FW_POS_VOLT'), 250.0)] 
    #setup condition
    condition_3=cond.condition(con_set_3)

    v = extract_filterpos(condition_3, m.mnemonic('IMIR_HK_FW_POS_RATIO'), m.mnemonic('IMIR_HK_FW_CUR_POS'))
    print (v)

   

# create initial database or check if all tables are setup 

path = directory+filename
day_routine(path)


print('programm end')
#####################################
#programm end 

"""
 for element in m.mnemonic('IMIR_HK_FW_CUR_POS'):

        if condition_3.state(element['Secondary Time']): 
            cur_pos_time = element['Secondary Time']
            interval = condition_3.get_interval(element['Secondary Time'],0)
            filtername = element['EU Value']

            if interval is not None:
                for item in m.mnemonic('IMIR_HK_FW_POS_RATIO'): 
                    if (item['Secondary Time'] > cur_pos_time) and (abs(float(item['EU Value'])) > 0.1): 
                        if (item['Secondary Time'] > interval[0]) and (item['Secondary Time'] < interval[1]): 

                            pos_values[]
                            print(filtername+'={}'.format(item['EU Value']))
                            break
                        else: 
                            pass
                    else: 
                        pass 
        else: 
            pass
"""