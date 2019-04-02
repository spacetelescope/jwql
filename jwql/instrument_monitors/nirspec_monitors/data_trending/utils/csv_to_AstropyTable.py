#! /usr/bin/env python
"""Module for importing and sorting mnemonics

This module imports a whole set of mnemonics from a .CSV sheet and converts it
to an astropy table. In a second step the table is sorted by its mnemoncis
and for each mnemmonic another astropy table with reduced content is created.
The last step is to append the data (time and engineering value) with its
mnemonic identifier as key to a dictionary.

Authors
-------
    - Daniel Kühbacher

Use
---


Dependencies
------------
    mnemonics.py -> includes a list of mnemonics to be evaluated

References
----------

Notes
-----

"""
from astropy.table import Table
from astropy.time import Time
import warnings
import jwql.instrument_monitors.nirspec_monitors.data_trending.utils.mnemonics as mn


class mnemonics:
    """class to hold a set of mnemonics"""

    __mnemonic_dict = {}

    def __init__(self, import_path):
        """main function of this class
        Parameters
        ----------
        import_path : str
            defines file to import (csv sheet)
        """
        imported_data = self.import_CSV(import_path)
        length = len(imported_data)

        print('{} was imported - {} lines'.format(import_path, length))

        #look for every mnmonic given in mnemonicy.py
        for mnemonic_name in mn.mnemonic_set_query:
            temp = self.sort_mnemonic(mnemonic_name, imported_data)
            #append temp to dict with related mnemonic
            if temp != None:
                self.__mnemonic_dict.update({mnemonic_name:temp})
            else:
                warnings.warn("fatal error")


    def import_CSV(self, path):
        """imports csv sheet and converts it to AstropyTable
        Parameters
        ----------
        path : str
            defines path to file to import
        Return
        ------
        imported_data : AstropyTable
            container for imported data
        """
        #read data from given *CSV file
        imported_data=Table.read(path, format='ascii.basic', delimiter=',')
        return imported_data


    #returns table of single mnemonic
    def mnemonic(self, name):
        """Returns table of one single mnemonic
        Parameters
        ----------
        name : str
            name of mnemonic
        Return
        ------
        __mnemonic_dict[name] : AstropyTable
            corresponding table to mnemonic name
        """
        try:
            return self.__mnemonic_dict[name]
        except KeyError:
            print('{} not in list'.format(name))


    #looks for given mnemonic in given table
    #returns list containing astropy tables with sorted mnemonics and engineering values
    #adds useful meta data to Table
    def sort_mnemonic(self, mnemonic, table):
        """Looks for all values in table with identifier "mnemonic"
           Converts time string to mjd format
        Parameters
        ----------
        mnemonic : str
            identifies which mnemonic to look for
        table : AstropyTable
            table that stores mnemonics and data
        Return
        ------
        mnemonic_table : AstropyTable
            stores all data associated with identifier "mnemonic"
        """

        temp1: float = []
        temp2 = []

        #appends present mnemonic data to temp arrays temp1 and temp2
        for item in table:
            try:
                if item['Telemetry Mnemonic'] == mnemonic:
                    #convert time string to mjd format
                    temp = item['Secondary Time'].replace('/','-').replace(' ','T')
                    t = Time(temp, format='isot')

                    temp1.append(t.mjd)
                    temp2.append(item['EU Value'])
            except KeyError:
                warnings.warn("{} is not in mnemonic table".format(mnemonic))

        description = ('time','value')
        data = [temp1, temp2]

        #add some meta data
        if len(temp1) > 0:
            date_start = temp1[0]
            date_end = temp1[len(temp1)-1]
            info = {'start':date_start, 'end':date_end}
        else:
            info = {"n":"n"}

        #add name of mnemonic to meta data of list
        info['mnemonic'] = mnemonic
        info['len'] = len(temp1)

        #table to return
        mnemonic_table = Table(data, names = description, \
                        dtype = ('f8','str'), meta = info)
        return mnemonic_table

if __name__ =='__main__':
    pass
