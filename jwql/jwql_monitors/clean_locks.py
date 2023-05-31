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
import argparse
import glob
import os

from jwql.utils.protect_module import PID_LOCKFILE_KEY
from psutil import pid_exists


def clean_lock_file(filename):
    try:
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
    lock_files = glob.glob(search_path + "/*.lock")
    return lock_files


def parse_args():
    """ Parse command line arguments.

    Parameters:

    Returns:
        arguments: argparse.Namespace object
            An object containing all of the added arguments.

    Outputs:
        Nothing
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
    # Lock file format is established in `jwql/utils/protect_module.py::lock_module`
    with open(filename, 'r') as file:
        for line in file:
            if PID_LOCKFILE_KEY in line:
                number_index = line.index(PID_LOCKFILE_KEY) + len(PID_LOCKFILE_KEY)
                number = line[number_index:].strip()
                return int(number)

    raise SyntaxError(f"No PID found in {filename} - Please manually investigate and delete if appropriate")


if __name__ == '__main__':
    email_data = "The JWQL project CLEAN_LOCKS.PY has recently run and performed actions that you should be aware of:\n"
    args = parse_args()
    lock_files = get_all_lock_files(args.p)

    for file in lock_files:
        notify_str = clean_lock_file(file)
        if len(notify_str):
            email_data = email_data + notify_str + "\n"

    # Email all lock files that were deleted
    # SAPP TODO - create email to send out!
    print("EMAIL THIS: ")
    print(email_data)

    # SAPP TODO - implement this
"""
        deliverer = '{}@stsci.edu'.format(user)

        message = MIMEText(success_message)
        message['Subject'] = 'JWQL ACTION FROM `CLEAN_LOCKS` SCRIPT'
        message['From'] = deliverer
        message['To'] = 'redcat@stsci.edu'
        message['CC'] = deliverer

        s = smtplib.SMTP('smtp.stsci.edu')
        s.send_message(message)
        s.quit()
    """
