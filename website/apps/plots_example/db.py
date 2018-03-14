'''
Interact with the JWQL database
'''

import os
import sys

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Temporary fix until converted into a package...
current_dir = os.getcwd()
parent_dir = os.path.join(os.path.dirname(current_dir), 'utils')
sys.path.insert(0, parent_dir)
from utils import get_config

class DatabaseConnection:
    def __init__(self):
        '''Start session with Quicklook database that can be used to query the
        database for information'''

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

    def get_filepaths_for_instrument(self, instrument):
        '''Given an instrument, query the database for all filenames
        associated with said instrument'''
        instrument = instrument.upper()

        results = self.session.query(self.ObservationWebtest)\
            .filter(self.ObservationWebtest.instrument == instrument)

        filepaths = []
        for i in results:
            filename = i.filename
            prog_id = filename[2:7]
            file_path = os.path.join('jw' + prog_id, filename)
            filepaths.append(file_path)

        return filepaths

    def get_filenames_for_instrument(self, instrument):
        '''Given an instrument, query the database for all filenames
        associated with said instrument'''
        instrument = instrument.upper()

        results = self.session.query(self.ObservationWebtest)\
            .filter(self.ObservationWebtest.instrument == instrument)

        filenames = []
        for i in results:
            filename = i.filename
            filenames.append(filename)

        return filenames
