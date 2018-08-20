#! /usr/bin/env python

"""
This module is meant as a monitor template to aid in creating new
monitor scripts and to demonstrate how to format them and use
logging within them.

Authors
-------

    - Catherine Martlin, 2018

Use
---

    This module is meant as a monitor template. For modules
    that you may run from the command line you have the 
    following provided in this section: 

    This module can be executedfrom the command line: 
    ::

        python monitor_template.py

    Alternatively, it can be called from scripts with the following
    import statements:
    ::

      from monitor_template import main_monitor_template
      from monitor_template import second_function

    Also be sure to include required arguments, for example: 

    Required arguments (in a ``config.json`` file):
    ``outputs`` - The path to the output files needs to be in a
                ``config.json`` file in the ``utils`` directory.

Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``utils`` directory.

Notes
-----

    You will likely have more importants than this basic template. 
    Be sure to follow the imports organization rules. 
"""
import os
import logging

from jwql.logging.logging_functions import configure_logging
from jwql.logging.logging_functions import log_info
from jwql.logging.logging_functions import log_fail

@log_fail
@log_info
def main_monitor_template():
    """ This is your main function"""

    # Begin logging: 
    logging.info(" ")
    logging.info(" ")
    logging.info("Beginning the script run: ")

    # Here is where you place your functions:
    well_named_variable = "Function does something."
    result_of_second_function = second_function(well_named_variable)

def second_function(input_value):
    """ This is your axiliary function; you may have many of these."""

    # Begin logging: 
    logging.info(" ")
    logging.info("The auxiliary function has started running.")

    # Example function: 
    well_named_input = input_value
    useful_result = input_value + " The other function did something, too. "

    logging.info("The auxiliary function is returning: ")
    logging.info(useful_result)
    logging.info(" ")

    return useful_result

if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    main_monitor_template()
