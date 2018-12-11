#! /usr/bin/env python

"""
This module is meant to monitor and gather statistics of the filesystem
that hosts data for the ``jwql`` application. This will answer
questions such as the total number of files, how much disk space is
being used, and then plot these values over time.

Authors
-------

    - Misty Cracraft, Sara Ogaz

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

import datetime
import logging
import numpy as np
import os
import subprocess

from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.plotting import figure, output_file, save

from jwql.database import database_interface as di
from jwql.database.database_interface import Filesystem_general
from jwql.database.database_interface import Filesystem_instrument as InsDb
from jwql.utils.logging_functions import configure_logging, log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import filename_parser
from jwql.utils.utils import get_config


@log_fail
@log_info
def monitor_filesystem():
    """
    Tabulates the inventory of the JWST filesystem, saving
    statistics to files, and generates plots.
    """

    # Begin logging
    logging.info('Beginning filesystem monitoring.')

    # Get path, dirs and files in system and count files in all directories
    settings = get_config()
    filesystem = settings['filesystem']

    # set up dictionaries for output
    results_dict = {}
    size_dict = {}

    # Walk through all directories recursively and count files
    logging.info('Searching filesystem...')
    for dirpath, dirs, files in os.walk(filesystem):
        results_dict['file_count'] += len(files)  # find number of all files
        for filename in files:
            file_path = os.path.join(dirpath, filename)
            if filename.endswith(".fits"):  # find total number of fits files
                suffix = filename_parser(filename)['suffix']  # define suffix
                detector = filename_parser(filename)['detector']
                # first three characters of detector specify instrument
                instrument = detector[0:3]
                key_count = instrument+'_'+suffix+'_count'
                key_size = instrument+'_'+suffix+'_size'
                results_dict['fits_files'] += 1
                size_dict['size_fits'] += os.path.getsize(file_path)
                results_dict[key_count] += 1
                size_dict[key_size] += os.path.getsize(file_path)
                # size_dict[instrument] += os.path.getsize(file_path)
    logging.info('{} files found in filesystem'.format(
        results_dict['fits_files']))

    # Get df style stats on file system
    out = subprocess.check_output('df {}'.format(filesystem), shell=True)
    # put into string for parsing from byte format
    outstring = out.decode("utf-8")
    parsed = outstring.split(sep=None)

    # Select desired elements from parsed string, put these in dictionary, too?
    total_size = int(parsed[8])  # in blocks of 512 bytes
    used_size = int(parsed[9])
    available_size = int(parsed[10])

    # Save stats for plotting over time  # also define this as part of database
    # get date of stats
    now = datetime.datetime.now().isoformat(sep='T')

    # add row to filesystem_general table
    di.session.add(di.Filesystem_general(date=now, total_size=total_size,
                                         used_size=used_size,
                                         available_size=available_size,
                                         file_count=results_dict['file_count'],
                                         fits_files=results_dict['fits_files'],
                                         size_fits=size_dict['size_fits']))

    # Add row to filesystem_instrument table
    current_columns = [t.name for t in
                       di.Filesystem_instrument.metadata.sorted_tables[2].columns]
    current_columns.remove('date')

    # fancy dictionary stuff
    combo_dict = {**results_dict, **size_dict}
    # more fancy dict stuff
    filtered_dict = {k: combo_dict.get(k, 0) for k in current_columns}
    di.session.add(di.Filesystem_instrument(date=now, **filtered_dict))

    # Commit new rows to database
    di.session.commit()

    # Create the plots
    plot_system_stats()


def plot_system_stats():
    """
    Read in the file of saved stats over time and plot them.
    """

    # get path for files
    settings = get_config()
    outputs_dir = os.path.join(settings['outputs'], 'monitor_filesystem')

    # read in file of statistics
    general_query = di.session.query(Filesystem_general.date,
                                     Filesystem_general.file_count,
                                     Filesystem_general.total_size,
                                     Filesystem_general.used_size,
                                     Filesystem_general.available_size,
                                     Filesystem_general.fits_files,
                                     Filesystem_general.size_fits).all()
    date_list_general, file_count, sy_size, used_size, free_size, fits_files, \
        fits_sz = [], [], [], [], [], [], []

    for row in general_query:
        date_list_general.append(row[0])
        file_count.append(row[1])
        sy_size.append(row[2])
        used_size.append(row[3])
        free_size.append(row[4])
        fits_files.append(row[5])
        fits_sz.append(row[6])

    # put in proper np array types and convert to GB sizes
    dates = np.array(date_list_general, dtype='datetime64')
    systemsize = np.array(sy_size) / (1024.**3)
    freesize = np.array(free_size) / (1024.**3)
    usedsize = np.array(used_size) / (1024.**3)
    fits_size = np.array(fits_sz) / (1024.**3)
    fits = fits_files

    # Information from Filesystem_instrument
    # There is a better way to do this... but we don't know what the column
    # name lists will be ahead of time, so from what I can tell, we have to
    # either hard code the column names or do the summation after the query.
    uncal_filecount_results = di.session.query((InsDb.nrc_uncal_count +
                                                InsDb.nrs_uncal_count +
                                                InsDb.nis_uncal_count +
                                                InsDb.mir_uncal_count +
                                                InsDb.gui_uncal_count).
                                               label("uncal_count")).all()
    uncal = [row[0] for row in uncal_filecount_results]

    cal_filecount_results = di.session.query((InsDb.nrc_cal_count +
                                              InsDb.nrs_cal_count +
                                              InsDb.nis_cal_count +
                                              InsDb.mir_cal_count +
                                              InsDb.gui_cal_count).
                                             label("cal_count")).all()
    cal = [row[0] for row in cal_filecount_results]

    rate_filecount_results = di.session.query((InsDb.nrc_rate_count +
                                               InsDb.nrs_rate_count +
                                               InsDb.nis_rate_count +
                                               InsDb.mir_rate_count +
                                               InsDb.gui_rate_count).
                                              label("rate_count")).all()
    rate = [row[0] for row in rate_filecount_results]

    rateints_filecount_results = di.session.query((InsDb.nrc_rateints_count +
                                                   InsDb.nrs_rateints_count +
                                                   InsDb.nis_rateints_count +
                                                   InsDb.mir_rateints_count +
                                                   InsDb.gui_rateints_count).
                                                  label("rateints_count")).all()
    rateints = [row[0] for row in rateints_filecount_results]

    i2d_filecount_results = di.session.query((InsDb.nrc_i2d_count +
                                              InsDb.nrs_i2d_count +
                                              InsDb.nis_i2d_count +
                                              InsDb.mir_i2d_count +
                                              InsDb.gui_i2d_count).
                                             label("i2d_count")).all()
    i2d = [row[0] for row in i2d_filecount_results]

    nircam_filecount_results = di.session.query((InsDb.nrc_uncal_count +
                                                 InsDb.nrc_cal_count +
                                                 InsDb.nrc_rate_count +
                                                 InsDb.nrc_rateints_count +
                                                 InsDb.nrc_i2d_count).
                                                label("nir_count")).all()
    nircam = [row[0] for row in nircam_filecount_results]

    nirspec_filecount_results = di.session.query((InsDb.nrs_uncal_count +
                                                  InsDb.nrs_cal_count +
                                                  InsDb.nrs_rate_count +
                                                  InsDb.nrs_rateints_count +
                                                  InsDb.nrs_i2d_count).
                                                 label("nrs_count")).all()
    nirspec = [row[0] for row in nirspec_filecount_results]

    niriss_filecount_results = di.session.query((InsDb.nis_uncal_count +
                                                 InsDb.nis_cal_count +
                                                 InsDb.nis_rate_count +
                                                 InsDb.nis_rateints_count +
                                                 InsDb.nis_i2d_count).
                                                label("nis_count")).all()
    niriss = [row[0] for row in niriss_filecount_results]

    miri_filecount_results = di.session.query((InsDb.mir_uncal_count +
                                               InsDb.mir_cal_count +
                                               InsDb.mir_rate_count +
                                               InsDb.mir_rateints_count +
                                               InsDb.mir_i2d_count).
                                              label("mir_count")).all()
    miri = [row[0] for row in miri_filecount_results]

    fgs_filecount_results = di.session.query((InsDb.gui_uncal_count +
                                              InsDb.gui_cal_count +
                                              InsDb.gui_rate_count +
                                              InsDb.gui_rateints_count +
                                              InsDb.gui_i2d_count).
                                             label("nir_count")).all()
    fgs = [row[0] for row in fgs_filecount_results]

    # Next is the size set
    uncal_size_results = di.session.query((InsDb.nrc_uncal_size +
                                           InsDb.nrs_uncal_size +
                                           InsDb.nis_uncal_size +
                                           InsDb.mir_uncal_size +
                                           InsDb.gui_uncal_size).
                                          label("uncal_size")).all()
    uncal_size = np.array([row[0] for row in uncal_size_results]) / (1024.**3)

    cal_size_results = di.session.query((InsDb.nrc_cal_size +
                                         InsDb.nrs_cal_size +
                                         InsDb.nis_cal_size +
                                         InsDb.mir_cal_size +
                                         InsDb.gui_cal_size).
                                        label("cal_size")).all()
    cal_size = np.array([row[0] for row in cal_size_results]) / (1024.**3)

    rate_size_results = di.session.query((InsDb.nrc_rate_size +
                                          InsDb.nrs_rate_size +
                                          InsDb.nis_rate_size +
                                          InsDb.mir_rate_size +
                                          InsDb.gui_rate_size).
                                         label("rate_size")).all()
    rate_size = np.array([row[0] for row in rate_size_results]) / (1024.**3)

    rateints_size_results = di.session.query((InsDb.nrc_rateints_size +
                                              InsDb.nrs_rateints_size +
                                              InsDb.nis_rateints_size +
                                              InsDb.mir_rateints_size +
                                              InsDb.gui_rateints_size).
                                             label("rateints_size")).all()
    rateints_size = np.array([row[0] for row in rateints_size_results]) / (1024.**3)

    i2d_size_results = di.session.query((InsDb.nrc_i2d_size +
                                         InsDb.nrs_i2d_size +
                                         InsDb.nis_i2d_size +
                                         InsDb.mir_i2d_size +
                                         InsDb.gui_i2d_size).
                                        label("i2d_size")).all()
    i2d_size = np.array([row[0] for row in i2d_size_results]) / (1024.**3)

    nircam_size_results = di.session.query((InsDb.nrc_uncal_size +
                                            InsDb.nrc_cal_size +
                                            InsDb.nrc_rate_size +
                                            InsDb.nrc_rateints_size +
                                            InsDb.nrc_i2d_size).
                                           label("nrc_size")).all()
    nircam_size = np.array([row[0] for row in nircam_size_results]) / (1024.**3)

    nirspec_size_results = di.session.query((InsDb.nrs_uncal_size +
                                             InsDb.nrs_cal_size +
                                             InsDb.nrs_rate_size +
                                             InsDb.nrs_rateints_size +
                                             InsDb.nrs_i2d_size).
                                            label("nrs_size")).all()
    nirspec_size = np.array([row[0] for row in nirspec_size_results]) / (1024.**3)

    niriss_size_results = di.session.query((InsDb.nis_uncal_size +
                                            InsDb.nis_cal_size +
                                            InsDb.nis_rate_size +
                                            InsDb.nis_rateints_size +
                                            InsDb.nis_i2d_size).
                                           label("nis_size")).all()
    niriss_size = np.array([row[0] for row in niriss_size_results]) / (1024.**3)

    miri_size_results = di.session.query((InsDb.mir_uncal_size +
                                          InsDb.mir_cal_size +
                                          InsDb.mir_rate_size +
                                          InsDb.mir_rateints_size +
                                          InsDb.mir_i2d_size).
                                         label("mir_size")).all()
    miri_size = np.array([row[0] for row in miri_size_results]) / (1024.**3)

    fgs_size_results = di.session.query((InsDb.gui_uncal_size +
                                         InsDb.gui_cal_size +
                                         InsDb.gui_rate_size +
                                         InsDb.gui_rateints_size +
                                         InsDb.gui_i2d_size).
                                        label("mir_size")).all()
    fgs_size = np.array([row[0] for row in fgs_size_results]) / (1024.**3)

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
    # This was original "date", what did we want here?
    p3.square(dates, cal, color='blue')
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
    # This was original "date", what did we want here?
    p4.square(dates, cal_size, color='blue')
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
