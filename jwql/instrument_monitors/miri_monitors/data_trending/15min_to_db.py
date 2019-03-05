
import statistics
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.utils.csv_to_AstropyTable as apt

from jwql.instrument_monitors.miri_monitors.data_trending.utils.process_data import once_a_day_routine

#create filename string
directory = '/home/daniel/STScI/trainigData/set_1_15min/'

filenames1 = [
'imir_190218_229_15mFOFTLM2019049190357389.CSV',
'imir_190218_242_15mFOFTLM2019049190828360.CSV',
'imir_190218_230_15mFOFTLM2019049190418712.CSV',
'imir_190218_243_15mFOFTLM2019049190849540.CSV',
'imir_190218_231_15mFOFTLM2019049190441348.CSV',
'imir_190218_244_15mFOFTLM2019049190905148.CSV',
'imir_190218_232_15mFOFTLM2019049190505181.CSV',
'imir_190218_245_15mFOFTLM2019049190928651.CSV',
'imir_190218_233_15mFOFTLM2019049190534172.CSV',
'imir_190218_246_15mFOFTLM2019049190944061.CSV',
'imir_190218_247_15mFOFTLM2019049191005149.CSV',
'imir_190218_235_15mFOFTLM2019049190616250.CSV',
'imir_190218_234_15mFOFTLM2019049190551817.CSV',
'imir_190218_248_15mFOFTLM2019049191021707.CSV',
'imir_190218_236_15mFOFTLM2019049190632019.CSV',
'imir_190218_249_15mFOFTLM2019049191042754.CSV',
'imir_190218_237_15mFOFTLM2019049190653391.CSV',
'imir_190218_250_15mFOFTLM2019049191100333.CSV',
'imir_190218_238_15mFOFTLM2019049190708898.CSV',
'imir_190218_251_15mFOFTLM2019049191121307.CSV',
'imir_190218_239_15mFOFTLM2019049190733579.CSV',
'imir_190218_252_15mFOFTLM2019049191135679.CSV',
'imir_190218_240_15mFOFTLM2019049190750440.CSV',
'imir_190218_253_15mFOFTLM2019049191156202.CSV',
'imir_190218_241_15mFOFTLM2019049190811168.CSV',
'imir_190218_254_15mFOFTLM2019049191211341.CSV']

#old files
filenames = [
'imir_190130_otis229FOFTLM2019030204146194.CSV',
'imir_190130_otis240FOFTLM2019030210631185.CSV',
'imir_190130_otis230FOFTLM2019030204240886.CSV',
'imir_190130_otis241FOFTLM2019030210651672.CSV',
'imir_190130_otis231FOFTLM2019030204334644.CSV',
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
'imir_190130_otis239FOFTLM2019030204805611.CSV',
'imir_190130_otis250FOFTLM2019030211032094.CSV']

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

        elif key == "SE_ZIMIRICEB":
            length = len(value)
            mean = statistics.mean(value)
            deviation = statistics.stdev(value)

            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "SE_ZIMIRICEB_IDLE", dataset)

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
    db_file = "/home/daniel/STScI/jwql/jwql/database/miri_database_new.db"
    conn = sql.create_connection(db_file)

    for name in filenames:
        path = directory + name
        process_file(conn, path)

    sql.close_connection(conn)
    print("done")

if __name__ == "__main__":
    main()
