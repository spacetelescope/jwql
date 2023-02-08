#!/usr/bin/env python

import argparse
from astropy.io import fits
from collections import OrderedDict
from copy import deepcopy
from glob import glob
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

from jwql.instrument_monitors.pipeline_tools import PIPELINE_STEP_MAPPING, get_pipeline_steps
from jwql.utils.logging_functions import configure_logging
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path


def run_pipe(input_file, short_name, work_directory, instrument, outputs):
    """Run the steps of ``calwebb_detector1`` on the input file, saving the result of each
    step as a separate output file, then return the name-and-path of the file as reduced
    in the reduction directory.
    """
    input_file_basename = os.path.basename(input_file)
    start_dir = os.path.dirname(input_file)
    status_file_name = short_name + "_status.txt"
    status_file = os.path.join(work_directory, status_file_name)
    uncal_file = os.path.join(work_directory, input_file_basename)
    
    with open(status_file, 'a+') as status_file:
        status_file.write("Starting pipeline\n")
    
    try:    
        copy_files([input_file_name], work_directory)
        set_permissions(uncal_file)
    
        steps = get_pipeline_steps(instrument)
        first_step_to_be_run = True
        for step_name in steps:
            with open(status_file, 'a+') as status_file:
                status_file.write("Running step {}\n".format(step_name))
            kwargs = {}
            if step_name in ['jump', 'rate']:
                kwargs = {'maximum_cores': 'all'}
            if steps[step_name]:
                output_file_name = short_name + "_{}.fits".format(step_name)
                output_file = os.path.join(work_directory, output_file_name)
                # skip already-done steps
                if not os.path.isfile(output_file):
                    if first_step_to_be_run:
                        model = PIPELINE_STEP_MAPPING[step_name].call(input_file_name, **kwargs)
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
                
                    done = True
                    for output in outputs:
                        output_name = "{}_{}.fits".format(short_name, output)
                        output_check_file = os.path.join(work_directory, output_name)
                        if not os.path.isfile(output_check_file):
                            done = False
                    if done:
                        break
    except Exception as e:
        with open(status_file, "a+") as statfile:
            statfile.write("EXCEPTION\n")
            statfile.write("{}\n".format(e))
            statfile.write("FAILED")
        sys.exit(1)
    
    with open(status_file, "a+") as statfile:
        statfile.write("SUCCEEDED")
    # Done.


def run_save_jump(input_file_name, short_name, work_directory, instrument, ramp_fit=True, save_fitopt=True):
    """Call ``calwebb_detector1`` on the provided file, running all
    steps up to the ``ramp_fit`` step, and save the result. Optionally
    run the ``ramp_fit`` step and save the resulting slope file as well.
    """
    input_file_basename = os.path.basename(input_file_name)
    start_dir = os.path.dirname(input_file_name)
    status_file_name = short_name + "_status.txt"
    status_file = os.path.join(work_directory, status_file_name)
    uncal_file = os.path.join(work_directory, input_file_basename)

    with open(status_file, 'a+') as status_file:
        status_file.write("Starting pipeline\n")
    
    try:
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
        model.jump.output_dir = os.getcwd()
        model.jump.maximum_cores = 'all'
        jump_output = uncal_file.replace('uncal', 'jump')

        # Check to see if the jump version of the requested file is already
        # present
        run_jump = not os.path.isfile(jump_output)

        if ramp_fit:
            model.ramp_fit.save_results = True
            model.ramp_fit.maximum_cores = 'all'
            # model.save_results = True
            model.output_dir = os.getcwd()
            # pipe_output = os.path.join(output_dir, input_file_only.replace('uncal', 'rate'))
            pipe_output = uncal_file.replace('uncal', '0_ramp_fit')
            run_slope = not os.path.isfile(pipe_output)
            if save_fitopt:
                model.ramp_fit.save_opt = True
                fitopt_output = uncal_file.replace('uncal', 'fitopt')
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

        if run_jump or (ramp_fit and run_slope) or (save_fitopt and run_fitopt):
            model.run(datamodel)
        else:
            print(("Files with all requested calibration states for {} already present in "
                   "output directory. Skipping pipeline call.".format(uncal_file)))
    except Exception as e:
        with open(status_file, "a+") as statfile:
            statfile.write("EXCEPTION\n")
            statfile.write("{}\n".format(e))
            statfile.write("FAILED")
        sys.exit(1)
    
    with open(status_file, "a+") as statfile:
        statfile.write("{}\n".format(jump_output))
        statfile.write("{}\n".format(pipe_output))
        statfile.write("{}\n".format(fitopt_output))
        statfile.write("SUCCEEDED")
    # Done.

#CompletedProcess(args=['/home/svc_jwqladm_mon/jwql/jwql/jwql/shared_tasks/run_pipeline.py', 'cal', 'refpix', '/internal/data1/outputs/ops/calibrated_data', 'niriss', '/grp/jwst/ins/jwql/transfer/ops/incoming/jw01499040001_02201_00001_nis_uncal.fits', 'jw01499040001_02201_00001_nis'], returncode=126)

if __name__ == '__main__':
    with open("/internal/data1/outputs/ops/calibrated_data/general_status.txt", "w") as status_file:
        status_file.write("Started at {}\n".format(time.ctime()))
        status_file.write("\targv={}\n".format(sys.argv))
        status_file.write("\toriginal argv={}\n".format(sys.orig_argv))

    file_help = 'Input file to calibrate'
    path_help = 'Directory in which to do the calibration'
    ins_help = 'Instrument that was used to produce the input file'
    pipe_help = 'Pipeline type to run (valid values are "jump" and "cal")'
    out_help = 'Comma-separated list of output extensions (for cal only, otherwise just "all")'
    name_help = 'Input file name with no path or extensions'
    parser = argparse.ArgumentParser(description='Run local calibration')
    parser.add_argument('pipe', metavar='PIPE', type=str, help=pipe_help)
    parser.add_argument('outputs', metavar='OUTPUTS', type=str, help=out_help)
    parser.add_argument('working_path', metavar='PATH', type=str, help=path_help)
    parser.add_argument('instrument', metavar='INSTRUMENT', type=str, help=ins_help)
    parser.add_argument('input_file', metavar='FILE', type=str, help=file_help)
    parser.add_argument('short_name', metavar='NAME', type=str, help=name_help)

    with open("/internal/data1/outputs/ops/calibrated_data/general_status.txt", "a+") as status_file:
        status_file.write("Created argument parser at {}\n".format(time.ctime()))

    try:
        args = parser.parse_args()
    except Exception as e:
        with open("/internal/data1/outputs/ops/calibrated_data/general_status.txt", "a+") as status_file:
            status_file.write("Error parsing arguments.\n")
            status_file.write("{}".format(e))
        raise e

    with open("/internal/data1/outputs/ops/calibrated_data/general_status.txt", "a+") as status_file:
        status_file.write("Finished parsing args at {}\n".format(time.ctime()))
    
    input_file = args.input_file
    instrument = args.instrument
    short_name = args.short_name
    working_path = args.working_path
    pipe_type = args.pipe
    outputs = args.outputs
    
    status_file = os.path.join(working_path, short_name+"_status.txt")
    with open(status_file, 'a+') as out_file:
        out_file.write("Starting Process\n")
        out_file.write("\tpipeline is {}\n".format(pipe_type))
        out_file.write("\toutputs is {}\n".format(outputs))
        out_file.write("\tworking_path is {}\n".format(working_path))
        out_file.write("\tinstrument is {}\n".format(instrument))
        out_file.write("\tinput_file is {}\n".format(input_file))
        out_file.write("\tshort_name is {}\n".format(short_name))
    
    if not os.path.isfile(args.input_file):
        raise FileNotFoundError("No input file {}".format(args.input_file))
    
    if pipe_type not in ['jump', 'cal']:
        raise ValueError("Unknown calibration type {}".format(pipe_type))

    if pipe_type == 'jump':
        with open(status_file, 'a+') as out_file:
            out_file.write("Running jump pipeline.\n")
        run_save_jump(input_file, short_name, working_path, instrument, ramp_fit=True, save_fitopt=True)
    elif pipe_type == 'cal':
        with open(status_file, 'a+') as out_file:
            out_file.write("Running cal pipeline.\n")
        outputs = outputs.split(",")
        run_pipe(input_file, short_name, work_directory, instrument, outputs)
