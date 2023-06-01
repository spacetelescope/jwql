#! /usr/bin/env python

"""Evaluate and clean all *.lock files in the current directory.

This script is used as protection for scripts using the `jwql/utils/protect_module.py::lock_module` decorator

There are infrequent instances where the MODULE_NAME.lock file will linger despite the process no longer running.
This script will
    Cycle through all *.lock files generated from the lock_module decorator
    Retreive their associated PIDs
    Delete any lock file who's associated PID is no longer running.
    Email confirmation of any files that were deleted

Authors
-------

    - Bradley Sappington


Use
---

    This script is intended to be run as a frequent cronjob as protection for generate_preview_images.py

    ::

        python clean_locks.py
        or
        python clean_locks.py -p "/directory/to/check"
"""
# SAPP TODO - NO LONGER NEED THIS MODULE!

import argparse
import getpass
import glob
import os
import smtplib
import socket

from email.mime.text import MIMEText
from jwql.utils import permissions
from jwql.utils.protect_module import PID_LOCKFILE_KEY
from psutil import pid_exists


def clean_lock_file(filename):
    try:
        permissions.set_permissions(filename)
        pid = retreive_pid_from_lock_file(filename)
        if not pid_exists(pid):
            # if PID associated with the lock file is no longer running, then lock file should not exist, delete it.
            if os.path.exists(filename):
                os.remove(filename)
                return (f"DELETED FILE `{filename}` - This file's associated PID was no longer running.\n"
                        f"This lock file would have blocked future instances of `{filename.replace('.lock', '.py')}`")
        return ""
    except SyntaxError as e:
        return str(e)


def get_all_lock_files(search_path="."):
    '''This function returns a list of all lock files in a given directory.

    Parameters
    ----------
    search_path, optional
        The directory path where the function will search for lock files. By default, it is set to the
        current directory (".") but it can be changed to any other directory path.

    Returns
    -------
        list: file paths for all files with the extension ".lock" in the search path

    '''
    lock_files = glob.glob(search_path + "/*.lock")
    return lock_files


def parse_args():
    """ Parse command line arguments.

    Parameters
    ----------
        None

    Returns
    ----------
        argparse.Namespace object: An object containing all of the added arguments.

    """
    path_help = ('Directory where you would like to search for *.lock files.'
                 ' Default is current directory')

    parser = argparse.ArgumentParser()
    parser.add_argument('-p',
                        type=str,
                        help=path_help,
                        action='store',
                        required=False,
                        default='.')

    arguments = parser.parse_args()

    return arguments


def retreive_pid_from_lock_file(filename):
    '''This function retrieves a process ID from a lock file.

    Parameters
    ----------
    filename
        The filename parameter is a string that represents the name of the lock file from which the process
        ID (PID) needs to be retrieved.

    Returns
    -------
        int: The process ID (PID)
        or
        SyntaxError: Indicating that the file should be manually investigated and deleted if appropriate.

    '''
    # Lock file format is established in `jwql/utils/protect_module.py::lock_module`
    with open(filename, 'r') as file:
        for line in file:
            if PID_LOCKFILE_KEY in line:
                number_index = line.index(PID_LOCKFILE_KEY) + len(PID_LOCKFILE_KEY)
                number = line[number_index:].strip()
                return int(number)

    raise SyntaxError(f"No PID found in {filename} - Please manually investigate and delete if appropriate")


def send_notification(message):
    '''Sends an email notification to JWQL team alerting them of script actually solving issue (or not)

    Parameters
    ----------
    message
        The message to be included in the email notification that will be sent out.

    '''

    user = getpass.getuser()
    hostname = socket.gethostname()
    deliverer = '{}@stsci.edu'.format(user)

    message = MIMEText(message)
    message['Subject'] = f'JWQL ALERT FOR `CLEAN_LOCKS` SCRIPT ON {hostname}'
    message['From'] = deliverer
    message['To'] = 'bsappington@stsci.edu'  # SAPP TODO - CHANGE TO JWQL@stsci.edu after testing

    s = smtplib.SMTP('smtp.stsci.edu')
    s.send_message(message)
    s.quit()


if __name__ == '__main__':
    email_data = "The JWQL project's CLEAN_LOCKS.PY has recently run and performed actions that you should be aware of:\n\n"
    args = parse_args()
    lock_files = get_all_lock_files(args.p)
    notify_team = False

    for file in lock_files:
        notify_str = clean_lock_file(file)
        if len(notify_str):
            notify_team = True
            email_data = email_data + notify_str + "\n"

    if notify_team:
        send_notification(email_data)
