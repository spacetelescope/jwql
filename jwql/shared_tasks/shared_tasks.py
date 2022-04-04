#! /usr/bin/env python

"""This module contains code for the celery application, which is used for any demanding 
work which should be restricted in terms of how many iterations are run simultaneously, or
which should be offloaded to a separate server as allowed. Currently, celery tasks exist 
for:

- Running the JWST pipeline on provided data files

In general, tasks should be created or used in situations where having multiple monitors 
(or parts of the website, etc.) running the same task would be wasteful (or has the 
potential for crashes due to system resources being exhausted). Tasks may be useful if 
multiple independent monitors might need the same thing (e.g. pipeline processing of the 
same data file), and having each of them producing that thing independently would be 
wasteful in terms of time and resources. If a task covers *both* cases, then it is 
particularly useful.

Because multiple monitors may be running at the same time, and may need the same task 
performed, and because running the same task multiple times would be as wasteful as just 
having each monitor run it independently, the celery-singleton module is used to require 
task uniqueness. This is transparent to the monitors involved, as a duplicate task will be 
given the same AsyncResult object as the existing task asking for the same resource, so 
the monitor can simply proceed as if it were the only one requesting the task.

Author
------

    - Brian York

Use
---

The basic method of running a celery task is::

    # This can, of course, be a relative import
    from jwql.shared_tasks.shared_tasks import <task>
    
    def some_function(some_arguments):
        # ... do some work ...
        task_result = <task>.delay(<arguments>)

        # Note that get() is a blocking call, so it will wait for the result to be 
        # available, and then return the result.
        # Note that if the task raises an exception, then the get() method will raise
        # the same exception. To avoid this, call get(propagate=False)
        return_value = task_result.get()
        if task_result.successful():
            # ... do work with the return value ...
        else:
            # do whatever needs to be done on failure
            # if you need an exception, look at task_result.traceback
        
        # ... do other work ...  

If you want to queue up multiple instances of the same task, and get the results back as 
a list::

    from celery import group
    from jwql.shared_tasks.shared_tasks import my_task
    
    # ...
    task_results = group(my_task.s(arg) for arg in some_list)
    for task_result in task_results.get():
        # do whatever result checking, and whatever work
    # ...

Finally, if you want to queue up a bunch of tasks and then work on them as they succeed 
(or fail), then one way to do so is::

    from jwql.shared_tasks.shared_tasks import my_task
    
    # ...
    def do_work(work_args):
        # ...
    
    # ...
    task_results = []
    for item in to_do_items:
        task_results.append(my_task.delay(item))
    
    while len(task_results) > 0:
        i = 0
        while i < len(task_results):
            if task_results[i].ready():
                task_result = task_results.pop(i)
                if task_result.successful():
                    do_work(task_result.get())
                else:
                    # ... handle failure ...
                    # REMEMBER that you need to call get() or forget() on the result.
                task_results.remove
            else:
                i += 1
        # in order to avoid busy-waiting, wait for a minute before checking again.
        sleep(60)

There are many other ways to call and use tasks, including ways to group tasks, run them 
synchronously, run a group of tasks with a final callback function, etc. These are best
explained by the celery documentation itself.
"""
from copy import copy, deepcopy
import datetime
import logging
import os

from astropy.io import ascii, fits
from astropy.modeling import models
from astropy.time import Time
import numpy as np
from pysiaf import Siaf
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.instrument_monitors import pipeline_tools
from jwql.utils import calculations, instrument_properties, monitor_utils
from jwql.utils.constants import ASIC_TEMPLATES, JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_DATAPRODUCTS, \
                                 RAPID_READPATTERNS
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path

from celery_singleton import Singleton
from celery import Celery


celery_app = Celery('shared_tasks', broker='redis://localhost:6379/0')


@celery_app.task(base=Singleton, unique_on=['input_file', ])
def run_calwebb_detector1(input_file, path=None):
    """Run the steps of ``calwebb_detector1`` on the input file, saving the result of each 
    step as a separate output file, then return the name-and-path of the file as reduced 
    in the reduction directory.

    Parameters
    ----------
    input_file : str
        File on which to run the pipeline steps
    
    path : str, default None
        The location to find the input file. If not provided, the input file will be 
        searched for in the JWQL data directories.
    
    Returns
    -------
    reduction_path : str
        The path at which the reduced data file(s) may be found.
    """
    if path is None or not os.path.isfile(os.path.join(path, input_file)):
        input_file = filesystem_path(input_file)

    output_dir = os.path.join(get_config()['outputs'], 'calibrated_data')
    ensure_dir_exists(output_dir)
    input_filename = os.path.join(output_dir, input_file)
    if not os.path.isfile(input_filename):
        copy_files([input_file], output_dir)
    header = fits.getheader(input_filename)
    # *****TODO***** can I get instrument this way?
    instrument = header['INSTRUME']
    
    required_steps = pipeline_tools.get_pipeline_steps(instrument)
    
    first_step_to_be_run = True
    for step_name in steps:
        if steps[step_name]:
            output_filename = input_file.replace(".fits", "_{}.fits".format(step_name))
            # skip already-done steps                
            if not os.path.isfile(output_filename):
                if first_step_to_be_run:
                    model = PIPELINE_STEP_MAPPING[step_name].call(input_filename)
                    first_step_to_be_run = False
                else:
                    model = PIPELINE_STEP_MAPPING[step_name].call(model)

                if step_name != 'rate':
                    # Make sure the dither_points metadata entry is at integer (was a 
                    # string prior to jwst v1.2.1, so some input data still have the 
                    # string entry.
                    # If we don't change that to an integer before saving the new file, 
                    # the jwst package will crash.
                    try:
                        model.meta.dither.dither_points = int(model.meta.dither.dither_points)
                    except TypeError:
                        # If the dither_points entry is not populated, then ignore this 
                        # change
                        pass
                    model.save(output_filename)
                else:
                    try:
                        model[0].meta.dither.dither_points = int(model[0].meta.dither.dither_points)
                    except TypeError:
                        # If the dither_points entry is not populated, then ignore this change
                        pass
                    model[0].save(output_filename)

    return output_dir


if __name__ == '__main__':

    pass
