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
import gc
from glob import glob
import logging
from logging import FileHandler, StreamHandler
import os
import redis
import shutil
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
from celery.signals import after_setup_logger, after_setup_task_logger, task_postrun
from celery.utils.log import get_task_logger

REDIS_HOST = get_config()["redis_host"]
REDIS_PORT = get_config()["redis_port"]
REDIS_URL = "redis://{}:{}".format(REDIS_HOST, REDIS_PORT)
REDIS_CLIENT = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# Okay, let's explain these options:
#   - the first argument ('shared_tasks') is the task queue to listen to. We only have one,
#     and we've named it 'shared_tasks'. Both the clients (monitors) and the server(s)
#     (workers) need to use the same queue so that the workers are taking tasks from the 
#     same place that the monitors are putting them.
#   - the broker is the server that keeps track of tasks and task IDs. redis does this
#   - the backend is the server that keeps track of events. redis does this too
#   - worker_mask_tasks_per_child is how many tasks a process can run before it gets
#     restarted and replaced. This is set to 1 because the pipeline has memory leaks.
#   - worker_prefetch_multiplier is how many tasks a worker can reserve for itself at a 
#     time. If set to 0, a worker can reserve any number. If set to an integer, a single
#     worker can reserve that many tasks. We don't really want workers reserving tasks 
#     while they're already running a task, because tasks can take a long time to finish,
#     and there's no reason for the other workers to be sitting around doing nothing while
#     all the monitors are waiting on a single worker.
#   - worker_concurrency is how many task threads a worker can run concurrently on the same
#     machine. It's set to 1 because an individual pipeline process can consume all of the
#     available memory, so setting the concurrency higher will result in inevitable crashes.
celery_app = Celery('shared_tasks', broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(worker_max_tasks_per_child=1)
celery_app.conf.update(worker_prefetch_multiplier=1)
celery_app.conf.update(task_acks_late=True)
celery_app.conf.update(worker_concurrency=1)


def only_one(function=None, key="", timeout=None):
    """Enforce only one of the function running at a time. Import as decorator."""

    def _dec(run_func):
        """Decorator."""

        def _caller(*args, **kwargs):
            """Caller."""
            ret_value = None
            have_lock = False
            lock = REDIS_CLIENT.lock(key, timeout=timeout)
            try:
                have_lock = lock.acquire(blocking=False)
                if have_lock:
                    ret_value = run_func(*args, **kwargs)
                else:
                    logging.warning("Lock {} is already in use.".format(key))
                    msg = "If you believe that this is a stale lock, log in to {}"
                    msg += " and enter 'redis-cli del {}'"
                    logging.warning(msg.format(get_config()['redis_host'], key))
            finally:
                if have_lock:
                    lock.release()

            return ret_value

        return _caller

    return _dec(function) if function is not None else _dec

def create_task_log_handler(logger, propagate):
    log_file_name = configure_logging('shared_tasks')
    output_dir = os.path.join(get_config()['outputs'], 'calibrated_data')
    ensure_dir_exists(output_dir)
    celery_log_file_handler = FileHandler(log_file_name)
    logger.addHandler(celery_log_file_handler)
    for handler in logger.handlers:
        handler.setFormatter(TaskFormatter('%(asctime)s - %(task_id)s - %(task_name)s - %(name)s - %(levelname)s - %(message)s'))
    logger.propagate = propagate
    if not os.path.exists(os.path.join(output_dir, "celery_pipeline_log.cfg")):
        with open(os.path.join(output_dir, "celery_pipeline_log.cfg"), "w") as cfg_file:
            cfg_file.write("[*]\n")
            cfg_file.write("level = WARNING\n")
            cfg_file.write("handler = append:{}\n".format(log_file_name))

@after_setup_task_logger.connect
def after_setup_celery_task_logger(logger, **kwargs):
    """ This function sets the 'celery.task' logger handler and formatter """
    create_task_log_handler(logger, True)


@after_setup_logger.connect
def after_setup_celery_logger(logger, **kwargs):
    """ This function sets the 'celery' logger handler and formatter """
    create_task_log_handler(logger, False)


@task_postrun.connect
def collect_after_task(**kwargs):
    gc.collect()


@celery_app.task(name='jwql.shared_tasks.shared_tasks.run_calwebb_detector1')
def run_calwebb_detector1(input_file_name, instrument, step_args={}):
    """Run the steps of ``calwebb_detector1`` on the input file, saving the result of each
    step as a separate output file, then return the name-and-path of the file as reduced
    in the reduction directory.

    Parameters
    ----------
    input_file : str
        File on which to run the pipeline steps
    
    instrument : str
        Instrument that was used for the observation contained in input_file_name.

    step_args : dict
        A dictionary containing custom arguments to supply to individual pipeline steps. 
        When a step is run, the dictionary will be checked for a key matching the step 
        name (as defined in jwql.utils.utils.get_pipeline_steps() for the provided 
        instrument). The value matching the step key should, itself, be a dictionary that
        can be spliced in to step.call() via dereferencing (**dict)

    Returns
    -------
    reduction_path : str
        The path at which the reduced data file(s) may be found.
    """
    msg = "*****CELERY: Starting {} calibration task for {}"
    logging.info(msg.format(instrument, input_file_name))
    
    input_file = os.path.join(get_config()["transfer_dir"], "incoming", input_file_name)
    if not os.path.isfile(input_file):
        logging.error("*****CELERY: File {} not found!".format(input_file))
        raise FileNotFoundError("{} not found".format(input_file))
    
    cal_dir = os.path.join(get_config()['outputs'], "calibrated_data")
    uncal_file = os.path.join(cal_dir, input_file_name)
    short_name = input_file_name.replace("_0thgroup", "").replace("_uncal", "").replace("_dark", "").replace(".fits", "")
    ensure_dir_exists(cal_dir)
    copy_files([input_file], cal_dir)
    set_permissions(uncal_file)
    
    output_dir = os.path.join(get_config()["transfer_dir"], "outgoing")
    
    log_config = os.path.join(output_dir, "celery_pipeline_log.cfg")

    steps = get_pipeline_steps(instrument)

    first_step_to_be_run = True
    for step_name in steps:
        kwargs = {}
        if step_name in step_args:
            kwargs = step_args[step_name]
        if steps[step_name]:
            output_filename = short_name + "_{}.fits".format(step_name)
            output_file = os.path.join(cal_dir, output_filename)
            transfer_file = os.path.join(output_dir, output_filename)
            # skip already-done steps
            logging.info("*****CELERY: Running Pipeline Step {}".format(step_name))
            if not os.path.isfile(output_file):
                if first_step_to_be_run:
                    model = PIPELINE_STEP_MAPPING[step_name].call(uncal_file, logcfg=log_config, **kwargs)
                    first_step_to_be_run = False
                else:
                    model = PIPELINE_STEP_MAPPING[step_name].call(model, logcfg=log_config, **kwargs)

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
            else:
                logging.info("*****CELERY: File {} exists".format(output_filename))
            if not os.path.exists(transfer_file):
                copy_files([output_file], output_dir)
            set_permissions(transfer_file)

    logging.info("*****CELERY: Finished calibration.")
    return output_dir


@celery_app.task(name='jwql.shared_tasks.shared_tasks.calwebb_detector1_save_jump')
def calwebb_detector1_save_jump(input_file_name, ramp_fit=True, save_fitopt=True):
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
    """
    msg = "*****CELERY: Started Save Jump Task on {}. ramp_fit={}, save_fitopt={}"
    logging.info(msg.format(input_file_name, ramp_fit, save_fitopt))

    input_file = os.path.join(get_config()["transfer_dir"], "incoming", input_file_name)
    if not os.path.isfile(input_file):
        logging.error("*****CELERY: File {} not found!".format(input_file))
        raise FileNotFoundError("{} not found".format(input_file))
    
    cal_dir = os.path.join(get_config()['outputs'], "calibrated_data")
    uncal_file = os.path.join(cal_dir, input_file_name)
    short_name = input_file_name.replace("_uncal", "").replace("_0thgroup", "")
    ensure_dir_exists(cal_dir)
    copy_files([input_file], cal_dir)
    set_permissions(uncal_file)
    
    output_dir = os.path.join(get_config()["transfer_dir"], "outgoing")

    log_config = os.path.join(output_dir, "celery_pipeline_log.cfg")

    # Find the instrument used to collect the data
    datamodel = datamodels.RampModel(uncal_file)
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
    model.jump.output_dir = cal_dir
    jump_output = os.path.join(cal_dir, input_file.replace('uncal', 'jump'))
    
    model.logcfg = log_config

    # Check to see if the jump version of the requested file is already
    # present
    run_jump = not os.path.isfile(jump_output)

    if ramp_fit:
        model.ramp_fit.save_results = True
        # model.save_results = True
        model.output_dir = cal_dir
        # pipe_output = os.path.join(output_dir, input_file_only.replace('uncal', 'rate'))
        pipe_output = os.path.join(cal_dir, input_file.replace('uncal', '0_ramp_fit'))
        run_slope = not os.path.isfile(pipe_output)
        if save_fitopt:
            model.ramp_fit.save_opt = True
            fitopt_output = os.path.join(cal_dir, input_file.replace('uncal', 'fitopt'))
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
    logging.info("*****CELERY: Running save_jump pipeline")
    if run_jump or (ramp_fit and run_slope) or (save_fitopt and run_fitopt):
        model.run(datamodel)
    else:
        print(("Files with all requested calibration states for {} already present in "
               "output directory. Skipping pipeline call.".format(input_file)))
    
    calibrated_files = glob(uncal_file.replace("_uncal.fits", "*"))
    logging.info("*****CELERY: Pipeline Output is {}".format(calibrated_files))
    copy_files(calibrated_files, output_dir)

    logging.info("*****CELERY: Finished pipeline")
    return jump_output, pipe_output, fitopt_output


def prep_file(input_file, in_ext):
    """Prepares a file for calibration by:
    
    - Creating a short file-name from the file (i.e. the name without the calibration 
      extension)
    - Creating a redis lock on the short name
    - Copying the uncalibrated file into the transfer directory
    
    Returns the lock and the short name.
    
    Parameters
    ----------
    input_file : str
        Name of the fits file to run
    
    in_ext : str
        The calibration extension currently present on the input file
    
    Returns
    -------
    lock : redis lock
        Acquired lock on the input file
    
    short_name : str
        The exposure ID with the calibration tag and the fits extension chopped off.
    
    uncal_file : str
        The raw file to be calibrated
    """
    config = get_config()
    send_path = os.path.join(config["transfer_dir"], "incoming")
    ensure_dir_exists(send_path)
    receive_path = os.path.join(config["transfer_dir"], "outgoing")
    ensure_dir_exists(receive_path)
    
    input_path, input_name = os.path.split(input_file)
    logging.info("\tPath is {}, file is {}".format(input_path, input_name))

    if "uncal" not in in_ext:
        logging.info("\tSwitching from {} to uncal".format(in_ext))
        uncal_name = os.path.basename(input_file).replace(in_ext, "uncal")
        uncal_file = filesystem_path(uncal_name, check_existence=True)
    else:
        uncal_file = input_file
        uncal_name = input_name
    
    output_file_or_files = []
    short_name = input_name.replace("_"+in_ext, "").replace(".fits", "")
    logging.info("\tLocking {}".format(short_name))
    cal_lock = REDIS_CLIENT.lock(short_name)
    have_lock = cal_lock.acquire(blocking=True)
    if not have_lock:
        msg = "Waited for lock on {}, and was granted it, but don't have it!"
        logging.critical(msg.format(short_name))
        raise ValueError("Redis lock for {} is in an unknown state".format(short_name))
    logging.info("\t\tAcquired Lock.")
    logging.info("\t\tCopying {} to {}".format(input_file, send_path))
    copy_files([uncal_file], send_path)
    return short_name, cal_lock, os.path.join(send_path, uncal_name)


def start_pipeline(input_file, ext_or_exts, instrument, jump_pipe=False):
    """Starts the standard or save_jump pipeline for the provided file.
    
    .. warning::
    
        Only call this function if you have already locked the file using Redis.
    
    This function performs the following steps:
    
    - Determine whether to call calwebb_detector1 or save_jump tasks
    - If calling save_jump, determine which outputs are expected
    - Call the task
    - return the task result object (so that it can be dealt with appropriately)
    
    When this function returns, the task may or may not have started, and probably will 
    not have finished. Because the task was called using the ``delay()`` method, calling 
    ``result.get()`` will block until the result is available.
    
    .. warning::
    
        This function will not use the ``celery`` settings to trap exceptions, so calling
        ``result.get()`` *may* raise an exception if the task itself raises an exception.

    Parameters
    ----------
    input_file : str
        Name of fits file to run on the pipeline

    ext_or_exts : str or list-of-str
        The requested output calibrated files
    
    instrument : str
        Name of the instrument being calibrated
    
    jump_pipe : bool
        Whether the detector1 jump pipeline is being used (e.g. the bad pixel monitor)

    Returns
    -------
    result : celery.result.AsyncResult
        The task result object
    """
    if jump_pipe:
        ramp_fit = False
        save_fitopt = False
        for ext in ext_or_exts:
            if "ramp" in ext:
                ramp_fit = True
            elif "fitopt" in ext:
                save_fitopt = True
        result = calwebb_detector1_save_jump.delay(input_file, ramp_fit=ramp_fit, save_fitopt=save_fitopt)
    else:
        result = run_calwebb_detector1.delay(input_file, instrument)
    return result


def retrieve_files(short_name, ext_or_exts, dest_dir):
    """This function takes the name of a calibrated file, the desired extensions, the
    directory to which they should be copied, and a redis lock. It then does the following:
    
    - Copy the file(s) with the provided extensions to the output directory
    - Deletes the files from the transfer directory
    - Releases the lock
    
    Parameters
    ----------
    short_name : str
        Name of the calibrated file (without any calibration tags or file extension)

    ext_or_exts : str or list of str
        Desired extension(s)
    
    dest_dir : str
        Location for the desired extensions
    
    Returns
    -------
    output_file_or_files : str or list of str
        The location of the requested calibrated files                                                                                           
    """
    config = get_config()
    send_path = os.path.join(config["transfer_dir"], "incoming")
    ensure_dir_exists(send_path)
    receive_path = os.path.join(config["transfer_dir"], "outgoing")
    ensure_dir_exists(receive_path)
    
    if isinstance(ext_or_exts, str):
        ext_or_exts = [ext_or_exts]
    file_or_files = ["{}_{}.fits".format(short_name, x) for x in ext_or_exts]
    output_file_or_files = [os.path.join(dest_dir, x) for x in file_or_files]
    logging.info("\t\tCopying {} to {}".format(file_or_files, dest_dir))
    copy_files([os.path.join(receive_path, x) for x in file_or_files], dest_dir)
    logging.info("\t\tClearing Transfer Files")
    to_clear = glob(os.path.join(send_path, short_name+"*")) + glob(os.path.join(receive_path, short_name+"*"))
    for file in to_clear:
        os.remove(file)
    if len(output_file_or_files) == 1:
        output_file_or_files = output_file_or_files[0]
    return output_file_or_files


def run_pipeline(input_file, in_ext, ext_or_exts, instrument, jump_pipe=False):
    """Convenience function for using the ``run_calwebb_detector1`` function on a data 
    file, including the following steps:
    
    - Lock the file ID so that no other calibration happens at the same time
    - Copy the input (raw) file to the (central storage) transfer location
    - Call the ``run_calwebb_detector1`` task
    - For the extension (or extensions) (where by "extension" we mean 'uncal' or 'refpix'
      or 'jump' rather than something like '.fits') requested, copy the files from the 
      outgoing transfer location to the same directory as the input file
    - Delete the input file from the transfer location
    - Delete the output files from the transfer location
    
    It will then return what it was given – either a single file+path or a list of 
    files+paths, depending on what ``out_exts`` was provided as.

    Parameters
    ----------
    input_file : str
        Name of fits file to run on the pipeline

    ext_or_exts : str or list-of-str
        The requested output calibrated files
    
    instrument : str
        Name of the instrument being calibrated
    
    jump_pipe : bool
        Whether the detector1 jump pipeline is being used (e.g. the bad pixel monitor)

    Returns
    -------
    file_or_files : str or list-of-str
        Name (or names) of the result file(s), including path(s)
    """
    logging.info("Pipeline Call for {} requesting {}".format(input_file, ext_or_exts))
    try:
        retrieve_dir = os.path.dirname(input_file)
        cal_lock, short_name, uncal_file = prep_file(input_file, in_ext)
        result = start_pipeline(uncal_file, ext_or_exts, instrument, jump_pipe=jump_pipe)
        logging.info("\t\tStarting with ID {}".format(result.id))
        processed_path = result.get()
        logging.info("\t\tPipeline Complete")
        output = retrieve_files(short_name, ext_or_exts, retrieve_dir)
    except Exception as e:
        logging.error('\tPipeline processing failed for {}'.format(input_name))
        logging.error('\tProcessing raised {}'.format(e))
    finally:
        cal_lock.release()
        logging.info("\tReleased Lock {}".format(short_name))
    
    logging.info("Pipeline Call Completed")
    return output


def run_parallel_pipeline(input_files, in_ext, ext_or_exts, instrument, jump_pipe=False):
    """Convenience function for using the ``run_calwebb_detector1`` function on a list of
    data files, breaking them into parallel celery calls, collecting the results together,
    and returning the results as another list. In particular, this function will do the
    following:
    
    - Lock the file ID so that no other calibration happens at the same time
    - Copy the input (raw) file to the (central storage) transfer location
    - Call the ``run_calwebb_detector1`` task
    - For the extension (or extensions) (where by "extension" we mean 'uncal' or 'refpix'
      or 'jump' rather than something like '.fits') requested, copy the files from the 
      outgoing transfer location to the same directory as the input file
    - Delete the input file from the transfer location
    - Delete the output files from the transfer location
    
    It will then return what it was given – either a single file+path or a list of 
    files+paths, depending on what ``out_exts`` was provided as.

    Parameters
    ----------
    input_file : str
        Name of fits file to run on the pipeline
    
    in_ext : str
        Input file extension

    ext_or_exts : str or list-of-str
        The requested output calibrated files
    
    instrument : str
        Name of the instrument being calibrated
    
    jump_pipe : bool
        Whether the detector1 jump pipeline is being used (e.g. the bad pixel monitor)

    Returns
    -------
    file_or_files : str or list-of-str
        Name (or names) of the result file(s), including path(s)
    """
    logging.info("Pipeline call requestion calibrated extensions {}".format(ext_or_exts))
    for input_file in input_files:
        logging.info("\tCalibrating {}".format(input_file))
    
    input_file_paths = {}
    results = {}
    locks = {}
    outputs = {}
    output_dirs = {}

    logging.info("Dispatching celery tasks")
    try:
        for input_file in input_files:
            retrieve_dir = os.path.dirname(input_file)
            cal_lock, short_name, uncal_file = prep_file(input_file, in_ext)
            output_dirs[short_name] = retrieve_dir
            input_file_paths[short_name] = input_file
            locks[short_name] = cal_lock
            results[short_name] = start_pipeline(uncal_file, ext_or_exts, instrument, jump_pipe=jump_pipe)
            logging.info("\tStarting {} with ID {}".format(short_name, results[short_name].id))
        logging.info("Celery tasks submitted.")
        logging.info("Waiting for task results")
        for short_name in results:
            try:
                logging.info("\tWaiting for {} ({})".format(short_name, results[short_name].id))
                processed_path = results[short_name].get()
                logging.info("\t{} retrieved".format(short_name))
                outputs[input_file_paths[short_name]] = retrieve_files(short_name, ext_or_exts, output_dirs[short_name])
                logging.info("\tFiles copied for {}".format(short_name))
            except Exception as e:
                logging.error('\tPipeline processing failed for {}'.format(input_name))
                logging.error('\tProcessing raised {}'.format(e))
        logging.info("Finished retrieving results")
    finally:
        logging.info("Releasing locks")
        for short_name in locks:
            locks[short_name].release()
            logging.info("\tReleased Lock {}".format(short_name))
        logging.info("Finished releasing locks")
    
    logging.info("Pipeline Call Completed")
    return outputs


if __name__ == '__main__':

    pass
