Logging Style Guide for `jwql` Instrument Monitors
==================================================

This document serves as a style guide for adding logging to `jwql` instrument monitor software.  Any monitoring contribution to the `jwql` code repository should be checked against this guide to ensure proper usage of logging functions, and any violation of this and the style guide should be fixed before the code is committed to the `main` or `develop` branches.  Please refer to the accompanying [`example.py`](https://github.com/spacetelescope/jwql/blob/main/style_guide/example.py) script for a example code that abides by the style guide and the logging guide.


Introduction
------------

All contributions of instrument monitors to the `jwql` code repository should conform to the following logging guidelines. This is to ensure uniformity across monitoring scripts and to help allow for `jwql` maintainers to programmatically interface with log files.

The `logging_functions.py` script can be found within the `jwql` code repository underneath the `utils` directory. Users can review that code for information on how `jwql` logging works, but should be able to setup logging by following the documentation below.


Logging Set-Up
--------------

First, ensure that the monitoring script imports the following libraries:

```python
import os
import logging

from jwql.utils.logging_functions import configure_logging, log_info, log_fail, log_timing
```

Next, under the `if __name__ == '__main__'` portion of the monitoring script, add these lines of code in order to configure the logging.  This creates and initializes a corresponding log file (stored in the `jwql` central storage area):

```python
# Configure logging
module = os.path.basename(__file__).strip('.py')
configure_logging(module)
```

Lastly, wrap the `log_info` and `log_fail` decorators around the main function of the monitor:

```python
@log_fail
@log_info
def my_monitor_main():
    """The main function of the monitor"""
```


Convenience Decorators
----------------------

The `logging_functions` module also provides a convenience  decorator, `log_timing` for logging the time required to execute a given function:

```python
@log_timing
def my_function():
    """Some function"""
```


In-line Logging Use
-------------------

Users should place logging statements within the code to indicate any notable parts of the monitoring script execution.  This includes such things as:

- An external file has been accessed/written to
- A database query/insert/update has been performed
- To document the number of data products being processed/produced
- To document the begin/end points of a long process
- etc.


Example log file
----------------

The following is what a completed log file may look like:

```
03/28/2019 02:30:11 AM INFO: User: <system user>
03/28/2019 02:30:11 AM INFO: System: <server name>
03/28/2019 02:30:11 AM INFO: Python Version: 3.6.4 |Anaconda, Inc.| (default, Mar 13 2018, 01:15:57) [GCC 7.2.0]
03/28/2019 02:30:11 AM INFO: Python Executable Path: /path/to/environment/jwql/bin/python
03/28/2019 02:30:11 AM INFO: Beginning <instrument_monitor>
03/28/2019 02:30:11 AM INFO: Using 100 files for analysis
03/28/2019 02:30:11 AM INFO: Read in my_favorite.fits file
03/28/2019 02:30:11 AM INFO: astroquery.mast query returned 77 files
03/28/2019 02:30:11 AM INFO: Saved Bokeh plot to: /some/location/plot.html
03/28/2019 02:30:11 AM INFO: <instrument_monitor> completed successfully.
03/28/2019 02:30:11 AM INFO: Elapsed Real Time: 0:2:48
03/28/2019 02:30:11 AM INFO: Elapsed CPU Time: 0:1:15
03/28/2019 02:30:11 AM INFO: Completed Successfully
```
