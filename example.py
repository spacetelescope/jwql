#! /usr/bin/env python
"""This is the module docstring.

The module docstring should have a one line description (as above) as
well as a more detailed description in a paragraph below the one line
description (i.e. this).  Module dosctring lines should be limited to
72 characters.  Monospace font can be achived with ``two single
forward-apostrophes``.  The description should provided a detailed
overview of the purpose of the module (what does it do) and how it
acheieves this purpose (how does it do it).

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
import os
import sys

from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import scipy
from sqlalchemy import Float, Integer, String


def my_main_function(path, filter):
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

    print('Using {} as an input file'.format(path))
    an_int = 1
    a_float = 3.14
    a_bool = True
    a_list = ['Dog', 'Cat', 'Turtle', False, 7]
    a_tuple = ('Dog', 'Cat', 'Turtle', False, 7)
    a_dict = {'key1': 'value1', 'key2': 'value2'}
    an_obj = object()

    result = some_other_function(an_int, a_float, a_bool, a_list, a_tuple, a_dict, an_obj)

    print(result)


def parse_args():
    """Parse command line arguments. Returns ``args`` object.

    Returns
    -------
    args : obj
        An argparse object containing all of the arguments
    """

    # Create help strings
    path_help = 'The path to the input file.'
    filter_help = 'The filter to process (e.g. "F606W").'

    # Add arguments
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()

    return args


def some_other_function(an_int, a_float, a_bool, a_list, a_tuple, a_dict, an_obj):
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

    pass


if __name__ == '__main__':

    args = parse_args()

    my_main_function(args.path, args.filter)
