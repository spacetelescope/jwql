#! /usr/bin/env python

"""Engineering Database Mnemonics Trending Monitor (EDB Trending Monitor)

more description here
"""
from collections import defaultdict
from copy import deepcopy
import datetime
import json
import numpy as np
import os
from requests.exceptions import HTTPError
import urllib

from astropy.stats import sigma_clipped_stats
from astropy.table import Table
from astropy.time import Time, TimeDelta
import astropy.units as u
from bokeh.embed import components, json_item
from bokeh.layouts import gridplot
from bokeh.models import BoxAnnotation, ColumnDataSource, DatetimeTickFormatter, HoverTool
from bokeh.models.widgets import Tabs, Panel
from bokeh.plotting import figure, output_file, save, show
from bokeh.palettes import Turbo256
from jwql.database import database_interface
from jwql.database.database_interface import NIRCamEDBDailyStats, NIRCamEDBBlockStats, \
                                             NIRCamEDBTimeIntervalStats, NIRCamEDBEveryChangeStats, \
                                             NIRISSEDBDailyStats, NIRISSEDBBlockStats, \
                                             NIRISSEDBTimeIntervalStats, NIRISSEDBEveryChangeStats, \
                                             MIRIEDBDailyStats, MIRIEDBBlockStats, \
                                             MIRIEDBTimeIntervalStats, MIRIEDBEveryChangeStats, \
                                             FGSEDBDailyStats, FGSEDBBlockStats, \
                                             FGSEDBTimeIntervalStats, FGSEDBEveryChangeStats, \
                                             NIRSpecEDBDailyStats, NIRSpecEDBBlockStats, \
                                             NIRSpecEDBTimeIntervalStats, NIRSpecEDBEveryChangeStats, session
from jwql.edb import engineering_database as ed
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import condition
from jwql.instrument_monitors.common_monitors.edb_telemetry_monitor_utils import utils
from jwql.utils.constants import EDB_DEFAULT_PLOT_RANGE, JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import ensure_dir_exists, get_config


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

    def add_figure(self, fig, key):
        """Add Bokeh figure to the dictionary of figures

        Parameters
        ----------
        fig : bokeh.plotting.figure
            Plot of a single mnemonic

        key : str
            Key under which to store the plot
        """
        if key in self.figures:
            self.figures[key].append(fig)
        else:
            self.figures[key] = [fig]


    def add_new_block_db_entry(self, mnem, query_time):
        """Add a new entry to the database table for any kind
        of telemetry type other than "none" (which does not save
        data in the database) and "every_change" (which needs a
        custom table.)

        Parameters
        ----------
        mnem : jwql.edb.engineering_database.EdbMnemonic
            Mnemonic information

        query_time : datetime.datetime
            Start time of the query
        """

        print('In add_new_block_db_entry. stdev data:')
        #print(mnem.data["euvalues"].data, type(mnem.data["euvalues"]))
        print(mnem.stdev, type(mnem.stdev))




        # Construct new entry for dark database table
        db_entry = {'mnemonic': mnem.mnemonic_identifier,
                    'latest_query': query_time,
                    'times': mnem.data["dates"].data,
                    'data': mnem.data["euvalues"].data,
                    'stdev': mnem.stdev,
                    'entry_date': datetime.datetime.now()
                    }
        self.history_table.__table__.insert().execute(db_entry)

    def add_new_every_change_db_entry(self, mnem, mnem_dict, dependency_name, query_time):
        """Add new entries to the database table for "every change"
        mnemonics. Add a separate entry for each dependency value.

        Parameters
        ----------
        mnem : str
            Name of the mnemonic whose data is being saved

        mnem_dict : dict
            Dictionary containing every_change data as output by organize_every_change()

        dependency_name : str
            Name of mnemonic whose values the changes in mnemonic are based on

        query_time : datetime.datetime
            Start time of the query
        """
        # Construct new entry for dark database table
        #entry_date = datetime.datetime.now()
        #for key, value in data_dict.items():
        #    db_entry = {'mnemonic': mnem,
        #                'dependency_mnemonic': dependency_name,
        #                'dependency_value': key,
        #                'mnemonic_value': value[1],
        #                'times': value[0],
        #                'latest_query': query_time,
        #                'entry_date': entry_date
        #                }
        #    self.history_table.__table__.insert().execute(db_entry)

        # We create a separate database entry for each unique value of the
        # dependency mnemonic.
        for key, value in mnem_dict.items():
            (times, values, means, stdevs) = value
            db_entry = {'mnemonic': mnem,
                        'dependency_mnemonic': dependency_name,
                        'dependency_value': key,
                        'mnemonic_value': values,
                        'time': times,
                        'mean': means,
                        'stdev': stdevs,
                        'latest_query': query_time,
                        'entry_date': datetime.datetime.now()
                        }
            self.history_table.__table__.insert().execute(db_entry)



        #db_entry = {'mnemonic': mnem.mnemonic_identifier,
        #            'dependency_mnemonic': dependency_name,
        #            'dependency_value': mnem.every_change_values,
        #            'mnemonic_value': mnem.data["euvalues"].data,
        #            'times': mnem.data["dates"].data,
        #            'latest_query': query_time,
        #            'entry_date': datetime.datetime.now()
        #                }
        #self.history_table.__table__.insert().execute(db_entry)



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
                good_points = np.where((mnem_data.data["dates"] >= bin_times[b_idx]) & (mnem_data.data["dates"] < bin_times[b_idx+1]))
                bin_mean, bin_med, bin_stdev = sigma_clipped_stats(mnem_data.data["data"][good_points], sigma=sigma)
                all_means.append(bin_mean)
                all_meds.append(bin_med)
                all_stdevs.append(bin_stdev)
        return all_means, all_meds, all_stdevs, all_times

    def filter_telemetry(self, mnem, data, dep_list):
        """
        Filter telemetry data for a single mnemonic based on a list of
        conditions/dependencies, as well as a time.

        Parameters
        ----------
        mnem : str
            Name of the mnemonic whose dependencies will be queried

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

        print('NUMBER OF DEPS: ', len(dep_list))


        all_conditions = []
        for dependency in dep_list:

            if dependency["name"] != mnem:
                # If the dependency to retrieve is different than the mnemonic being filtered,
                # get the dependency's times and values from the EDB.
                dep_mnemonic = self.get_dependency_data(dependency, data.requested_start_time, data.requested_end_time)

            else:
                # If we are just filtering the mnemonic based on it's own values, then there is
                # no need to query the EDB
                dep_mnemonic = {}
                dep_mnemonic["dates"] = data.data["dates"]
                dep_mnemonic["euvalues"] = data.data["euvalues"]


            """
            if dependency["name"] == 'IMIR_HK_ICE_SEC_VOLT1':
                print('IMIR_HK_ICE_SEC_VOLT1')
                good = np.where(dep_mnemonic["euvalues"] > 25)[0]
                print('GOOD VOLT1: ', dep_mnemonic["euvalues"][good])
                print(dep_mnemonic["dates"][good])
                print(len(good))
                print('\n\n')
                for g, d,v in zip(good, dep_mnemonic["euvalues"].data[good], dep_mnemonic["dates"].data[good]):
                    print(g, d, v)
                #print(dep_mnemonic["euvalues"])
                #print(dep_mnemonic["dates"])
            """


            if len(dep_mnemonic["dates"]) > 0:
                time_boundaries = condition.relation_test(dep_mnemonic, dependency["relation"], dependency["threshold"])
                all_conditions.append(time_boundaries)

                # If time_boundaries is [(None, None)] then there is no time period where the condition is True. In
                # this case, reset the time boundaries to something nonsensical. Then when good data are extracted
                # after this loop, nothing will be extracted.
                #if time_boundaries[0][0] is None:
                #    print(('No values of the dependency match the condition. Setting the range of good valid '
                #           'times to something that makes no sense (1021-12-25), so that no data will be extracted '
                #           ' from the mnemonic.'))
                #    all_conditions.append([datetime(1021, 12, 25), datetime(1021, 12, 25, 0, 0, 1)])
            else:
                # In this case, the query for dependency data returned an empty array. With no information
                # on the dependency, it seems like we have to throw out the data for the mnemonic of
                # interest, because there is no way to know if the proper conditions have been met.
                print((f'No data for dependency {dependency["name"]} between {data.requested_start_time} and {data.requested_end_time}, '
                       f'so ignoring {mnem} data for the same time period.'))

                print('\n\n\nVVVVV', data.requested_start_time, '\n\n\n')


                filtered = empty_edb_instance(data.mnemonic_identifier, data.requested_start_time,
                                              data.requested_end_time, meta=data.meta, info=data.info)
                return filtered




            #print('all_conditions time pairs:')
            #print(all_conditions[0].time_pairs)
            #print(all_conditions[0].time_pairs[0][0])
            #print(all_conditions[0].time_pairs[0][1])
            #print(len(data.data["dates"]))
            #print(data.data["dates"])

            #print('all_conditions: ')
            #print(all_conditions)

            #print(all_conditions[0].time_pairs[0][0])
            #print(all_conditions[0].time_pairs[0][1])

            #if dependency["name"] == 'SE_ZIMIRICEA':
            #    print('all_conditions time pairs:')
            #    print(all_conditions[0].time_pairs)


            #on = np.where(data.data["dates"] == all_conditions[0].time_pairs[0][0])[0]
            #off = np.where(data.data["dates"] == all_conditions[0].time_pairs[0][1])[0]

            #print(data.data["dates"][on], data.data["euvalues"][on])
            #print(data.data["dates"][off], data.data["euvalues"][off])
            #try:
            #    print(data.data["dates"][off+1], data.data["euvalues"][off+1])
            #except:
            #    print("no more data")



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

        # For change only data, like SE_ZIMIRICEA, interpolate values to match the start and stop
        # times of all conditions in order to prevent a very stable value (meaning few datapoints)
        # from being interpreted as having no data during the time period of the conditions
        if data.meta['TlmMnemonics'][0]['AllPoints'] == 0:
            boundary_times = []
            for cond in all_conditions:
                for time_pair in cond.time_pairs:
                    boundary_times.extend([time_pair[0], time_pair[1]])
            # If we have a valid list of start/stop times (i.e. no None entries), then
            # interpolate the every-change data onto those dates

            print('boundary_times:', boundary_times)

            #nones_present = any([None in time_tup for time_tup in boundary_times])
            if None not in boundary_times:
                data.interpolate(sorted(np.unique(np.array(boundary_times))))

        full_condition.extract_data(data.data)
        #filtered_data, block_indexes = cond.extract_data(full_condition, data.data)


        #if data.mnemonic_identifier == 'IMIR_HK_ICE_SEC_VOLT1':
        #    print('extracted data:')
        #    print(full_condition.extracted_data)
        #    print(len(full_condition.extracted_data))
        #    print(full_condition.block_indexes)


        #print('CONDITON')
        #print(full_condition.extracted_data["dates"])
        #print(full_condition.block_indexes)


        # Put the results into an instance of EdbMnemonic
        #new_start_time = np.min(full_condition.extracted_data["dates"])
        #new_end_time = np.max(full_condition.extracted_data["dates"])
        filtered = ed.EdbMnemonic(data.mnemonic_identifier, data.requested_start_time, data.requested_end_time,
                                  full_condition.extracted_data, data.meta, data.info, blocks=full_condition.block_indexes)
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

        # If the mnemonic instance is empty, then populate the blocks and every_change_values
        # properties, and exit
        if len(mnem_data) == 0:
            mnem_data.blocks = [0, 1]
            mnem_data.every_change_values = [np.nan]
            return mnem_data

        # Retrieve the data for the dependency to use
        #if dep_list[0]["name"] in self.query_results: this only works if the dates are ok
        #    dep_table = self.query_results[dep_list[0]["name"]].data
        #    dependency = {}
        #    dependency["dates"] = dep_table["dates"].data
        #    dependency["euvalues"] = dep_table["euvalues"].data
        #else:
        dependency = self.get_dependency_data(dep_list[0], mnem_data.requested_start_time,
                                              mnem_data.requested_end_time)

        # If the dependency data are empty, then we can't define blocks. Set the entire range
        # of data to a single block. Since filter_data is called before find_all_changes, we
        # *should* never end up in here, as missing dependency data should zero out the main
        # mnemonic in there.
        if len(dependency) == 0:
            mnem_data.blocks = [0, len(mnem)]
            mnem_data.every_change_values = [np.nan]

        # From a check of the data in the D-string EDB from rehearsals, it looks like the times
        # associated with the mnemonic of interest and the dependency are the same. So no
        # need to interpolate? We can just get indexes from the latter and apply them to
        # the former? Add a test for this so we can catch if that's not true.
        # First, find all the unique values of the dependency. This assumes that the depenedency
        # values are strings, which is the case for the MIRI mnemonics originally requested
        # for this every-change case.

        # Make sure the data values for the dependency are strings.
        if type(dependency["euvalues"][0]) != np.str_:
            raise NotImplementedError("find_all_changes() is not set up to handle non-strings in the dependency data")
        else:
            change_indexes = np.where(dependency["euvalues"][:-1] != dependency["euvalues"][1:])[0]

            # Increase values by 1 to get the correct index for the full data length
            if len(change_indexes) > 0:
                change_indexes += 1


            #print('from where statement: ', len(change_indexes))

            # Add 0 as the first element
            change_indexes = np.insert(change_indexes, 0, 0)

            #print('insert 0: ', len(change_indexes))

            # Add the largest index as the final element
            change_indexes = np.insert(change_indexes, len(change_indexes), len(dependency["euvalues"]))

            #print('insert end: ', len(change_indexes))
            #print(change_indexes)

            # If dates differ between the mnemonic of interest and the dependency, then interpolate to match
            if not np.all(dependency["dates"] == mnem_data.data["dates"].data):
                mnem_data.interpolate(dependency["dates"])

            # Set blocks values
            #tups = []
            #vals = []
            #for i in range(len(change_indexes) - 1):
            #    #tups.append((change_indexes[i], change_indexes[i+1]))
            #    #tups.append(change_indexes[i])
            #    vals.append(dependency["euvalues"][tups[i]])
            #print('CHECKING:', change_indexes)
            #print(change_indexes[0:-1])
            vals = dependency["euvalues"][change_indexes[0:-1]].data

            mnem_data.blocks = change_indexes
            mnem_data.every_change_values = vals

            #print('BLOCKS in find_all_changes:')
            #print(mnem_data.blocks)
            #print(mnem_data.every_change_values)

            print(len(mnem_data))
            print(len(dependency['dates']))
            print(change_indexes)
            print(vals)
            print(mnem_data.blocks)
            print(mnem_data.every_change_values)


        return mnem_data


    def get_dependency_data(self, dependency, starttime, endtime):
        """Find EDB data for the mnemonic listed as a dependency. Keep a dcitionary up to
        date with query results for all dependencies, in order to minimize the number of
        queries we have to make. Return the requested dependency's time and data values.

        Parameters
        ----------
        dependency : dict
            Mnemonic to seach for

        starttime : astropy.time.Time

        endtime : astropy.time.Time

        Returns
        -------
        dep_mnemonic : dict
            Data for the dependency mnemonic. Keys are "dates" and "euvalues"
        """
        print('\nDEPENDENCY:')
        print(dependency)



        # If we have already queried the EDB for the dependency's data in the time
        # range of interest, then use that data rather than re-querying.
        if dependency["name"] in self.query_results:

            # We need the full time to be covered
            if ((self.query_results[dependency["name"]].requested_start_time <= starttime) and
                (self.query_results[dependency["name"]].requested_end_time >= endtime)):

                print(f'Dependency {dependency["name"]} is already present in self.query_results.')
                #print(self.query_results[dependency["name"]].requested_start_time, starttime)
                #print(self.query_results[dependency["name"]].requested_end_time, endtime)

                matching_times = np.where((self.query_results[dependency["name"]].data["dates"] > starttime) &
                                          (self.query_results[dependency["name"]].data["dates"] < endtime))
                dep_mnemonic = {"dates": self.query_results[dependency["name"]].data["dates"][matching_times],
                                "euvalues": self.query_results[dependency["name"]].data["euvalues"][matching_times]}

                print(f'Length of returned data: {len(dep_mnemonic["dates"])}')
            else:
                # If what we have doesn't cover the time range we need, then query the EDB.
                print(f'Dependency {dependency["name"]} is present in self.query results, but does not cover the needed time. Querying EDB for the dependency.')
                #print(self.query_results[dependency["name"]].requested_start_time, starttime)
                #print(self.query_results[dependency["name"]].requested_end_time, endtime)
                mnemonic_data = ed.get_mnemonic(dependency["name"], starttime, endtime)
                print(f'Length of returned data: {len(mnemonic_data)}, {starttime}, {endtime}')
                mnemonic_data.save_table(f'edb_results_for_development_{dependency["name"]}.txt')
                dep_mnemonic = {"dates": mnemonic_data.data["dates"], "euvalues": mnemonic_data.data["euvalues"]}

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
            print(f'Dependency {dependency["name"]} is not in self.query_results. Querying the EDB.')
            self.query_results[dependency["name"]] = ed.get_mnemonic(dependency["name"], starttime, endtime)
            print(f'Length of data: {len(self.query_results[dependency["name"]])}, {starttime}, {endtime}')
            self.query_results[dependency["name"]].save_table(f'edb_results_for_development_{dependency["name"]}.txt')
            dep_mnemonic = {"dates": self.query_results[dependency["name"]].data["dates"],
                            "euvalues": self.query_results[dependency["name"]].data["euvalues"]}

        return dep_mnemonic

    def get_history(self, mnemonic, start_date, end_date, info={}, meta={}):
        """Retrieve data for a single mnemonic over the given time range

        Parameters
        ----------
        mnemonic : str
            Name of mnemonic whose data is to be retrieved

        start_date : datetime
            Beginning date of data retrieval

        end_date : datetime
            Ending date of data retrieval

        Returns
        -------
        hist : jwql.edb.engineering_database.EdbMnemonic
            Retrieved data
        """
        data = session.query(self.history_table) \
            .filter(self.history_table.mnemonic == mnemonic,
                    self.history_table.latest_query > start_date,
                    self.history_table.latest_query < end_date)

        all_dates = []
        all_values = []
        for row in data:
            all_dates.extend(row.times)
            all_values.extend(row.data)

        tab = Table([all_dates, all_values], names=('dates', 'euvalues'))
        hist = ed.EdbMnemonic(mnemonic, start_date, end_date, tab, meta, info)
        return hist

    def get_history_every_change(self, mnemonic, start_date, end_date):
        """Retrieve data for a single mnemonic over the given time range for every_change data
        e.g. IMIR_HK_FW_POS_RATIO, where we need to calculate and store an average value for
        each block of time where IMIR_HK_FW_CUR_POS has a different value. This has nothing to
        do with 'change-only' data as stored in the EDB.

        Parameters
        ----------
        mnemonic : str
            Name of mnemonic whose data is to be retrieved

        start_date : datetime
            Beginning date of data retrieval

        end_date : datetime
            Ending date of data retrieval

        Returns
        -------
        hist : dict
            Retrieved data. Keys are the value of the dependency mnemonic,
            and each value is a 3-tuple. The tuple contains the times, values,
            and mean value of the primary mnemonic corresponding to the times
            that they dependency mnemonic has the value of the key.
        """
        data = session.query(self.history_table) \
            .filter(self.history_table.mnemonic == mnemonic,
                    self.history_table.latest_query > start_date,
                    self.history_table.latest_query < end_date)

        # Set up the dictionary to contain the data
        hist = {}
        #for dep_val in np.unique(data.dependency_value):
        #    hist[dep_val] = []

        # Place the data from the database into the appropriate key
        for row in data:
            if row.dependency_value in hist:
                if len(hist[row.dependency_value]) > 0:
                    times, values, means = hist[row.dependency_value]
                else:
                    times = []
                    values = []
                    means = []
                times.extend(row.time)
                values.extend(row.mnemonic_value)
                means.extend(row.mean)
                hist[row.dependency_value] = (times, values, means)
            else:
                hist[row.dependency_value] = (row.time, row.mnemonic_value, row.mean)

        return hist


    def get_mnemonic_info(self, mnemonic, starting_time, ending_time, telemetry_type):
        """Wrapper around the code to query the EDB, filter the result, and calculate
        appropriate statistics for a single mnemonic

        Parameters
        ----------
        mnemonic : dict
            Dictionary of information about the mnemonic to be processed. Dictionary
            as read in from the json file of mnemonics

        starting_time : datetime.datetime
            Beginning time for query

        ending_time : datetime.datetime
            Ending time for query

        telemetry_type : str
            How the telemetry will be processed. This is the top-level heirarchy from
            the json file containing the mnemonics. e.g. "daily_means", "every_change"

        Returns
        -------
        good_mnemonic_data : jwql.edb.engineering_database.EdbMnemonic
            EdbMnemonic instance containing filtered data for the given mnemonic
        """
        # Query the EDB. An astropy table is returned.
        print(f'Querying EDB for: {mnemonic["name"]} from {starting_time} to {ending_time}')

        try:
            mnemonic_data = ed.get_mnemonic(mnemonic["name"], starting_time, ending_time)

            if mnemonic['name'] in ['SE_ZIMIRICEA', 'SE_ZBUSVLT']:
                print(mnemonic['name'])
                print(mnemonic_data.meta)
                print(mnemonic_data.info)
                print('As retrieved from EDB:')
                print('First length of data: ', len(mnemonic_data.data["dates"]))
                #print(mnemonic_data.data)

            # FOR DEVELOPMENT - NO NEED TO SAVE WHEN RUNNING FOR REAL
            mnemonic_data.save_table(f'edb_results_for_development_{mnemonic["name"]}.txt')

            # Populate the dictionary of queried data in order to avoid repeated queries
            #is this necessary?
            #if len(mnemonic_data) > 0:
            #    usename = "name"
            #    if "database_id" in mnemonic:
            #        usename = "database_id"
            #    self.query_results[mnemonic[usename]] = mnemonic_data

            if len(mnemonic_data) == 0:
                print(f"No data returned from EDB for {mnemonic['name']} between {starting_time} and {ending_time}")
                return None

            # If the mnemonic has an alternative name (due to e.g. repeated calls for that mnemonic but with
            # different averaging schemes), then update the mnemonic_identifier in the returned EdbMnemonic
            # instance. This will allow different versions to be saved in the database.
            if "database_id" in mnemonic:
                mnemonic_data.mnemonic_identifier = mnemonic["database_id"]
            else:
                mnemonic_data.mnemonic_identifier = mnemonic["name"]

        except (urllib.error.HTTPError, HTTPError):
            # Mnemonic not accessible. This is largely for development where we don't
            # have access to all the mnemonics that we will in commissioning due to
            # querying the d-string.
            print(f'{mnemonic["name"]} not accessible with current search.')
            return None


        #if mnemonic["name"] == 'IMIR_HK_ICE_SEC_VOLT1':
        #    print(np.max(mnemonic_data.data["euvalues"]))



        print(f'Length of returned data: {len(mnemonic_data)}')

        # Remove the first and last entries in the returned data, since MAST
        # automatically includes the two points immediately outside the requested
        # time range.
        # THIS LOOKS LIKE IT IS NOT NECESSARY ANY LONGER GIVEN THE NEW MAST SERVICE
        #mnemonic_data = utils.remove_outer_points(mnemonic_data)

        # Filter the data - good_mnemonic_data is an EdbMnemonic instance
        if ((len(mnemonic["dependency"]) > 0) and (telemetry_type != "every_change")):
            good_mnemonic_data = self.filter_telemetry(mnemonic["name"], mnemonic_data, mnemonic['dependency'])

            #if mnemonic["name"] == 'IMIR_HK_ICE_SEC_VOLT1':
            #    print('Min and Max values of filtered data:')
            #    print(np.min(good_mnemonic_data.data["euvalues"]), np.max(good_mnemonic_data.data["euvalues"]))


            if mnemonic['name'] == 'SE_ZIMIRICEA':
                print('After filtering by dependencies:')
                print(good_mnemonic_data.data)


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
            return good_mnemonic_data
        else:
            return None

    def identify_tables(self, inst, tel_type):
        """Determine which database tables to use for a run of the dark
        monitor
        """
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst]
        if '_means' in tel_type:
            tel_type = tel_type.strip('_means')
        tel_type = tel_type.title().replace('_', '')
        self.history_table_name = f'{mixed_case_name}EDB{tel_type}Stats'
        self.history_table = getattr(database_interface, f'{mixed_case_name}EDB{tel_type}Stats')

    def load_data(self, mnemonic_name, start_date, end_date):
        """Query the database tables to get data"""

        print('USE self.get_history')

        self.history_table = session.query(self.history_table) \
            .filter(self.history_table.mnemonic == mnemonic_name) \
            .all()

    def most_recent_search(self, telem_name):
        """Query the database and return the information
        on the most recent query, indicating the last time the
        EDB Mnemonic monitor was executed.

        Parameters
        ----------
        telem_name : str
            Mnemonic to search for

        Returns
        -------
        query_result : astropy.time.Time
            Date of the ending range of the previous query
        """
        query = session.query(self.history_table).filter(self.history_table.mnemonic == telem_name).order_by(self.hisotry_table.latest_query).all()

        if len(query) == 0:
            base_time = '2021-09-01 00:00:00'
            #query_result = Time(base_time)
            query_result = datetime.strptime(base_time, '%Y-%m-%d %H:%M:%S.%f')
            logging.info(('\tNo query history for {}. Returning default "previous query" date of {}.'.format(self.mnemonic, base_time)))
        else:
            #query_result = Time(query[-1].latest_query)
            query_result = datetime.strptime(query[-1].latest_query, '%Y-%m-%d %H:%M:%S.%f')

        return query_result

    def multiday_mnemonic_query(self, mnemonic_dict, starting_time_list, ending_time_list, telemetry_type,
                                use_dates=None):
        """
        """
        multiday_table = Table()
        multiday_median_times = []
        multiday_mean_vals = []
        multiday_stdev_vals = []
        multiday_every_change_data = []
        info = {}
        meta = {}
        identifier = mnemonic_dict[self._usename]
        if '*' in mnemonic_dict["plot_data"]:
            # Define the mnemonic identifier to be <mnemonic_name_1>*<mnemonic_name_2>
            product_identifier = f'{mnemonic_dict[self._usename]}{mnemonic_dict["plot_data"]}'
        #identifier = mnemonic_dict["name"]
        #if "database_id" in mnemonic_dict:
        #    identifier = mnemonic_dict["database_id"]
        for i, (starttime, endtime) in enumerate(zip(starting_time_list, ending_time_list)):

            # This function wraps around the EDB query and telemetry filtering, and
            # averaging. In this way, when a user requests an updated plot for one of
            # the mnemonics whose data are not stored in the JWQL database, we can simply
            # call this function for that specific mnemonic
            mnemonic_info = self.get_mnemonic_info(mnemonic_dict, starttime, endtime, telemetry_type)

            # If data are returned, do the appropriate averaging
            if mnemonic_info is not None:


            #probably also need to relax the constraints on the multiplication a bit. Perhaps only for single value
            #means? If the difference between the times is less than XX% of the total time covered by the mean, then
            #consider that close enough?
            #print('1. ', mnemonic_info.data)


            #if mnemonic_day_info is not None:
            #    # Add results for multiple days here. This needs to be done for both
            #    # averaged and non-averaged mnemonics
            #    if not initialized:
            #        mnemonic_info = deepcopy(mnemonic_day_info)
            #        initialized = True
            #    else:
            #        mnemonic_info = menonic_info + mnemonic_day_info
            #else:
            #    pass


                identifier = mnemonic_info.mnemonic_identifier
                info = mnemonic_info.info
                meta = mnemonic_info.meta
                print('in multiday:', mnemonic_info.info["unit"])

                # Calculate mean/median/stdev
                mnemonic_info = calculate_statistics(mnemonic_info, telemetry_type)

                if identifier in ['SE_ZIMIRICEA', 'SE_ZBUSVLT']:
                    print("Mean value: ", identifier, mnemonic_info.mean)
                    print('2. ', mnemonic_info.data)




                # If this mnemonic is going to be plotted as a product with another mnemonic, then
                # retrieve the second mnemonic info here
                if '*' in mnemonic_dict["plot_data"]:

                    if telemetry_type == 'every_change':
                        raise ValueError("Plotting product of two mnemonics is not supported for every-change data.")

                    temp_dict = deepcopy(mnemonic_dict)
                    temp_dict["name"] = mnemonic_dict["plot_data"].strip('*')
                    product_mnemonic_info = self.get_mnemonic_info(temp_dict, starttime, endtime, telemetry_type)

                    if product_mnemonic_info is None:
                        print(f'{temp_dict["name"]} to use as product has no data between {starttime} and {endtime}.\n\n')
                        continue

                    print('Prod mnemonic 1 length:', len(mnemonic_info))
                    print('Prod mnemonic 2 length:', len(product_mnemonic_info))

                    # If either mnemonic is every-change data, then first interpolate it
                    # onto the dates of the other. If they are both every-change data,
                    # then interpolate onto the mnemonic with the smaller date range
                    if mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] == 0:
                        numpts = 50
                        if product_mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] == 0:
                            delta = (mnemonic_info.data["dates"][-1] - mnemonic_info.data["dates"][0]) / numpts
                            mnem_new_dates = [mnemonic_info.data["dates"][0] + i*delta for i in range(len(numpts))]
                            prod_new_dates = [product_mnemonic_info.data["dates"][0] + i*delta for i in range(len(numpts))]
                            mnemonic_info.interpolate(mnem_new_dates)
                            product_mnemonic_info.interpolate(prod_new_dates)
                        else:
                            mnemonic_info.interpolate(product_mnemonic_info.data["dates"])
                    else:
                        if product_mnemonic_info.meta['TlmMnemonics'][0]['AllPoints'] == 0:
                            product_mnemonic_info.interpolate(mnemonic_info.data["dates"])
                        else:
                            pass

                    print('Prod mnemonic 1 length:', len(mnemonic_info))
                    print('Prod mnemonic 2 length:', len(product_mnemonic_info))


                    # Multiply the mnemonics together to get the quantity to be plotted
                    combined = mnemonic_info * product_mnemonic_info
                    #combined = product_mnemonic_info * mnemonic_info

                    print('Mult mnemonic length:', len(combined))




                    # Calculate mean/median/stdev
                    mnemonic_info = calculate_statistics(combined, telemetry_type)

                    # Define the mnemonic identifier to be <mnemonic_name_1>*<mnemonic_name_2>
                    #product_identifier = f'{mnemonic_dict[self._usename]}{mnemonic_dict["plot_data"]}'


                # Combine information from multiple days here. If averaging is done, keep track of
                # only the averaged data. If no averaging is done, keep all data.
                if telemetry_type != 'none':
                    multiday_median_times.extend(mnemonic_info.median_times)
                    multiday_mean_vals.extend(mnemonic_info.mean)
                    multiday_stdev_vals.extend(mnemonic_info.stdev)
                    if telemetry_type == 'every_change':
                        multiday_every_change_data.extend(mnemonic_info.every_change_values)
                else:
                    multiday_median_times.extend(mnemonic_info.data["dates"].data)
                    multiday_mean_vals.extend(mnemonic_info.data["euvalues"].data)
                    multiday_stdev_vals.extend(mnemonic_info.stdev)

            else:
                print(f'{mnemonic_dict["name"]} has no data between {starttime} and {endtime}.\n\n')
                continue




            print(f'DONE with query for: {starttime}, {endtime}\n\n')



        # If all daily queries return empty results, get the info metadata from the EDB
        if len(info) == 0:
            print(mnemonic_dict["name"])
            info = ed.get_mnemonic_info(mnemonic_dict["name"])

        # Combine the mean values and median time data from multiple days into a single EdbMnemonic
        # instance. Do this for all averaging conditions, including the case of no averaging.
        multiday_table["dates"] = multiday_median_times
        multiday_table["euvalues"] = multiday_mean_vals
        all_data = ed.EdbMnemonic(identifier, starting_time_list[0], ending_time_list[-1],
                                  multiday_table, meta, info)
        all_data.stdev = multiday_stdev_vals

        # If it is an every_change mnemonic, then we need to also keep track of the dependency
        # values that correspond to the mean values.
        if telemetry_type == 'every_change':
            all_data.every_change_values = multiday_every_change_data

        # Set the mnemonic identifier to be <mnemonic_name_1>*<mnemonic_name_2>
        # This will be used in the title of the plot later
        if '*' in mnemonic_dict["plot_data"]:
            all_data.mnemonic_identifier = product_identifier


        print(f'DONE WITH {mnemonic_dict["name"]}')
        #print(all_data.data)
        return all_data

    def execute(self, mnem_to_query=None, plot_start=None, plot_end=None):
        """Top-level wrapper to run the monitor. Take a requested list of mnemonics to
        process, or assume that mnemonics will be processed.

        Parameters
        ----------
        mnem_to_query : dict
            Mnemonic names to query. This should be a dictionary with the instrument
            names as keys and a list of mnemonic names as the value. This option is
            intended for use
            when someone requests, from the website, an expanded timeframe
            compared to the default. The monitor will then look up the details
            of each mnemonic (i.e. dependencies, averaging) from the standard
            json file, and will run the query using query_start and query_end.

        plot_start : astropy.time.Time
            Start time to use for the query when requested from the website. Note
            that the query will be broken up into multiple queries, each spanning
            the default amount of time, in order to prevent querying for too much
            data at one time.

        plot_end : astropy.time.Time
            End time to use for the query when requested from the website.
        """
        # This is a dictionary that will hold the query results for multiple mnemonics,
        # in an effort to minimize the number of EDB queries and save time.
        self.query_results = {}

        # The cadence with which the EDB is queried. This is different than the query
        # duration. This is the cadence of the query starts, while the duration is the
        # block of time to query over. For example, a cadence of 1 day and a duration
        # of 15 minutes means that the EDB will be queried over 12:00am - 12:15am each
        # day.
        #self.query_cadence = 1 * u.day
        self.query_cadence = datetime.timedelta(days=1)

        # Set up directory structure to hold the saved plots
        config = get_config()
        base_dir = os.path.join(config["outputs"], "edb_telemetry_monitor")

        # Case where the user is requesting the monitor run for some subset of
        # mnemonics for some non-standard time span
        if mnem_to_query is not None:
            if plot_start is None or plot_end is None:
                raise ValueError(("If mnem_to_query is provided, plot_start and plot_end "
                                  "must also be provided."))

            for instrument_name in JWST_INSTRUMENT_NAMES:
                if instrument_name in mnem_to_query:
                    # Read in a list of mnemonics that the instrument teams want to monitor
                    # From either a text file, or a edb_mnemonics_montior database table
                    monitor_dir = os.path.dirname(os.path.abspath(__file__))
                    #mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', f'{instrument_name.lower()}_mnemonics_to_monitor.json')

                    # Define the output directory in which the html files will be saved
                    self.plot_output_dir = os.path.join(base_dir, instrument_name)
                    ensure_dir_exists(self.plot_output_dir)

                    # For development
                    #mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', 'miri_test.json')
                    mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', 'nircam_mnemonic_to_monitor.json')

                    # Read in file with nominal list of mnemonics
                    with open(mnemonic_file) as json_file:
                        mnem_dict = json.load(json_file)

                    # Filter to keep only the requested mnemonics
                    filtered_mnemonic_dict = {}
                    for telem_type in mnem_dict:
                        for mnemonic in mnem_dict[telem_type]:
                            if mnemonic["name"] in mnem_to_query:
                                if telem_type not in filtered_mnemonic_dict:
                                    filtered_mnemonic_dict[telem_type] = []
                                filtered_mnemonic_dict[telem_type].append(mnemonic)

                    self.run(instrument_name, filtered_mnemonic_dict, plot_start=plot_start, plot_end=plot_end)
        else:
            # Here, no input was provided on specific mnemonics to run, so we run the entire suite
            # as defined by the json files.

            # Loop over all instruments
            for instrument_name in ['nircam']:  #JWST_INSTRUMENT_NAMES:
                monitor_dir = os.path.dirname(os.path.abspath(__file__))
                #mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', f'{instrument_name.lower()}_mnemonics_to_monitor.json')

                # For development
                #mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', 'miri_test.json')
                mnemonic_file = os.path.join(monitor_dir, 'edb_monitor_data', 'nircam_mnemonics_to_monitor.json')

                # Define the output directory in which the html files will be saved
                self.plot_output_dir = os.path.join(base_dir, instrument_name)
                ensure_dir_exists(self.plot_output_dir)

                # Read in file with nominal list of mnemonics
                with open(mnemonic_file) as json_file:
                    mnem_dict = json.load(json_file)

                # Run with the entire dictionary
                self.run(instrument_name, mnem_dict, plot_start=plot_start, plot_end=plot_end)




    def run(self, instrument, mnemonic_dict, plot_start=None, plot_end=None):
        """Run the monitor

        """
        # Container to hold and organize all plots
        self.figures = {}
        self.instrument = instrument

        # Query the EDB for all mnemonics for the period of time between the previous query and the current date
        # Use exsiting JWQL EDB code - as shown above (move to within the loop over mnemonics to allow
        # a custom query time for each)
        #today = Time.now()
        #today = Time('2021-09-02 09:00:00')  # for development
        today = datetime.datetime(2021, 9, 4, 9, 0, 0)
        #today = datetime.now()
        #today = datetime.datetime(2022, 3, 24)  # for development

        # Set the limits for the telemetry plots if necessary
        if plot_start is None:
            #plot_start = today - TimeDelta(EDB_DEFAULT_PLOT_RANGE, format='jd')
            plot_start = today - datetime.timedelta(days=EDB_DEFAULT_PLOT_RANGE)

        if plot_end is None:
            plot_end = today


        # Only used as fall-back plot range for cases where there is no data
        self._plot_start = plot_start
        self._plot_end = plot_end
        print('plot_start and plot_end: ', plot_start, plot_end)

        #************FOR TESTING WITH TEXT FILES****************
        #teststarttime = datetime.datetime(2019,1,1,0,0,0)
        #testendtime = datetime.datetime(2019,1,3,0,15,10)
        #************FOR TESTING WITH TEXT FILES****************

        #q = ed.get_mnemonics(mnemonics_to_monitor, starttime, endtime)

        # "Daily" mnemonics. For these, we query only for a small set time range each day.
        # Filter the data to keep that which conforms to the dependencies, then calculate
        # a single mean value for the day
        #for mnemonic in mnemonic_dict['daily_means'] + mnemonic_dict['block_means'] + ...:  ?
        for telem_type in mnemonic_dict:
            print(f'\n\nTELEM_TYPE: {telem_type}\n\n')
            # Figure out the time period over which the mnemonic should be queried
            query_duration = utils.get_query_duration(telem_type)

            # Determine which database tables are needed based on instrument
            if telem_type != 'none':
                self.identify_tables(instrument, telem_type)

            for mnemonic in mnemonic_dict[telem_type]:

                # Only two types of plots are currently supported. Plotting the data in the EdbMnemonic
                # directly, and plotting it as the product with a second EdbMnemonic
                if '*' not in mnemonic["plot_data"] and mnemonic["plot_data"] != 'nominal':
                    raise NotImplementedError(('The plot_data entry in the mnemonic dictionary can currently only '
                                               'be "nominal" or "*<MNEMONIC_NAME>", indicating that the current '
                                               'mnemonic should be plotted as the product of the mnemonic*<MNEMONIC_NAME>. '
                                               'e.g. for a mnemonic that reports current, plot the data as a power by '
                                               'multiplying with a mnemonic that reports voltage. No other mnemonic '
                                               'combination schemes have been implemented.'))

                # A mnemonic that is being monitored in more than one way will have a secondary name to
                # use for the database, stored in the "database_id" key.
                self._usename = 'name'
                if 'database_id' in mnemonic:
                    self._usename = 'database_id'

                if telem_type != 'none':
                    # Find the end time of the previous query. In this case where we are querying over only
                    # some subset of the day, set the previous query time to be the start of the previous
                    # query. Given this, it is easy to simply add a day to the previous query time in order
                    # to come up with the new query time.
                    # usename = 'name'
                    # if 'database_id' in mnemonic:
                    #    usename = 'database_id'

                    #most_recent_search = self.most_recent_search(mnemonic[usename])
                    #most_recent_search = Time('2021-12-13')  # for development
                    #most_recent_search = Time('2021-09-01T00:00:00')  # for development
                    most_recent_search = datetime.datetime(2021, 9, 1, 9, 0, 0) # for development

                    print('most_recent_search, self.query_cadence:', most_recent_search, self.query_cadence)

                    if plot_end > (most_recent_search + self.query_cadence):
                        # Here we need to query the EDB to cover the entire plot range
                        #starttime = most_recent_search + TimeDelta(self.query_cadence)
                        print("We need to query the EDB")
                        starttime = most_recent_search + self.query_cadence
                    else:
                        # Here the entire plot range is before the most recent search,
                        # so all we need to do is query the JWQL database for the data.
                        print("No need to query the EDB")
                        starttime = None

                else:
                    # In the case where telemetry data have no averaging done, we do not store the data
                    # in the JWQL database, in order to save space. So in this case, we will retrieve
                    # all of the data from the EDB directly, from some default start time until the
                    # present day.
                    starttime = plot_start

                    # For development---------
                    #most_recent_search = Time('2021-09-01T00:00:00')  # for development
                    #most_recent_search = datetime.datetime(2022,9,1,9,0,0)  # for development
                    #starttime = most_recent_search + self.query_cadence
                    #starttime = most_recent_search + TimeDelta(self.query_cadence)
                    #For development---------------------


                # Check for the case where, for whatever reason, there have been missed days. If so, we need
                # to run the calculations separately for each day. Should we query for the full time and then
                # filter, or query once per day? The latter is probably slower. Could the former turn into a
                # problem if e.g. someone wants to track a new mnemonic and it's been 100 days since the
                # default most recent search time? Also note that some mnemonics contain data sampled quite
                # frequently, and querying over many days might lead to a very large table and/or slow
                # response.
                if starttime is None:
                    query_start_times = None
                else:
                    query_start_times = []
                    query_end_times = []
                    #time_range = int((plot_end - starttime).to(u.day).value)
                    dtime = plot_end - starttime
                    if dtime > query_duration:
                        full_days = dtime.days
                        partial_day = dtime.seconds
                        # If the time span is not a full day, but long enough to cover the query_duration,
                        # then we can fit in a final query on the last day
                        if partial_day > query_duration.total_seconds():
                            full_days += 1
                    # Create an array of starting and ending query times. Start times are once per day
                    # between the previous query time and the present. End times are the start times
                    # plus the query duration.


                    print(starttime, most_recent_search, self.query_cadence, plot_end, full_days)



                    for delta in range(full_days):
                        #tmp_start = starttime + TimeDelta(delta * u.day)
                        tmp_start = starttime + datetime.timedelta(days=delta)
                        query_start_times.append(tmp_start)
                        #query_end_times.append(tmp_start + TimeDelta(query_duration))
                        query_end_times.append(tmp_start + query_duration)

                    # Make sure the end time of the final query is before the current time
                    if query_end_times[-1] > today:
                        query_end_times = np.array(query_end_times)
                        query_start_times = np.array(query_start_times)
                        valid_end_times = query_end_times <= today
                        query_start_times = query_start_times[valid_end_times]
                        query_end_times = query_end_times[valid_end_times]


                # For development-------------------------
                #query_start_times = [starttime]
                ##query_end_times = [starttime + TimeDelta(480. * u.minute)]
                #query_end_times = [starttime + timedelta(days=0.25)]
                print('query start times: ', query_start_times)
                print('query_end_times: ', query_end_times)
                # For development-------------------------


                if telem_type != 'none':
                    if query_start_times is not None:


                        # UNCOMMENT WHEN DONE TESTING!!!!!
                        new_data = self.multiday_mnemonic_query(mnemonic, query_start_times, query_end_times, telem_type)

                        #************FOR TESTING****************
                        #filename = f'{mnemonic["name"]}_test_data.txt'
                        #new_data = temp_read_test_data(filename, mindate=teststarttime, maxdate=testendtime)
                        #************FOR TESTING****************

                    else:
                        # In this case, all the data needed are already in the JWQLDB, so return an empty
                        # EDBMnemonic instance. This will be combined with the data from the JWQLDB later.
                        info = ed.get_mnemonic_info(mnemonic["name"])
                        new_data = empty_edb_instance(mnemonic[self._usename], plot_start, plot_end, info=info)
                        print("empty", new_data.info["unit"])
                else:
                    new_data = self.multiday_mnemonic_query(mnemonic, query_start_times, query_end_times, telem_type)

                # Save the averaged/smoothed data and dates/times to the database,
                # but only for cases where we are averaging. For cases with no averaging
                # the database would get too large too quickly. In that case the monitor
                # will re-query the EDB for the entire history each time.
                if telem_type != "none":
                    if telem_type != 'every_change':
                        self.add_new_block_db_entry(new_data, query_start_times[-1])
                    else:
                        # Before we can add the every-change data to the database, organize it to make it
                        # easier to access. Note that every_change_data is now a dict rather than an EDBMnemonic instance
                        every_change_data = organize_every_change(new_data)
                        self.add_new_every_change_db_entry(new_data.mnemonic_identifier, every_change_data, mnemonic['dependency'][0]["name"],
                                                           query_start_times[-1])

                    # Retrieve the historical data from the database, so that we can add the new data
                    if telem_type != 'every_change':
                        historical_data = self.get_history(new_data.mnemonic_identifier, plot_start, plot_end, info=new_data.info,
                                                           meta=new_data.meta)
                        ending = starttime
                        if ending is None:
                            ending = plot_end
                        historical_data.requested_end_time = ending
                    else:
                        historical_data = self.get_history_every_change(new_data.mnemonic_identifier, plot_start, plot_end)

                    # Place the historical data into an EdbMnemonic instance
                    #hist_tab = Table()
                    #if len(hist_data["times"]) > 0:
                    #    hist_tab["dates"] = [Time(ele) for ele in hist_data["times"]]
                    #    hist_tab["euvalues"] = hist_data["data"]
                    #
                    # Data in the database go up through the most recent query.
                    # But if we are asking for a time range completely within the time
                    # covered by the database, then the ending time needs to be the
                    # requested ending plot time.
                    #ending = starttime
                    #if ending is None:
                    #    ending = plot_end
                    #else:
                    #    hist_tab["dates"] = []
                    #    hist_tab["euvalues"] = []
                    #    ending = plot_end
                    #
                    #historical_data = ed.EdbMnemonic(new_data.mnemonic_identifier, plot_start, ending,
                    #                                 hist_tab, {}, new_data.info)

                    #historical_data.requested_end_time = ending

                    #if telem_type == 'every_change':
                        #historical_data.every_change_values = hist_data["dependency_values"]


                    # Historical data, which will be averages
                    #historical_data = self.get_history(mnemonic[usename], plot_start, plot_end)

                    # To make plotting easier, create a new EdbMnemonic instance and
                    # populate it with the historical data combined (concatenated) with the
                    # newly averaged data

                    # Now we need to put the newly averaged data into its own EdbMnemonic instance
                    print('COMBINING WITH HISTORY')
                    print('length of historical data: ', len(historical_data))
                    print('length of new data: ', len(new_data))
                    #print(new_data)
                    #print(new_data.data)
                    #new_table = Table()
                    #new_table["dates"] = mnemonic_info.median_times
                    #new_table["euvalues"] = mnemonic_info.mean
                    #new_data = ed.EdbMnemonic(mnemonic["name"], mnemonic_info.requested_start_time, mnemonic_info.requested_end_time,
                    #                          new_table, mnemonic_info.meta, mnemonic_info.info)

                    # FOR DEVELOPMENT----------
                    """
                    #deltatime = np.max(mnemonic_info.median_times) - np.min(mnemonic_info.median_times)
                    htab = Table()
                    #htab["dates"] = [Time('2021-10-01') + TimeDelta(0.2*i, format='jd') for i in range(4)]
                    from datetime import timedelta
                    #htab["dates"] = [new_data.median_times[0] + timedelta(days=0.2*(i+1)) for i in range(4)]
                    if len(new_data) > 0:
                        htab["dates"] = [new_data.data["dates"].data[0] + timedelta(days=0.2*(i+1)) for i in range(-6, -2)]
                        #htab["euvalues"] = np.repeat(new_data.mean, 4)
                        htab["euvalues"] = np.repeat(new_data.data["euvalues"].data[0], 4)
                    else:
                        if telem_type != 'every_change':
                            htab["dates"] = [datetime.datetime(2021, 9, 30) + timedelta(days=0.2*(i+1)) for i in range(-6, -2)]
                            htab["euvalues"] = np.repeat(0.1, 4)
                        else:
                            htab["dates"] = [datetime.datetime(2021, 9, 30) + timedelta(days=0.2*(i+1)) for i in range(-6, -2)]
                            htab["euvalues"] = np.array([0.1, 0.15, 0.1, 0.2])


                    #new_table["dates"] = mnemonic_info.median_times - deltatime - TimeDelta(25, format='sec')
                    #if "database_id" in mnemonic:
                    #    name = mnemonic["database_id"]
                    #else:
                    #    name = mnemonic["name"]
                    historical_data = ed.EdbMnemonic(mnemonic[self._usename], new_data.requested_start_time, new_data.requested_end_time,
                                                     htab, new_data.meta, new_data.info) #, blocks=mnemonic_info.blocks)
                    """
                    # FOR DEVELOPMENT----------


                    # save using the string in mnemonic["database_id"]
                    if telem_type != 'every_change':



                        # Turned off for testing. TURN BACK ON LATER-------------------------------------------------
                        #self.add_new_block_db_entry(new_data, query_start_times[-1])
                        # Now add the new data to the historical data
                        mnemonic_info = new_data + historical_data

                        print('length of mnemonic_info: ', len(mnemonic_info))
                    else:
                        print('Every change data, preparing to combine with history')
                        #print(new_data.every_change_values)

                        # Note that every_change_data is now a dict rather than an EDBMnemonic instance
                        #every_change_data = organize_every_change(new_data)

                        print('length of every_change_data: ', len(every_change_data))

                        # If new_data is completely empty, we should still add an entry to the database, in
                        # order to note the updated most recent query time.
                        #usename = "name"
                        #if "database_id" in mnemonic:
                        #    usename = "database_id"





                        # Turned off for testing. TURN BACK ON LATER-------------------------------------------------
                        #self.add_new_every_change_db_entry(mnemonic[self._usename], every_change_data, mnemonic['dependency'][0]["name"],
                        #                                   query_start_times[-1])





                        # Combine the historical data with the new data from the EDB
                        mnemonic_info = add_every_change_history(historical_data, every_change_data)
                        print('length of mnemonic_info: ', len(mnemonic_info))
                        #combine = every_change_data + historical_data
                        #mnemonic_info - from combination? then could be an edbmnemonic instance or a dict...
                        #mnemonic_info = deepcopy(historical_data)
                        #for key in every_change_data:
                        #    if key in mnemonic_info:
                        #        mnemonic_info[key].extend(every_change_data[key])
                        #    else:
                        #        mnemonic_info[key] = every_change_data[key]
                    # Turned off for testing. TURN BACK ON LATER-------------------------------------------------

                else:
                    mnemonic_info = new_data


                print('COMBINED LENGTH: ', len(mnemonic_info))
                #print('units of mnemonic info data:', mnemonic_info.info["unit"])

                """
                # If there is no new data and no historical data, then create an empty plot and move on
                # to the next mnemonic
                if len(mnemonic_info.data["dates"]) == 0:
                    print(f"Mnemonic {mnemonic['name']} contains no data.")
                    #create_empty_plot(mnemonic['name'])
                    mnemonic_info.bokeh_plot(savefig=True, out_dir=self.plot_output_dir, nominal_value=nominal,
                                                    yellow_limits=yellow, red_limits=red, return_components=False,
                                                    return_fig=True)
                """

                """
                # If the mnemonic is to be plotted as the product with some other mnemonic, then get
                # the other mnemonic's info here
                if '*' in mnemonic["plot_data"]:  # (e.g. "*SB_FJDKN")
                    # Get the data for the mnemonic to be combined, place into an EdbMnemonic instance, and
                    # filter with the same criteria used to filter the original mnemonic's data
                    #combine_mnemonic = {"name": mnemonic["plot_data"].split('*')[1]}
                    #combine_data = self.get_dependency_data(combine_mnemonic, mnemonic_info.data_start_time, mnemonic_info.data_end_time)

                    #combine_tab = Table([combine_data["dates"], combine_data["euvalues"]], names=("dates", "euvalues"))
                    #combine_obj = ed.EdbMnemonic(combine_mnemonic, mnemonic_info.data_start_time, mnemonic_info.data_end_time,
                    #                             combine_tab, self.query_results[combine_mnemonic["name"]].meta,
                    #                             self.query_results[combine_mnemonic["name"]].info)

                    # Since the dependency to plot with can be used for multiple plots with different filtering/
                    # averaging info, it's best to re-retrive this from the EDB for each mnemonic that needs it.
                    combine_dict = deepcopy(mnemonic)
                    combine_dict["name"] = mnemonic["plot_data"].split('*')[1]

                    # Let's add the same suffix to this plot dependency data as is added to the main mnemonic
                    # to be plotted.
                    if "database_id" in mnemonic:
                        suffix = mnemonic["database_id"][len(mnemonic["name"]):]
                        combine_dict["database_id"] = combine_dict["name"] + suffix

                    # Either query the EDB or retreive from self.query_results, or leave empty if data fro the
                    # entire plotting range is already in the JWQL database.
                    if telem_type != 'none':
                        if most_recent_search < plot_end:
                            filtered_combine_obj = self.multiday_mnemonic_query(combine_dict, query_start_times, query_end_times, telem_type)
                        else:
                            #usename = "name"
                            #if "database_id" in mnemonic:
                            #    usename = "database_id"
                            info = ed.get_mnemonic_info(combine_dict["name"])
                            filtered_combine_obj = empty_edb_instance(combine_dict[self._usename], plot_start, plot_end, info=info)
                    else:
                        filtered_combine_obj = self.multiday_mnemonic_query(combine_dict, query_start_times, query_end_times, telem_type)



                    print('FILT:')
                    print(filtered_combine_obj.data)
                    print(filtered_combine_obj.info["unit"])





                    #filtered_combine_obj = self.multiday_mnemonic_query(combine_dict, query_start_times, query_end_times, telem_type)

                    #filtered/averaged data is saved in the database, but what if the data to plot with are
                    #filtered/averaged in a different way than how they were going into the database?
                    #SUFFIXES. Need to add suffixes to input mnemonics to capture different filtering/averaging
                    #schemes.




                    # For cases where averaging was done, create a new EdbMnemonic instance and place the
                    # averaged data into the data attribute, for easier multiplying and plotting later.
                    if telem_type != 'none':





                        # In this case we also need to retrieve the historical data from the database, so that
                        # we can add the new data and create an updated plot
                        if telem_type != 'every_change':
                            historical_combine_data = self.get_history(filtered_combine_obj.mnemonic_identifier, plot_start, plot_end,
                                                                       info=mnemonic_info.info, meta=mnemonic_info.meta)
                            ending = starttime
                            if ending is None:
                                ending = plot_end
                            historical_combine_data.requested_end_time = ending
                        else:
                            historical_combine_data = self.get_history_every_change(filtered_combine_obj.mnemonic_identifier, plot_start, plot_end)

                        if telem_type != 'every_change':





                            # Turned off for testing. TURN BACK ON LATER-------------------------------------------------
                            #self.add_new_block_db_entry(filtered_combine_obj, query_start_times[-1].datetime)






                            # Now add the new data to the historical data
                            data_to_combine = filtered_combine_obj + historical_combine_data
                        else:
                            every_change_combine_data = organize_every_change(filtered_combine_obj)

                            # If new_data is completely empty, we should still add an entry to the database, in
                            # order to note the updated most recent query time.
                            #usename = "name"
                            #if "database_id" in mnemonic:
                            #    usename = "database_id"



                            # Turned off for testing. TURN BACK ON LATER-------------------------------------------------
                            #self.add_new_every_change_db_entry(filtered_combine_obj[self._usename], every_change_combine_data,
                            #                                   filtered_combine_obj['dependency'][0]["name"],
                            #                                   query_start_times[-1])




                            # Combine the historical data with the new data from the EDB
                            data_to_combine = add_every_change_history(historical_combine_data, every_change_combine_data)


                        # When averaging is done, we need to retrieve older data from the database
                        # These data will already be averaged.
                        # USE THE LINE LINE BELOW IRL.
                        #historical_combine_data = self.get_history(combine_mnemonic["name"])


                        # FOR DEVELOPMENT----------------------------
                        htab = Table()
                        from datetime import timedelta
                        #htab["dates"] = [filtered_combine_obj.median_times[0] + timedelta(days=0.2*(i+1)) for i in range(4)]
                        #htab["euvalues"] = np.repeat(filtered_combine_obj.mean, 4)
                        htab["dates"] = [filtered_combine_obj.data["dates"].data[0] + timedelta(days=0.2*(i+1)) for i in range(-6, -2)]
                        htab["euvalues"] = np.repeat(filtered_combine_obj.data["euvalues"].data[0], 4)

                        #new_table["dates"] = mnemonic_info.median_times - deltatime - TimeDelta(25, format='sec')
                        #usename = 'name'
                        #if "database_id" in mnemonic:
                        #    usename = "database_id"
                            #how do we distinguish this case, where the mnemonic name comes from the plot_data entry?
                            #the plot_data entry needs to be the actual mnemonic to use, including suffix?
                            #except we cannot use that to query the EDB.
                        historical_combine_data = ed.EdbMnemonic(filtered_combine_obj.mnemonic_identifier, filtered_combine_obj.requested_start_time,
                                                                 filtered_combine_obj.requested_end_time,
                                                                 htab, filtered_combine_obj.meta, filtered_combine_obj.info) #, blocks=mnemonic_info.blocks)
                        # FOR DEVELOPMENT----------------------------

                        print('Length of filtered mnemonic to multiply by:', len(filtered_combine_obj))
                        print('Length of historical data for multiply mnemonic:', len(historical_combine_data))
                        print('Units of filtered mnemonic to multiply by: ', filtered_combine_obj.info["unit"])
                        print('Units of historical data for multiply mnemonic: ', historical_combine_data.info["unit"])



                        #new_table = Table()
                        #new_table["dates"] = filtered_combine_obj.median_times
                        #new_table["euvalues"] = filtered_combine_obj.mean
                        #filtered_combine_obj = ed.EdbMnemonic(filtered_combine_obj.mnemonic_identifier,
                        #                                      filtered_combine_obj.requested_start_time,
                        #                                      filtered_combine_obj.requested_end_time, new_table, {}, {})

                        # Now add the new data to the historical data
                        #filtered_combine_obj = filtered_combine_obj + historical_combine_data


                        print('Combine queried and hist for multiply mnemonic: ', len(data_to_combine))
                        print('Units of combined queried and history for multiply mnemonic: ', data_to_combine.info["unit"])


                    # Multiply the two menmonics' data in order to create the data to be plotted.
                    # Interpolation is done within the multiplication method
                    previous_id = new_data.mnemonic_identifier
                    if telem_type != 'every_change':
                        print(len(mnemonic_info))
                        print(len(filtered_combine_obj))

                        print('BEFORE MULTIPLYING:')
                        print(mnemonic_info.data)
                        print(mnemonic_info.info["unit"])

                        mnemonic_info = mnemonic_info * data_to_combine
                        mnemonic_info.mnemonic_identifier = f'{previous_id} * {filtered_combine_obj.mnemonic_identifier}'


                        print("After Multiplying:")
                        print(mnemonic_info.data)
                        print(mnemonic_info.info["unit"])

                    else:
                        raise NotImplementedError(("Plotting every-change data in combination with a second mnemonic "
                                                   "is not yet supported, as it has not yet been requested by any "
                                                   "instrument team."))
                        mnemonic_info = mult_every_change_data(mnemonic_info, data_to_combine)
                    """

                # Create and save plot--------------------------------------
                nominal = utils.check_key(mnemonic, "nominal_value")
                yellow = utils.check_key(mnemonic, "yellow_limits")
                red = utils.check_key(mnemonic, "red_limits")

                #daily_means - plot mnemonic_info.means - including history from db
                #block_means - plot mnemonic_info.means - including history from db
                #every_change - plot mnemonic_info.means, but separate lines for each block - complex - .every_change_values
                #time_interval - plot mnemonic_info.means - including history from db
                #none - plot mnemonic_info.data directly - no history to add.

                if telem_type != 'every_change':
                    figure = mnemonic_info.bokeh_plot(savefig=False, out_dir=self.plot_output_dir, nominal_value=nominal,
                                                      yellow_limits=yellow, red_limits=red, return_components=False,
                                                      return_fig=True, show_plot=False)
                else:
                    # Get mean_values from the database
                    ##### NOTE: "every_change" here isn't the best term. This section is for mnemonics
                    # such as the MIRI position sensor ratios and commanded positions. In these cases,
                    # the dependency has a set of possible values (e.g. 'F2550W, 'F770W') and we want to
                    # find the mean of the mnemonic associated with each dependency value. The term "each change"
                    # comes from the MIRI document listing mnemonics to montior. It is NOT the same as
                    # the more generic "change only" telemetry data, where data points in the array represent
                    # only times where the value has changed from what it was previously.
                    figure = plot_every_change_data(mnemonic_info, new_data.mnemonic_identifier, new_data.info["unit"],
                                                    savefig=False, out_dir=self.plot_output_dir, show_plot=False)

                # Store the figure according to the "plot_category" given in the input json file
                self.add_figure(figure, mnemonic["plot_category"])

                ############how do we do this so that plots can be remade if requested by the user?
                ############maybe rather than saving plots we save EdbMnmonic instances? Then rebuild the
                ############plots starting from those?

        # Create a tabbed, gridded set of plots for each category of plot
        self.tabbed_figure()


    def tabbed_figure(self, ncols=3):
        """Create a tabbed figure containing all of the mnemonic plots

        Parameters
        ----------
        ncols : int
            Number of columns of plots in each plot tab
        """
        panel_list = []
        for key, plot_list in self.figures.items():
            grid = gridplot(plot_list, ncols=ncols, merge_tools=False)  # merge_tool=False to allow separate tools for each plot?

            # Create one panel for each plot category
            panel_list.append(Panel(child=grid, title=key))

        # Assign the panels to Tabs
        tabbed = Tabs(tabs=panel_list)

        # Save the tabbed plot to a json file
        item_text = json.dumps(json_item(tabbed, "myplot"))
        basename = f'edb_{self.instrument}_tabbed_plots.json'
        output_file = os.path.join(self.plot_output_dir, basename)
        with open(output_file, 'w') as outfile:
            outfile.write(item_text)
        print(f'JSON file with tabbed plots saved to {outfile}')


def add_every_change_history(dict1, dict2):
    """Combine two dictionaries that contain every change data. For keys that are
    present in both dictionaries, remove any duplicate entries based on date.

    Parameters
    ----------
    dict1 : dict
        First dictionary to combine

    dict2 : dict
        Second dictionary to combine

    Returns
    -------
    dd : collections.defaultdict
        Combined dictionary
    """
    combined = defaultdict(list)

    for key, value in dict1.items():
        if key in dict2:
            if np.min(value[0]) < np.min(dict2[key][0]):
                all_dates = np.append(value[0], dict2[key][0])
                all_data = np.append(value[1], dict2[key][1])
                all_means = np.append(value[2], dict2[key][2])
                all_devs = np.append(value[3], dict2[key][3])
            else:
                all_dates = np.append(dict2[key][0], value[0])
                all_data = np.append(dict2[key][1], value[1])
                all_means = np.append(dict2[key][2], value[2])
                all_devs = np.append(dict2[key][3], value[3])

            # Remove any duplicates, based on the dates' entries
            # Keep track of the indexes of the removed rows, so that any blocks
            # information can be updated
            #unique_dates, unq_idx = np.unique(all_dates, return_index=True)
            #unique_data = all_data[unq_idx]
            #unique_means = all_means[unq_idx]
            #combined[key] = (unique_dates, unique_data, unique_means)

            # Not sure how to treat duplicates here. If we remove duplicates, then
            # the mean values may not be valid any more. For example, if there is a
            # 4 hour overlap, but each mean is for a 24 hour period. We could remove
            # those 4 hours of entries, but then what would we do with the mean values
            # that cover those times. Let's instead warn the user if there are duplicate
            # entries, but don't take any action
            unique_dates = np.unique(all_dates, return_index=False)
            if len(unique_dates) != len(all_dates):
                print(("WARNING - There are duplicate entries in the every-change history "
                       "and the new entry. Keeping and plotting all values, but be sure the "
                       "data look ok."))
            updated_value = (all_dates, all_data, all_means, all_devs)
            combined[key] = updated_value
        else:
            combined[key] = value
    # Add entries for keys that are in dict2 but not dict1
    for key, value in dict2.items():
        if key not in dict1:
            combined[key] = value
    return combined

def calculate_statistics(mnemonic_instance, telemetry_type):
    """
    """
    if telemetry_type == "daily_means":
        print("Calculating daily means")
        mnemonic_instance.daily_stats()
    elif telemetry_type == "block_means":
        print('Calculating block stats')
        mnemonic_instance.block_stats()
    elif telemetry_type == "every_change":
        print('Calculating block stats on change only')
        mnemonic_instance.block_stats()
    elif telemetry_type == "time_interval":
        print('Time interval data')
        stats_duration = utils.get_averaging_time_duration(mnemonic["mean_time_block"])
        mnemonic_instance.timed_stats(stats_duration)
    elif telemetry_type == "none":
        mnemonic_instance.full_stats()
    return mnemonic_instance



def create_empty_plot(title, out_dir='./',):
    """Create and save an empty Bokeh plot

    Parameters
    ----------
    title : str
        Title to add to the plot

    """
    data = {'x_values': [],
            'y_values': []}

    # Create a ColumnDataSource by passing the dict
    source = ColumnDataSource(data=data)

    # Create a plot using the ColumnDataSource's two columns
    fig = figure(title=title)
    fig.line(x=[0], y=[0])
    fig.circle(x='x_values', y='y_values', source=source)

    filename = os.path.join(out_dir, f"telem_plot_{title}.html")
    print(f'\n\nSAVING HTML FILE TO: {filename}')
    output_file(filename=filename, title=self.mnemonic_identifier)
    save(fig)

def empty_edb_instance(name, beginning, ending, meta={}, info={}):
    """Create an EdbMnemonic instance with an empty data table
    """
    tab = Table()
    tab["dates"] = []
    tab["euvalues"] = []
    return ed.EdbMnemonic(name, beginning, ending, tab, meta, info)


def every_change_to_allPoints(data):
    """Convert a table of every-change style mnemonic data into AllPoints.
    To do this, simply add a new data point immediately prior to each existing
    datapoint. The new data should have a value equal to the data in the
    preceding point. This should be enough that the data can be correctly
    interpolated later.

    Parameters
    ----------
    data : astropy.table.Table
        Table of every-change data. Columns should be "dates" and "euvalues"

    Returns
    -------
    new_data : astropy.table.Table
        Updated table with points that can be interpreted as AllPoints
    """
    new_dates = [data["dates"][0]]
    new_values = [data["euvalues"][0]]
    for i, row in enumerate(data[0:-1]):
        # Create a new point very close in time to the next point, with the
        # same value as the current point
        new_values.append(row["euvalues"])
        next_date = data["dates"][i+1]
        delta = next_date - row["dates"]
        delta_secs = datetime.timedelta(seconds=delta.seconds * 0.9999)
        new_dates.append(row["dates"] + delta_secs)

        # Add the date and value of the next point
        new_dates.append(data["dates"][i+1])
        new_values.append(data["euvalues"].data[i+1])

    new_data = Table([new_dates, new_values], names=("dates", "euvalues"))
    return new_data


def organize_every_change(mnemonic):
    """Given an EdbMnemonic instance containing every_change data,
    organize the information such that there are single 1d arrays
    of data and dates for each of the dependency values. This will
    make plotting and saving in the database much more straight
    forward

    Parameters
    ----------
    mnemonic : jwql.edb.engineering_database.EdbMnemonic
        Object containing all data

    Returns
    -------
    all_data : dict
        Dictionary of organized results. Keys are the dependency value,
        and values are tuples. The first element of each tuple is a list
        of dates, the second element is a list of data values, and the third
        is a the signma-clipped mean value of the data.
    """

    print('IN ORGANIZE_EVERY_CHANGE')
    print(mnemonic.data)
    print(mnemonic.blocks)
    print(mnemonic.every_change_values)





    all_data = {}
    unique_vals = np.unique(mnemonic.every_change_values)
    if not isinstance(mnemonic.every_change_values, np.ndarray):
        every_change = np.array(mnemonic.every_change_values)
    else:
        every_change = mnemonic.every_change_values

    # For each dependency value, pull out the corresponding mnemonic values and times.
    for val in unique_vals:
        good = np.where(every_change == str(val))[0]  # val is np.str_ type. need to convert to str
        val_times = mnemonic.data["dates"].data[good]
        val_data = mnemonic.data["euvalues"].data[good]

        # Calculate the mean for each dependency value, and normalize the data
        meanval, medianval, stdevval = sigma_clipped_stats(val_data, sigma=3)
        all_data[val] = (val_times, val_data, meanval, stdevval)

    return all_data


def remove_overlaps():
    """
    """
    if np.min(self.data["dates"]) < np.min(mnem.data["dates"]):
        early_dates = self.data["dates"].data
        late_dates = mnem.data["dates"].data
        early_data = self.data["euvalues"].data
        late_data = mnem.data["euvalues"].data
        early_blocks = self.blocks
        late_blocks = mnem.blocks
    else:
        early_dates = mnem.data["dates"].data
        late_dates = self.data["dates"].data
        early_data = mnem.data["euvalues"].data
        late_data = self.data["euvalues"].data
        early_blocks = mnem.blocks
        late_blocks = self.blocks

    # Remove any duplicates, based on the dates entries
    # Keep track of the indexes of the removed rows, so that any blocks
    # information can be updated
    all_dates = np.append(early_dates, late_dates)
    unique_dates, unq_idx = np.unique(all_dates, return_index=True)

    # Combine the data and keep only unique elements
    all_data = np.append(early_data, late_data)
    unique_data = all_data[unq_idx]


def plot_every_change_data(data, mnem_name, units, show_plot=False, savefig=True, out_dir='./', nominal_value=None, yellow_limits=None,
                           red_limits=None, xrange=(None, None), yrange=(None, None), return_components=True, return_fig=False):
    """Create a plot for mnemonics where we want to see the behavior within
    each change

    Parameters
    ----------
    mnem : collections.defaultdict
        UPDATE DESCRIPTION HERE
        Data to be plotted.

    show_plot : bool
        If True, show plot on screen rather than returning div and script

    savefig : bool
        If True, file is saved to html file

    out_dir : str
        Directory into which the html file is saved

    nominal_value : float
        Expected or nominal value for the telemetry. If provided, a horizontal dashed line
        at this value will be added.

    yellow_limits : list
        2-element list giving the lower and upper limits outside of which the telemetry value
        is considered non-nominal. If provided, the area of the plot between these two values
        will be given a green background, and that outside of these limits will have a yellow
        background.

    red_limits : list
        2-element list giving the lower and upper limits outside of which the telemetry value
        is considered worse than in the yellow region. If provided, the area of the plot outside
        of these two values will have a red background.

    xrange : tuple
        Tuple of min, max datetime values to use as the plot range in the x direction.

    yrange : tuple
        Tuple of min, max datetime values to use as the plot range in the y direction.

    """
    fig = figure(tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type='datetime',
                     title=mnem_name, x_axis_label='Time', y_axis_label=f'{units}')

    if savefig:
        filename = os.path.join(out_dir, f"telem_plot_{mnem_name.replace(' ', '_')}.html")
        print(f'\n\nSAVING HTML FILE TO: {filename}')

    colors = [int(len(Turbo256) / len(data)) * e for e in range(len(data))]


    hover_tool = HoverTool(tooltips=[('Value', '@dep'),
                                     ('Data', '@y{1.11111}'),
                                     ('Date', '@x{%d %b %Y %H:%M:%S}')
                                    ], mode='mouse', renderers=[cdata])
    hover_tool.formatters={'@x': 'datetime'}
    fig.tools.append(hover_tool)


    # Find the min and max values in the x-range. These may be used for plotting
    # the nominal_value line later. Initialize here, and then dial them in based
    # on the data.
    min_time = datetime.datetime.today()
    max_time = datetime.datetime(2021, 12, 25)

    for (key, value), color in zip(data.items(), colors):
        if len(value) > 0:
            val_times, val_data, meanval, stdevval = value
            dependency_val = np.repeat(key, len(val_times))

            # Normalize by the mean so that all data will fit on one plot easily
            val_data /= meanval

            source = ColumnDataSource(data={'x': val_times, 'y': val_data, 'dep': dependency_val})

            data = fig.line(x='x', y='y', line_width=1, line_color=Turbo256[color], source=source, legend_label=key)
            cdata = fig.circle(x='x', y='y', fill_color=Turbo256[color], size=8, source=source, legend_label=key)

            #hover_tool = HoverTool(tooltips=[('Value', '@dep'),
            #                                 ('Data', '@y{1.11111}'),
            #                                 ('Date', '@x{%d %b %Y %H:%M:%S}')
            #                                ], mode='mouse', renderers=[cdata])
            #hover_tool.formatters={'@x': 'datetime'}
            #fig.tools.append(hover_tool)

            if np.min(val_times) < min_val:
                min_time = np.min(val_times)
            if np.max(val_times) > max_val:
                max_time = np.max(val_times)

    # If the input dictionary is empty, then create an empty plot with reasonable
    # x range
    if len(data) == 0:
        null_dates = [self.requested_start_time, self.requested_end_time,]
        source = ColumnDataSource(data={'x': null_times, 'y': [0, 0], 'dep': 'None'})
        data = fig.line(x='x', y='y', line_width=1, line_color=0, source=source, legend_label='None')
        data.visible = False
        totpts = 0
    else:
        numpts = [len(val) for key, val in mnem.items()]
        totpts = np.sum(np.array(numpts))

    # For a plot with zero or one point, set the x and y range to something reasonable
    if totpts < 2:
        fig.x_range=Range1d(self._plot_start - datetime.timedelta(days=1), self._plot_end)
        bottom, top = (-1, 1)
        if yellow_limits is not None:
            bottom, top = yellow_limits
        if red_limits is not None:
            bottom, top = red_limits
        fig.y_range=Range1d(bottom, top)

    # If there is a nominal value provided, plot a dashed line for it
    if nominal_value is not None:
        fig.line([min_time, max_time], [nominal_value, nominal_value], color='black',
                 line_dash='dashed', alpha=0.5)

    # If limits for warnings/errors are provided, create colored background boxes
    if yellow_limits is not None or red_limits is not None:
        fig = add_limit_boxes(fig, yellow=yellow_limits, red=red_limits)

    # Make the x axis tick labels look nice
    fig.xaxis.formatter=DatetimeTickFormatter(microseconds=["%d %b %H:%M:%S.%3N"],
                                              seconds=["%d %b %H:%M:%S.%3N"],
                                              hours=["%d %b %H:%M"],
                                              days=["%d %b %H:%M"],
                                              months=["%d %b %Y %H:%M"],
                                              years=["%d %b %Y"]
                                             )
    fig.xaxis.major_label_orientation = np.pi/4

    # Force the axes' range if requested
    if xrange[0] is not None:
        fig.x_range.start = xrange[0].timestamp()*1000.
    if xrange[1] is not None:
        fig.x_range.end = xrange[1].timestamp()*1000.
    if yrange[0] is not None:
        fig.y_range.start = yrange[0]
    if yrange[1] is not None:
        fig.y_range.end = yrange[1]

    fig.legend.location = "top_left"
    fig.legend.click_policy="hide"

    if savefig:
        output_file(filename=filename, title=mnem_name)
        save(fig)
        set_permissions(filename)

    if show_plot:
        show(fig)
    if return_components:
        script, div = components(fig)
        return [div, script]
    if return_fig:
        return fig



def temp_read_test_data(filename, mindate=None, maxdate=None):
    """Read in a text file with test telemetry data, for development.
    Remove before merging
    """
    from astropy.io import ascii
    data = ascii.read(filename)
    dt = []
    for ele in data["dates"]:
        ints = [int(n) for n in ele.split(',')]
        dt.append(datetime.datetime(ints[0], ints[1], ints[2], ints[3], ints[4], ints[5]))
    dt = np.array(dt)

    vals = data["euvalues"]

    if maxdate is not None:
        good = np.where(dt <= np.array(maxdate))[0]
        print(good, type(good))
        dt = dt[good]
        vals = vals[good]
    else:
        maxdate = dt[-1]

    if mindate is not None:
        good = dt >= mindate
        dt = dt[good]
        vals = vals[good]
    else:
        mindate = dt[0]

    new_tab = Table()
    new_tab["dates"] = dt
    new_tab["euvalues"] = vals

    mnem = filename.strip('_test_data.txt')
    info = ed.get_mnemonic_info(mnem)

    meta = {}
    if mnem == 'SE_ZIMIRICEA':
        allpts = 0
    else:
        allpts = 1
    meta['TlmMnemonics'] = [{'AllPoints': allpts}]

    m = ed.EdbMnemonic(mnem, mindate, maxdate, new_tab, meta, info)
    return m





if __name__ == '__main__':
    monitor = EdbMnemonicMonitor()
    monitor.execute()
