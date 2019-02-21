
import statistics
import sqlite3

import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as mn
import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
import jwql.instrument_monitors.miri_monitors.data_trending.utils.csv_to_AstropyTable as apt

from jwql.instrument_monitors.miri_monitors.data_trending.utils.process_data import whole_day_routine, wheelpos_routine



#create filename string
directory='/home/daniel/STScI/trainigData/set_1_day/'

filenames = [
'imir_190204_DoY2292017FOFTLM2019035182609402.CSV',
'imir_190204_DoY2402017FOFTLM2019035180907145.CSV',
'imir_190204_DoY2412017FOFTLM2019035181004311.CSV',
'imir_190204_DoY2312017FOFTLM2019035184159965.CSV',
'imir_190204_DoY2422017FOFTLM2019035181027504.CSV',
'imir_190204_DoY2322017FOFTLM2019035184236985.CSV',
'imir_190204_DoY2432017FOFTLM2019035181100606.CSV',
'imir_190204_DoY2332017FOFTLM2019035184306076.CSV',
'imir_190204_DoY2442017FOFTLM2019035181126853.CSV',
'imir_190204_DoY2342017FOFTLM2019035184347174.CSV',
'imir_190204_DoY2452017FOFTLM2019035181155234.CSV',
'imir_190204_DoY2352017FOFTLM2019035184708935.CSV',
'imir_190204_DoY2462017FOFTLM2019035181230871.CSV',
'imir_190204_DoY2362017FOFTLM2019035184737246.CSV',
'imir_190204_DoY2472017FOFTLM2019035181252890.CSV',
'imir_190204_DoY2372017FOFTLM2019035184806338.CSV',
'imir_190204_DoY2482017FOFTLM2019035181322838.CSV',
'imir_190204_DoY2382017FOFTLM2019035184832737.CSV',
'imir_190204_DoY2492017FOFTLM2019035181406861.CSV',
'imir_190204_DoY2392017FOFTLM2019035180833486.CSV',
'imir_190204_DoY2502017FOFTLM2019035181519288.CSV']


def process_file(conn, path):
    m_raw_data = apt.mnemonics(path)


    cond3, FW_volt, GW14_volt, GW23_volt, CCC_volt = whole_day_routine(m_raw_data)
    FW, GW14, GW23, CCC= wheelpos_routine(m_raw_data)

    #put data from con3 to database
    for key, value in cond3.items():

        m = m_raw_data.mnemonic(key)

        if value != None:
            if len(value) > 2:
                if key == "SE_ZIMIRICEA":
                    length = len(value)
                    mean = statistics.mean(value)
                    deviation = statistics.stdev(value)
                    dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
                    sql.add_data(conn, "SE_ZIMIRICEA_HV_ON", dataset)

                elif key == "IMIR_HK_ICE_SEC_VOLT4":
                    length = len(value)
                    mean = statistics.mean(value)
                    deviation = statistics.stdev(value)
                    dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
                    sql.add_data(conn, "IMIR_HK_ICE_SEC_VOLT4_HV_ON", dataset)

                else:
                    length = len(value)
                    mean = statistics.mean(value)
                    deviation = statistics.stdev(value)
                    dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
                    sql.add_data(conn, key, dataset)
###########################################################################

    m = m_raw_data.mnemonic('IMIR_HK_FW_POS_VOLT')
    if FW_volt != None:
        if len(FW_volt) > 2:
            length = len(FW_volt)
            mean = statistics.mean(FW_volt)
            deviation = statistics.stdev(FW_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_FW_POS_VOLT", dataset)

    m = m_raw_data.mnemonic('IMIR_HK_GW14_POS_VOLT')
    if GW14_volt != None:
        if len(GW14_volt) > 2:
            length = len(GW14_volt)
            mean = statistics.mean(GW14_volt)
            deviation = statistics.stdev(GW14_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_GW14_POS_VOLT", dataset)

    m = m_raw_data.mnemonic('IMIR_HK_GW23_POS_VOLT')
    if GW23_volt != None:
        if len(GW23_volt) > 2:
            length = len(GW23_volt)
            mean = statistics.mean(GW23_volt)
            deviation = statistics.stdev(GW23_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_GW23_POS_VOLT", dataset)

    m = m_raw_data.mnemonic('IMIR_HK_CCC_POS_VOLT')
    if CCC_volt != None:
        if len(CCC_volt) > 2:
            length = len(CCC_volt)
            mean = statistics.mean(CCC_volt)
            deviation = statistics.stdev(CCC_volt)
            dataset = (float(m.meta['start']), float(m.meta['end']), length, mean, deviation)
            sql.add_data(conn, "IMIR_HK_CCC_POS_VOLT", dataset)

    #########################################################################################
    for pos in mn.fw_positions:
        try:
            data = FW[pos]
            for element in data:
                sql.add_wheel_data(conn, 'IMIR_HK_FW_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass

    for pos in mn.gw_positions:
        try:
            data_GW14 = GW14[pos]
            data_GW23 = GW14[pos]

            for element in data_GW14:
                sql.add_wheel_data(conn, 'IMIR_HK_GW14_POS_RATIO_{}'.format(pos), element)
            for element in data_GW23:
                sql.add_wheel_data(conn, 'IMIR_HK_GW23_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass

    for pos in mn.ccc_positions:
        try:
            data = CCC[pos]
            for element in data:
                sql.add_wheel_data(conn, 'IMIR_HK_CCC_POS_RATIO_{}'.format(pos), element)
        except KeyError:
            pass



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
