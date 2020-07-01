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
    - Misty Cracraft
    - Sara Ogaz

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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.types import ARRAY

from jwql.utils.constants import ANOMALIES_PER_INSTRUMENT, FILE_SUFFIX_TYPES, JWST_INSTRUMENT_NAMES
from jwql.utils.utils import get_config

ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


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

    return session, base, engine, meta


# Import a global session.  If running from readthedocs or Jenkins, pass a dummy connection string
if 'build' and 'project' in socket.gethostname() or ON_JENKINS:
    dummy_connection_string = 'postgresql+psycopg2://account:password@hostname:0000/db_name'
    session, base, engine, meta = load_connection(dummy_connection_string)
else:
    SETTINGS = get_config()
    session, base, engine, meta = load_connection(SETTINGS['connection_string'])


class FilesystemGeneral(base):
    """ORM for the general (non instrument specific) filesystem monitor
    table"""

    # Name the table
    __tablename__ = 'filesystem_general'

    # Define the columns
    id = Column(Integer, primary_key=True, nullable=False)
    date = Column(DateTime, unique=True, nullable=False)
    total_file_count = Column(Integer, nullable=False)
    total_file_size = Column(Float, nullable=False)
    fits_file_count = Column(Integer, nullable=False)
    fits_file_size = Column(Float, nullable=False)
    used = Column(Float, nullable=False)
    available = Column(Float, nullable=False)


class FilesystemInstrument(base):
    """ORM for the instrument specific filesystem monitor table"""

    # Name the table
    __tablename__ = 'filesystem_instrument'
    __table_args__ = (UniqueConstraint('date', 'instrument', 'filetype',
                                       name='filesystem_instrument_uc'),)

    # Define the columns
    id = Column(Integer, primary_key=True, nullable=False)
    date = Column(DateTime, nullable=False)
    instrument = Column(Enum(*JWST_INSTRUMENT_NAMES, name='instrument_enum'), nullable=False)
    filetype = Column(Enum(*FILE_SUFFIX_TYPES, name='filetype_enum'), nullable=False)
    count = Column(Integer, nullable=False)
    size = Column(Float, nullable=False)

    @property
    def colnames(self):
        """A list of all the column names in this table EXCEPT the date column"""
        # Get the columns
        a_list = [col for col, val in self.__dict__.items()
                  if not isinstance(val, datetime)]

        return a_list


class CentralStore(base):
    """ORM for the central storage area filesystem monitor
    table"""

    # Name the table
    __tablename__ = 'central_storage'

    # Define the columns
    id = Column(Integer, primary_key=True, nullable=False)
    date = Column(DateTime, nullable=False)
    area = Column(String(), nullable=False)
    size = Column(Float, nullable=False)
    used = Column(Float, nullable=False)
    available = Column(Float, nullable=False)


class Monitor(base):
    """ORM for the ``monitor`` table"""

    # Name the table
    __tablename__ = 'monitor'

    id = Column(Integer, primary_key=True)
    monitor_name = Column(String(), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(Enum('SUCCESS', 'FAILURE', name='monitor_status'), nullable=True)
    affected_tables = Column(ARRAY(String, dimensions=1), nullable=True)
    log_file = Column(String(), nullable=False)


def anomaly_orm_factory(class_name):
    """Create a ``SQLAlchemy`` ORM Class for an anomaly table.

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

    instrument = data_dict['__tablename__'].split('_')[0]
    instrument_anomalies = []
    for anomaly in ANOMALIES_PER_INSTRUMENT:
        if instrument in ANOMALIES_PER_INSTRUMENT[anomaly]:
            instrument_anomalies.append(anomaly)

    # Define anomaly table column names
    data_dict['columns'] = instrument_anomalies
    data_dict['names'] = [name.replace('_', ' ') for name in data_dict['columns']]

    # Create a table with the appropriate Columns
    data_dict['id'] = Column(Integer, primary_key=True, nullable=False)
    data_dict['rootname'] = Column(String(), nullable=False)
    data_dict['flag_date'] = Column(DateTime, nullable=False)
    data_dict['user'] = Column(String(), nullable=False)

    for column in data_dict['columns']:
        data_dict[column] = Column(Boolean, nullable=False, default=False)

    return type(class_name, (base,), data_dict)


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
                      'bool': Boolean
                      }

    # Get the data from the table definition file
    instrument = table_name.split('_')[0]
    table_definition_file = os.path.join(os.path.split(__file__)[0],
                                         'monitor_table_definitions',
                                         instrument.lower(),
                                         '{}.txt'.format(table_name))
    with open(table_definition_file, 'r') as f:
        data = f.readlines()

    # Parse out the column names from the data types
    column_definitions = [item.strip().split(', ') for item in data]
    for column_definition in column_definitions:
        column_name = column_definition[0]
        data_type = column_definition[1]

        if 'array' in data_type:
            dtype, _a, dimension = data_type.split('_')
            dimension = int(dimension[0])
            array = True
        else:
            dtype = data_type
            array = False

        # Create a new column
        if dtype in list(data_type_dict.keys()):
            if array:
                data_dict[column_name.lower()] = Column(ARRAY(data_type_dict[dtype],
                                                              dimensions=dimension))
            else:
                data_dict[column_name.lower()] = Column(data_type_dict[dtype])
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
    data_dict['__table_args__'] = (
        UniqueConstraint('id', 'entry_date', name='{}_uc'.format(data_dict['__tablename__'])),
    )

    # Get monitor-specific columns
    data_dict = get_monitor_columns(data_dict, data_dict['__tablename__'])

    # Get monitor-specific table constrains
    data_dict = get_monitor_table_constraints(data_dict, data_dict['__tablename__'])

    return type(class_name, (base,), data_dict)


# Create tables from ORM factory
NIRCamAnomaly = anomaly_orm_factory('nircam_anomaly')
NIRISSAnomaly = anomaly_orm_factory('niriss_anomaly')
NIRSpecAnomaly = anomaly_orm_factory('nirspec_anomaly')
MIRIAnomaly = anomaly_orm_factory('miri_anomaly')
FGSAnomaly = anomaly_orm_factory('fgs_anomaly')
NIRCamDarkQueryHistory = monitor_orm_factory('nircam_dark_query_history')
NIRCamDarkPixelStats = monitor_orm_factory('nircam_dark_pixel_stats')
NIRCamDarkDarkCurrent = monitor_orm_factory('nircam_dark_dark_current')
NIRISSDarkQueryHistory = monitor_orm_factory('niriss_dark_query_history')
NIRISSDarkPixelStats = monitor_orm_factory('niriss_dark_pixel_stats')
NIRISSDarkDarkCurrent = monitor_orm_factory('niriss_dark_dark_current')
NIRSpecDarkQueryHistory = monitor_orm_factory('nirspec_dark_query_history')
NIRSpecDarkPixelStats = monitor_orm_factory('nirspec_dark_pixel_stats')
NIRSpecDarkDarkCurrent = monitor_orm_factory('nirspec_dark_dark_current')
MIRIDarkQueryHistory = monitor_orm_factory('miri_dark_query_history')
MIRIDarkPixelStats = monitor_orm_factory('miri_dark_pixel_stats')
MIRIDarkDarkCurrent = monitor_orm_factory('miri_dark_dark_current')
FGSDarkQueryHistory = monitor_orm_factory('fgs_dark_query_history')
FGSDarkPixelStats = monitor_orm_factory('fgs_dark_pixel_stats')
FGSDarkDarkCurrent = monitor_orm_factory('fgs_dark_dark_current')
NIRCamBiasQueryHistory = monitor_orm_factory('nircam_bias_query_history')
NIRCamBiasStats = monitor_orm_factory('nircam_bias_stats')
NIRCamBadPixelQueryHistory = monitor_orm_factory('nircam_bad_pixel_query_history')
NIRCamBadPixelStats = monitor_orm_factory('nircam_bad_pixel_stats')
NIRISSBadPixelQueryHistory = monitor_orm_factory('niriss_bad_pixel_query_history')
NIRISSBadPixelStats = monitor_orm_factory('niriss_bad_pixel_stats')
FGSBadPixelQueryHistory = monitor_orm_factory('fgs_bad_pixel_query_history')
FGSBadPixelStats = monitor_orm_factory('fgs_bad_pixel_stats')
MIRIBadPixelQueryHistory = monitor_orm_factory('miri_bad_pixel_query_history')
MIRIBadPixelStats = monitor_orm_factory('miri_bad_pixel_stats')
NIRSpecBadPixelQueryHistory = monitor_orm_factory('nirspec_bad_pixel_query_history')
NIRSpecBadPixelStats = monitor_orm_factory('nirspec_bad_pixel_stats')
NIRCamReadnoiseQueryHistory = monitor_orm_factory('nircam_readnoise_query_history')
NIRCamReadnoiseStats = monitor_orm_factory('nircam_readnoise_stats')
NIRISSReadnoiseQueryHistory = monitor_orm_factory('niriss_readnoise_query_history')
NIRISSReadnoiseStats = monitor_orm_factory('niriss_readnoise_stats')

if __name__ == '__main__':

    base.metadata.create_all(engine)
