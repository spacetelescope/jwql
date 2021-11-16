#! /usr/bin/env python

"""Engineering Database Mnemonics Trending Monitor (EDB Trending Monitor)

more description here
"""
import datetime
import os

from astropy.io import ascii
from astropy.time import Time

from jwql.database.database_interface import NIRCamEDBMnemonics, NIRISSEDBMnemonics, MIRIEDBMnemonics, \
                                             FGSEDBMnemonics, NIRSpecEDBMnemonics
from jwql.edb import engineering_database as ed
from jwql.utils.constants import JWST_INSTRUMENT_NAMES


# To query the EDB for a single mnemonic
#starttime = Time('2019-01-16T00:00:00.000')
#endtime = Time('2019-01-16T00:01:00.000')
#mnemonic = 'IMIR_HK_ICE_SEC_VOLT4'
#mnemonic_data = ed.get_mnemonic(mnemonic, starttime, endtime)

"""
m.mnemonic_identifier
Out[12]: 'IMIR_HK_ICE_SEC_VOLT4'

In [14]: m.requested_start_time
Out[14]: <Time object: scale='utc' format='isot' value=2019-01-16T00:00:00.000>

In [15]: m.requested_end_time
Out[15]: <Time object: scale='utc' format='isot' value=2019-01-16T00:01:00.000>

In [16]: m.data_start_time
Out[16]: <Time object: scale='utc' format='mjd' value=58498.99995387731>

In [17]: m.data_end_time
Out[17]: <Time object: scale='utc' format='mjd' value=58499.000712395835>

In [18]: m.meta
Out[18]:
{'status': 'COMPLETE',
 'msg': '',
 'fields': [{'name': 'theTime', 'type': 'date'},
  {'name': 'MJD', 'type': 'float'},
  {'name': 'euvalue', 'type': 'float'},
  {'name': 'sqldataType', 'type': 'string'}],
 'paging': {'page': 1,
  'pageSize': 50000,
  'pagesFiltered': 1,
  'rows': 17,
  'rowsFiltered': 17,
  'rowsTotal': 17}}

In [19]: m.info
Out[19]:
{'subsystem': 'MIRI',
 'tlmMnemonic': 'IMIR_HK_ICE_SEC_VOLT4',
 'tlmIdentifier': 210961,
 'description': 'MIR Housekeeping Packet ICE Motor Secondary Voltage 4',
 'sqlDataType': 'real',
 'unit': 'V',
 'longDescription': None}

In [20]: m.data
Out[20]:
<Table length=17>
       theTime               MJD          euvalue   sqldataType
        str21              float64        float64       str4
--------------------- ------------------ ---------- -----------
/Date(1547596796015)/  58498.99995387731   4.611158        real
/Date(1547596800111)/  58499.00000128472   4.608176        real
/Date(1547596804207)/  58499.00004869213 4.60519457        real
/Date(1547596808303)/  58499.00009609954   4.602213        real
/Date(1547596812399)/  58499.00014350694 4.61413956        real
/Date(1547596816495)/ 58499.000190914354   4.611158        real
/Date(1547596820591)/  58499.00023832176   4.608176        real
/Date(1547596824687)/  58499.00028572917 4.60519457        real
/Date(1547596828783)/  58499.00033313657   4.602213        real
/Date(1547596832879)/ 58499.000380543985 4.61413956        real
/Date(1547596836975)/  58499.00042795139   4.611158        real
/Date(1547596841071)/  58499.00047535879   4.611158        real
/Date(1547596845167)/ 58499.000522766204   4.608176        real
/Date(1547596849263)/  58499.00057017361 4.60519457        real
/Date(1547596853359)/  58499.00061758102   4.602213        real
/Date(1547596857455)/  58499.00066498842 4.61413956        real
/Date(1547596861551)/ 58499.000712395835   4.611158        real
"""

# To query for a list of mnemonics
#m_list = ['SA_ZFGOUTFOV', 'IMIR_HK_ICE_SEC_VOLT4']
#q = ed.get_mnemonics(m_list, starttime, endtime)

"""
result is an ordered dictionary of EdbMnemonic objects, as shown above
q.keys()
Out[8]: odict_keys(['SA_ZFGOUTFOV', 'IMIR_HK_ICE_SEC_VOLT4'])
"""


class EDBMnemonicMonitor():
    def __init__(self):
        pass

    def add_new_db_entry(self, telem_name, times, data, query_time):
        """
        """
        # Construct new entry for dark database table
        db_entry = {'mnemonic': telem_name,
                    'latest_query': query_time,
                    'times': times,
                    'data': data,
                    'entry_date': datetime.datetime.now()
                    }
        self.db_table.__table__.insert().execute(db_entry)

    def calc_daily_stats(self, data):
        """Calculate the mean value for daily averaged data
        """
        #mean_val = np.mean(data["data"])
        #c, low, upp = sigmaclip(a, fact, fact)
        return sigma_clipped_stats(data["data"], sigma=3)


    def filter_telemetry(self, data, dep_list):
        """
        Filter telemetry data for a single mnemonic based on a list of
        conditions/dependencies, as well as a time.

        Parameters
        ----------
        data : jwql.edb.engineering_database.EdbMnemonic
            Information and query results for a single mnemonic

        dep_list : list
            List of dependencies for a given mnemonic. Each element of the list
            is a dictionary containing the keys: name, relation, and threshold.

        Returns
        -------
        filtered_data : jwql.edb.engineering_database.EdbMnemonic
            Filtered information and query results for a single mnemonic
        """
        all_conditions = []
        for dependency in dep_list:

            # Get the mnemonic times and values for the given start_time and end_time window.
            dep_mnemonic = self.get_dependency_data(dependency, data.start_time, data.end_time)

            # Add the condition to the conditions list
            if dependency["relation"] == '=':
                all_conditions.append(cond.equal(dep_mnemonic, dependency["threshold"]))
            elif dependency["relation"] == '>':
                all_conditions.append(cond.greater_than(dep_mnemonic, dependency["threshold"]))
            elif dependency["relation"] == '<':
                all_conditions.append(cond.less_than(dep_mnemonic, dependency["threshold"]))
            else:
                raise ValueError("Unrecognized dependency relation for {}: {}".format(dependency["name"], dependency["relation"]))

        # Now find the mnemonic's data that during times when all conditions were met
        if len(all_conditions) > 0:
            full_condition = cond.condition(all_conditions)
            filtered_data = cond.extract_data(full_condition, data)
            need to make sure we keep filtered_data as an EdbMnemonic object instance
            return filtered_data
        else:
            return None


    def get_dependency_data(self, dependency, starttime, endtime):
        """Find EDB data for the mnemonic listed as a dependency. Keep a dcitionary up to
        date with query results for all dependencies, in order to minimize the number of
        queries we have to make. Return the requested dependency's time and data values.

        Parameters
        ----------
        dependency : str
            Mnemonic to seach for

        starttime :

        endtime :

        Returns
        -------
        dep_mnemonic : dict
            Data for the dependency mnemonic. Keys are "times" and "data"
        """
        # If we have already queried the EDB for the dependency's data in the time
        # range of interest, then use that data rather than re-querying.
        if dependency["name"] in self.query_results:

            # We need the full time to be covered
            if ((self.query_results[dependency["name"]].start_time > starttime) and
                (self.query_results[dependency["name"]].end_time < endtime)):




                matching_times = np.where((self.query_results[dependency["name"]]["times"] > starttime) and
                                          (self.query_results[dependency["name"]]["times"] < endtime))
                dep_mnemonic = {"times": self.query_results[dependency["name"]]["times"][matching_times],
                                    "data": self.query_results[dependency["name"]]["data"][matching_times]}
            else:
                # If we haven't yet queried the EDB for the dependency, or what we have
                # doesn't cover the time range we need, then query the EDB.
                mnemonic_data = ed.get_mnemonic(dependency["name"], starttime, endtime)
                dep_mnemonic = {"times": mnemonic_data["data"].data, "data": menmonic_data["data"].data}

                # This is to save the data so that we may avoid an EDB query next time
                # Add the new data to the saved query results
                all_times = np.append(self.query_results[dependency["name"]]["times"], mnemonic_data.data['times'])
                all_data = np.append(self.query_results[dependency["name"]]["data"], mnemonic_data.data['data'])#[times_sorted]

                # Save only the unique elements, in case we are adding overlapping data
                final_times, unique_idx = np.unique(all_times, return_index=True)
                self.query_results[dependency["name"]]["times"] = final_times
                self.query_results[dependency["name"]]["data"] = all_data[unique_idx]
        else:
            mnemonic_data = ed.get_mnemonic(dependency["name"], starttime, endtime)
            dep_mnemonic = {"times": mnemonic_data["data"].data, "data": menmonic_data["data"].data}
            self.query_results[dependency["name"]]["times"] = mnemonic_data["data"].data
            self.query_results[dependency["name"]]["data"] = menmonic_data["data"].data
        return dep_mnemonic






    def identify_tables(self):
        """Determine which database tables to use for a run of the dark
        monitor
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.db_table = eval('{}EDBMnemonics'.format(mixed_case_name))

    def get_query_duration(self, duration_string):
        """Turn the string version of the EDB query duration into an astropy
        quantity. Allowed duration_string values include "daily_means",
        "every_change", "block_means", or "X_UNIT", where X is a number, and
        UNIT is a unit of time. (e.g. "5_min")

        Parameters
        ----------
        duration_string : str
            Length of time for the query

        Returns
        -------
        time : astropy.units.quantity.Quantity
        """
        if duration_string.lower() == 'daily_means':
            time = 15. * u.minute
        elif duration_string in ["every_change", "block_means"]:
            time = 1. * u.day
        else:
            # Here we assume the string has the format X_UNIT,
            # where X is a number, and UNIT is a unit of time
            try:
                length, unit = duration_string.split('_')
                length = float(length)

                if "min" in unit:
                    unit = u.minute
                elif "sec" in unit:
                    unit = u.second
                elif "hour" in unit:
                    unit = u.hour
                elif "day" in unit:
                    unit = u.day
                else:
                    raise ValueError("Unsupported time unit: {}".format(unit))

                time = length * unit

            except ValueError:
                raise ValueError("Unexpected/unsupported mnemonic duration string: {}".format(duration_string))

        return time


    def most_recent_search(self, telem_name):
        """Query the database and return the information
        on the most recent query, indicating the last time the
        EDB Mnemonic monitor was executed.

        Returns
        -------
        query_result : float
            Date (in MJD) of the ending range of the previous query
        """
        query = session.query(self.db_table).filter(self.db.mnemonic == telem_name).order_by(self.query_table.latest_query).all()

        if len(query) == 0:
            base_time = '2015-12-01'
            query_result = Time(base_time)  # a.k.a. Dec 1, 2015 == CV3
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'.format(self.mnemonic, base_time)))
        else:
            query_result = query[-1].latest_query

        return query_result


    def run(self):
        """
        """
        # This is a dictionary that will hold the query results for multiple mnemonics,
        # in an effort to minimize the number of EDB queries and save time.
        self.query_results = {}


        # Loop over all instruments
        for instrument in JWST_INSTRUMENT_NAMES:

            # Read in a list of mnemonics that the instrument teams want to monitor
            #     From either a text file, or a edb_mnemonics_montior database table
            monitor_dir = os.path.abspath(__file__)
            mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', '{}_mnemonics_to_monitor.json')
            with open(mnemonic_file) as json_file:
                mnemonic_dict = json.load(json_file)

            # Check the edb_mnemonics_monitor database table to see the date of the previous query
            # as is done in other monitors
            self.identify_tables()

            # Do we keep separate "full day" and "15 minute" mnemonic lists? For MIRI, the difference
            # between these two is that those in the "15minute" list had values that don't change much or
            # quickly over time. So you only need to retrieve a few minutes worth of data in order to calculate
            # a good mean value. However, there are still conditions to apply to these. What if the 15-minute
            # window happens to be at a time when the conditions are not met?
            # It seems like we could query all mnemonics over the entire day to maximize the change that the condition
            # will be met. The trade off is that this may be slower (need to test this).




            # Query the EDB for all mnemonics for the period of time between the previous query and the current date
            # Use exsiting JWQL EDB code - as shown above (move to within the loop over mnemonics to allow
            # a custom query time for each)
            today = Time.now()
            #q = ed.get_mnemonics(mnemonics_to_monitor, starttime, endtime)

            # "Daily" mnemonics. For these, we query only for a small set time range each day.
            # Filter the data to keep that which conforms to the dependencies, then calculate
            # a single mean value for the day
            #for mnemonic in mnemonic_dict['daily_means'] + mnemonic_dict['block_means'] + ...:  ?
            for telem_type in mnemonic_dict:
                # Figure out the time period over which the mnemonic should be queried
                query_duration = get_query_duration(telem_type)

                for mnemonic in mnemonic_dict[telem_type]:
                    # Find the end time of the previous query. In this case where we are querying over only
                    # some subset of the day, set the previous query time to be the start of the previous
                    # query. Given this, it is easy to simply add a day to the previous query time in order
                    # to come up with the new query time.
                    most_recent_search = self.most_recent_search(mnemonic['name'])
                    starttime = most_recent_search + 1.  # THIS ASSUMES UNITS OF MJD, AND BAKES IN A 1-DAY CADENCE

                    # Check for the case where, for whatever reason, there have been missed days. If so, we need
                    # to run the calculations separately for each day. Should we query for the full time and then
                    # filter, or query once per day? The latter is probably slower. Could the former turn into a
                    # problem if e.g. someone wants to track a new mnemonic and it's been 100 days since the
                    # default most recent search time?
                    query_start_times = np.arange(startime, today, 1.)  # This again assumes MJD
                    query_end_times = query_times +  query_duration

                # Make sure the end time of the final query is before the current time
                if query_end_times[-1] > today:
                    query_start_times = query_start_times[0:-1]
                    query_end_times = query_end_times[0:-1]

                # Loop over the query times, and query the EDB
                for starttime, endtime in zip(query_start_times, query_end_times):

                    # Query the EDB. An astropy table is returned.
                    mnemonic_data = ed.get_mnemonic(mnemonic, starttime, endtime)

                    # Filter the data
                    good_mnemonic_data = filter_telemetry(mnemonic_data, mnemonic['dependency'])


                    Above here, I think everything should be identical for all types of mnemonics (daily, block, every_change, etc)


                    # If the filtered data contains enough entries, then proceed.
                    if len(good_mnemonic_data["data"]) > 0:

                        if mnemonic in mnemonic["daily_means":]
                            mean_val, median_val, std_val = calc_daily_stats(good_mnemonic_data["data"])
                            median_times = np.median(good_mnemonic_data["times"])
                        elif mnemonic in mnemonic["block_means"]:
                            mean_val, median_val, std_val, median_times = calc_block_averages(good_mnemonic_data["data"])
                        elif mnemonic in mnemonic["every_change"]:
                            pass
                        elif mnemonic in mnemonic["time_interval"]:
                            pass
                        elif mnemonic in mnemonic["none"]:
                            pass
                        # Save the averaged/smoothed data and dates/times to the edb_mnemonics_monitor database
                        #      Just as with other monitors
                        self.add_new_db_entry(mnemonic, median_time, mean_val, stdev_val)
                    else:
                        pass
                        # self.logger.info("Mnemonic {} has no data that match the requested conditions.".format(mnemonic))

                    # Re-create the plot for the mnemonic, adding the new data
                    # Can probably steal some of the data trending code for this

                    # Display the plot on the web app


            # "Each instance" mnemonics. For these, we query for the entire day. Then filter the data
            # to keep that which conforms to the dependencies. For each block of data kept (i.e. each
            # continuous block of time where the dependencies are satisfied), calculate a mean value.
            # The result will be a mean value for each block of time.
            for mnemonic in mnemonic_dict['each_instance']:
                # Set the previous query time to be the start of the previous
                # query. Given this, it is easy to simply add a day to the previous query time in order
                # to come up with the new query time.
                most_recent_search = self.most_recent_search(mnemonic['name'])
                starttime = most_recent_search + 1.  # THIS ASSUMES UNITS OF MJD, AND BAKES IN A 1-DAY CADENCE

                # Check for the case where, for whatever reason, there have been missed days. If so, we need
                # to run the calculations separately for each day. Should we query for the full time and then
                # filter, or query once per day? The latter is probably slower. Could the former turn into a
                # problem if e.g. someone wants to track a new mnemonic and it's been 100 days since the
                # default most recent search time?
                query_start_times = np.arange(startime, today, 1.)  # This again assumes MJD
                query_end_times = query_times + self.each_instance_delta[instrument]

                # Make sure the end time of the final query is before the current time
                if query_end_times[-1] > today:
                    query_start_times = query_start_times[0:-1]
                    query_end_times = query_end_times[0:-1]

                # Loop over the query times, and query the EDB
                for starttime, endtime in zip(query_start_times, query_end_times):

                    # Query the EDB.
                    mnemonic_data = ed.get_mnemonic(mnemonic, starttime, endtime)

                    # Filter the data
                    good_mnemonic_data = filter_each_instance_data(mnemonic_data, mnemonic['dependency'])

                    # If the filtered data contains enough entries, then proceed.
                    if len(good_mnemonic_data.data) > 0:
                        mean_val, std_val = calc_stats(good_mnemonic_data.data)

                        # Save the averaged/smoothed data and dates/times to the edb_mnemonics_monitor database
                        #      Just as with other monitors
                        self.add_new_db_entry(mnemonic, averaged_times, averaged_data)

                    # Re-create the plot for the mnemonic, adding the new data
                    # Can probably steal some of the data trending code for this

                    # Display the plot on the web app


            # "Every change" mnemonics. These are similar to the "each instance" mnemonics above, except
            # that there is no filtering by dependency value. We break the data up into blocks again, but
            # this time the end of one block and start of another is simply a change in the data value.
            for mnemonic in mnemonic_dict['every_change']:
                # Set the previous query time to be the start of the previous
                # query. Given this, it is easy to simply add a day to the previous query time in order
                # to come up with the new query time.
                most_recent_search = self.most_recent_search(mnemonic['name'])
                starttime = most_recent_search + 1.  # THIS ASSUMES UNITS OF MJD, AND BAKES IN A 1-DAY CADENCE

                # Check for the case where, for whatever reason, there have been missed days. If so, we need
                # to run the calculations separately for each day. Should we query for the full time and then
                # filter, or query once per day? The latter is probably slower. Could the former turn into a
                # problem if e.g. someone wants to track a new mnemonic and it's been 100 days since the
                # default most recent search time?
                query_start_times = np.arange(startime, today, 1.)  # This again assumes MJD
                query_end_times = query_times + self.every_change_delta[instrument]

                # Make sure the end time of the final query is before the current time
                if query_end_times[-1] > today:
                    query_start_times = query_start_times[0:-1]
                    query_end_times = query_end_times[0:-1]

                # Loop over the query times, and query the EDB
                for starttime, endtime in zip(query_start_times, query_end_times):

                    # Query the EDB.
                    mnemonic_data = ed.get_mnemonic(mnemonic, starttime, endtime)

                    # Filter the data
                    good_mnemonic_data = filter_every_change_data(mnemonic_data, mnemonic['dependency'])

                    # If the filtered data contains enough entries, then proceed.
                    if len(good_mnemonic_data.data) > 0:
                        mean_val, std_val = calc_stats(good_mnemonic_data.data)

                        # Save the averaged/smoothed data and dates/times to the edb_mnemonics_monitor database
                        #      Just as with other monitors
                        self.add_new_db_entry(mnemonic, averaged_times, averaged_data)

                    # Re-create the plot for the mnemonic, adding the new data
                    # Can probably steal some of the data trending code for this

                    # Display the plot on the web app











# Other options:
# A separate "previous query" time for each mnemonic?
# Johannes built a function to query for many mnemonics but with a single start and end time
# If no data are returned for a particular mnemonic, then skip all the updating. If data are
# returned the next time, we should still be able to update the plot without having lost any
# information. Using a single date will keep things simpler.
#
# BUT: what about a case where a team tracks a mnemonic for a while, then decides to stop, and
# then returns to tracking it later? If we use a single previous query time, then that mnemonic
# will end up with a hole in it's plot for the time that the mnemonic wasn't tracked. If we keep
# a separate time for each mnemonic, then the plot will always be complete. The downsides of this
# are that 1) we need to store more data in the database and 2) Now we need a separate query for
# each mnemonic, which will probably slow things down

