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
import matplotlib
matplotlib.use('Agg')
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRSpecGratingQueryHistory, NIRSpecGratingStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, GRATING_TELEMETRY
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.monitor_utils import update_monitor_table
from jwql.utils.utils import initialize_instrument_monitor


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
        # note that grating_val gets bogged down if running over a long time period. Can run in smaller chunks of time, eg:
        # start_telemetry_time = Time(Time('2019-01-28 00:00:00.000', format='iso'), format='decimalyear')
        # end_telemetry_time = Time(Time('2019-02-15 00:01:00.000', format='iso'), format='decimalyear')

        # Construct new entry for this file for the grating wheel database table.
        grating_val = get_mnemonic('INRSI_GWA_MECH_POS', start_telemetry_time, end_telemetry_time)
        type_error = False
        for telem in GRATING_TELEMETRY.keys():
            if 'POSITION' in telem:
                grating = telem.split('_')[0]
                telemetry = telem.replace(grating + "_", "")
            else:
                telemetry = telem
            try:
                mnemonic = get_mnemonic(telemetry, start_telemetry_time, end_telemetry_time)
            except TypeError:
                type_error = True
                logging.info("TypeError because data was empty; try using earlier start date to run grating_monitor. Data should be present already.")

            # include placeholder values for other telemetry in order to insert into database
            other_telems = GRATING_TELEMETRY.keys()
            other_telems_dict = {}
            for telems in other_telems:
                other_telems_dict[telems.lower()] = None
            other_telems_dict.pop(telem.lower())

            if type_error is False:
                for time in mnemonic.data['MJD']:
                    if 'POSITION' in telem:
                        # Grating wheel x and y positions are recorded sporadically when the GWA is moved, whereas most telemetry is recorded on a regular time interval
                        # Find the previous grating wheel value that was recorded closest to the time the mnemonic value was recorded
                        # We expect the telemetry to be recorded within the past 14 days
                        # see https://jira.stsci.edu/browse/JSDP-1810
                        # Telemetry values that exhibit this behavior include INRSI_GWA_X_TILT_AVGED, INRSI_GWA_Y_TILT_AVGED,
                        # INRSI_C_GWA_X_POSITION, INRSI_C_GWA_Y_POSITION, INRSI_C_GWA_X_POS_REC, INRSI_C_GWA_Y_POS_REC, INRSI_GWA_TILT_TEMP
                        try:
                            min_distance = np.min(grating_val.data['MJD'][np.where(grating_val.data['MJD'] > time)] - time)
                            if min_distance > 14:
                                logging.warning("Grating retrieved may not match grating for which voltage is being determined")
                            closest_location = np.where((grating_val.data['MJD'] - time) == min_distance)[0][0]
                            grating_used = grating_val.data['euvalue'][closest_location]
                        except ValueError:
                            logging.warning("Using next rather than previous gwa val")
                            min_distance = np.min(abs(grating_val.data['MJD'] - time))
                            closest_location = np.where(abs(grating_val.data['MJD'] - time) == min_distance)[0][0]
                            grating_used = grating_val.data['euvalue'][closest_location]
                        if grating_used == grating:
                            try:
                                grating_db_entry = {'time': time,
                                                    telem.lower(): float(mnemonic.data['euvalue'][np.where(mnemonic.data['MJD'] == time)]),
                                                    'run_monitor': True,  # Update if monitor_run is set to False
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
                            # Not adding entry because data is for a "grating_used" other than the "grating" specified
                            continue
                    else:
                        try:
                            grating_db_entry = {'time': time,
                                                telem.lower(): float(mnemonic.data['euvalue'][np.where(mnemonic.data['MJD'] == time)]),
                                                'run_monitor': True,  # Update if monitor_run is set to False
                                                'entry_date': datetime.datetime.now()  # need slightly different times to add to database
                                                }
                            grating_db_entry.update(other_telems_dict)
                            # Add this new entry to the grating database table
                            self.stats_table.__table__.insert().execute(grating_db_entry)
                            logging.info('\tNew entry added to grating database table: {}'.format(grating_db_entry))
                        except TypeError:
                            logging.warning("may be skipping a value with same entry_date.")
                            continue
            else:
                logging.warning("There was a TypeError causing this data entry to fail.")

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
        # as the start time in the new MAST search. Could include a 30 day
        # buffer to catch any missing telemetry, but this would include
        # quite a lot of extra data and increase run time.
        most_recent_search = self.most_recent_search()
        self.query_start = most_recent_search
        logging.info('\tQuery times: {} {}'.format(self.query_start, self.query_end))

        self.process()
        monitor_run = True
        # If there is a case when we wouldn't want to run the monitor, it could be included here, with monitor_run set to False.
        # However, we should be updating these plots on the daily schedule becuase the telemetry will be updated frequently.

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