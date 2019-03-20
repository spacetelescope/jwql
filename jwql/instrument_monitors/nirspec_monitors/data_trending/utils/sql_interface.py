"""Module holds functions to generate and access sqlite databases

The module is tailored for use in miri data trending. It holds functions to
create and close connections to a sqlite database. Calling the module itself
creates a sqlite database with specific tables used at miri data trending.

Authors
-------
    - Daniel Kühbacher

Use
---

Dependencies
------------
    import mnemonics as m

References
----------

Notes
-----

"""
import os
import sqlite3
from sqlite3 import Error

import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as m
from jwql.utils.utils import get_config, filename_parser

def create_connection(db_file):
    '''Sets up a connection or builds database
    Parameters
    ----------
    db_file : string
        represents filename of database
    Return
    ------
    conn : DBobject or None
        Connection object or None
    '''
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
    '''Add data of a specific mnemonic to database if it not exists
    Parameters
    ----------
    conn : DBobject
        connection object to access database
    mnemonic : string
        identifies the table
    data : list
        specifies the data
    '''

    c = conn.cursor()

    #check if data already exists (start_time as identifier)
    c.execute('SELECT id from {} WHERE start_time= {}'.format(mnemonic, data[0]))
    temp = c.fetchall()

    if len(temp) == 0:
        c.execute('INSERT INTO {} (start_time,end_time,data_points,average,deviation) \
                VALUES (?,?,?,?,?)'.format(mnemonic),data)
        conn.commit()
    else:
        print('data for {} already exists'.format(mnemonic))


def add_wheel_data(conn, mnemonic, data):
    '''Add data of a specific wheel position to database if it not exists
    Parameters
    ----------
    conn : DBobject
        connection object to access database
    mnemonic : string
        identifies the table
    data : list
        specifies the data
    '''

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


def main():
    ''' Creates SQLite database with tables proposed in mnemonics.py'''

    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

    #generate paths
    DATABASE_LOCATION = os.path.join(get_config()['jwql_dir'], 'database')
    DATABASE_FILE = os.path.join(DATABASE_LOCATION, 'nirspec_database.db')

    conn = create_connection(DATABASE_FILE)

    c=conn.cursor()

    for mnemonic in m.mnemonic_set_database:
        try:
            c.execute('CREATE TABLE IF NOT EXISTS {} (         \
                                        id INTEGER,                     \
                                        start_time REAL,                \
                                        end_time REAL,                  \
                                        data_points INTEGER,               \
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

#sets up database if called as main
if __name__ == "__main__":
    main()
    print("sql_interface.py done")
