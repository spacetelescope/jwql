#! /usr/bin/env python

"""This module contains code for the grating wheel monitor, which monitors
the grating wheel positions over time. This code has been adapted from bias_monitor.py

Author
------
    - Teagan King

Use
---
    This module can be used from the command line as such:

    ::

        python grating_monitor.py
"""

import datetime
import logging
import os

from astropy.time import Time
from jwql.edb.engineering_database import get_mnemonic
from jwql.edb.engineering_database import get_mnemonics
import matplotlib
matplotlib.use('Agg')
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRSpecGratingQueryHistory, NIRSpecGratingStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, GRATING_TELEMETRY
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.monitor_utils import update_monitor_table
from jwql.utils.utils import ensure_dir_exists, get_config, initialize_instrument_monitor


class Grating():
    """Class for executing the grating wheel monitor.

    This class will search for a particular mnemonic for each
    instrument and will run the monitor on these files. The monitor 
    will perform statistical measurements and plot the mnemonic data
    in order to monitor the grating wheel telemetry over time.
    Results are all saved to database tables.

    Attributes
    ----------
    query_start : float
        MJD start date to use for querying EDB.

    query_end : float
        MJD end date to use for querying EDB.

    instrument : str
        Name of instrument used to collect the data.
    """

    def __init__(self):
        """Initialize an instance of the ``Grating`` class."""

    def identify_tables(self):
        """Determine which database tables to use for a run of the grating wheel
        monitor.
        """

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.query_table = eval('{}GratingQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}GratingStats'.format(mixed_case_name))

    def most_recent_search(self):
        """Query the query history database and return the information
        on the most recent query where the grating wheel monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous MAST query
            where the grating wheel monitor was run.
        """
        query = session.query(self.query_table).filter(self.query_table.run_monitor == True).order_by(self.query_table.end_time_mjd).all()

        if len(query) == 0:
            query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history. Beginning search date will be set to {}.'.format(query_result)))
        else:
            query_result = query[-1].end_time_mjd

        return query_result

    def process(self):
        """The main method for processing telemetry.  See module docstrings
        for further details.

        """

        start_telemetry_time = Time(Time(self.query_start, format='mjd'), format='decimalyear')
        end_telemetry_time = Time(Time(self.query_end, format='mjd'), format='decimalyear')
        # end_telemetry_time = Time(Time(Time.now(), format='mjd'), format='decimalyear')
        # grating_val gets bogged down if more than about a day

        # Construct new entry for this file for the grating wheel database table.
        retrieved_grat = False
        for telem in GRATING_TELEMETRY.keys():
            # if telem in ['INRSH_GWA_ADCMGAIN', 'INRSH_GWA_ADCMOFFSET', 'INRSH_GWA_MOTOR_VREF']:
            #     continue
            if 'POSITION' in telem:
                grating = telem.split('_')[0]
                telemetry = telem.replace(grating+"_", "")
                if retrieved_grat is False:
                    try:
                        mnemonics = get_mnemonics([telemetry, 'INRSI_GWA_MECH_POS'], start_telemetry_time, end_telemetry_time)
                        mnemonic = mnemonics[telemetry]
                        grating_val = mnemonics['INRSI_GWA_MECH_POS']
                        retrieved_grat = True
                    except TypeError:
                        type_error = True
                        print("type error because data was empty; try using earlier start date if you want this to run. Data should be present already.")
                        # FIGURE OUT HOW TO DEAL WITH THIS ERROR
            else:
                try:
                    mnemonic = get_mnemonic(telem, start_telemetry_time, end_telemetry_time)
                except TypeError:
                    type_error = True
                    print("type error because data was empty 2")
                    continue
            other_telems = GRATING_TELEMETRY.keys()
            other_telems_dict = {}
            for telems in other_telems:
                other_telems_dict[telems.lower()] = None
            other_telems_dict.pop(telem.lower())
            if type_error is False:
                for time in mnemonic.data['MJD']:
                    if 'POSITION' in telem:
                        min_distance = np.min(abs(grating_val.data['MJD']-time))
                        if min_distance > 0.01:  # determine whether this is realistic time difference between data for voltage and grating value
                            logging.warning("Grating retrieved may not match grating for which voltage is being determined")
                        closest_location = np.where(abs(grating_val.data['MJD']-time) == min_distance)[0][0]
                        grating_used = grating_val.data['euvalue'][closest_location]
                        if grating_used == grating:
                            try:
                                grating_db_entry = {'time': time,
                                                    telem.lower(): float(mnemonic.data['euvalue'][np.where(mnemonic.data['MJD'] == time)]),
                                                    'run_monitor': True,  # UPDATE
                                                    'entry_date': datetime.datetime.now()  # need slightly different times to add to database
                                                    }
                                grating_db_entry.update(other_telems_dict)
                                # Add this new entry to the grating database table
                                self.stats_table.__table__.insert().execute(grating_db_entry)
                                logging.info('\tNew entry added to grating database table: {}'.format(grating_db_entry))
                            except TypeError:
                                logging.warning("May be skipping a value with same entry_date")
                                continue
                        else:
                            logging.warning("Not adding entry because data is for {} rather than {}".format(grating_used, grating))
                            continue
                    else:
                        try:
                            grating_db_entry = {'time': time,
                                                telem.lower(): float(mnemonic.data['euvalue'][np.where(mnemonic.data['MJD'] == time)]),
                                                'run_monitor': True,  # UPDATE
                                                'entry_date': datetime.datetime.now()  # need slightly different times to add to database
                                                }
                            grating_db_entry.update(other_telems_dict)
                            # Add this new entry to the grating database table
                            self.stats_table.__table__.insert().execute(grating_db_entry)
                            logging.info('\tNew entry added to grating database table: {}'.format(grating_db_entry))
                        except TypeError:
                            logging.warning("may be skipping a value with same entry_date.")
                            continue

    @log_fail
    @log_info
    def run(self):
        """The main method.  See module docstrings for further details."""

        logging.info('Begin logging for grating_monitor')

        # Use the current time as the end time for MAST query
        self.query_end = Time.now().mjd

        self.instrument = 'nirspec'

        # Identify which database tables to use
        self.identify_tables()

        # Locate the record of most recent MAST search; use this time
        # (plus a 30 day buffer to catch any missing files from
        # previous run) as the start time in the new MAST search.
        most_recent_search = self.most_recent_search()
        self.query_start = most_recent_search  # MAYBE USE 30 DAYS BUFFER BEFORE THAT?
        logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

        self.process()
        monitor_run = True
        # else:  # DETERMINE CASE WHEN DON"T RUN MONITOR-- THERE SHOULD FREQUENTLY BE UPDATED TELEMETRY THOUGH
        #     logging.info('\tGrating monitor skipped. {} new dark files for {}.'.format(len(new_files), self.instrument))
        #     monitor_run = False

        # Update the query history
        new_entry = {'instrument': self.instrument,
                     'start_time_mjd': self.query_start,
                     'end_time_mjd': self.query_end,
                     'run_monitor': monitor_run,
                     'entry_date': datetime.datetime.now()}
        self.query_table.__table__.insert().execute(new_entry)
        logging.info('\tUpdated the query history table')

        logging.info('Grating Monitor completed successfully.')


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    monitor = Grating()
    monitor.run()

    update_monitor_table(module, start_time, log_file)
