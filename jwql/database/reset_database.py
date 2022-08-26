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

from jwql.database.database_interface import base, set_read_permissions, INSTRUMENT_TABLES
from jwql.utils.utils import get_config


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Reset JWQL database tables')
    parser.add_argument('instrument', metavar='INSTRUMENT', type=str,
                        help='instrument tables to reset ("all" for all)',
                        default='all')
    args = parser.parse_args()

    instrument = args.instrument

    connection_string = get_config()['connection_string']
    server_type = connection_string.split('@')[-1][0]

    assert server_type != 'p', 'Cannot reset production database!'

    prompt = ('About to reset {} tables for database instance {}. Do you '
              'wish to proceed? (y/n)\n'.format(instrument, connection_string))
    response = input(prompt)

    if response.lower() == 'y':
        if instrument.lower() == 'all':
            base.metadata.drop_all()
            base.metadata.create_all()
        elif instrument.lower() in ['nircam', 'nirspec', 'niriss', 'miri', 'fgs']:
            tables = [x.__table__ for x in INSTRUMENT_TABLES[instrument]]
            base.metadata.drop_all(tables=tables)
            base.metadata.create_all(tables=tables)
        else:
            raise ValueError("Unknown instrument {}".format(instrument))
        set_read_permissions()
        print('\nDatabase instance {} has been reset'.format(connection_string))
