"""This module provides ORMs for the ``jwql`` database, as well as
``engine`` and ``session`` objects for connecting to the database.

The ``load_connection()`` function within this module allows the user
to connect to the ``jwql`` database via the ``session``, ``base``,
and ``engine`` objects (described below).  The classes within serve as
ORMs (Object-relational mappings) that define the individual tables of
the relational database.

The ``engine`` object serves as the low-level database API and perhaps
most importantly contains dialects which allows the ``sqlalchemy``
module to communicate with the database.

The ``base`` object serves as a base class for class definitions.  It
produces ``Table`` objects and constructs ORMs.

The ``session`` object manages operations on ORM-mapped objects, as
construced by the base.  These operations include querying, for
example.

Authors
-------

    Matthew Bourque
    Bryan Hilbert
    Sara Ogaz

Use
---
    This module is intended to be imported from various ``jwql``
    modules and scripts.  The importable objects from this module are
    as follows:
    ::

        from jwql.database.database_interface import base
        from jwql.database.database_interface import engine
        from jwql.database.database_interface import session
        from jwql.database.database_interface import Master
        from jwql.database.database_interface import Filetypes
        from jwql.database.database_interface import <header_table>

Dependencies
------------
    External library dependencies include:

    - ``jwql``
    - ``sqlalchemy``
"""

from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import create_engine
from sqlalchemy import declarative_base
from sqlalchemy import Enum
from sqlalchemy import sessionmaker
from sqlalehcmy import String


def load_connection(connection_string):
    """Return ``session``, ``base``, and ``engine`` objects for
    connecting to the ``acsql`` database.

    Create an ``engine`` using an given ``connection_string``. Create a
    ``base`` class and ``session`` class from the ``engine``. Create an
    instance of the ``session`` class. Return the ``session``,
    ``base``, and ``engine`` instances.

    Parameters
    ----------
    connection_string : str
        The connection string to connect to the ``acsql`` database. The
        connection string should take the form:
        ``dialect+driver://username:password@host:port/database``

    Returns
    -------
    session : sesson object
        Provides a holding zone for all objects loaded or associated
        with the database.
    base : base object
        Provides a base class for declarative class definitions.
    engine : engine object
        Provides a source of database connectivity and behavior.
    """

    engine = create_engine(connection_string, echo=False, pool_timeout=100000)
    base = declarative_base(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    return session, base, engine


class Master(base):
    """ORM for the  master table."""

    def __init__(self, data_dict):
        self.__dict__.update(data_dict)

    __tablename__ = 'master'
    rootname = Column(String(37), primary_key=True, index=True, nullable=False)
    path = Column(String(21), nullable=False)
    first_ingest_date = Column(Date, nullable=False)
    last_ingest_date = Column(Date, nullable=False)
    instrument = Column(Enum(*get_instrument_list()), nullable=False)
    detector = Column(Enum(*get_detector_list()), nullable=False)
    access_level = Column(Enum('public', 'proprietary'), nullable=False)
    proposal_type = Column(Enum(*get_proposal_type_list()), nullable=False)
