"""Module holds functions to generate and access sqlite databases

The module is tailored for use in miri data trending. It holds functions to
create and close connections to a sqlite database. Calling the module itself
creates a sqlite database with specific tables used at miri data trending.

Authors
-------
    - Daniel Kühbacher

Use
---
    import the module as follow:
    >>>jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql


Dependencies
------------
    no external files needed

References
----------

Notes
-----

"""


import sqlite3
from sqlite3 import Error
import jwql.instrument_monitors.miri_monitors.data_trending.utils.mnemonics as m



def create_connection(db_file):
    """Sets up a connection or builds database
    Parameters
    ----------
    db_file : string
        represents filename of database
    Return
    ------
    conn : DBobject or None
        Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        print('Connected to database "{}"'.format(db_file))
        return conn
    except Error as e:
        print(e)
    return None


def close_connection(conn):
    '''Closes connection to database
    Parameters
    ----------
    conn : DBobject
        Connection object to be closed
    '''
    conn.close()
    print('Connection closed')


def add_data(conn, mnemonic, data):

    c = conn.cursor()

    #check if data already exists (start_time as identifier)
    c.execute('SELECT id from {} WHERE start_time= {}'.format(mnemonic, data[0]))
    temp = c.fetchall()

    if len(temp) == 0:
        c.execute('INSERT INTO {} (start_time,end_time,data_points,average,deviation) \
                VALUES (?,?,?,?,?)'.format(mnemonic),data)
        conn.commit()
    else:
        print('data already exists')


def add_wheel_data(conn, mnemonic, data):

    c = conn.cursor()

    #check if data already exists (start_time)
    c.execute('SELECT id from {} WHERE timestamp = {}'.format(mnemonic, data[0]))
    temp = c.fetchall()

    if len(temp) == 0:
        c.execute('INSERT INTO {} (timestamp, value) \
                VALUES (?,?)'.format(mnemonic),data)
        conn.commit()
    else:
        print('data already exists')



def query_data(conn, mnemonic, column):
    """Requests the database for given column
    Parameters
    ----------
    conn : database object
        represents link to database
    mnemonic : str
        Contains the name of the requested mnemonic
    column : list
        contains names of columns which are requested
    Returns
    -------
    list
        contains queried data
    """
    c = conn.cursor()

    data = []

    c.execute(' SELECT start_time, average, deviation  FROM {} ORDER BY start_time'.format(mnemonic, column))

    data=c.fetchall()

    return data

def query_pos(conn, mnemonic, column):
    """Requests the database for given column
    Parameters
    ----------
    conn : database object
        represents link to database
    mnemonic : str
        Contains the name of the requested mnemonic
    column : list
        contains names of columns which are requested
    Returns
    -------
    list
        contains queried data
    """
    c = conn.cursor()

    data = []

    c.execute(' SELECT timestamp, value  FROM {} ORDER BY timestamp'.format(mnemonic, column))

    data=c.fetchall()

    return data

def main():
    ''' Creates SQLite database with tables proposed in mnemonics.py'''

    while True:
        name = input("choose name and location of database:")
        conn = create_connection(path)

        if conn != None:
            break
        else:
            pass

    c=conn.cursor()

    for mnemonic in m.mnemonic_set_database:
        try:
            c.execute('CREATE TABLE IF NOT EXISTS {} (         \
                                        id INTEGER,                     \
                                        start_time REAL,                \
                                        end_time REAL,                  \
                                        data_points REAL,               \
                                        average REAL,                   \
                                        deviation REAL,                 \
                                        performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\
                                        PRIMARY KEY (id));'.format(mnemonic))
        except Error as e:
            print('e')

    for mnemonic in m.mnemonic_wheelpositions:
        try:
            c.execute('CREATE TABLE IF NOT EXISTS {} (         \
                                        id INTEGER,            \
                                        timestamp REAL,        \
                                        value REAL,            \
                                        performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\
                                        PRIMARY KEY (id));'.format(mnemonic))
        except Error as e:
            print('e')

    print("Database initial setup complete")
    conn.commit()
    close_connection(conn)

#
if __name__ == "__main__":
    main()
    print("sql_interface.py done")
