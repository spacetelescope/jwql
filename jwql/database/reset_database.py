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

from jwql.database.database_interface import base
from jwql.utils.utils import get_config


if __name__ == '__main__':

    connection_string = get_config()['connection_string']
    server_type = connection_string.split('@')[-1][0]

    assert server_type != 'p', 'Cannot reset production database!'

    prompt = ('About to reset all tables for database instance {}. Do you '
              'wish to proceed? (y/n)\n'.format(connection_string))
    response = input(prompt)

    if response.lower() == 'y':
        base.metadata.drop_all()
        base.metadata.create_all()
        print('\nDatabase instance {} has been reset'.format(connection_string))
