#!/usr/bin/env python

"""Tests for the ``plotting`` module.

Authors
-------

    - Joe Filippazzo

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_plotting.py
"""

import glob
import os
import re
import sys

import bokeh
from pandas import DataFrame
import pytest

from jwql.utils.plotting import bar_chart

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
JWQL_DIR = __location__.split('tests')[0]


def test_bar_chart():
    """Make sure some dummy data generates a ``bokeh`` plot"""

    # Make a toy dataframe
    data = DataFrame({'meow': {'foo': 12, 'bar': 23, 'baz': 2},
                      'mix': {'foo': 45, 'bar': 31, 'baz': 23},
                      'deliver': {'foo': 62, 'bar': 20, 'baz': 9}})
    data = data.reset_index()

    # And generate a figure
    plt = bar_chart(data, 'index')

    assert str(type(plt)) == "<class 'bokeh.plotting.figure.Figure'>"


@pytest.mark.skipif(sys.version_info[:2] != (3, 6),
                    reason="Web server run on Python 3.6")
def test_bokeh_version():
    """Make sure that the current version of Bokeh matches the version being
    used in all the web app HTML templates.
    """
    env_version = bokeh.__version__

    template_paths = os.path.join(JWQL_DIR, 'website/apps/jwql/templates', '*.html')
    all_web_html_files = glob.glob(template_paths)

    for file in all_web_html_files:
        with open(file, 'r+', encoding="utf-8") as f:
            content = f.read()

        # Find all of the times "bokeh-#.#.#' appears in a template
        html_versions = re.findall(r'(?<=bokeh-)\d+\.\d+\.\d+', content)
        html_versions += re.findall(r'(?<=bokeh-widgets-)\d+\.\d+\.\d+', content)

        # Make sure they all match the environment version
        for version in html_versions:
            assert version == env_version, \
                'Bokeh version ({}) in HTML template {} '.format(version, os.path.basename(file)) + \
                'does not match current environment version ({}).'.format(env_version)
