
""" Logging functions for the ``jwql`` automation platform.

This module provides decorators to log the execution of modules.  Log
files are written to the ``logs/`` directory in the ``jwql`` central
storage area, named by module name and timestamp, e.g.
``monitor_filesystem/monitor_filesystem_2018-06-20-15:22:51.log``


Authors
-------

    - Catherine Martlin 2018
    - Alex Viana, 2013 (WFC3 QL Version)

Use
---

    To log the execution of a module, use:
    ::

        import os
        import logging

        from jwql.logging.logging_functions import configure_logging
        from jwql.logging.logging_functions import log_info
        from jwql.logging.logging_functions import log_fail

        @log_info
        @log_fail
        def my_main_function():
            pass

        if __name__ == '__main__':

            module = os.path.basename(__file__).replace('.py', '')
            configure_logging(module)

            my_main_function()

Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``utils`` directory.


References
----------
    This code is adopted and updated from python routine
    ``logging_functions.py`` written by Alex Viana, 2013 for the WFC3
    Quicklook automation platform.
"""

import datetime
import getpass
import importlib
import logging
import os
import pwd
import socket
import sys
import time
import traceback

from functools import wraps

from jwql.utils.permissions import set_permissions
from jwql.utils.utils import get_config, ensure_dir_exists

LOG_FILE_LOC = ''
PRODUCTION_BOOL = ''


def configure_logging(module, production_mode=True, path='./'):
    """Configure the log file with a standard logging format.

    Parameters
    ----------
    module : str
        The name of the module being logged.
    production_mode : bool
        Whether or not the output should be written to the production
        environement.
    path : str
        Where to write the log if user-supplied path; default to working dir.
    """

    # Determine log file location
    if production_mode:
        log_file = make_log_file(module)
    else:
        log_file = make_log_file(module, production_mode=False, path=path)
    global LOG_FILE_LOC
    global PRODUCTION_BOOL
    LOG_FILE_LOC = log_file
    PRODUCTION_BOOL = production_mode

    # Create the log file and set the permissions
    logging.basicConfig(filename=log_file,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S %p',
                        level=logging.INFO)
    set_permissions(log_file)


def make_log_file(module, production_mode=True, path='./'):
    """Create the log file name based on the module name.

    The name of the ``log_file`` is a combination of the name of the
    module being logged and the current datetime.

    Parameters
    ----------
    module : str
        The name of the module being logged.
    production_mode : bool
        Whether or not the output should be written to the production
        environment.
    path : str
        Where to write the log if user-supplied path; default to
        working dir.

    Returns
    -------
    log_file : str
        The full path to where the log file will be written to.
    """

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
    filename = '{0}_{1}.log'.format(module, timestamp)
    user = pwd.getpwuid(os.getuid()).pw_name

    settings = get_config()
    admin_account = settings['admin_account']
    log_path = settings['log_dir']

    if user != admin_account or not production_mode:
        module = os.path.join('dev', module)

    if production_mode:
        log_file = os.path.join(log_path, module, filename)
    else:
        log_file = os.path.join(path, filename)

    ensure_dir_exists(os.path.dirname(log_file))

    return log_file


def log_info(func):
    """Decorator to log useful system information.

    This function can be used as a decorator to log user environment
    and system information. Future packages we want to track can be
    added or removed as necessary.

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
    def wrapped(*a, **kw):

        # Log environment information
        logging.info('User: ' + getpass.getuser())
        logging.info('System: ' + socket.gethostname())
        logging.info('Python Version: ' + sys.version.replace('\n', ''))
        logging.info('Python Executable Path: ' + sys.executable)

        # Read in setup.py file to build list of required modules
        settings = get_config()
        setup_file_name = settings['setup_file']
        with open(setup_file_name) as setup:
            for line in setup:
                if line[0:8] == "REQUIRES":
                    module_required = line[12:-2]
                    module_list = module_required.split(',')

        # Clean up the module list
        module_list = [module.replace('"', '').replace("'", '').replace(' ', '') for module in module_list]
        module_list = [module.split('=')[0] for module in module_list]

        # Log common module version information
        for module in module_list:
            try:
                mod = importlib.import_module(module)
                logging.info(module + ' Version: ' + mod.__version__)
                logging.info(module + ' Path: ' + mod.__path__[0])
            except ImportError as err:
                logging.warning(err)

        # Call the function and time it
        t1_cpu = time.clock()
        t1_time = time.time()
        func(*a, **kw)
        t2_cpu = time.clock()
        t2_time = time.time()

        # Log execution time
        hours_cpu, remainder_cpu = divmod(t2_cpu - t1_cpu, 60 * 60)
        minutes_cpu, seconds_cpu = divmod(remainder_cpu, 60)
        hours_time, remainder_time = divmod(t2_time - t1_time, 60 * 60)
        minutes_time, seconds_time = divmod(remainder_time, 60)
        logging.info('Elapsed Real Time: {0:.0f}:{1:.0f}:{2:f}'.format(hours_time, minutes_time, seconds_time))
        logging.info('Elapsed CPU Time: {0:.0f}:{1:.0f}:{2:f}'.format(hours_cpu, minutes_cpu, seconds_cpu))

    return wrapped


def log_fail(func):
    """Decorator to log crashes in the decorated code.

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
    def wrapped(*a, **kw):

        try:

            # Run the function
            func(*a, **kw)
            logging.info('Completed Successfully')

        except Exception:
            logging.critical(traceback.format_exc())
            logging.critical('CRASHED')

    return wrapped
