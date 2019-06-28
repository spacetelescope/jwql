#! /usr/bin/env python

"""
This module is meant to monitor and gather statistics of the filesystem
that hosts data for the ``jwql`` application. This will answer
questions such as the total number of files, how much disk space is
being used, and then plot these values over time.

Authors
-------

    - Misty Cracraft

Use
---

    This module can be executed from the command line:

    ::

        python monitor_filesystem.py

    Alternatively, it can be called from scripts with the following
    import statements:

    ::

        from monitor_filesystem import filesystem_monitor
        from monitor_filesystem import plot_system_stats


    Required arguments (in a ``config.json`` file):
    ``filepath`` - The path to the input file needs to be in a
    ``config.json`` file in the ``utils`` directory
    ``outputs`` - The path to the output files needs to be in a
    ``config.json`` file in the ``utils`` directory.

    Required arguments for plotting:
    ``inputfile`` - The name of the file to save all of the system
    statistics to
    ``filebytype`` - The name of the file to save stats on fits type
    files to


Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``utils`` directory.

Notes
-----

    The ``monitor_filesystem`` function queries the filesystem,
    calculates the statistics and saves the output file(s) in the
    directory specified in the ``config.json`` file.

    The ``plot_system_stats`` function reads in the two specified files
    of statistics and plots the figures to an html output page as well
    as saving them to an output html file.
"""

from collections import defaultdict
import datetime
import logging
import os
import subprocess
import json

from astropy.utils.misc import JsonCustomEncoder

from jwql.utils.logging_functions import configure_logging, log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import filename_parser
from jwql.utils.utils import get_config


@log_fail
@log_info
def monitor_filesystem():
    """Tabulates the inventory of the JWST filesystem, saving
    statistics to files, and generates plots.
    """

    # Begin logging
    logging.info('Beginning filesystem monitoring.')

    # Get path, directories and files in system and count files in all directories
    settings = get_config()
    filesystem = settings['filesystem']
    outputs_dir = os.path.join(settings['outputs'], 'monitor_filesystem')

    # set up dictionaries for output
    results_dict = defaultdict(int)
    size_dict = defaultdict(float)
    # Walk through all directories recursively and count files
    logging.info('Searching filesystem...')
    for dirpath, dirs, files in os.walk(filesystem):
        results_dict['file_count'] += len(files)  # find number of all files
        for filename in files:
            file_path = os.path.join(dirpath, filename)
            if filename.endswith(".fits"):  # find total number of fits files
                results_dict['fits_files'] += 1
                size_dict['size_fits'] += os.path.getsize(file_path)
                suffix = filename_parser(filename)['suffix']
                results_dict[suffix] += 1
                size_dict[suffix] += os.path.getsize(file_path)
                detector = filename_parser(filename)['detector']
                instrument = detector[0:3]  # first three characters of detector specify instrument
                results_dict[instrument] += 1
                size_dict[instrument] += os.path.getsize(file_path)
    logging.info('{} files found in filesystem'.format(results_dict['fits_files']))

    # Get df style stats on file system
    out = subprocess.check_output('df {}'.format(filesystem), shell=True)
    outstring = out.decode("utf-8")  # put into string for parsing from byte format
    parsed = outstring.split(sep=None)

    # Select desired elements from parsed string
    total = int(parsed[8])  # in blocks of 512 bytes
    used = int(parsed[9])
    available = int(parsed[10])
    percent_used = parsed[11]

    # Save stats for plotting over time
    now = datetime.datetime.now().isoformat(sep='T', timespec='auto')  # get date of stats

    # set up output file and write stats
    statsfile = os.path.join(outputs_dir, 'statsfile.json')
    stats_output = {'timestamp': now, 'file_count': results_dict['file_count'], 
                    'tot': total, 'avail': available, 'used': used, 
                    'pct': percent_used}
    with open(statsfile, "r+") as f:
        f.seek(os.stat(statsfile).st_size -1)
        f.write( ',{}]'.format(now, json.dumps(stats_output, 
                                               cls=JsonCustomEncoder)))
    set_permissions(statsfile)
    logging.info('Saved file statistics to: {}'.format(statsfile))
    
    filetype_outs = ['fits', 'uncal', 'cal', 'rate', 'rateint', 'i2d', 'nrc', 
                     'nrs', 'nis', 'mir', 'fgs']
    filetype_keys = ['fits_files', 'uncal', 'cal', 'rate', 'rateints', 
                     'i2d', 'nrc', 'nrs', 'nis', 'mir', 'gui']

    # set up and read out stats on files by type
    filesbytype = os.path.join(outputs_dir, 'filesbytype.json')
    fbt_output = {'timestamp': now}
    fbt_output.update(dict([(x, results_dict[y]) for x, y in zip(filetype_outs, 
                                                              filetype_keys)]))
    with open(filesbytype, "r+") as f:
        f.seek(os.stat(filesbytype).st_size -1)
        f.write( ',{}]'.format(now, json.dumps(fbt_output,
                                               cls=JsonCustomEncoder)))
    set_permissions(filesbytype, verbose=False)
    logging.info('Saved file statistics by type to {}'.format(filesbytype))

    # set up file size by type file
    sizebytype = os.path.join(outputs_dir, 'sizebytype.json')
    sbt_output = {'timestamp': now}
    sbt_output.update(dict([(x, size_dict[y]) for x, y in zip(filetype_outs, 
                                                             filetype_keys)]))
    with open(sizebytype, "r+") as f:
        f.seek(os.stat(sizebytype).st_size -1)
        f.write( ',{}]'.format(now, json.dumps(sbt_output,
                                               cls=JsonCustomEncoder)))
    set_permissions(sizebytype, verbose=False)
    logging.info('Saved file sizes by type to {}'.format(sizebytype))
    logging.info('Filesystem statistics calculation complete.')



if __name__ == '__main__':

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    monitor_filesystem()