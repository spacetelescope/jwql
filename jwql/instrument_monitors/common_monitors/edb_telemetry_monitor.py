#! /usr/bin/env python

"""Engineering Database Mnemonics Trending Monitor (EDB Trending Monitor)

more description here
"""
import datetime
import numpy as np
import os

from astropy.io import ascii
from astropy.stats import sigma_clipped_stats
from astropy.time import Time

from jwql.database.database_interface import NIRCamEDBMnemonics, NIRISSEDBMnemonics, MIRIEDBMnemonics, \
                                             FGSEDBMnemonics, NIRSpecEDBMnemonics
from jwql.edb import engineering_database as ed
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import utils
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


class EdbMnemonicMonitor():
    def __init__(self):
        self.query_results = {}

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

    def calc_block_stats(self, mnem_data, sigma=3):
        """Calculate stats for a mnemonic where we want a mean value for
        each block of good data, where blocks are separated by times where
        the data are ignored.

        Parameters
        ----------
        mnem_data : jwql.edb.engineering_database.EdbMnemonic
            class instance

        sigma : int
            Number of sigma to use for sigma clipping

        Returns
        -------
        mnem_data : jwql.edb.engineering_database.EdbMnemonic
            Class instance with telemetry statistics added

        move this to be an attribute of EdbMnemonic class
        """
        means = []
        medians = []
        stdevs = []
        medtimes = []
        for i, index in enumerate(mnem_data.blocks[0:-1]):
            meanval, medianval, stdevval = sigma_clipped_stats(mnem_data.data["data"][index:mnem_data.blocks[i+1]], sigma=sigma)
            medtimes.append(np.median(mnem_data.data["MJD"][index:mnem_data.blocks[i+1]]))

        #    OR:
        #for time_tup in mnem_data.time_pairs:
        #    good = np.where((mnem_data.data["MJD"] >= time_tup[0]) & (mnem_data.data["MJD"] < time_tup[1]))
        #    meanval, medianval, stdevval = sigma_clipped_stats(mnem_data.data["data"][good], sigma=sigma)
        #    medtimes.append(np.median(mnem_data.data["MJD"][good]))



            means.append(meanval)
            medians.append(medianval)
            stdevs.append(stdevval)
        mnem_data.mean = means
        mnem_data.median = medians
        mnem_data.stdev = stdevs
        mnem_data.median_time = medtimes
        return mnem_data

    def calc_daily_stats(self, data, sigma=3):
        """Calculate the mean value for daily averaged data

        Parameters
        ----------
        data : dict
            "data" and "MJD" keys

        sigma : int
            Number of sigma to use for sigma clipping

        move this to be an attribute of EdbMnemonic class
        """
        #mean_val = np.mean(data["data"])
        #c, low, upp = sigmaclip(a, fact, fact)
        return sigma_clipped_stats(data["data"], sigma=sigma)

    def calc_every_change_stats(self, mnem_data):
        """Calculate stats for telemetry data for each
        """
        pass

    def calc_timed_stats(self, mnem_data, bintime, sigma=3):
        """Calculate stats for telemetry using time-based averaging.
        This works on data that have potentially been filtered. How do
        we treated any breaks in the data due to the filtering? Enforce
        a new bin at each filtered block of data? Blindly average by
        time and ignore any missing data due to filtering? The former
        makes more sense to me

        Parameters
        ----------
        mnem_data : jwql.edb.engineering_database.EdbMnemonic

        bintime : astropy.time.Quantity

        Returns
        -------
        all_means

        all_meds

        all_stdevs

        all_times
        """
        # what are the units of mnem_data.data["MJD"]? A: MJD
        all_means = []
        all_meds = []
        all_stdevs = []
        all_times = []

        minimal_delta = 1 * u.sec  # modify based on units of time
        for i in range(len(mnem_data.blocks)-1):
            block_min_time = mnem_data.data["MJD"][mnem_data.blocks[i]]
            block_max_time = mnem_data.data["MJD"][mnem_data.blocks[i+1]]
            bin_times = np.arange(block_min_time, block_max_time+minimal_delta, bintime)
            all_times.extend((bin_times[1:] - bin_times[0:-1]) / 2.)  # for plotting later

            for b_idx in range(len(bin_times)-1):
                good_points = np.where((mnem_data.data["MJD"] >= bin_times[b_idx]) & (mnem_data.data["MJD"] < bin_times[b_idx+1]))
                bin_mean, bin_med, bin_stdev = sigma_clipped_stats(mnem_data.data["data"][good_points], sigma=sigma)
                all_means.append(bin_mean)
                all_meds.append(bin_med)
                all_stdevs.append(bin_stdev)
        return all_means, all_meds, all_stdevs, all_times

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
        filtered : jwql.edb.engineering_database.EdbMnemonic
            Filtered information and query results for a single mnemonic
        """
        if len(dep_list) == 0:
            return data

        all_conditions = []
        for dependency in dep_list:

            # Get the mnemonic times and values for the given start_time and end_time window.
            dep_mnemonic = self.get_dependency_data(dependency, data.start_time, data.end_time)

            # Add the condition to the conditions list
            if dependency["relation"] == '=':

                print(dep_mnemonic)
                print(dependency)
                junk = cond.equal(dep_mnemonic, dependency["threshold"])
                print('time_pairs:', junk.time_pairs)

                all_conditions.append(junk)
            elif dependency["relation"] == '>':
                all_conditions.append(cond.greater_than(dep_mnemonic, dependency["threshold"]))
            elif dependency["relation"] == '<':
                all_conditions.append(cond.less_than(dep_mnemonic, dependency["threshold"]))
            else:
                raise ValueError("Unrecognized dependency relation for {}: {}".format(dependency["name"], dependency["relation"]))

        # Now find the mnemonic's data that during times when all conditions were met
        if len(all_conditions) > 0:
            full_condition = cond.condition(all_conditions)
            filtered_data, block_indexes = cond.extract_data(full_condition, data.data)

        # Put the results into an instance of EdbMnemonic
        new_start_time = np.min(filtered_data["MJD"])
        new_end_time = np.max(filtered_data["MJD"])
        filtered = EdbMnemonic(data.mnemonic_identifier, new_start_time, new_end_time, filtered_data, data.meta, data.info, blocks=block_indexes)
        return filtered

    def find_all_changes(self, mnem_data, dep_list, threshold=3):
        """Identify indexes of data to create separate blocks for each value of the
        condition. This is for the "every_change" mnemonics, where we want to create a
        mean value for all telemetry data acquired for each value of some dependency
        mnemonic.

        For now, this function assumes that we only have one dependency. I'm not sure
        how it would work with multiple dependencies.
        """
        if len(dep_list) > 1:
            raise NotImplementedError("Not sure how to work with every_change data with multiple dependencies.")

        dependency = self.query_results[dep_list[0]["name"]]

        # Locate the times where the dependency value changed by a large amount
        # Then for each block, calculate a sigma-clipped mean and stdev
        first_diffs = np.abs(dependency.data["data"].data[1:] - dependency.data["data"].data[0:-1])
        full_mean, full_med, full_dev = sigma_clipped_stats(first_diffs, sigma=3)
        jumps = np.where(first_diffs >= threshold*full_dev)[0]



        print(full_mean, full_med, full_dev, threshold*full_dev)
        print(first_diffs)
        print(jumps)



        #OR:
        #create a histogram of dependency["data"], find the peaks, and group points around those

        # Add 1 so that the indexes refer to the first element of each block
        jumps += 1
        jump_times = dependency.data["MJD"][jumps]

        print(jumps)
        print(dependency.data["MJD"])
        print(jump_times)

        # Do we need to calucate and save the mean values of the dependency at each block?
        all_dep_means = []
        all_dep_meds = []
        all_dep_devs = []
        all_dep_times = []
        for i in range(len(jumps)-1):
            dep_block = dependency.data["data"][jumps[i]:jumps[i+1]]
            mean_dep_val, med_dep_val, dev_dep_val = sigma_clipped_stats(dep_block, sigma=3)
            all_dep_means.append(mean_dep_val)
            all_dep_meds.append(med_dep_val)
            all_dep_devs.append(dev_dep_val)
            all_dep_times.append(np.median(dependency.data["MJD"][jumps[i]:jumps[i+1]]))

        # Now calculate the mean and stdev for the elements between each pair of jump times
        all_means = []
        all_meds = []
        all_devs = []
        all_times = []
        for i in range(len(jump_times)):
            block_points = np.where((mnem_data.data["MJD"] >= jump_times[i]) & (mnem_data.data["MJD"] < jump_times[i+1]))
            mean_val, med_val, dev_val = sigma_clipped_stats(mnem_data.data["data"][block_points], sigma=3)
            all_means.append(mean_val)
            all_meds.append(med_val)
            all_devs.append(dev_val)
            all_times.append(np.median(mnem_data.data["MJD"][block_points]))
        return all_means, all_meds, all_devs, all_times, all_dep_means, all_dep_meds, all_dep_devs, all_dep_times




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
            Data for the dependency mnemonic. Keys are "MJD" and "data"
        """
        # If we have already queried the EDB for the dependency's data in the time
        # range of interest, then use that data rather than re-querying.
        if dependency["name"] in self.query_results:

            # We need the full time to be covered
            if ((self.query_results[dependency["name"]].start_time <= starttime) and
                (self.query_results[dependency["name"]].end_time >= endtime)):

                matching_times = np.where((self.query_results[dependency["name"]].data["MJD"] > starttime) and
                                          (self.query_results[dependency["name"]].data["MJD"] < endtime))
                dep_mnemonic = {"MJD": self.query_results[dependency["name"]].data["MJD"][matching_times],
                                    "data": self.query_results[dependency["name"]].data["data"][matching_times]}
            else:
                # If what we have doesn't cover the time range we need, then query the EDB.
                mnemonic_data = ed.get_mnemonic(dependency["name"], starttime, endtime)
                dep_mnemonic = {"MJD": mnemonic_data.data["MJD"], "data": menmonic_data.data["data"]}

                # This is to save the data so that we may avoid an EDB query next time
                # Add the new data to the saved query results
                all_times = np.append(self.query_results[dependency["name"]].data["MJD"], mnemonic_data.data["MJD"])
                all_data = np.append(self.query_results[dependency["name"]].data["data"], mnemonic_data.data["data"])

                # Save only the unique elements, in case we are adding overlapping data
                final_times, unique_idx = np.unique(all_times, return_index=True)
                new_table = Table()
                new_table["MJD"] = final_times
                new_table["data"] = all_data[unique_idx]
                self.query_results[dependency["name"]].data = new_table
        else:
            self.query_results[dependency["name"]] = ed.get_mnemonic(dependency["name"], starttime, endtime)
            dep_mnemonic = {"MJD": self.query_results[dependency["name"]].data["MJD"],
                            "data": self.query_results[dependency["name"]].data["data"]}
        return dep_mnemonic

    def get_mnemonic_info(name, starting_time, ending_time):
        """Wrapper around the code to query the EDB, filter the result, and calculate
        appropriate statistics for a single mnemonic

        Parameters
        ----------
        name : dict
            Dictionary of information about the mnemonic to be processed. Dictionary
            as read in from the json file of mnemonics

        starting_time : float
            Beginning time for query in MJD

        ending_time : float
            Ending time for query in MJD

        Returns
        -------
        good_mnemonic_data : jwql.edb.engineering_database.EdbMnemonic
            EdbMnemonic instance containing filtered data for the given mnemonic
        """
        # Query the EDB. An astropy table is returned.
        mnemonic_data = ed.get_mnemonic(mnemonic, starttime, endtime)

        # Filter the data - good_mnemonic_data is an EdbMnemonic instance
        if len(mnemonic['dependency']) > 0:
            good_mnemonic_data = filter_telemetry(mnemonic_data, mnemonic['dependency'])
        else:
            # No dependencies here. Keep all the data
            good_mnemonic_data = mnemonic_data
            good_mnemonic_data.blocks = [0]

        if telem_type == "every_change":
            self.find_all_changes(good_mnemonic_data, mnemonic['dependency'])

        # If the filtered data contains enough entries, then proceed.
        if len(good_mnemonic_data.data) > 0:
            #we can make the daily mean, block mean, and timed mean methods of the EdbMnemonic class.
            #what about every change? separate method here? new one there as well?
            if telem_type == "daily_means":
                mean_vals, median_vals, std_vals = self.calc_daily_stats(good_mnemonic_data["data"])
                median_times = np.median(good_mnemonic_data["MJD"])
            elif telem_type == "block_means":
                mean_vals, median_vals, std_vals, median_times = self.calc_block_stats(good_mnemonic_data)
            elif telem_type == "every_change":
                mean_vals, std_vals, median_times = self.calc_every_change_stats(good_mnemonic_data)
            elif telem_type == "time_interval":
                stats_duration = utils.get_averaging_time_duration(mnemonic["mean_time_block"])
                mean_vals, median_vals, std_vals, median_times = self.calc_timed_stats(good_mnemonic_data, stats_duration)
            elif telem_type == "none":
                # No averaging done
                mean_vals = good_mnemonic_data["data"]
                median_times = good_mnemonic_data["MJD"]
            #add means to EdbMnemonic class as an attribute
            return good_mnemonic_data
        else:
            return None

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
                query_duration = utils.get_query_duration(telem_type)

                for mnemonic in mnemonic_dict[telem_type]:

                    if telem_type != 'none':
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

                    else:
                        # In the case where telemetry data have no averaging done, we do not store the data
                        # in the JWQL database, in order to save space. So in this case, we will retrieve
                        # all of the data from the EDB directly, from some default start time until the
                        # present day.
                        query_start_times = np.array([DEFAULT_EDB_QUERY_START_TIME])
                        query_end_times = np.array([today.mjd])

                    # Make sure the end time of the final query is before the current time
                    if query_end_times[-1] > today:
                        valid_end_times = query_end_times <= today
                        query_start_times = query_start_times[valid_end_times]
                        query_end_times = query_end_times[valid_end_times]

                    # Loop over the query times, and query the EDB
                    for starttime, endtime in zip(query_start_times, query_end_times):

                        # This function wraps around the EDB query and telemetry filtering, and
                        # averaging. In this way, when a user requests an updated plot for one of
                        # the mnemonics whose data are not stored in the JWQL database, we can simply
                        # call this function for that specific mnemonic
                        mnemonic_info = self.get_mnemonic_info(mnemonic, starttime, endtime)

                        if mnemonic_info is not None:
                            if telem_type != 'none':
                                # Save the averaged/smoothed data and dates/times to the database,
                                # but only for cases where we are averaging. For cases with no averaging
                                # the database would get too large too quickly. In that case the monitor
                                # will re-query the EDB for the entire history each time.
                                self.add_new_db_entry(mnemonic, median_time, mean_val, stdev_val)
                        else:
                            pass
                            # self.logger.info(f"Mnemonic {mnemonic["name"]} has no data that match the requested conditions.")

                    # How will we prepare for plotting in the case of a mnemonic with no averaging?
                    # If the data are not going to be save in the database, how will we get to it at
                    # plot creation time? Maybe we create and populate a temporary database table?
                    # Or create a plots here and save them to be rendered later?
                    if telem_type == 'none':
                        pass



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

