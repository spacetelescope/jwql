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
    - Lauren Chambers
    - Bryan Hilbert

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
import os
import socket

import pandas as pd
from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy import create_engine
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Time
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.types import ARRAY

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

# Import a global session.  If running from readthedocs, pass a dummy connection string
if 'build' and 'project' and 'jwql' in socket.gethostname():
    dummy_connection_string = 'postgresql+psycopg2://account:password@hostname:0000/db_name'
    session, base, engine, meta = load_connection(dummy_connection_string)
else:
    SETTINGS = utils.get_config()
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


class Monitor(base):
    """ORM for the ``monitor`` table"""

    # Name the table
    __tablename__ = 'monitor'

    id = Column(Integer, primary_key=True)
    monitor_name = Column(String(), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(Enum('SUCESS', 'FAILURE', name='monitor_status'), nullable=True)
    affected_tables = Column(postgresql.ARRAY(String, dimensions=1), nullable=True)
    log_file = Column(String(), nullable=False)


def get_monitor_columns(data_dict, table_name):
    """Read in the corresponding table definition text file to
    generate ``SQLAlchemy`` columns for the table.

    Parameters
    ----------
    data_dict : dict
        A dictionary whose keys are column names and whose values
        are column definitions.
    table_name : str
        The name of the database table

    Returns
    -------
    data_dict : dict
        An updated ``data_dict`` with the approriate columns for
        the monitor added.
    """

    # Define column types
    data_type_dict = {'integer': Integer(),
                      'string': String(),
                      'float': Float(precision=32),
                      'decimal': Float(precision='13,8'),
                      'date': Date(),
                      'time': Time(),
                      'datetime': DateTime,
                      'bool': Boolean}

    # Get the data from the table definition file
    table_definition_file = os.path.join(os.path.split(__file__)[0],
                                         'monitor_table_definitions',
                                         '{}.txt'.format(table_name))
    with open(table_definition_file, 'r') as f:
        data = f.readlines()

    # Parse out the column names from the data types
    column_definitions = [item.strip().split(', ') for item in data]
    for column_definition in column_definitions:
        column_name = column_definition[0]
        data_type = column_definition[1]

        # Create a new column
        if data_type in list(data_type_dict.keys()):
            data_dict[column_name.lower()] = Column(data_type_dict[data_type])
        else:
            raise ValueError('Unrecognized column type: {}:{}'.format(column_name, data_type))

    return data_dict


def get_monitor_table_constraints(data_dict, table_name):
    """Add any necessary table constrains to the given table via the
    ``data_dict``.

    Parameters
    ----------
    data_dict : dict
        A dictionary whose keys are column names and whose values
        are column definitions.
    table_name : str
        The name of the database table

    Returns
    -------
    data_dict : dict
        An updated ``data_dict`` with the approriate table constraints
        for the monitor added.
    """

    return data_dict


def monitor_orm_factory(class_name):
    """Create a ``SQLAlchemy`` ORM Class for a ``jwql`` instrument
    monitor.

    Parameters
    ----------
    class_name : str
        The name of the class to be created

    Returns
    -------
    class : obj
        The ``SQLAlchemy`` ORM
    """

    # Initialize a dictionary to hold the column metadata
    data_dict = {}
    data_dict['__tablename__'] = class_name.lower()

    # Columns specific to all monitor ORMs
    data_dict['id'] = Column(Integer, primary_key=True, nullable=False)
    data_dict['entry_date'] = Column(DateTime, unique=True, nullable=False, default=datetime.now())
    data_dict['__table_args__'] = (UniqueConstraint('id', 'entry_date', name='monitor_uc'),)

    # Get monitor-specific columns
    data_dict = get_monitor_columns(data_dict, data_dict['__tablename__'])

    # Get monitor-specific table constrains
    data_dict = get_monitor_table_constraints(data_dict, data_dict['__tablename__'])

    return type(class_name, (base,), data_dict)

# Create tables from ORM factory
# NIRCamDarkQueries = monitor_orm_factory('nircam_dark_queries')
# NIRCamDarkPixelStats = monitor_orm_factory('nircam_dark_pixel_stats')
# NIRCamDarkDarkCurrent = monitor_orm_factory('nircam_dark_dark_current')


if __name__ == '__main__':

    base.metadata.create_all(engine)
