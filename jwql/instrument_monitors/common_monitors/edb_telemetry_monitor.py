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

    def filter_daily_mean_data(self, data, dep_list, start_time, end_time):
        """


        Paramters
        ---------
        dep_list : list
            List of dependencies for a given mnemonic. Each element of the list
            is a dictionary containing the keys: name, relation, and threshold.


        for each dependency, query the EDB and get the telelmetry values.
        Save them somehow. Then, during the next query of the same mnemonic,
        check to see if it exists, and if the time span of the existing data include
        that you are looking to query. If so, just use the data. If not, query the ebd
        and use that data, but also combine the new query results with the old, so
        that we can potentially save the query the third time, etc.

        How do we save it?
        self.query_reuslts = {}
        self.query_results['MNEMONIC_NAME_HERE'] = {"times": time_values, "data":data_values}



        """
        for dependency in dep_list:
            if dependency["name"] in self.query_results:

                # We need the full time to be covered
                if ((np.min(self.query_results[dependency["name"]]["times"]) > start_time) and
                    (np.max(self.query_results[dependency["name"]]["times"]) < end_time)):
                    matching_times = np.where((self.query_results[dependency["name"]]["times"] > start_time) and
                                              (self.query_results[dependency["name"]]["times"] < end_time))
                    dep_times = self.query_results[dependency["name"]]["times"][matching_times]
                    dep_data = self.query_results[dependency["name"]]["data"][matching_times]
                else:
                    # Query the EDB.
                    mnemonic_data = ed.get_mnemonic(mnemonic, start_time, end_time)
                    dep_times = mnemonic_data.times
                    dep_data = mnemonic_data.data

                    # This is to save the data so that we may avoid an EDB query next time
                    # Add the new data to the saved query results
                    all_times = np.append(self.query_results[dependency["name"]]["times"], mnemonic_data.data['times'])
                    #times_sorted = np.argsort(all_times)
                    #all_times = all_times[times_sorted]
                    all_data = np.append(self.query_results[dependency["name"]]["data"], mnemonic_data.data['data'])#[times_sorted]

                    # Returns the unique values, the index of the first occurrence of a value, and the count for each element
                    final_times, unique_idx = np.unique(all_times, return_index=True)
                    self.query_results[dependency["name"]]["times"] = final_times
                    self.query_results[dependency["name"]]["data"] = all_data[unique_idx]

                # Now find the times when the dependency data satisfy the requirement
                if dependency["relation"] in ['<', '>', '=']:
                    relation_statement = '{} {} {}'.format(dependency["name"], dependency["relation"], dependency["threshold"])
                elif dependency["relation"] in ['ON', 'OFF']:
                    relation_statement = '{} == {}'.format(dependency["name"], dependency["relation"])
                good_data = eval(relation_statement)

                # If there are matching times, then filter the original mnemonic's data
                if np.any(good_data):
                    do it here
                    check existing conditional classes. maybe we can use some of that code




    def identify_tables(self):
        """Determine which database tables to use for a run of the dark
        monitor
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]
        self.db_table = eval('{}EDBMnemonics'.format(mixed_case_name))

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
            for mnemonic in mnemonic_dict['daily_means']:
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
                query_end_times = query_times + self.daily_mean_delta[instrument]

                # Make sure the end time of the final query is before the current time
                if query_end_times[-1] > today:
                    query_start_times = query_start_times[0:-1]
                    query_end_times = query_end_times[0:-1]

                # Loop over the query times, and query the EDB
                for starttime, endtime in zip(query_start_times, query_end_times):

                    # Query the EDB.
                    mnemonic_data = ed.get_mnemonic(mnemonic, starttime, endtime)

                    # Filter the data
                    good_mnemonic_data = filter_daily_mean_data(mnemonic_data, mnemonic['dependency'], starttime, endtime)

                    # If the filtered data contains enough entries, then proceed.
                    if len(good_mnemonic_data.data) > 0:
                        mean_val, std_val = calc_stats(good_mnemonic_data.data)

                        # Save the averaged/smoothed data and dates/times to the edb_mnemonics_monitor database
                        #      Just as with other monitors
                        self.add_new_db_entry(mnemonic, averaged_times, averaged_data)

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

