#! /usr/bin/env python

"""This module monitors the status of monitors run via cron job via log files. Basic
results (e.g. success, failure) are collected

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be executed as such:

    ::

        from somewhere import something
        something.doooooo_it()

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

#from bokeh.charts import save, output_file
from bokeh.embed import components
from bokeh.io import output_file, save, show
from bokeh.layouts import widgetbox
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, DateFormatter, HTMLTemplateFormatter, TableColumn

from jwql.utils.logging_functions import configure_logging, log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import get_config


def create_table(status_dict):
    """Create interactive Bokeh table containing the logfile status results. Modified from
    https://bokeh.pydata.org/en/latest/docs/user_guide/examples/interaction_data_table.html

    Parameters
    ----------
    status_dict : dict
        Status results from all logfiles
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
    print(data)
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

    # Save the plot as full html
    output_dir = get_config()['outputs']
    output_filename = "cron_status_table"
    html_filename = output_filename + '.html'
    outfile = os.path.join(output_dir, 'monitor_cron_jobs', html_filename)
    output_file(outfile)
    print("Show only during development")
    show(widgetbox(data_table))
    #save(outfile)
    #set_permissions(outfile)
    #logging.info('Saved Bokeh DataTable as html file: {}'.format(outfile))

    # Save plot as components
    script, div = components(data_table)

    div_outfile = os.path.join(output_dir, 'monitor_cron_jobs', output_filename + "_component.html")
    with open(div_outfile, 'w') as f:
        f.write(div)
        f.close()
    #set_permissions(div_outfile)

    script_outfile = os.path.join(output_dir, 'monitor_cron_jobs', output_filename + "_component.js")
    with open(script_outfile, 'w') as f:
        f.write(script)
        f.close()
    #set_permissions(script_outfile)

    #logging.info('Saved Bokeh components files: {}_component.html and {}_component.js'
    #             .format(output_filename, output_filename))

    stophere


def find_latest(logfiles):
    """Given a list of log files in a directory, identify the most recent.
    We should be able to do this by either looking at timestamps, or by
    parsing filenames. Let's use timestamps.

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
    latest = max(logfiles, key=os.path.getctime)
    latest_time = os.path.getctime(latest)
    return (latest, latest_time)


def get_cadence(filenames):
    """Calculate the cadence of the log files in a given directory.
    Use timestamps

    Parameters
    ---------

    filenames : list
        List of log files to examine

    Returns
    -------

    mean_delta : float
        Mean time in seconds between the appearance of consecutive log files

    stdev_delta : float
        Standard deviation in seconds between the appearance of consecutive log files
    """
    times = [os.path.getctime(filename) for filename in filenames]
    if len(times) > 2:
        sorted_times = np.array(sorted(times))
        delta_times = sorted_times[1:] - sorted_times[0:-1]
        mean_delta = np.mean(delta_times)
        stdev_delta = np.std(delta_times)
    else:
        # If there are only 1 or 2 files, then let's assume we can't
        # get a reliable measure of cadence. Fall back to a value of
        # 1 year between files, to avoid accidentally flagging this monitor
        # as running late in the subsequent check
        mean_delta = 31556736.0  # sec per year
        stdev_delta = 31556736.0  # sec per year
    return mean_delta, stdev_delta


#@log_fail
#@log_info
def status(production_mode=True):
    """Main function: determine the status of the instrument montiors by examining
    log files.

    Parameters
    ----------

    production_mode : bool
        If true, look in the main log directory. If false, look in the dev log
        file directory.

    Returns
    -------

    logfile_status : dict
        Nested dictionary containing the status for all monitors. Top level keys
        include all monitors. Within a given monitor, the value is a dictionary
        containing 'missing_file' and 'status' keys. 'missing_file' is a boolean
        describing whether or not there is a suspected missing log file based
        on the timestamps of the existing files. 'status' is a string that is
        either 'success' or 'failure'.
    """
    # Begin logging
    #logging.info("Beginning cron job status monitor")

    # Get main logfile path
    #settings = get_config()
    #log_path = settings['log_dir']
    print("LOG PATH HARDWIRED FOR DEVELOPMENT. CHANGE BEFORE PUSHING")
    log_path = '/grp/jwst/ins/jwql/logs/'

    # If we are in development mode, the log files are in a slightly
    # different location than in production mode
    if not production_mode:
        log_path = os.path.join(log_path, 'dev')

    # Set up a dictionary to keep track of results
    logfile_status = {}

    # Get a list of the directories under the main logging directory.
    generator = os.walk(log_path, topdown=True)

    # Loop over monitors (note that subsubdir should always be empty)
    for subdir, subsubdir, filenames in generator:
        if len(filenames) > 0:
            monitor_name = subdir.split('/')[-1]
            log_file_list = [os.path.join(subdir, filename) for filename in filenames]
            print('log_file_list', log_file_list)

            # Find the cadence of the monitor
            delta_time, stdev_time = get_cadence(log_file_list)
            print('delta_time: {}, {}'.format(delta_time, stdev_time))

            # Identify the most recent log file
            latest_log, latest_log_time = find_latest(log_file_list)
            print('latest_log: {}'.format(latest_log))

            # Check to see if we expect a file more recent than the latest
            missing_file = missing_file_check(delta_time, stdev_time, latest_log)
            if missing_file:
                print('Expected a more recent {} logfile than {}'.format(monitor_name, os.path.basename(latest_log)))
                #logging.warning('Expected a more recent {} logfile than {}'
                #                .format(monitor_name, os.path.basename(latest_log)))

            # Check the file for success/failure
            result = success_check(latest_log)
            print('result: {}'.format(result))

            # Add results to the dictionary
            logfile_status[monitor_name] = {'logname': os.path.basename(latest_log),
                                            'latest_time': latest_log_time,
                                            'missing_file': missing_file, 'status': result}

    # Create table of results using Bokeh
    create_table(logfile_status)
    stophere
    return logfile_status


def missing_file_check(avg_time_between, uncertainty, latest_file):
    """Given the name of the most recent log file, along with the historical average
    time between files and the stdev of the time between files, determine whether we
    expect a more recent log file than the file given. This could hint at a problem
    with the cron job used to create the log files.

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
        False =  It is reasonable that the file given is the most recent
    """
    latest_time = os.path.getctime(latest_file)
    now = time.time()
    time_since_latest = now - latest_time
    if time_since_latest > (avg_time_between + 3 * uncertainty):
        late = True
    else:
        late = False
    return late


def success_check(filename):
    """Parse the given log file and check whether the script execution was
    successful or not

    Parameters
    ----------

    filename : str
        Name of the log file to parse

    Returns
    -------

    execution : str
        'success' or 'failure'
    """
    with open(filename, 'r') as file_obj:
        all_lines = file_obj.readlines()
    final_line = all_lines[-1]
    if 'complete' in final_line.lower():
        execution = 'success'
    else:
        execution = 'failure'
    return execution
