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
    of statistics and plots the figures to an html output page as well as
    saving them to an output html file.
"""

from collections import defaultdict
import datetime
import numpy as np
import os
import subprocess

from bokeh.plotting import figure, output_file, show
from bokeh.layouts import gridplot

from jwql.utils.utils import filename_parser
from jwql.utils.utils import get_config


def filesystem_monitor():
    """ Get statistics on filesystem"""

    # Get path, directories and files in system and count files in all directories
    settings = get_config()
    filesystem = settings['filesystem']
    outputs_dir = os.path.join(settings['outputs'], 'filesystem_monitor')

    # set counters to zero
    file_count = 0
    fits_files = 0

    results_dict = defaultdict(int)
    # Walk through all directories recursively and count files
    for dirpath, dirs, files in os.walk(filesystem):  # .__next__()
        file_count += len(files)
        for filename in files:
            if filename.endswith(".fits"):  # find total number of fits files
                fits_files += 1
                suffix = filename_parser(filename)['suffix']
                results_dict[suffix] += 1

    # Get df style stats on file system
    out = subprocess.check_output('df .', shell=True)
    outstring = out.decode("utf-8")  # put into string for parsing from byte format
    parsed = outstring.split(sep=None)

    # Select desired elements from parsed string
    total = int(parsed[11])  # in blocks of 512 bytes
    used = int(parsed[12])
    available = int(parsed[13])
    percent_used = parsed[14]

    # Save stats for plotting over time
    now = datetime.datetime.now().isoformat(sep='T', timespec='auto')  # get date of stats

    # set up output file and write stats
    output = os.path.join(outputs_dir, 'statsfile.txt')

    with open(output, "a") as f:
        f.write("{0} {1:15d} {2:15d} {3:15d} {4:15d} {5}\n".format(now, file_count, total,
                available, used, percent_used))

    # set up and read out stats on files by type
    filesbytype = os.path.join(outputs_dir, 'filesbytype.txt')
    with open(filesbytype, "a+") as f2:
        f2.write("{0} {1} {2} {3} {4} {5}\n".format(fits_files, results_dict['uncal'],
                 results_dict['cal'], results_dict['rate'], results_dict['rateints'],
                 results_dict['i2d']))


def plot_system_stats(stats_file, filebytype):
    """Read in the file of saved stats over time and plot them.

    Parameters
    -----------
    stats_file : str
        file containing information of stats over time
    filebytype : str
        file containing information of file counts by type over
        time
    """

    # get path for files
    settings = get_config()
    outputs_dir = os.path.join(settings['outputs'], 'filesystem_monitor')

    # read in file of statistics
    date, f_count, sysize, frsize, used, percent = np.loadtxt(outputs_dir + stats_file, dtype=str, unpack=True)

    fits_files, uncalfiles, calfiles, ratefiles, rateintsfiles, i2dfiles = np.loadtxt(outputs_dir + filebytype,
                                                                                      dtype=str, unpack=True)

    # put in proper np array types
    dates = np.array(date, dtype='datetime64')
    file_count = f_count.astype(int)
    systemsize = sysize.astype(int)
    freesize = frsize.astype(int)
    usedsize = used.astype(int)

    fits = fits_files.astype(int)
    uncal = uncalfiles.astype(int)
    cal = calfiles.astype(int)
    rate = ratefiles.astype(int)
    rateints = rateintsfiles.astype(int)
    i2d = i2dfiles.astype(int)

    # plot the data
    # Plot filecount vs. date
    output_file(outputs_dir + "filecount.html")
    p1 = figure(
       tools='pan,box_zoom,reset,save', x_axis_type='datetime',
       title="Total File Counts", x_axis_label='Date', y_axis_label='Count')
    p1.line(dates, file_count, line_width=2, line_color='blue')
    p1.circle(dates, file_count, color='blue')

    # Plot system stats vs. date
    p2 = figure(
      tools='pan,box_zoom,reset,save', x_axis_type='datetime',
      title='System stats', x_axis_label='Date', y_axis_label='Bytes')
    p2.line(dates, systemsize, legend='Total size', line_color='red')
    p2.line(dates, freesize, legend='Free bytes', line_color='blue')
    p2.line(dates, usedsize, legend='Used bytes', line_color='green')

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

    # create a layout with a grid pattern
    grid = gridplot([[p1, p2], [p3, None]])
    show(grid)


if __name__ == '__main__':

   inputfile = 'statsfile.txt'
   filebytype = 'filesbytype.txt'

   filesystem_monitor()
   plot_system_stats(inputfile,filebytype)
