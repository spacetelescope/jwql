#! /usr/bin/env python

"""Clean old log files from the collection of log files

Authors
-------

    - Bryan Hilbert

Use
---

    To delete log files that are older than some threshold age:
    ::

    > python clean_old_log_files.py --time_limit 7  # days

"""
import argparse
from datetime import datetime, timedelta
import os
import socket

from jwql.utils.utils import get_config

HOSTNAME = socket.gethostname()
configs = get_config()
LOG_BASE_DIR = configs['log_dir']


def define_options():
    """Create parser to take the time limit.

    Returns
    -------
    parser : argparse.ArgumentParser
        Parser containing time limit
    """
    usage = 'clean_old_log_files.py -t 14'
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument('-t', '--time_limit', type=float, default=14,
                        help='Time limit in days. Log files older than this will be deleted.')
    parser.add_argument('-d', '--dry_run', action="store_true",
                        help='If True, the log files that would be deleted are printed to the screen')
    return parser


def run(time_limit=timedelta(days=14), dry_run=False):
    """Look through log directories and delete log files that are older than ``time_limit``.
    Have time_limit default to be 14 days.

    Inputs
    ------
    time_limit : datetime.timdelta
        Files older than this time limit will be deleted

    dry_run : bool
        If True, log files will not be deleted. Those that would be deleted are instead
        printed to the screen
    """
    now = datetime.now()

    if 'pljwql' in HOSTNAME:
        subdir = 'ops'
    elif 'tljwql' in HOSTNAME:
        subdir = 'test'
    else:
        # This should cover the dev server as well as local machines
        subdir = 'dev'

    #log_dir = os.path.join(LOG_BASE_DIR, subdir)
    log_dir = '/ifs/jwst/wit/nircam/hilbert/jwql/test_logs/dev'
    for logtype in os.scandir(log_dir):
        if logtype.is_dir():
            for item in os.scandir(logtype):
                # We only try to delete log files produced by the machine on which
                # this script is running. e.g. log files produced by the test server
                # can only be deleted by running this script on the test server.
                if HOSTNAME in item.name and item.name[-4:] == '.log':
                    stat_result = item.stat()
                    last_modified_time = datetime.fromtimestamp(stat_result.st_mtime)
                    age = now - last_modified_time
                    if age > time_limit:
                        full_path = os.path.join(log_dir, logtype, item)
                        if not dry_run:
                            os.remove(full_path)
                        else:
                            print(f'DELETE: {full_path}')

if __name__ == '__main__':
    parser = define_options()
    args = parser.parse_args()
    run(time_limit=timedelta(days=args.time_limit), dry_run=args.dry_run)
