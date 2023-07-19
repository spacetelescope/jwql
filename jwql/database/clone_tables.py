#! /usr/bin/env python

"""Clone a table (or tables) from the ``jwqldb`` databases. In particular, this script
supports cloning a table (or tables) into ``pandas`` frames, and supports writing a 
``pandas`` frame into a database table. The intent of the script is to let a table (or all 
the tables related to a particular monitor) from production to be copied to either the 
test or dev database, to allow for local testing that can match the state of the 
production database.

Note that, before using this script, you must ensure that the source and destination 
table(s) have the same columns and, if you want an exact copy, the destination table 
should be emtpy. For the above reasons, unless you have a compelling reason not to do so,
you should run the ``reset_database.py`` script before running this script.

The intended workflow is that you first read a set of tables from production::

    python clone_tables.py read -m bad_pixel

Then, after moving the pandas file(s) to the appropriate server, write them::

    python clone_tables.py write -m bad_pixel

*These commands work because they are not intended to be run on the same server or as the 
same user.*

Authors
-------

    - Brian York

Use
---

    This script is intended to be used in the command line:
    ::

        python clone_tables.py {write|read} [-i instrument] [-m monitor] [-t tables]

Dependencies
------------

    Users must have a ``config.json`` configuration file with a proper
    ``connection_string`` key that points to the ``jwqldb`` database.
    The ``connection_string`` format is
    ``postgresql+psycopg2://user:password@host:port/database``.
"""

import argparse
import os
import sys

import pandas

from jwql.database import database_interface
from jwql.database.database_interface import INSTRUMENT_TABLES, MONITOR_TABLES


if __name__ == '__main__':

    ins_help = "Instrument tables to clone"
    mon_help = "Monitor tables to clone"
    tab_help = "Individual tables to clone (comma-separated list)"
    action_help = "Action to take (read or write)"
    parser = argparse.ArgumentParser(description='Reset JWQL database tables')
    parser.add_argument('action', metavar='ACTION', type=str, help=action_help)
    parser.add_argument('-i', '--instrument', metavar='INSTRUMENT', type=str,
                        help=ins_help, default=None, dest='instrument')
    parser.add_argument('-m', '--monitor', metavar='MONITOR', type=str,
                        help=mon_help, default=None, dest='monitor')
    parser.add_argument('-t', '--table', metavar='TABLE', type=str,
                        help=tab_help, default=None, dest='table')
    args = parser.parse_args()
    
    if args.instrument is not None:
        instrument = args.instrument.lower()
        active_tables = INSTRUMENT_TABLES[instrument]
    elif args.monitor is not None:
        monitor = args.monitor.lower()
        active_tables = MONITOR_TABLES[monitor]
    elif args.table is not None:
        table_list = args.table.split(",")
        active_tables = []
        for table in table_list:
            if hasattr(database_interface, table):
                active_tables.append(getattr(database_interface, table))
            else:
                print("ERROR: Unknown table {}. Skipping.".format(table))
        if len(active_tables) == 0:
            print("ERROR: No tables selected.")
            sys.exit(1)
    else:
        print("ERROR: Must specify one (and only one) of instrument, monitor, or table")
        sys.exit(1)
    
    action = args.action.lower()
    if action == 'read': # read tables to pandas
        for table in active_tables:
            frame = database_interface.session.query(table).data_frame
            frame.to_csv(table.__tablename__+'.csv.gz')
    elif action == 'write': # write pandas to tables
        for table in active_tables:
            file_name = table.__tablename__+'.csv.gz'
            if not os.path.isfile(file_name):
                print("ERROR: Archive {} not found. Skipping.".format(file_name))
                continue
            frame = pandas.read_csv(file_name)
            frame.to_sql(table.__tablename__, database_interface.engine)
    else:
        print("ERROR: Unknown action {}".format(action))
