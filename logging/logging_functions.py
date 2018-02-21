""" Logging functions for the James Webb Quicklook automation platform

Working notes: 
1) Will definitely want the same type of decorators that WFC3 QL uses - one
to track failures and one to track useful system information. Are there
any other things we will want to create a decorator for? 

2) Also which module version information will we want to track with our info 
decorator?

3) Do we want to follow the same naming convention stuff? Have the make_log_file 
function perform the same way?

4) Will we follow the same saving convention of the different directories and 
want to set up a recent directory for the most recent log file to be available 
all the time? 







Authors
-------
Catherine Martlin 2018


Use
___


Dependencies
____________


References
__________

Code will likely be adopted from python routine written by Alex Viana, 2013 
for the WFC3 Quicklook automation platform.

Notes
_____



"""

