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
    parser.add_argument('-t', '--time_limit', type=int, default=14,
                        help='Time limit in days. Log files older than this will be deleted.')
    return parser

def run(time_limit=timedelta(days=14)):
    """Look through log directories and delete log files that are older than ``time_limit``.
    Have time_limit default to be 14 days.

    Inputs
    ------
    time_limit : datetime.timdelta
        Files older than this time limit will be deleted
    """
    now = datetime.now()

    if 'pljwql' in HOSTNAME:
        subdir = 'ops'
    elif 'tljwql' in HOSTNAME:
        subdir = 'test'
    else:
        # This should cover the dev server as well as local machines
        subdir = 'dev'

    log_dir = os.path.join(LOG_BASE_DIR, subdir)
    for logtype in os.scandir(log_dir):
        if logtype.is_dir():
            for item in os.scandir(logtype):
                # We only try to delete log files produced by the machine one which
                # this script is running. e.g.
                if HOSTNAME in item.name and item.name[-4:] == '.log':
                    stat_result = item.stat()
                    last_modified_time = datetime.fromtimestamp(stat_result.st_mtime)
                    age = now - last_modified_time
                    if age > time_limit:
                        #os.remove(item.name)
                        full_path = os.path.join(log_dir, logtype, item)
                        print(f'DELETING {full_path}')
    print('Once initial testing is complete, replace the print statement above with the os.remove line above it.')

if __name__ == '__main__':
    parser = define_options()
    args = parser.parse_args()
    run(timedelta(days=args.time_limit))
