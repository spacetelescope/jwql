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

    - Joe Filippazzo
    - Johannes Sahlmann
    - Matthew Bourque

Use
---

    Executing the module on the command line will build the database
    tables defined within:

    ::

        python database_interface.py

    Users wishing to interact with the existing database may do so by
    importing various connection objects and database tables, for
    example:

    ::

        from jwql.database.database_interface import Anomaly
        from jwql.database.database_interface import session

        results = session.query(Anomaly).all()

Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``utils`` directory.
"""

from datetime import datetime
import socket

import pandas as pd
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query

from jwql.utils import utils


# Monkey patch Query with data_frame method
@property
def data_frame(self):
    """Method to return a ``pandas.DataFrame`` of the results"""
    return pd.read_sql(self.statement, self.session.bind)

Query.data_frame = data_frame


def load_connection(connection_string):
    """Return ``session``, ``base``, ``engine``, and ``metadata``
    objects for connecting to the ``jwqldb`` database.

    Create an ``engine`` using an given ``connection_string``. Create
    a ``base`` class and ``session`` class from the ``engine``. Create
    an instance of the ``session`` class. Return the ``session``,
    ``base``, and ``engine`` instances. This was stolen from the
    `ascql` repository.

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

    References
    ----------
    ``ascql``:
        https://github.com/spacetelescope/acsql/blob/master/acsql/database/database_interface.py
    """
    engine = create_engine(connection_string, echo=False)
    base = declarative_base(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    meta = MetaData()

    return session, base, engine, meta


# Import a global session.  If running from readthedocs, pass a dummy connection string
if 'build' and 'project' and 'jwql' in socket.gethostname():
    dummy_connection_string = 'postgresql+psycopg2://account:password@hostname:0000/db_name'
    session, base, engine, meta = load_connection(dummy_connection_string)
else:
    SETTINGS = utils.get_config()
    session, base, engine, meta = load_connection(SETTINGS['connection_string'])


class Anomaly(base):
    """ORM for the ``anomalies`` table"""

    # Name the table
    __tablename__ = 'anomalies'

    # Define the columns
    id = Column(Integer, primary_key=True, nullable=False)
    filename = Column(String, nullable=False)
    flag_date = Column(DateTime, nullable=False, default=datetime.now())
    bowtie = Column(Boolean, nullable=False, default=False)
    snowball = Column(Boolean, nullable=False, default=False)
    cosmic_ray_shower = Column(Boolean, nullable=False, default=False)
    crosstalk = Column(Boolean, nullable=False, default=False)
    cte_correction_error = Column(Boolean, nullable=False, default=False)
    data_transfer_error = Column(Boolean, nullable=False, default=False)
    detector_ghost = Column(Boolean, nullable=False, default=False)
    diamond = Column(Boolean, nullable=False, default=False)
    diffraction_spike = Column(Boolean, nullable=False, default=False)
    dragon_breath = Column(Boolean, nullable=False, default=False)
    earth_limb = Column(Boolean, nullable=False, default=False)
    excessive_saturation = Column(Boolean, nullable=False, default=False)
    figure8_ghost = Column(Boolean, nullable=False, default=False)
    filter_ghost = Column(Boolean, nullable=False, default=False)
    fringing = Column(Boolean, nullable=False, default=False)
    guidestar_failure = Column(Boolean, nullable=False, default=False)
    banding = Column(Boolean, nullable=False, default=False)
    persistence = Column(Boolean, nullable=False, default=False)
    prominent_blobs = Column(Boolean, nullable=False, default=False)
    trail = Column(Boolean, nullable=False, default=False)
    scattered_light = Column(Boolean, nullable=False, default=False)
    other = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        """Return the canonical string representation of the object"""

        # Get the columns that are True
        a_list = [col for col, val in self.__dict__.items()
                  if val is True and isinstance(val, bool)]

        txt = ('Anomaly {0.id}: {0.filename} flagged at '
               '{0.flag_date} for {1}').format(self, a_list)

        return txt

    @property
    def colnames(self):
        """A list of all the column names in this table"""

        # Get the columns
        a_list = [col for col, val in self.__dict__.items()
                  if isinstance(val, bool)]

        return a_list


if __name__ == '__main__':

    base.metadata.create_all(engine)
