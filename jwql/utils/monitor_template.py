#! /usr/bin/env python

"""
This module is intended to be a template to aid in creating new
monitoring scripts and to demonstrate how to format them to fully
utilize the ``jwql`` framework.

Each monitoring script must be executable from the command line (i.e.
have a ``if '__name__' == '__main__' section), as well as have a "main"
function that calls all other functions, methods, or modules (i.e.
the entirety of the code is executed within the scope of the main
function), as shown in this example.

Users may utilize the ``jwql`` framework functions for logging,
setting permissions, parsing filenames, etc. (See related ``import``s).

Authors
-------

    - Catherine Martlin
    - Matthew Bourque

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
    https://github.com/spacetelescope/jwql/blob/master/style_guide/README.md
"""

import os
import logging

from astroquery.mast import Mast
from jwst import datamodels
from bokeh.charts import Donut
from bokeh.embed import components

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
from jwql.utils.constants import JWST_DATAPRODUCTS, JWST_INSTRUMENT_NAMES


@log_fail
@log_info
def monitor_template_main():
    """ The main function of the ``monitor_template`` module."""

    # Example of logging
    my_variable = 'foo'
    logging.info('Some useful information: {}'.format(my_variable))

    # Example of querying for a dataset via MAST API
    service = "Mast.Jwst.Filtered.Niriss"
    params = {"columns": "filename",
              "filters": [{"paramName": "filter",
                          "values": ['F430M']}]}
    response = Mast.service_request_async(service, params)
    result = response[0].json()['data']
    filename_of_interest = result[0]['filename']  # jw00304002001_02102_00001_nis_uncal.fits

    # Example of parsing a filename
    filename_dict = filename_parser(filename_of_interest)
    # Contents of filename_dict:
    #     {'program_id': '00304',
    #      'observation': '002',
    #      'visit': '001',
    #      'visit_group': '02',
    #      'parallel_seq_id': '1',
    #      'activity': '02',
    #      'exposure_id': '00001',
    #      'detector': 'nis',
    #      'suffix': 'uncal'}

    # Example of locating a dataset in the filesystem
    filesystem = get_config()['filesystem']
    dataset = os.path.join(filesystem, 'jw{}'.format(filename_dict['program_id']),
                           filename_of_interest)

    # Example of reading in dataset using jwst.datamodels
    im = datamodels.open(dataset)
    # Now have access to:
    #     im.data  # Data array
    #     im.err  # ERR array
    #     im.meta  # Metadata such as header keywords

    # Example of saving a file and setting permissions
    im.save('some_filename.fits')
    set_permissions('some_filename.fits')

    # Example of creating and exporting a Bokeh plot
    plt = Donut(im.data, plot_width=600, plot_height=600)
    plt.sizing_mode = 'stretch_both'  # Necessary for responsive sizing on web app
    script, div = components(plt)

    plot_output_dir = get_config()['outputs']
    div_outfile = os.path.join(plot_output_dir, 'monitor_name',
                               filename_of_interest + "_component.html")
    script_outfile = os.path.join(plot_output_dir, 'monitor_name',
                                  filename_of_interest + "_component.js")

    for outfile, component in zip([div_outfile, script_outfile], [div, script]):
        with open(outfile, 'w') as f:
            f.write(component)
            f.close()
        set_permissions(outfile)

    # Perform any other necessary code
    well_named_variable = "Function does something."
    result_of_second_function = second_function(well_named_variable)


def second_function(input_value):
    """ This is your axiliary function; you may have many of these.

    Parameters
    ----------
    input_value : str
        Some value to modify in the function.

    Returns
    -------
    useful_result : str
        The result of modifying the input value.
    """

    # Begin logging:
    logging.info(" ")
    logging.info("The auxiliary function has started running.")

    # Example function:
    useful_result = input_value + " The other function did something, too."

    logging.info("The auxiliary function is returning: ")
    logging.info(useful_result)
    logging.info(" ")

    return useful_result


if __name__ == '__main__':

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    # Call the main function
    monitor_template_main()
