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

from datetime import datetime

import pandas as pd
from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query

from jwql.utils import utils


SETTINGS = utils.get_config()


# Monkey patch Query with data_frame method
@property
def data_frame(self):
    """Method to return a pandas.DataFrame of the results"""
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
    meta = MetaData(engine)

    # Make sure it has an anomalies table
    if not engine.has_table('anomalies'):
        print("No 'anomalies' table. Generating one now...")

        # Define anomaly table column names
        columns = ['bowtie', 'snowball', 'cosmic_ray_shower', 'crosstalk',
                   'cte_correction_error', 'data_transfer_error', 'detector_ghost',
                   'diamond', 'diffraction_spike', 'dragon_breath', 'earth_limb',
                   'excessive_saturation', 'figure8_ghost', 'filter_ghost',
                   'fringing', 'guidestar_failure', 'banding', 'persistence',
                   'prominent_blobs', 'trail', 'scattered_light', 'other']

        # Create a table with the appropriate Columns
        anomalies = Table('anomalies', meta,
                          Column('id', Integer, primary_key=True, nullable=False),
                          Column('filename', String, nullable=False),
                          Column('flag_date', DateTime, nullable=False, server_default=str(datetime.now())),
                          *[Column(name, String, nullable=False, server_default="False") for name in columns])

        # Implement it
        meta.create_all()

    return session, base, engine, meta


# Load the objects for the database
session, base, engine, meta = load_connection(SETTINGS['connection_string'])


# Make convenience methods for Base class
@property
def colnames(self):
    """A list of all the column names in this table"""
    # Get the columns
    a_list = sorted([col for col, val in self._sa_instance_state.attrs.items()
              if col not in ['id', 'filename', 'flag_date']])

    return a_list


@property
def names(self):
    """A list of human readable names for all the columns in this table"""
    return [name.replace('_', ' ') for name in self.colnames]


# Generate Base class and add methods
Base = automap_base()
Base.colnames = colnames
Base.names = names
Base.prepare(engine, reflect=True)


# Automap Anomaly class from Base class for anomalies table
Anomaly = Base.classes.anomalies


if __name__ == '__main__':

    base.metadata.create_all(engine)
