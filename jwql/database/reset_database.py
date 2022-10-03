#! /usr/bin/env python

"""Reset all tables in the ``jwqldb`` database.

Authors
-------

    - Matthew Bourque

Use
---

    This script is intended to be used in the command line:
    ::

        python reset_database.py

Dependencies
------------

    Users must have a ``config.json`` configuration file with a proper
    ``connection_string`` key that points to the ``jwqldb`` database.
    The ``connection_string`` format is
    ``postgresql+psycopg2://user:password@host:port/database``.
"""

import argparse
from sqlalchemy.exc import ProgrammingError
import sys

from jwql.database.database_interface import base, set_read_permissions
from jwql.database.database_interface import INSTRUMENT_TABLES, MONITOR_TABLES
from jwql.utils.utils import get_config


if __name__ == '__main__':

    ins_help = "Instrument tables to reset ('all' for all), default 'all'"
    mon_help = "Monitor tables to reset ('all' for all), default 'all'"
    parser = argparse.ArgumentParser(description='Reset JWQL database tables')
    parser.add_argument('-i', '--instrument', metavar='INSTRUMENT', type=str,
                        help=ins_help, default='all', dest='instrument')
    parser.add_argument('-m', '--monitor', metavar='MONITOR', type=str,
                        help=mon_help, default='all', dest='monitor')
    parser.add_argument('--explicitly_reset_production', action='store_true',
                        default=False, help='Needed to allow reset of Production tables',
                        dest='explicit_prod')
    parser.add_argument('--explicitly_reset_anomalies', action='store_true',
                        default=False, help='Needed to allow reset of anomaly tables',
                        dest='explicit_anomaly')
    args = parser.parse_args()

    instrument = args.instrument.lower()
    monitor = args.monitor.lower()
    
    if instrument != 'all' and instrument not in INSTRUMENT_TABLES:
        sys.stderr.write("ERROR: Unknown instrument {}".format(instrument))
        sys.exit(1)
    if monitor != 'all' and monitor not in MONITOR_TABLES:
        sys.stderr.write("ERROR: Unknown monitor {}".format(monitor))
        sys.exit(1)

    connection_string = get_config()['connection_string']
    server_type = connection_string.split('@')[-1][0]
    
    if server_type == 'p' and not args.explicit_prod:
        msg = "ERROR: Can't reset production databases without explicitly setting the "
        msg += "--explicitly_reset_production flag!"
        sys.stderr.write(msg)
        sys.exit(1)
    
    if monitor == 'anomaly' and not args.explicit_anomaly:
        msg = "ERROR: Can't reset anomaly tables without explicitly setting the "
        msg += "--explicitly_reset_anomalies flag!"
        sys.stderr.write(msg)
        sys.exit(1)

    msg = 'About to reset instruments: {} and monitors: {} tables for database instance {}. Do you wish to proceed? (y/N)'
    response = input(msg.format(monitor, instrument, connection_string))

    if response.lower() != 'y':
        print("Did not enter y/Y. Stopping.")
        sys.exit(0)
    else:
        tables = []
        if instrument != 'all':
            base_tables = INSTRUMENT_TABLES[instrument]
            if monitor == 'all':
                check_tables = base_tables
            else:
                check_tables = MONITOR_TABLES[monitor]
        elif monitor != 'all':
            base_tables = MONITOR_TABLES[monitor]
            if instrument == 'all':
                check_tables = base_tables
            else:
                check_tables = INSTRUMENT_TABLES[instrument]
        else: # instrument and monitor are both 'all'
            if args.explicit_anomaly: # really delete everything
                base.metadata.drop_all()
                base.metadata.create_all()
                print('\nDatabase instance {} has been reset'.format(connection_string))
                sys.exit(0)
            else:
                for monitor in MONITOR_TABLES:
                    if monitor != 'anomaly':
                        for table in MONITOR_TABLES[monitor]:
                            try:
                                table.__table__.drop()
                            except ProgrammingError as pe:
                                print("*****ERROR*****")
                                print(pe)
                                print("*****ERROR TYPE*****")
                                print(type(pe))
                                print("*****ERROR CODE*****")
                                print(pe.orig)
                                print("*****DONE ERROR CODE*****")
                                raise pe
                            table.__table__.create()
                print('\nDatabase instance {} has been reset'.format(connection_string))
                sys.exit(0)
        
        # Choosing what to reset. We want every table in base_tables that is *also* in
        # check_tables.
        for table in base_tables:
            if table in check_tables:
                if (table not in MONITOR_TABLES['anomaly']) or (args.explicit_anomaly):
                    try:
                        table.__table__.drop()
                    except ProgrammingError as pe:
                        print("*****ERROR*****")
                        print(pe)
                        print("*****ERROR TYPE*****")
                        print(type(pe))
                        print("*****ERROR CODE*****")
                        print(pe.orig)
                        print("*****DONE ERROR CODE*****")
                        raise pe
                    table.__table__.create()
        print('\nDatabase instance {} has been reset'.format(connection_string))
