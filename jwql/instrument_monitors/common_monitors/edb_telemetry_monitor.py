#! /usr/bin/env python

"""Engineering Database Mnemonics Trending Monitor (EDB Trending Monitor)

more description here
"""
import datetime
import json
import numpy as np
import os

from astropy.io import ascii
from astropy.stats import sigma_clipped_stats
from astropy.time import Time, TimeDelta
import astropy.units as u

from jwql.database.database_interface import NIRCamEDBMnemonics, NIRISSEDBMnemonics, MIRIEDBMnemonics, \
                                             FGSEDBMnemonics, NIRSpecEDBMnemonics
from jwql.edb import engineering_database as ed
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import condition
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import utils
from jwql.utils.constants import EDB_LOOK_BACK_TIME, JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config


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

    def add_new_db_entry(self, mnem, query_time):
        """Add a new entry to the database table

        Parameters
        ----------
        mnem : jwql.edb.engineering_database.EdbMnemonic
            Mnemonic information

        query_time : datetime.datetime
            Start time of the query
        """
        # Construct new entry for dark database table
        db_entry = {'mnemonic': mnem.info["name"],
                    'latest_query': query_time,
                    'times': mnem.median_times,
                    'data': mnem.mean,
                    'stdev': mnem.stdev,
                    'entry_date': datetime.datetime.now()
                    }
        self.history_table.__table__.insert().execute(db_entry)

    """
    def calc_block_stats(self, mnem_data, sigma=3):
        Calculate stats for a mnemonic where we want a mean value for
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

    def calc_full_stats(self, data, sigma=3):
        Calculate the mean/median/stdev of the data

        Parameters
        ----------
        data : dict
            "data" and "MJD" keys

        sigma : int
            Number of sigma to use for sigma clipping

        move this to be an attribute of EdbMnemonic class

        return sigma_clipped_stats(data["data"], sigma=sigma)



    def calc_daily_stats(self, data, sigma=3):
        Calculate the statistics for each day in the data
        contained in data["data"]. Should we add a check for a
        case where the final block of time is <<1 day?

        Parameters
        ----------
        data : dict
            "euvalues" and "dates" keys. Values for both keys must
            be numpy arrays rather than lists.

        sigma : int
            Number of sigma to use for sigma clipping

        move this to be an attribute of EdbMnemonic class

        min_date = np.min(data["dates"])
        num_days = (np.max(data["dates"]) - min_date).days

        # If all the data are within a day, set num_days=1 in order to get
        # a starting and ending time within limits below
        if num_days == 0:
            num_days = 1

        limits = np.array([min_date + datetime.timedelta(days=x) for x in range(num_days+1)])
        means, meds, devs, times = [], [], [], []
        for i in range(len(limits) - 1):
            good = np.where((data["dates"] >= limits[i]) & (data["dates"] < limits[i+1]))
            avg, med, dev = sigma_clipped_stats(data["euvalues"][good], sigma=sigma)
            means.append(avg)
            meds.append(med)
            devs.append(dev)
            times.append(limits[i] + (limits[i+1] - limits[i]) / 2.)

        return means, meds, devs, times
    """

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
            block_min_time = mnem_data.data["dates"][mnem_data.blocks[i]]
            block_max_time = mnem_data.data["dates"][mnem_data.blocks[i+1]]
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


            all_conditions.append(condition.relation_test(dep_mnemonic, dependency["relation"], dependency["threshold"]))

            """
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
            """

        # Now find the mnemonic's data that during times when all conditions were met
        full_condition = condition.condition(all_conditions)
        full_condition.extract_data(data.data)
        #filtered_data, block_indexes = cond.extract_data(full_condition, data.data)

        # Put the results into an instance of EdbMnemonic
        new_start_time = np.min(full_condition.extracted_data["dates"])
        new_end_time = np.max(full_condition.extracted_data["dates"])
        filtered = EdbMnemonic(data.mnemonic_identifier, new_start_time, new_end_time, full_condition.extracted_data,
                               data.meta, data.info, blocks=full_condition.block_indexes)
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

        # From a check of the data in the D-string EDB from rehearsals, it looks like the times
        # associated with the mnemonic of interest and the dependency are the same. So no
        # need to interpolate? We can just get indexes from the latter and apply them to
        # the former? Add a test for this so we can catch if that's not true.
        # First, find all the unique values of the dependency. This assumes that the depenedency
        # values are strings, which is the case for the MIRI mnemonics originally requested
        # for this every-change case.

        # Make sure the data values for the dependency are strings.
        if type(dependency.data["euvalues"][0]) != np.str_:
            raise NotImplementedError("find_all_changes() is not set up to handle non-strings in the dependency data")
        else:
            change_indexes = np.where(dependency.data["euvalues"][:-1] != dependency.data["euvalues"][1:])[0]

            # If dates differ between the mnemonic of interest and the dependency, then interpolate to match
            if not np.all(dependency.data["dates"] == mnem_data.data["dates"]):
                mnem_data.interpolate(dependency.data["dates"].data)

            # Set blocks values
            mnem_data.blocks = np.insert(change_indexes + 1, 0, 0)
            mnem_data.every_change_values = dependency.data["euvalues"][mnem_data.blocks]

        return mnem_data


    def get_dependency_data(self, dependency, starttime, endtime):
        """Find EDB data for the mnemonic listed as a dependency. Keep a dcitionary up to
        date with query results for all dependencies, in order to minimize the number of
        queries we have to make. Return the requested dependency's time and data values.

        Parameters
        ----------
        dependency : str
            Mnemonic to seach for

        starttime : astropy.time.Time

        endtime : astropy.time.Time

        Returns
        -------
        dep_mnemonic : dict
            Data for the dependency mnemonic. Keys are "dates" and "euvalues"
        """
        # If we have already queried the EDB for the dependency's data in the time
        # range of interest, then use that data rather than re-querying.
        if dependency["name"] in self.query_results:

            # We need the full time to be covered
            if ((self.query_results[dependency["name"]].data_start_time <= starttime) and
                (self.query_results[dependency["name"]].data_end_time >= endtime)):

                matching_times = np.where((self.query_results[dependency["name"]].data["dates"] > starttime) and
                                          (self.query_results[dependency["name"]].data["dates"] < endtime))
                dep_mnemonic = {"dates": self.query_results[dependency["name"]].data["dates"][matching_times],
                                "euvalues": self.query_results[dependency["name"]].data["euvalues"][matching_times]}
            else:
                # If what we have doesn't cover the time range we need, then query the EDB.
                mnemonic_data = ed.get_mnemonic(dependency["name"], starttime, endtime)
                dep_mnemonic = {"dates": mnemonic_data.data["dates"], "euvalues": menmonic_data.data["euvalues"]}

                # This is to save the data so that we may avoid an EDB query next time
                # Add the new data to the saved query results. This should also filter out
                # any duplicate rows.
                self.query_results[dependency["name"]] = self.query_results[dependency["name"]] + mnemonic_data

                ################################
                # These lines should be replaced now that EdbMnemonic has __add__ defined
                #all_times = np.append(self.query_results[dependency["name"]].data["dates"], mnemonic_data.data["dates"])
                #all_data = np.append(self.query_results[dependency["name"]].data["euvalues"], mnemonic_data.data["euvalues"])

                # Save only the unique elements, in case we are adding overlapping data
                #final_times, unique_idx = np.unique(all_times, return_index=True)
                #new_table = Table()
                #new_table["dates"] = final_times
                #new_table["euvalues"] = all_data[unique_idx]
                #self.query_results[dependency["name"]].data = new_table
                ################################
        else:
            self.query_results[dependency["name"]] = ed.get_mnemonic(dependency["name"], starttime, endtime)
            dep_mnemonic = {"dates": self.query_results[dependency["name"]].data["dates"],
                            "euvalues": self.query_results[dependency["name"]].data["euvalues"]}
        return dep_mnemonic

    def get_mnemonic_info(self, mnemonic, starting_time, ending_time, telemetry_type):
        """Wrapper around the code to query the EDB, filter the result, and calculate
        appropriate statistics for a single mnemonic

        Parameters
        ----------
        mnemonic : dict
            Dictionary of information about the mnemonic to be processed. Dictionary
            as read in from the json file of mnemonics

        starting_time : float
            Beginning time for query in MJD

        ending_time : float
            Ending time for query in MJD

        telemetry_type : str
            How the telemetry will be processed. This is the top-level heirarchy from
            the json file containing the mnemonics. e.g. "daily_means", "every_change"

        Returns
        -------
        good_mnemonic_data : jwql.edb.engineering_database.EdbMnemonic
            EdbMnemonic instance containing filtered data for the given mnemonic
        """
        # Query the EDB. An astropy table is returned.
        print('querying edb for: ', mnemonic["name"], starting_time, ending_time, type(starting_time), type(ending_time))

        try:
            mnemonic_data = ed.get_mnemonic(mnemonic["name"], starting_time, ending_time)
        except HTTPError:
            # Mnemonic not accessible. This is largely for development where we don't
            # have access to all the mnemonics that we will in commissioning due to
            # querying the d-string.
            print(f'{mnemonic["name"]} not accessible with current search.')
            return None

        # Remove the first and last entries in the returned data, since MAST
        # automatically includes the two points immediately outside the requested
        # time range.
        # THIS LOOKS LIKE IT IS NOT NECESSARY ANY LONGER GIVEN THE NEW MAST SERVICE
        #mnemonic_data = utils.remove_outer_points(mnemonic_data)

        # Filter the data - good_mnemonic_data is an EdbMnemonic instance
        if ((len(mnemonic["dependency"]) > 0) and (telemetry_type != "every_change")):
            good_mnemonic_data = self.filter_telemetry(mnemonic_data, mnemonic['dependency'])
        else:
            # No dependencies. Keep all the data
            good_mnemonic_data = mnemonic_data
            good_mnemonic_data.blocks = [0]

        if telemetry_type == "every_change":
            # Note that this adds good_mnemonic_data.every_change_values, which is not present
            # in other modes, but will be needed for plotting
            good_mnemonic_data = self.find_all_changes(good_mnemonic_data, mnemonic['dependency'])

        # If the filtered data contains enough entries, then proceed.
        if len(good_mnemonic_data.data) > 0:


##############this has been moved elsewhere
            #we can make the daily mean, block mean, and timed mean methods of the EdbMnemonic class.
            #what about every change? separate method here? new one there as well?
            #if telemetry_type == "daily_means":
            #    mean_vals, median_vals, std_vals, time_vals = self.calc_daily_stats(good_mnemonic_data.data)
            #elif telemetry_type == "block_means":
            #    mean_vals, median_vals, std_vals, median_times = self.calc_block_stats(good_mnemonic_data)
            #elif telemetry_type == "every_change":
            #    mean_vals, std_vals, median_times = self.calc_every_change_stats(good_mnemonic_data)
            #elif telemetry_type == "time_interval":
            #    stats_duration = utils.get_averaging_time_duration(mnemonic["mean_time_block"])
            #    mean_vals, median_vals, std_vals, median_times = self.calc_timed_stats(good_mnemonic_data, stats_duration)
            #elif telemetry_type == "none":
            #    # No averaging done
            #    mean_vals = good_mnemonic_data["euvalues"]
            #    median_times = good_mnemonic_data["dates"]
##############this has been moved elsewhere

            return good_mnemonic_data
        else:
            return None

    def identify_tables(self, inst):
        """Determine which database tables to use for a run of the dark
        monitor
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst]
        self.history_table = eval('{}EDBMnemonics'.format(mixed_case_name))

    def load_data(self, mnemonic_name):
        """Query the database tables to get data"""

        # Query database for all data in NIRCamDarkDarkCurrent with a matching aperture
        self.history_table = session.query(self.history_table) \
            .filter(self.history_table.mnemonic == mnemonic_name) \
            .all()

    def most_recent_search(self, telem_name):
        """Query the database and return the information
        on the most recent query, indicating the last time the
        EDB Mnemonic monitor was executed.

        Returns
        -------
        query_result : astropy.time.Time
            Date of the ending range of the previous query
        """
        query = session.query(self.history_table).filter(self.history_table.mnemonic == telem_name).order_by(self.hisotry_table.latest_query).all()

        if len(query) == 0:
            base_time = '2021-08-01'
            query_result = Time(base_time)
            logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'.format(self.mnemonic, base_time)))
        else:
            query_result = Time(query[-1].latest_query)

        return query_result


    def run(self):
        """
        """
        # This is a dictionary that will hold the query results for multiple mnemonics,
        # in an effort to minimize the number of EDB queries and save time.
        self.query_results = {}

        # The cadence with which the EDB is queried. This is different than the query
        # duration. This is the cadence of the query starts, while the duration is the
        # block of time to query over. For example, a cadence of 1 day and a duration
        # of 15 minutes means that the EDB will be queried over 12:00am - 12:15am each
        # day.
        query_cadence = 1 * u.day

        # Set up directory structure to hold the saved plots
        config = get_config()
        base_dir = os.path.join(config["outputs"], "edb_telemetry_monitor")

        # Loop over all instruments
        for instrument in ['nircam']:  #JWST_INSTRUMENT_NAMES:
            plot_output_dir = os.path.join(base_dir, isntrument)

            # Read in a list of mnemonics that the instrument teams want to monitor
            #     From either a text file, or a edb_mnemonics_montior database table
            monitor_dir = os.path.dirname(os.path.abspath(__file__))
            mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', f'{instrument.lower()}_mnemonics_to_monitor.json')
            with open(mnemonic_file) as json_file:
                mnemonic_dict = json.load(json_file)

            # Check the edb_mnemonics_monitor database table to see the date of the previous query
            # as is done in other monitors
            #self.identify_tables(instrument)

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
                        #most_recent_search = self.most_recent_search(mnemonic['name'])
                        most_recent_search = Time('2021-12-13')  # for development
                        starttime = most_recent_search + TimeDelta(query_cadence)

                        # In this case we also need to retrieve the historical data from the database, so that
                        # we can add the new data and create an updated plot
                        self.load_data(mnemonic["name"])
                    else:
                        # In the case where telemetry data have no averaging done, we do not store the data
                        # in the JWQL database, in order to save space. So in this case, we will retrieve
                        # all of the data from the EDB directly, from some default start time until the
                        # present day.
                        starttime = Time.now() - TimeDelta(EDB_LOOK_BACK_TIME, format='jd')

                    # Check for the case where, for whatever reason, there have been missed days. If so, we need
                    # to run the calculations separately for each day. Should we query for the full time and then
                    # filter, or query once per day? The latter is probably slower. Could the former turn into a
                    # problem if e.g. someone wants to track a new mnemonic and it's been 100 days since the
                    # default most recent search time?
                    query_start_times = []
                    query_end_times = []
                    time_range = int((today - starttime).to(u.day).value)
                    # Create an array of starting and ending query times. Start times are once per day
                    # between the previous query time and the present. End times are the start times
                    # plus the query duration.
                    for delta in range(time_range):
                        tmp_start = starttime + TimeDelta(delta * u.day)
                        query_start_times.append(tmp_start)
                        query_end_times.append(tmp_start + TimeDelta(query_duration))

                    # Make sure the end time of the final query is before the current time
                    if query_end_times[-1] > today:
                        valid_end_times = query_end_times <= today
                        query_start_times = query_start_times[valid_end_times]
                        query_end_times = query_end_times[valid_end_times]

                    # Loop over the query times, query the EDB, filter data, and store in
                    # an EdbMnemonic object
                    initialized = False
                    for starttime, endtime in zip(query_start_times, query_end_times):

                        # This function wraps around the EDB query and telemetry filtering, and
                        # averaging. In this way, when a user requests an updated plot for one of
                        # the mnemonics whose data are not stored in the JWQL database, we can simply
                        # call this function for that specific mnemonic
                        mnemonic_day_info = self.get_mnemonic_info(mnemonic, starttime, endtime, telem_type)

                        if mnemonic_day_info is not None:
                            # Add results for multiple days here. This needs to be done for both
                            # averaged and non-averaged mnemonics
                            if not initialized:
                                mnemonic_info = deepcopy(mnemonic_day_info)
                                initialized = True
                            else:
                                mnemonic_info = menonic_info + mnemonic_day_info
                        else:
                            pass

                    # Now calculate statistics if this is a menmonic where averaging is to be done.
                    if telemetry_type == "daily_means":
                        mnemonic_info.calc_daily_stats()
                    elif telemetry_type == "block_means":
                        mnemonic_info.calc_block_stats()
                    elif telemetry_type == "every_change":
                        mnemonic_info.calc_every_change_stats()
                    elif telemetry_type == "time_interval":
                        stats_duration = utils.get_averaging_time_duration(mnemonic["mean_time_block"])
                        mnemonic_info.calc_timed_stats(stats_duration)
                    elif telemetry_type == "none":
                        mnemonic_info.mean = 'No_averaging'

                    # Save the averaged/smoothed data and dates/times to the database,
                    # but only for cases where we are averaging. For cases with no averaging
                    # the database would get too large too quickly. In that case the monitor
                    # will re-query the EDB for the entire history each time.
                    if telemetry_type != "none":
                        self.add_new_db_entry(mnemonic_info, query_start_times[-1].datetime)
                        print('use line above IRL. Be sure to add to databse before concatenating the historical and new data')

                        # To make plotting easier, create a new EdbMnemonic instance and
                        # populate it with the historical data combined (concatenated) with the
                        # newly averaged data
                        historical_data = EdbMnemonic(mnemonic["name"], self.history_table, stuff)
                        mnemonic_info = mnemonic_info + historical_data

                    # Create and save plot
                    nominal = utils.check_key(mnemonic_info.info, "nominal_value")
                    yellow = utils.check_key(mnemonic_info.info, "yellow_limits")
                    red = utils.check_key(mnemonic_info.info, "red_limits")

                    if mnemonic["plot_data"] == "nominal":
                        _, _ = mnemonic_info.bokeh_plot(save=True, out_dir=plot_output_dir, nominal_value=nominal,
                                                        yellow_limits=yellow, red_limits=red)
                    elif '*' in mnemonic["plot_data"]:  # (e.g. "*SB_FJDKN")
                        # Get the data for the mnemonic to be combined, place into an EdbMnemonic instance, and
                        # filter with the same criteria used to filter the original mnemonic's data
                        combine_mnemonic = mnemonic["plot_data"].split('*')[1]
                        combine_data = self.get_dependency_data(combine_mnemonic, mnemonic_info.data_start_time, mnemonic_info.data_end_time)
                        combine_tab = Table([combine_data["dates"], combine_data["euvalues"]], names=("dates", "euvalues"))
                        combine_obj = EdbMnemonic(combine_mnemonic, mnemonic_info.data_start_time, mnemonic_info.data_end_time,
                                                  combine_tab, self.query_results[combine_mnemonic].meta,
                                                  self.query_results[combine_mnemonic].info)
                        filtered_combine_obj = self.filter_telemetry(combine_obj, mnemonic["dependency"])

                        # Interpolate the new menmonic's data to be at the same times as self.mnemonic_info
                        combined = self.mnemonic_info * filtered_combine_obj

                        # Create a plot from the combined data
                        _, _ = combined.bokeh_plot(save=True, out_dir=plot_output_dir, nominal_value=nominal,
                                                   yellow_limits=yellow, red_limits=red)
                    else:
                        raise NotImplementedError(('The plot_data entry in the mnemonic dictionary can currently only '
                                                   'be "nominal" or "*<MNEMONIC_NAME>", indicating that the current '
                                                   'mnemonic should be plotted as the product of the mnemonic*<MNEMONIC_NAME>. '
                                                   'e.g. for a mnemonic that reports current, plot the data as a power by '
                                                   'multiplying with a mnemonic that reports voltage. No other mnemonic '
                                                   'combination schemes have been implemented.'))



