#!/usr/bin/env python
"""Tests for the ``jwql`` web application.

Authors
-------

    - Lauren Chambers

Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_website.py
"""

import sys
sys.path.append("../..")

import pytest

from jwql.utils.utils import JWST_INSTRUMENTS
from website.apps.jwql.data_containers import (
    get_acknowledgements, get_dashboard_components,
    get_filenames_by_instrument, get_header_info
)


def test_acknowledgements():
    """Checks that an acknowledgements list exists and has content."""

    acknowledgements = get_acknowledgements()
    assert isinstance(acknowledgements, list), 'Acknowledgements in invalid form'
    assert len(acknowledgements) > 0, 'No acknowledgements listed'


def test_dashboard():
    """Checks that there are dashboard components to display.  Also
    checks that the components have required HTML components.
    """

    dashboard_components = get_dashboard_components()
    assert len(dashboard_components) > 0, 'No dashboard components found'

    for monitor_key in dashboard_components.keys():
        for plot_key in dashboard_components[monitor_key]:
            div, script = dashboard_components[monitor_key][plot_key]
            assert '<div class="bk-root">' in div
            assert '<script type="text/javascript">' in script


@pytest.mark.xfail
def test_get_filesname_by_instrument():
    """Checks that the `get_filenames_by_instrument` function returns
    files for each instrument.
    """

    for instrument in JWST_INSTRUMENTS:
        filepaths = get_filenames_by_instrument(instrument)
        assert len(filepaths) > 0, 'No {} files found in filesystem'.format(instrument)


@pytest.mark.xfail
def test_get_header_info():
    """Checks that the `get_header_info` function returns a valid
    header.
    """

    header = get_header_info('jw86700007001_02101_00001_guider2_trapsfilled.fits')
    assert header.startswith('SIMPLE')
