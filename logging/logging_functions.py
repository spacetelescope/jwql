""" Logging functions for the James Webb Quicklook automation platform

Working notes: 
1) Will definitely want the same type of decorators that WFC3 QL uses - one
to track failures and one to track useful system information. Are there
any other things we will want to create a decorator for? 



2) Also which module version information will we want to track with our info 
decorator? 

--> I updated this portion of the code to include everything from our 
`setup.py` under the required section there. 



3) Do we want to follow the same naming convention stuff? Have the make_log_file 
function perform the same way?



4) Will we follow the same saving convention of the different directories and 
want to set up a recent directory for the most recent log file to be available 
all the time? 

--> I started updating to use JWQL information instead. We still need to decide
what our goal is for our log files. 





Authors
-------
Catherine Martlin 2018


Use
___


Dependencies
____________


References
__________

Code will likely be adopted from python routine logging_functions.py written 
by Alex Viana, 2013 for the WFC3 Quicklook automation platform.

Notes
_____



"""

import datetime
import getpass
import glob
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
    module being logged and the current datetime.  If the code is being
    executed by ``jwqladmin``, it goes to the production area.
    Otherwise it goes to the ``_______`` area.

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
        log_file = os.path.join('/grp/jwst/ins/jwql/logs/', module, filename)
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

        # Log common module version information
        try:
            import astropy
            logging.info('astropy Version: ' + astropy.__version__)
            logging.info('astropy Path: ' + astropy.__path__[0])
        except ImportError as err:
            logging.warning(err.message)
        try:
            import django
            logging.info('django Version: ' + django.__version__)
            logging.info('django Path: ' + django.__path__[0])
        except ImportError as err:
            logging.warning(err.message)
        try:
            import matplotlib
            logging.info('matplotlib Version: ' + matplotlib.__version__)
            logging.info('matplotlib Path: ' + matplotlib.__path__[0])
        except ImportError as err:
            logging.warning(err.message)
        try:
            import numpy
            logging.info('numpy Version: ' + numpy.__version__)
            logging.info('numpy Path: ' + numpy.__path__[0])
        except ImportError as err:
            logging.warning(err.message)
        try:
            import sphinx
            logging.info('sphinx Version: ' + sphinx.__version__)
            logging.info('sphinx Path: ' + sphinx.__path__[0])
        except ImportError as err:
            logging.warning(err.message)
        try:
            import sqlalchemy
            logging.info('sqlalchemy Version: ' + sqlalchemy.__version__)
            logging.info('sqlalchemy Path: ' + sqlalchemy.__path__[0])
        except ImportError as err:
            logging.warning(err.message)
        try:
            import yaml
            logging.info('yaml Version: ' + yaml.__version__)
            logging.info('yaml Path: ' + yaml.__path__[0])
        except ImportError as err:
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


def print_or_log(message, production):
    """Print or log the given message, depending if the script is being
    executed in production mode or not.

    When 'production' is True, it is assumed that the user is operating
    the script in production and thus wishes to have the output of the
    script be logged.  Otherwise, the message is printed to standard
    output.

    Parameters:
        message : string
            The message to log or print.
        production : boolean
            True/False if operating in production or not.

    Outputs:
        Either a logged message or a printed message to the standard
        output.
    """

    if production:
        logging.info(message)
    else:
        print(message)


# -----------------------------------------------------------------------------

def production_only(func, prod_serv):
    """Decorator that only executes the decorated code on the
    production server.

    Parameters
    ----------
    func : func
        The function to decorate.
    prod_serv : str
        The name of the production server

    Returns
    -------
    wrapped : func
        The wrapped function.
    """

    @wraps(func)
    def wrapped():
        if socket.gethostname() == prod_serv:
            func()
        else:
            print('Dev mode. Not running ' + func.__name__)

    return wrapped




