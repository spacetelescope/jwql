
""" Logging functions for the James Webb Quicklook automation platform.


Authors
-------
Catherine Martlin 2018



Use
___
=======
Alex Viana, 2013 (WFC3 QL Version)
 

Use
___
Things will be written to '/grp/jwst/ins/jwql/logs/dev/<module>/<module_log_filename>'
for now. 

Once we have a live production environment and codebase we'll have those
logs sent to '/grp/jwst/ins/jwql/logs/<module>/<module_log_filename>'. 



Dependencies
____________
The user must have a configuration file named ``config.json``
placed in the current working directory.


References
__________
Code is adopted and updated from python routine logging_functions.py 
written by Alex Viana, 2013 for the WFC3 Quicklook automation platform.

Notes
_____



"""

import datetime
import getpass
import glob
import importlib
import logging
import os
import pwd
import shutil
import socket
import sys
import time
import traceback

from functools import wraps

LOG_FILE_LOC = ''
PRODUCTION_BOOL = ''


def configure_logging(module, production_mode=True, path='./'):
    """Configure the standard logging format.

    Parameters
    ----------
    module : str
        The name of the module being logged.
    production_mode : bool
        Whether or not the output should be written to the production environement.
    path : str
        Where to write the log if user-supplied path; default to working dir.
    """
    if production_mode:
        log_file = make_log_file(module)
    else:
        log_file = make_log_file(module, production_mode=False, path=path)

    global LOG_FILE_LOC
    global PRODUCTION_BOOL
    LOG_FILE_LOC = log_file
    PRODUCTION_BOOL = production_mode
    logging.basicConfig(filename=log_file,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S %p',
                        level=logging.INFO)


def make_log_file(module, production_mode=True, path='./'):
    """Create the log file name based on the module name.

    The name of the ``log_file`` is a combination of the name of the
    module being logged and the current datetime.

    Parameters
    ----------
    module : str
        The name of the module being logged.
    production_mode : bool
        Whether or not the output should be written to the production environment.
    path : str
        Where to write the log if user-supplied path; default to working dir.

    Returns
    -------
    log_file : str
        The full path to where the log file will be written to.
    """

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
    filename = '{0}_{1}.log'.format(module, timestamp)
    user = pwd.getpwuid(os.getuid()).pw_name

    #exempt_modules = []
    if user != 'jwqladmin' and module not in exempt_modules and production_mode:
        module = os.path.join('dev', module)
    
    if production_mode:
        log_file = os.path.join('/grp/jwst/ins/jwql/logs/', module, filename) # Do we not want this on the github?#
    else:
        log_file = os.path.join(path, filename)

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


        with open("../setup.py") as setup:   # When I've got the config file up, change this to not be a path.
            for line in setup:
                if line[0:8] == "REQUIRES":
                    mod_required = line[12:-2]
                    mod_list = mod_required.split(',')

        # Log common module version information
        for mod in mod_list:
            mod = mod.replace('"', '')
            mod = mod.replace("'", '')
            mod = mod.replace(' ', '')
            try: 
                m = importlib.import_module(mod)
                logging.info(mod + ' Version: ' + m.__version__)
                logging.info(mod + ' Path: ' + m.__path__[0])
            except: ImportError as err:
                logging.warning(err.message)

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

        except Exception as err:
            logging.critical(traceback.format_exc())
            logging.critical('CRASHED')

        finally:
            if PRODUCTION_BOOL:        
                # Copy the log to the recent/ directory
                recent_dir = os.path.join(os.path.dirname(LOG_FILE_LOC), 'recent/')
                recent_filename = os.path.join(recent_dir, os.path.basename(LOG_FILE_LOC))
                existing_logs = glob.glob(os.path.join(recent_dir, '*.log'))
                for existing_log in existing_logs:
                    os.remove(existing_log)
                shutil.copyfile(LOG_FILE_LOC, recent_filename)

    return wrapped