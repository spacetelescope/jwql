import statistics
import os
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.csv_to_AstropyTable as apt
from jwql.utils.utils import get_config, filename_parser

from astropy.table import Table, Column

from jwql.instrument_monitors.nirspec_monitors.data_trending.utils.process_data import once_a_day_routine

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

#point to the directory where your files are located!
directory = '/home/daniel/STScI/trainigData/nirspec_15min/'

#here some some files contain the same data but they are all incomplete
#in order to generate a full database we have to import all of them
filenames = [
"FOFTLM2019067164301300_15min_day234.CSV",
"FOFTLM2019067164828534_15min_day244.CSV",
"FOFTLM2019067165013302_15min_day254.CSV",
"FOFTLM2019067164416045_15min_day235.CSV",
"FOFTLM2019067164837365_15min_day245.CSV",
"FOFTLM2019067165022368_15min_day255.CSV",
"FOFTLM2019067164555966_15min_day236.CSV",
"FOFTLM2019067164851969_15min_day246.CSV",
"FOFTLM2019067165033636_15min_day256.CSC",
"FOFTLM2019067164712315_15min_day237.CSV",
"FOFTLM2019067164859479_15min_day247.CSV",
"FOFTLM2019067165046387_15min_day257.CSV",
"FOFTLM2019067164721495_15min_day238.CSV",
"FOFTLM2019067164908225_15min_day248.CSV",
"FOFTLM2019067165053256_15min_day258.CSV",
"FOFTLM2019067164731039_15min_day239.CSV",
"FOFTLM2019067164918458_15min_day249.CSV",
"FOFTLM2019067165107118_15min_day259.CSV",
"FOFTLM2019067164744470_15min_day240.CSV",
"FOFTLM2019067164932178_15min_day250.CSV",
"FOFTLM2019067165118696_15min_day260.CSV",
"FOFTLM2019067164755086_15min_day241.CSV",
"FOFTLM2019067164941354_15min_day251.CSV",
"FOFTLM2019067165124648_15min_day261.CSV",
"FOFTLM2019067164808149_15min_day242.CSV",
"FOFTLM2019067164952300_15min_day252.CSV",
"FOFTLM2019067165135284_15min_day262.CSV",
"FOFTLM2019067164820344_15min_day243.CSV",
"FOFTLM2019067165001624_15min_day253.CSV",
"FOFTLM2019067165144927_15min_day263.CSV"]

def process_file(conn, path):
    '''Parse CSV file, process data within and put to DB
    Parameters
    ----------
    conn : DBobject
        Connection object to temporary database
    path : str
        defines path to the files
    '''

    #import mnemonic data and append dict to variable below
    m_raw_data = apt.mnemonics(path)

    #process raw data with once a day routine
    cond1 = once_a_day_routine(m_raw_data)

    #put all data in a database that uses a condition
    for key, value in cond1.items():

        m = m_raw_data.mnemonic(key)

        length = len(value)
        mean = statistics.mean(value)
        deviation = statistics.stdev(value)

        dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
        sql.add_data(conn, key, dataset)

    #add rest of the data to database
    for identifier in mn.mnemSet_15min:

        m = m_raw_data.mnemonic(identifier)

        temp = []

        #look for all values that fit to the given conditions
        for element in m:
            temp.append(float(element['value']))

        #return None if no applicable data was found
        if len(temp) > 2:
            length = len(temp)
            mean = statistics.mean(temp)
            deviation = statistics.stdev(temp)

            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, identifier, dataset)
        else:
            print('No data for {}'.format(identifier))

        del temp


def main():
    #generate paths
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'nirspec_database.db')

    #connect to temporary database
    conn = sql.create_connection(DATABASE_FILE)

    #do for every file in list above
    for name in filenames:
        path = directory + name
        process_file(conn, path)

    #close connection
    sql.close_connection(conn)
    print("done")

if __name__ == "__main__":
    main()
