#! /usr/bin/env python

"""
This module is intended to be a template to aid in creating new
monitoring scripts and to demonstrate how to format them to fully
utilize the ``jwql`` framework.

Each monitoring script must be executable from the command line (i.e.
have a ``if '__name__' == '__main__' section), as well as a "main"
function that calls all other functions, methods, or modules (i.e.
the entirety of the code is executed within the scope of the main
function).

Users may utilize the ``jwql`` framework functions for logging,
setting permissions, parsing filenames, etc. (See related ``import``s).

Authors
-------

    - Catherine Martlin

Use
---

    This module can be executed from the command line:
    ::

        python monitor_template.py

    Alternatively, it can be called from a python environment via the
    following import statements:
    ::

      from monitor_template import main_monitor_function
      from monitor_template import secondary_function

Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``utils`` directory.

Notes
-----

    Any monitoring script written for ``jwql`` must adhere to the
    ``jwql`` style guide located at:
    https://github.com/spacetelescope/jwql/blob/master/style_guide/style_guide.md
"""

import os
import logging

# Functions for logging
from jwql.logging.logging_functions import configure_logging
from jwql.logging.logging_functions import log_info
from jwql.logging.logging_functions import log_fail

# Function for setting permissions of files/directories
from jwql.permissions.permissions import set_permissions

# Function for parsing filenames
from jwql.utils.utils import filename_parser

# Objects for hard-coded information
from jwql.utils.utils import get_config
from jwql.utils.utils import JWST_INSTRUMENTS

@log_fail
@log_info
def main_monitor_template():
    """ The main function of the module."""

    # Example of logging
    logging.info(" ")
    logging.info(" ")
    logging.info("Beginning the script run: ")

    # Example of locating a dataset in filesystem


    # Example of querying for a dataset via MAST API


    # Example of saving a file and setting permissions


    # Example of parsing a filename


    # Perform any other necessary code
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

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    # Call the main function
    main_monitor_function()
