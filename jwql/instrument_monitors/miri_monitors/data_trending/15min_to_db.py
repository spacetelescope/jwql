
import statistics
import mnemonics as mn
import sql_interface as sql
import csv_to_AstropyTable as apt

from data_extract import once_a_day_routine



#create filename string
directory = '/home/daniel/STScI/trainigData/set_1_15min_complete/'

filenames1 = [
'imir_190130_otis229FOFTLM2019030204146194.CSV',
'imir_190130_otis230FOFTLM2019030204240886.CSV',
'imir_190130_otis241FOFTLM2019030210651672.CSV',
'imir_190130_otis240FOFTLM2019030210631185.CSV',
'imir_190130_otis231FOFTLM2019030204334644.CSV',
'imir_190130_otis233FOFTLM2019030204521412.CSV',
'imir_190130_otis242FOFTLM2019030210728909.CSV',
'imir_190130_otis232FOFTLM2019030204455835.CSV',  
'imir_190130_otis243FOFTLM2019030210744062.CSV',
'imir_190130_otis233FOFTLM2019030204521412.CSV',  
'imir_190130_otis244FOFTLM2019030210809362.CSV',
'imir_190130_otis234FOFTLM2019030204555665.CSV',  
'imir_190130_otis245FOFTLM2019030210828095.CSV',
'imir_190130_otis235FOFTLM2019030204617145.CSV',  
'imir_190130_otis246FOFTLM2019030210852965.CSV',
'imir_190130_otis236FOFTLM2019030204651604.CSV',  
'imir_190130_otis247FOFTLM2019030210914141.CSV',
'imir_190130_otis237FOFTLM2019030204712019.CSV',  
'imir_190130_otis248FOFTLM2019030210940944.CSV',
'imir_190130_otis238FOFTLM2019030204738855.CSV',  
'imir_190130_otis249FOFTLM2019030211002524.CSV',
'imir_190130_otis239FOFTLM2019030204805611.CSV']

filenames = [  
'imir_190130_otis229FOFTLM2019030204146194.CSV', 
'imir_190130_otis234FOFTLM2019030204555665.CSV', 
'imir_190130_otis230FOFTLM2019030204240886.CSV', 
'imir_190130_otis235FOFTLM2019030204617145.CSV', 
'imir_190130_otis231FOFTLM2019030204334644.CSV',   
'imir_190130_otis236FOFTLM2019030204651604.CSV', 
'imir_190130_otis232FOFTLM2019030204455835.CSV',   
'imir_190130_otis237FOFTLM2019030204712019.CSV', 
'imir_190130_otis233FOFTLM2019030204521412.CSV',   
'imir_190130_otis238FOFTLM2019030204738855.CSV']

def process_file(conn, path): 
    m_raw_data = apt.mnemonics(path)

    cond1, cond2 = once_a_day_routine(m_raw_data)

    for key, value in cond1.items(): 

        m = m_raw_data.mnemonic(key)

        if key == "SE_ZIMIRICEA": 
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)

            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "SE_ZIMIRICEA_IDLE", dataset)

        elif key == "IMIR_HK_ICE_SEC_VOLT4": 
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)

            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_IDLE", dataset)

        else:
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)

            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, key, dataset)    

    for key, value in cond2.items():
        length = len(value)
        mean = statistics.mean(value)
        deviation = statistics.stdev(value)

        dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
        sql.add_data(conn, key, dataset) 


def main():
    db_file = "miri_database.db"
    conn = sql.create_connection(db_file)

    for name in filenames:
        path = directory + name
        process_file(conn, path)

    sql.close_connection(conn)
    print("done")

if __name__ == "__main__": 
    main()