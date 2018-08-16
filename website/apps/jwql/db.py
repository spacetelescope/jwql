"""Connects to the ``jwql`` database.

This module is the primary interface between the ``jwql`` webapp and
the ``jwql`` database. It uses ``SQLAlchemy`` to start a session with
the database, and provides class methods that perform useful queries on
that database (for example, getting the names of all the files
associated with a certain instrument).

Authors
-------

    - Lauren Chambers

Use
---
    This module can be used as such:

    ::
        from db import DatabaseConnection
        db_connect = DatabaseConnection()
        data = db_connect.get_filenames_for_instrument('NIRCam')

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in ``jwql/utils/`` directory.
"""

import os

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from astroquery.mast import Mast

from jwql.utils.utils import get_config


class DatabaseConnection:
    """Facilitates connection with the ``jwql`` database.

    Attributes
    ----------
    ObservationWebtest : obj
        Class instance in an "automap" schema corresponding to the
        ``observationwebtest`` database table
    session : obj
        Session with the database that enables querying
    """

    def __init__(self, db_type, instrument=None):
        """Determine what kind of database is being queried, and
        call appropriate initialization method
        """

        self.db_type = db_type

        assert self.db_type in ['MAST', 'SQL'], \
            'Unrecognized database type: {}. Must be SQL or MAST.'.format(db_type)

        if self.db_type == 'MAST':
            self.init_MAST(instrument)
        elif self.db_type == 'SQL':
            self.init_SQL()

    def init_SQL(self):
        """Start SQLAlchemy session with the ``jwql`` database"""

        # Get database credentials from config file
        connection_string = get_config()['database']['connection_string']

        # Connect to the database
        engine = create_engine(connection_string)

        # Allow for automapping of database tables to classes
        Base = automap_base()

        # Reflect the tables in the database
        Base.prepare(engine, reflect=True)

        # Find the observations table
        self.ObservationWebtest = Base.classes.observations_webtest

        # Start a session to enable queries
        self.session = Session(engine)

    def init_MAST(self, instrument=None):
        """Determine the necessary service string to query the MAST
        database.
        """

        # Correctly format the instrument string
        if instrument:
            instrument = instrument[0].upper() + instrument[1:].lower()
        else:
            raise TypeError('Must provide instrument to initialize MAST database.')

        # Define the service name for the given instrument
        self.service = "Mast.Jwst.Filtered." + instrument
        print(self.service)


    def get_files_for_instrument(self, instrument):
        """Given an instrument, query the database for all filenames
        and paths associated with said instrument

        Parameters
        ----------
        instrument : str
            Name of JWST instrument

        Returns
        -------
        filepaths: list
            List of all filepaths in database for the provided
            instrument
        filenames: list
            List of all filenames in database for the provided
            instrument
        """

        instrument = instrument.upper()

        if self.db_type == 'SQL':
            results = self.session.query(self.ObservationWebtest)\
                .filter(self.ObservationWebtest.instrument == instrument)
        elif self.db_type == 'MAST':
            params = {"columns": "*",
                      "filters": []}
            response = Mast.service_request_async(self.service, params)
            results = response[0].json()['data']

        filepaths = []
        filenames = []
        for i in results:
            if self.db_type == 'SQL':
                filename = i.filename
            elif self.db_type == 'MAST':
                filename = i['filename']
            prog_id = filename[2:7]
            file_path = os.path.join('jw' + prog_id, filename)
            filepaths.append(file_path)
            filenames.append(filename)

        return filepaths, filenames
