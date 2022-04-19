#! /usr/bin/env python
"""Module generates conditions over one or more mnemonics

This module's purpose is to filter input data based on a given
list of conditions. Data matching the list of conditions can be
extracted.

If for instance we have a table of time/data values for a particular
mnemonic, and we wish to extract all data where the conditions "x>1"
and "y<0.25" are true, the module looks for all elements where the
condition applies and where it does not apply. Data points that match
the conditions are then copied into a new table.

Authors
-------
    - Daniel Kühbacher
    - Bryan Hilbert

Use
---
    This module is not prepared for standalone use.

    For use in program set condition up like below:

    import the module as follows:
    >>>import condition as cond

    Create a list of conditions, each with a relation (e.g. '>'')
    and a threshold value.
    >>>all_conditions = []
    >>>dep = {"dates": [list_of_datetimes], "euvalues": [list_of_values]}
    >>>good_times_1 = cond.relation_test(dep, '>', 0.25)

    >>>dep2 = {"dates": [list_of_datetimes], "euvalues": [list_of_values]}
    >>>good_times_2 = cond.relation_test(dep2, '>', 0.25)

    Place condition list into instance of condition class.
    >>>full_condition = cond.condition(all_conditions)

    Call the extract_data() method and provide an astropy Table containing
    information to be checked against the conditions
    >>>full_condition.extract_data(data_table)

    full_condition.extracted_data is then an astropy Table containing
    the data that matches the list of conditions
"""
from astropy.table import Table
from copy import deepcopy  # only needed for development
import numpy as np


class condition:
    """Class to hold several subconditions"""
    def __init__(self, cond_set):
        """Initialize object with set of conditions

        Parameters
        ----------
        cond_set : list
            List of subconditions objects
        """
        self.cond_set = cond_set

        # Initialize parameters
        self.time_pairs = []
        self.__state = False

    def __len__(self):
        """Return the number of rows in the catalog
        """
        return len(self.cond_set)

    def __del__(self):
        """Delete object - destructor method"""
        del self.time_pairs[:]

    def print_times(self):
        """Print conditions time pairs on command line (developement)"""
        print('Available time pairs:')
        for times in self.time_pairs:
            print('list: ' + str(times))

    def extract_data(self, mnemonic):
        """Extract data from the mnemonic that match the condition

        condition is a list of conditions, each of which must have:
        time_pairs = [con.time_pars for con in conditions]

        Each element of the time_pairs list should be a list of tuples with (start, end)

        Working example---
        mnemonic = {"dates": np.arange(14), "euvalues": np.array([12., 13., 13., 14, 12, 15, 13, 13, 13, 13, 10, 9, 13, 12])}
        cond1_times = [(1., 5), (8, 16.)]
        cond2_times = [(3., 6), (10, 14.)]
        cond3_times = [(4., 12.)]

        For each time tuple in each condition, find whether each element in mnemonic falls
        between the starting and ending times
        tf1 = [((mnemonic["dates"] >= t[0]) & (mnemonic["dates"] <= t[1])) for t in cond1_times]
        tf2 = [((mnemonic["dates"] >= t[0]) & (mnemonic["dates"] <= t[1])) for t in cond2_times]
        tf3 = [((mnemonic["dates"] >= t[0]) & (mnemonic["dates"] <= t[1])) for t in cond3_times]

        Now for each condition, combine the boolean arrays into a single array that describes
        whether each element of mnemonic falls within one of the time intervals
        tf1_flat = tf1[0] | tf1[1]
        tf2_flat = tf2[0] | tf2[1]
        tf3_flat = tf3  # because there is only one time interval here

        Now combine the boolean arrays into a single array that describes whether each element
        of mnemonic falls within one time interval of all conditions
        tf = tf1_flat & tf2_flat & tf3_flat
        """
        # 2D matrix to hold boolean values for all conditions
        tf_matrix = np.zeros((len(self.cond_set), len(mnemonic["dates"]))).astype(bool)

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
                tf_cond = [((mnemonic["dates"].data >= times[0]) & (mnemonic["dates"].data <= times[1])) for times in cond.time_pairs]

                if len(tf_cond) > 1:
                    # If there are multiple blocks of good time pairs, combine them
                    # into a 2D array (rather than list)
                    tf_2d = np.zeros((len(tf_cond), len(tf_cond[1]))).astype(bool)
                    for index in range(len(tf_cond)):
                        tf_2d[index, :] = tf_cond[index]

                    # Flatten the 2D boolean array. If the mnemonic's time falls within any of
                    # the good time pairs, it should be True here
                    tf_flat = np.any(tf_2d, axis=0)
                elif len(tf_cond) == 1:
                    # If there is only one block of good times, then no need to create
                    # a 2D array and flatten
                    tf_flat = np.array(tf_cond)
                else:
                    raise ValueError(f"tf_cond has a length of {len(tf_cond)}, which is not expected.")

                # Create a 2D boolean matrix that will hold the T/F values for all conditions
                tf_matrix[i, :] = tf_flat

        # Finally, if the mnemonic's time falls within a good time block for all of the
        # conditions, then it is considered good.
        tf = np.all(tf_matrix, axis=0)

        # Extract the good data and save it in an array
        good_data = Table()
        good_data["dates"] = mnemonic["dates"][tf]
        good_data["euvalues"] = mnemonic["euvalues"][tf]
        self.extracted_data = good_data

        # We need to keep data from distinct blocks of time separate, because we may
        # need to calculate statistics for each good time block separately. Use tf to
        # find blocks. Anywhere an F falls between some T's, we have a separate block.
        # Save tuples of (start_time, end_time) for blocks.
        # Save those in self.block_indexes below.

        # Add a False 0th element
        tf_plus_false = np.insert(tf, 0, False)

        # Now we need to find the indexes where the array switches from False to True.
        # These will be the starting indexes of the blocks. (Remember to subtract 1 in
        # order to account for the added False element)
        switches = tf_plus_false.astype(int)[0:-1] - tf.astype(int)
        switch_to_true = np.where(switches == -1)[0]
        switch_to_false = np.where(switches == 1)[0]

        # These indexes apply to the original data. Once we extract the good
        # data using tf, we now need to adjust these indexes so that they
        # apply to the extracted data.
        filtered_indexes = []
        for i in range(len(switch_to_true)):
            if i == 0:
                diff = switch_to_true[i]
            else:
                diff = switch_to_true[i] - switch_to_false[i - 1]
            switch_to_true -= diff
            switch_to_false -= diff
            filtered_indexes.append(switch_to_true[i])
        self.block_indexes = filtered_indexes

        # Add the index of the final element
        self.block_indexes.append(len(good_data))

    def get_interval(self, time):
        """Returns time interval if "time" is in between starting and
        ending times

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

        # Check every condition
        for cond in self.time_pairs:
            # Check every time pair in condition
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

    def state(self, time):
        """Checks whether condition is true or false at a given time.
        Returns state of the condition at a given time
            if state(given time)==True -> condition is true
            if state(given time)==False -> condition is false
        Checks condition for every sub condition in condition set

        Parameters
        ----------
        time : float
            Input time for condition query

        Returns
        -------
        state : bool
            True/False statement whether the condition applies or not
        """
        state = self.__state

        for cond in self.time_pairs:

            if self.__check_subcondition(cond, time):
                state = True
            else:
                state = False
                break

        return state

    def __check_subcondition(self, cond, time):
        """Check if the given time occurs within the time pairs
        that are collected within the given condition.
        """
        # If there are no values available
        if cond[0][0] == 0:
            return False

        for time_pair in cond:
            # If just a positive time is available, return True
            if (time_pair[1] == 0) and (time > time_pair[0]):
                return True

            # If given time occurs between a time pair, return True
            elif (time_pair[0]) <= time and (time < time_pair[1]):
                return True

            else:
                pass


class relation_test():
    """Class for comparing data points to a threshold value with some relation
    """
    def __init__(self, mnemonic, rel, value):
        """Initialize parameters. For example, if you have mnemonic data and
        you want to know where the data have values > 0.25, then ```rel```
        should be '>' and value should be 0.25.

        Parameters
        ----------
        mnemonic : jwql.edb.engineering_database.EdbMnemonic
            Object containing time/value data for mnemonic of interest

        rel : str
            Relation between the mnemonic data and ```value```
            (e.g. "=", ">")

        value : float
            Threshold value for good data.
        """
        self.time_pairs = []
        self.mnemonic = mnemonic
        self.value = value

        if rel == "=":
            rel = "=="
        self.rel = rel

        self.time_pairs = self.cond_true_time()

    def cond_true_time(self):
        """Find all times where all conditions are true

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

        good_time_values = self.mnemonic["dates"][good_points]
        bad_time_values = self.mnemonic["dates"][bad_points]

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
                # All values are bad.
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
        # in order to get the index counters correct below.
        if all_vals[0]:
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
            if i < (len(change_indexes) - 1):
                good_blocks.append((all_times[strt], all_times[change_indexes[i + 1] - 1]))
            else:
                good_blocks.append((all_times[strt], all_times[-1]))

        return good_blocks


if __name__ == '__main__':
    pass
