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

    This script is intended to be run as an hourly cronjob as protection for generate_preview_images.py

    ::

        python clean_locks.py
"""
import glob
import os

from psutil import pid_exists

# SAPP TODO - MAKE NOTE TO add psutil to env in dev/test/prod
# SAPP TODO - Consider making LOCK_FILE_PID_KEY in protect_module.py to keep this method safe if there is ever a change to "Process Id = ".


def clean_lock_file(filename):
    try:
        pid = retreive_pid_from_lock_file(filename)
        if not pid_exists(pid):
            # if PID associated with the lock file is no longer running, then lock file should not exist, delete it.
            if os.path.exists(filename):
                os.remove(filename)
                print(f"File '{filename}' deleted successfully.")  # SAPP TODO -DEL THIS
                return f"File '{filename}' was never deleted and associated PID no longer running, deleted successfully."
            else:
                print(f"File '{filename}' does not exist.")  # SAPP TODO -DEL THIS
    except SyntaxError as e:
        return e


def get_all_lock_files(search_path):
    if search_path is None:
        search_path = "."

    lock_files = glob.glob(search_path + "/*.lock")
    return lock_files


def retreive_pid_from_lock_file(filename):
    # Lock file format is established in `jwql/utils/protect_module.py::lock_module`

    with open(filename, 'r') as file:
        for line in file:
            if "Process Id = " in line:
                number_index = line.index("Process Id = ") + len("Process Id = ")
                number = line[number_index:].strip()
                print(f"YES PID FOUND IN {filename}!!!!")  # SAPP TODO -DEL THIS
                return int(number)

    print(f"NO PID FOUND IN {filename}")  # SAPP TODO -DEL THIS
    raise SyntaxError(f"No PID found in {filename}")


if __name__ == '__main__':
    email_data = []

    lock_files = get_all_lock_files()

    for file in lock_files:
        notify_str = clean_lock_file(file)
        if len(notify_str):
            email_data.append(notify_str)

    # Email all lock files that were deleted
    # SAPP TODO - create email to send out!
    print("EMAIL THIS: ")
    for line in email_data:
        print(line)
