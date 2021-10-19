#! /usr/bin/env python

"""Engineering Database Mnemonics Trending Monitor (EDB Trending Monitor)

more description here
"""




from jwql.edb import engineering_database as ed



# To query the EDB for a single mnemonic
starttime = Time('2019-01-16T00:00:00.000')
endtime = Time('2019-01-16T00:01:00.000')
mnemonic = 'IMIR_HK_ICE_SEC_VOLT4'
mnemonic_data = ed.get_mnemonic(mnemonic, starttime, endtime)

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
m_list = ['SA_ZFGOUTFOV', 'IMIR_HK_ICE_SEC_VOLT4']
q = ed.get_mnemonics(m_list, starttime, endtime)

"""
result is an ordered dictionary of EdbMnemonic objects, as shown above
q.keys()
Out[8]: odict_keys(['SA_ZFGOUTFOV', 'IMIR_HK_ICE_SEC_VOLT4'])
"""



def run():
    """
    """
    # Loop over all instruments

        # Read in a list of memonics that the instrument teams want to monitor
        #     From either a text file, or a edb_mnemonics_montior database table

        # Check the edb_mnemonics_monitor database table to see the date of the previous query
        #     As is done in other monitors

        # Query the EDB for all mnemonics for the period of time between the previous query and the current date
        # Use exsiting JWQL EDB code - as shown above

        # Loop over mnemonics

            # If the latest query retrieved enough data:

                # Figure out what, if any, kind of averaging/smoothing to do (like the 15-min/daily averaging in data_trending)
                # and apply it to the new data
                # Can probably steal some of the data trending code for this

                # Save the averaged/smoothed data and dates/times to the edb_mnemonics_monitor database
                #      Just as with other monitors

                # Re-create the plot for the mnemonic, adding the new data
                # Can probably steal some of the data trending code for this

                # Display the plot on the web app

                # Add the current date/time to the edb_menmonic_monitor database as the end time of the latest query


# Other options:
# A separate "previous query" time for each mnemonic?
# Johannes built a function to query for many mnemonics but with a single start and end time
# If no data are returned for a particular mnemonic, then skip all the updating. If data are
# returned the next time, we should still be able to update the plot without having lost any
# information. Using a single date will keep things simpler.


