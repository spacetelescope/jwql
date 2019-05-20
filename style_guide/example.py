#! /usr/bin/env python
"""This is the module docstring.

The module docstring should have a one line description (as above) as
well as a more detailed description in a paragraph below the one line
description (i.e. this).  Module dosctring lines should be limited to
72 characters.  Monospace font can be achived with ``two single
forward-apostrophes``.  The description should provided a detailed
overview of the purpose of the module (what does it do) and how it
achieves this purpose (how does it do it).

Authors
-------

    - Matthew Bourque

Use
---

    This module can be executed via the command line as such:

    ::
        python example.py [path] [-f|--filter filter]

    Required arguments:

    ``path`` - The path to the input file

    Optional arguments:

    ``-f|--filter`` - The filter to process.  if not provided, the
        defult value is "F606W".

Dependencies
------------

    Here is where any external dependencies can be listed or described.
    For example:

    The user must have a configuration file named ``config.yaml``
    placed in the current working directory.

References
----------

    Here is where any references to external sources related to the
    code can be listed or described.  For example:

    Code adopted from IDL routine written by Hilbert et al., 2009.

Notes
-----

    Here is where any additional notes (that are beyond the scope of the
    description) can be described.
"""

import argparse
import glob
import logging
import os
import sys
from typing import List, Union, Tuple, Optional, Any, Dict

from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import scipy
from sqlalchemy import Float, Integer, String

from jwql.utils.logging_functions import configure_logging, log_info, log_fail, log_timing


# Global variables should be avoided, but if used should be named with
# all-caps
A_GLOBAL_VARIABLE = 'foo' # type: str


@log_fail
@log_info
def my_main_function(path: str, filter: str) -> None:
    """The main function of the ``example`` module.

    This function performs the main tasks of the module.  See module
    docstrings for further details.

    Parameters
    ----------
    path : str
        The path to the input file.
    filter : str
        The filter to process (e.g. "F606W").
    """

    logging.info('Using {} as an input file'.format(path))

    an_int = 1 # type: int
    a_float = 3.14 # type: float
    a_bool = True # type: bool
    a_list = ['Dog', 'Cat', 'Turtle', False, 7] # type: List[Union[str, bool, int]]
    a_tuple = ('Dog', 'Cat', 'Turtle', False, 7) # type: Tuple[str, str, str, bool, int]
    a_dict = {'key1': 'value1', 'key2': 'value2'} # type: Dict[str, str]
    an_obj = object() # type: object

    result = some_other_function(an_int, a_float, a_bool, a_list, a_tuple, a_dict, an_obj) # type: Optional[int]

    logging.info(result)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments. Returns ``args`` object.

    Returns
    -------
    args : obj
        An argparse object containing all of the arguments
    """

    # Create help strings
    path_help = 'The path to the input file.' # type: str
    filter_help = 'The filter to process (e.g. "F606W").' # type: str

    # Add arguments
    parser = argparse.ArgumentParser() # type: argparse.ArgumentParser
    parser.add_argument('path',
                        type=str,
                        default=os.getcwd(),
                        help=path_help)
    parser.add_argument('-f --filter',
                        dest='filter',
                        type=str,
                        required=False,
                        default='F606W',
                        help=filter_help)

    # Parse args
    args = parser.parse_args() # type: argparse.Namespace

    return args


@log_timing
def some_other_function(an_int: int, a_float: float, a_bool: bool, a_list: List[Any],
                        a_tuple: Tuple[Any], a_dict: Dict[Any, Any], an_obj: object) -> int:
    """This function just does a bunch of nonsense.

    But it serves as a decent example of some things.

    Parameters
    ----------
    an_int : int
        Who knows what we will use this integer for.
    a_bool : bool
        Who knows what we will use this boolean for.
    a_float: float
        Who knows what we will use this float for.
    a_list : list
        Who knows what we will use this list for.
    a_tuple : tuple
        Who knows what we will use this tuple for.
    a_dict : dict
        Who knows what we will use this dictionary for.
    an_obj : obj
        Who knows what we will use this object for.

    Returns
    -------
    results : int
        The result of the function.
    """

    # File I/O should be handeled with 'with open' when possible
    with open('my_file', 'w') as f:
        f.write('My favorite integer is {}'.format(an_int))

    # Operators should be separated by spaces
    logging.info(a_float + a_float)

    return an_int


if __name__ == '__main__':

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    args = parse_args() # type: argparse.Namespace

    my_main_function(args.path, args.filter)
