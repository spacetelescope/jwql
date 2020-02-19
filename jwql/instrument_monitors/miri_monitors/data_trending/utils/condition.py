#! /usr/bin/env python

"""Generates conditions over one or more mnemonics

This module's purpose is to return True/False for any times by reference
of certain conditions. If for instance the condition "x>1" over a
defined period of time is needed, the module looks for all elements
where the condition applies and where it does not apply. This generates
two lists, which contain the "start" and "end" times of the condition.
A futher function combines the start- and endtimes to time-tuples
between which the condition is known as TRUE. A "state" function returns
True/False for an exact time attribute, whereby the condition is
represented in binary form.

Authors
-------

    - Daniel Kühbacher

Use
---

    This module is not intended for standalone use.

    For use in program, set condition up like below:

    import the module as follows:
    ::

        import condition as cond

    generate list with required conditions:
    ::

        con_set = [
            cond.equal(m.mnemonic('IMIR_HK_POM_LOOP'),'OFF'),
            cond.smaller(m.mnemonic('IMIR_HK_ICE_SEC_VOLT1'),1),
            cond.greater(m.mnemonic('SE_ZIMIRICEA'),0.2)]

    generate object of condition with the con_set as attribute:
    ::

        condition_object=cond.condition(con_set)

    Now the ``condition_object`` can return a ``True``/``False``
    statement whether the time given as attribut meets the conditions:
    ::
        if condition.state(float(element['Primary Time'])):
            -> True when condition for the given time applies
            -> False when condition for the given time is not applicable
"""


class condition:
    """Class to hold several subconditions"""

    # Contains list of representative time pairs for each subcondition
    condition_time_pairs = []

    # State of the condition
    __state = False

    def __init__(self, condition_set):
        """Initialize object with set of conditions

        Parameters
        ----------
        condition_set : list
            list contains subconditions objects
        """

        self.condition_set = condition_set

    def __del__(self):
        """Delete object - destructor method"""
        del self.condition_time_pairs[:]

    def _check_subcondition(self, condition, time):

        # If there are no values availlable
        if condition[0][0] == 0:
            return False

        for time_pair in condition:
            if (time_pair[1] == 0) and (time > time_pair[0]):
                return True

            elif (time_pair[0]) <= time and (time < time_pair[1]):
                return True

            else:
                pass

    def get_interval(self, time):
        """Returns time interval if available, where ``time`` is in
        between

        Parameters
        ----------
        time : float
            Given time attribute
        Returns
        -------
        time_pair : tuple
            pair of start_time and end_time where time is in between
        """

        end_time = 10000000
        start_time = 0

        for condition in self.condition_time_pairs:
            for pair in condition:
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

    def generate_time_pairs(start_times, end_times):
        """Forms time pairs out of start times and end times

        Parameters
        ----------
        start_times : list
            Contains all times where a condition applies
        end_times : list
            Contains all times where the condition does not apply

        Returns
        -------
        time_pair : list
            List of touples with start and end time
        """

        time_pair: float = []

        # When the conditons doesn´t apply anyway
        if not start_times:
            time_pair.append((0, 0))

        # Check if the condition indicates an open time range
        elif not end_times:
            time_pair.append((start_times[0], 0))

        # Generate time pairs
        # For each start time a higher or equal end time is searched for
        # these times form am touple which is appended to  time_pair : list
        else:
            time_hook = 0
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

    def print_times(self):
        """Print conditions time pairs on command line (developement)"""
        print('Available time pairs:')
        for times in self.condition_time_pairs:
            print('list: ' + str(times))

    def state(self, time):
        """Checks whether condition is true of false at a given time.

        Returns state of the condition at a given time.

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

        for condition in self.condition_time_pairs:
            if self._check_subcondition(condition, time):
                state = True
            else:
                state = False
                break

        return state


class equal(condition):
    """Class to hold single "is equal" subcondition"""

    def __init__(self, mnemonic, value):
        """Initializes subconditon

        Parameters
        ----------
        mnemonic : obj
            ``astropy.Table`` object that includes mnemomic engineering
            data and corresponding primary time
        value : str
            coparison value for equal statement
        """

        self.mnemonic = mnemonic
        self.value = value
        condition.condition_time_pairs.append((self.condition_true_time()))

    def condition_true_time(self):
        """Filters all values that are equal to a given comparison value

        Returns
        -------
        time_pairs : list
            list of tuples with start and end time
        """

        temp_start, temp_end = [], []

        for key in self.mnemonic:

            # Find all times whoses raw values equal the given value
            if key['value'] == self.value:
                temp_start.append(key['time'])

            # Find all end values
            else:
                temp_end.append(key['time'])

        time_pairs = condition.generate_time_pairs(temp_start, temp_end)

        return time_pairs


class greater(condition):
    """Class to hold single "greater than" subcondition"""

    def __init__(self, mnemonic, value):
        """Initializes subconditon

        Parameters
        ----------
        mnemonic : obj
            ``astropy.Table`` object that includes mnemomic engineering
            data and corresponding primary time
        value : str
            Coparison value for equal statement
        """

        self.mnemonic = mnemonic
        self.value = value
        condition.condition_time_pairs.append((self.condition_true_time()))

    def condition_true_time(self):
        """Filters all values that are greater than a given comparison
        value

        Returns
        -------
        time_pairs : list
            List of touples with start and end time
        """

        temp_start: float = []
        temp_end: float = []

        for key in self.mnemonic:

            # Find all times whose Raw values are grater than the given value
            if float(key['value']) > self.value:
                temp_start.append(key['time'])

            # Find all end values
            else:
                temp_end.append(key['time'])

        time_pairs = condition.generate_time_pairs(temp_start, temp_end)

        return time_pairs


class smaller(condition):
    """Class to hold single "smaller than" subcondition"""

    def __init__(self, mnemonic, value):
        """Initializes subconditon

        Parameters
        ----------
        mnemonic : obj
            ``astropy.Table`` object that includes mnemomic engineering
            data and corresponding primary time
        value : str
            Coparison value for equal statement
        """

        self.mnemonic = mnemonic
        self.value = value
        condition.condition_time_pairs.append((self.condition_true_time()))

    def condition_true_time(self):
        """Filters all values that are greater than a given comparison value

        Returns
        -------
        time_pairs : list
            List of touples with start and end time
        """

        temp_start: float = []
        temp_end: float = []

        for key in self.mnemonic:

            # Find all times whose Raw values are grater than the given value
            if float(key['value']) < self.value:
                temp_start.append(key['time'])

            # Find all end values
            else:
                temp_end.append(key['time'])

        time_pairs = condition.generate_time_pairs(temp_start, temp_end)

        return time_pairs
