


def update_task(conn, task):
    """
    update priority, begin_date, and end date of a task
    :param conn:
    :param task:
    :return: project id

    """
    sql = ''' UPDATE tasks
              SET priority = ? ,
                  begin_date = ? ,
                  end_date = ?
              WHERE id = ?'''

    cur = conn.cursor()
    cur.execute(sql, task)

def create_project(conn, project):
    """
    Create a new project into the projects table
    :param conn:
    :param project:
    :return: project id
    """
    sql = ''' INSERT INTO projects(name,begin_date,end_date)
              VALUES(?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, project)
    return cur.lastrowid

def create_task(conn, task):
    """
    Create a new task
    :param conn:
    :param task:
    :return:
    """
 
    sql = ''' INSERT INTO tasks(name,priority,status_id,project_id,begin_date,end_date)
              VALUES(?,?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, task)
    return cur.lastrowid

def add_data(conn, name, dataset): 

    cur=conn.cursor()
    cur.execute('INSERT INTO {} (start_time,end_time,datapoints,average,deviation) \
        VALUES (?,?,?,?,?)'.format(name),dataset)
    conn.commit()




    return cur.lastrowid

def delete_task(conn, id):
    """
    Delete a task by task id
    :param conn:  Connection to the SQLite database
    :param id: id of the task
    :return:
    """
    sql = 'DELETE FROM tasks WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, (id,))


def delete_all_tasks(conn):
    """
    Delete all rows in the tasks table
    :param conn: Connection to the SQLite database
    :return:
    """
    sql = 'DELETE FROM tasks'
    cur = conn.cursor()
    cur.execute(sql)



def select_all_tasks(conn):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks")
 
    rows = cur.fetchall()
 
    for row in rows:
        print(row)



import functions as func
import statistics
import sqlite3

import mnemonics as mn
import sql_interface as sql
import condition as cond

#module does: 
#
#
#
#

#create filename string
directory='/home/daniel/STScI/trainigData/set_1_15min/'

filenames=[
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


def once_a_day_routine(path, conn): 

    #read data in file "path"  and return dictionary with mnemonic and astropy table 
    m = func.mnemonics(path)

    #prepare condition for data retrieval 
    con_set_1 = [                                               \
    cond.equal(m.mnemonic('IMIR_HK_IMG_CAL_LOOP'),'OFF'),       \
    cond.equal(m.mnemonic('IMIR_HK_IFU_CAL_LOOP'),'OFF'),       \
    cond.equal(m.mnemonic('IMIR_HK_POM_LOOP'),'OFF'),           \
    cond.smaller(m.mnemonic('IMIR_HK_ICE_SEC_VOLT1'),1),        \
    cond.greater(m.mnemonic('SE_ZIMIRICEA'),0.2)]
    #setup condition
    condition_1=cond.condition(con_set_1)


    for mnemonic_nam in mn.mnemonic_cond_1:

        dataset=func.extract_useful_data(condition_1, m.mnemonic(mnemonic_nam))

        if dataset is None:
            print('no data for {}'.format(mnemonic_nam))    
        else:
            sql.add_data(conn,mnemonic_nam, dataset)

    del condition_1

    print('Values for condition 1 extracted: {}'.format(filename))

    #
    #
    #
    #
    #
    #
    #

    #prepare condition for data retrieval 
    con_set_2 = [                                               \
    cond.greater(m.mnemonic('SE_ZIMIRFPEA'),0.5),       \
    cond.equal(m.mnemonic('IGDP_IT_MIR_IC_STATUS'),'DETECTOR READY'),       \
    cond.equal(m.mnemonic('IGDP_IT_MIR_LW_STATUS'),'DETECTOR READY')]
    #setup condition
    condition_2=cond.condition(con_set_2)

    for mnemonic_nam in mn.mnemonic_cond_2:

        dataset=func.extract_useful_data(condition_2, m.mnemonic(mnemonic_nam))

        if dataset is None:
            print('no data for {}'.format(mnemonic_nam))    
        else:
            sql.add_data(conn,mnemonic_nam, dataset)

    del condition_1

    print('Values for condition 2 extracted: {}'.format(filename))
    



# create initial database or check if all tables are setup 
db_file = "MIRI_mnemonics.db"
conn = sql.create_connection(db_file)
sql.create_database(conn, mn.mnemonic_set)

path = directory + filenames[0]
once_a_day_routine(path,conn)

sql.close_connection(conn)
print('programm end')
#####################################
#programm end 
def extract_useful_data(condition, mnemonic):

    temp = []

    #look for all values that fit to the given conditions
    for element in mnemonic:
       # print('at %6.8f appears %6.8f',element['Primary Time'],element['EU Value']))
        if condition.state( float(element['Secondary Time'])):

            print("condition true: value= {}, time= {}".format(str(element['EU Value']),str(element['Secondary Time'])))

            temp.append(float(element['EU Value']))

    length= len(temp)


    if length > 2:
        average = sum(temp) / length 
        deviation=statistics.stdev(temp)
        del temp[:]
        return (float(mnemonic['Secondary Time'][0]), float(mnemonic['Secondary Time'][-1]), length, average, deviation)
    else: 
        return None




def extract_filterpos(condition, ratio_mnem, pos_mnem):
    '''Extracts to filterpositions corresponding ratio values 
    Parameters
    ----------
    condition : object 
        conditon object that holds one or more subconditions
    ratio_mem : AstropyTable 
        holds ratio values of one specific mnemonic 
    pos_mem : AstropyTable
        holds pos values of one specific mnemonic
    Return
    ------
    pos_values : dict 
        holds ratio values and times with corresponding pos label
    '''

    pos_values = defaultdict(list)

    #do for every position in mnemonic
    for pos in pos_mnem:

        interval = condition.get_interval(pos['time'])

        if interval is not None:
            cur_pos_time = pos['time']
            filtername = pos['value']

            for ratio in ratio_mnem: 

                if (ratio['time'] == cur_pos_time) and (abs(float(ratio['value'])) > 0.1): 
                    if (ratio['time'] > interval[0]) and (ratio['time'] < interval[1]): 
                        pos_values[pos['value']].append( ( ratio['time'], ratio['value']) )
                        break
    return pos_values
