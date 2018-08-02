"""
A module to interact with the JWQL postgresql database ``jwqldb``

The ``load_connection()`` function within this module allows the user
to connect to the ``jwqldb`` database via the ``session``, ``base``,
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
    Joe Filippazzo, Johannes Sahlmann, Matthew Bourque

"""

import pandas as pd
from ..utils import utils
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.query import Query
from datetime import datetime

# SETTINGS = utils.get_config()
SETTINGS = {'connection_string': 'sqlite://'}


# Monkey patch Query with data_frame method
def data_frame(self):
    """Method to return a pandas.DataFrame of the results"""
    return pd.read_sql(self.statement, self.session.bind)


Query.data_frame = data_frame


def load_connection(connection_string):
    """Return ``session``, ``base``, ``engine``, and ``metadata`` objects for
    connecting to the ``jwqldb`` database.

    Create an ``engine`` using an given ``connection_string``. Create a
    ``base`` class and ``session`` class from the ``engine``. Create an
    instance of the ``session`` class. Return the ``session``,
    ``base``, and ``engine`` instances.

    Stolen from https://github.com/spacetelescope/acsql/blob/master/acsql/
    database/database_interface.py

    Parameters
    ----------
    connection_string : str
        A postgresql database connection string. The
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
    meta: metadata object
        The connection metadata
    """
    engine = create_engine(connection_string, echo=False)
    base = declarative_base(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    meta = MetaData()

    return session, base, engine, meta


session, base, engine, meta = load_connection(SETTINGS['connection_string'])


class Anomaly(base):
    """ORM for the anomalies table"""
    # Name the table
    __tablename__ = 'anomalies'

    # Define the columns
    id = Column(Integer, primary_key=True, nullable=False)
    filename = Column(String, nullable=False)
    flag_date = Column(DateTime, nullable=False, default=datetime.now())
    bowtie = Column(Boolean, nullable=False, default=False)
    dragon = Column(Boolean, nullable=False, default=False)
    snowball = Column(Boolean, nullable=False, default=False)

    def __repr__(self):

        # Get the columns that are True
        a_list = [col for col, val in self.__dict__.items()
                  if val is True and isinstance(val, bool)]

        return """Anomaly {0.id}: {0.filename} flagged at {0.flag_date} for \
{1}""".format(self, a_list)


base.metadata.create_all(engine)
