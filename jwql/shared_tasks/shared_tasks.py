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
from collections import OrderedDict

import logging
from logging import FileHandler, StreamHandler
import os
import sys

from astropy.io import fits

from jwst import datamodels
from jwst.dq_init import DQInitStep
from jwst.dark_current import DarkCurrentStep
from jwst.firstframe import FirstFrameStep
from jwst.group_scale import GroupScaleStep
from jwst.ipc import IPCStep
from jwst.jump import JumpStep
from jwst.lastframe import LastFrameStep
from jwst.linearity import LinearityStep
from jwst.persistence import PersistenceStep
from jwst.pipeline.calwebb_detector1 import Detector1Pipeline
from jwst.ramp_fitting import RampFitStep
from jwst.refpix import RefPixStep
from jwst.rscd import RscdStep
from jwst.saturation import SaturationStep
from jwst.superbias import SuperBiasStep

from jwql.instrument_monitors.pipeline_tools import PIPELINE_STEP_MAPPING, get_pipeline_steps
from jwql.utils.logging_functions import configure_logging
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path

from celery import Celery
from celery.app.log import TaskFormatter
from celery.signals import after_setup_logger, after_setup_task_logger
from celery.utils.log import get_task_logger


celery_app = Celery('shared_tasks', 
                    broker='redis://localhost', 
                    backend='redis://localhost',
                    worker_max_memory_per_child=32*1024*1024 # new child after 32GB consumed
                    )


def create_task_log_handler(logger, propagate):
    celery_log_file_handler = FileHandler(configure_logging('shared_tasks'))
    celery_log_stream_handler = StreamHandler(sys.stdout)
    logger.addHandler(celery_log_file_handler)
    logger.addHandler(celery_log_stream_handler)
    for handler in logger.handlers:
        handler.setFormatter(TaskFormatter('%(asctime)s - %(task_id)s - %(task_name)s - %(name)s - %(levelname)s - %(message)s'))
    logger.propagate = propagate


@after_setup_task_logger.connect
def after_setup_celery_task_logger(logger, **kwargs):
    """ This function sets the 'celery.task' logger handler and formatter """
    create_task_log_handler(logger, True)


@after_setup_logger.connect
def after_setup_celery_logger(logger, **kwargs):
    """ This function sets the 'celery' logger handler and formatter """
    create_task_log_handler(logger, False)


@celery_app.task(name='jwql.shared_tasks.shared_tasks.run_calwebb_detector1')
def run_calwebb_detector1(input_file, instrument, path=None, tso=False):
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
    logging.info("Got calibration task with arguments {} {} {}".format(input_file, instrument, path))
    
    if "uncal" not in input_file:
        if "_" in input_file:
            short_name = input_file[:input_file.rfind("_")]
        else:
            short_name = input_file.replace(".fits", "")
        uncal_file = short_name + "_uncal.fits"
        if path is None or not os.path.isfile(os.path.join(path, uncal_file)):
            uncal_file = filesystem_path(uncal_file)
    else:
        short_name = input_file[:input_file.rfind("_uncal")]
        if os.path.isfile(os.path.join(path, input_file)):
            uncal_file = os.path.join(path, input_file)
        else:
            uncal_file = filesystem_path(input_file)

    output_dir = os.path.join(get_config()['outputs'], 'calibrated_data')
    ensure_dir_exists(output_dir)
    input_filename = os.path.join(output_dir, uncal_file)
    if not os.path.isfile(input_filename):
        copy_files([uncal_file], output_dir)
    set_permissions(input_filename)

    steps = get_pipeline_steps(instrument)

    first_step_to_be_run = True
    for step_name in steps:
        if steps[step_name]:
            output_filename = short_name + "_{}.fits".format(step_name)
            output_file = os.path.join(output_dir, output_filename)
            # skip already-done steps
            if not os.path.isfile(output_file):
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
                    model.save(output_file)
                else:
                    try:
                        model[0].meta.dither.dither_points = int(model[0].meta.dither.dither_points)
                    except TypeError:
                        # If the dither_points entry is not populated, then ignore this change
                        pass
                    model[0].save(output_file)
            set_permissions(output_file)

    logging.info("Finished calibration.")
    return output_dir

@celery_app.task(name='jwql.shared_tasks.shared_tasks.calwebb_detector1_save_jump')
def calwebb_detector1_save_jump(input_file, ramp_fit=True, save_fitopt=True, path=None, tso=False):
    """Call ``calwebb_detector1`` on the provided file, running all
    steps up to the ``ramp_fit`` step, and save the result. Optionally
    run the ``ramp_fit`` step and save the resulting slope file as well.

    Parameters
    ----------
    input_file : str
        Name of fits file to run on the pipeline

    ramp_fit : bool
        If ``False``, the ``ramp_fit`` step is not run. The output file
        will be a ``*_jump.fits`` file.
        If ``True``, the ``*jump.fits`` file will be produced and saved.
        In addition, the ``ramp_fit`` step will be run and a
        ``*rate.fits`` or ``*_rateints.fits`` file will be saved.
        (``rateints`` if the input file has >1 integration)

    save_fitopt : bool
        If ``True``, the file of optional outputs from the ramp fitting
        step of the pipeline is saved.

    Returns
    -------
    jump_output : str
        Name of the saved file containing the output prior to the
        ``ramp_fit`` step.

    pipe_output : str
        Name of the saved file containing the output after ramp-fitting
        is performed (if requested). Otherwise ``None``.

    fitopt_output : str
        Name of the saved file containing the output after ramp-fitting
        is performed (if requested). Otherwise ``None``.

    output_dir : str
        Name of the directory where the output file is saved
    """
    msg = "Started Task. with inputs {} {} {} {}"
    logging.info(msg.format(input_file, ramp_fit, save_fitopt, path))

    if "uncal" not in input_file:
        if "_" in input_file:
            short_name = input_file[:input_file.rfind("_")]
        else:
            short_name = input_file.replace(".fits", "")
        uncal_file = short_name + "_uncal.fits"
        if path is None or not os.path.isfile(os.path.join(path, uncal_file)):
            uncal_file = filesystem_path(uncal_file)
    else:
        short_name = input_file[:input_file.rfind("_uncal")]
        if os.path.isfile(os.path.join(path, input_file)):
            uncal_file = os.path.join(path, input_file)
        else:
            uncal_file = filesystem_path(input_file)

    output_dir = os.path.join(get_config()['outputs'], 'calibrated_data')
    ensure_dir_exists(output_dir)
    input_filename = os.path.join(output_dir, uncal_file)
    if not os.path.isfile(input_filename):
        copy_files([uncal_file], output_dir)
    set_permissions(input_filename)

    input_file_only = input_file

    # Find the instrument used to collect the data
    datamodel = datamodels.RampModel(input_filename)
    instrument = datamodel.meta.instrument.name.lower()

    # If the data pre-date jwst version 1.2.1, then they will have
    # the NUMDTHPT keyword (with string value of the number of dithers)
    # rather than the newer NRIMDTPT keyword (with an integer value of
    # the number of dithers). If so, we need to update the file here so
    # that it doesn't cause the pipeline to crash later. Both old and
    # new keywords are mapped to the model.meta.dither.dither_points
    # metadata entry. So we should be able to focus on that.
    if isinstance(datamodel.meta.dither.dither_points, str):
        # If we have a string, change it to an integer
        datamodel.meta.dither.dither_points = int(datamodel.meta.dither.dither_points)
    elif datamodel.meta.dither.dither_points is None:
        # If the information is missing completely, put in a dummy value
        datamodel.meta.dither.dither_points = 1

    # Switch to calling the pipeline rather than individual steps,
    # and use the run() method so that we can set parameters
    # progammatically.
    model = Detector1Pipeline()

    # Always true
    if instrument == 'nircam':
        model.refpix.odd_even_rows = False

    # Default CR rejection threshold is too low
    model.jump.rejection_threshold = 15

    # Turn off IPC step until it is put in the right place
    model.ipc.skip = True

    model.jump.save_results = True
    model.jump.output_dir = output_dir
    jump_output = os.path.join(output_dir, input_file_only.replace('uncal', 'jump'))

    # Check to see if the jump version of the requested file is already
    # present
    run_jump = not os.path.isfile(jump_output)

    if ramp_fit:
        model.ramp_fit.save_results = True
        # model.save_results = True
        model.output_dir = output_dir
        # pipe_output = os.path.join(output_dir, input_file_only.replace('uncal', 'rate'))
        pipe_output = os.path.join(output_dir, input_file_only.replace('uncal', '0_ramp_fit'))
        run_slope = not os.path.isfile(pipe_output)
        if save_fitopt:
            model.ramp_fit.save_opt = True
            fitopt_output = os.path.join(output_dir, input_file_only.replace('uncal', 'fitopt'))
            run_fitopt = not os.path.isfile(fitopt_output)
        else:
            model.ramp_fit.save_opt = False
            fitopt_output = None
            run_fitopt = False
    else:
        model.ramp_fit.skip = True
        pipe_output = None
        fitopt_output = None
        run_slope = False
        run_fitopt = False

    # Call the pipeline if any of the files at the requested calibration
    # states are not present in the output directory
    if run_jump or (ramp_fit and run_slope) or (save_fitopt and run_fitopt):
        model.run(datamodel)
    else:
        print(("Files with all requested calibration states for {} already present in "
               "output directory. Skipping pipeline call.".format(input_file)))

    logging.info("Finished pipeline")
    return jump_output, pipe_output, fitopt_output, output_dir


if __name__ == '__main__':

    pass
