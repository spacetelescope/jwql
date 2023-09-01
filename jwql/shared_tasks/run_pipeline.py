#!/usr/bin/env python

import argparse
from astropy.io import fits
from collections import OrderedDict
from copy import deepcopy
from glob import glob
import json
import os
import shutil
import sys
import time

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

from jwql.instrument_monitors.pipeline_tools import PIPELINE_STEP_MAPPING, completed_pipeline_steps, get_pipeline_steps
from jwql.utils.logging_functions import configure_logging
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path


def run_pipe(input_file, short_name, work_directory, instrument, outputs, max_cores='all', step_args={}):
    """Run the steps of ``calwebb_detector1`` on the input file, saving the result of each
    step as a separate output file, then return the name-and-path of the file as reduced
    in the reduction directory.
    """
    input_file_basename = os.path.basename(input_file)
    start_dir = os.path.dirname(input_file)
    status_file_name = short_name + "_status.txt"
    status_file = os.path.join(work_directory, status_file_name)
    uncal_file = os.path.join(work_directory, input_file_basename)

    with open(status_file, 'a+') as status_f:
        status_f.write("Running run_pipe\n")
        status_f.write("\t input_file_basename is {} ({})\n".format(input_file_basename, type(input_file_basename)))
        status_f.write("\t start_dir is {} ({})\n".format(start_dir, type(start_dir)))
        status_f.write("\t uncal_file is {} ({})\n".format(uncal_file, type(uncal_file)))
        status_f.write(f"\t outputs is {outputs}\n")

    try:
        copy_files([input_file], work_directory)
        set_permissions(uncal_file)

        steps = get_pipeline_steps(instrument)

        # If the input file is a file other than uncal.fits, then we may only need to run a
        # subset of steps. Check the completed steps in the input file. Find the latest step
        # that has been completed, and skip that plus all prior steps
        if 'uncal' not in input_file:
            completed_steps = completed_pipeline_steps(input_file)

            # Reverse the boolean value, so that now steps answers the question: "Do we need
            # to run this step?""
            for step in steps:
                steps[step] = not completed_steps[step]

        # Make sure we don't run steps out of order. Find the latest step that has been
        # run, and only run subsequent steps. This protects against cases where some early
        # step was not run. In that case, we don't want to go back and run it because running
        # pipeline steps out of order doesn't work.
        if instrument in ['miri', 'nirspec']:
            last_run = 'group_scale'  # initialize to the first step
        else:
            last_run = 'dq_init'

        for step in steps:
            if not steps[step]:
                last_run = deepcopy(step)

        for step in steps:
            if step == last_run:
                break
            if step != last_run:
                steps[step] = False

        # Set any steps the user specifically asks to skip
        for step, step_dict in step_args.items():
            if 'skip' in step_dict:
                if step_dict['skip']:
                    steps[step] = False

        # Run each specified step
        first_step_to_be_run = True
        for step_name in steps:
            kwargs = {}
            if step_name in step_args:
                kwargs = step_args[step_name]
            if step_name in ['jump', 'rate']:
                kwargs['maximum_cores'] = max_cores
            if steps[step_name]:
                sys.stderr.write("Running step {}\n".format(step_name))
                with open(status_file, 'a+') as status_f:
                    status_f.write("Running step {}\n".format(step_name))
                output_file_name = short_name + "_{}.fits".format(step_name)
                output_file = os.path.join(work_directory, output_file_name)
                # skip already-done steps
                if not os.path.isfile(output_file):
                    if first_step_to_be_run:
                        model = PIPELINE_STEP_MAPPING[step_name].call(input_file, **kwargs)
                        first_step_to_be_run = False
                    else:
                        model = PIPELINE_STEP_MAPPING[step_name].call(model, **kwargs)

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
                        if 'rateints' in outputs:
                            outbase = os.path.basename(output_file)
                            outbase = outbase.replace('rate', 'rateints')
                            output_file = os.path.join(work_directory, outbase)
                            model[1].save(output_file)
                            with open(status_file, 'a+') as status_f:
                                status_f.write(f"Saved rateints model to {output_file}\n")
                    done = True
                    for output in outputs:
                        output_name = "{}_{}.fits".format(short_name, output)
                        output_check_file = os.path.join(work_directory, output_name)
                        if not os.path.isfile(output_check_file):
                            done = False
                    if done:
                        sys.stderr.write("Done pipeline.\n")
                        break
            else:
                sys.stderr.write("Skipping step {}\n".format(step_name))
                with open(status_file, 'a+') as status_f:
                    status_f.write("Skipping step {}\n".format(step_name))

    except Exception as e:
        with open(status_file, "a+") as status_f:
            status_f.write("EXCEPTION\n")
            status_f.write("{}\n".format(e))
            status_f.write("FAILED")
        sys.exit(1)

    with open(status_file, "a+") as status_f:
        status_f.write("SUCCEEDED")
    # Done.


def run_save_jump(input_file, short_name, work_directory, instrument, ramp_fit=True, save_fitopt=True, max_cores='all', step_args={}):
    """Call ``calwebb_detector1`` on the provided file, running all
    steps up to the ``ramp_fit`` step, and save the result. Optionally
    run the ``ramp_fit`` step and save the resulting slope file as well.
    """
    input_file_basename = os.path.basename(input_file)
    status_file_name = short_name + "_status.txt"
    status_file = os.path.join(work_directory, status_file_name)
    uncal_file = os.path.join(work_directory, input_file_basename)

    sys.stderr.write("Starting pipeline\n")
    with open(status_file, 'a+') as status_f:
        status_f.write("Starting pipeline\n")

    try:
        copy_files([input_file], work_directory)
        set_permissions(uncal_file)

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
        params = {}

        # Always true
        if instrument == 'nircam':
            params['refpix'] = dict(odd_even_rows=False)

        # Default CR rejection threshold is too low
        params['jump']['rejection_threshold'] = 15

        # Set up to save jump step output
        params['jump']['save_results'] = True
        params['jump']['output_dir'] = work_directory
        params['jump']['maximum_cores'] = max_cores
        jump_output = short_name + '_jump.fits'

        # Check to see if the jump version of the requested file is already
        # present
        run_jump = not os.path.isfile(jump_output)

        if ramp_fit:
            params['ramp_fit'] = dict(save_results=True, maximum_cores=max_cores)

            pipe_output = os.path.join(work_directory, short_name + '_0_ramp_fit.fits')
            run_slope = not os.path.isfile(pipe_output)
            if save_fitopt:
                params['ramp_fit']['save_opt'] = True
                fitopt_output = os.path.join(work_directory, short_name + '_fitopt.fits')
                run_fitopt = not os.path.isfile(fitopt_output)
            else:
                params['ramp_fit']['save_opt'] = False
                fitopt_output = None
                run_fitopt = False
        else:
            params['ramp_fit']['skip'] = True
            pipe_output = None
            fitopt_output = None
            run_slope = False
            run_fitopt = False

        # If the input file is dark.fits rather than uncal.fits, then skip
        # all of the pipeline steps that are run prior to dark subtraction
        if 'dark.fits' in input_file:
            if instrument.lower() == 'miri':
                steps_to_skip = ['group_scale', 'dq_init', 'saturation', 'ipc', 'firstframe',
                                 'lastframe', 'reset', 'linearity', 'rscd']
            else:
                steps_to_skip = ['group_scale', 'dq_init', 'saturation', 'ipc', 'superbias',
                                 'refpix', 'linearity']
            for step in steps_to_skip:
                step_dict = dict(skip=True)
                if step in params:
                    params[step] = params[step].update(step_dict)
                else:
                    params[step] = dict(skip=True)
        else:
            # Turn off IPC step until it is put in the right place
            params['ipc'] = dict(skip=True)

        # Include any user-specified parameters
        for step_name in step_args:
            if step_name in params:
                params[step_name] = params[step_name].update(step_args[step_name])
            else:
                params[step_name] = step_args[step_name]

        if run_jump or (ramp_fit and run_slope) or (save_fitopt and run_fitopt):
            model.call(datamodel, output_dir=work_directory, steps=params)
        else:
            print(("Files with all requested calibration states for {} already present in "
                   "output directory. Skipping pipeline call.".format(uncal_file)))
    except Exception as e:
        with open(status_file, "a+") as status_f:
            status_f.write("EXCEPTION\n")
            status_f.write("{}\n".format(e))
            status_f.write("FAILED")
        sys.exit(1)

    with open(status_file, "a+") as status_f:
        status_f.write("{}\n".format(jump_output))
        status_f.write("{}\n".format(pipe_output))
        status_f.write("{}\n".format(pipe_output.replace("0_ramp", "1_ramp")))
        status_f.write("{}\n".format(fitopt_output))
        status_f.write("SUCCEEDED")
    # Done.


if __name__ == '__main__':
    status_dir = os.path.join(get_config()['outputs'], 'calibrated_data')
    general_status_file = os.path.join(status_dir, "general_status.txt")

    with open(general_status_file, "w") as status_file:
        status_file.write("Started at {}\n".format(time.ctime()))
        status_file.write("\targv={}\n".format(sys.argv))

    file_help = 'Input file to calibrate'
    path_help = 'Directory in which to do the calibration'
    ins_help = 'Instrument that was used to produce the input file'
    pipe_help = 'Pipeline type to run (valid values are "jump" and "cal")'
    out_help = 'Comma-separated list of output extensions (for cal only, otherwise just "all")'
    name_help = 'Input file name with no path or extensions'
    cores_help = 'Maximum cores to use (default "all")'
    step_args_help = 'Step-specific parameter value nested dictionary'
    parser = argparse.ArgumentParser(description='Run local calibration')
    parser.add_argument('pipe', metavar='PIPE', type=str, help=pipe_help)
    parser.add_argument('outputs', metavar='OUTPUTS', type=str, help=out_help)
    parser.add_argument('working_path', metavar='PATH', type=str, help=path_help)
    parser.add_argument('instrument', metavar='INSTRUMENT', type=str, help=ins_help)
    parser.add_argument('input_file', metavar='FILE', type=str, help=file_help)
    parser.add_argument('short_name', metavar='NAME', type=str, help=name_help)
    parser.add_argument('max_cores', metavar='CORES', type=str, help=cores_help)
    parser.add_argument('--step_args', metavar='STEP_ARGS', type=json.loads, default='{}', help=step_args_help)

    with open(general_status_file, "a+") as status_file:
        status_file.write("Created argument parser at {}\n".format(time.ctime()))

    try:
        args = parser.parse_args()
    except Exception as e:
        with open(general_status_file, "a+") as status_file:
            status_file.write("Error parsing arguments.\n")
            status_file.write("{}".format(e))
        raise e

    with open(general_status_file, "a+") as status_file:
        status_file.write("Finished parsing args at {}\n".format(time.ctime()))

    input_file = args.input_file
    instrument = args.instrument
    short_name = args.short_name
    working_path = args.working_path
    pipe_type = args.pipe
    outputs = args.outputs
    step_args = args.step_args

    status_file = os.path.join(working_path, short_name+"_status.txt")
    with open(status_file, 'w') as out_file:
        out_file.write("Starting Process\n")
        out_file.write("\tpipeline is {} ({})\n".format(pipe_type, type(pipe_type)))
        out_file.write("\toutputs is {} ({})\n".format(outputs, type(outputs)))
        out_file.write("\tworking_path is {} ({})\n".format(working_path, type(working_path)))
        out_file.write("\tinstrument is {} ({})\n".format(instrument, type(instrument)))
        out_file.write("\tinput_file is {} ({})\n".format(input_file, type(input_file)))
        out_file.write("\tshort_name is {} ({})\n".format(short_name, type(short_name)))
        out_file.write("\tstep_args is {} ({})\n".format(step_args, type(step_args)))

    if not os.path.isfile(args.input_file):
        raise FileNotFoundError("No input file {}".format(args.input_file))

    if pipe_type not in ['jump', 'cal']:
        raise ValueError("Unknown calibration type {}".format(pipe_type))

    try:
        if pipe_type == 'jump':
            with open(status_file, 'a+') as out_file:
                out_file.write("Running jump pipeline.\n")
            run_save_jump(input_file, short_name, working_path, instrument, ramp_fit=True, save_fitopt=True, max_cores=args.max_cores, step_args=args.step_args)
        elif pipe_type == 'cal':
            with open(status_file, 'a+') as out_file:
                out_file.write("Running cal pipeline.\n")
            outputs = outputs.split(",")
            run_pipe(input_file, short_name, working_path, instrument, outputs, max_cores=args.max_cores, step_args=args.step_args)
    except Exception as e:
        with open(status_file, 'a+') as out_file:
            out_file.write("Exception when starting pipeline.\n")
            out_file.write("{}\n".format(e))
        raise e
