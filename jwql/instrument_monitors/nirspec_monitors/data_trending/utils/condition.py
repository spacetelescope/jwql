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


class condition:
    """Class to hold several subconditions"""

    #contains list of representative time pairs for each subcondition
    cond_time_pairs = []
    #state of the condition
    __state = False

    #initializes condition through condition set
    def __init__(self, cond_set):
        """Initialize object with set of conditions
        Parameters
        ----------
        cond_set : list
            list contains subconditions objects
        """
        self.cond_set = cond_set

    #destructor -> take care that all time_pairs are deleted!
    def __del__(self):
        """Delete object - destructor method"""
        del self.cond_time_pairs[:]

    #prints all stored time pairs (for developement only)
    def print_times(self):
        """Print conditions time pairs on command line (developement)"""
        print('Available time pairs:')
        for times in self.cond_time_pairs:
            print('list: '+str(times))

    #returns a interval if time is anywhere in between
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

        #do for every condition
        for cond in self.cond_time_pairs:
            #do for every time pair in condition
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


    #generates time pairs out of start and end times
    def generate_time_pairs(start_times, end_times):
        """Forms time pairs out of start times and end times
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
        """
        #internal use only
        time_pair: float = []

        #when the conditons doesn´t apply anyway
        if not start_times:
            time_pair.append((0,0))

        #check if the condition indicates an open time range
        elif not end_times:
            time_pair.append((start_times[0], 0))

        #generate time pairs
        #for each start time a higher or equal end time is searched for
        #these times form am touple which is appended to  time_pair : list
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


    #returns state of the condition at a given time
    #if state(given time)==True -> condition is true
    #if state(given time)==False -> condition is false
    def state(self, time):
        """Checks whether condition is true of false at a given time
        Parameters
        ----------
        time : float
            input time for condition query
        Return
        ------
        state : bool
            True/False statement whether the condition applies or not
        """
        #checks condition for every sub condition in condition set (subconditions)

        state = self.__state

        for cond in self.cond_time_pairs:

            if self.__check_subcondition(cond, time):
                state = True
            else:
                state = False
                break

        return state


    def __check_subcondition(self, cond, time):

        #if there are no values availlable
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


class equal(condition):
    """Class to hold single "is equal" subcondition"""

    stringval = True

    #add attributes to function - start function "cond_time_pairs()"
    def __init__(self, mnemonic, value, stringval=True):
        """Initializes subconditon
        Parameters
        ----------
        mnemonic : astropy table
            includes mnemomic engineering data and corresponding primary time
        value : str
            coparison value for equal statement
        """
        self.mnemonic = mnemonic
        self.value = value
        self.stringval = stringval
        condition.cond_time_pairs.append((self.cond_true_time()))


    #generates a list of time-touples (start_time, end_time) that mark the beginning and end of
    #wheather the condition is true or not
    def cond_true_time(self):
        """Filters all values that are equal to a given comparison value
        if equal: Primary time -> temp_start
        if not equal: Primary time -> temp_end
        Return
        ------
        time_p : list
            list of touples with start and end time
        """
        temp_start = []
        temp_end = []

        for key in self.mnemonic:

            #find all times whoses Raw values equal the given value
            if self.stringval:
                if key['value'] == self.value:
                    temp_start.append(key["time"])

                #find all end values
                else:
                    temp_end.append(key["time"])
            else:
                # just another option to compare float values
                if float(key['value']) == self.value:
                    temp_start.append(key["time"])

                #find all end values
                else:
                    temp_end.append(key["time"])

        time_p = condition.generate_time_pairs(temp_start, temp_end)
        return time_p

class unequal(condition):
    """Class to hold single "is unequal" subcondition"""

    #add attributes to function - start function "cond_time_pairs()"
    def __init__(self, mnemonic, value):
        """Initializes subconditon
        Parameters
        ----------
        mnemonic : astropy table
            includes mnemomic engineering data and corresponding primary time
        value : str
            coparison value for equal statement
        """
        self.mnemonic = mnemonic
        self.value = value
        condition.cond_time_pairs.append((self.cond_true_time()))


    #generates a list of time-touples (start_time, end_time) that mark the beginning and end of
    #wheather the condition is true or not
    def cond_true_time(self):
        """Filters all values that are equal to a given comparison value
        if equal: Primary time -> temp_start
        if not equal: Primary time -> temp_end
        Return
        ------
        time_p : list
            list of touples with start and end time
        """
        temp_start = []
        temp_end = []

        for key in self.mnemonic:

            #find all times whoses Raw values equal the given value
            if key['value'] != self.value:
                temp_start.append(key["time"])

            #find all end values
            else:
                temp_end.append(key["time"])

        time_p = condition.generate_time_pairs(temp_start, temp_end)
        return time_p

class greater(condition):
    """Class to hold single "greater than" subcondition"""

    #add attributes to function - start function "cond_time_pairs()"
    def __init__(self, mnemonic, value):
        """Initializes subconditon
        Parameters
        ----------
        mnemonic : astropy table
            includes mnemomic engineering data and corresponding primary time
        value : str
            coparison value for equal statement
        """
        self.mnemonic= mnemonic
        self.value=value
        condition.cond_time_pairs.append((self.cond_true_time()))

    def cond_true_time(self):
        """Filters all values that are greater than a given comparison value
        if equal: Primary time -> temp_start
        if not equal: Primary time -> temp_end
        Return
        ------
        time_p : list
            list of touples with start and end time
        """
        temp_start: float = []
        temp_end: float = []

        for key in self.mnemonic:

            #find all times whose Raw values are grater than the given value
            if float(key['value']) > self.value:
                temp_start.append(key["time"])

            #find all end values
            else:
                temp_end.append(key["time"])

        time_p = condition.generate_time_pairs(temp_start, temp_end)
        return time_p


class smaller(condition):
    """Class to hold single "greater than" subcondition"""

    #add attributes to function - start function "cond_time_pairs()"
    def __init__(self, mnemonic, value):
        """Initializes subconditon
        Parameters
        ----------
        mnemonic : astropy table
            includes mnemomic engineering data and corresponding primary time
        value : str
            coparison value for equal statement
        """
        self.mnemonic=mnemonic
        self.value=value
        condition.cond_time_pairs.append((self.cond_true_time()))

    def cond_true_time(self):
        """Filters all values that are greater than a given comparison value
        if equal: Primary time -> temp_start
        if not equal: Primary time -> temp_end
        Return
        ------
        time_p : list
            list of touples with start and end time
        """
        temp_start: float = []
        temp_end: float = []

        for key in self.mnemonic:

            #find all times whose Raw values are grater than the given value
            if float(key['value']) < self.value:
                temp_start.append(key["time"])

            #find all end values
            else:
                temp_end.append(key["time"])

        time_p = condition.generate_time_pairs(temp_start, temp_end)
        return time_p


if __name__ =='__main__':
    pass
