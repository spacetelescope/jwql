#! /usr/bin/env python

""" Protect_module wrapper for the ``jwql`` automation platform.

This module provides a decorator to protect against the execution of multiple instances of a module.
Intended for when only ONE instance of a module should run at any given time.
Using this decorator, When a module is run, a Lock file is written.  The Lock file is removed upon completion of the module.
If there is already a lock file created for that module, the decorator will exit before running module specific code.

The file will also contain the process id for reference, in case a lock file exists and
the user does not think it should (i.e. module exited unexpectedly without proper closure)

This decorator is designed for use with JWQL Monitors and Generate functions.
It should decorate a function called "protected_code" which contains the main functionality where locking is required.


Authors
-------

    - Bradley Sappington

Use
---

    To protect a module to ensure it is not run multiple times
    ::

        import os
        from jwql.utils.protect_module import lock_module

        @lock_module
        def protected_code():
            # Protected code ensures only 1 instance of module will run at any given time

            # Example code normally in __name == '__main__' check
            initialize_code()
            my_main_function()
            logging_code()
            ...

        if __name__ == '__main__':
            protected_code()


Dependencies
------------

    None

References
----------

    None
"""
import inspect
import getpass
import os
import smtplib
import socket

from email.mime.text import MIMEText
from functools import wraps
from psutil import pid_exists

_PID_LOCKFILE_KEY = "Process Id = "


def _clean_lock_file(filename, module):
    locked = True
    try:
        pid = _retreive_pid_from_lock_file(filename)
        notify_str = ""
        if not pid_exists(pid):
            # if PID associated with the lock file is no longer running, then lock file should not exist, delete it.
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    notify_str = (f"DELETED FILE `{filename}`\nThis file's associated PID was no longer running.\n\n"
                                  f"This implies the previous instance of {module} may not have completed successfully.\n\n"
                                  f"New instance starting now.")
                    locked = False
                except Exception as e:
                    notify_str = f"Exception {e} \n {type(e).__name__}\n{e.args}\n\n"
                    notify_str = notify_str + filename + " delete failed, Please Manually Delete"
        return notify_str, locked
    except SyntaxError as e:
        return str(e), locked


def _retreive_pid_from_lock_file(filename):
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
            if _PID_LOCKFILE_KEY in line:
                number_index = line.index(_PID_LOCKFILE_KEY) + len(_PID_LOCKFILE_KEY)
                number = line[number_index:].strip()
                return int(number)

    raise SyntaxError(f"No PID found in {filename} - Please manually investigate and delete if appropriate")


def _send_notification(message):
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
    message['Subject'] = f'JWQL ALERT FOR LOCK_MODULE ON {hostname}'
    message['From'] = deliverer
    message['To'] = 'bsappington@stsci.edu'  # SAPP TODO - CHANGE TO JWQL@stsci.edu after testing

    s = smtplib.SMTP('smtp.stsci.edu')
    s.send_message(message)
    s.quit()


def lock_module(func):
    """Decorator to prevent more than 1 instance of a module.

    This function can be used as a decorator to create lock files on python
    modules where we only want one instance running at any given time.
    More info at top of module

    Parameters
    ----------
    func : func
        The function to decorate.

    Returns
    -------
    wrapped : func
        The wrapped function.
    """

    @wraps(func)
    def wrapped(*args, **kwargs):

        # Get the module name of the calling method
        existing_lock = False
        notify_str = ""
        frame = inspect.stack()[1]
        mod = inspect.getmodule(frame[0])
        module = mod.__file__

        # remove python suffix if it exists, then append to make testing work properly for instances where .py may not exist
        module_lock = module.replace('.py', '.lock')

        if os.path.exists(module_lock):
            notify_str, existing_lock = _clean_lock_file(module_lock, module)
        if not existing_lock:
            if notify_str:
                _send_notification(notify_str)
                notify_str = ""

            try:
                with open(module_lock, "w") as lock_file:
                    lock_file.write(f"{_PID_LOCKFILE_KEY}{os.getpid()}\n")
                return func(*args, **kwargs)
            finally:
                try:
                    os.remove(module_lock)
                except Exception as e:
                    notify_str = f"Exception {e} \n {type(e).__name__}\n{e.args}\n"
                    notify_str = notify_str + module_lock + " delete failed, please investigate cause"
        if len(notify_str):
            _send_notification(notify_str)
    return wrapped
