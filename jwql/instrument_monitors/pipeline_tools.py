"""Various utility functions related to the JWST calibration pipeline

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be imported as such:
    ::

        from jwql.instrument_monitors import pipeline_tools
        pipeline_steps = pipeline_tools.completed_pipeline_steps(filename)
 """

from collections import OrderedDict
import copy
import numpy as np
import os

from astropy.io import fits
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
from jwst.rscd import RSCD_Step
from jwst.saturation import SaturationStep
from jwst.superbias import SuperBiasStep

from jwql.utils.constants import JWST_INSTRUMENT_NAMES_UPPERCASE

# Define the fits header keyword that accompanies each step
PIPE_KEYWORDS = {'S_GRPSCL': 'group_scale', 'S_DQINIT': 'dq_init', 'S_SATURA': 'saturation',
                 'S_IPC': 'ipc', 'S_REFPIX': 'refpix', 'S_SUPERB': 'superbias',
                 'S_PERSIS': 'persistence', 'S_DARK': 'dark_current', 'S_LINEAR': 'linearity',
                 'S_FRSTFR': 'firstframe', 'S_LASTFR': 'lastframe', 'S_RSCD': 'rscd',
                 'S_JUMP': 'jump', 'S_RAMP': 'rate'}

PIPELINE_STEP_MAPPING = {'dq_init': DQInitStep, 'dark_current': DarkCurrentStep,
                         'firstframe': FirstFrameStep, 'group_scale': GroupScaleStep,
                         'ipc': IPCStep, 'jump': JumpStep, 'lastframe': LastFrameStep,
                         'linearity': LinearityStep, 'persistence': PersistenceStep,
                         'rate': RampFitStep, 'refpix': RefPixStep, 'rscd': RSCD_Step,
                         'saturation': SaturationStep, 'superbias': SuperBiasStep}

# Readout patterns that have nframes != a power of 2. These readout patterns
# require the group_scale pipeline step to be run.
GROUPSCALE_READOUT_PATTERNS = ['NRSIRS2']


def completed_pipeline_steps(filename):
    """Return a list of the completed pipeline steps for a given file.

    Parameters
    ----------
    filename : str
        File to examine

    Returns
    -------
    completed : collections.OrderedDict
        Dictionary with boolean entry for each pipeline step,
        indicating which pipeline steps have been run on filename
    """

    # Initialize using PIPE_KEYWORDS so that entries are guaranteed to
    # be in the correct order
    completed = OrderedDict({})
    for key in PIPE_KEYWORDS.values():
        completed[key] = False

    header = fits.getheader(filename)
    for key in PIPE_KEYWORDS.keys():
        try:
            value = header.get(key)
        except KeyError:
            value == 'NOT DONE'
        if value == 'COMPLETE':
            completed[PIPE_KEYWORDS[key]] = True

    return completed


def get_pipeline_steps(instrument):
    """Get the names and order of the ``calwebb_detector1`` pipeline
    steps for a given instrument. Use values that match up with the
    values in the ``PIPE_STEP`` defintion in ``definitions.py``

    Parameters
    ----------
    instrument : str
        Name of JWST instrument

    Returns
    -------
    steps : collections.OrderedDict
        Dictionary of step names
    """

    # Ensure instrument name is valid
    instrument = instrument.upper()
    if instrument not in JWST_INSTRUMENT_NAMES_UPPERCASE.values():
        raise ValueError("WARNING: {} is not a valid instrument name.".format(instrument))

    # Order is important in 'steps' lists below!!
    if instrument == 'MIRI':
        steps = ['group_scale', 'dq_init', 'saturation', 'ipc', 'firstframe', 'lastframe',
                 'linearity', 'rscd', 'dark_current', 'refpix', 'persistence', 'jump', 'rate']
        # No persistence correction for MIRI
        steps.remove('persistence')
        # MIRI is limited to one frame per group
        steps.remove('group_scale')
    else:
        steps = ['group_scale', 'dq_init', 'saturation', 'ipc', 'superbias', 'refpix', 'linearity',
                 'persistence', 'dark_current', 'jump', 'rate']

        # No persistence correction for NIRSpec
        if instrument == 'NIRSPEC':
            steps.remove('persistence')
        else:
            # NIRCam, NISISS, FGS all do not need group scale as nframes is
            # always a multiple of 2
            steps.remove('group_scale')

    # IPC correction currently not done for any instrument
    steps.remove('ipc')

    # Initialize using PIPE_KEYWORDS so the steps will be in the right order
    required_steps = OrderedDict({})
    for key in steps:
        required_steps[key] = True
    for key in PIPE_KEYWORDS.values():
        if key not in required_steps.keys():
            required_steps[key] = False

    return required_steps


def image_stack(file_list):
    """Given a list of fits files containing 2D images, read in all data
    and place into a 3D stack

    Parameters
    ----------
    file_list : list
        List of fits file names

    Returns
    -------
    cube : numpy.ndarray
        3D stack of the 2D images
    """

    exptimes = []
    for i, input_file in enumerate(file_list):
        with fits.open(input_file) as hdu:
            image = hdu[1].data
            exptime = hdu[0].header['EFFINTTM']
            num_ints = hdu[0].header['NINTS']

        # Stack all inputs together into a single 3D image cube
        if i == 0:
            ndim_base = image.shape
            if len(ndim_base) == 3:
                cube = copy.deepcopy(image)
            elif len(ndim_base) == 2:
                cube = np.expand_dims(image, 0)
        else:
            ndim = image.shape
            if ndim_base[-2:] == ndim[-2:]:
                if len(ndim) == 2:
                    image = np.expand_dims(image, 0)
                elif len(ndim) > 3:
                    raise ValueError("4-dimensional input slope images not supported.")
                cube = np.vstack((cube, image))
            else:
                raise ValueError("Input images are of inconsistent size in x/y dimension.")
        exptimes.append([exptime] * num_ints)

    return cube, exptimes


def run_calwebb_detector1_steps(input_file, steps):
    """Run the steps of ``calwebb_detector1`` specified in the steps
    dictionary on the input file

    Parameters
    ----------
    input_file : str
        File on which to run the pipeline steps

    steps : collections.OrderedDict
        Keys are the individual pipeline steps (as seen in the
        ``PIPE_KEYWORDS`` values above). Boolean values indicate whether
        a step should be run or not. Steps are run in the official
        ``calwebb_detector1`` order.
    """

    first_step_to_be_run = True
    for step_name in steps:
        if steps[step_name]:
            if first_step_to_be_run:
                model = PIPELINE_STEP_MAPPING[step_name].call(input_file)
                first_step_to_be_run = False
            else:
                model = PIPELINE_STEP_MAPPING[step_name].call(model)
            suffix = step_name
    output_filename = input_file.replace('.fits', '_{}.fits'.format(suffix))
    if suffix != 'rate':
        model.save(output_filename)
    else:
        model[0].save(output_filename)

    return output_filename


def calwebb_detector1_save_jump(input_file, output_dir, ramp_fit=True, save_fitopt=True):
    """Call ``calwebb_detector1`` on the provided file, running all
    steps up to the ``ramp_fit`` step, and save the result. Optionally
    run the ``ramp_fit`` step and save the resulting slope file as well.

    Parameters
    ----------
    input_file : str
        Name of fits file to run on the pipeline

    output_dir : str
        Directory into which the pipeline outputs are saved

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
    """
    input_file_only = os.path.basename(input_file)

    # Find the instrument used to collect the data
    instrument = fits.getheader(input_file)['INSTRUME'].lower()

    # Switch to calling the pipeline rather than individual steps,
    # and use the run() method so that we can set parameters
    # progammatically.
    model = Detector1Pipeline()

    # Always true
    if instrument == 'nircam':
        model.refpix.odd_even_rows = False

    # Default CR rejection threshold is too low
    model.jump.rejection_threshold = 15

    model.jump.save_results = True
    model.jump.output_dir = output_dir
    jump_output = os.path.join(output_dir, input_file_only.replace('uncal', 'jump'))

    # Check to see if the jump version of the requested file is already
    # present
    run_jump =  not os.path.isfile(jump_output)

    if ramp_fit:
        model.ramp_fit.save_results = True
        #model.save_results = True
        model.output_dir = output_dir
        #pipe_output = os.path.join(output_dir, input_file_only.replace('uncal', 'rate'))
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
        model.run(input_file)
    else:
        print(("Files with all requested calibration states for {} already present in "
               "output directory. Skipping pipeline call.".format(input_file)))

    return jump_output, pipe_output, fitopt_output


def steps_to_run(all_steps, finished_steps):
    """Given a list of pipeline steps that need to be completed as well
    as a list of steps that have already been completed, return a list
    of steps remaining to be done.

    Parameters
    ----------
    all_steps : collections.OrderedDict
        A dictionary of all steps that need to be completed

    finished_steps : collections.OrderedDict
        A dictionary with keys equal to the pipeline steps and boolean
        values indicating whether a particular step has been completed
        or not (i.e. output from ``completed_pipeline_steps``)

    Returns
    -------
    steps_to_run : collections.OrderedDict
        A dictionaru with keys equal to the pipeline steps and boolean
        values indicating whether a particular step has yet to be run.
    """

    torun = copy.deepcopy(finished_steps)

    for key in all_steps:
        if all_steps[key] == finished_steps[key]:
            torun[key] = False
        elif ((all_steps[key] is True) & (finished_steps[key] is False)):
            torun[key] = True
        elif ((all_steps[key] is False) & (finished_steps[key] is True)):
            print(("WARNING: {} step has been run "
                   "but the requirements say that it should not "
                   "be. Need a new input file.".format(key)))

    return torun
