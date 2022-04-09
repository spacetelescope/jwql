#! /usr/bin/env python
"""Module generates conditions over one or more mnemonics

The modules purpose is to return True/False for any times by reference of
certain conditions. If for instance the condition "x>1" over a defined period of
time is needed, the module looks for all elements where the condition applies
and where it does not apply. This generates two lists, which contain the "start"
and "end" times of the condition.
A futher function combines the start- and endtimes to time-tuples between which
the condition is known as TRUE. A "state" function returns True/False for an
exact time attribute, whereby the condition is represented in binary form.

Authors
-------
    - Daniel Kühbacher
    - Bryan Hilbert

Use
---
    This module is not prepared for standalone use.

    For use in programm set condition up like below:

    import the module as follow:
    >>>import condition as cond

    generate list with required conditions:
    >>>con_set = [ cond.equal(m.mnemonic('IMIR_HK_POM_LOOP'),'OFF'),
                cond.smaller(m.mnemonic('IMIR_HK_ICE_SEC_VOLT1'),1),
                cond.greater(m.mnemonic('SE_ZIMIRICEA'),0.2)]

    generate object of condition with the con_set as attribute:
    >>>condition_object=cond.condition(con_set)

    Now the condition_object can return a True/False statement wheather
    the time given as attribut meets the conditions:

    >>>if condition.state(float(element['Primary Time'])):
        -> True when condition for the given time applies
        -> False when condition for the given time is not applicable

Dependencies
------------
    no external files needed

References
----------

Notes
-----

"""
from astropy.table import Table
from copy import deepcopy  # only needed for development
import numpy as np

class condition:
    """Class to hold several subconditions"""

    # contains list of representative time pairs for each subcondition
    #time_pairs = []
    # state of the condition
    #__state = False

    # initializes condition through condition set
    def __init__(self, cond_set):
        """Initialize object with set of conditions
        Parameters
        ----------
        cond_set : list
            list contains subconditions objects
        """
        self.cond_set = cond_set

        # Different from the original version
        self.time_pairs = []
        self.__state = False

    def __len__(self):
        """Return the number of rows in the catalog
        """
        return len(self.cond_set)

    # destructor -> take care that all time_pairs are deleted!
    def __del__(self):
        """Delete object - destructor method"""
        del self.time_pairs[:]

    # prints all stored time pairs (for developement only)
    def print_times(self):
        """Print conditions time pairs on command line (developement)"""
        print('Available time pairs:')
        for times in self.time_pairs:
            print('list: '+str(times))

    def extract_data(self, mnemonic):
        """replace the original extract_data with something faster,
        based on comparing boolean arrays, rather than looping over
        elements of arrays
        """
        #condition is a list of conditions, each of which must have:
        #time_pairs = [con.time_pars for con in conditions]

        #now each element of the time_pairs list should be a list of tuples with (start, end)


        ## Working example---
        #mnemonic = {"dates": np.arange(14), "euvalues": np.array([12., 13., 13., 14, 12, 15, 13, 13, 13, 13, 10, 9, 13, 12])}
        #cond1_times = [(1., 5), (8, 16.)]
        #cond2_times = [(3., 6), (10, 14.)]
        #cond3_times = [(4., 12.)]

        # For each time tuple in each condition, find whether each element in mnemonic falls
        # between the starting and ending times
        #tf1 = [((mnemonic["dates"] >= t[0]) & (mnemonic["dates"] <= t[1])) for t in cond1_times]
        #tf2 = [((mnemonic["dates"] >= t[0]) & (mnemonic["dates"] <= t[1])) for t in cond2_times]
        #tf3 = [((mnemonic["dates"] >= t[0]) & (mnemonic["dates"] <= t[1])) for t in cond3_times]

        # Now for each condition, combine the boolean arrays into a single array that describes
        # whether each element of mnemonic falls within one of the time intervals
        #tf1_flat = tf1[0] | tf1[1]
        #tf2_flat = tf2[0] | tf2[1]
        #tf3_flat = tf3  # because there is only one time interval here

        # Now combine the boolean arrays into a single array that describes whether each element
        # of mnemonic falls within one time interval of all conditions
        #tf = tf1_flat & tf2_flat & tf3_flat
        # Working example---
        # Now, how to we generalize this for arbirary numbers of time intervals for each condition???


        # FOR DEVELOPMENT---------------
        orig_mnem = deepcopy(mnemonic)
        # FOR DEVELOPMENT---------------


        # Generalized code

        # 2D matrix to hold boolean values for all conditions
        tf_matrix = np.zeros((len(self.cond_set), len(mnemonic["dates"]))).astype(bool)



        print('length of self.cond_set:', len(self.cond_set))
        print(self.cond_set[0].time_pairs)



        # Loop over conditions
        for i, cond in enumerate(self.cond_set):
            # Check if any of the time pairs include None, which indicates no good data
            if None in cond.time_pairs[0]:
                self.extracted_data = Table()
                self.extracted_data['dates'] = []
                self.extracted_data['euvalues'] = []
                self.block_indexes = [0, 0]
                return Table(names=('dates', 'euvalues')), None
            else:
                # Find whether each mnemonic time falls within each of the good time blocks


                #print(mnemonic["dates"].data)
                #print(cond.time_pairs)
                #print(condition_list.cond_set[i].time_pairs)

                #print(type(mnemonic))
                #print(mnemonic["dates"])
                #print(type(mnemonic["dates"]))
                #print(mnemonic["dates"].data)


                print('all cond.time_pairs: ', cond.time_pairs)
                #print('menmonic dates: ', mnemonic["dates"].data)



                #need to figure out what to do here.
                #change only mnemonic has one entry at starttime and one at endtime
                #the dependency has a bunch of entries that start before starttime and go until after endtime
                #In the case below, that leads to False in tf_cond here. do we interpolate only if its change=only
                #data? interpolate onto what time list?
                tf_cond = [((mnemonic["dates"].data >= times[0]) & (mnemonic["dates"].data <= times[1])) for times in cond.time_pairs]



                #print(i)
                print('tf_cond:', tf_cond)
                if len(tf_cond) > 1:
                    # If there are multiple blocks of good time pairs, combine them
                    # into a 2D array (rather than list)
                    tf_2d = np.zeros((len(tf_cond), len(tf_cond[1]))).astype(bool)
                    for index in range(len(tf_cond)):
                        tf_2d[index, :] = tf_cond[index]
                    #print('tf_2d:', tf_2d)

                    # Flatten the 2D boolean array. If the mnemonic's time falls within any of
                    # the good time pairs, it should be True here
                    tf_flat = np.any(tf_2d, axis=0)
                    #print('tf_flat:', tf_flat)
                elif len(tf_cond) == 1:
                    # If there is only one block of good times, then no need to create
                    # a 2D array and flatten
                    tf_flat = np.array(tf_cond)
                else:
                    print("uh oh. shouldn't be here.")
                # Create a 2D boolean matrix that will hold the T/F values for all conditions
                tf_matrix[i, :] = tf_flat
                #print('tf_matrix:', tf_matrix)

        # Finally, if the mnemonic's time falls within a good time block for all of the
        # conditions, then it is considered good.
        tf = np.all(tf_matrix, axis=0)

        # Extract the good data and save it in an array
        good_data = Table()
        good_data["dates"] = mnemonic["dates"][tf]
        good_data["euvalues"] = mnemonic["euvalues"][tf]
        self.extracted_data = good_data



        print("Number of entries that are good: ", np.sum(tf))
        print(tf_matrix)

        # We need to keep data from distinct blocks of time separate, because we may
        # need to calculate statistics for each good time block separately. Use tf to
        # find blocks. Anywhere an F falls between some T's, we have a separate block.
        # Save tuples of (start_time, end_time) for blocks.

        # Add a False 0th element
        tf_plus_false = np.insert(tf, 0, False)

        # Now we need to find the indexes where the array switches from False to True.
        # These will be the starting indexes of the blocks. (Remember to subtract 1 in
        # order to account for the added False element)
        switches = tf_plus_false.astype(int)[0:-1] - tf.astype(int)
        switch_to_true = np.where(switches == -1)[0]
        switch_to_false = np.where(switches == 1)[0]


        # Add the final element to switch_to_false if the number of switches are not equal
        # (i.e. if the data are good through the end of the array)
        # NOT NEEDED, since the filtered_indexes loop works on the i-1 element of
        # switch_to_false
        #if len(switch_to_false) - len(switch_to_true) == 1:
        #    switch_to_false = np.append(switch_to_false, -1, len(mnemonic["MJD"]))
        #elif len(switch_to_false) - len(switch_to_true) == 0:
        #    pass
        #else:
        #    raise ValueError("Number of switches of good to bad data are not consistent.")


        # These indexes apply to the original data. Once we extract the good
        # data using tf, we now need to adjust these indexes so that they
        # apply to the extracted data.
        filtered_indexes = []
        for i in range(len(switch_to_true)):
            if i == 0:
                diff = switch_to_true[i]
            else:
                diff = switch_to_true[i] - switch_to_false[i-1]
            switch_to_true -= diff
            switch_to_false -= diff
            filtered_indexes.append(switch_to_true[i])
        self.block_indexes = filtered_indexes


        # Add the index of the final element
        self.block_indexes.append(len(good_data))

        #print("in condition:", len(good_data), len(mnemonic["dates"]))


        #print('BLOCK_INDEXES:', self.block_indexes)
        #print(len(mnemonic["dates"]))
        #print(mnemonic["euvalues"].data)





        #if ((len(self.block_indexes) > 10) & (self.block_indexes[-1] == 7031)):
        #    print(mnemonic.info)

        #    print('tf: ')
        #    for i in range(50):
        #        print(i, tf[i])

        #    print('switch to true)')
        #    for i, t in enumerate(switch_to_true):
        #        print(i, t)

        #    print('switch to false)')
        #    for i, f in enumerate(switch_to_false):
        #        print(i, f)


        #    for i in range(45):
        #        print(i, mnemonic["euvalues"].data[i], orig_mnem["euvalues"].data[i])
            #for i in range(45):
            #    print(i, orig_mnem["euvalues"].data[i])


        #to_true_times = mnemonic["MJD"][switch_to_true]
        #to_false_times = mnemonic["MJD"][switch_to_false]

        # If the first transistion is True->False, then add the initial time entry
        # as a transition to True, in order to help with creating time pairs later
        #if to_false_times[0] < to_true_times[0]:
        #    to_true_times = np.insert(to_true_times, 0, mnemonic["MJD"][0])

        # If the last transision is False->True, then add the final time entry
        # as a transition to False, in order to help with creating time pairs later
        #if to_true_times[-1] > to_false_times[-1]:
        #    to_false_times.append(mnemonic["MJD"][-1])

        #if len(to_true_times) != len(to_false_times):
        #    raise ValueError("Number of T/F transistions are not equal.")

        # Now create a list of tupes of starting and ending times
        #block_time_pairs = [(true_time, false_time) for true_time, false_time in zip(to_true_times, to_false_times)]

        """
        with added F to beginning

        arr    FTTTTFFTTTFFFFT
        shift  TTTTFFTTTFFFFT
        diff   -000+0-00+000-
        nozero 0 4 6 9 13
        """


        #for a mnemonic:
        #    data = [2,3,2,4,3,5,3,2,3,4,3,2,4]
        #    time = [1,2,5,6,8,9,10,11,12,23,24,25]
        #    return this instead of time tuples? indexes_of_blocks = [0, 2, 4, 9]

        # If the first transistion is True->False, then add the initial time entry
        # as a transition to True, in order to help with creating time pairs later
        # THIS IS NOT NEEDED IF WE PREPEND A FALSE TO TF ABOVE
        #if switch_to_false[0] < switch_to_true[0]:
        #    switch_to_true = np.insert(switch_to_true, 0, mnemonic["MJD"][0])

        #return good_data, filtered_indexes


    # returns a interval if time is anywhere in between
    def get_interval(self, time):
        """Returns time interval if availlable, where "time" is in between
        Parameters
        ----------
        time : float
            given time attribute
        Return
        ------
        time_pair : tuple
            pair of start_time and end_time where time is in between
        """
        end_time = 10000000
        start_time = 0

        # do for every condition
        for cond in self.time_pairs:
            # do for every time pair in condition
            for pair in cond:
                if (time > pair[0]) and (time < pair[1]):
                    if (end_time > pair[1]) and (start_time < pair[0]):
                        start_time = pair[0]
                        end_time = pair[1]
                        break
                    else:
                        break

        if (end_time != 10000000) and (start_time != 0):
            return [start_time, end_time]
        else:
            return None

    """
    def generate_time_pairs(start_times, end_times):
        Forms time pairs out of start times and end times
        Parameters
        ----------
        start_times : list
            contains all times where a condition applies
        end_times : list
            contains all times where the condition does not apply
        Return
        ------
        time_pair : list
            list of touples with start and end time

        # internal use only
        time_pair: float = []

        # when the conditons doesn´t apply anyway
        if not start_times:
            time_pair.append((0, 0))

        # check if the condition indicates an open time range
        elif not end_times:
            time_pair.append((start_times[0], 0))

        # generate time pairs
        # for each start time a higher or equal end time is searched for
        # these times form am touple which is appended to  time_pair : list
        else:
            time_hook = 0
            last_start_time = 0

            for start in list(sorted(set(start_times))):

                if(start > time_hook):
                    for end in list(sorted(set(end_times))):

                        if end > start:

                            time_pair.append((start, end))
                            time_hook = end
                            break

            if list(sorted(set(start_times)))[-1] > list(sorted(set(end_times)))[-1]:
                time_pair.append((list(sorted(set(end_times)))[-1], 0))

        return(time_pair)
    """


    """
    def generate_time_pairs(self, good_times, bad_times):
        Define blocks of time where a condition is true. Creates a list of
        tuples of (start time, end time) where a condition is true, given a
        list of times where the condition is true and where it is false.

        For example:
        good_times = [2, 3, 4, 7, 8]
        bad_times = [0, 1, 5, 6, 9, 10]

        Will return:
        [(2, 4), (7, 8)]

        Can we do this with only good_times as input? Yes, if you can assume
        that the delta between consecutive time entries is a constant. Perhaps
        safer to look at bad_times as well.

        Parameters
        ----------
        good_times : list
            List of times where some condition is True

        bad_times : list
            List of times where some condition is False

        Returns
        -------
        good_blocks : list
            List of 2-tuples, where each tuple contains the starting and ending
            time where the condition is True.

        # This is an attempt to replace the original generate_time_pairs above,
        # with an eye towards making it faster. Probably should end up doing some
        # tests to make sure that it really is faster.
        #add check to be sure no time is in both good and bad lists?
        good_times = list(sorted(set(good_times)))
        bad_times = list(sorted(set(bad_times)))


        print('in generate_time_pairs:')
        print(good_times)
        print(bad_times)


        # Take care of the easy cases, where all times are good or all are bad
        if len(bad_times) == 0:
            if len(good_times) > 0:
                # All values are good
                return [(good_times[0], good_times[-1])]
            else:
                # No good or bad values
                raise ValueError("No good or bad values provided. Unable to create list of corresponding times.")
        else:
            if len(good_times) == 0:
                # All values are bad
                return [(None, None)]

        # Now the case where there are both good and bad input times
        # Combine and sort the good and bad times lists
        all_times = np.array(good_times + bad_times)
        sort_idx = np.argsort(all_times)
        all_times = all_times[sort_idx]


        print(all_times)


        # Create boolean arrays to match the time arrays. Combine in the same
        # way as the good and bad time lists above.
        good = [True] * len(good_times)
        bad = [False] * len(bad_times)
        all_vals = np.array(good + bad)
        all_vals = all_vals[sort_idx]


        print(all_vals)

        # Find the indexes where the value switches from one element to the next
        a_change_indexes = np.where(all_vals[:-1] != all_vals[1:])[0]
        change_indexes = a_change_indexes + 1
        change_indexes = np.insert(change_indexes, 0, 0)
        change_len = len(change_indexes) + 1


        print(change_indexes)


        # Now create tuples of the start and end times where the values change
        # We need to know if the first element of the data is True or False,
        # in order to get the index counters correct below. Note the we can use
        # "if all_vals[0] == True:"" or "if all_vals[0]:"" here. I prefer the
        # former, for readability.
        if all_vals[0] == True:
            start_idx = 0
            counter_delta = 0
        else:
            start_idx = 1
            counter_delta = 1

        # We need to loop over EVERY OTHER change index, so that in the end we have a list
        # of tuples of only the good_times. i.e. we need to skip the blocks corresponding to
        # the bad_times.
        good_blocks = []
        for counti, strt in enumerate(change_indexes[start_idx:len(change_indexes):2]):
            i = counti * 2 + counter_delta

            print(counti, start_idx, strt, i, len(change_indexes))

            if i < (len(change_indexes) - 1):
                print('initial', all_times[strt], all_times[change_indexes[i+1]-1])
                good_blocks.append((all_times[strt], all_times[change_indexes[i+1]-1]))
            else:
                print('final',all_times[strt], all_times[-1])
                good_blocks.append((all_times[strt], all_times[-1]))



        print('good_blocks:',good_blocks)

        return good_blocks
    """


    def state(self, time):
        """Checks whether condition is true or false at a given time
        Parameters
        ----------
        time : float
            input time for condition query
        Return
        ------
        state : bool
            True/False statement whether the condition applies or not
        """
        # returns state of the condition at a given time
        # if state(given time)==True -> condition is true
        # if state(given time)==False -> condition is false
        # #checks condition for every sub condition in condition set (subconditions)

        state = self.__state

        for cond in self.time_pairs:

            if self.__check_subcondition(cond, time):
                state = True
            else:
                state = False
                break

        return state

    def __check_subcondition(self, cond, time):

        # if there are no values availlable
        if cond[0][0] == 0:
            return False

        for time_pair in cond:
            #if just a positive time is availlable, return true
            if (time_pair[1] == 0) and (time > time_pair[0]):

                return True

            #if given time occurs between a time pair, return true
            elif (time_pair[0]) <= time and (time < time_pair[1]):

                return True

            else:
                pass
















class relation():
    """Base class for more specific relationship classes (e.g. equal)
    """
    def __init__(self):
        self.time_pairs = []

    def generate_time_pairs(self, good_times, bad_times):
        """Define blocks of time where a condition is true. Creates a list of
        tuples of (start time, end time) where a condition is true, given a
        list of times where the condition is true and where it is false.

        For example:
        good_times = [2, 3, 4, 7, 8]
        bad_times = [0, 1, 5, 6, 9, 10]

        Will return:
        [(2, 4), (7, 8)]

        Can we do this with only good_times as input? Yes, if you can assume
        that the delta between consecutive time entries is a constant. Perhaps
        safer to look at bad_times as well.

        Parameters
        ----------
        good_times : list
            List of times where some condition is True

        bad_times : list
            List of times where some condition is False

        Returns
        -------
        good_blocks : list
            List of 2-tuples, where each tuple contains the starting and ending
            time where the condition is True.
        """
        # This is an attempt to replace the original generate_time_pairs above,
        # with an eye towards making it faster. Probably should end up doing some
        # tests to make sure that it really is faster.
        #add check to be sure no time is in both good and bad lists?
        good_times = list(sorted(set(good_times)))
        bad_times = list(sorted(set(bad_times)))

        # Take care of the easy cases, where all times are good or all are bad
        if len(bad_times) == 0:
            if len(good_times) > 0:
                # All values are good
                return [(good_times[0], good_times[-1])]
            else:
                # No good or bad values
                raise ValueError("No good or bad values provided. Unable to create list of corresponding times.")
        else:
            if len(good_times) == 0:
                # All values are bad
                return [(None, None)]

        # Now the case where there are both good and bad input times
        # Combine and sort the good and bad times lists
        all_times = np.array(good_times + bad_times)
        sort_idx = np.argsort(all_times)
        all_times = all_times[sort_idx]

        # Create boolean arrays to match the time arrays. Combine in the same
        # way as the good and bad time lists above.
        good = [True] * len(good_times)
        bad = [False] * len(bad_times)
        all_vals = np.array(good + bad)
        all_vals = all_vals[sort_idx]

        # Find the indexes where the value switches from one element to the next
        a_change_indexes = np.where(all_vals[:-1] != all_vals[1:])[0]
        change_indexes = a_change_indexes + 1
        change_indexes = np.insert(change_indexes, 0, 0)
        change_len = len(change_indexes) + 1

        # Now create tuples of the start and end times where the values change
        # We need to know if the first element of the data is True or False,
        # in order to get the index counters correct below. Note the we can use
        # "if all_vals[0] == True:"" or "if all_vals[0]:"" here. I prefer the
        # former, for readability.
        if all_vals[0] == True:
            start_idx = 0
            counter_delta = 0
        else:
            start_idx = 1
            counter_delta = 1

        # We need to loop over EVERY OTHER change index, so that in the end we have a list
        # of tuples of only the good_times. i.e. we need to skip the blocks corresponding to
        # the bad_times.
        good_blocks = []
        for counti, strt in enumerate(change_indexes[start_idx:len(change_indexes):2]):
            i = counti * 2 + counter_delta

            #print(counti, start_idx, strt, i, len(change_indexes))

            if i < (len(change_indexes) - 1):
                #print('initial', all_times[strt], all_times[change_indexes[i+1]-1])
                good_blocks.append((all_times[strt], all_times[change_indexes[i+1]-1]))
            else:
                #print('final',all_times[strt], all_times[-1])
                good_blocks.append((all_times[strt], all_times[-1]))



        #print('good_blocks:',good_blocks)

        return good_blocks



class equal(relation):
    """Class to hold single "is equal" subcondition"""
    def __init__(self, mnemonic, value):
        """Initializes subconditon
        Parameters
        ----------
        mnemonic : dict
            Dictionary for a single mnemonic. "MJD" key holds time values,
            and "data" key holds corresponding telemetry data values. Each
            should be a 1d numpy array.

        value : str or float or int
            Comparison value for equal statement
        """
        relation.__init__(self)

        self.mnemonic = mnemonic
        self.value = value
        self.mnemonic["euvalues"] = np.array(self.mnemonic["euvalues"])  # check if this is needed, might already be array as returned by EDB
        self.mnemonic["dates"] = np.array(self.mnemonic["dates"])    # check if this is needed, might already be array as returned by EDB
        self.time_pairs = self.cond_true_time()

    def cond_true_time(self):
        """Find all times whose values are equal to the given comparison value

        Return
        ------
        time_pairs : list
            List of 2-tuples where each tuple contains the starting and
            ending times of a block of data that matches the condition
        """
        good_points = np.where(self.mnemonic["euvalues"] == self.value)[0]
        bad_points = np.where(self.mnemonic["euvalues"] != self.value)[0]
        good_time_values = self.mnemonic["dates"][good_points]
        bad_time_values = self.mnemonic["dates"][bad_points]
        time_pairs = self.generate_time_pairs(good_time_values, bad_time_values)
        return time_pairs


class greater_than(relation):
    """Class to hold single "greater than" subcondition"""
    def __init__(self, mnemonic, value):
        """Initializes subconditon
        Parameters
        ----------
        mnemonic : dict
            Dictionary for a single mnemonic. "MJD" key holds time values,
            and "data" key holds corresponding telemetry data values

        value : float
            Comparison value for equal statement
        """
        relation.__init__(self)

        self.mnemonic = mnemonic
        self.value = value
        self.time_pairs = self.cond_true_time()

    def cond_true_time(self):
        """Find all times whose corresponding values are greater than a
        given comparison value

        Return
        ------
        time_pairs : list
            List of 2-tuples where each tuple contains the starting and
            ending times of a block of data that matches the condition
        """
        good_points = np.where(self.mnemonic["euvalues"] > self.value)[0]
        bad_points = np.where(self.mnemonic["euvalues"] <= self.value)[0]
        good_time_values = self.mnemonic["dates"][good_points]
        bad_time_values = self.mnemonic["dates"][bad_points]
        time_pairs = self.generate_time_pairs(good_time_values, bad_time_values)
        return time_pairs


class less_than(relation):
    """Class to hold single "greater than" subcondition"""
    def __init__(self, mnemonic, value):
        """Initializes subconditon
        Parameters
        ----------
        mnemonic : dict
            Dictionary for a single mnemonic. "MJD" key holds time values,
            and "data" key holds corresponding telemetry data values

        value : float
            Coparison value for equal statement
        """
        self.mnemonic = mnemonic
        self.value = value
        self.time_pairs = self.cond_true_time()

    def cond_true_time(self):
        """Find all times whose corresponding values are less than a
        given comparison value

        Return
        ------
        time_pairs : list
            List of 2-tuples where each tuple contains the starting and
            ending times of a block of data that matches the condition
        """
        good_points = np.where(self.mnemonic["euvalues"] < self.value)[0]
        bad_points = np.where(self.mnemonic["euvalues"] >= self.value)[0]
        good_time_values = self.mnemonic["dates"][good_points]
        bad_time_values = self.mnemonic["dates"][bad_points]
        time_pairs = self.generate_time_pairs(good_time_values, bad_time_values)
        return time_pairs




def extract_data(condition_list, mnemonic):
    """
    MOVED INTO condition class



    replace the original extract_data with something faster,
    based on comparing boolean arrays, rather than looping over
    elements of arrays
    """
    #condition is a list of conditions, each of which must have:
    #time_pairs = [con.time_pars for con in conditions]

    #now each element of the time_pairs list should be a list of tuples with (start, end)


    ## Working example---
    #mnemonic = {"MJD": np.arange(14), "data": np.array([12., 13., 13., 14, 12, 15, 13, 13, 13, 13, 10, 9, 13, 12])}
    #cond1_times = [(1., 5), (8, 16.)]
    #cond2_times = [(3., 6), (10, 14.)]
    #cond3_times = [(4., 12.)]

    # For each time tuple in each condition, find whether each element in mnemonic falls
    # between the starting and ending times
    #tf1 = [((mnemonic["MJD"] >= t[0]) & (mnemonic["MJD"] <= t[1])) for t in cond1_times]
    #tf2 = [((mnemonic["MJD"] >= t[0]) & (mnemonic["MJD"] <= t[1])) for t in cond2_times]
    #tf3 = [((mnemonic["MJD"] >= t[0]) & (mnemonic["MJD"] <= t[1])) for t in cond3_times]

    # Now for each condition, combine the boolean arrays into a single array that describes
    # whether each element of mnemonic falls within one of the time intervals
    #tf1_flat = tf1[0] | tf1[1]
    #tf2_flat = tf2[0] | tf2[1]
    #tf3_flat = tf3  # because there is only one time interval here

    # Now combine the boolean arrays into a single array that describes whether each element
    # of mnemonic falls within one time interval of all conditions
    #tf = tf1_flat & tf2_flat & tf3_flat
    # Working example---
    # Now, how to we generalize this for arbirary numbers of time intervals for each condition???


    # Generalized code

    # 2D matrix to hold boolean values for all conditions
    tf_matrix = np.zeros((len(condition_list), len(mnemonic["MJD"]))).astype(bool)

    # Loop over conditions
    for i, cond in enumerate(condition_list.cond_set):
        # Check if any of the time pairs include None, which indicates no good data
        if None in cond.time_pairs[0]:
            return Table(names=('MJD', 'data')), None

        # Find whether each mnemonic time falls within each of the good time blocks


        #print(mnemonic["MJD"].data)
        #print(cond.time_pairs)
        #print(condition_list.cond_set[i].time_pairs)


        tf_cond = [((mnemonic["MJD"].data >= times[0]) & (mnemonic["MJD"].data <= times[1])) for times in cond.time_pairs]
        #print(i)
        #print('tf_cond:', tf_cond)
        if len(tf_cond) > 1:
            # If there are multiple blocks of good time pairs, combine them
            # into a 2D array (rather than list)
            tf_2d = np.zeros((len(tf_cond), len(tf_cond[1]))).astype(bool)
            for index in range(len(tf_cond)):
                tf_2d[index, :] = tf_cond[index]
            #print('tf_2d:', tf_2d)

            # Flatten the 2D boolean array. If the mnemonic's time falls within any of
            # the good time pairs, it should be True here
            tf_flat = np.any(tf_2d, axis=0)
            #print('tf_flat:', tf_flat)
        elif len(tf_cond) == 1:
            # If there is only one block of good times, then no need to create
            # a 2D array and flatten
            tf_flat = np.array(tf_cond)
        else:
            print("uh oh. shouldn't be here.")
        # Create a 2D boolean matrix that will hold the T/F values for all conditions
        tf_matrix[i, :] = tf_flat
        #print('tf_matrix:', tf_matrix)

    # Finally, if the mnemonic's time falls within a good time block for all of the
    # conditions, then it is considered good.
    tf = np.all(tf_matrix, axis=0)

    # Extract the good data and save it in an array
    good_data = Table()
    good_data["MJD"] = mnemonic["MJD"][tf]
    good_data["data"] = mnemonic["data"][tf]

    #do we need the info below??
    #we already have the time_pairs, which can be
    #used to break the data into blocks for averaging.
    #Maybe we dont need all this indexing stuff after all??
    #I guess it will be needed for the case of time-based averages,
    #on the assumption that we want to create bins based on time but also
    #avoid having bins cross blocks of invalid data? So if we are averaging
    #data every 30 minutes, but we have a 5 minute block of good data,
    #followed by 15 minutes of bad data, then 10 minutes of good data,
    #we want to treat the 5 minute and 10 minute periods of data separately???

    # We need to keep data from distinct blocks of time separate, because we may
    # need to calculate statistics for each good time block separately. Use tf to
    # find blocks. Anywhere an F falls between some T's, we have a separate block.
    # Save tuples of (start_time, end_time) for blocks.

    # Add a False 0th element
    tf_plus_false = np.insert(tf, 0, False)

    # Now we need to find the indexes where the array switches from False to True.
    # These will be the starting indexes of the blocks. (Remember to subtract 1 in
    # order to account for the added False element)
    switches = tf_plus_false.astype(int)[0:-1] - tf.astype(int)
    switch_to_true = np.where(switches == -1)[0]
    switch_to_false = np.where(switches == 1)[0]


    # Add the final element to switch_to_false if the number of switches are not equal
    # (i.e. if the data are good through the end of the array)
    # NOT NEEDED, since the filtered_indexes loop works on the i-1 element of
    # switch_to_false
    #if len(switch_to_false) - len(switch_to_true) == 1:
    #    switch_to_false = np.append(switch_to_false, -1, len(mnemonic["MJD"]))
    #elif len(switch_to_false) - len(switch_to_true) == 0:
    #    pass
    #else:
    #    raise ValueError("Number of switches of good to bad data are not consistent.")


    # These indexes apply to the original data. Once we extract the good
    # data using tf, we now need to adjust these indexes so that they
    # apply to the extracted data.
    filtered_indexes = []
    for i in range(len(switch_to_true)):
        if i == 0:
            diff = switch_to_true[i]
        else:
            diff = switch_to_true[i] - switch_to_false[i-1]
        switch_to_true -= diff
        switch_to_false -= diff
        filtered_indexes.append(switch_to_true[i])




    #to_true_times = mnemonic["MJD"][switch_to_true]
    #to_false_times = mnemonic["MJD"][switch_to_false]

    # If the first transistion is True->False, then add the initial time entry
    # as a transition to True, in order to help with creating time pairs later
    #if to_false_times[0] < to_true_times[0]:
    #    to_true_times = np.insert(to_true_times, 0, mnemonic["MJD"][0])

    # If the last transision is False->True, then add the final time entry
    # as a transition to False, in order to help with creating time pairs later
    #if to_true_times[-1] > to_false_times[-1]:
    #    to_false_times.append(mnemonic["MJD"][-1])

    #if len(to_true_times) != len(to_false_times):
    #    raise ValueError("Number of T/F transistions are not equal.")

    # Now create a list of tupes of starting and ending times
    #block_time_pairs = [(true_time, false_time) for true_time, false_time in zip(to_true_times, to_false_times)]

    """
    with added F to beginning

    arr    FTTTTFFTTTFFFFT
    shift  TTTTFFTTTFFFFT
    diff   -000+0-00+000-
    nozero 0 4 6 9 13
    """


    #for a mnemonic:
    #    data = [2,3,2,4,3,5,3,2,3,4,3,2,4]
    #    time = [1,2,5,6,8,9,10,11,12,23,24,25]
    #    return this instead of time tuples? indexes_of_blocks = [0, 2, 4, 9]

    # If the first transistion is True->False, then add the initial time entry
    # as a transition to True, in order to help with creating time pairs later
    # THIS IS NOT NEEDED IF WE PREPEND A FALSE TO TF ABOVE
    #if switch_to_false[0] < switch_to_true[0]:
    #    switch_to_true = np.insert(switch_to_true, 0, mnemonic["MJD"][0])

    return good_data, filtered_indexes






"""
def extract_data(condition, mnemonic):
    Extract data from a given mnemmonic if all of the requested
    conditions are satisfied.

    Parameters
    ----------
    condition : conidtion obj
        conditon object that holds one or more subconditions

    mnemonic : astropy.table.Table
        Table with value and time data for a single mnemonic

    Return
    ------
    good_data : astropy.table.Table
        Data during times when all conditions are met

    extracted_times = []
    extracted_data = []
    good_data = Table()

    # Look for all values that fit to the given conditions
    for element in mnemonic:
        if condition.state(float(element['times'])):
            extracted_times.append(float(element['times']))
            extracted_data.append(float(element['data']))


    #HERE: produce a list of tuples where the final filtered data
    #has come from. Like the time_pairs list for a single condition
    #Or perhaps just a list of index numbers where the filtered data
    #has a break? we need to be able to calculate means over each block
    #later.

    good_data["data"] = extracted_data
    good_data["MJD"] = extracted_times
    return good_data
"""


# Test case with a single relation class that uses exec()
class relation_test():
    """Base class for more specific relationship classes (e.g. equal)
    """
    def __init__(self, mnemonic, rel, value):
        self.time_pairs = []
        self.mnemonic = mnemonic
        self.value = value

        if rel == "=":
            rel = "=="
        self.rel = rel

        self.time_pairs = self.cond_true_time()

        #print("\n\n\nTIME_PAIRS:")
        #print(len(self.time_pairs))
        #print(self.time_pairs)

        if len(self.time_pairs) > 1:
            goods1 = np.where(self.mnemonic["dates"] == self.time_pairs[0][0])[0]
            goode1 = np.where(self.mnemonic["dates"] == self.time_pairs[0][1])[0]
            goods2 = np.where(self.mnemonic["dates"] == self.time_pairs[1][0])[0]
            goode2 = np.where(self.mnemonic["dates"] == self.time_pairs[1][1])[0]
            #print(self.mnemonic["dates"].data[goods1], self.mnemonic["dates"].data[goode1], self.mnemonic["euvalues"].data[goods1], self.mnemonic["euvalues"].data[goode1])
            #print(self.mnemonic["dates"].data[goods2], self.mnemonic["dates"].data[goode2], self.mnemonic["euvalues"].data[goods2], self.mnemonic["euvalues"].data[goode2])
            #print(self.mnemonic["dates"].data[goode1+1], self.mnemonic["euvalues"].data[goode1+1])




    def cond_true_time(self):
        """Find all times whose corresponding values are less than a
        given comparison value

        Return
        ------
        time_pairs : list
            List of 2-tuples where each tuple contains the starting and
            ending times of a block of data that matches the condition
        """
        if self.rel == '>':
            opp = '<='
        elif self.rel == '<':
            opp = '>='
        elif self.rel == '==':
            opp = '!='
        elif self.rel == '!=':
            opp = '=='
        elif self.rel == '<=':
            opp = '>'
        elif self.rel == '>=':
            opp = '<'
        else:
            raise ValueError(f'Unrecognized relation: {self.rel}')

        good_points = eval(f'np.where(self.mnemonic["euvalues"] {self.rel} self.value)[0]')
        bad_points = eval(f'np.where(self.mnemonic["euvalues"] {opp} self.value)[0]')

        #print('In cond_true_time in relation_test:')
        #print(self.rel, self.value)
        #print(self.mnemonic["euvalues"])
        #print('cond_true_time:')
        #print(self.mnemonic)
        #print(self.rel, self.value)
        #print(len(good_points), len(bad_points))
        #print('\n')






        good_time_values = self.mnemonic["dates"][good_points]
        bad_time_values = self.mnemonic["dates"][bad_points]

        #try:
        #    print('CHECK:')
        #    print(self.mnemonic["dates"].data[2571:2574])
        #    print(self.mnemonic["euvalues"].data[2571:2574])
        #except:
        #    pass


        time_pairs = self.generate_time_pairs(good_time_values, bad_time_values)
        return time_pairs


    def generate_time_pairs(self, good_times, bad_times):
        """Define blocks of time where a condition is true. Creates a list of
        tuples of (start time, end time) where a condition is true, given a
        list of times where the condition is true and where it is false.

        For example:
        good_times = [2, 3, 4, 7, 8]
        bad_times = [0, 1, 5, 6, 9, 10]

        Will return:
        [(2, 4), (7, 8)]

        Can we do this with only good_times as input? Yes, if you can assume
        that the delta between consecutive time entries is a constant. Perhaps
        safer to look at bad_times as well.

        Parameters
        ----------
        good_times : list
            List of times where some condition is True

        bad_times : list
            List of times where some condition is False

        Returns
        -------
        good_blocks : list
            List of 2-tuples, where each tuple contains the starting and ending
            time where the condition is True.
        """
        # This is an attempt to replace the original generate_time_pairs above,
        # with an eye towards making it faster. Probably should end up doing some
        # tests to make sure that it really is faster.
        #add check to be sure no time is in both good and bad lists?

        #print('GOOD_TIMES:')
        #print(len(good_times))
        #print(good_times[2571:2574])
        #print('BAD_TIMES:')
        #print(bad_times.data[0:10])


        good_times = list(sorted(set(good_times)))
        bad_times = list(sorted(set(bad_times)))


        #print('in generate_time_pairs:')
        #print(good_times[0:10])
        #print('\n\n\n')
        #print(bad_times[0:10])

        # Take care of the easy cases, where all times are good or all are bad
        if len(bad_times) == 0:
            if len(good_times) > 0:
                # All values are good
                return [(good_times[0], good_times[-1])]
            else:
                # No good or bad values
                raise ValueError("No good or bad values provided. Unable to create list of corresponding times.")
        else:
            if len(good_times) == 0:
                # All values are bad.
                return [(None, None)]

        # Now the case where there are both good and bad input times
        # Combine and sort the good and bad times lists
        all_times = np.array(good_times + bad_times)
        sort_idx = np.argsort(all_times)
        all_times = all_times[sort_idx]


        #print('ALL_TIMES')
        #print(all_times)


        # Create boolean arrays to match the time arrays. Combine in the same
        # way as the good and bad time lists above.
        good = [True] * len(good_times)
        bad = [False] * len(bad_times)
        all_vals = np.array(good + bad)
        all_vals = all_vals[sort_idx]

        #print('ALL_VALS:')
        #print(all_vals)

        # Find the indexes where the value switches from one element to the next
        a_change_indexes = np.where(all_vals[:-1] != all_vals[1:])[0]
        change_indexes = a_change_indexes + 1
        change_indexes = np.insert(change_indexes, 0, 0)
        change_len = len(change_indexes) + 1

        #print('CHANGE_INDEXES:')
        #print(change_indexes)

        #print(all_vals[change_indexes[1]-1:change_indexes[1]+2])
        #print(all_times[change_indexes[1]-1:change_indexes[1]+2])
        #print(good_times[2571:2574])
        #print(bad_times[0:10])


        # Now create tuples of the start and end times where the values change
        # We need to know if the first element of the data is True or False,
        # in order to get the index counters correct below. Note the we can use
        # "if all_vals[0] == True:"" or "if all_vals[0]:"" here. I prefer the
        # former, for readability.
        if all_vals[0] == True:
            start_idx = 0
            counter_delta = 0
        else:
            start_idx = 1
            counter_delta = 1

        # We need to loop over EVERY OTHER change index, so that in the end we have a list
        # of tuples of only the good_times. i.e. we need to skip the blocks corresponding to
        # the bad_times.
        good_blocks = []
        for counti, strt in enumerate(change_indexes[start_idx:len(change_indexes):2]):
            i = counti * 2 + counter_delta

            #print(counti, start_idx, strt, i, len(change_indexes))

            if i < (len(change_indexes) - 1):
                #print('initial', all_times[strt], all_times[change_indexes[i+1]-1])
                good_blocks.append((all_times[strt], all_times[change_indexes[i+1]-1]))
            else:
                #print('final',all_times[strt], all_times[-1])
                good_blocks.append((all_times[strt], all_times[-1]))



        #print('good_blocks:',good_blocks)


        return good_blocks






if __name__ == '__main__':
    pass
