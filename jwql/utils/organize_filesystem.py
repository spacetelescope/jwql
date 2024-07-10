#! /usr/bin/env python

"""This module takes a collection of JWST FITS files and moves the
files into a MAST-data-cache-like filesystem.

The files that the module will process is provided by the
``old_filesysem`` key in the ``config.json`` file.  The files will be
moved into the directory provided by the ``filesystem`` key in the
``config.json`` file.

For example, the file
``<old_filesystem>/jw00312/jw00312002001_02102_00001_nrcb4_rateints.fits``
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
import shutil

from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, get_config, ensure_dir_exists, filename_parser

SETTINGS = get_config()


def organize_filesystem():
    """The main function of the ``organize_filesystem`` module.  See
    module docstrings for further details.
    """

    # Walk through list of files to process
    for directory, _, files in os.walk(SETTINGS['old_filesystem']):

        print('Processing {}'.format(directory))

        for filename in files:

            # Parse the filename for metadata
            src = os.path.join(directory, filename)
            filename_dict = filename_parser(src)

            # Build destination path for those filenames that can be parsed
            try:
                destination_directory = os.path.join(
                    SETTINGS['filesystem'],
                    'jw{}'.format(filename_dict['program_id']),
                    'jw{}{}{}'.format(filename_dict['program_id'], filename_dict['observation'], filename_dict['visit']))
            except KeyError:
                # Some filenames do not have a program_id/observation/visit structure
                # Files that are not recognized by filename_parser will also end up here.
                break

            # Build complete destination location
            dst = os.path.join(destination_directory, os.path.basename(src))

            # Create parent directories if necessary
            # ensure_dir_exists(destination_directory)

            # Move the file over
            # shutil.move(src, dst)
            print('\tMoved {} to {}'.format(src, dst))


def revert_filesystem():
    """Perform the opposite of ``organize_filesystem`` -- this function will move
    files from a MAST-data-cache-like organization to the previous organization.

    For example, the file
    ``<filesystem>/jw00312/jw00312002001/jw00312002001_02102_00001_nrcb4_rateints.fits`
    will be placed in the directory ``<old_filesystem>/jw00312/``.
    """

    # Walk through list of files to process
    for directory, _, files in os.walk(SETTINGS['filesystem']):

        print('Processing {}'.format(directory))

        for filename in files:

            # Parse the filename for metadata
            src = os.path.join(directory, filename)
            filename_dict = filename_parser(src)

            # Build destination path for those filenames that can be parsed
            try:
                destination_directory = os.path.join(
                    SETTINGS['old_filesystem'],
                    'jw{}'.format(filename_dict['program_id']))
            except KeyError:
                # Some filenames do not have a program_id/observation/visit structure
                # Filenames not recognized by filename_parser() will also end up here.
                break

            # Build complete destination location
            dst = os.path.join(destination_directory, os.path.basename(src))

            # Create parent directories if necessary
            # ensure_dir_exists(destination_directory)

            # Move the file over
            # shutil.move(src, dst)
            print('\tMoved {} to {}'.format(src, dst))


if __name__ == '__main__':

    organize_filesystem()
