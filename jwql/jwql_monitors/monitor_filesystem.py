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
import numpy as np
import os
import subprocess

from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.plotting import figure, output_file, save

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
    statsfile = os.path.join(outputs_dir, 'statsfile.txt')
    with open(statsfile, "a+") as f:
        f.write("{0} {1:15d} {2:15d} {3:15d} {4:15d} {5}\n".format(now, results_dict['file_count'],
                total, available, used, percent_used))
    set_permissions(statsfile)
    logging.info('Saved file statistics to: {}'.format(statsfile))

    # set up and read out stats on files by type
    filesbytype = os.path.join(outputs_dir, 'filesbytype.txt')
    with open(filesbytype, "a+") as f2:
        f2.write("{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}\n".format(results_dict['fits_files'],
                 results_dict['uncal'], results_dict['cal'], results_dict['rate'],
                 results_dict['rateints'], results_dict['i2d'], results_dict['nrc'],
                 results_dict['nrs'], results_dict['nis'], results_dict['mir'], results_dict['gui']))
    set_permissions(filesbytype, verbose=False)
    logging.info('Saved file statistics by type to {}'.format(filesbytype))

    # set up file size by type file
    sizebytype = os.path.join(outputs_dir, 'sizebytype.txt')
    with open(sizebytype, "a+") as f3:
        f3.write("{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10}\n".format(size_dict['size_fits'],
                 size_dict['uncal'], size_dict['cal'], size_dict['rate'],
                 size_dict['rateints'], size_dict['i2d'], size_dict['nrc'],
                 size_dict['nrs'], size_dict['nis'], size_dict['mir'], size_dict['gui']))
    set_permissions(sizebytype, verbose=False)
    logging.info('Saved file sizes by type to {}'.format(sizebytype))

    logging.info('Filesystem statistics calculation complete.')

    # Create the plots
    plot_system_stats(statsfile, filesbytype, sizebytype)


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
    date, f_count, sysize, frsize, used, percent = np.loadtxt(stats_file, dtype=str, unpack=True)
    fits_files, uncalfiles, calfiles, ratefiles, rateintsfiles, i2dfiles, nrcfiles, nrsfiles, nisfiles, mirfiles, fgsfiles = np.loadtxt(filebytype, dtype=str, unpack=True)
    fits_sz, uncal_sz, cal_sz, rate_sz, rateints_sz, i2d_sz, nrc_sz, nrs_sz, nis_sz, mir_sz, fgs_sz = np.loadtxt(sizebytype, dtype=str, unpack=True)
    logging.info('Read in file statistics from {}, {}, {}'.format(stats_file, filebytype, sizebytype))

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
    nircam = nrcfiles.astype(int)
    nirspec = nrsfiles.astype(int)
    niriss = nisfiles.astype(int)
    miri = mirfiles.astype(int)
    fgs = fgsfiles.astype(int)

    fits_size = fits_sz.astype(float) / (1024.**3)
    uncal_size = uncal_sz.astype(float) / (1024.**3)
    cal_size = cal_sz.astype(float) / (1024.**3)
    rate_size = rate_sz.astype(float) / (1024.**3)
    rateints_size = rateints_sz.astype(float) / (1024.**3)
    i2d_size = i2d_sz.astype(float) / (1024.**3)
    nircam_size = nrc_sz.astype(float) / (1024.**3)
    nirspec_size = nrs_sz.astype(float) / (1024.**3)
    niriss_size = nis_sz.astype(float) / (1024.**3)
    miri_size = mir_sz.astype(float) / (1024.**3)
    fgs_size = fgs_sz.astype(float) / (1024.**3)

    # plot the data
    # Plot filecount vs. date
    p1 = figure(
       tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type='datetime',
       title="Total File Counts", x_axis_label='Date', y_axis_label='Count')
    p1.line(dates, file_count, line_width=2, line_color='blue')
    p1.circle(dates, file_count, color='blue')

    # Plot system stats vs. date
    p2 = figure(
      tools='pan,box_zoom,wheel_zoom,reset,save', x_axis_type='datetime',
      title='System stats', x_axis_label='Date', y_axis_label='GB')
    p2.line(dates, systemsize, legend='Total size', line_color='red')
    p2.circle(dates, systemsize, color='red')
    p2.line(dates, freesize, legend='Free bytes', line_color='blue')
    p2.circle(dates, freesize, color='blue')
    p2.line(dates, usedsize, legend='Used bytes', line_color='green')
    p2.circle(dates, usedsize, color='green')

    # Plot fits files by type vs. date
    p3 = figure(
       tools='pan,box_zoom,wheel_zoom,reset,save', x_axis_type='datetime',
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
    p3.line(dates, nircam, legend='nircam fits files', line_color='midnightblue')
    p3.x(dates, nircam, color='midnightblue')
    p3.line(dates, nirspec, legend='nirspec fits files', line_color='springgreen')
    p3.x(dates, nirspec, color='springgreen')
    p3.line(dates, niriss, legend='niriss fits files', line_color='darkcyan')
    p3.x(dates, niriss, color='darkcyan')
    p3.line(dates, miri, legend='miri fits files', line_color='dodgerblue')
    p3.x(dates, miri, color='dodgerblue')
    p3.line(dates, fgs, legend='fgs fits files', line_color='darkred')
    p3.x(dates, fgs, color='darkred')

    # plot size of total fits files by type
    p4 = figure(
       tools='pan,box_zoom,wheel_zoom,reset,save', x_axis_type='datetime',
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
    p4.line(dates, nircam_size, legend='nircam fits files', line_color='midnightblue')
    p4.x(dates, nircam_size, color='midnightblue')
    p4.line(dates, nirspec_size, legend='nirspec fits files', line_color='springgreen')
    p4.x(dates, nirspec_size, color='springgreen')
    p4.line(dates, niriss_size, legend='niriss fits files', line_color='darkcyan')
    p4.x(dates, niriss_size, color='darkcyan')
    p4.line(dates, miri_size, legend='miri fits files', line_color='dodgerblue')
    p4.x(dates, miri_size, color='dodgerblue')
    p4.line(dates, fgs_size, legend='fgs fits files', line_color='darkred')
    p4.x(dates, fgs_size, color='darkred')

    # create a layout with a grid pattern to save all plots
    grid = gridplot([[p1, p2], [p3, p4]])
    outfile = os.path.join(outputs_dir, "filesystem_monitor.html")
    output_file(outfile)
    save(grid)
    set_permissions(outfile)
    logging.info('Saved plot of all statistics to {}'.format(outfile))

    # Save each plot's components
    plots = [p1, p2, p3, p4]
    plot_names = ['filecount', 'system_stats', 'filecount_type', 'size_type']
    for plot, name in zip(plots, plot_names):
        plot.sizing_mode = 'stretch_both'
        script, div = components(plot)

        div_outfile = os.path.join(outputs_dir, "{}_component.html".format(name))
        with open(div_outfile, 'w') as f:
            f.write(div)
            f.close()
        set_permissions(div_outfile)

        script_outfile = os.path.join(outputs_dir, "{}_component.js".format(name))
        with open(script_outfile, 'w') as f:
            f.write(script)
            f.close()
        set_permissions(script_outfile)

        logging.info('Saved components files: {}_component.html and {}_component.js'.format(name, name))

    logging.info('Filesystem statistics plotting complete.')

    # Begin logging:
    logging.info("Completed.")


if __name__ == '__main__':

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    monitor_filesystem()
