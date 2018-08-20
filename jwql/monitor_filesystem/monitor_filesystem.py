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

    The ``filesystem_monitor`` function queries the filesystem,
    calculates the statistics and saves the output file(s) in the
    directory specified in the ``config.json`` file.

    The ``plot_system_stats`` function reads in the two specified files
    of statistics and plots the figures to an html output page as well
    as saving them to an output html file.
"""

from collections import defaultdict
import datetime
import logging
import numpy as np
import os
import subprocess

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import gridplot

from jwql.permissions.permissions import set_permissions
from jwql.utils.utils import filename_parser
from jwql.utils.utils import get_config
from jwql.logging.logging_functions import configure_logging
from jwql.logging.logging_functions import log_info
from jwql.logging.logging_functions import log_fail

@log_fail
@log_info
def filesystem_monitor():
    """ Get statistics on filesystem"""

        # Begin logging: 
    logging.info("Beginning the script run: ")

    # Get path, directories and files in system and count files in all directories
    settings = get_config()
    filesystem = settings['filesystem']
    outputs_dir = os.path.join(settings['outputs'], 'filesystem_monitor')

    # set up dictionaries for output
    results_dict = defaultdict(int)
    size_dict = defaultdict(float)
    # Walk through all directories recursively and count files
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
    statsfile = os.path.join(outputs_dir, 'statsfile.txt')
    with open(statsfile, "a+") as f:
        f.write("{0} {1:15d} {2:15d} {3:15d} {4:15d} {5}\n".format(now, results_dict['file_count'],
                total, available, used, percent_used))
    set_permissions(statsfile, verbose=False)

    # set up and read out stats on files by type
    filesbytype = os.path.join(outputs_dir, 'filesbytype.txt')
    with open(filesbytype, "a+") as f2:
        f2.write("{0} {1} {2} {3} {4} {5}\n".format(results_dict['fits_files'],
                 results_dict['uncal'], results_dict['cal'], results_dict['rate'],
                 results_dict['rateints'], results_dict['i2d']))
    set_permissions(filesbytype, verbose=False)

    # set up file size by type file
    sizebytype = os.path.join(outputs_dir, 'sizebytype.txt')
    with open(sizebytype, "a+") as f3:
        f3.write("{0} {1} {2} {3} {4} {5}\n".format(size_dict['size_fits'],
                 size_dict['uncal'], size_dict['cal'], size_dict['rate'],
                 size_dict['rateints'], size_dict['i2d']))
    set_permissions(sizebytype, verbose=False)

 
def plot_system_stats(stats_file, filebytype, sizebytype):
    """Read in the file of saved stats over time and plot them.

    Parameters
    -----------
    stats_file : str
        file containing information of stats over time
    filebytype : str
        file containing information of file counts by type over
        time
    sizebytype : str
        file containing information on file sizes by type over time
    """

    # get path for files
    settings = get_config()
    outputs_dir = os.path.join(settings['outputs'], 'monitor_filesystem')

    # read in file of statistics
    date, f_count, sysize, frsize, used, percent = np.loadtxt(os.path.join(outputs_dir, stats_file), dtype=str, unpack=True)
    fits_files, uncalfiles, calfiles, ratefiles, rateintsfiles, i2dfiles, nrcfiles, nrsfiles, nisfiles, mirfiles, fgsfiles = np.loadtxt(os.path.join(outputs_dir, filebytype), dtype=str, unpack=True)
    fits_sz, uncal_sz, cal_sz, rate_sz, rateints_sz, i2d_sz, nrc_sz, nrs_sz, nis_sz, mir_sz, fgs_sz = np.loadtxt(os.path.join(outputs_dir, sizebytype), dtype=str, unpack=True)

    # put in proper np array types and convert to GB sizes
    dates = np.array(date, dtype='datetime64')
    file_count = f_count.astype(float)
    systemsize = sysize.astype(float) / (1024.**3)
    freesize = frsize.astype(float) / (1024.**3)
    usedsize = used.astype(float) / (1024.**3)

    fits = fits_files.astype(int)
    uncal = uncalfiles.astype(int)
    cal = calfiles.astype(int)
    rate = ratefiles.astype(int)
    rateints = rateintsfiles.astype(int)
    i2d = i2dfiles.astype(int)

    fits_size = fits_sz.astype(float) / (1024.**3)
    uncal_size = uncal_sz.astype(float) / (1024.**3)
    cal_size = cal_sz.astype(float) / (1024.**3)
    rate_size = rate_sz.astype(float) / (1024.**3)
    rateints_size = rateints_sz.astype(float) / (1024.**3)
    i2d_size = i2d_sz.astype(float) / (1024.**3)

    # plot the data
    # Plot filecount vs. date
    p1 = figure(
       tools='pan,box_zoom,reset,save', x_axis_type='datetime',
       title="Total File Counts", x_axis_label='Date', y_axis_label='Count')
    p1.line(dates, file_count, line_width=2, line_color='blue')
    p1.circle(dates, file_count, color='blue')

    # Plot system stats vs. date
    p2 = figure(
      tools='pan,box_zoom,reset,save', x_axis_type='datetime',
      title='System stats', x_axis_label='Date', y_axis_label='GB')
    p2.line(dates, systemsize, legend='Total size', line_color='red')
    p2.circle(dates, systemsize, color='red')
    p2.line(dates, freesize, legend='Free bytes', line_color='blue')
    p2.circle(dates, freesize, color='blue')
    p2.line(dates, usedsize, legend='Used bytes', line_color='green')
    p2.circle(dates, usedsize, color='green')

    # Plot fits files by type vs. date
    p3 = figure(
       tools='pan,box_zoom,reset,save', x_axis_type='datetime',
       title="Total File Counts by Type", x_axis_label='Date', y_axis_label='Count')
    p3.line(dates, fits, legend='Total fits files', line_color='black')
    p3.circle(dates, fits, color='black')
    p3.line(dates, uncal, legend='uncalibrated fits files', line_color='red')
    p3.diamond(dates, uncal, color='red')
    p3.line(dates, cal, legend='calibrated fits files', line_color='blue')
    p3.square(date, cal, color='blue')
    p3.line(dates, rate, legend='rate fits files', line_color='green')
    p3.triangle(dates, rate, color='green')
    p3.line(dates, rateints, legend='rateints fits files', line_color='orange')
    p3.asterisk(dates, rateints, color='orange')
    p3.line(dates, i2d, legend='i2d fits files', line_color='purple')
    p3.x(dates, i2d, color='purple')

    # plot size of total fits files by type
    p4 = figure(
       tools='pan,box_zoom,reset,save', x_axis_type='datetime',
       title="Total File Sizes by Type", x_axis_label='Date', y_axis_label='GB')
    p4.line(dates, fits_size, legend='Total fits files', line_color='black')
    p4.circle(dates, fits_size, color='black')
    p4.line(dates, uncal_size, legend='uncalibrated fits files', line_color='red')
    p4.diamond(dates, uncal_size, color='red')
    p4.line(dates, cal_size, legend='calibrated fits files', line_color='blue')
    p4.square(date, cal_size, color='blue')
    p4.line(dates, rate_size, legend='rate fits files', line_color='green')
    p4.triangle(dates, rate_size, color='green')
    p4.line(dates, rateints_size, legend='rateints fits files', line_color='orange')
    p4.asterisk(dates, rateints_size, color='orange')
    p4.line(dates, i2d_size, legend='i2d fits files', line_color='purple')
    p4.x(dates, i2d_size, color='purple')

    # create a layout with a grid pattern
    grid = gridplot([[p1, p2], [p3, p4]])
    outfile = os.path.join(outputs_dir, "filesystem_monitor.html")
    output_file(outfile)
    save(grid)
    set_permissions(outfile, verbose=False)

    # Begin logging: 
    logging.info("Completed.")



if __name__ == '__main__':

    inputfile = 'statsfile.txt'
    filebytype = 'filesbytype.txt'
    sizebytype = 'sizebytype.txt'

    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    filesystem_monitor()
    plot_system_stats(inputfile, filebytype, sizebytype)
