#! /usr/bin/env python

"""This module monitors the status of the ``jwql`` monitors via their
log files. Basic results (e.g. ``success``, ``failure``) are collected
and placed in a ``bokeh`` table for display on the web app.

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be executed as such:

    ::

        from jwql.jwql_monitors import monitor_cron_jobs
        monitor_cron_jobs.status()

Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``utils`` directory.
"""

from datetime import datetime
import logging
import numpy as np
import os
import time

from bokeh.io import save, output_file
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, DateFormatter, HTMLTemplateFormatter, TableColumn

from jwql.utils.logging_functions import configure_logging, log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import get_config


def create_table(status_dict):
    """Create interactive ``bokeh`` table containing the logfile status
    results.

    Parameters
    ----------
    status_dict : dict
        Nested dictionary with status results from all logfiles
    """
    # Rearrange the nested dictionary into a non-nested dict for the table
    filenames = []
    dates = []
    missings = []
    results = []
    for key in status_dict:
        filenames.append(status_dict[key]['logname'])
        dates.append(datetime.fromtimestamp(status_dict[key]['latest_time']))
        missings.append(str(status_dict[key]['missing_file']))
        results.append(status_dict[key]['status'])

    # div to color the boxes in the status column
    success_template = """
    <div style="background:<%=
        (function colorfromstr(){
            if(value == "success"){
                return("green")}
            else{return("red")}
            }()) %>;
        color: white">
    <%= value %></div>
    """

    # div to color the boxes in the column for possibly late logfiles
    missing_template = """
    <div style="background:<%=
        (function colorfrombool(){
            if(value == "True"){
                return("orange")}
            else{return("green")}
            }()) %>;
        color: white">
    <%= value %></div>
    """
    success_formatter = HTMLTemplateFormatter(template=success_template)
    missing_formatter = HTMLTemplateFormatter(template=missing_template)

    data = dict(name=list(status_dict.keys()), filename=filenames, date=dates, missing=missings,
                result=results)
    source = ColumnDataSource(data)

    datefmt = DateFormatter(format="RFC-2822")
    columns = [
        TableColumn(field="name", title="Monitor Name", width=200),
        TableColumn(field="filename", title="Most Recent File", width=350),
        TableColumn(field="date", title="Most Recent Time", width=200, formatter=datefmt),
        TableColumn(field="missing", title="Possible Missing File", width=200, formatter=missing_formatter),
        TableColumn(field="result", title="Status", width=100, formatter=success_formatter),
    ]
    data_table = DataTable(source=source, columns=columns, width=800, height=280, index_position=None)

    # Get output directory for saving the table files
    output_dir = get_config()['outputs']
    output_filename = 'cron_status_table'

    # Save full html
    html_outfile = os.path.join(output_dir, 'monitor_cron_jobs', '{}.html'.format(output_filename))
    output_file(html_outfile)
    save(data_table)
    try:
        set_permissions(html_outfile)
    except PermissionError:
        logging.warning('Unable to set permissions for {}'.format(html_outfile))
    logging.info('Saved Bokeh full HTML file: {}'.format(html_outfile))


def find_latest(logfiles):
    """Given a list of log files in a directory, identify the most
    recent. The way that ``jwql.utils.logging_functions.make_log_file``
    is set up, log files for all monitors are guaranteed to be the name
    of the monitor followed by the datetime that they were run, so we
    should be able to simply sort the filenames and the last will be the
    most recent.

    Parameters
    ----------
    logfiles : list
        List of logfiles in the directory

    Returns
    -------
    latest : str
        Filename of the most recent file

    latest_time : float
        Time associated with the most recent log file
    """
    latest = sorted(logfiles)[-1]
    latest_time = os.path.getctime(latest)
    return (latest, latest_time)


def get_cadence(filenames):
    """Calculate the cadence of the log files in a given directory.
    Use timestamps

    Parameters
    ----------
    filenames : list
        List of log files to examine

    Returns
    -------
    mean_delta : float
        Mean time in seconds between the appearance of consecutive log
        files

    stdev_delta : float
        Standard deviation in seconds between the appearance of
        consecutive log files
    """
    minimum_log_num = 3  # Set to a low value for now since we don't have many logfiles
    times = [os.path.getctime(filename) for filename in filenames]
    if len(times) >= minimum_log_num:
        sorted_times = np.array(sorted(times))
        delta_times = sorted_times[1:] - sorted_times[0:-1]
        mean_delta = np.mean(delta_times)
        stdev_delta = np.std(delta_times)
    else:
        # If there are < minimum_log_num logfiles, then let's assume we can't
        # get a reliable measure of cadence. Fall back to a value of
        # 1 year between files, to avoid accidentally flagging this monitor
        # as running late in the subsequent check
        mean_delta = 31556736.0  # sec per year
        stdev_delta = 31556736.0  # sec per year
    return mean_delta, stdev_delta


def missing_file_check(avg_time_between, uncertainty, latest_file):
    """Given the name of the most recent log file, along with the
    historical average time between files and the stdev of the time
    between files, determine whether we expect a more recent log file
    than the file given. This could hint at a problem with the cron job
    used to create the log files.

    Parameters
    ----------
    avg_time_between : float
        Average number of seconds between log files

    uncertainty : float
        Standard deviation of the number of seconds between log files

    latest_file : str
        Name of the most recent log file

    Returns
    -------
    late : bool
        True = We expect a more recent file than that given
        False =  It is reasonable that the file given is the most
        recent
    """
    latest_time = os.path.getctime(latest_file)
    now = time.time()
    time_since_latest = now - latest_time
    if time_since_latest > (avg_time_between + 3 * uncertainty):
        late = True
    else:
        late = False
    return late


@log_fail
@log_info
def status(production_mode=True):
    """Main function: determine the status of the instrument montiors
    by examining log files.

    Parameters
    ----------
    production_mode : bool
        If ``True``, look in the main log directory. If ``False``, look
        in the ``dev`` log file directory.

    Returns
    -------
    logfile_status : dict
        Nested dictionary containing the status for all monitors. Top
        level keys include all monitors. Within a given monitor, the
        value is a dictionary containing 'missing_file' and 'status'
        keys. 'missing_file' is a boolean describing whether or not
        there is a suspected missing log file based on the timestamps
        of the existing files. 'status' is a string that is either
        'success' or 'failure'.
    """
    # Begin logging
    logging.info("Beginning cron job status monitor")

    # Get main logfile path
    log_path = get_config()['log_dir']

    # If we are in development mode, the log files are in a slightly
    # different location than in production mode
    if production_mode:
        log_path = os.path.join(log_path, 'prod')
    else:
        log_path = os.path.join(log_path, 'dev')

    # Set up a dictionary to keep track of results
    logfile_status = {}

    # Get a list of the directories under the main logging directory.
    generator = os.walk(log_path, topdown=True)

    # Loop over monitors
    for subdir, subsubdir, filenames in generator:
        # When running in production mode, skip the 'dev' subdirectory,
        # as it contains the development version of the monitor logs
        if production_mode:
            subsubdir[:] = [dirname for dirname in subsubdir if dirname != 'dev']

        if len(filenames) > 0:
            monitor_name = subdir.split('/')[-1]

            # Avoid monitor_cron_jobs itseft
            if monitor_name != 'monitor_cron_jobs':

                log_file_list = [os.path.join(subdir, filename) for filename in filenames]

                # Find the cadence of the monitor
                delta_time, stdev_time = get_cadence(log_file_list)

                # Identify the most recent log file
                latest_log, latest_log_time = find_latest(log_file_list)

                # Check to see if we expect a file more recent than the latest
                missing_file = missing_file_check(delta_time, stdev_time, latest_log)
                if missing_file:
                    logging.warning('Expected a more recent {} logfile than {}'
                                    .format(monitor_name, os.path.basename(latest_log)))

                # Check the file for success/failure
                result = success_check(latest_log)
                logging.info('{}: Latest log file indicates {}'.format(monitor_name, result))

                # Add results to the dictionary
                logfile_status[monitor_name] = {'logname': os.path.basename(latest_log),
                                                'latest_time': latest_log_time,
                                                'missing_file': missing_file, 'status': result}

    # Create table of results using Bokeh
    create_table(logfile_status)
    logging.info('Cron job status monitor completed successfully.')


def success_check(filename):
    """Parse the given log file and check whether the script execution
    was successful or not

    Parameters
    ----------
    filename : str
        Name of the log file to parse

    Returns
    -------
    execution : str
        ``success`` or ``failure``
    """
    with open(filename, 'r') as file_obj:
        all_lines = file_obj.readlines()
    final_line = all_lines[-1]
    if 'complete' in final_line.lower():
        execution = 'success'
    else:
        execution = 'failure'
    return execution


if __name__ == '__main__':

    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    status()
