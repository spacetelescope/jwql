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

import os
import inspect
from functools import wraps


# This key is defined here because it is utilized in other modules
PID_LOCKFILE_KEY = "Process Id = "


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
        frame = inspect.stack()[1]
        mod = inspect.getmodule(frame[0])
        module = mod.__file__

        # remove python suffix if it exists, then append to make testing work properly for instances where .py may not exist
        module_lock = module.replace('.py', '.lock')

        if os.path.exists(module_lock):
            indent = " " * 4
            print(indent + "ERROR!! Instance of protected module already running for:")
            print(indent + module)
            print(indent + f"Check PID in {module_lock} and verify process is still running")
            print(indent + "If logged PID is not currently running, delete lock file and run again")
        else:
            try:
                with open(module_lock, "w") as lock_file:
                    lock_file.write(f"{PID_LOCKFILE_KEY}{os.getpid()}\n")
                return func(*args, **kwargs)
            finally:
                try:
                    os.remove(module_lock)
                except Exception as e:
                    print(e, type(e).__name__, e.args)
                    print(module_lock + ' delete failed, Please Manually Delete')
                    pass
    return wrapped
