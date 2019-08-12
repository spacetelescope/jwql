#! /usr/bin/env python

"""Tests for the ``pipeline_tools`` module.

Authors
-------

    - Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to stdout):
    ::

        pytest -s test_pipeline_tools.py
"""

from collections import OrderedDict
import os
import pytest

import numpy as np

from jwql.instrument_monitors import pipeline_tools
from jwql.utils.utils import get_config

# Determine if tests are being run on jenkins
ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_completed_pipeline_steps():
    """Test that the list of completed pipeline steps for a file is
    correct

    Parameters
    ----------
    filename : str
        File to be checked
    """

    filename = os.path.join(get_config()['filesystem'], 'jw00312',
                            'jw00312002001_02102_00001_nrcb4_rateints.fits')
    completed_steps = pipeline_tools.completed_pipeline_steps(filename)
    true_completed = OrderedDict([('group_scale', False),
                                  ('dq_init', True),
                                  ('saturation', True),
                                  ('ipc', False),
                                  ('refpix', True),
                                  ('superbias', True),
                                  ('persistence', True),
                                  ('dark_current', True),
                                  ('linearity', True),
                                  ('firstframe', False),
                                  ('lastframe', False),
                                  ('rscd', False),
                                  ('jump', True),
                                  ('rate', True)])

    # Only test steps that have a value of True
    completed_steps = OrderedDict((k, v) for k, v in completed_steps.items() if v is True)
    true_completed = OrderedDict((k, v) for k, v in true_completed.items() if v is True)

    assert completed_steps == true_completed


def test_get_pipeline_steps():
    """Test that the proper pipeline steps are returned for an
    instrument
    """

    # FGS, NIRCam, and NIRISS
    instruments = ['fgs', 'nircam', 'niriss']
    for instrument in instruments:
        req_steps = pipeline_tools.get_pipeline_steps(instrument)
        steps = ['dq_init', 'saturation', 'superbias', 'refpix', 'linearity',
                 'persistence', 'dark_current', 'jump', 'rate']
        not_required = ['group_scale', 'ipc', 'firstframe', 'lastframe', 'rscd']
        steps_dict = OrderedDict({})
        for step in steps:
            steps_dict[step] = True
        for step in not_required:
            steps_dict[step] = False

        # Only test steps that have a value of True
        req_steps = OrderedDict((k, v) for k, v in req_steps.items() if v is True)
        steps_dict = OrderedDict((k, v) for k, v in steps_dict.items() if v is True)
        assert req_steps == steps_dict

    # NIRSpec
    nrs_req_steps = pipeline_tools.get_pipeline_steps('nirspec')
    nrs_steps = ['group_scale', 'dq_init', 'saturation', 'superbias', 'refpix', 'linearity',
                 'dark_current', 'jump', 'rate']
    not_required = ['ipc', 'persistence', 'firstframe', 'lastframe', 'rscd']
    nrs_dict = OrderedDict({})
    for step in nrs_steps:
        nrs_dict[step] = True
    for step in not_required:
        nrs_dict[step] = False
    # Only test steps that have a value of True
    nrs_req_steps = OrderedDict((k, v) for k, v in nrs_req_steps.items() if v is True)
    nrs_dict = OrderedDict((k, v) for k, v in nrs_dict.items() if v is True)
    assert nrs_req_steps == nrs_dict

    # MIRI
    miri_req_steps = pipeline_tools.get_pipeline_steps('miri')
    miri_steps = ['dq_init', 'saturation', 'firstframe', 'lastframe',
                  'linearity', 'rscd', 'dark_current', 'refpix', 'jump', 'rate']
    not_required = ['group_scale', 'ipc', 'superbias', 'persistence']
    miri_dict = OrderedDict({})
    for step in miri_steps:
        miri_dict[step] = True
    for step in not_required:
        miri_dict[step] = False
    # Only test steps that have a value of True
    miri_req_steps = OrderedDict((k, v) for k, v in miri_req_steps.items() if v is True)
    miri_dict = OrderedDict((k, v) for k, v in miri_dict.items() if v is True)
    assert miri_req_steps == miri_dict


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_image_stack():
    """Test stacking of slope images"""

    directory = os.path.join(get_config()['test_dir'], 'dark_monitor')
    files = [os.path.join(directory, 'test_image_{}.fits'.format(str(i + 1))) for i in range(3)]

    image_stack, exptimes = pipeline_tools.image_stack(files)
    truth = np.zeros((3, 10, 10))
    truth[0, :, :] = 5.
    truth[1, :, :] = 10.
    truth[2, :, :] = 15.

    assert np.all(image_stack == truth)
    assert exptimes == [[10.5], [10.5], [10.5]]


def test_steps_to_run():
    """Test that the dictionaries for steps required and steps completed
    are correctly combined to create a dictionary of pipeline steps to
    be done

    Parameters
    ----------
    filename : str
        File to be checked

    required : OrderedDict
        Dict of all pipeline steps to be run on filename

    already_done : OrderedDict
        Dict of pipeline steps already run on filename
    """

    required = OrderedDict([('group_scale', True),
                            ('dq_init', False),
                            ('saturation', False),
                            ('ipc', False),
                            ('refpix', False),
                            ('superbias', False),
                            ('persistence', True),
                            ('dark_current', True),
                            ('linearity', False),
                            ('firstframe', False),
                            ('lastframe', False),
                            ('rscd', False),
                            ('jump', True),
                            ('rate', True)])
    already_done = OrderedDict([('group_scale', True),
                                ('dq_init', False),
                                ('saturation', False),
                                ('ipc', False),
                                ('refpix', False),
                                ('superbias', False),
                                ('persistence', True),
                                ('dark_current', True),
                                ('linearity', False),
                                ('firstframe', False),
                                ('lastframe', False),
                                ('rscd', False),
                                ('jump', False),
                                ('rate', False)])

    steps_to_run = pipeline_tools.steps_to_run(required, already_done)
    true_steps_to_run = OrderedDict([('group_scale', False),
                                     ('dq_init', False),
                                     ('saturation', False),
                                     ('ipc', False),
                                     ('refpix', False),
                                     ('superbias', False),
                                     ('persistence', False),
                                     ('dark_current', False),
                                     ('linearity', False),
                                     ('firstframe', False),
                                     ('lastframe', False),
                                     ('rscd', False),
                                     ('jump', True),
                                     ('rate', True)])

    assert steps_to_run == true_steps_to_run
