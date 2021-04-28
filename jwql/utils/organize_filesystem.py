#! /usr/bin/env python

"""This module takes a collection of JWST FITS files and copies the
files into a MAST-data-cache-like filesystem.

The files that the module will process is provided by the
``old_filesysem`` key in the ``config.json`` file.  The files will be
copied into the directory provided by the ``filesystem`` key in the
``config.json`` file.

For example, the file
``<old_filesystem>/jw00312/jw00312002001_02102_00001_nrcb4_rateints.fits`
 will be placed in the directory ``<filesystem>/jw00312/jw00312002001/``.

Authors
-------

    - Matthew Bourque

Use
---

    This module is intended to be executed via the command line as such:
    ::

        python organize_filesystem.py
"""

import os

from jwql.utils.utils import filename_parser
from jwql.utils.utils import copy_files, get_config, ensure_dir_exists


def organize_filesystem():
    """The main function of the ``organize_filesystem`` module.  See
    module docstrings for further details.
    """

    # Walk through list of files to process
    for directory, _, files in os.walk(get_config()['old_filesystem']):

        print('Processing {}'.format(directory))

        for filename in files:

            # Parse the filename for metadata
            src = os.path.join(directory, filename)
            filename_dict = filename_parser(src)

            # Build destination path for those filenames that can be parsed
            try:
                destination_directory = os.path.join(
                    get_config()['filesystem'],
                    'jw{}'.format(filename_dict['program_id']),
                    'jw{}{}{}'.format(filename_dict['program_id'], filename_dict['observation'], filename_dict['visit']))
            except KeyError:  # Some filenames do not have a program_id/observation/visit structure
                break

            # Create parent directories if necessary
            ensure_dir_exists(destination_directory)

            # Copy the file over
            success, failed = copy_files([src], destination_directory)
            print('\tCopied {} to {}'.format(src, destination_directory))


if __name__ == '__main__':

    organize_filesystem()
