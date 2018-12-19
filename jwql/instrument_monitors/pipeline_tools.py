"""Various utility functions for the ``jwql`` project.

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be imported as such:

    >>> from jwql.instrument_monitors import pipeline_tools
    pipeline_steps = pipeline_tools.completed_pipeline_steps(filename)
 """

from collections import OrderedDict

from jwql.utils.utils import JWST_INSTRUMENTS
from jwst import datamodels

# Define the fits header keyword that accompanies each step
PIPE_KEYWORDS = {'S_GRPSCL': 'group_scale', 'S_DQINIT': 'dq_init', 'S_SATURA': 'saturation',
                 'S_REFPIX': 'refpix', 'S_SUPERB': 'superbias', 'S_IPC': 'ipc', 'S_PERSIS': 'persistence',
                 'S_DARK': 'dark_current', 'S_LINEAR': 'linearlity', 'S_FRSTFR': 'firstframe',
                 'S_LASTFR': 'lastframe', 'S_RSCD': 'rscd', 'S_JUMP': 'jump',  'S_RAMP': 'rate'}


def completed_pipeline_steps(filename):
    """
    Return a list of the completed pipeline steps for a given file.

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

    header = fits.getheader(input_file)
    for key in PIPE_KEYWORDS.keys():
        try:
            value = header.get(key)
            if value == 'COMPLETE':
                completed[PIPE_KEYWORDS[key]] = True
        except:
            pass
    return completed


def get_pipeline_steps(instrument):
    """Get the names and order of the calwebb_detector1
    pipeline steps for a given instrument. Use values that match up with the values in the
    PIPE_STEP defintion in definitions.py

    Parameters
    ----------

    instrument : str
        Name of JWST instrument

    Returns
    -------

    steps : collections.OrderedDict
        Dictionary of step names (and modules? do we care?)
    """
    instrument = instrument.upper()
    if instrument not in JWST_INSTRUMENTS:
        raise ValueError("WARNING: {} is not a valid instrument name.".format(instrument))
    # all_steps = Detector1Pipeline.step_defs

    # Order is important in 'steps' lists below!!
    if instrument == 'MIRI':
        steps = ['group_scale', 'dq_init', 'saturation', 'ipc', 'firstframe', 'lastframe',
                 'linearity', 'rscd', 'dark_current', 'refpix', 'persistence', 'jump', 'rate']
        # No persistence correction for MIRI
        steps.remove('persistence')
    else:
        steps = ['group_scale', 'dq_init', 'saturation', 'ipc', 'superbias', 'refpix', 'linearity',
                 'persistence', 'dark_current', 'jump', 'rate']

        # No persistence correction for NIRSpec
        if instrument == 'NIRSPEC':
            steps.remove('persistence')

    # Initialize using PIPE_KEYWORDS so the steps will be in the right
    # order
    req = OrderedDict({})
    for key in PIPE_KEYWORDS.values():
        req[key] = False
    if stepstr is None:
        return req

    for ele in steps:
        try:
            req[ele] = True
        except KeyError as error:
            print(error)
    return req


def run_calwebb_detector1(input_file, steps):
    """Run the steps of calwebb_detector1 specified in the steps
    dictionary on the input file

    Parameters
    ----------
    input_file : str
        File on which to run the pipeline steps

    steps : collections.OrderedDict
        Keys are the individual pipeline steps (as seen in the
        PIPE_KEYWORDS values above). Boolean values indicate
        whether a step should be run or not. Steps are run in the
        official calwebb_detector1 order.
    """
    for step_name in steps.keys():
        if step[step_name]:
            run_that_step!!


def steps_to_run(input_file, all_steps, finished_steps):
    """Given a list of pipeline steps that need to be completed as
    well as a list of steps that have already been completed, return
    a list of steps remaining to be done.

    Parameters
    ----------
    all_steps : collections.OrderedDict
        A dictionary of all steps that need to be completed

    finished_steps : collections.OrderedDict
        A dictionary with keys equal to the pipeline steps and boolean
        values indicating whether a particular step has been completed
        or not (i.e. output from completed_pipeline_steps)

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
            print(("WARNING: Input file {} has had {} step run, "
                   "but the requirements say that it should not "
                   "be. Need a new input file.".format(input_file, key)))
    return torun
