'''
Interact with the JWQL database
'''

import os

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.txt')

class DatabaseConnection:
    def __init__(self):
        '''Start session with Quicklook database that can be used to query the
        database for information'''

        # Get database credentials from config.txt file
        params = []
        with open(CONFIG) as f:
            for line in f.readlines():
                params.append(line.split()[1])
        dbengine, dbname, dbuser, dbpassword, dbhost, dbport = params

        # Allow for automapping of database tables to classes
        Base = automap_base()

        # Connect to the database
        connection_string = 'postgresql+psycopg2://{}:{}@{}/{}'.format(dbuser, dbpassword, dbhost, dbname)
        engine = create_engine(connection_string)

        # Reflect the tables in the database
        Base.prepare(engine, reflect=True)

        # Find the observations table
        self.ObservationWebtest = Base.classes.observations_webtest

        # Start a session to enable queries
        self.session = Session(engine)

    def get_filenames_for_instrument(self, instrument):
        '''Given an instrument, query the database for all filenames
        associated with said instrument'''
        instrument = instrument.upper()

        results = self.session.query(self.ObservationWebtest)\
            .filter(self.ObservationWebtest.instrument == instrument)

        filenames = []
        for i in results:
            filename = i.filename
            prog_id = filename[2:7]
            file_path = os.path.join(prog_id, filename)
            filenames.append(file_path)

        return filenames
